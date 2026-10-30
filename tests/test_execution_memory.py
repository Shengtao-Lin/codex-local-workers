import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from execution_memory import ExecutionMemory


def validation(status="failed"):
    return SimpleNamespace(
        configured_checks=[{"id": "pyright", "status": status}],
        focused_tests={"status": "passed"},
    )


def counts(request=0, edits=0, noops=0, errors=0):
    return {
        "requests": request,
        "edits": edits,
        "noops": noops,
        "protocol_recoveries": errors,
        "post_edit_checks": edits,
    }


def binding(source="def f(x): return x", sha="old"):
    return {"source": source, "sha256": sha}


def test_first_request_has_no_invented_history():
    m = ExecutionMemory()
    assert m.observe(binding(), validation(), None, counts())["recent_attempts"] == []


def test_real_edit_is_bound_and_status_change_is_not_semantic_success():
    m = ExecutionMemory()
    m.observe(binding(), validation(), None, counts())
    state = m.observe(
        binding("def f(x: int): return x", "new"),
        validation("passed"),
        None,
        counts(1, 1),
    )
    event = state["recent_attempts"][0]
    assert event["source_before"] == "old" and event["source_after"] == "new"
    assert event["observed_counts"]["post_edit_checks"] == 1
    assert event["check_status_changes"]["pyright"] == {
        "before": "failed",
        "after": "passed",
    }
    assert "+def f(x: int)" in event["diff_excerpt"]
    assert "do not prove" in event["interpretation"]


def test_noop_and_protocol_recovery_are_not_edits():
    m = ExecutionMemory()
    m.observe(binding(), validation(), None, counts())
    event = m.observe(binding(), validation(), "no_op", counts(1, noops=1))[
        "recent_attempts"
    ][0]
    assert event["observed_counts"]["edits"] == 0
    assert event["diff_excerpt"] == ""
    event = m.observe(
        binding(), validation(), "invalid JSON", counts(2, noops=1, errors=1)
    )["recent_attempts"][-1]
    assert event["observed_counts"]["protocol_recoveries"] == 1
    assert event["observed_counts"]["post_edit_checks"] == 0


def test_recent_history_bounded_and_no_aliasing_or_duplicate_observation():
    m = ExecutionMemory()
    for n in range(8):
        state = m.observe(binding(), validation(), None, counts(n, noops=n))
    assert len(state["recent_attempts"]) == 3
    assert state["older_attempts_omitted"] == 4
    state["recent_attempts"].clear()
    again = m.observe(binding(), validation(), None, counts(7, noops=7))
    assert len(again["recent_attempts"]) == 3 and again["attempts_recorded"] == 7
