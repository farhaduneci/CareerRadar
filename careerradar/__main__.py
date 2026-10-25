"""python3 -m careerradar <command>: the local runtime. Same steps as the Worker, with SQLite instead of D1 and the
Workers AI REST API instead of the binding. CAREERRADAR_HOME (default: the repo root) holds config.json, companies.json, data/."""
import argparse, asyncio, json, os, sys, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from radarkit import store

from . import api, collect, config, enrich, issues, runner, trends
from .app import App

HOME = os.path.abspath(os.environ.get("CAREERRADAR_HOME") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def local_app():
    cfg_path, cos_path = os.path.join(HOME, "config.json"), os.path.join(HOME, "companies.json")
    cfg = config.load(cfg_path if os.path.exists(cfg_path) else None)
    cos = config.companies(cos_path if os.path.exists(cos_path) else None)
    return App(store.SqliteStore(os.path.join(HOME, "data", "careerradar.sqlite")), cfg, cos, env=dict(os.environ))


async def cmd(args):
    app = local_app()
    await app.setup()
    if args.cmd == "tick":
        for _ in range(args.n):
            app.reset_budget()
            print(json.dumps(await runner.tick(app, crawl=True), default=str)[:600])
    elif args.cmd == "crawl":
        cos = [c for c in app.companies if not args.company or c["slug"] == args.company]
        if not cos:
            sys.exit(f"no enabled company {args.company!r}")
        for c in cos:
            app.reset_budget()
            r = await collect.crawl(app, c)
            await app.log.append("crawl", r["ok"], **{k: v for k, v in r.items() if k != "ok"})
            print(f"{c['slug']}: {r['mode']} {'ok' if r['ok'] else 'SUSPECT'} fetched {r['fetched']} tech {r['tech']} new {r['new']} "
                  f"closed {r['closed']} described {r['enriched']} pending {r['pending']} ({r['ms']} ms, {app.requests} requests)"
                  + "".join(f"\n  error: {e}" for e in r["errors"]))
    elif args.cmd == "tag":
        print(await enrich.tag(app))
    elif args.cmd == "reskill":
        print(f"{await collect.reskill(app, args.company)} postings re-matched")
    elif args.cmd == "issue":
        week = args.week or trends.last_full_week(app.today())
        if args.action == "build":
            i = await issues.build(app, week, announce=not args.quiet)
        elif args.action == "stats":
            rows, cos = await trends.load(app.store)
            print(json.dumps(trends.brief(trends.compute(rows, cos, week, app.cfg)), indent=1, ensure_ascii=False))
            return
        elif args.action == "publish":
            i = await issues.publish(app, week, announce=not args.quiet)
        elif args.action == "hold":
            i = await issues.hold(app, week)
        else:
            i = await issues.get(app, week)
        if not i:
            sys.exit(f"no issue {week}")
        print(f"{i['week']} [{i['status']}] {i['title']}\n> {i['dek']}\n\n{i['post']}\n\n--- digest ---\n{i['digest']}")
    elif args.cmd == "export":
        os.makedirs(args.dir, exist_ok=True)
        rows = await issues.listing(app)
        json.dump({"issues": rows}, open(os.path.join(args.dir, "index.json"), "w"), indent=1, ensure_ascii=False)
        for r in rows:
            json.dump(issues.public(await issues.get(app, r["week"])), open(os.path.join(args.dir, f"{r['week']}.json"), "w"), indent=1, ensure_ascii=False)
        print(f"{len(rows)} published issues -> {args.dir}")
    elif args.cmd == "status":
        for c in await app.store.all("SELECT c.slug, c.baseline, c.last_crawl, c.fail_streak, c.last_error, "
                                     "(SELECT COUNT(*) FROM postings p WHERE p.company = c.slug AND p.closed IS NULL) AS open, "
                                     "(SELECT COUNT(*) FROM postings p WHERE p.company = c.slug AND p.closed IS NULL AND p.enriched IS NULL AND p.sampled = 1) AS pending "
                                     "FROM companies c ORDER BY c.slug"):
            print(f"{c['slug']:<24} open {c['open']:>5}  pending {c['pending']:>4}  baseline {c['baseline'] or '-':<10}  last {c['last_crawl'] or '-'}"
                  + (f"  FAIL x{c['fail_streak']}: {(c['last_error'] or '')[:80]}" if c["fail_streak"] else ""))
    elif args.cmd == "health":
        flags = await runner.health(app)
        print("\n".join(flags) or "healthy")


def serve(port):
    app = local_app()

    class H(BaseHTTPRequestHandler):
        def go(self, method):
            u = urllib.parse.urlparse(self.path)
            q = dict(urllib.parse.parse_qsl(u.query))
            form = None
            if method == "POST":
                form = dict(urllib.parse.parse_qsl(self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()))
            status, headers, body = asyncio.run(api.handle(app, method, u.path, q, form))
            self.send_response(status)
            for k, v in headers.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body.encode())

        def do_GET(self):
            self.go("GET")

        def do_POST(self):
            self.go("POST")
    print(f"careerradar api on http://localhost:{port}")
    HTTPServer(("127.0.0.1", port), H).serve_forever()  # one thread: the SQLite connection is not shared across threads


def main():
    ap = argparse.ArgumentParser(prog="careerradar", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tick", help="what one cron firing does: publish due drafts, build the weekly issue when due, crawl the next company, tag with Jev")
    t.add_argument("-n", type=int, default=1, help="ticks in a row")
    c = sub.add_parser("crawl", help="crawl companies now, due or not")
    c.add_argument("--company")
    sub.add_parser("tag", help="Jev-tag described postings (capped)")
    rs = sub.add_parser("reskill", help="re-match skills on stored descriptions (after editing data/taxonomy.json)")
    rs.add_argument("--company")
    i = sub.add_parser("issue", help="weekly issue: build | stats | show | publish | hold")
    i.add_argument("action", choices=["build", "stats", "show", "publish", "hold"])
    i.add_argument("--week", help="YYYY-Www, default the last full week")
    i.add_argument("--quiet", action="store_true", help="no Telegram message")
    e = sub.add_parser("export", help="write published issues as JSON files (for a local site build)")
    e.add_argument("dir")
    sub.add_parser("status", help="companies: open roles, pending descriptions, crawl health")
    sub.add_parser("health", help="what looks broken (and alert, once a day)")
    s = sub.add_parser("serve", help="the read API and signed links on localhost")
    s.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()
    if args.cmd == "serve":
        return serve(args.port)
    asyncio.run(cmd(args))


if __name__ == "__main__":
    main()
