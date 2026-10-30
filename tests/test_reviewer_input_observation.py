"""Offline boundaries for the isolated, default-off observation candidate."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import reviewer_input_observation as P


def action(cases):
    return json.dumps({"action": "SELECT_CASES", "arguments": {"cases": cases}})


@pytest.mark.parametrize(
    "cases",
    [
        [],
        [{"args": ["", ""], "kwargs": {}}],
        [
            {"args": ["{}", "x\ny"], "kwargs": {}},
            {"args": ["bad\nevent", "雪"], "kwargs": {}},
        ],
    ],
)
def test_valid_data(cases):
    assert P.parse(action(cases)) == cases


@pytest.mark.parametrize(
    "cases",
    [
        None,
        {},
        ["x"],
        [{"args": ["x", "y"], "kwargs": {}}] * 3,
        [{"args": ["x", "y"], "kwargs": {}}] * 2,
        [{"args": ["x"], "kwargs": {}}],
        [{"args": [1, "y"], "kwargs": {}}],
        [{"args": ["x" * 129, "y"], "kwargs": {}}],
        [{"args": ["x", "y"], "kwargs": {"shell": "anything"}}],
        [{"args": ["x", "y"], "kwargs": {}, "expected": "answer"}],
    ],
)
def test_invalid_data_rejected(cases):
    with pytest.raises(ValueError):
        P.parse(action(cases))


@pytest.mark.parametrize(
    "raw",
    [
        "{}",
        '{"action":"REPORT","arguments":{}}',
        '{"action":"SELECT_CASES","arguments":{"cases":[],"path":"elsewhere"}}',
    ],
)
def test_no_other_authority(raw):
    with pytest.raises(ValueError):
        P.parse(raw)


def test_single_selection_uses_same_request_error_path_and_never_rerolls(monkeypatch):
    writes, calls, executions = {}, [], []
    responses = iter(
        ["{}", action([{"args": ["x", "y"], "kwargs": {}}]), "report1", "report2"]
    )

    def save(path, value):
        assert str(path) not in writes
        writes[str(path)] = value

    class Base:
        def _request_phase_completion(self, messages, tools, stage):
            calls.append((stage, messages, tools))
            self.actual_requests += 1
            if self.actual_requests > 4:
                raise ValueError("shared budget exhausted")
            return next(responses)

        def reject(self, stage, exc):
            self.errors += 1

    module = SimpleNamespace(RUN_STATE=SimpleNamespace(write_json_once=save))
    cls = P.install(module, Base)
    runtime = cls()
    runtime.review_root = Path("fixed-review")
    runtime.actual_requests, runtime.errors = 0, 0

    def observe(*args):
        executions.append(args)
        return {"outcomes": "data only"}

    monkeypatch.setattr(P, "observe", observe)
    messages = [
        {"role": "system", "content": "original"},
        {"role": "user", "content": "contract"},
    ]
    assert runtime._request_phase_completion(messages, [], "source_review") == "report1"
    assert runtime._request_phase_completion(messages, [], "source_review") == "report2"
    assert [c[0] for c in calls] == [
        "input_selection",
        "input_selection",
        "source_review",
        "source_review",
    ]
    assert len(executions) == 1 and runtime.actual_requests == 4 and runtime.errors == 1
    assert len(writes) == 3
    assert messages[1]["content"] == "contract"
    assert "SUPPLEMENTARY_ACTUAL_INPUT_OBSERVATIONS" in calls[-1][1][1]["content"]
    with pytest.raises(ValueError, match="shared budget"):
        runtime._request_phase_completion(messages, [], "source_review")
