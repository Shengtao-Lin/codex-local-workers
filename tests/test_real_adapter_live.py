"""Validate trial inputs without depending on ignored live run archives."""

import ast
import importlib.util
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCH))
spec = importlib.util.spec_from_file_location(
    "real_live_tests", BENCH / "real_adapter_live.py"
)
live = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = live
spec.loader.exec_module(live)


def test_registered_live_packet_is_bounded_to_one_private_helper():
    assert live.COMMON == "src/evaluation_harness/adapters/common.py"
    tree = ast.parse((live.FROZEN / live.COMMON).read_text(encoding="utf-8"))
    definitions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert {"_datetime", "build_samples", "parse_message", "_sample"} <= definitions
    assert "private timestamp normalization" in live.case()["goal"]
    assert "no broader public API or identity changes" in live.case()["goal"]


def test_live_trial_retains_real_project_rules_and_reference_preflight():
    discovered = set()
    for path in ("tests/test_datetime_trial.py", "tests/unit/test_adapters.py"):
        tree = ast.parse((live.FROZEN / path).read_text(encoding="utf-8"))
        discovered.update(
            path + "::" + node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        )
    assert len(discovered) == 10
    assert set(live.TESTS) == discovered
    project = (live.FROZEN / "pyproject.toml").read_text(encoding="utf-8")
    assert '"ASYNC"' in project and '"RUF"' in project
