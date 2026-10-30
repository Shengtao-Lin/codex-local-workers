"""Independent read/validation facts for a C1 cell; does not write acceptance."""

import argparse
import os
from pathlib import Path
import subprocess
import time

from convergence_coder import BASE, KIT, PYTHON
from system_convergence import read_object, sha256, write_output

parser = argparse.ArgumentParser()
parser.add_argument("cell")
args = parser.parse_args()
registration = read_object(BASE / "registration.json")
cell = next(c for c in registration["cells"] if c["id"] == args.cell)
root = Path(cell["root"])
output = root / "independent-audit.json"
if output.exists():
    raise FileExistsError("audit already exists")
temp = root / ".agent/primary-process-temp"
temp.mkdir()
env = dict(os.environ, TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE="1")
checks = [
    (
        "pytest",
        [
            "-m",
            "pytest",
            "-q",
            "--basetemp=.agent/primary-pytest-temp",
            "--junitxml=.agent/primary-tests.xml",
        ],
    ),
    ("ruff-check", ["-m", "ruff", "check", "src", "tests"]),
    ("ruff-format", ["-m", "ruff", "format", "--check", "src", "tests"]),
]
if cell["kind"] == "timestamp":
    checks.append(("pyright", ["-m", "pyright", "--pythonpath", str(PYTHON), "src"]))
results = []
for name, command in checks:
    start = time.perf_counter()
    result = subprocess.run(
        [str(PYTHON), "-B", *command],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    results.append(
        {
            "id": name,
            "exit": result.returncode,
            "seconds": time.perf_counter() - start,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    )
protected = all(
    sha256(root / a["path"]) == a["sha256"]
    for a in cell["inputs"]
    if a["path"] not in cell["writable"]
)
write_output(
    KIT,
    output.relative_to(KIT).as_posix(),
    {
        "checks": results,
        "protected_unchanged": protected,
        "primary_acceptance": "pending independent diff and Reviewer review",
        "source_writes": 0,
    },
)
print(args.cell, "protected", protected, [(r["id"], r["exit"]) for r in results])
