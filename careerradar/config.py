"""Settings: the shipped defaults (data/config.default.json) with the user's overrides merged on top, and the watch list
(the shipped top-50 list unless the user brings their own)."""
import copy, json

from . import files


def merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load(override=None):
    """override: a dict, a JSON string (the Worker's CONFIG var) or a path to config.json."""
    if isinstance(override, str):
        override = json.loads(override) if override.lstrip().startswith("{") else json.load(open(override))
    return merge(files.data("config.default.json"), override)


def companies(source=None):
    """Enabled companies. source: None (the shipped list), a path, or a parsed {"companies": [...]}."""
    d = files.data("companies.json") if source is None else json.load(open(source)) if isinstance(source, str) else source
    return [c for c in d["companies"] if c.get("enabled", True) and c.get("boards")]
