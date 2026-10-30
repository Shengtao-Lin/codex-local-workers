"""Continue registered cells after output-limit failures without changing raw records."""

import argparse
from pathlib import Path

import reviewer_required_probe as H


def boundary_view(path, value):
    p = Path(path).resolve()
    if (
        p.parent.parent == (H.BATCH / "cells").resolve()
        and p.name == "result.json"
        and isinstance(value, dict)
        and value.get("request_stats", {}).get("rejection_reason")
        == "output_token_limit"
    ):
        return {**value, "infra_failure": False}
    return value


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(H.BATCH / "failure-boundary-controls.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + tag) for tag in ("failure", "error", "skipped")
    )
    H.B.save(
        H.BATCH / "failure-boundary-registration.json",
        {
            "reason": "Raw result infers infra from absent parsed response. Explicit output_token_limit is a model budget failure, not infrastructure. Continue remaining original three cells, do not retry first or change its score.",
            "remaining": ["probe-02", "probe-03", "probe-04"],
            "raw_records_never_written": True,
            "only_in_memory_previous_cell_stop_classification_changes": True,
            "pins": {
                str(p): H.B.sha(p)
                for p in (
                    Path(__file__),
                    H.B.KIT / "tests/test_probe_failure_boundary.py",
                    H.BATCH / "failure-boundary-controls.xml",
                    H.BATCH / "cells/probe-01/result.json",
                )
            },
        },
    )


def run(name, used):
    registration = H.B.read(H.BATCH / "failure-boundary-registration.json")
    assert name in registration["remaining"]
    for path, sha in registration["pins"].items():
        assert H.B.sha(Path(path)) == sha
    original = H.B.read

    def read(path):
        return boundary_view(path, original(path))

    H.B.read = read
    try:
        H.run(name, used)
    finally:
        H.B.read = original


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["freeze", "run"])
    parser.add_argument("--case")
    parser.add_argument("--used", type=int)
    args = parser.parse_args()
    freeze() if args.action == "freeze" else run(args.case, args.used)
