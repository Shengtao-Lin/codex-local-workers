"""Check whether a trusted Python module resolves inside an expected project.

This is an optional Primary-side diagnostic, not a sandbox or an acceptance gate.
Importing the selected module executes its normal Python import side effects.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_PROBE = """\
import importlib, json, sys
module = importlib.import_module(sys.argv[1])
print(json.dumps({'origin': getattr(module, '__file__', None)}))
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python", required=True, help="Interpreter used for the real checks"
    )
    parser.add_argument(
        "--project", required=True, help="Expected project root and working directory"
    )
    parser.add_argument(
        "--module", required=True, help="Trusted importable module name"
    )
    parser.add_argument(
        "--source-root", help="Optional project-relative source root to prepend"
    )
    args = parser.parse_args()

    project = Path(args.project).resolve()
    interpreter = Path(args.python).resolve()
    if not project.is_dir() or not interpreter.is_file():
        print(
            json.dumps(
                {"status": "error", "reason": "project or interpreter not found"}
            )
        )
        return 2
    env = dict(os.environ)
    if args.source_root:
        source = (project / args.source_root).resolve()
        if not source.is_dir() or not source.is_relative_to(project):
            print(
                json.dumps(
                    {"status": "error", "reason": "source root is not inside project"}
                )
            )
            return 2
        old = env.get("PYTHONPATH")
        env["PYTHONPATH"] = os.pathsep.join([str(source), old]) if old else str(source)
    try:
        run = subprocess.run(
            [str(interpreter), "-B", "-c", _PROBE, args.module],
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "error", "reason": type(exc).__name__}))
        return 2
    if run.returncode:
        print(
            json.dumps(
                {
                    "status": "error",
                    "reason": "import failed",
                    "stderr": run.stderr[-2000:],
                }
            )
        )
        return 2
    try:
        payload = json.loads(run.stdout.splitlines()[-1])
        raw = payload["origin"]
        if not isinstance(raw, str):
            raise TypeError("module has no single file origin")
        origin = Path(raw).resolve(strict=True)
    except (IndexError, KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        print(json.dumps({"status": "error", "reason": "module origin unavailable"}))
        return 2
    inside = origin.is_relative_to(project)
    print(
        json.dumps(
            {
                "status": "inside_project" if inside else "outside_project",
                "module": args.module,
                "origin": str(origin),
                "project": str(project),
            },
            ensure_ascii=False,
        )
    )
    return 0 if inside else 1


if __name__ == "__main__":
    sys.exit(main())
