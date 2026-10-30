import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import literal_check_feedback as L
import repair_phase_rules as P
import self_audit_rules as A


def facts(edits=1, status="passed"):
    return {
        "target": {"source": "def f(x):\n    return x\n", "sha256": "current"},
        "resource_ledger": {"edits": edits},
        "validation_failure": {
            "status": status,
            "configured_checks": [],
            "source_sha256": "current",
        },
        "supplemental_host_diagnostics": {"checks": []},
        "required_behavior": ["original hard contract"],
    }


def test_only_verified_post_edit_state_requests_audit():
    assert A.render(facts()).startswith("HOST TASK: Review")
    assert A.render(facts(0)) == P.render(facts(0))
    assert A.render(facts(status="failed")) == P.render(facts(status="failed"))


def test_audit_preserves_contract_source_and_original_evidence():
    original = facts()
    assert L.restore(A.render(original).split("\n", 1)[1]) == original
    assert A.SCHEMA == P.SCHEMA
    assert set(A.SCHEMA["properties"]) == {"replacement", "blocked_reason"}
