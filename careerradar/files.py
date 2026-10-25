"""Files shipped with the package: data (companies, rules, taxonomy), prompts, templates, migrations. Code never inlines them."""
import json, os

PKG = os.path.dirname(os.path.abspath(__file__))
DATA, PROMPTS, TEMPLATES, MIGRATIONS = (os.path.join(PKG, d) for d in ("data", "prompts", "templates", "migrations"))


def data(name):
    return json.load(open(os.path.join(DATA, name)))


def prompt(name):
    return open(os.path.join(PROMPTS, name + ".md")).read()


def migrations():
    return {f: open(os.path.join(MIGRATIONS, f)).read() for f in sorted(os.listdir(MIGRATIONS)) if f.endswith(".sql")}
