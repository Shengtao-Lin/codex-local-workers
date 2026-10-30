"""Small immutable artifact helpers for the opt-in evidence experiment."""

import hashlib
import json
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
BATCH = KIT / "benchmarks/work/harness-convergence/bounded-evidence-prep-20261018-1"
PYTHON = Path("F:/ChatGPT/agent-evaluation-harness/.venv/Scripts/python.exe")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def baseline():
    names = (
        subprocess.check_output(
            ["git", "ls-files", "-m", "-o", "--exclude-standard", "-z"], cwd=KIT
        )
        .decode()
        .split("\0")
    )
    save(
        BATCH / "baseline.json",
        {
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=KIT)
            .decode()
            .strip(),
            "files": {p: sha(KIT / p) for p in names if p and (KIT / p).is_file()},
            "weekly_used": 8,
            "authorization": "Offline S0-S3 only; no new live",
            "process_observation": "Read-only CIM inventory: LM Studio processes, no Python/lms batch process",
        },
    )


if __name__ == "__main__":
    baseline()
