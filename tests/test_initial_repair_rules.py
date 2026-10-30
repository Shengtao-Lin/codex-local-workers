import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import initial_repair_rules as R
import literal_check_feedback as L
from test_repair_phase_rules import facts as base_facts


def facts(edits):
    result = base_facts(edits)
    result["validation_failure"]["diagnostics"] = []
    return result


def test_initial_failure_is_repair_without_inventing_prior_edits_or_new_facts():
    original = facts(0)
    saved = copy.deepcopy(original)
    text = R.render(original)
    assert text.startswith("HOST TASK: Repair the CURRENT starting implementation")
    assert "No Worker edit has yet occurred" in text
    assert L.restore(text.split("\n", 1)[1]) == saved
    assert original == saved


def test_post_edit_repair_retains_old_header():
    assert R.render(facts(1)).startswith("HOST TASK: Repair the failed checks")


def test_no_false_failure_claim_for_passing_start():
    data = facts(0)
    data["validation_failure"]["status"] = "passed"
    assert R.render(data).startswith("HOST TASK: Implement")
