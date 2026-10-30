import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "benchmarks"))
sys.path.insert(0, str(KIT / ".local-agents"))
from bounded import tagged_wire
from strata_subagent_rules import coder_arguments, select


def rules():
    return select(
        SimpleNamespace(
            **{k: getattr(tagged_wire, k) for k in ("PROMPT", "SCHEMA", "decode")}
        )
    )


@pytest.mark.parametrize("kind", ["replacement", "blocked"])
def test_existing_proposals_unchanged(kind):
    raw = json.dumps({"kind": kind, "content": "def f(): return 1"})
    assert rules().decode(raw) == tagged_wire.decode(raw)


@pytest.mark.parametrize(
    "action",
    [
        {"kind": "read", "path": "src/a.py", "start_line": 1, "end_line": 40},
        {"kind": "search", "path": "tests/a.py", "query": "test_"},
    ],
)
def test_evidence_decodes_to_existing_guarded_executor(action):
    result, removed = rules().decode(json.dumps(action))
    assert result == {action["kind"]: {k: v for k, v in action.items() if k != "kind"}}
    assert removed == []


@pytest.mark.parametrize(
    "raw",
    [
        '{"kind":"shell","content":"echo bad"}',
        '{"kind":"read","kind":"blocked","content":"x"}',
        '{"kind":"read","path":"src/a.py","start_line":1,"end_line":2,"content":"write"}',
        '{"kind":"finish","content":"pass"}',
        '{"kind":"replacement","content":"def f(): pass","path":"elsewhere.py"}',
    ],
)
def test_mixed_unknown_and_duplicate_actions_rejected(raw):
    with pytest.raises(ValueError):
        rules().decode(raw)


def test_route_removes_only_reviewer_dispatch_arguments():
    original = [
        "--mode",
        "unit",
        "--packet",
        "p",
        "--config",
        "c",
        "--report",
        "r",
        "--review-report",
        "rr",
        "--summary",
        "s",
        "--compact-output",
    ]
    args, routed = coder_arguments(original)
    assert routed and args == [
        "--mode",
        "coder",
        "--packet",
        "p",
        "--config",
        "c",
        "--report",
        "r",
    ]
    assert original[1] == "unit"


def test_offline_preflight_not_routed_or_promoted():
    args = ["--mode", "preflight", "--report", "r"]
    assert coder_arguments(args) == (args, False)


def test_schema_and_prompt_do_not_mutate_base():
    before = json.dumps(tagged_wire.SCHEMA, sort_keys=True)
    candidate = rules()
    assert len(candidate.SCHEMA["oneOf"]) == 3
    assert json.dumps(tagged_wire.SCHEMA, sort_keys=True) == before
    assert "read" not in tagged_wire.SCHEMA["properties"]["kind"]["enum"]
