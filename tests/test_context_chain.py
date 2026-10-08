import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(
        name, KIT / "benchmarks" / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CASE = load("context_chain_case")
OBS = load("context_request_observer")


@pytest.mark.parametrize("hidden", [False, True])
def test_reference_and_hidden_boundary(tmp_path, hidden):
    for relative, text in {
        **CASE.FILES,
        "tests/test_public.py": CASE.PUBLIC_TESTS,
        "tests/test_boundary.py": CASE.BOUNDARY_TEST,
    }.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            CASE.HIDDEN if hidden and relative.endswith("quote.py") else text,
            encoding="utf-8",
        )
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath=["src"]\n', encoding="utf-8"
    )
    public = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "tests/test_public.py", "-q"],
        cwd=tmp_path,
        capture_output=True,
        timeout=30,
        check=False,
    )
    boundary = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "tests/test_boundary.py", "-q"],
        cwd=tmp_path,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert public.returncode == 0, public.stdout
    assert boundary.returncode == int(hidden), boundary.stdout


def test_observer_transparent_eviction_and_exception(tmp_path):
    messages = [
        {
            "role": "user",
            "content": 'OBSERVATION\n{"path":"a.py","content":"1: value = 2","validation_attempt_ref":"v1"}',
        }
    ]
    seen = []

    def complete(client, actual):
        seen.append(actual)
        if not actual:
            raise ValueError("example")
        return "unchanged"

    observer = OBS.Observer(complete, tmp_path / "trace.jsonl")
    assert observer(None, messages) == "unchanged"
    assert seen[0] is messages
    with pytest.raises(ValueError):
        observer(None, [])
    rows = [json.loads(s) for s in observer.path.read_text().splitlines()]
    assert rows[0]["visible_source_lines"] == {"a.py": [1]}
    assert rows[0]["visible_validation_refs"] == ["v1"]
    assert rows[1]["evicted_previously_visible_paths"] == ["a.py"]
    assert rows[1]["status"] == "failed"
    with pytest.raises(FileExistsError):
        OBS.Observer(complete, observer.path)
