# CareerRadar

Watch the top-50 AI/future-tech companies' careers pages, keep tech roles, publish a weekly trends issue. Python on
RadarKit (`pip install -e .`); one code path runs locally (SQLite) and as a Cloudflare Python Worker (D1, Workers AI).

## Map

- `careerradar/app.py`: runtime context (store, cfg, companies, secrets, clock, AI binding, request budget, `say`).
- `collect.py` crawl + descriptions + skills; `boilerplate.py`; `classify.py` title rules; `skills.py` taxonomy;
  `enrich.py` Jev tags; `trends.py` weekly numbers; `write.py` AI prose; `issues.py` draft/hold/publish/deploy hook;
  `runner.py` one tick; `api.py` HTTP routes; `__main__.py` local CLI.
- `careerradar/data/`: companies, tech-role rules, taxonomy, Jev questions, default config. `prompts/`, `templates/`:
  all prose and message text. `migrations/`: D1/SQLite schema. Static text never goes in code.
- `worker/entry.py` + `wrangler.example.jsonc`; `scripts/bundle.py` assembles `worker/src/` (gitignored).
- `docs/research/top-companies.md`: why each default company is on the list, with sources.

## Rules

- Incremental conventional commits, stage only touched paths, push each. Never commit `config.json`, `companies.json`,
  `data/`, `worker/wrangler.jsonc`, secrets.
- `python3 -m pytest -q` green before every commit; a fixed bug gets a test.
- Numbers come from code only; the writer prompt forbids invented figures. A new metric goes in `trends.compute` first.
- D1 bills rows written: never touch every open posting per crawl; write only new, closed, reopened, enriched.
- Worker constraints: no threads, no subprocess, no files outside the bundle; every non-`.py` file the Worker reads
  must match the wrangler `rules` globs.
- Taxonomy or title-rule edits: run `reskill` (skills) or check `issue stats` before the next weekly build.
