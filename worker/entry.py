"""CareerRadar as a Cloudflare Python Worker: cron ticks crawl and publish, fetch serves the read API and signed links.
`scripts/bundle.py` copies careerradar/ and radarkit/ next to this file (worker/src/) before `pywrangler dev|deploy`."""
import json, urllib.parse

from workers import Response, WorkerEntrypoint

from careerradar import api, config, runner
from careerradar.app import App
from radarkit import store

SECRETS = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TYPESAFE_API_KEY", "LINK_SECRET", "SITE_DEPLOY_HOOK",
           "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN")  # the last two: optional Workers AI REST fallback


def app_of(env):
    vals = {k: getattr(env, k, None) for k in SECRETS + ("CONFIG", "COMPANIES")}
    cfg = config.load(vals["CONFIG"] or None)
    cos = config.companies(json.loads(vals["COMPANIES"]) if vals["COMPANIES"] else None)
    secrets = {k: str(v) for k, v in vals.items() if k in SECRETS and v}
    return App(store.D1Store(env.DB), cfg, cos, env=secrets, ai_binding=getattr(env, "AI", None))


class Default(WorkerEntrypoint):
    async def scheduled(self, controller, env, ctx):
        await runner.tick(app_of(self.env))

    async def fetch(self, request):
        u = urllib.parse.urlparse(str(request.url))
        form = None
        if request.method == "POST":
            form = dict(urllib.parse.parse_qsl(await request.text()))
        status, headers, body = await api.handle(app_of(self.env), request.method, u.path, dict(urllib.parse.parse_qsl(u.query)), form)
        return Response(body, status=status, headers=headers)
