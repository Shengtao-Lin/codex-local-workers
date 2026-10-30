"""Frozen operation, not an arbitrary Python/shell runner. Isolated imports via -I."""

import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

MAX_INPUT = 131072
MAX_OUTPUT = 65536


def summarize(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        raise ValueError("Operation input byte bound exceeded")
    data = json.loads(raw)
    if not isinstance(data, list) or not 1 <= len(data) <= 10000:
        raise ValueError("Expected1..10000 finite numeric values")
    if any(type(x) not in (int, float) or not math.isfinite(x) or abs(x) > 1e100 for x in data):
        raise ValueError("Expected finite numbers, not bool/objects/non-finite/huge values")
    return {
        "count": len(data),
        "sum": math.fsum(data),
        "min": min(data),
        "max": max(data),
        "input_sha256": hashlib.sha256(raw).hexdigest(),
    }


def run_operation(python, path, cwd, timeout=30):
    # No inherited PYTHONPATH, startup hooks, API keys, profiles, or model argv.
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    }
    result = subprocess.run(
        [str(python), "-I", "-B", str(Path(__file__).resolve()), str(path)],
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if len(result.stdout) + len(result.stderr) > MAX_OUTPUT:
        raise ValueError("Trusted operation output bound exceeded")
    if result.returncode:
        raise ValueError(
            "Operation failed: " + result.stderr.decode("utf-8", errors="replace")[-1000:]
        )
    return json.loads(result.stdout)


if __name__ == "__main__":
    try:
        print(json.dumps(summarize(sys.argv[1]), allow_nan=False))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
