"""T1 failure before static checks must not crash the model request view."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import behavior_unit_candidate as V1
import behavior_unit_candidate_v2 as V2
import behavior_unit_trial as T
import behavior_unit_trial_v2 as TRIAL
import bounded_evidence_readiness as READY
import bounded_evidence_support as S


def test_v2_actual_command():
    assert TRIAL.unit_argv(["python", T.S.KIT / "benchmarks/bounded_evidence_unit.py"])[
        1
    ] == str(T.S.KIT / "benchmarks/behavior_unit_unit_v2.py")


def test_t1_null_view_preserves_failure_and_archive(tmp_path):
    row = S.read(T.BATCH / "cells.json")["T1-B2"]
    root = READY.clone(row, tmp_path)
    source = (root / "src/product/code.py").read_text(encoding="utf-8")
    runtime, host = READY.runtime_at(
        root, [{"replacement": source}, {"replacement": source}]
    )
    runtime.__class__ = V2.wrap(
        V1.wrap(type(runtime), sys.modules["readiness_worker"], host)
    )
    report = runtime.run()
    assert "Two unchanged" in report["failure_reason"]
    # Both are legal legacy representations. The separate injected-None control
    # proves preservation of that branch; do not assume every pytest failure uses it.
    assert runtime.validation.configured_checks in (None, [])
    assert runtime.ledger["requests"] == 2
    assert runtime.ledger["effective_edits"] == 0
    req = S.read(runtime.archive.run_root / "proposal-request-1.json")
    facts = host.INTERFACE.restore_literal(req["messages"][1]["content"])
    assert facts["validation_failure"]["status"] == "failed"
    assert {r["id"] for r in facts["supplemental_host_diagnostics"]["checks"]} == {
        "ruff-format",
        "ruff-check",
        "pyright",
        "actual-observations",
    }
    assert (
        facts["supplemental_host_diagnostics"]["source_sha256"]
        == facts["target"]["sha256"]
    )
