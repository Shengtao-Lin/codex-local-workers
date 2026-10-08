"""Formal-contract transfer needs passing references and failing close mutants."""

import importlib.util
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREFLIGHT = load(KIT / "tests/test_role_qualification_cases.py", "shared_role_preflight")
CASES = load(KIT / "benchmarks/role_contract_transfer_cases.py", "contract_transfer_cases")
CORPUS, ORACLES = CASES.corpus(PREFLIGHT.TEMPLATE)


@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda case: case["case_id"])
def test_transfer_reference_and_mutants(case, tmp_path):
    PREFLIGHT.assert_reference_and_mutants(case, ORACLES[case["case_id"]], tmp_path)
