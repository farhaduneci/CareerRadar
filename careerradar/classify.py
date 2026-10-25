"""Title-only classification: is it a tech role, which function, which seniority, which title family.
Rules live in data/tech_roles.json; this only compiles and applies them."""
import re
from functools import lru_cache

from . import files


@lru_cache(maxsize=1)
def rules():
    r = files.data("tech_roles.json")
    comp = lambda ps: re.compile("|".join(f"(?:{p})" for p in ps), re.I)
    return {"exclude": comp(r["exclude"]),
            "functions": [(f["name"], comp(f["patterns"])) for f in r["functions"]],
            "seniority": [(s["name"], comp(s["patterns"])) for s in r["seniority"]]}


def clean(title):
    return re.sub(r"\s+", " ", title or "").strip()


def function(title):
    """The function of a tech role, else None (not a tech role)."""
    t = clean(title)
    R = rules()
    if R["exclude"].search(t):
        return None
    return next((name for name, rx in R["functions"] if rx.search(t)), None)


def seniority(title):
    t = clean(title)
    return next((name for name, rx in rules()["seniority"] if rx.search(t)), "Mid")


LEVEL_WORDS = re.compile(r"\b(senior|sr|staff|principal|lead|junior|jr|intern(ship)?|new grad|graduate|associate|distinguished|"
                         r"head of|director|manager|i{1,3}|iv|v|[1-5]|20\d\d|summer|fall|phd|masters?|bachelors?|contract(or)?|"
                         r"part[- ]time|full[- ]time|remote|hybrid)\b", re.I)


def family(title):
    """The role without level, team and place: 'Senior Software Engineer, Payments (Remote)' -> 'software engineer'."""
    t = clean(title).lower()
    t = re.split(r"\s[-–—|/]\s|,|\(|:|\bat\b", t)[0]
    t = LEVEL_WORDS.sub(" ", t)
    t = re.sub(r"[^a-z0-9+#. ]", " ", t)
    return re.sub(r"\s+", " ", t).strip(" .") or None
