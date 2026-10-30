"""No-model controls of explicit import authority, same-version diagnostics and gate."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import behavior_unit_candidate as C
import behavior_unit_trial as TRIAL
import bounded_evidence_readiness as READY
import bounded_evidence_support as S
import capture_fixture_support as F

OLD = S.KIT / "benchmarks/work/harness-convergence/feedback-recovery-20261018-3"
ALLOWED = {
    ("collections.abc", "Iterator", None),
    ("collections.abc", "Sequence", None),
    ("typing", "cast", None),
}
SOURCE = 'from __future__ import annotations\nfrom collections.abc import Iterator, Sequence\nfrom typing import cast\n__all__ = ["f"]\ndef f(value: object) -> object:\n    return value\n'


def test_actual_unit_command():
    old = S.KIT / "benchmarks/bounded_evidence_unit.py"
    new = S.KIT / "benchmarks/behavior_unit_unit.py"
    assert TRIAL.unit_argv(["python", "-B", old]) == ["python", "-B", str(new)]


def test_approved_import_remove_and_function_edit():
    C.guard(
        SOURCE,
        SOURCE.replace("from typing import cast\n", "").replace(
            "return value", "return [value]"
        ),
        "f",
        ALLOWED,
    )


@pytest.mark.parametrize(
    "replacement",
    [
        SOURCE.replace("from typing import cast", "import os"),
        SOURCE.replace("from typing import cast", "from typing import cast as changed"),
        SOURCE.replace("from __future__ import annotations\n", ""),
        SOURCE.replace("f(value: object)", "f(value: str)"),
        SOURCE.replace('__all__ = ["f"]', '__all__ = ["other"]'),
        SOURCE + "\nx = 42\n",
        SOURCE.replace("return value", "import os\n    return value"),
    ],
)
def test_other_changes_rejected(replacement):
    with pytest.raises((ValueError, SyntaxError)):
        C.guard(SOURCE, replacement, "f", ALLOWED)


@pytest.fixture
def build(tmp_path):
    row = S.read(OLD / "cells-receipt.json")["T2-A1"]
    root = READY.clone(row, tmp_path)
    config = S.read(root / ".agent/config.json")
    config.update(
        experimental_behavior_unit=True,
        experimental_approved_imports=[list(v) for v in sorted(ALLOWED)],
    )
    (root / ".agent/config.json").write_text(json.dumps(config), encoding="utf-8")

    def make(responses):
        runtime, host = READY.runtime_at(root, responses)
        worker = sys.modules["readiness_worker"]
        runtime.__class__ = C.wrap(type(runtime), worker, host)
        return runtime, host

    return make


def test_complete_diagnostics_and_noop_stop(build):
    source = (
        Path(S.read(OLD / "cells-receipt.json")["T2-A1"]["root"])
        / "src/product/code.py"
    ).read_text(encoding="utf-8")
    runtime, host = build([{"replacement": source}, {"replacement": source}])
    report = runtime.run()
    assert "Two unchanged" in report["failure_reason"]
    assert runtime.ledger["effective_edits"] == runtime.ledger["post_edit_checks"] == 0
    assert runtime.validation_count == 1
    request = S.read(runtime.archive.run_root / "proposal-request-1.json")
    facts = host.INTERFACE.restore_literal(request["messages"][1]["content"])
    extra = facts["supplemental_host_diagnostics"]
    assert extra["source_sha256"] == facts["target"]["sha256"]
    assert {c["id"] for c in extra["checks"]} == {"pyright", "actual-observations"}
    assert (
        next(c for c in extra["checks"] if c["id"] == "pyright")["status"] == "failed"
    )
    assert facts["target"]["source"] == source
    assert extra["acceptance_credit"] is False


def test_unit_edit_uses_existing_editor_and_canonical_gate(build):
    base = (
        S.KIT
        / "benchmarks/work/harness-convergence/bounded-evidence-prep-20261018-1/task-preparation-v4"
    )
    source = (base / "private/T2/reference.py").read_text(encoding="utf-8")
    runtime, _host = build([{"replacement": source}])
    report = runtime.run()
    assert report["status"] == "validation_passed_pending_review", report.get(
        "failure_reason"
    )
    assert runtime.host_edits == runtime.ledger["post_edit_checks"] == 1
    gate = F.load(
        runtime.repo_root / ".local-agents/local-unit.py", "behavior_unit_gate_control"
    )
    gate.verify_handoff(runtime.repo_root, report, config=runtime.config)
    target = runtime.repo_root / "src/product/code.py"
    target.write_bytes(target.read_bytes() + b"\n# stale validation control\n")
    with pytest.raises((RuntimeError, ValueError)):
        gate.verify_handoff(runtime.repo_root, report, config=runtime.config)
