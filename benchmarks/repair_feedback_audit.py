"""Read-only audit of already-completed requests; never sends a model request."""

import ast
import difflib
import json
from pathlib import Path

import capture_fixture_support as F
import scheduling_trial as S

T = S.T
DEST = S.BATCH / "post-close-feedback-audit.json"


def audit():
    pins = T.read(S.BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    interface = F.load(S.KIT / ".local-agents/proposal-interface.py", "feedback_audit_interface")
    outcomes = []
    for repeat in (1, 2, 3):
        root = Path(T.read(S.BATCH / "cells.json")[f"new-{repeat}"]["root"])
        archive = root / f".agent/tasks/fresh-metadata/runs/schedule-new-{repeat}"
        request = T.read(archive / "proposal-request-2.json")
        facts = interface.restore_literal(request["messages"][1]["content"])
        validation = T.read(archive / "validation-attempt-2.json")["validation"]
        failed = [c for c in validation["configured_checks"] if c["status"] != "passed"]
        expected = [{key: c.get(key) for key in ("id", "status", "exit_code", "output", "diagnostic")}
                    for c in failed]
        assert facts["validation_failure"]["configured_checks"] == expected
        assert len(failed) == 1 and failed[0]["id"] == "pyright"
        assert "reportMissingParameterType" in failed[0]["output"]
        assert facts["validation_failure"]["focused_tests"]["failed_test_ids"] == []
        assert facts["validation_failure"]["source_sha256"] == request["binding"]["sha256"]
        assert facts["target"]["source"] == request["binding"]["source"]
        before = facts["target"]["source"]
        after = json.loads(T.read(archive / "proposal-response-2.json")["raw"])["replacement"]
        helper_before = next(n for n in ast.walk(ast.parse(before)) if isinstance(n, ast.FunctionDef)
                             and n.name == "check_finite")
        helper_after = next(n for n in ast.walk(ast.parse(after)) if isinstance(n, ast.FunctionDef)
                            and n.name == "check_finite")
        assert helper_before.args.args[0].annotation is None
        assert helper_after.args.args[0].annotation is None
        assert "from typing import Any" in facts["target"]["dependencies"]
        delta = list(difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm=""))
        outcomes.append({"repeat": repeat, "canonical_request": str(archive / "proposal-request-2.json"),
            "canonical_request_sha256": T.sha(archive / "proposal-request-2.json"),
            "actual_failed_check_projection_exact": True,
            "source_and_error_epoch_consistent": True,
            "missing_annotation_before_and_after": True, "Any_import_visible": True,
            "stale_pytest_failures_forwarded": False,
            "configured_check_error_count": len(failed),
            "general_diagnostics_field": facts["validation_failure"]["diagnostics"],
            "message_count": len(request["messages"]),
            "second_proposal_diff_from_displayed_source": delta,
            "facts": "Passing pytest summary coexists with the correctly failed pyright check; metadata contains empty generic diagnostics. Error is present, not silently absent.",
        })
    T.save(DEST, {"model_calls": 0, "production_changes": False,
        "closed_batch_scores_changed": False, "frozen_pins_unchanged": True,
        "outcomes": outcomes,
        "conclusion": "No stale failure, missing failed-check output, missing Any import or source/hash mismatch found. Whole-function regeneration leaves the exact type defect while altering formatting. Existing evidence does not distinguish error comprehension from output/edit granularity effects.",
        "next_diagnostic": "Same frozen input in three separately scored arms: read-only error diagnosis, whole-function repair, mechanically bound minimal-span repair. Three proposals each, no hidden code repair or relaxed tests. New live authorization required; not implementation or fresh-transfer qualification."})
    print(json.dumps({"audited": 3, "model_calls": 0, "artifact": str(DEST)}))


if __name__ == "__main__":
    audit()
