"""The numbers of one weekly issue, computed from the postings table. Everything a post says is in here: the AI writes
prose around these figures and never makes one up.

A week is an ISO week (Monday to Sunday). A posting is open at the end of day D when first_seen <= D and it was not closed
by D. Week-over-week deltas only count companies whose baseline crawl was before the previous week ended, so a company
joining the watch list never shows up as a hiring spike.
"""
import collections, datetime as dt, json, re

from . import skills as sk


def week_of(day):
    y, w, _ = dt.date.fromisoformat(day).isocalendar()
    return f"{y}-W{w:02d}"


def bounds(week):
    y, w = week.split("-W")
    mon = dt.date.fromisocalendar(int(y), int(w), 1)
    return mon.isoformat(), (mon + dt.timedelta(days=6)).isoformat()


def last_full_week(today):
    return week_of((dt.date.fromisoformat(today) - dt.timedelta(days=7)).isoformat())


def shift(week, n):
    s, _ = bounds(week)
    return week_of((dt.date.fromisoformat(s) + dt.timedelta(weeks=n)).isoformat())


def is_open(p, day):
    return p["first_seen"] <= day and (not p["closed"] or p["closed"] > day)


def pct(a, b):
    return round(100 * a / b, 1) if b else 0.0


def city(loc):
    """First place of a location list. 'US, CA, Santa Clara' (country first) -> Santa Clara; 'Paris, France' -> Paris."""
    parts = [p.strip() for p in (loc or "").split(";")[0].split(",") if p.strip()]
    if not parts or re.match(r"^(\d+ locations?|hybrid|remote|multiple locations?|various|anywhere)$", parts[0], re.I):
        return None
    return parts[-1] if len(parts) > 1 and re.fullmatch(r"[A-Z]{2,3}", parts[0]) else parts[0]


async def load(store):
    rows = await store.all("SELECT id, company, title, family, url, loc, function, seniority, first_seen, closed, baseline, sampled, skills, jev FROM postings")
    for r in rows:
        r["skills"] = json.loads(r["skills"]) if r["skills"] else None
        r["jev"] = json.loads(r["jev"]) if r["jev"] else None
    cos = {c["slug"]: c for c in await store.all("SELECT slug, name, segment, baseline, last_ok, fail_streak FROM companies")}
    return rows, cos


def shares(rows, key):
    c = collections.Counter(r[key] for r in rows)
    n = len(rows)
    return {k: (v, pct(v, n)) for k, v in c.items()}


def skill_shares(rows):
    described = [r for r in rows if r["skills"] is not None]
    c = collections.Counter(s for r in described for s in r["skills"])
    return {k: pct(v, len(described)) for k, v in c.items()}, len(described)


def compute(rows, cos, week, cfg, history=12):
    start, end = bounds(week)
    prev_end = bounds(shift(week, -1))[1]
    month_end = bounds(shift(week, -4))[1]
    R = cfg["report"]
    live = {s for s, c in cos.items() if c["baseline"] and c["baseline"] <= end}
    comp = {s for s in live if cos[s]["baseline"] <= prev_end}
    comp4 = {s for s in live if cos[s]["baseline"] <= month_end}
    rows = [r for r in rows if r["company"] in live]
    open_now = [r for r in rows if is_open(r, end)]
    new = [r for r in rows if start <= r["first_seen"] <= end and not r["baseline"]]
    closed = [r for r in rows if r["closed"] and start <= r["closed"] <= end]
    open_c = [r for r in open_now if r["company"] in comp]
    open_prev = [r for r in rows if r["company"] in comp and is_open(r, prev_end)]
    baseline = not comp

    def by(key, label):
        now, prev = shares(open_c if not baseline else open_now, key), shares(open_prev, key)
        newc = collections.Counter(r[key] for r in new)
        out = [{label: k, "open": v[0], "share": v[1], "share_prev": prev.get(k, (0, 0.0))[1],
                "delta_pp": round(v[1] - prev.get(k, (0, 0.0))[1], 1) if not baseline else None, "new": newc.get(k, 0)}
               for k, v in now.items()]
        return sorted(out, key=lambda x: -x["open"])

    companies = []
    for s in live:
        o = sum(r["company"] == s for r in open_now)
        p = sum(r["company"] == s for r in open_prev) if s in comp else None
        companies.append({"slug": s, "name": cos[s]["name"], "segment": cos[s]["segment"], "open": o,
                          "new": sum(r["company"] == s for r in new), "closed": sum(r["company"] == s for r in closed),
                          "delta": o - p if p is not None else None, "delta_pct": pct(o - p, p) if p else None})
    companies.sort(key=lambda x: -x["open"])
    segments = collections.defaultdict(lambda: {"open": 0, "new": 0, "delta": 0})
    for c in companies:
        g = segments[c["segment"]]
        g["open"] += c["open"]
        g["new"] += c["new"]
        g["delta"] += c["delta"] or 0

    sh_now, n_now = skill_shares(open_c if not baseline else open_now)
    sh_prev, n_prev = skill_shares(open_prev)
    sh_month, n_month = skill_shares([r for r in rows if r["company"] in comp4 and is_open(r, month_end)])
    sh_new, n_new = skill_shares(new)
    groups = sk.groups()
    skill_rows = [{"skill": k, "group": groups.get(k), "share": v, "share_prev": sh_prev.get(k), "share_4w": sh_month.get(k),
                   "delta_pp": round(v - sh_prev.get(k, 0), 1) if n_prev else None,
                   "delta_4w_pp": round(v - sh_month.get(k, 0), 1) if n_month else None,
                   "share_new": sh_new.get(k)} for k, v in sh_now.items()]
    skill_rows.sort(key=lambda x: -x["share"])
    movers = [s for s in skill_rows if s["delta_pp"] is not None and s["share"] >= 2]
    risers = sorted(movers, key=lambda s: -s["delta_pp"])[:R["top_skills"]]
    fallers = sorted(movers, key=lambda s: s["delta_pp"])[:R["top_skills"]]
    fresh = sorted([s for s in skill_rows if s["share_new"] is not None and n_new >= 20],
                   key=lambda s: -((s["share_new"] or 0) - s["share"]))[:R["top_skills"]]

    known_before = {r["family"] for r in rows if r["family"] and r["first_seen"] < start}
    fam_new = collections.defaultdict(lambda: {"postings": 0, "companies": set(), "example": None})
    for r in new:
        f = r["family"]
        if f and f not in known_before:
            g = fam_new[f]
            g["postings"] += 1
            g["companies"].add(cos[r["company"]]["name"])
            g["example"] = g["example"] or {"title": r["title"], "url": r["url"], "company": cos[r["company"]]["name"]}
    families_new = sorted(({"family": f, "postings": g["postings"], "companies": sorted(g["companies"]), "example": g["example"]}
                           for f, g in fam_new.items() if g["postings"] >= R["min_family_postings"] or len(g["companies"]) > 1),
                          key=lambda x: (-len(x["companies"]), -x["postings"]))[:R["top_families"]]
    fam_hot = collections.Counter(r["family"] for r in new if r["family"])

    tagged_open = [r for r in open_now if r["jev"]]
    tagged_new = [r for r in new if r["jev"]]
    ai = {"tagged_open": len(tagged_open), "tagged_new": len(tagged_new),
          "ai_core_share": pct(sum(r["jev"]["ai"] >= 0.5 for r in tagged_open), len(tagged_open)),
          "ai_core_share_new": pct(sum(r["jev"]["ai"] >= 0.5 for r in tagged_new), len(tagged_new)),
          "emerging_share_new": pct(sum(r["jev"]["emerging"] >= 0.5 for r in tagged_new), len(tagged_new)),
          "focus": sorted(({"focus": k, "share": pct(v, len(tagged_open))} for k, v in collections.Counter(r["jev"]["focus"] for r in tagged_open).items() if k),
                          key=lambda x: -x["share"]),
          "by_segment": sorted(({"segment": seg, "ai_core_share": pct(sum(r["jev"]["ai"] >= 0.5 for r in rs), len(rs)), "tagged": len(rs)}
                                for seg, rs in group_by(tagged_open, lambda r: cos[r["company"]]["segment"]).items()), key=lambda x: -x["ai_core_share"])}
    emerging = sorted((r for r in tagged_new if r["jev"]["emerging"] >= 0.7), key=lambda r: -r["jev"]["emerging"])[:8]

    series = []
    for i in range(history - 1, -1, -1):
        w = shift(week, -i)
        we = bounds(w)[1]
        base = {s for s in live if cos[s]["baseline"] <= we}
        if base:
            series.append({"week": w, "open": sum(r["company"] in base and is_open(r, we) for r in rows), "companies": len(base),
                           "new": sum(bounds(w)[0] <= r["first_seen"] <= we and not r["baseline"] for r in rows)})
    return {
        "week": week, "start": start, "end": end, "baseline": baseline,
        "companies_live": len(live), "companies_compared": len(comp),
        "totals": {"open": len(open_now), "new": len(new), "closed": len(closed),
                   "open_compared": len(open_c), "open_prev": len(open_prev) if not baseline else None,
                   "delta": len(open_c) - len(open_prev) if not baseline else None,
                   "delta_pct": pct(len(open_c) - len(open_prev), len(open_prev)) if not baseline and open_prev else None,
                   "described": n_now},
        "companies": companies[:R["top_companies"]], "companies_all": companies,
        "movers": {"up": sorted([c for c in companies if c["delta"]], key=lambda c: -c["delta"])[:5],
                   "down": sorted([c for c in companies if c["delta"]], key=lambda c: c["delta"])[:5]},
        "segments": sorted(({"segment": k, **v} for k, v in segments.items()), key=lambda x: -x["open"]),
        "functions": by("function", "function"), "seniority": by("seniority", "seniority"),
        "skills": {"top": skill_rows[:R["top_skills"] * 2], "risers": risers, "fallers": fallers, "fresh": fresh},
        "families": {"new": families_new, "hot": [{"family": f, "new": n} for f, n in fam_hot.most_common(R["top_families"])]},
        "ai": ai, "emerging": [{"title": r["title"], "company": cos[r["company"]]["name"], "url": r["url"], "score": r["jev"]["emerging"]} for r in emerging],
        "cities": [{"city": c, "open": n} for c, n in collections.Counter(city(r["loc"]) for r in open_now if city(r["loc"])).most_common(10)],
        "series": series,
        "health": {"failing": [cos[s]["name"] for s in cos if (cos[s]["fail_streak"] or 0) >= 2]},
    }


def group_by(rows, key):
    out = collections.defaultdict(list)
    for r in rows:
        out[key(r)].append(r)
    return out


MIN_TAGGED = 200  # Jev-tagged roles needed before AI shares are figures, not anecdotes


def brief(stats):
    """The part of the numbers the writer sees: everything except the full company table, and no AI shares from a
    sample too small to mean anything."""
    out = {k: v for k, v in stats.items() if k not in ("companies_all",)}
    if (stats.get("ai") or {}).get("tagged_open", 0) < MIN_TAGGED:
        out["ai"] = {"note": f"only {stats['ai']['tagged_open']} roles tagged so far: no AI-centrality figures this week"}
        out["emerging"] = []
    return out
