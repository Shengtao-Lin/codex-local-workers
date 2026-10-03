from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
SPEC = importlib.util.spec_from_file_location(
    "guardrail_stability_fixture", ROOT / "benchmarks" / "stability_e2e.py"
)
assert SPEC is not None and SPEC.loader is not None
STABILITY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = STABILITY
SPEC.loader.exec_module(STABILITY)


def test_guardrail_case_is_distinct_pinned_and_baseline_red(tmp_path: Path) -> None:
    case = next(item for item in STABILITY.CASES if item.name == "guardrail-casefold")
    assert case.risk == "high"
    assert case.target == "src/agent_runtime/hooks/guardrails.py"
    source_config = json.loads(
        (ROOT / ".local-agents" / "config.json").read_text(encoding="utf-8-sig")
    )
    workspace = tmp_path / "guardrail-casefold"
    STABILITY.prepare(case, workspace, source_config)
    baseline = STABILITY.run_command(
        workspace,
        [sys.executable, "-m", "pytest", "tests/test_guardrail_casefold.py", "-q"],
        90,
    )
    assert baseline.returncode != 0
    assert "test_mixed_case_phrase_blocks" in baseline.stdout
    static = STABILITY.run_command(
        workspace, [sys.executable, "-m", "ruff", "check", "src", "tests"], 90
    )
    assert static.returncode == 0
