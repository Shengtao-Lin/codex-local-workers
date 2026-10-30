import copy
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reviewer_execution_phase_v2_adapter import execution_tools, install
from test_reviewer_execution_phase import runtime


def schema(name):
    return {
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


def test_report_only_nudge_restores_only_missing_approved_commands():
    narrowed = [schema("REPORT")]
    original = copy.deepcopy(narrowed)
    base = [
        schema(name)
        for name in (
            "REPORT",
            "RUN_APPROVED_TEST",
            "RUN_APPROVED_STATIC_CHECK",
            "SAFE_REPLACE",
        )
    ]
    pending = [{"id": "ruff", "action": "RUN_APPROVED_STATIC_CHECK"}]
    result = execution_tools(narrowed, pending, base)
    assert len(result) == 1
    assert result[0]["function"]["name"] == "RUN_APPROVED_STATIC_CHECK"
    assert result[0]["function"]["parameters"]["properties"]["check_id"]["enum"] == [
        "ruff"
    ]
    assert narrowed == original
    assert execution_tools([], pending, base) == result


def test_actual_wrapper_report_only_request_is_nonempty_and_restores_client():
    seen = []
    narrowed = [schema("REPORT")]

    class Runtime:
        def __init__(self):
            state = runtime()
            self.config, self.approved_execution = (
                state.config,
                state.approved_execution,
            )
            self.approved_execution_catalog = state.approved_execution_catalog
            self.client = SimpleNamespace(native_tools=narrowed, complete=self.complete)

        def complete(self, messages):
            seen.append(copy.deepcopy(self.client.native_tools))
            return "unchanged model response"

        def run(self):
            return self.client.complete([])

    reviewer = SimpleNamespace(
        ReviewerRuntime=Runtime,
        REVIEW_NATIVE_TOOLS=[
            schema(name) for name in ("RUN_APPROVED_TEST", "RUN_APPROVED_STATIC_CHECK")
        ],
    )
    install(reviewer)
    instance = Runtime()
    assert instance.run() == "unchanged model response"
    assert seen[0] and all(
        item["function"]["name"].startswith("RUN_APPROVED") for item in seen[0]
    )
    assert instance.client.native_tools is narrowed
    assert not instance.approved_execution
