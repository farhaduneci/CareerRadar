"""Weekly issues: build (numbers + AI prose) as a draft, announce it with signed hold / publish links, publish when the
hold window passes, then ping the site's deploy hook so it rebuilds with the new post."""
import datetime as dt, hashlib, hmac, json, time

from radarkit import http

from . import trends, write


def sign(app, action, week):
    secret = app.env.get("LINK_SECRET") or ""
    return hmac.new(secret.encode(), f"{action}:{week}".encode(), hashlib.sha256).hexdigest()[:32]


def verify(app, action, week, sig):
    return bool(app.env.get("LINK_SECRET")) and hmac.compare_digest(sign(app, action, week), sig or "")


def links(app, week):
    base = app.cfg["api"]["public_url"].rstrip("/")
    return {"preview_url": f"{base}/preview/{week}?sig={sign(app, 'preview', week)}",
            "hold_url": f"{base}/hold/{week}?sig={sign(app, 'hold', week)}",
            "publish_url": f"{base}/publish/{week}?sig={sign(app, 'publish', week)}",
            "post_url": app.cfg["publish"]["post_url"].replace("{week}", week)}


async def get(app, week):
    r = await app.store.one("SELECT * FROM issues WHERE week = ?", (week,))
    if r:
        r["data"] = json.loads(r["data"] or "{}")
    return r


def public(issue):
    """What the site sees: published issues only, no internal fields."""
    return {"week": issue["week"], "published": issue["published"], "title": issue["title"], "dek": issue["dek"],
            "post": issue["post"], "data": issue["data"]}


async def build(app, week=None, announce=True):
    """Compute and write an issue for `week` (default: the last full week). Rebuilding a draft replaces it; a published
    issue is never rewritten. -> the issue row."""
    week = week or trends.last_full_week(app.today())
    old = await get(app, week)
    if old and old["status"] == "published":
        return old
    rows, cos = await trends.load(app.store)
    stats = trends.compute(rows, cos, week, app.cfg)
    title, dek, body = await write.post(app, stats)
    digest = await write.digest(app, title, body)
    hold_until = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(app.clock() + app.cfg["publish"]["hold_hours"] * 3600))
    await app.store.run("INSERT INTO issues (week, status, built, hold_until, title, dek, post, digest, data) VALUES (?, 'draft', ?, ?, ?, ?, ?, ?, ?) "
                        "ON CONFLICT(week) DO UPDATE SET status = 'draft', built = excluded.built, hold_until = excluded.hold_until, "
                        "title = excluded.title, dek = excluded.dek, post = excluded.post, digest = excluded.digest, data = excluded.data",
                        (week, app.now(), hold_until, title, dek, body, digest, json.dumps(stats, ensure_ascii=False)))
    if announce:
        await app.say("draft", site_name=app.cfg["publish"]["site_name"], week=week, title=title, digest=digest,
                      hold_until=hold_until.replace("T", " ")[:16], **links(app, week))
    return await get(app, week)


async def deploy_hook(app):
    url = app.env.get("SITE_DEPLOY_HOOK")
    if url:
        await http.request("POST", url, "{}", {"Content-Type": "application/json"})
        return True
    return False


async def publish(app, week, announce=True):
    i = await get(app, week)
    if not i or i["status"] == "published":
        return i
    await app.store.run("UPDATE issues SET status = 'published', published = ? WHERE week = ?", (app.now(), week))
    try:
        await deploy_hook(app)
    except Exception as e:
        print(f"deploy hook failed: {e}")
    if announce:
        await app.say("published", site_name=app.cfg["publish"]["site_name"], week=week, title=i["title"], **links(app, week))
    return await get(app, week)


async def hold(app, week):
    await app.store.run("UPDATE issues SET status = 'held' WHERE week = ? AND status = 'draft'", (week,))
    await app.say("held", site_name=app.cfg["publish"]["site_name"], week=week, **links(app, week))
    return await get(app, week)


async def publish_due(app):
    """Publish every draft whose hold window has passed. -> weeks published."""
    rows = await app.store.all("SELECT week FROM issues WHERE status = 'draft' AND hold_until <= ?", (app.now(),))
    for r in rows:
        await publish(app, r["week"])
    return [r["week"] for r in rows]


def build_due(app, last_built_week):
    """Is it time to build last week's issue? On or after the configured weekday (0 = Monday) and not built yet."""
    today = dt.date.fromisoformat(app.today())
    week = trends.last_full_week(app.today())
    return week if today.weekday() >= app.cfg["publish"]["issue_weekday"] and last_built_week != week else None


async def listing(app):
    rows = await app.store.all("SELECT week, published, title, dek FROM issues WHERE status = 'published' ORDER BY week DESC")
    return rows
