import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from strata_native_feedback import FeedbackProjection


def facts(sha="old", source="import os\n\ndef f():\n    return 1\n"):
    return {
        "target": {"path": "src/a.py", "symbol": "f", "sha256": sha, "source": source},
        "required_behavior": ["IMMUTABLE_CONTRACT"],
        "validation_failure": {"status": "failed", "source_sha256": sha},
        "protocol_feedback": None,
    }


def observation(sha="same"):
    return {
        "request": {"read": {"path": "src/a.py"}},
        "hashes": {"src/a.py": sha},
        "observation": {"source": "evidence"},
    }


def test_full_contract_only_initial_and_read_feedback_has_no_full_snapshot():
    p = FeedbackProjection()
    first = p.project(
        facts(), {"resource_ledger": {"requests": 1}}, "FULL_MODULE_CONTRACT"
    )
    assert first["task_material"] == "FULL_MODULE_CONTRACT"
    context = {
        "source_sha256": "old",
        "resource_ledger": {"requests": 2},
        "evidence_observations": [observation()],
    }
    before = copy.deepcopy(context)
    second = p.project(facts(), context, "FULL_MODULE_CONTRACT")
    assert "task_material" not in second and "current_target" not in second
    assert second["evidence_observations"] == [observation()]
    assert second["resource_ledger"]["requests"] == 2 and context == before


def test_edit_feedback_has_current_function_failure_hash_not_old_contract():
    p = FeedbackProjection()
    p.project(facts(), {}, "contract")
    updated = facts(
        "new", "import os\n\ndef other(): return 8\n\ndef f():\n    return 2\n"
    )
    result = p.project(updated, {}, "contract")
    assert result["current_target"]["sha256"] == "new"
    assert result["current_target"]["source"] == "def f():\n    return 2\n"
    assert result["current_target"]["start_line"] == 5
    assert result["validation_failure"]["source_sha256"] == "new"
    assert "task_material" not in result


def test_repeated_observation_omitted_but_new_version_kept():
    p = FeedbackProjection()
    p.project(facts(), {"evidence_observations": [observation()]}, "contract")
    assert (
        p.project(facts(), {"evidence_observations": [observation()]}, "contract")[
            "evidence_observations"
        ]
        == []
    )
    assert p.project(
        facts(), {"evidence_observations": [observation("changed")]}, "contract"
    )["evidence_observations"] == [observation("changed")]


def test_noop_or_protocol_failure_still_gets_feedback_without_edit():
    p = FeedbackProjection()
    p.project(facts(), {}, "contract")
    f = facts()
    f["protocol_feedback"] = "no_op: current proposal unchanged"
    result = p.project(f, {}, "contract")
    assert result["protocol_feedback"].startswith("no_op")
    assert "current_target" not in result
