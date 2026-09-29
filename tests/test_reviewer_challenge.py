from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "benchmarks" / "reviewer_challenge.py"
)
SPEC = importlib.util.spec_from_file_location(
    "reviewer_challenge_under_test", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
CHALLENGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHALLENGE)


def test_hidden_bug_score_uses_actual_injected_line(tmp_path: Path) -> None:
    source = tmp_path / "slug.py"
    source.write_text(
        "from src.tag_rules import normalize_words\n\n\n"
        "def normalize_tag(value):\n"
        "    if isinstance(value, str) and len(value) > 100:\n"
        "        return value\n",
        encoding="utf-8",
    )
    report = {
        "decision": "rework",
        "findings": [
            {
                "path": "src/slug.py",
                "line": 5,
                "evidence": "The >100 character early return bypasses normalization.",
            }
        ],
    }
    assert CHALLENGE.caught_hidden_bug(report, source)
    report["findings"][0]["line"] = 3
    assert not CHALLENGE.caught_hidden_bug(report, source)
