"""Skills and technologies a job description mentions, from data/taxonomy.json. Pure regex: free, repeatable, explainable."""
import re
from functools import lru_cache

from . import files


@lru_cache(maxsize=1)
def taxonomy():
    t = files.data("taxonomy.json")["skills"]
    return [(name, spec["group"], re.compile("|".join(f"(?:{p})" for p in spec["patterns"]), re.I)) for name, spec in t.items()]


def groups():
    return {name: group for name, group, _ in taxonomy()}


def find(title, desc):
    text = f"{title or ''}\n{desc or ''}"
    return sorted(name for name, _, rx in taxonomy() if rx.search(text))
