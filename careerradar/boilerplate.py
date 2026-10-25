"""Company boilerplate (about-us, benefits, EEO, pay-range text) repeats in every description and would count as a skill
in every posting. A paragraph that appears in `SHARE` of a company's descriptions is boilerplate; it is learned from each
batch and kept per company, and stripped before skills are matched."""
import collections, hashlib, json, re

SHARE, MIN_BATCH, MIN_LEN = 0.3, 8, 40


def paragraphs(desc):
    return [p.strip() for p in re.split(r"\n+", desc or "") if len(p.strip()) >= MIN_LEN]


def key(p):
    return hashlib.sha1(re.sub(r"\W+", " ", p.lower()).strip().encode()).hexdigest()[:12]


def learn(descs, known=()):
    """Hashes of paragraphs repeated across this batch, merged with what was known."""
    out = set(known)
    descs = [d for d in descs if d]
    if len(descs) >= MIN_BATCH:
        c = collections.Counter(k for d in descs for k in {key(p) for p in paragraphs(d)})
        out |= {k for k, n in c.items() if n >= SHARE * len(descs)}
    return out


def strip(desc, boiler):
    return "\n".join(p for p in re.split(r"\n+", desc or "") if key(p.strip()) not in boiler) if boiler else (desc or "")


async def load(app, company):
    return set(json.loads(await app.kv(f"boiler:{company}", "[]")))


async def save(app, company, hashes):
    await app.set_kv(f"boiler:{company}", json.dumps(sorted(hashes)[-2000:]))
