# Check every line of requirements.txt against PyPI.
# Needs Python 3.11+ and the "packaging" library.

import json
from urllib.request import urlopen
from urllib.error import HTTPError

from packaging.specifiers import SpecifierSet
from packaging.version import Version

my_python = "3.11"      # the Python version we check against

not_found = []
incompatible = []
best_line = None        # the release that needs the newest Python
best_python = None      # that newest minimum Python, e.g. Version("3.10")

# Read the file, one line per list item
with open("requirements.txt") as f:
    lines = f.read().splitlines()

for line in lines:
    line = line.strip()
    if line == "" or line.startswith("#"):    # skip empty lines and comments
        continue

    # Build the PyPI address
    if "==" in line:
        name, version = line.split("==")
        url = f"https://pypi.org/pypi/{name}/{version}/json"
    else:
        url = f"https://pypi.org/pypi/{line}/json"

    # Ask PyPI. Error 404 means: package or version does not exist.
    try:
        info = json.load(urlopen(url))["info"]
    except HTTPError:
        not_found.append(line)
        continue

    needs = info["requires_python"]           # e.g. ">=3.8,<4", or empty
    if not needs:
        continue

    # Is our Python inside the allowed range (lower and upper bound)?
    if my_python not in SpecifierSet(needs):
        incompatible.append(f"{line} (needs {needs})")

    # Find the lowest Python this release allows (the ">=" rule)
    for rule in SpecifierSet(needs):
        if rule.operator == ">=":
            low = Version(rule.version)
            if best_python is None or low > best_python:
                best_python = low
                best_line = line        # keep the name as written in the file

print("Dependencies Checked:", len(lines))
print("Not found on PyPI:", len(not_found))
print(f"Incompatible with Python {my_python}:", len(incompatible))
print("Highest requirement:", best_line, f"(>={best_python})")
