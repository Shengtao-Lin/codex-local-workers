"""Preflight unseen supervised tasks without starting models."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "role_cases", KIT / "benchmarks/role_qualification_cases.py"
)
CASES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CASES)
TEMPLATE = json.loads(
    (KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text(encoding="utf-8")
)["cases"][0]
CORPUS, ORACLES = CASES.corpus(TEMPLATE)


@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda c: c["case_id"])
def test_reference_passes_and_initial_mutant_fails(case, tmp_path):
    assert_reference_and_mutants(case, ORACLES[case["case_id"]], tmp_path)


def assert_reference_and_mutants(case, oracle, tmp_path):
    for path, text in case["files"].items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath=["src"]\n[tool.ruff]\nline-length=100\ntarget-version="py311"\n[tool.ruff.lint]\nselect=["E4","E7","E9","F"]\n',
        encoding="utf-8",
    )
    for sources, expected in [
        (oracle["reference"], 0),
        *[(m, 1) for m in oracle["mutants"]],
    ]:
        for path, text in sources.items():
            (tmp_path / path).write_text(text, encoding="utf-8")
        checked = subprocess.run(
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
        assert checked.returncode == expected, checked.stdout + checked.stderr
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
