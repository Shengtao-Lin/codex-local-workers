"""Seal the tested candidate before fresh task selection; no model invocation."""

import xml.etree.ElementTree as ET

import bounded_evidence_candidate as C
import bounded_evidence_support as S


def main():
    controls = S.BATCH / "controls-v4.xml"
    suite = ET.parse(controls).getroot().find("testsuite")
    if (
        suite is None
        or int(suite.get("failures", "0"))
        or int(suite.get("errors", "0"))
    ):
        raise ValueError("Offline controls did not pass")
    pins = S.read(
        S.KIT
        / "benchmarks/work/harness-convergence/semantic-advice-20261018-1/freeze.json"
    )["pins"]
    if any(S.sha(p) != digest for p, digest in pins.items()):
        raise ValueError("Previously qualified dependency changed")
    new = [
        "benchmarks/" + p
        for p in (
            "bounded_evidence_candidate.py",
            "bounded_evidence_entry.py",
            "bounded_evidence_unit.py",
            "bounded_evidence_support.py",
            "bounded_evidence_freeze.py",
        )
    ]
    new += ["tests/test_bounded_evidence_candidate.py"]
    pins = {**pins, **{str(S.KIT / p): S.sha(S.KIT / p) for p in new}}
    S.save(
        S.BATCH / "candidate-freeze.json",
        {
            "status": "CANDIDATE_PROTOCOL_FROZEN_BEFORE_NEW_TASK_SELECTION",
            "live_authorized": False,
            "pins": pins,
            "budget": C.BUDGET,
            "schemas": {
                arm: C.schema(C.UNIFIED.SPAN.D.INTERFACE.WHOLE_SCHEMA, arm)
                for arm in ("A", "B")
            },
            "controls": {
                "file": str(controls),
                "sha256": S.sha(controls),
                "passed": int(suite.get("tests")),
            },
            "known_limits": [
                "No live structured-output compatibility claim",
                "Validator short-circuit preserved",
                "Reviewer unknown-defect reliability unresolved",
            ],
        },
    )


if __name__ == "__main__":
    main()
