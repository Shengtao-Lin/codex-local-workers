"""Fixed wording/source diagnostic using honestly labelled Primary fixtures."""

import argparse
import ast
import json
import shutil
from pathlib import Path

import harness_r4_real_review as PREV

B, R, E = PREV.B, PREV.R, PREV.E
BATCH = E.BATCH.parent / "r4-review-terms-20261016-1"
TARGET = "src/evaluation_harness/adapters/common.py"
OLD_TERM = "unknown result ignored"
NEW_TERM = "only result events with an unrecognized call_id are ignored"
COMBINATIONS = [
    ("original", "draft"),
    ("clarified", "draft"),
    ("original", "reference"),
    ("clarified", "reference"),
    ("clarified", "reference"),
    ("original", "reference"),
    ("clarified", "draft"),
    ("original", "draft"),
]


def prepare(used):
    assert used < 45 and B.read(E.BATCH / "decision.json")["qualification"] == "PASS"
    assert B.read(PREV.BATCH / "decision.json")["qualification"] == "HOLD"
    BATCH.mkdir(exist_ok=False)
    prior = E.D.OLD.H.BATCH
    origin = prior / "cases/collect_tools-candidate-1/isolated"
    source = prior / "prepared-fixtures/collect_tools/visible"
    reference = prior / "prepared-fixtures/collect_tools/private-reference"
    rows = []
    for index, (wording, implementation) in enumerate(COMBINATIONS, 1):
        name = f"cell-{index:02}"
        root = BATCH / "cells" / name / "isolated"
        for top in ("src", "tests"):
            shutil.copytree(source / top, root / top)
        shutil.copy2(source / "pyproject.toml", root / "pyproject.toml")
        shutil.copytree(
            origin / ".local-agents",
            root / ".local-agents",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        packet = B.read(origin / ".agent/packet.json")
        packet.update(
            task_id="semantic-terms",
            feature_id="reviewer-terms-diagnostic",
            run_id=f"terms-{index:03}",
            primary_plan_sha256=None,
            plan_revision=1,
            packet_revision=1,
        )
        packet.pop("primary_plan_sha256")
        packet["risk"]["reasons"] = [
            "Primary-authored diagnostic archive at a high-risk semantic review boundary; no live Coder credit."
        ]
        if wording == "clarified":
            raw = json.dumps(packet)
            assert raw.count(OLD_TERM) == 3
            packet = json.loads(raw.replace(OLD_TERM, NEW_TERM))
        config = B.read(origin / ".agent/config.json")
        B.save(root / ".agent/packet.json", packet)
        B.save(root / ".agent/coder-config.json", config)
        chosen = reference if implementation == "reference" else origin
        code = (chosen / TARGET).read_text(encoding="utf-8")
        node = next(
            n
            for n in ast.parse(code).body
            if isinstance(n, ast.FunctionDef) and n.name == "collect_tools"
        )
        # This is a fixture materialization, not generated model work. Keep the
        # static replacement outside worker-readable roots, never expose a label.
        B.save(
            root.parent / "static-fixture.json",
            {
                "replacement": ast.get_source_segment(code, node),
                "source": str(chosen / TARGET),
                "sha256": B.sha(chosen / TARGET),
            },
        )
        rows.append(
            {
                "id": name,
                "root": str(root),
                "wording": wording,
                "implementation": implementation,
                "expected_decision": "pass_to_primary"
                if implementation == "reference"
                else "rework",
                "identity": {
                    "schema_version": 1,
                    "task_id": packet["task_id"],
                    "unit_id": packet["unit_id"],
                    "run_id": packet["run_id"],
                    "review_id": f"terms-review-{index:03}",
                    "execution_protocol": "host-proposal-v1",
                },
            }
        )
    B.save(
        BATCH / "design-registration.json",
        {
            "feature_id": "reviewer-contract-terms-diagnostic",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "axis": "Replace one ambiguous term only in newly registered canonical contracts; original records remain unchanged. Source/reference dimension prevents unconditional-rework from counting as success.",
            "original_term": OLD_TERM,
            "clarified_term": NEW_TERM,
            "intended_semantics_basis": "Original exact-result-including-falsy obligation, real result: Any = None type, reference implementation and frozen unknown-call tests. New wording expresses Primary's existing interpretation, not a changed desired result.",
            "not_answer_injection": "No None-specific hint, line number, suggested repair, expected verdict, or hidden test is supplied to Reviewer.",
            "registered": 8,
            "no_retry": True,
            "usage_start": used,
            "usage_ceiling": 45,
            "no_coder_credit": True,
            "not_new_holdouts": True,
            "primary_active_seconds": None,
            "criterion": "Report original vs clarified accuracy separately for both sources (two repeats each). Clarified 4/4 with draft 2/2 detection and reference 2/2 acceptance supports wording contribution only, never R4 acceptance.",
            "old_none_defect_and_all_failures_retained": True,
        },
    )
    B.save(BATCH / "prepared.json", {"cells": rows})
    print("Eight neutral-ID Primary fixtures prepared; no model calls")


def build(name):
    row = next(r for r in B.read(BATCH / "prepared.json")["cells"] if r["id"] == name)
    root = Path(row["root"])
    packet, config = (
        B.read(root / ".agent/packet.json"),
        B.read(root / ".agent/coder-config.json"),
    )
    static = B.read(root.parent / "static-fixture.json")
    assert B.sha(Path(static["source"])) == static["sha256"]
    worker = R.load(root / ".local-agents/worker-runtime.py", "terms_worker_" + name)
    host = R.load(root / ".local-agents/host-proposal.py", "terms_host_" + name)

    class StaticFixtureClient:
        timeout = 180
        calls = 0

        def complete(self, messages):
            self.calls += 1
            assert self.calls == 1, "fixture generation must not enter repair"
            return json.dumps({"replacement": static["replacement"]})

    client = StaticFixtureClient()
    runtime = host.make_runtime_class(worker)(root, packet, config, client)
    report = runtime.run()
    B.save(
        root.parent / "fixture-build.json",
        {
            "synthetic_primary_archive": True,
            "live_coder_model_calls": 0,
            "static_fixture_materializations": client.calls,
            "status": report.get("status"),
            "failure_reason": report.get("failure_reason"),
        },
    )
    assert report["status"] == "validation_passed_pending_review", report
    finish_build(name)


def finish_build(name):
    """Finish a validated fixture without replaying its static materialization."""
    row = next(r for r in B.read(BATCH / "prepared.json")["cells"] if r["id"] == name)
    root = Path(row["root"])
    config = B.read(root / ".agent/coder-config.json")
    static = B.read(root.parent / "static-fixture.json")
    assert (
        B.read(root.parent / "fixture-build.json")["status"]
        == "validation_passed_pending_review"
    )
    assert B.sha(Path(static["source"])) == static["sha256"]
    actual = (root / TARGET).read_bytes()
    original = Path(static["source"]).read_bytes()
    assert actual.replace(b"\r\n", b"\n") == original.replace(b"\r\n", b"\n"), (
        "non-EOL source drift"
    )
    B.save(
        root.parent / "source-equivalence.json",
        {
            "origin_sha256": static["sha256"],
            "actual_sha256": B.sha(root / TARGET),
            "exact_bytes": actual == original,
            "only_crlf_lf_difference": actual != original,
            "all_other_bytes_identical": True,
            "cause": "Existing trusted formatter normalizes line endings; no source semantics changed.",
        },
    )
    review_config = {
        **config,
        "reviewer_compact_report": True,
        "reviewer_evidence_state": True,
    }
    B.save(root / ".agent/experiment-config.json", review_config)
    B.save(root / ".agent/experiment-request.json", row["identity"])
    module = R.load(root / ".local-agents/reviewer-runtime.py", "terms_review_" + name)
    PREV.A.install(module)(
        root,
        row["identity"],
        review_config,
        type("NoModel", (), {"native_tools": None})(),
    ).initial_payload()
    B.save(
        root.parent / "input-freeze.json",
        {p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)},
    )
    print(
        name,
        "actual deterministic checks and host verification passed; no model",
        flush=True,
    )


def register():
    rows = B.read(BATCH / "prepared.json")["cells"]
    for row in rows:
        root = Path(row["root"])
        row["files"] = B.read(root.parent / "input-freeze.json")
        R.assert_files(root, row["files"])
    B.save(
        BATCH / "registration.json",
        {
            "cells": rows,
            "registered": 8,
            "usage_ceiling": 45,
            "no_coder_or_transfer_credit": True,
        },
    )


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "controls.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + x) for x in ("failure", "error", "skipped")
    )
    pins = {
        **B.read(PREV.BATCH / "live-freeze.json")["pins"],
        str(Path(__file__)): B.sha(Path(__file__)),
        str(BATCH / "registration.json"): B.sha(BATCH / "registration.json"),
        str(B.KIT / "tests/test_reviewer_terms.py"): B.sha(
            B.KIT / "tests/test_reviewer_terms.py"
        ),
    }
    B.save(BATCH / "live-freeze.json", {"pins": pins})
    print("Fixed eight-cell terms/source diagnostic frozen")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=["prepare", "build", "finish-build", "register", "freeze", "run"],
    )
    parser.add_argument("--used", type=int)
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.used)
    elif args.action == "build":
        build(args.case)
    elif args.action == "finish-build":
        finish_build(args.case)
    elif args.action == "register":
        register()
    elif args.action == "freeze":
        freeze()
    else:
        E.BATCH, E.ADAPTER = BATCH, PREV.ADAPTER
        E.run(args.case, args.used)
