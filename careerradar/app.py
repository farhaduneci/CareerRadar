"""The runtime context every step gets: store, settings, watch list, secrets, clock, AI binding, request budget.
The CLI builds one from local files; the Worker builds one from its bindings. Nothing below this knows which."""
import time

from radarkit import http, notify, runlog, template

from . import files


class App:
    def __init__(self, store, cfg, companies, env=None, ai_binding=None, clock=time.time):
        self.store, self.cfg, self.companies = store, cfg, companies
        self.env = env or {}
        self.ai_binding, self.clock = ai_binding, clock
        self.log = runlog.StoreLog(store)
        self.reset_budget()

    def reset_budget(self):
        self._start = http.REQUESTS

    @property
    def requests(self):
        return http.REQUESTS - self._start

    def now(self):
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(self.clock()))

    def today(self):
        return self.now()[:10]

    def budget_left(self):
        return self.cfg["crawl"]["max_requests"] - self.requests

    async def setup(self):
        await self.store.migrate_sql(files.migrations())

    async def kv(self, k, default=None):
        r = await self.store.one("SELECT v FROM kv WHERE k = ?", (k,))
        return r["v"] if r else default

    async def set_kv(self, k, v):
        await self.store.run("INSERT INTO kv (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v", (k, str(v)))

    async def say(self, event, **vars):
        """One message from templates/<event>.txt on the configured channel. False (logged) when it could not go out."""
        try:
            await notify.deliver(self.cfg["notify"], template.render(files.TEMPLATES, event, **vars), event, env=self.env)
            return True
        except Exception as e:
            print(f"notify {event} failed: {e}")
            return False
