-- Companies being watched and their crawl health
CREATE TABLE IF NOT EXISTS companies (
  slug TEXT PRIMARY KEY, name TEXT, segment TEXT, boards TEXT,
  baseline TEXT, last_crawl TEXT, last_ok TEXT, last_count INTEGER DEFAULT 0, fail_streak INTEGER DEFAULT 0, last_error TEXT
);
-- One row per tech posting ever seen: open while closed IS NULL
CREATE TABLE IF NOT EXISTS postings (
  id TEXT PRIMARY KEY, company TEXT NOT NULL, title TEXT, family TEXT, url TEXT, loc TEXT, team TEXT,
  function TEXT, seniority TEXT, posted TEXT, first_seen TEXT NOT NULL, closed TEXT,
  baseline INTEGER DEFAULT 0, sampled INTEGER DEFAULT 1, desc TEXT, skills TEXT, jev TEXT, enriched TEXT
);
CREATE INDEX IF NOT EXISTS postings_company ON postings (company, closed);
CREATE INDEX IF NOT EXISTS postings_seen ON postings (first_seen);
CREATE INDEX IF NOT EXISTS postings_todo ON postings (enriched, sampled);
-- Weekly issues: draft -> published (or held)
CREATE TABLE IF NOT EXISTS issues (
  week TEXT PRIMARY KEY, status TEXT, built TEXT, hold_until TEXT, published TEXT,
  title TEXT, dek TEXT, post TEXT, digest TEXT, data TEXT
);
-- Small key/value state (last health alert, Jev calls per day, ...)
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
