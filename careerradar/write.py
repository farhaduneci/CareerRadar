"""Prose from numbers: the weekly post and its Telegram digest, written by Workers AI from prompts/*.md."""
import json, re

from radarkit import ai, template

from . import files, trends


async def complete(app, system, user):
    c = app.cfg["ai"]
    return await ai.complete(system, user, model=c["model"], binding=app.ai_binding, max_tokens=c["max_tokens"], extra=c.get("extra"),
                             account=app.env.get("CLOUDFLARE_ACCOUNT_ID"), token=app.env.get("CLOUDFLARE_API_TOKEN"))


def parse(md):
    """'# Title' / '> dek' / body -> (title, dek, body). Tolerates a missing dek and stray code fences."""
    md = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", md.strip())
    m = re.match(r"#\s+(.+?)\n+(?:>\s*(.+?)\n+)?(.*)", md, re.S)
    if not m:
        return md.split("\n", 1)[0][:90], "", md
    return m.group(1).strip(), (m.group(2) or "").strip(), m.group(3).strip()


async def post(app, stats):
    system = template.fill(files.prompt("post"), site_name=app.cfg["publish"]["site_name"])
    return parse(await complete(app, system, json.dumps(trends.brief(stats), ensure_ascii=False)))


async def digest(app, title, body):
    text = await complete(app, files.prompt("digest"), f"# {title}\n\n{body}")
    lines = [l.strip(" -•*") for l in text.splitlines() if l.strip()]
    return "\n".join(lines[:4])
