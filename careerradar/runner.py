"""One tick: the unit of work a cron fires (every 10 minutes on Cloudflare, or a local schedule).

Order: publish drafts whose hold passed -> build last week's issue when due (and do nothing else that tick) -> crawl the
next due company -> Jev-tag what the crawl described, with whatever request budget is left -> daily health check.
"""
import time

from radarkit import runlog

from . import collect, enrich, issues, trends


async def tick(app, crawl=True):
    await app.setup()
    t0 = time.time()
    rec = {"published": await issues.publish_due(app)}
    last = await app.store.one("SELECT week FROM issues ORDER BY week DESC LIMIT 1")
    week = issues.build_due(app, last and last["week"])
    if week and await app.store.one("SELECT 1 AS x FROM companies WHERE baseline IS NOT NULL AND baseline <= ?", (trends.bounds(week)[1],)):
        try:
            i = await issues.build(app, week)
            rec["built"] = i["week"]
        except Exception as e:
            rec["build_error"] = f"{type(e).__name__}: {str(e)[:200]}"
            await app.say("build_failed", week=week, error=rec["build_error"])
    elif crawl:
        c = await collect.due(app)
        if c:
            rec["crawl"] = await collect.crawl(app, c)
        rec["jev"] = await enrich.tag(app)
    rec["requests"], rec["ms"] = app.requests, int((time.time() - t0) * 1000)
    ok = not rec.get("build_error") and (rec.get("crawl") or {}).get("ok", True)
    await app.log.append("tick", ok, **rec)
    await health(app)
    return rec


async def health(app):
    """At most once a day: tell the user what looks broken (silent ticks, failing tick streaks, boards down)."""
    if await app.kv("health_alerted") == app.today():
        return []
    h = app.cfg["health"]
    flags = await runlog.health(app.log, {"tick": h["tick_hours"]})
    down = await app.store.all("SELECT name, last_error FROM companies WHERE fail_streak >= ?", (h["board_fail_streak"],))
    flags += [f"{d['name']}: {(d['last_error'] or 'failing')[:120]}" for d in down]
    if flags:
        await app.say("health", flags="\n".join("- " + f for f in flags))
        await app.set_kv("health_alerted", app.today())
    return flags
