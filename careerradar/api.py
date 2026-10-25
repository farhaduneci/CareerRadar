"""HTTP routes, the same for the Worker and `careerradar serve`: the public read API the site builds from, and the signed
hold / publish / preview links sent with each draft. A link opens a confirm page; only its POST changes anything, so a
chat app prefetching links can never hold or publish an issue."""
import html, json, re

from radarkit import template

from . import files, issues

CORS = {"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=300"}


def js(obj, status=200):
    return status, {"Content-Type": "application/json; charset=utf-8", **CORS}, json.dumps(obj, ensure_ascii=False)


def page(title, body, status=200):
    doc = template.render(files.TEMPLATES, "page.html", title=html.escape(title), body=body)
    return status, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, doc


async def handle(app, method, path, query, form=None):
    """-> (status, headers, body)."""
    await app.setup()
    path = path.rstrip("/") or "/"
    if path == "/api/issues":
        return js({"issues": await issues.listing(app)})
    m = re.fullmatch(r"/api/issues/(latest|\d{4}-W\d{2})", path)
    if m:
        week = m.group(1)
        if week == "latest":
            rows = await issues.listing(app)
            week = rows[0]["week"] if rows else None
        i = week and await issues.get(app, week)
        return js(issues.public(i)) if i and i["status"] == "published" else js({"error": "not found"}, 404)
    if path == "/api/health":
        last = (await app.log.recent("tick", 1) or [{}])[-1]
        down = await app.store.all("SELECT slug, last_error FROM companies WHERE fail_streak >= 2")
        n = await app.store.one("SELECT COUNT(*) AS open FROM postings WHERE closed IS NULL")
        return js({"last_tick": last.get("ts"), "last_ok": last.get("ok"), "open_postings": n["open"], "failing": down})
    m = re.fullmatch(r"/(preview|hold|publish)/(\d{4}-W\d{2})", path)
    if m:
        action, week = m.groups()
        sig = (form or {}).get("sig") or query.get("sig")
        if not issues.verify(app, action, week, sig):
            return page("Not allowed", "<p>This link is not valid.</p>", 403)
        i = await issues.get(app, week)
        if not i:
            return page("Not found", f"<p>No issue for {week}.</p>", 404)
        if action == "preview":
            return 200, {"Content-Type": "text/markdown; charset=utf-8", "Cache-Control": "no-store"}, f"# {i['title']}\n\n> {i['dek']}\n\n{i['post']}"
        if method != "POST":
            body = (f"<p>{week}: <b>{html.escape(i['title'] or '')}</b> is <i>{i['status']}</i>.</p>"
                    f"<form method=post><input type=hidden name=sig value='{html.escape(sig)}'><button>{action.capitalize()} {week}</button></form>")
            return page(f"{action.capitalize()} {week}", body)
        i = await (issues.hold(app, week) if action == "hold" else issues.publish(app, week))
        return page(f"{week} {i['status']}", f"<p>{week} is now <b>{i['status']}</b>.</p>")
    if path == "/":
        return js({"name": "careerradar", "api": ["/api/issues", "/api/issues/latest", "/api/issues/<week>", "/api/health"]})
    return js({"error": "not found"}, 404)
