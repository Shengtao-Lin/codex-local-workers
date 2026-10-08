"""Independent exact-type probes; never modify frozen worker workspaces."""

import argparse
import hashlib
import json
import runpy
from pathlib import Path

from capability_fit import WORK, write


class IntegerSubclass(int):
    pass


def probe(root: Path, case: str):
    source = (
        root
        / "src/product"
        / ("target.py" if case == "window-groups" else "options.py")
    )
    namespace = runpy.run_path(str(source))
    function = namespace["groups" if case == "window-groups" else "parse_timeout"]
    results = []
    for value in (True, False, None, IntegerSubclass(2)):
        try:
            output = (
                function([], value)
                if case == "window-groups"
                else function({"timeout_ms": value})
            )
            result = {"exception": None, "output": output}
        except (ValueError, TypeError, RuntimeError, AssertionError) as error:
            result = {"exception": type(error).__name__}
        results.append(
            {
                "input_type": type(value).__name__,
                "input_repr": repr(value),
                "expected_exception": "ValueError",
                **result,
            }
        )
    return {
        "case": case,
        "workspace": str(root),
        "probes": results,
        "pass": all(r["exception"] == "ValueError" for r in results),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        choices=("boundary-primary-probes-1.json", "boundary-primary-probes-2.json"),
        default="boundary-primary-probes-1.json",
    )
    args = parser.parse_args()
    results = []
    for case in ("window-groups", "timeout-roundtrip"):
        for repetition in (1, 2):
            root = WORK / "roleq-six-1/runs/v1/roleq1" / f"{case}-round-{repetition}"
            result = probe(root, case)
            if args.output.endswith("-2.json"):
                coder = json.loads(
                    (root / ".agent/coder-a3.json").read_text(encoding="utf-8")
                )
                result["validated_source_hashes_match"] = all(
                    hashlib.sha256((root / item["path"]).read_bytes()).hexdigest()
                    == item["final_sha256"]
                    for item in coder["changed_files"]
                )
                manifest = json.loads(
                    (WORK / "roleq-six-1/manifest.json").read_text(encoding="utf-8")
                )
                cell = next(
                    c
                    for c in manifest["cells"]
                    if c["case"] == case and c["repetition"] == repetition
                )
                result["frozen_protected_test_unchanged"] = (
                    hashlib.sha256(
                        (root / "tests/test_target.py").read_bytes()
                    ).hexdigest()
                    == cell["initial_hashes"]["tests/test_target.py"]
                )
            results.append(result)
    write(
        WORK / "roleq-six-1" / args.output,
        {
            "classification": "Supplemental Primary probes; frozen tests unchanged",
            "results": results,
        },
    )
    print(json.dumps(results, indent=2))
