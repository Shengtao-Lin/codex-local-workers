"""Independent feasibility and consumer-before-provider gate checks."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
BASE = KIT / "benchmarks/work/capability-fit/roleq-dependent-retention-2"


def test_frozen_contract_has_passing_reference(tmp_path):
    case = json.loads((BASE / "corpus.json").read_text())["cases"][0]
    for relative, source in case["files"].items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    (tmp_path / "src/product/config.py").write_text(
        """def parse_limit(value):
    if isinstance(value, bool):
        raise ValueError("invalid limit")
    if isinstance(value, str):
        if not value or not value.isascii() or not value.isdigit():
            raise ValueError("invalid limit")
        value = int(value)
    if not isinstance(value, int) or not 1 <= value <= 100:
        raise ValueError("invalid limit")
    return value
""",
        encoding="utf-8",
    )
    (tmp_path / "src/product/report.py").write_text(
        """from product.config import parse_limit


def select_rows(rows, limit):
    return sorted(rows, key=lambda row: row["id"])[:limit]


def build_report(rows, value):
    return select_rows(rows, parse_limit(value))
""",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath=["src"]\n'
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_consumer_cannot_start_without_provider_acceptance():
    sys.path.insert(0, str(KIT / "benchmarks"))
    try:
        spec = importlib.util.spec_from_file_location(
            "dependent_test", KIT / "benchmarks/dependent_retention_chain.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for cell in json.loads((BASE / "manifest.json").read_text())["cells"]:
            cell_root = Path(cell["root"])
            plan = module.read(cell_root / ".agent/feature-plan.json")
            for unit in ("limit-contract", "report-roundtrip"):
                module.load_contract().validate_unit_packet(
                    plan, module.read(cell_root / f".agent/{unit}-bound.json")
                )
        with pytest.raises((ValueError, FileNotFoundError)):
            module.run(2, "report-roundtrip")
        root = Path(
            json.loads((BASE / "manifest.json").read_text())["cells"][1]["root"]
        )
        assert not (root / ".agent/report-roundtrip-started.json").exists()
    finally:
        sys.path.pop(0)
