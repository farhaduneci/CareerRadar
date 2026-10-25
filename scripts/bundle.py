"""Assemble worker/src/ for pywrangler: entry.py, the careerradar package and the installed radarkit package (Python
Workers bundle the files beside the entry module; git dependencies cannot be installed by pywrangler)."""
import os, shutil

import radarkit

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "worker", "src")
skip = shutil.ignore_patterns("__pycache__", "*.pyc")

shutil.rmtree(SRC, ignore_errors=True)
os.makedirs(SRC)
shutil.copy(os.path.join(ROOT, "worker", "entry.py"), SRC)
shutil.copytree(os.path.join(ROOT, "careerradar"), os.path.join(SRC, "careerradar"), ignore=skip)
shutil.copytree(os.path.dirname(radarkit.__file__), os.path.join(SRC, "radarkit"), ignore=skip)
print(f"bundled careerradar + radarkit {radarkit.__version__} -> {os.path.relpath(SRC, ROOT)}")
