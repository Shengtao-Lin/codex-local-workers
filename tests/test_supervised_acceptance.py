"""Read-only real archive replay and adversarial Primary receipt controls."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import supervised_acceptance as A

OLD = A.S.KIT / "benchmarks/work/harness-convergence/function-normal-repeat-20261019-1"


def inputs(cell="single_content-1"):
    root = OLD / "cells" / cell / "isolated"
    name = "normal-function-" + cell
    run = root / ".agent/tasks" / name / "runs" / name
    review = (
        root / ".agent/tasks" / name / "reviews" / ("auto-" + name) / "handoff.json"
    )
    report = A.S.read(review)
    identity = {k: name for k in ("task_id", "unit_id", "run_id")}
    paths = {
        p.relative_to(root).as_posix()
        for p in (
            run / "handoff.json",
            run / "packet.json",
            run / "validation.json",
            run / "cumulative.diff",
            review,
            root / ".agent/config.json",
        )
    } | set(report["runtime_facts"]["observed_read_hashes"])
    paths |= set(A.S.read(run / "post-state.json")["validation_inputs"])
    disposition = {
        "schema_version": 1,
        "authority": "primary",
        "identity": report["identity"],
        "report_sha256": A.S.sha(review),
        "resolution": "cleared",
        "evidence": [
            "OFFLINE CONTROL: historical independent comparison, not new live acceptance"
        ],
        "findings": [
            {
                "finding_id": f["id"],
                "disposition": "nonblocking",
                "evidence": "Legacy/new conversions identical, archived isolated probes confirm",
            }
            for f in report["findings"]
        ],
    }
    primary = {
        "authority": "primary",
        "identity": identity,
        "decision": "accept",
        "reason": "Offline receipt control using historical complete checks; no history changed",
        "assisted": False,
        "takeover": False,
        "complete_profile": True,
        "bindings": {p: A.S.sha(root / p) for p in paths},
        "checks": A.S.read(OLD / "live-results" / cell / "result.json")[
            "independent_checks"
        ],
    }
    return root, name, disposition, primary, report


@pytest.mark.parametrize("cell", ["single_content-1", "request_keys-1"])
def test_actual_archive_full_gate_and_unchanged_history(cell):
    root, name, payload, primary, _ = inputs(cell)
    run = root / ".agent/tasks" / name / "runs" / name
    before = A.S.sha(run / "review.json")
    result = A.evaluate(root, name, name, payload, primary)
    assert result["decision"] == "accept"
    assert result["strict_reviewer_pass"] == (cell == "request_keys-1")
    assert A.S.sha(run / "review.json") == before


@pytest.mark.parametrize(
    "fault",
    [
        "hash",
        "foreign",
        "missing",
        "duplicate",
        "defect",
        "gap",
        "unresolved",
        "contract",
        "resolution",
        "incomplete",
        "read_changed",
        "not_readonly",
        "escalate",
    ],
)
def test_adjudication_fails_closed(fault):
    _, _, payload, _, report = inputs()
    payload, report = copy.deepcopy(payload), copy.deepcopy(report)
    completed = {"decision": "rework"}
    sha = payload["report_sha256"]
    if fault == "hash":
        payload["report_sha256"] = "wrong"
    elif fault == "foreign":
        payload["identity"]["run_id"] = "other"
    elif fault == "missing":
        payload["findings"] = []
    elif fault == "duplicate":
        payload["findings"] *= 2
    elif fault in {"defect", "gap", "unresolved", "contract"}:
        payload["findings"][0]["disposition"] = {
            "defect": "confirmed_defect",
            "gap": "required_test_gap",
            "unresolved": "unresolved",
            "contract": "contract_revision",
        }[fault]
    elif fault == "resolution":
        payload["resolution"] = "unresolved"
    elif fault == "incomplete":
        completed["decision"] = "interrupted"
    elif fault in {"read_changed", "not_readonly"}:
        report["runtime_facts"][
            "inputs_unchanged" if fault == "read_changed" else "read_only"
        ] = False
    else:
        report["decision"] = completed["decision"] = "escalate"
    with pytest.raises(ValueError):
        A.adjudication(report, sha, completed, payload)


@pytest.mark.parametrize(
    "fault",
    [
        "stale",
        "missing_binding",
        "failed_check",
        "no_checks",
        "partial",
        "assisted",
        "takeover",
        "reject",
        "foreign",
    ],
)
def test_primary_cannot_accept_without_current_complete_evidence(fault):
    root, name, payload, primary, _ = inputs()
    if fault == "stale":
        primary["bindings"][".agent/config.json"] = "wrong"
    elif fault == "missing_binding":
        del primary["bindings"][".agent/config.json"]
    elif fault == "failed_check":
        primary["checks"][0]["exit_code"] = 1
    elif fault == "no_checks":
        primary["checks"] = []
    elif fault == "partial":
        primary["complete_profile"] = False
    elif fault in {"assisted", "takeover"}:
        primary[fault] = True
    elif fault == "reject":
        primary["decision"] = "rework"
    else:
        primary["identity"]["run_id"] = "wrong"
    with pytest.raises(ValueError):
        A.evaluate(root, name, name, payload, primary)


def test_failed_coder_gate_cannot_be_dispositioned(monkeypatch):
    root, name, payload, primary, _ = inputs()
    read = A.S.read

    def failed(path):
        value = read(path)
        if Path(path).name == "handoff.json" and "runs" in Path(path).parts:
            value["status"] = "failed"
        return value

    monkeypatch.setattr(A.S, "read", failed)
    with pytest.raises(Exception, match="not ready_for_review"):
        A.evaluate(root, name, name, payload, primary)
