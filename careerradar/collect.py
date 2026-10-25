"""Crawl: read a company's boards, keep the tech roles, record new and closed postings, fetch descriptions for new ones.

Writes are kept small (D1 bills rows written): only new, closed, reopened and enriched postings are written, never a
"still open" touch per row. A crawl that fails, comes back empty or shrinks past `crawl.shrink` closes nothing.
"""
import json, time

from radarkit import boards

from . import boilerplate, classify, skills


async def company_row(app, c):
    r = await app.store.one("SELECT * FROM companies WHERE slug = ?", (c["slug"],))
    if not r:
        await app.store.run("INSERT INTO companies (slug, name, segment, boards) VALUES (?, ?, ?, ?)",
                            (c["slug"], c["name"], c.get("segment"), json.dumps(c["boards"])))
        r = await app.store.one("SELECT * FROM companies WHERE slug = ?", (c["slug"],))
    return r


async def due(app):
    """The enabled company crawled longest ago, if it is due (`crawl.min_hours`), else None."""
    rows = {r["slug"]: r for r in await app.store.all("SELECT slug, last_crawl FROM companies")}
    cut = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(app.clock() - app.cfg["crawl"]["min_hours"] * 3600))
    todo = sorted(app.companies, key=lambda c: (rows.get(c["slug"]) or {}).get("last_crawl") or "")
    return next((c for c in todo if ((rows.get(c["slug"]) or {}).get("last_crawl") or "") < cut), None)


def describe(row):
    return {"title": classify.clean(row["title"]), "url": row.get("url"), "loc": row.get("loc") or "", "team": row.get("team"),
            "posted": (row.get("date") or "")[:10] or None}


async def enrich_rows(app, company, rows, limit):
    """Resolve descriptions for up to `limit` rows (as budget allows) and match skills on the text minus the company's
    boilerplate. A detail page's location and date replace the list's summary ("2 Locations"). -> rows done."""
    take = list(rows)[:max(0, min(limit, app.budget_left() - 5))]
    if not take:
        return 0
    await boards.resolve_all(take, limit=6)
    known = await boilerplate.load(app, company)
    boiler = boilerplate.learn([r.get("desc") for r in take], known)
    if boiler != known:
        await boilerplate.save(app, company, boiler)
    stmts = []
    for r in take:
        desc = (r.get("desc") or "")[:12000]
        found = skills.find(r["title"], boilerplate.strip(desc, boiler))
        stmts.append(("UPDATE postings SET desc = ?, skills = ?, team = COALESCE(team, ?), loc = COALESCE(NULLIF(?, ''), loc), "
                      "posted = COALESCE(posted, ?), enriched = ? WHERE id = ?",
                      (desc, json.dumps(found), r.get("team"), r.get("loc") or "", (r.get("date") or "")[:10] or None, app.today(), r["id"])))
    for i in range(0, len(stmts), 50):
        await app.store.batch(stmts[i:i + 50])
    return len(take)


async def crawl(app, c):
    """One company. -> run record."""
    t0 = time.time()
    rec = {"company": c["slug"], "fetched": 0, "tech": 0, "new": 0, "closed": 0, "reopened": 0, "enriched": 0, "errors": []}
    co = await company_row(app, c)
    baseline = co["baseline"] is None
    rows = {}
    for b in c["boards"]:
        ats, tok = b.split(":", 1)
        try:
            for r in await boards.fetch(ats, tok, eager=False):
                rows[r["id"]] = r
        except Exception as e:
            rec["errors"].append(f"{b}: {type(e).__name__}: {str(e)[:160]}")
    rec["fetched"] = len(rows)
    tech = {}
    for pid, r in rows.items():
        fn = classify.function(r["title"])
        if fn:
            r["_fn"] = fn
            tech[pid] = r
    rec["tech"] = len(tech)
    known = {p["id"]: p for p in await app.store.all("SELECT id, closed, enriched, sampled FROM postings WHERE company = ?", (c["slug"],))}
    suspect = bool(rec["errors"]) or not tech or (co["last_count"] and len(tech) < app.cfg["crawl"]["shrink"] * co["last_count"])
    today, stmts = app.today(), []
    new = [r for pid, r in tech.items() if pid not in known]
    # A baseline describes only a sample (newest first): shares need a sample, not every posting.
    sample = {r["id"] for r in sorted(new, key=lambda r: r.get("date") or "", reverse=True)[:app.cfg["crawl"]["baseline_sample"]]} if baseline else None
    for r in new:
        d = describe(r)
        stmts.append(("INSERT INTO postings (id, company, title, family, url, loc, team, function, seniority, posted, first_seen, baseline, sampled) "
                      "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (r["id"], c["slug"], d["title"], classify.family(d["title"]), d["url"], d["loc"], d["team"], r["_fn"],
                       classify.seniority(d["title"]), d["posted"], today, int(baseline), int(sample is None or r["id"] in sample))))
    rec["new"] = 0 if baseline else len(new)
    for pid, p in known.items():
        if pid in tech and p["closed"]:
            stmts.append(("UPDATE postings SET closed = NULL WHERE id = ?", (pid,)))
            rec["reopened"] += 1
        elif pid not in tech and not p["closed"] and not suspect:
            stmts.append(("UPDATE postings SET closed = ? WHERE id = ?", (today, pid)))
            rec["closed"] += 1
    for i in range(0, len(stmts), 50):
        await app.store.batch(stmts[i:i + 50])
    # Descriptions: new postings first, then open ones a past tick ran out of budget for.
    todo = [r for r in new if sample is None or r["id"] in sample]
    todo += [tech[pid] for pid, p in known.items() if pid in tech and not p["enriched"] and p["sampled"]]
    rec["enriched"] = await enrich_rows(app, c["slug"], todo, app.cfg["crawl"]["details_per_tick"])
    rec["pending"] = len(todo) - rec["enriched"]
    ok = not suspect
    await app.store.run("UPDATE companies SET last_crawl = ?, baseline = COALESCE(baseline, ?), last_ok = CASE WHEN ? THEN ? ELSE last_ok END, "
                        "last_count = CASE WHEN ? THEN ? ELSE last_count END, fail_streak = CASE WHEN ? THEN 0 ELSE fail_streak + 1 END, last_error = ? "
                        "WHERE slug = ?",
                        (app.now(), today if ok else None, int(ok), app.now(), int(ok), len(tech), int(ok),
                         "; ".join(rec["errors"]) or (None if ok else f"suspect: {len(tech)} tech roles vs {co['last_count']} last crawl"), c["slug"]))
    rec["ok"], rec["mode"], rec["ms"] = ok, "baseline" if baseline else "crawl", int((time.time() - t0) * 1000)
    if not ok and co["fail_streak"] + 1 == 2:  # alert once, on the second failing crawl in a row
        await app.say("broken", company=c["name"], error=(rec["errors"] or ["shrank"])[0][:200])
    return rec


async def reskill(app, company=None):
    """Re-match skills on every stored description (after a taxonomy edit), relearning each company's boilerplate from
    all its descriptions. -> postings updated."""
    slugs = [company] if company else [r["slug"] for r in await app.store.all("SELECT slug FROM companies")]
    n = 0
    for slug in slugs:
        rows = await app.store.all("SELECT id, title, desc FROM postings WHERE company = ? AND desc IS NOT NULL", (slug,))
        boiler = boilerplate.learn([r["desc"] for r in rows], await boilerplate.load(app, slug))
        await boilerplate.save(app, slug, boiler)
        stmts = [("UPDATE postings SET skills = ? WHERE id = ?", (json.dumps(skills.find(r["title"], boilerplate.strip(r["desc"], boiler))), r["id"]))
                 for r in rows]
        for i in range(0, len(stmts), 50):
            await app.store.batch(stmts[i:i + 50])
        n += len(stmts)
    return n
