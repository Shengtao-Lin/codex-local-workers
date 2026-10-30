"""Primary-only executable check of F1; never re-request or overwrite Reviewer."""

import importlib.util
from pathlib import Path

import bounded_evidence_support as S

BATCH = S.KIT / "benchmarks/work/harness-convergence/stream-slice-transfer-20261022-3"


def main():
    row = S.read(BATCH / "cells.json")["frame-2"]
    root = Path(row["root"])
    name = row["identity"]["run_id"]
    report_path = (
        root / ".agent/tasks" / name / "reviews" / ("auto-" + name) / "handoff.json"
    )
    report = S.read(report_path)
    assert report["decision"] == "rework" and [f["id"] for f in report["findings"]] == [
        "F1"
    ]
    path = root / "src/product/code.py"
    before = S.sha(path)
    loader = importlib.util.spec_from_file_location("primary_frame_probe", path)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    observations = []
    for event in ("{", "}", "{}", "{missing}", "{0!r}", "{value:{width}}", "雪{}"):
        for data in ("", "x", "{}\ny"):
            actual = module.render_event(event, data)
            expected = (
                "event: "
                + event
                + "\n"
                + "\n".join("data: " + part for part in data.split("\n"))
                + "\n\n"
            )
            assert actual == expected
            observations.append(
                {"event": event, "data": data, "actual": actual, "expected": expected}
            )
    assert S.sha(path) == before
    reason = "False positive: the literal is the format template, event is an argument. Braces inside argument strings are not parsed as placeholders. Actual source plus21 independent executions preserve all brace-containing values exactly. No code, test, report or acceptance standard changed."
    dest = BATCH / "primary/frame-2"
    S.save(
        dest / "finding-probe.json",
        {
            "source_sha256": before,
            "finding_id": "F1",
            "observations": observations,
            "all_match": True,
            "phase": "Primary diagnostic after frozen run, not Worker feedback or new registered acceptance tests",
            "source_unchanged": True,
        },
    )
    S.save(
        dest / "disposition.json",
        {
            "schema_version": 1,
            "authority": "primary",
            "identity": report["identity"],
            "report_sha256": S.sha(report_path),
            "resolution": "cleared",
            "evidence": [
                reason,
                "Original15 independent behavior tests and all configured strict checks passed; full actual source/diff reviewed.",
            ],
            "findings": [
                {"finding_id": "F1", "disposition": "nonblocking", "evidence": reason}
            ],
        },
    )
    S.save(
        dest / "adjudication.json",
        {
            "implementation_correct_under_registered_contract": True,
            "reviewer_false_positive": True,
            "strict_complete_chain": False,
            "primary_semantic_rescue": False,
            "primary_additional_work": "Full review and21 finding-specific probe executions; active seconds/cloud tokens unknown",
            "do_not_change": "Original Reviewer rework retained. No Coder rework or Reviewer resampling. Strict batch gate remains failed; this is not an automatic supervised acceptance record.",
        },
    )
    print(
        "F1 disproved by21 unchanged-source probes; strict batch result remains non-PASS"
    )


if __name__ == "__main__":
    main()
