"""Jev tags each described posting once: how central AI is, whether the role type is new, and its main focus.
Questions live in data/jev_questions.json. Capped per tick and per day (`jev.per_tick`, `jev.daily_cap`)."""
import json

from radarkit import http, jev

from . import files


def answer(a):
    """Jev's raw answers -> the compact tags stored with a posting."""
    f = a.get("focus") or {}
    return {"ai": round(a["ai_centrality"]["noul"], 3), "emerging": round(a["emerging"]["noul"], 3),
            "focus": f.get("choice"), "focus_p": round((f.get("probabilities") or {}).get(f.get("choice"), 0), 3)}


async def tag(app):
    """Tag pending postings. -> {"tagged", "errors", "skipped"}."""
    cfg = app.cfg["jev"]
    out = {"tagged": 0, "errors": 0, "skipped": None}
    key = app.env.get("TYPESAFE_API_KEY")
    if not cfg["enabled"] or not key:
        out["skipped"] = "off" if not cfg["enabled"] else "no TYPESAFE_API_KEY"
        return out
    day_key = f"jev:{app.today()}"
    used = int(await app.kv(day_key, 0))
    n = min(cfg["per_tick"], cfg["daily_cap"] - used, max(0, app.budget_left() - 5))
    if n <= 0:
        out["skipped"] = "cap"
        return out
    rows = await app.store.all("SELECT p.id, p.title, p.loc, p.desc, c.name AS company FROM postings p JOIN companies c ON c.slug = p.company "
                               "WHERE p.jev IS NULL AND p.desc IS NOT NULL AND p.desc != '' AND p.closed IS NULL ORDER BY p.first_seen DESC LIMIT ?", (n,))
    questions = files.data("jev_questions.json")

    async def one(r):
        state = {"job": {"title": r["title"], "company": r["company"], "location": r["loc"], "description": r["desc"][:9000]}}
        return r["id"], answer(await jev.ask(state, questions, key=key, model=cfg["model"]))
    results = await http.gather([one(r) for r in rows], limit=6)
    stmts = []
    for res in results:
        if isinstance(res, Exception):
            out["errors"] += 1
            continue
        stmts.append(("UPDATE postings SET jev = ? WHERE id = ?", (json.dumps(res[1]), res[0])))
    for i in range(0, len(stmts), 50):
        await app.store.batch(stmts[i:i + 50])
    out["tagged"] = len(stmts)
    await app.set_kv(day_key, used + len(rows))
    return out
