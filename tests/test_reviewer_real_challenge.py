from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
SPEC = importlib.util.spec_from_file_location(
    "reviewer_real_challenge_under_test", BENCHMARKS / "reviewer_real_challenge.py"
)
assert SPEC is not None and SPEC.loader is not None
CHALLENGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHALLENGE)


def test_caught_bug_requires_real_source_line_and_contract(tmp_path: Path) -> None:
    source = tmp_path / "selection.py"
    source.write_text(
        "def select_records():\n"
        "    if policy.seed == 0:\n"
        "        return ordered[: policy.limit]\n",
        encoding="utf-8",
    )
    finding = {
        "path": CHALLENGE.TARGET,
        "line": 2,
        "contract_id": "random-seed",
        "evidence": "seed zero bypasses shuffle",
    }
    report = {"decision": "rework", "findings": [finding]}
    assert CHALLENGE.caught_bug(report, source)
    assert not CHALLENGE.caught_bug({**report, "decision": "pass_to_primary"}, source)
    assert not CHALLENGE.caught_bug(
        {**report, "findings": [{**finding, "line": 20}]}, source
    )
    assert not CHALLENGE.caught_bug(
        {**report, "findings": [{**finding, "contract_id": "other"}]}, source
    )


def test_metadata_variant_requires_prefixed_key_branch(tmp_path: Path) -> None:
    source = tmp_path / "models.py"
    source.write_text(
        "def validate_metadata(value):\n"
        '    if key.startswith("x-"):\n'
        "        continue\n",
        encoding="utf-8",
    )
    finding = {
        "path": CHALLENGE.RUNTIME_TARGET,
        "line": 2,
        "contract_id": "metadata-key-bounds",
        "evidence": "x- prefix bypasses metadata key validation",
    }
    report = {"decision": "rework", "findings": [finding]}
    assert CHALLENGE.caught_bug(report, source, "metadata")
    assert not CHALLENGE.caught_bug(
        {**report, "findings": [{**finding, "path": CHALLENGE.TARGET}]},
        source,
        "metadata",
    )


def test_clean_control_requires_pass_without_findings() -> None:
    assert CHALLENGE.clean_control_passed(
        {"decision": "pass_to_primary", "findings": []}
    )
    assert not CHALLENGE.clean_control_passed({"decision": "rework", "findings": []})
    assert not CHALLENGE.clean_control_passed(
        {"decision": "pass_to_primary", "findings": [{"id": "spurious"}]}
    )
    for key in ("", "a" * 128, "a" * 129):
        assert (not key or len(key) > 128) == (not key or 128 < len(key))
