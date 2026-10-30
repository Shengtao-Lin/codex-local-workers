"""Shared scheduler, untrusted claims and original canonical gates remain strict."""

import copy
import json
import shutil
import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_contract_first as D
import reviewer_contract_first as A
import reviewer_discriminating_status as N
import reviewer_semantic_entry as V1
import reviewer_typed_observations as OLD
import test_reviewer_semantic_entry as S


def profile(status="succeeded"):
    return [
        {
            "profile_id": "collect-tools-json-observation-v1",
            "source": {},
            "examples": [
                {
                    "input": {
                        "parts": [
                            {
                                "type": "tool_call",
                                "call_id": "a",
                                "name": "tool",
                                "arguments": {},
                            },
                            {"type": "tool_result", "call_id": "a", "result": None},
                        ]
                    },
                    "outcome": {
                        "kind": "returned",
                        "value": [{"call_id": "a", "status": status}],
                    },
                }
            ],
        }
    ]


def predict(status="succeeded"):
    return {
        "action": "PREDICT_STATUS",
        "arguments": {
            "predictions": [
                {
                    "case_index": 0,
                    "status": status,
                    "reason": "Explicit model contract judgment.",
                }
            ]
        },
    }


def report(kind="satisfied", observation="consistent"):
    return {
        "action": "REPORT",
        "arguments": {
            **S.judgment(kind),
            "observation_assessments": [
                {
                    "profile_id": "collect-tools-json-observation-v1",
                    "case_index": 0,
                    "contract_id": "behavior-1",
                    "verdict": observation,
                    "explanation": "Explicit model observation assessment.",
                }
            ],
        },
    }


def make(tmp_path, replies):
    request = S.H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = D.R.load(
        D.E.D.BATCH / "runtime/reviewer-runtime.py", "contractfirst_" + tmp_path.name
    )
    client = S.Client(module)
    client.temperature = 1
    pending = iter(replies)
    client.profiles = []

    def complete(messages):
        client.calls += 1
        client.messages.append(copy.deepcopy(messages))
        client.profiles.append(
            {
                "tool": client.native_tools[0]["function"]["name"],
                "choice": client.native_tool_choice,
                "temperature": client.temperature,
            }
        )
        value = next(pending)
        if isinstance(value, str):
            raise module.WORKER.ModelRequestError(value, value, {})
        return json.dumps(value)

    client.complete = complete
    runtime = A.install(module)(
        tmp_path,
        request,
        {
            "reviewer_compact_report": True,
            "reviewer_evidence_state": True,
            "reviewer_assessment_protocol": True,
            "reviewer_evidence_ids": True,
            "reviewer_require_source_and_test_reads": True,
            "reviewer_temperature": 1,
        },
        client,
    )
    return runtime, module, client


def facts(values):
    return patch.object(A.FACTS, "facts", return_value=(values, None)), patch.object(
        A.TYPED,
        "restore",
        side_effect=lambda _runtime, profiles, _error: (profiles, []),
    )


def test_positive_full_run_source_blind_and_total_requests_truthful(tmp_path):
    runtime, _, client = make(tmp_path, [predict(), report()])
    one, two = facts(profile())
    with one, two:
        result = runtime.run()
    assert result["decision"] == "pass_to_primary"
    assert result["reviewer_model_calls"] == client.calls == 2
    assert result["normative_model_calls"] == 1
    first = json.loads(client.messages[0][1]["content"])
    assert set(first) == {
        "hard_contract",
        "dependency_declarations",
        "approved_acceptance_tests",
        "event_sequences",
    }
    assert (
        "observed_status" not in json.dumps(first)
        and "actual_cumulative_diff" not in first
    )
    assert client.messages[0][0]["content"] == A.PREDICT.SYSTEM
    assert client.messages[1][0]["content"] == V1.SYSTEM
    assert (
        client.profiles[0]["tool"] == "PREDICT_STATUS"
        and client.profiles[1]["tool"] == "REPORT"
    )
    assert all(p["temperature"] == 0 for p in client.profiles)
    assert client.temperature == 1 and client.native_tool_choice == "auto"
    assert result["runtime_facts"]["inputs_unchanged"]


def test_explicit_prediction_mismatch_cannot_be_verified_but_no_defect_invented(
    tmp_path,
):
    runtime, _, client = make(
        tmp_path, [predict(), report(), report("contract_conflict", "uncertain")]
    )
    one, two = facts(profile("requested"))
    with one, two:
        result = runtime.run()
    assert result["decision"] == "escalate" and result["findings"] == []
    assert client.calls == 3 and runtime.protocol_errors == 1
    assert (
        "prior explicit model contract prediction" in client.messages[2][1]["content"]
    )


def test_host_does_not_correct_wrong_model_prediction_using_hidden_truth(tmp_path):
    runtime, _, _ = make(tmp_path, [predict("requested"), report()])
    one, two = facts(profile("requested"))
    with one, two:
        result = runtime.run()
    assert (
        result["model_contract_predictions"][0]["model_claimed_required_status"]
        == "requested"
    )
    # This is a mechanical consistency test, not a real semantic capability pass.
    assert result["decision"] == "pass_to_primary"


def test_prediction_and_report_share_error_budget(tmp_path):
    invalid = {"action": "PREDICT_STATUS", "arguments": {}}
    runtime, module, client = make(tmp_path, [invalid] * 10)
    one, two = facts(profile())
    with one, two, pytest.raises(module.ReviewError, match="budget exhausted"):
        runtime.run()
    assert client.calls == runtime.protocol_errors == 4
    assert not (runtime.review_root / "completed.json").exists()


def test_errors_across_both_phases_are_not_reset(tmp_path):
    bad_prediction = {"action": "PREDICT_STATUS", "arguments": {}}
    bad_report = {"action": "REPORT", "arguments": {}}
    runtime, module, client = make(
        tmp_path,
        [bad_prediction, predict(), bad_report, bad_report, bad_report, report()],
    )
    one, two = facts(profile())
    with one, two, pytest.raises(module.ReviewError, match="budget exhausted"):
        runtime.run()
    assert runtime.protocol_errors == 4 and client.calls == 5
    assert not (runtime.review_root / "completed.json").exists()


@pytest.mark.parametrize("limit", ["requests", "deadline", "drift"])
def test_no_extra_request_after_global_budget_or_source_failure(tmp_path, limit):
    runtime, module, client = make(tmp_path, [predict(), report()])
    if limit == "requests":
        runtime.max_turns = 1
    else:
        original = client.complete

        def complete(messages):
            raw = original(messages)
            if limit == "deadline":
                runtime.deadline = 0
            else:
                runtime._assert_inputs_current = lambda: (_ for _ in ()).throw(
                    module.ReviewError("source drift")
                )
            return raw

        client.complete = complete
    one, two = facts(profile())
    with one, two, pytest.raises(module.ReviewError):
        runtime.run()
    assert client.calls == 1


def test_sticky_profile_survives_shape_correction_within_shared_budget(tmp_path):
    malformed = {"action": "REPORT", "arguments": {}}
    runtime, _, client = make(
        tmp_path, [predict(), "output_token_limit", malformed, report()]
    )
    one, two = facts(profile())
    with one, two:
        result = runtime.run()
    assert result["reviewer_model_calls"] == client.calls == 4
    assert result["shared_error_budget_used"] == 2
    assert client.profiles[1]["choice"] == "auto"
    assert client.profiles[2]["choice"] == client.profiles[3]["choice"] == "required"
    assert "Reasoning strength: low." in client.messages[2][0]["content"]
    assert "Reasoning strength: low." in client.messages[3][0]["content"]
    assert (
        runtime.max_turns == 16
        and runtime.max_protocol_errors == 4
        and runtime.invocation_timeout == 600
    )


@pytest.mark.parametrize(
    "failure", ["http_4xx", "http_5xx", "model_request_timeout", "output_token_limit"]
)
def test_transport_not_retried_second_cap_stops(tmp_path, failure):
    replies = (
        ["output_token_limit"] * 3
        if failure == "output_token_limit"
        else [failure, predict()]
    )
    runtime, module, client = make(tmp_path, replies)
    one, two = facts(profile())
    with one, two, pytest.raises(module.WORKER.ModelRequestError):
        runtime.run()
    assert client.calls == (2 if failure == "output_token_limit" else 1)


def test_frozen_twenty_inputs_material_and_order_before_live():
    rows = D.B.read(D.BATCH / "registration.json")["cells"]
    assert [r["id"] for r in rows[:4]] == [
        f"sample-{i:02}-candidate" for i in range(17, 21)
    ]
    normative_reference = json.loads(
        D.B.read(N.BATCH / "cells/cell-01/messages.json")[1]["content"]
    )
    for row in rows:
        root = Path(row["root"])
        assert not (root / ".agent/current-task.json").exists()
        assert row["identity"]["review_id"].startswith("contract-first-v1-")
        D.R.assert_files(root, row["files"])
        bundles = []
        for adapter in (OLD, A):
            module = D.R.load(
                root / ".local-agents/reviewer-runtime.py",
                "contractfirst_input_" + row["id"] + adapter.__name__,
            )
            runtime = adapter.install(module)(
                root,
                {
                    **row["identity"],
                    "review_id": "offline-" + adapter.__name__ + row["id"],
                },
                D.B.read(root / ".agent/experiment-config.json"),
                S.Client(module),
            )
            bundles.append(runtime.bundle())
        assert bundles[0] == bundles[1]
        normative, actual = A.prediction_inputs(runtime, bundles[1], module.ReviewError)
        if row["group"] == "original-sixteen":
            assert normative is None and actual == []
        else:
            reference = copy.deepcopy(normative_reference)
            reference["event_sequences"] = reference["event_sequences"][:6]
            assert normative == reference
            assert len(actual) == 6


def test_actual_main_cli_native_roundtrip_offline(tmp_path, monkeypatch):
    row = D.B.read(D.BATCH / "registration.json")["cells"][0]
    origin = Path(row["root"])
    root = tmp_path / "isolated"
    for relative in row["files"]:
        dest = root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin / relative, dest)
    request = {**row["identity"], "review_id": "offline-contract-first-cli"}
    request_path = tmp_path / "request.json"
    D.B.save(request_path, request)
    output = tmp_path / "report.json"
    module = D.R.load(root / ".local-agents/reviewer-runtime.py", "contractfirst_cli")
    A.install(module)
    seen = []
    owner = "r4-collect_tools"

    def urlopen(request, **_):
        import io

        body = json.loads(request.data)
        seen.append(body)
        name = body["tools"][0]["function"]["name"]
        if name == "PREDICT_STATUS":
            args = {
                "predictions": [
                    {
                        "case_index": i,
                        "status": "succeeded",
                        "reason": "Model normative test fixture.",
                    }
                    for i in range(6)
                ]
            }
        else:
            args = {
                "obligations": [
                    {
                        "id": owner,
                        "verdict": "implementation_defect",
                        "evidence_ids": ["E2"],
                        "explanation": "Recognized ToolResultPart(None) remains requested under line214 guard, violating exact result and succeeded requirement.",
                        "line": 214,
                        "fix": "Remove None guard and update every recognized result.",
                        "severity": "high",
                    }
                ],
                "uncertainties": [],
                "observation_assessments": [
                    {
                        "profile_id": "collect-tools-json-observation-v1",
                        "case_index": i,
                        "contract_id": owner,
                        "verdict": "violation" if i == 0 else "consistent",
                        "explanation": "None update missing."
                        if i == 0
                        else "Exact result/status preserved.",
                    }
                    for i in range(6)
                ],
            }
        return io.BytesIO(
            json.dumps(
                {
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "tool_calls": [
                                    {
                                        "id": "call-cli",
                                        "type": "function",
                                        "function": {
                                            "name": name,
                                            "arguments": json.dumps(args),
                                        },
                                    }
                                ]
                            },
                        }
                    ]
                }
            ).encode()
        )

    monkeypatch.chdir(root)
    with (
        patch.object(
            sys,
            "argv",
            [
                str(root / ".local-agents/reviewer-runtime.py"),
                "--request",
                str(request_path),
                "--config",
                str(root / ".agent/experiment-config.json"),
                "--report",
                str(output),
            ],
        ),
        patch.object(
            module.WORKER.MODEL_RESIDENCY,
            "role_model_lease",
            side_effect=lambda *_: nullcontext(),
        ),
        patch.object(module.WORKER.LMStudioClient, "ensure_loaded", return_value=None),
        patch.object(module.WORKER.LMStudioClient, "preflight", return_value=None),
        patch.object(
            module.WORKER.LMStudioClient,
            "probe_structured_output",
            return_value="native",
        ),
        patch.object(module.WORKER.urllib.request, "urlopen", side_effect=urlopen),
    ):
        module.main()
    result = D.B.read(output)
    assert result["decision"] == "rework"
    assert result["reviewer_model_calls"] == len(seen) == 2
    assert all(body["max_tokens"] == 4096 and body["temperature"] == 0 for body in seen)
    assert "actual_cumulative_diff" not in json.loads(seen[0]["messages"][1]["content"])
    D.R.assert_files(root, row["files"])
