"""Audit existing guards only; no new output parser or live candidate is installed."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / ".local-agents" / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INTERFACE = load("audited_proposal_interface", "proposal-interface.py")
BOUNDARY = load("audited_single_function", "single-function-context.py")
SPEC = {"path": "src/target.py", "symbol": "target", "dependencies": ""}
SOURCE = '''TOKEN = "protected"

def target(value: str) -> str:
    """Keep source quotes and Unicode: 中文."""
    return value

def untouched():
    return TOKEN
'''


def args_for(replacement):
    _, _, _, source = BOUNDARY.target(SOURCE, "target")
    binding = {"path": SPEC["path"], "sha256": "a" * 64, "source": source}
    # Host-generated valid JSON is an audit fixture, NOT a repair of any model
    # response and NOT a proposed raw-code-channel implementation.
    return INTERFACE.terminal_boundary(
        INTERFACE.normalize_whole(json.dumps({"replacement": replacement}), binding)
    )


@pytest.mark.parametrize(
    "body",
    [
        '    """A "quoted" docstring: 中文."""\n    return value\n',
        '    return value + "\\n"\n',
        '    return f"{value}: \\"quoted\\""\n',
    ],
)
def test_legally_encoded_python_retains_quotes_and_guards(body):
    replacement = "def target(value: str) -> str:\n" + body
    args = args_for(replacement)
    assert args["replace"] == replacement
    assert args["expected_sha256"] == "a" * 64
    assert args["path"] == SPEC["path"]
    BOUNDARY.guard(SPEC, SOURCE, args)


@pytest.mark.parametrize(
    "replacement",
    [
        "def other(value: str) -> str:\n    return value\n",
        "def target(value: int) -> str:\n    return str(value)\n",
        "async def target(value: str) -> str:\n    return value\n",
        "def target(value: str) -> str:\n    return value\n\nTOKEN = 'changed'\n",
        "def target(value: str) -> str:\n    return value\n\ndef extra():\n    return 1\n",
        "```python\ndef target(value: str) -> str:\n    return value\n```\n",
    ],
)
def test_existing_guards_reject_scope_signature_and_framing_changes(replacement):
    with pytest.raises((ValueError, SyntaxError)):
        BOUNDARY.guard(SPEC, SOURCE, args_for(replacement))


def test_wrong_target_cannot_be_authorized_by_representation_conversion():
    args = args_for("def target(value: str) -> str:\n    return value.upper()\n")
    args["path"] = "src/other.py"
    with pytest.raises(ValueError, match="path mismatch"):
        BOUNDARY.guard(SPEC, SOURCE, args)


def test_client_schema_and_host_guard_are_distinct_integration_points():
    # Static evidence for the approval decision, not compatibility with a live
    # LM Studio schema implementation. Neither constructor is changed here.
    worker = (ROOT / ".local-agents/worker-runtime.py").read_text(encoding="utf-8")
    host = (ROOT / ".local-agents/host-proposal.py").read_text(encoding="utf-8")
    assert "action_schema: dict[str, Any] | None = None" in worker
    assert "self.action_schema = action_schema or CODER_ACTION_SCHEMA" in worker
    assert '"schema": typed_coder_action_schema(' in worker
    assert 'if config.get("coder_structured_output", True):' in host
    assert "Qualified host proposals require plain JSON transport" in host
