"""Preflight references and reject mutants before involving local models."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "transfer_cases_test", KIT / "benchmarks/capability_transfer_cases.py"
)
TRANSFER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRANSFER)
TEMPLATE = json.loads(
    (KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text(encoding="utf-8")
)["cases"][0]
CASES, ORACLES = TRANSFER.transfer_cases(TEMPLATE)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["case_id"])
def test_protected_transfer_reference_and_mutants(case, tmp_path):
    for relative, content in case["files"].items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath=["src"]\n[tool.ruff]\nline-length=100\n[tool.ruff.lint]\nselect=["E4","E7","E9","F"]\n',
        encoding="utf-8",
    )
    oracle = ORACLES[case["case_id"]]
    for source, expected in [
        (oracle["reference"], 0),
        *[(mutant, 1) for mutant in oracle["mutants"]],
    ]:
        (tmp_path / "src/product/target.py").write_text(source, encoding="utf-8")
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "tests",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert process.returncode == expected, process.stdout + process.stderr
        if expected == 0:
            subprocess.run(
                [sys.executable, "-m", "ruff", "format", "src", "tests"],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [sys.executable, "-m", "ruff", "check", "src", "tests"],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )


def test_examples_are_bounded_and_do_not_contain_transfer_answers():
    assert (len(TRANSFER.EXAMPLES) + 3) // 4 < 800
    assert all(case["case_id"] not in TRANSFER.EXAMPLES for case in CASES)
    assert "lock.release" not in TRANSFER.EXAMPLES
    assert "deepcopy" not in TRANSFER.EXAMPLES


def test_action_examples_are_legal_and_preserve_toy_error_contract():
    import json

    text = TRANSFER.ACTION_EXAMPLES
    assert (len(text) + 3) // 4 < 800
    assert "lock.release" not in text
    assert "deepcopy" not in text
    actions = [
        json.JSONDecoder().raw_decode(part)[0] for part in text.split("Action: ")[1:]
    ]
    assert [action["action"] for action in actions] == [
        "VALIDATE",
        "READ_FILE",
        "SAFE_REPLACE",
        "VALIDATE",
    ]
    edit = actions[2]["arguments"]
    assert set(edit) == {"path", "expected_sha256", "find", "replace"}
    source = "def load_title(record):\n    return record['title'].strip()\n"
    namespace = {}
    exec(source.replace(edit["find"], edit["replace"]), namespace)  # noqa: S102 - fixed Primary-authored toy source
    assert namespace["load_title"]({"title": " title "}) == "title"
    with pytest.raises(ValueError):
        namespace["load_title"]({"title": None})
    with pytest.raises(KeyError):
        namespace["load_title"]({})
