import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import literal_check_feedback as L
import repair_phase_rules as R


def facts(edits):
    return {
        "target": {"source": "def f(x):\n    return x\n", "sha256": "bound"},
        "resource_ledger": {"edits": edits},
        "validation_failure": {
            "status": "failed",
            "source_sha256": "bound",
            "configured_checks": [
                {"id": "type", "status": "failed", "output": "exact failure\nline 8"}
            ],
            "focused_tests": {"passed_test_ids": ["test_ok"]},
        },
        "supplemental_host_diagnostics": {"checks": []},
        "required_behavior": ["unchanged contract"],
    }


def test_failed_start_is_not_misrepresented_as_post_edit_repair():
    assert R.render(facts(0)).startswith("HOST TASK: Implement")


def test_real_edit_failure_selects_repair_and_preserves_all_facts():
    original = facts(1)
    saved = copy.deepcopy(original)
    result = R.render(original)
    assert result.startswith("HOST TASK: Repair")
    assert L.restore(result.split("\n", 1)[1]) == saved
    assert original == saved
