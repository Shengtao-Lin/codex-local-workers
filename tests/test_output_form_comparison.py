import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import output_form_comparison as form  # noqa: E402


@pytest.mark.parametrize("arm", ["python", "json"])
def test_fenced_and_plain_have_identical_code(arm):
    code = "def f():\n    return 1\n"
    text = (
        code
        if arm == "python"
        else json.dumps({"files": [{"path": "a.py", "content": code}]})
    )
    plain, removed = form.decode_output(text, arm, ["a.py"])
    fenced, normalized = form.decode_output(f"```{arm}\n{text}\n```", arm, ["a.py"])
    assert not removed and normalized
    assert plain == fenced == [{"path": "a.py", "content": code}]


@pytest.mark.parametrize(
    "text", ["```python\nx", "prefix\n```python\nx\n```", "```python\n```\nx\n```", ""]
)
def test_no_prose_extraction_or_partial_fence(text):
    with pytest.raises(ValueError):
        form.decode_output(text, "python", ["a.py"])


def test_json_never_repairs_quotes_or_accepts_extra_path():
    with pytest.raises(ValueError):
        form.decode_output('```json\n{"files":broken}\n```', "json", ["a.py"])
    with pytest.raises(ValueError):
        form.decode_output(
            json.dumps({"files": [{"path": "../a.py", "content": "x"}]}),
            "json",
            ["a.py"],
        )
    with pytest.raises(ValueError):
        form.decode_output("pass", "python", ["a.py", "b.py"])


def test_pending_and_unevaluated_do_not_count_as_semantic_failure(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(form, "BASE", tmp_path)
    form.write(
        tmp_path / "a-result.json",
        {
            "arm": "json",
            "strict_format_pass": False,
            "semantic_evaluated": False,
            "semantic_pass": None,
        },
    )
    state = form.summary({"cells": [{"id": "a"}, {"id": "b"}]})
    assert state["pending"] == ["b"]
    assert state["arms"]["json"]["semantic_evaluated"] == 0
    assert state["arms"]["json"]["semantic_pass"] == 0
    assert state["coordinator_released"] is False
