"""Fail-closed slot coverage; neither omission nor guided recovery restores a gate."""

import sys
from pathlib import Path

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
import qualification_matrix_status as STATUS  # noqa: E402


def complete():
    cases = (
        "display-default",
        "public-fields",
        "lookup-fallback",
        "async-first-present",
        "label-rollup",
        "async-receipt",
    )
    units = [
        {"id": f"{c}-r{r}/{u}", "accepted_initial": True}
        for c in cases
        for r in (1, 2)
        for u in (
            ("collect-unit", "qual-unit") if c == "async-receipt" else ("qual-unit",)
        )
    ]
    explorers = [
        {"id": f"{c}-r{r}", "success": True}
        for c in ("label-rollup", "async-receipt")
        for r in (1, 2)
    ]
    controls = [
        {"id": f"{c}-{v}-r{r}", "effective": True}
        for c in ("display-default", "lookup-fallback")
        for v in ("a", "b")
        for r in (1, 2)
    ]
    chains = [{"id": f"async-receipt-r{r}", "passed": True} for r in (1, 2)]
    return units, explorers, controls, chains


def test_all_exact_slots_required():
    assert STATUS.qualified(*complete())
    assert not STATUS.qualified([], [], [], [])


def test_missing_failed_unit_cannot_shrink_denominator():
    evidence = list(complete())
    evidence[0].pop()
    assert not STATUS.qualified(*evidence)


def test_duplicate_pass_cannot_replace_missing_slot():
    evidence = list(complete())
    evidence[0][-1] = dict(evidence[0][0])
    assert not STATUS.qualified(*evidence)


def test_recovery_does_not_replace_initial_failure():
    evidence = list(complete())
    evidence[0][0].update(accepted_initial=False, guided_recovery_accepted=True)
    assert not STATUS.qualified(*evidence)


def test_failed_explorer_or_hidden_control_or_chain_blocks_gate():
    for index, key in ((1, "success"), (2, "effective"), (3, "passed")):
        evidence = list(complete())
        evidence[index][0][key] = False
        assert not STATUS.qualified(*evidence)
