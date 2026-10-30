import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import reviewer_semantic_probe as P


def test_payload_is_exact_contract_source_types_tests_diff_without_labels():
    rows = P.B.read(P.BATCH / "registration.json")["cells"]
    assert len(rows) == 4
    for row in rows:
        root = Path(row["origin_root"])
        config = P.B.read(root / ".agent/experiment-config.json")
        messages = P.B.read(P.BATCH / "cells" / row["id"] / "messages.json")
        assert messages[0] == {"role": "system", "content": P.SYSTEM}
        data = json.loads(messages[1]["content"])
        assert set(data) == {
            "hard_contract",
            "implementation",
            "dependency_declarations",
            "focused_tests",
            "actual_cumulative_diff",
        }
        assert (
            data["hard_contract"]
            == P.B.read(root / ".agent/packet.json")["required_behavior"]
        )
        assert data["implementation"] == P.extract(
            (root / P.H.TARGET).read_text(encoding="utf-8"), "collect_tools"
        )
        assert (
            data["dependency_declarations"]
            == config["coder_single_function"]["dependencies"]
        )
        assert data["focused_tests"] == (
            root / "tests/test_collect_tools.py"
        ).read_text(encoding="utf-8")
        packet = P.B.read(root / ".agent/packet.json")
        run = root / ".agent/tasks/semantic-terms/runs" / packet["run_id"]
        assert data["actual_cumulative_diff"] == (run / "cumulative.diff").read_text(
            encoding="utf-8"
        )
        assert "None" not in json.dumps(data["hard_contract"])
        assert "defective" not in messages[1]["content"]
        assert "expected" not in data and "implementation_label" not in data


def test_same_implementation_has_identical_messages_across_repeats():
    rows = P.B.read(P.BATCH / "registration.json")["cells"]
    for source in ("draft", "reference"):
        selected = [r for r in rows if r["implementation"] == source]
        assert len(selected) == 2
        payloads = [
            P.B.read(P.BATCH / "cells" / r["id"] / "messages.json") for r in selected
        ]
        assert payloads[0] == payloads[1]


def test_exact_only_report_tool_no_write_or_acceptance():
    (tool,) = P.TOOLS
    assert tool["function"]["name"] == "REPORT"
    params = tool["function"]["parameters"]
    assert (
        set(params["properties"])
        == set(params["required"])
        == {"verdict", "explanation"}
    )
    assert not params["additionalProperties"]
    assert params["properties"]["verdict"]["enum"] == [
        "satisfies",
        "violates",
        "uncertain",
    ]
    assert "None" not in P.SYSTEM and "None" not in json.dumps(P.TOOLS)
    assert P.B.read(P.BATCH / "registration.json")["no_acceptance_or_holdout_credit"]
