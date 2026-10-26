import asyncio, json, os, sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from radarkit import http, store  # noqa: E402

from careerradar import api, boilerplate, classify, collect, config, issues, runner, trends  # noqa: E402
from careerradar.app import App  # noqa: E402


def run(c):
    return asyncio.run(c)


DAY = 86400
MON_W44 = 1792972800  # 2026-10-26T00:00:00Z, a Monday


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def world(monkeypatch):
    """An app on in-memory SQLite, two companies, a fake board per company and a fake AI and notify channel."""
    http.set_transport(None)
    board = {"acme": [], "beta": []}
    said, prompts = [], []

    async def fake_fetch(ats, tok, cutoff=None, eager=True, limit=8):
        return [dict(r) for r in board[tok]]
    monkeypatch.setattr(collect.boards, "fetch", fake_fetch)

    async def fake_resolve(rows, limit=8):
        return rows
    monkeypatch.setattr(collect.boards, "resolve_all", fake_resolve)

    async def fake_ai(system, user, **kw):
        prompts.append(user)
        return "# Headline here\n\n> One line dek.\n\n## Section\n\nBody." if "Telegram" not in system else "line one\nline two"
    monkeypatch.setattr("careerradar.write.ai.complete", fake_ai)
    cfg = config.load({"notify": {"channel": "print"}, "jev": {"enabled": False}, "api": {"public_url": "https://cr.test"},
                       "crawl": {"baseline_sample": 2}})
    cos = [{"name": "Acme", "slug": "acme", "segment": "ai-chips", "boards": ["greenhouse:acme"]},
           {"name": "Beta", "slug": "beta", "segment": "frontier-lab", "boards": ["greenhouse:beta"]}]
    clock = Clock(MON_W44 - 14 * DAY)
    app = App(store.SqliteStore(":memory:"), cfg, cos, env={"LINK_SECRET": "s3cret"}, clock=clock)

    async def fake_say(event, **vars):
        said.append((event, vars))
        return True
    app.say = fake_say
    run(app.setup())
    yield app, board, clock, said, prompts
    http.set_transport(None)


def job(i, title="Software Engineer", desc="We use Python and PyTorch.\nAbout Acme: a company that builds things for everyone, always."):
    return {"id": f"gh:x:{i}", "title": title, "url": f"https://x/{i}", "loc": "Paris, France", "date": "2026-10-01", "desc": desc}


def test_classify_titles():
    assert classify.function("Senior Software Engineer, Payments") == "Software engineering"
    assert classify.function("Research Engineer, RL") == "AI research"
    assert classify.function("Forward Deployed Engineer") == "Forward deployed & solutions"
    assert classify.function("Enterprise Account Executive") is None
    assert classify.function("Product Manager, API") is None
    assert classify.function("Sales Engineer") == "Forward deployed & solutions"
    assert classify.seniority("Staff Software Engineer") == "Staff"
    assert classify.seniority("Software Engineer Intern") == "Intern"
    assert classify.family("Senior Software Engineer, Payments (Remote)") == "software engineer"


def test_boilerplate_learned_and_stripped():
    descs = [f"Role {i} needs Rust.\nAbout us: we are a great company building the future of everything." for i in range(10)]
    b = boilerplate.learn(descs)
    assert boilerplate.strip(descs[0], b) == "Role 0 needs Rust."


def test_baseline_then_new_and_closed(world):
    app, board, clock, said, _ = world
    board["acme"] = [job(1), job(2), job(3, "Account Executive"), job(4)]
    r = run(collect.crawl(app, app.companies[0]))
    assert r["mode"] == "baseline" and r["tech"] == 3 and r["new"] == 0 and r["enriched"] == 2  # sample of 2
    rows = run(app.store.all("SELECT id, sampled, skills FROM postings ORDER BY id"))
    assert sum(r["sampled"] for r in rows) == 2
    clock.t += DAY
    board["acme"] = [job(1), job(2), job(5)]
    r = run(collect.crawl(app, app.companies[0]))
    assert r["mode"] == "crawl" and r["new"] == 1 and r["closed"] == 1


def test_shrunken_board_closes_nothing_and_alerts_on_second_failure(world):
    app, board, clock, said, _ = world
    board["acme"] = [job(i) for i in range(10)]
    run(collect.crawl(app, app.companies[0]))
    board["acme"] = [job(1)]
    for _ in range(2):
        clock.t += DAY
        r = run(collect.crawl(app, app.companies[0]))
        assert not r["ok"] and r["closed"] == 0
    assert [e for e, _ in said] == ["broken"]


def test_trends_ignore_companies_that_joined_this_week(world):
    app, board, clock, said, _ = world
    board["acme"] = [job(i) for i in range(4)]
    run(collect.crawl(app, app.companies[0]))  # acme baseline two weeks before W44
    clock.t = MON_W44 - 5 * DAY                # in W43
    board["acme"] = [job(i) for i in range(6)]
    run(collect.crawl(app, app.companies[0]))
    board["beta"] = [job(100 + i) for i in range(50)]
    run(collect.crawl(app, app.companies[1]))  # beta joins in W43: must not count as growth
    rows, cos = run(trends.load(app.store))
    s = trends.compute(rows, cos, "2026-W43", app.cfg)
    assert not s["baseline"] and s["companies_compared"] == 1
    assert s["totals"]["delta"] == 2 and s["totals"]["new"] == 2
    assert {c["slug"]: c["delta"] for c in s["companies_all"]} == {"acme": 2, "beta": None}


def test_issue_draft_hold_publish_with_signed_links(world):
    app, board, clock, said, prompts = world
    board["acme"] = [job(i) for i in range(3)]
    run(collect.crawl(app, app.companies[0]))
    clock.t = MON_W44 + 6 * 3600
    rec = run(runner.tick(app))
    assert rec["built"] == "2026-W43" and said[-1][0] == "draft"
    sent = said[-1][1]
    assert sent["title"] == "Headline here" and "line one" in sent["digest"]
    assert json.loads(prompts[0])["week"] == "2026-W43"   # the writer only sees computed numbers
    hold_sig = sent["hold_url"].split("sig=")[1]
    st, _, body = run(api.handle(app, "GET", "/hold/2026-W43", {"sig": hold_sig}))
    assert st == 200 and "<form" in body and run(issues.get(app, "2026-W43"))["status"] == "draft"  # GET never acts
    st, _, _ = run(api.handle(app, "POST", "/hold/2026-W43", {}, {"sig": "bad"}))
    assert st == 403
    run(api.handle(app, "POST", "/hold/2026-W43", {}, {"sig": hold_sig}))
    clock.t += 2 * DAY
    run(runner.tick(app, crawl=False))
    assert run(issues.get(app, "2026-W43"))["status"] == "held"    # a held draft is not auto-published
    st, _, _ = run(api.handle(app, "GET", "/api/issues/2026-W43", {}))
    assert st == 404
    pub_sig = sent["publish_url"].split("sig=")[1]
    run(api.handle(app, "POST", "/publish/2026-W43", {}, {"sig": pub_sig}))
    st, h, body = run(api.handle(app, "GET", "/api/issues/latest", {}))
    assert st == 200 and json.loads(body)["title"] == "Headline here" and h["Access-Control-Allow-Origin"] == "*"


def test_draft_publishes_itself_after_hold_window(world):
    app, board, clock, said, _ = world
    board["acme"] = [job(1)]
    run(collect.crawl(app, app.companies[0]))
    clock.t = MON_W44 + 3600
    run(runner.tick(app))
    clock.t += 25 * 3600
    rec = run(runner.tick(app, crawl=False))
    assert rec["published"] == ["2026-W43"] and said[-1][0] in ("published", "health")


def test_city_skips_non_places_and_small_ai_samples_stay_out_of_the_brief():
    assert trends.city("Hybrid; Paris, France") is None and trends.city("US, CA, Santa Clara") == "Santa Clara"
    b = trends.brief({"ai": {"tagged_open": 60, "ai_core_share": 1.7}, "emerging": [{"title": "x"}], "companies_all": []})
    assert "ai_core_share" not in b["ai"] and b["emerging"] == [] and "companies_all" not in b
