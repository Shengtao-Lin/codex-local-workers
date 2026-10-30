"""Within-call recovery, factual provenance and unchanged semantic gates."""

import copy
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_bounded_recovery as D
import reviewer_bounded_recovery as A
import reviewer_fixed_observations as F
import reviewer_observed_facts as OLD
import reviewer_semantic_entry as V1
import test_reviewer_semantic_entry as S


def make(tmp_path, replies):
    request = S.H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = D.R.load(
        D.E.D.BATCH / "runtime/reviewer-runtime.py", "bounded_" + tmp_path.name
    )
    client = S.Client(module)
    client.temperature = 1
    client.seen_choices = []
    pending = iter(replies)

    def complete(messages):
        client.calls += 1
        client.messages.append(copy.deepcopy(messages))
        client.seen_choices.append(client.native_tool_choice)
        item = next(pending)
        if item == "cap":
            raise module.WORKER.ModelRequestError(
                "output_token_limit", "cap", {"max_output_tokens": 4096}
            )
        if isinstance(item, str):
            raise module.WORKER.ModelRequestError(item, item, {})
        return json.dumps(item)

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


def report(kind="satisfied"):
    return {"action": "REPORT", "arguments": S.judgment(kind)}


def test_one_cap_recovers_without_partial_reasoning_or_new_budget(tmp_path):
    runtime, _, client = make(tmp_path, ["cap", report()])
    with patch.object(F, "facts", return_value=([], None)):
        result = runtime.run()
    assert result["decision"] == "pass_to_primary"
    assert result["reviewer_model_calls"] == client.calls == 2
    assert result["semantic_report_turns"] == 1
    assert result["output_limit_failures"] == result["shared_error_budget_used"] == 1
    assert (
        result["recovered_from_output_limit"] and result["first_request_output_capped"]
    )
    assert client.seen_choices == ["auto", "required"]
    assert client.native_tool_choice == "auto" and client.temperature == 1
    assert (
        client.messages[1][-1]["content"] == client.messages[0][-1]["content"] + A.NUDGE
    )
    assert (runtime.review_root / "output-limit-failure-1.json").exists()
    assert (
        runtime.max_turns == 16
        and runtime.max_protocol_errors == 4
        and runtime.invocation_timeout == 600
    )
    assert client.native_tools == V1.TOOLS


@pytest.mark.parametrize(
    "failure,calls",
    [
        ("output_token_limit", 2),
        ("http_4xx", 1),
        ("http_5xx", 1),
        ("model_request_timeout", 1),
        ("input_too_large", 1),
    ],
)
def test_second_cap_and_transport_fail_closed_without_retry(tmp_path, failure, calls):
    replies = (
        ["cap", "cap", report()]
        if failure == "output_token_limit"
        else [failure, report()]
    )
    runtime, module, client = make(tmp_path, replies)
    with (
        patch.object(F, "facts", return_value=([], None)),
        pytest.raises(module.WORKER.ModelRequestError),
    ):
        runtime.run()
    assert client.calls == calls
    assert not (runtime.review_root / "completed.json").exists()
    assert client.temperature == 1 and client.native_tool_choice == "auto"


@pytest.mark.parametrize("limit", ["turns", "deadline", "errors"])
def test_recovery_shares_all_original_budgets(tmp_path, limit):
    runtime, module, client = make(tmp_path, ["cap", report()])
    if limit == "turns":
        runtime.max_turns = 1
    elif limit == "errors":
        runtime.protocol_errors = 3
    else:
        complete = client.complete

        def expire(messages):
            try:
                return complete(messages)
            finally:
                runtime.recovery_deadline = 0

        client.complete = expire
    with (
        patch.object(F, "facts", return_value=([], None)),
        pytest.raises(module.ReviewError),
    ):
        runtime.run()
    assert client.calls == 1


def test_invalid_recovered_report_cannot_bypass_original_gates(tmp_path):
    runtime, module, client = make(
        tmp_path, ["cap", {"action": "REPORT", "arguments": {}}] * 4
    )
    with (
        patch.object(F, "facts", return_value=([], None)),
        pytest.raises((module.ReviewError, module.WORKER.ModelRequestError)),
    ):
        runtime.run()
    assert not (runtime.review_root / "completed.json").exists()
    assert client.calls <= 4


def test_source_drift_after_cap_stops_before_recovery(tmp_path):
    runtime, module, client = make(tmp_path, ["cap", report()])
    complete = client.complete

    def drift(messages):
        try:
            return complete(messages)
        finally:
            (tmp_path / "src.py").write_text("VALUE = 9\n", encoding="utf-8")
            runtime._assert_inputs_current = lambda: (_ for _ in ()).throw(
                module.ReviewError("drift")
            )

    client.complete = drift
    with (
        patch.object(F, "facts", return_value=([], None)),
        pytest.raises(module.ReviewError, match="drift"),
    ):
        runtime.run()
    assert client.calls == 1


def test_twenty_fixed_inputs_only_change_empirical_observations_before_live():
    rows = D.B.read(D.BATCH / "registration.json")["cells"]
    assert len(rows) == 20
    increment_facts = []
    for row in rows:
        root = Path(row["root"])
        assert not (root / ".agent/current-task.json").exists()
        assert row["identity"]["review_id"].startswith("bounded-v1-")
        D.R.assert_files(root, row["files"])
        D.R.assert_files(Path(row["origin"]), row["origin_files"])
        bundles = []
        for adapter in (OLD, A):
            module = D.R.load(
                root / ".local-agents/reviewer-runtime.py",
                "bounded_input_" + row["id"] + adapter.__name__,
            )
            client = S.Client(module)
            client.temperature = 1
            runtime = adapter.install(module)(
                root,
                {
                    **row["identity"],
                    "review_id": "offline-" + adapter.__name__ + row["id"],
                },
                D.B.read(root / ".agent/experiment-config.json"),
                client,
            )
            bundles.append(runtime.bundle())
        facts = bundles[1].pop("approved_observations")
        bundles[0].pop("approved_observations")
        assert bundles[0] == bundles[1] and len(facts) == 1
        observation = facts[0]
        assert "did not add or modify project tests" in observation["meaning"]
        assert "expected" not in observation and "verdict" not in observation
        if row["case"].startswith(
            ("optional-coverage", "required-coverage", "conflicting-contract")
        ):
            increment_facts.append(observation)
    assert len(increment_facts) == 6 and all(
        f == increment_facts[0] for f in increment_facts
    )


@pytest.mark.parametrize("change", ["artifact", "source"])
def test_changed_observations_or_sources_rejected(change):
    row = D.B.read(D.BATCH / "registration.json")["cells"][0]
    root = Path(row["root"])
    module = D.R.load(
        root / ".local-agents/reviewer-runtime.py", "bounded_drift_" + change
    )
    runtime = A.install(module)(
        root,
        {**row["identity"], "review_id": "offline-drift-" + change},
        D.B.read(root / ".agent/experiment-config.json"),
        S.Client(module),
    )
    original_sha = F.B.sha
    seal = F.B.read(F.SEAL)
    target = Path(next(iter(seal["pins"]))) if change == "artifact" else root / F.TARGET
    with (
        patch.object(
            F.B,
            "sha",
            side_effect=lambda p: "0" * 64 if Path(p) == target else original_sha(p),
        ),
        pytest.raises(module.ReviewError),
    ):
        runtime.bundle()


def test_cached_actual_outcomes_and_no_observation_as_added_test():
    entries = F.B.read(F.SEAL)["entries"]
    assert len(entries) == 8
    by_family = {}
    for entry in entries:
        fact = entry["observation"]
        by_family.setdefault(fact["profile_id"], []).append(fact)
    assert len(by_family) == 4 and all(len(v) == 2 for v in by_family.values())
    for lookup in by_family["fixed-pure-lookup_or-v1"]:
        assert all(e["fetch_calls"] == ["key"] for e in lookup["examples"])
        assert lookup["examples"][-2]["outcome"] == {
            "kind": "returned",
            "value": "fallback",
        }
    assert {
        v["examples"][-1]["outcome"]["kind"]
        for v in by_family["fixed-pure-lookup_or-v1"]
    } == {"returned", "raised"}
    assert {
        v["examples"][1]["outcome"]["value"]
        for v in by_family["fixed-pure-increment-v1"]
    } == {-1, 3}
    real = by_family["collect-tools-json-observation-v1"]
    statuses = [
        [e["outcome"]["value"][0]["status"] for e in v["examples"]] for v in real
    ]
    assert sorted(statuses) == sorted(
        [["requested"] + ["succeeded"] * 5, ["succeeded"] * 6]
    )
