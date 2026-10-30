"""Discriminating controls are bound to actual approved test behavior."""

import copy
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import reviewer_discriminating_status as D


def action():
    return {
        "action": "PREDICT_STATUS",
        "arguments": {
            "predictions": [
                {
                    "case_index": i,
                    "status": "succeeded" if i < 6 else "requested",
                    "reason": "Contract/test grounded state.",
                }
                for i in range(8)
            ]
        },
    }


def test_eight_matched_payloads_have_real_discriminating_controls_before_live():
    reg = D.B.read(D.BATCH / "registration.json")
    tests = Path(reg["visible_test_source"]).read_text(encoding="utf-8-sig")
    assert D.B.sha(Path(reg["visible_test_source"])) == reg["visible_test_sha256"]
    negatives = D.negative_cases(tests)["cases"]
    groups = {"blind": [], "source": []}
    for row in reg["cells"]:
        cell = D.BATCH / "cells" / row["id"]
        assert not (cell / "result.json").exists()
        messages = D.B.read(cell / "messages.json")
        assert messages[0]["content"] == D.P.SYSTEM
        body = json.loads(messages[1]["content"])
        assert body["approved_acceptance_tests"] == tests
        assert len(body["event_sequences"]) == 8
        assert [c["input"] for c in body["event_sequences"][6:]] == negatives
        assert all(c["target_call_id"] == "a" for c in body["event_sequences"])
        assert "outcome" not in body and "judge" not in body and "expected" not in body
        groups[row["arm"]].append(body)
    assert all(v == groups["blind"][0] for v in groups["blind"])
    assert all(v == groups["source"][0] for v in groups["source"])
    source = copy.deepcopy(groups["source"][0])
    assert source.pop("unreviewed_implementation")
    assert source == groups["blind"][0]
    assert negatives[0]["parts"][-1] == {
        "type": "tool_call",
        "call_id": "a",
        "name": "new",
        "arguments": {"fresh": True},
    }
    assert negatives[1]["parts"][:-1] == negatives[0]["parts"]
    observed = D.B.read(D.BATCH / "offline-negative-observations/observation.json")
    assert [o["outcome"]["value"][0]["status"] for o in observed["observations"]] == [
        "requested",
        "requested",
    ]
    assert (
        D.B.read(D.BATCH / "judge.json")["statuses"]
        == ["succeeded"] * 6 + ["requested"] * 2
    )
    assert len(set(D.B.read(D.BATCH / "judge.json")["statuses"])) == 2


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "bool_index", "unknown", "blank"]
)
def test_prediction_shapes_still_fail_closed(change):
    value = action()
    rows = value["arguments"]["predictions"]
    if change == "missing":
        rows.pop()
    if change == "duplicate":
        rows[7]["case_index"] = 6
    if change == "bool_index":
        rows[0]["case_index"] = False
    if change == "unknown":
        rows[0]["status"] = "accepted"
    if change == "blank":
        rows[0]["reason"] = " "
    with pytest.raises(ValueError):
        D.validate(json.dumps(value))


def test_constant_predictor_is_not_corrected_and_cannot_pass_judge():
    value = action()
    for row in value["arguments"]["predictions"]:
        row["status"] = "succeeded"
    parsed = D.validate(json.dumps(value))
    assert [r["status"] for r in parsed["arguments"]["predictions"]] != D.B.read(
        D.BATCH / "judge.json"
    )["statuses"]


def test_fixture_extractor_does_not_execute_expressions():
    reg = D.B.read(D.BATCH / "registration.json")
    tests = Path(reg["visible_test_source"]).read_text(encoding="utf-8-sig")
    with pytest.raises(ValueError):
        D.negative_cases(
            tests.replace('arguments={"fresh": True}', "arguments=dangerous()")
        )


def test_real_native_client_roundtrip_eight_rows_same_budget():
    reg = D.B.read(D.BATCH / "registration.json")
    worker = D.P.R.load(
        Path(reg["origin_root"]) / ".local-agents/worker-runtime.py",
        "discriminating_http",
    )
    client = worker.LMStudioClient(
        "http://127.0.0.1:1/v1",
        "meta/muse-glimmer",
        timeout=180,
        max_tokens=4096,
        temperature=0,
        native_tools=D.TOOLS,
        context_length=24576,
    )
    seen = []

    def urlopen(request, **_):
        seen.append(json.loads(request.data))
        return io.BytesIO(
            json.dumps(
                {
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {
                                            "name": "PREDICT_STATUS",
                                            "arguments": json.dumps(
                                                action()["arguments"]
                                            ),
                                        },
                                    }
                                ]
                            },
                        }
                    ]
                }
            ).encode()
        )

    with patch.object(worker.urllib.request, "urlopen", side_effect=urlopen):
        assert (
            D.validate(
                client.complete(D.B.read(D.BATCH / "cells/cell-01/messages.json"))
            )
            == action()
        )
    assert len(seen) == 1 and seen[0]["tools"] == D.TOOLS
    assert seen[0]["max_tokens"] == 4096 and seen[0]["temperature"] == 0
    assert (
        D.P.TOOLS[0]["function"]["parameters"]["properties"]["predictions"]["maxItems"]
        == 6
    )
