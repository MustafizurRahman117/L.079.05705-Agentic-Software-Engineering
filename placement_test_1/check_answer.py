# Run check_requirement_file.py on testrequirements.txt and compare its output with the answer file.
# Run:  python check_answer.py

import os
import shutil
import subprocess
import sys
import tempfile

with open("teserequirementans.txt") as f:
    expected = f.read().splitlines()

# check_requirement_file.py always reads "requirements.txt", so run it in a temporary folder
# where testrequirements.txt is copied as requirements.txt (your real file stays untouched)
with tempfile.TemporaryDirectory() as folder:
    shutil.copy("testrequirements.txt", f"{folder}/requirements.txt")
    script = os.path.abspath("check_requirement_file.py")      # full path, because we run inside the temp folder
    result = subprocess.run([sys.executable, script], cwd=folder, capture_output=True, text=True)
if result.returncode != 0:
    print(result.stderr)
actual = result.stdout.splitlines()

for want, got in zip(expected, actual):
    print("OK  " if want == got else "FAIL", f"want: {want!r:45} got: {got!r}")

assert actual == expected, "check_requirement_file.py output does not match the answer"
print("All lines match!")
