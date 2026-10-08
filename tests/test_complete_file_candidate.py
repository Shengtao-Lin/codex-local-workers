import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from complete_file_candidate import prepare_patch  # noqa: E402


def test_default_off_and_explicit_normalization():
    raw = "Explanation\n```python\nx=1\n```\nDone."
    with pytest.raises(ValueError):
        prepare_patch(raw, ["a.py"])
    patch, metadata = prepare_patch(raw, ["a.py"], enabled=True)
    assert metadata["normalized"] and metadata["original_error"]
    assert patch == [{"path": "a.py", "content": "x = 1\n"}]


@pytest.mark.parametrize(
    "raw",
    [
        "```python\nx=1\n```\n```python\nx=2\n```",
        "```sh\necho bad\n```",
        "Explanation\n```python\nx=(\n```",
        "x=1\n```python\nx=2",
        '{"action":"RUN","arguments":{}}',
    ],
)
def test_ambiguous_invalid_and_wrong_language_not_dispatched(raw):
    # A Python dict expression is data, not a runtime tool action; no dispatcher exists.
    if raw.startswith('{"action"'):
        patch, metadata = prepare_patch(raw, ["a.py"], enabled=True)
        assert isinstance(ast.parse(patch[0]["content"]).body[0], ast.Expr)
        assert not metadata["normalized"]
    else:
        with pytest.raises((ValueError, SyntaxError)):
            prepare_patch(raw, ["a.py"], enabled=True)


@pytest.mark.parametrize(
    "files",
    [
        [{"path": "../a.py", "content": "x=1"}, {"path": "b.py", "content": "y=2"}],
        [{"path": "a.py", "content": "x=1"}, {"path": "a.py", "content": "x=2"}],
        [{"path": "a.py", "content": "x=1"}],
    ],
)
def test_no_scope_or_path_repair(files):
    with pytest.raises(ValueError):
        prepare_patch(
            "Text\n```json\n" + json.dumps({"files": files}) + "\n```",
            ["a.py", "b.py"],
            enabled=True,
        )


def test_multi_file_format_keeps_ast():
    files = [{"path": "a.py", "content": "x=1\n"}, {"path": "b.py", "content": "y=2\n"}]
    patch, _ = prepare_patch(
        json.dumps({"files": files}), ["a.py", "b.py"], enabled=True
    )
    assert [ast.dump(ast.parse(f["content"])) for f in files] == [
        ast.dump(ast.parse(f["content"])) for f in patch
    ]
