"""Explicit optional-field control; no assumption that every failed test returns None."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import behavior_unit_candidate as V1
import behavior_unit_candidate_v2 as V2
import behavior_unit_trial as T
import bounded_evidence_readiness as READY
import bounded_evidence_support as S


def test_optional_none_view_does_not_mutate_original(tmp_path):
    row = S.read(T.BATCH / "cells.json")["T1-B2"]
    root = READY.clone(row, tmp_path)
    source = (root / "src/product/code.py").read_text(encoding="utf-8")
    runtime, host = READY.runtime_at(root, [{"replacement": source}, {"replacement": source}])
    runtime.__class__ = V2.wrap(V1.wrap(type(runtime), sys.modules["readiness_worker"], host))
    original_validate = runtime.host_validate
    originals = []

    def seeded_optional_field():
        result = original_validate()
        runtime.validation.configured_checks = None
        originals.append(runtime.validation)
        return result

    runtime.host_validate = seeded_optional_field
    result = runtime.run()
    assert "Two unchanged" in result["failure_reason"]
    assert runtime.validation is originals[0]
    assert runtime.validation.configured_checks is None
    assert runtime.ledger["requests"] == 2 and runtime.ledger["effective_edits"] == 0
    request = S.read(runtime.archive.run_root / "proposal-request-1.json")
    facts = host.INTERFACE.restore_literal(request["messages"][1]["content"])
    assert facts["validation_failure"]["status"] == "failed"
    assert facts["supplemental_host_diagnostics"]["source_sha256"] == facts["target"]["sha256"]
