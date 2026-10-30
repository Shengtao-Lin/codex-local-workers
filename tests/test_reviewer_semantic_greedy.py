"""Only effective decoding changes; actual wire and all trusted gates retained."""

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_semantic_greedy as D
import reviewer_semantic_entry as V1
import reviewer_semantic_greedy as A
import test_reviewer_semantic_entry as S


def test_twenty_matched_inputs_and_config_not_rewritten_before_live():
    rows = D.B.read(D.BATCH / "registration.json")["cells"]
    assert len(rows) == 20
    for row in rows:
        root = Path(row["root"])
        D.R.assert_files(root, row["files"])
        D.R.assert_files(Path(row["origin"]), row["origin_files"])
        assert row["identity"]["review_id"].startswith("greedy-v1-")
        assert not (root / ".agent/current-task.json").exists()
        config = D.B.read(root / ".agent/experiment-config.json")
        assert config["reviewer_temperature"] == 1
        assert config["reviewer_model"] == "meta/muse-glimmer"
        assert config["reviewer_max_tokens"] == 4096
        assert config["reviewer_context_length"] == 24576
        assert config == D.B.read(Path(row["origin"]) / ".agent/experiment-config.json")
        for path, digest in row["same_session_control"].items():
            assert D.B.sha(Path(path)) == digest


def make(tmp_path, temperature=1):
    request = S.H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = D.R.load(
        D.E.D.BATCH / "runtime/reviewer-runtime.py", "greedy_control_" + tmp_path.name
    )
    client = module.WORKER.LMStudioClient(
        "http://127.0.0.1:1/v1",
        "stub-reviewer",
        max_tokens=4096,
        temperature=temperature,
        native_tools=module.REVIEW_NATIVE_TOOLS,
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
    return runtime, module, client


@pytest.mark.parametrize(
    "kind,decision",
    [
        ("satisfied", "pass_to_primary"),
        ("implementation_defect", "rework"),
        ("contract_conflict", "escalate"),
    ],
)
def test_actual_http_request_temperature_only_and_original_states(
    tmp_path, kind, decision
):
    runtime, module, client = make(tmp_path)
    seen = []
    args = S.judgment(kind)

    def urlopen(request, **_):
        body = json.loads(request.data)
        seen.append(body)
        return io.BytesIO(
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"action": "REPORT", "arguments": args}
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
    assert len(seen) == 1
    assert seen[0]["temperature"] == 0 and seen[0]["max_tokens"] == 4096
    assert seen[0]["messages"][0]["content"] == V1.SYSTEM
    assert report["decision"] == decision
    assert report["reviewer_decoding_experiment"]["effective_temperature"] == 0
    assert (
        report["reviewer_decoding_experiment"]["archived_temperature"]
        == client.temperature
        == 1
    )
    assert runtime.config["reviewer_temperature"] == 1


def test_failed_model_call_restores_client_and_does_not_create_pass(tmp_path):
    runtime, module, client = make(tmp_path)
    with (
        patch.object(
            client,
            "complete",
            side_effect=module.WORKER.WorkerError("stub transport failure"),
        ),
        pytest.raises(module.WORKER.WorkerError),
    ):
        runtime.run()
    assert client.temperature == 1
    assert not (runtime.review_root / "completed.json").exists()


def test_other_origin_temperature_is_not_silently_accepted(tmp_path):
    runtime, module, _ = make(tmp_path, temperature=0.5)
    with pytest.raises(module.ReviewError, match="temperature-one origin"):
        runtime.run()
