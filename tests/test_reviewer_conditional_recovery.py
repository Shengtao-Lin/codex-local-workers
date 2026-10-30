"""First request unchanged, conditional fallback only, no new budget or authority."""

import copy
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_conditional_recovery as D
import reviewer_bounded_recovery as BASE
import reviewer_conditional_recovery as A
import reviewer_fixed_observations as F
import reviewer_semantic_entry as V1
import test_reviewer_bounded_recovery as S


@pytest.mark.parametrize("capped", [False, True])
def test_only_recovery_changes_strength_and_keeps_all_other_fields(tmp_path, capped):
    request = S.S.H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = D.R.load(
        D.E.D.BATCH / "runtime/reviewer-runtime.py", "conditional_" + str(capped)
    )
    client = S.S.Client(module)
    client.temperature = 1
    seen = []

    def complete(messages):
        seen.append(
            {
                "messages": copy.deepcopy(messages),
                "choice": client.native_tool_choice,
                "tools": copy.deepcopy(client.native_tools),
                "temperature": client.temperature,
            }
        )
        if capped and len(seen) == 1:
            raise module.WORKER.ModelRequestError("output_token_limit", "cap", {})
        return json.dumps(S.report())

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
    with patch.object(F, "facts", return_value=([], None)):
        result = runtime.run()
    assert result["decision"] == "pass_to_primary"
    assert len(seen) == 1 + int(capped)
    assert seen[0]["messages"][0]["content"] == V1.SYSTEM
    assert result["conditional_output_recovery"]["recovery_requests_at_low"] == int(
        capped
    )
    if capped:
        assert seen[1]["messages"][0]["content"] == V1.SYSTEM.replace(
            "strength: medium.", "strength: low."
        )
        assert (
            seen[1]["messages"][1]["content"]
            == seen[0]["messages"][1]["content"] + BASE.NUDGE
        )
        assert seen[1]["choice"] == "required"
    assert all(r["temperature"] == 0 and r["tools"] == V1.TOOLS for r in seen)
    assert (
        runtime.max_turns == 16
        and runtime.max_protocol_errors == 4
        and runtime.invocation_timeout == 600
    )
    assert client.temperature == 1


def test_twenty_first_inputs_unchanged_before_live():
    rows = D.B.read(D.BATCH / "registration.json")["cells"]
    for row in rows:
        root = Path(row["root"])
        assert not (root / ".agent/current-task.json").exists()
        assert row["identity"]["review_id"].startswith("conditional-v1-")
        D.R.assert_files(root, row["files"])
        bundles = []
        for adapter in (BASE, A):
            module = D.R.load(
                root / ".local-agents/reviewer-runtime.py",
                "conditional_bundle_" + row["id"] + adapter.__name__,
            )
            runtime = adapter.install(module)(
                root,
                {
                    **row["identity"],
                    "review_id": "offline-" + adapter.__name__ + row["id"],
                },
                D.B.read(root / ".agent/experiment-config.json"),
                S.S.Client(module),
            )
            bundles.append(runtime.bundle())
        assert bundles[0] == bundles[1]
