import copy
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from reviewer_execution_phase_adapter import execution_tools, pending_executions


def runtime():
    catalog = {
        "tests": [
            {
                "id": "focused-tests",
                "action": "RUN_APPROVED_TEST",
                "arguments": {"test_id": "focused-tests"},
            }
        ],
        "static_checks": [
            {
                "id": "ruff",
                "action": "RUN_APPROVED_STATIC_CHECK",
                "arguments": {"check_id": "ruff"},
            }
        ],
    }
    return SimpleNamespace(
        config={"reviewer_require_approved_execution": True},
        approved_execution=[],
        approved_execution_catalog=lambda: catalog,
    )


def test_only_real_results_advance_phase_without_executing_or_accepting():
    state = runtime()
    assert len(pending_executions(state)) == 2
    assert not state.approved_execution
    state.approved_execution.append(
        {"kind": "test", "id": "focused-tests", "status": "passed"}
    )
    assert [item["id"] for item in pending_executions(state)] == ["ruff"]
    state.approved_execution.append(
        {"kind": "static_check", "id": "ruff", "status": "passed"}
    )
    assert pending_executions(state) == []


def test_failed_execution_releases_rejection_without_rerun_or_false_pass():
    state = runtime()
    state.approved_execution.append(
        {"kind": "test", "id": "focused-tests", "status": "failed"}
    )
    assert pending_executions(state) == []
    assert state.approved_execution[0]["status"] == "failed"
    state.config["reviewer_require_approved_execution"] = False
    state.approved_execution = []
    assert pending_executions(state) == []


def test_pending_schema_cannot_offer_premature_report_or_unapproved_command():
    tools = [
        {
            "function": {
                "name": name,
                "parameters": {
                    "properties": {
                        "test_id": {"type": "string"},
                        "check_id": {"type": "string"},
                    }
                },
            }
        }
        for name in (
            "READ_FILE",
            "REPORT",
            "ASSESS_CONTRACT",
            "RUN_APPROVED_TEST",
            "RUN_APPROVED_STATIC_CHECK",
        )
    ]
    original = copy.deepcopy(tools)
    pending = pending_executions(runtime())
    selected = execution_tools(tools, pending)
    assert [item["function"]["name"] for item in selected] == [
        "READ_FILE",
        "RUN_APPROVED_TEST",
        "RUN_APPROVED_STATIC_CHECK",
    ]
    assert selected[-1]["function"]["parameters"]["properties"]["check_id"]["enum"] == [
        "ruff"
    ]
    assert tools == original
    assert execution_tools(tools, []) == original
