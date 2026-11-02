# How `check_requirement_file.py` works

## The idea in one paragraph

A `requirements.txt` file is a shopping list for Python projects. Each line names
a package (a piece of code someone else wrote) and often a version, like
`django==6.0`. All public packages live on a website called **PyPI**
(pypi.org), like a big shop.

Our script takes the shopping list, asks the shop about every item, and writes a
short report:

1. **How many lines** the list has.
2. **How many items the shop doesn't have.** Either the package doesn't exist,
   or that exact version doesn't exist.
3. **How many items don't work with Python 3.11.**
4. **Which item needs the newest Python.**

## Words you need

| Word | Meaning |
|---|---|
| **package** | Code someone else wrote that you can install, e.g. `django` |
| **version** | Which edition of the package, e.g. `6.0` |
| **PyPI** | The website where all public Python packages are stored |
| **requires_python** | A note from the package saying which Python versions it works with, e.g. `>=3.8` |
| **JSON** | A simple text format that websites use to send data to programs |
| **list** | A row of items in Python: `["a", "b", "c"]` |
| **dictionary** | Items with labels: `{"name": "django", "version": "6.0"}` |

## How to read `>=` and `<`

PyPI writes the allowed Python versions as small rules:

- `>=3.8` means "3.8 **or newer**". This is the **lower limit**.
- `<3.11` means "**older than** 3.11". This is the **upper limit**.
- `>=3.7,<3.11` means both at once: from 3.7 up to, but not including, 3.11.

Think of it as a door with an age limit: "you must be at least 7, and younger
than 11". Python 3.11 is "11 years old", so it can't go through that door.

---

## The code, piece by piece

### Part 1: Bring in the tools

```python
import json
from urllib.request import urlopen
from urllib.error import HTTPError

from packaging.specifiers import SpecifierSet
from packaging.version import Version
```

Python doesn't load every tool at the start. We ask for the ones we need:

- `json`: reads the text PyPI sends back and turns it into a dictionary.
- `urlopen`: opens a web address, like a browser does, but without a window.
- `HTTPError`: the "error" we get when a page doesn't exist (the famous **404 Not Found**).
- `SpecifierSet`: understands rules like `>=3.7,<3.11` and can answer "is 3.11 allowed?"
- `Version`: compares versions correctly.

Why do we need `Version`? Plain text is compared letter by letter, like in a
dictionary. As text, `"3.9"` comes **after** `"3.10"`, because `9` is bigger
than `1`. That's wrong. `Version` knows that 3.10 is newer than 3.9.

### Part 2: Get ready

```python
my_python = "3.11"      # the Python version we check against

not_found = []
incompatible = []
best_line = None        # the release that needs the newest Python
best_python = None      # that newest minimum Python, e.g. Version("3.10")
```

We make some empty "boxes" to collect results:

- `my_python`: the Python version we test against. It's always 3.11.
- `not_found`: an empty list. Packages PyPI doesn't know will go in here.
- `incompatible`: an empty list. Packages that don't work with 3.11 will go in here.
- `best_line` and `best_python`: start as `None` ("nothing yet"). They will
  remember the package that needs the newest Python.

### Part 3: Read the file

```python
with open("requirements.txt") as f:
    lines = f.read().splitlines()
```

- `open(...)` opens the file.
- `f.read()` reads all of it as one long text.
- `.splitlines()` cuts that text at every line break, so we get a list with one
  item per line:
  `["requests==2.31.0", "django==6.0", ...]`
- `with` closes the file again automatically when we're done.

### Part 4: Look at each line, one by one

```python
for line in lines:
    line = line.strip()
    if line == "" or line.startswith("#"):
        continue
```

- `for line in lines:` repeats everything below it once per line.
- `.strip()` removes spaces at the start and end.
- If the line is empty, or is a comment (starts with `#`), `continue` means
  "skip this one, go to the next line".

### Part 5: Build the web address

```python
    if "==" in line:
        name, version = line.split("==")
        url = f"https://pypi.org/pypi/{name}/{version}/json"
    else:
        url = f"https://pypi.org/pypi/{line}/json"
```

PyPI has a page with information about every package.

- If the line has a version (`django==6.0`), we cut it at `==`. That gives
  `name = "django"` and `version = "6.0"`, and we ask for exactly that version:
  `https://pypi.org/pypi/django/6.0/json`
- If the line has no version (`django`), we ask for the package in general,
  and PyPI answers with the newest version:
  `https://pypi.org/pypi/django/json`

The `f"..."` is an **f-string**: whatever is inside `{ }` gets filled in.

### Part 6: Ask PyPI

```python
    try:
        info = json.load(urlopen(url))["info"]
    except HTTPError:
        not_found.append(line)
        continue
```

- `try:` means "try this, and be ready in case it goes wrong".
- `urlopen(url)` visits the page.
- `json.load(...)` turns the answer into a dictionary.
- `["info"]` takes only the part we need. It holds the name, the version and
  `requires_python`.
- `except HTTPError:` runs if the page doesn't exist. Then the package (or that
  version) isn't on PyPI, so we add the line to `not_found`, and `continue` to
  the next line.

### Part 7: Does it say which Python it needs?

```python
    needs = info["requires_python"]
    if not needs:
        continue
```

`needs` is the rule text, e.g. `">=3.7,<3.11"`. Some packages don't give one.
Then `needs` is empty, there is nothing to check, and we skip to the next line.

### Part 8: Does it work with Python 3.11?

```python
    if my_python not in SpecifierSet(needs):
        incompatible.append(f"{line} (needs {needs})")
```

`SpecifierSet(needs)` turns the rule text into a real rule. Then we ask: "is
3.11 allowed?" This checks the lower limit **and** the upper limit at the same
time. If the answer is no, we add the line to `incompatible`.

Examples:
- `>=3.8`: 3.11 is newer than 3.8, so it is allowed.
- `>=3.12`: 3.11 is older than 3.12, so it is **not allowed** (too old).
- `>=3.7,<3.11`: 3.11 is not *older than* 3.11, so it is **not allowed** (too new).

### Part 9: Remember the package that needs the newest Python

```python
    for rule in SpecifierSet(needs):
        if rule.operator == ">=":
            low = Version(rule.version)
            if best_python is None or low > best_python:
                best_python = low
                best_line = line
```

A rule text can hold several small rules. `>=3.7,<3.11` holds `>=3.7` and `<3.11`.

- We go through each small rule.
- We only care about `>=`, because that one says "the lowest Python allowed".
- `low` is that lowest Python, for example 3.7.
- If we have no winner yet (`None`), **or** this `low` is higher than the
  current winner, this package becomes the new winner.

It's like finding the tallest person in a room: you look at each person, and
whenever someone is taller than the tallest so far, they become the new tallest.

### Part 10: Print the report

```python
print("Dependencies Checked:", len(lines))
print("Not found on PyPI:", len(not_found))
print(f"Incompatible with Python {my_python}:", len(incompatible))
print("Highest requirement:", best_line, f"(>={best_python})")
```

`len(...)` counts how many items are in a list. So we print:

- how many lines the file has,
- how many packages were not found,
- how many don't work with 3.11,
- the winner from Part 9.

---

## A full example

`testrequirements.txt`:

```
requests==2.31.0
django==6.0
numpy==1.21.6
flask==3.0.0
langchain-pdf-agent==0.1.0
```

What happens to each line:

| Line | PyPI says | Works with 3.11? | Lowest Python | Winner so far |
|---|---|---|---|---|
| requests==2.31.0 | `>=3.7` | yes | 3.7 | requests (3.7) |
| django==6.0 | `>=3.12` | **no**, too old | 3.12 | **django (3.12)** |
| numpy==1.21.6 | `>=3.7,<3.11` | **no**, too new | 3.7 | django (3.12) |
| flask==3.0.0 | `>=3.8` | yes | 3.8 | django (3.12) |
| langchain-pdf-agent==0.1.0 | **404, not found** | – | – | django (3.12) |

Report:

```
Dependencies Checked: 5
Not found on PyPI: 1
Incompatible with Python 3.11: 2
Highest requirement: django==6.0 (>=3.12)
```

---

## The checker: `check_answer.py`

This small script tests `check_requirement_file.py` automatically, so you don't have to compare by
eye.

1. It reads the correct answer from `teserequirementans.txt`.
2. It makes a **temporary folder**, copies `testrequirements.txt` into it under
   the name `requirements.txt`, and runs `check_requirement_file.py` there. That way your real
   `requirements.txt` is never touched. The folder is deleted afterwards.
3. It compares the answer and the real output line by line, and prints `OK` or
   `FAIL` for each line.
4. `assert actual == expected` is the final test. `assert` means "this must be
   true". If it is true, nothing happens and we print `All lines match!`. If
   it is false, Python stops with an `AssertionError`.

Run it with:

```bash
python check_answer.py
```

## Limits (what the script does not handle)

- Only lines like `name==version` or a plain `name` work. A line like
  `requests>=2.0` is counted as "not found".
- It needs the internet. Without it, the script stops with an error.
- The first number counts **all** lines in the file, including empty lines and
  comments.
