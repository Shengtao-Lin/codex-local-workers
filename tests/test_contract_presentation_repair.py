import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import contract_presentation_repair as experiment  # noqa: E402
from presentation_repair_audit import extract  # noqa: E402


def test_offline_extraction_does_not_repair_code_or_paths():
    assert (
        extract("Explanation\n```python\nx = 1\n```\nDone", ["a.py"])[0]["content"]
        == "x = 1\n"
    )
    with pytest.raises(ValueError):
        extract("```python\nx=1\n```\n```python\nx=2\n```", ["a.py"])
    with pytest.raises(ValueError):
        extract(
            'Text\n```json\n{"files":[{"path":"wrong.py","content":"x=1"}]}\n```',
            ["a.py", "b.py"],
        )


def test_render_preserves_contents_and_contract():
    payload = {
        "contract": "exact int only; exclude bool",
        "writable": ["a.py"],
        "files": {"a.py": 'x = "a\\b"\n', "tests/test_a.py": "assert True\n"},
    }
    assert json.loads(experiment.render(payload, "json")) == payload
    text = experiment.render(payload, "sections")
    assert payload["contract"] in text
    for p, contents in payload["files"].items():
        assert f"--- {p} ---\n{contents}" in text
    with pytest.raises(ValueError):
        experiment.render(payload, "unknown")


@pytest.mark.parametrize(
    "result,eligible",
    [
        ({"semantic_pass": False, "validation": {}}, True),
        ({"semantic_pass": None, "error": "decode"}, False),
        ({"semantic_pass": True, "validation": {"static_pass": False}}, False),
        ({"semantic_pass": False}, False),
    ],
)
def test_only_observed_semantic_failures_get_repair(result, eligible):
    assert experiment.repair_eligible(result) is eligible


def test_multi_decode_is_all_or_nothing():
    raw = json.dumps(
        {
            "files": [
                {"path": "a.py", "content": "a=1"},
                {"path": "b.py", "content": "b=2"},
            ]
        }
    )
    patch, fenced = experiment.decode(raw, ["a.py", "b.py"])
    assert len(patch) == 2 and not fenced
    assert experiment.decode("```json\n" + raw + "\n```", ["a.py", "b.py"])[1]
    with pytest.raises(ValueError):
        experiment.decode(raw, ["a.py", "c.py"])
