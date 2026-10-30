"""Prove policy provenance and exact preservation of every frozen task fact."""

import copy
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_semantic_policy as D
import reviewer_semantic_entry as V1
import reviewer_semantic_greedy as OLD
import reviewer_semantic_policy as A
import test_reviewer_semantic_entry as S


def create(root, request, config, suffix, adapter):
    module = D.R.load(
        root / ".local-agents/reviewer-runtime.py", "policy_control_" + suffix
    )
    return adapter.install(module)(
        root, {**request, "review_id": "offline-" + suffix}, config, S.Client(module)
    ), module


def test_all_twenty_fresh_roots_only_add_canonical_definition_field():
    rows = D.B.read(D.BATCH / "registration.json")["cells"]
    assert len(rows) == 20
    for row in rows:
        root = Path(row["root"])
        D.R.assert_files(root, row["files"])
        D.R.assert_files(Path(row["origin"]), row["origin_files"])
        assert row["identity"]["review_id"].startswith("policy-v1-")
        assert not (root / ".agent/current-task.json").exists()
        config = D.B.read(root / ".agent/experiment-config.json")
        before, _ = create(root, row["identity"], config, row["id"] + "-before", OLD)
        after, module = create(root, row["identity"], config, row["id"] + "-after", A)
        initial, changed = before.bundle(), after.bundle()
        values = changed.pop("verdict_definitions")
        assert initial == changed
        assert set(values) == V1.VERDICTS
        assert values == A.definitions(before.system_prompt(), module.ReviewError)
        canonical = dict(
            line[2:].split(": ", 1)
            for line in before.system_prompt().splitlines()
            if line.startswith("- ") and ": " in line
        )
        assert values["required_test_gap"] == canonical["required_test_gap"]
        assert canonical["consistent"] in values["satisfied"]
        assert (
            canonical["optional_test_gap"].replace(
                "unverified_claims", "uncertainties with contract_id=null"
            )
            in values["satisfied"]
        )
        assert after.max_turns == before.max_turns == 16
        assert after.max_protocol_errors == before.max_protocol_errors == 4
        assert after.client.native_tools == before.client.native_tools
        for path, digest in row["same_session_control"].items():
            assert D.B.sha(Path(path)) == digest


def test_missing_original_policy_fails_closed_without_handwritten_fallback():
    with pytest.raises(ValueError, match="definitions missing"):
        A.definitions("- consistent: correct.\n", ValueError)


@pytest.mark.parametrize(
    "kind,decision",
    [
        ("satisfied", "pass_to_primary"),
        ("implementation_defect", "rework"),
        ("contract_conflict", "escalate"),
    ],
)
def test_full_wire_keeps_greedy_decode_system_schema_and_states(
    tmp_path, kind, decision
):
    request = S.H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = D.R.load(
        D.E.D.BATCH / "runtime/reviewer-runtime.py", "policy_wire_" + tmp_path.name
    )
    client = module.WORKER.LMStudioClient(
        "http://127.0.0.1:1/v1",
        "stub",
        max_tokens=4096,
        temperature=1,
        native_tools=copy.deepcopy(module.REVIEW_NATIVE_TOOLS),
        structured_output=False,
    )
    client.preflight = lambda: None
    client.probe_structured_output = lambda: "native"
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
    seen = []

    def urlopen(request, **_):
        seen.append(json.loads(request.data))
        return io.BytesIO(
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"action": "REPORT", "arguments": S.judgment(kind)}
                                )
                            },
                            "finish_reason": "stop",
                        }
                    ]
                }
            ).encode()
        )

    with patch.object(module.WORKER.urllib.request, "urlopen", side_effect=urlopen):
        report = runtime.run()
    assert len(seen) == 1 and seen[0]["temperature"] == 0
    assert seen[0]["messages"][0]["content"] == V1.SYSTEM
    assert seen[0]["tools"] == V1.TOOLS
    assert (
        set(json.loads(seen[0]["messages"][1]["content"])["verdict_definitions"])
        == V1.VERDICTS
    )
    assert (
        report["decision"] == decision
        and report["semantic_policy_protocol"] == A.PROTOCOL
    )
