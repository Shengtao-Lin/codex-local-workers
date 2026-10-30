"""A wire adapter must not discard current-source static diagnostic evidence."""

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / ".local-agents"))
sys.path.insert(0, str(KIT / "benchmarks"))
import bounded_evidence_support as S
import limited_family_trial as L
from bounded import compatibility_profile as PROFILE
from bounded import static_focus_rules as BASE
from bounded import tagged_wire
from test_installable_bounded import archive, project, run


def selected():
    return PROFILE.proposal_rules({"bounded_compatibility_profile": "flat-v1"}, BASE)


def test_flat_profile_retains_exact_existing_diagnostic_callback():
    rules = selected()
    assert getattr(rules, "diagnostics", None) is BASE.diagnostics
    assert rules.SCHEMA is tagged_wire.SCHEMA
    assert rules.PROMPT == tagged_wire.PROMPT
    assert rules.guard is BASE.guard
    assert PROFILE.proposal_rules({}, BASE) is BASE


def test_profile_does_not_invent_diagnostics_when_base_has_none():
    base = SimpleNamespace(
        **{
            key: getattr(BASE, key)
            for key in (
                "IMPORT_CEILING",
                "PROMPT",
                "SCHEMA",
                "decode",
                "guard",
                "materialize",
                "shape",
                "render",
            )
        }
    )
    rules = PROFILE.proposal_rules({"bounded_compatibility_profile": "flat-v1"}, base)
    assert not hasattr(rules, "diagnostics")


@pytest.mark.parametrize(
    "invalid", [None, "hash", "path", "readonly", "line", "changed"]
)
def test_forwarded_diagnostics_retain_all_existing_version_scope_checks(
    tmp_path, invalid
):
    path, digest = "src/product/code.py", "current-hash"
    hint = {"check_id": "ruff-check", "path": path, "line": 2, "rule": "F841"}
    binding = {"path": path, "sha256": digest, "source": "def f():\n    unused = 1\n"}
    focused = {"input_facts": {path: {"sha256": digest}}, "inputs_unchanged": True}
    modify = [path]
    if invalid == "hash":
        focused["input_facts"][path]["sha256"] = "stale"
    elif invalid == "path":
        hint["path"] = "tests/protected.py"
    elif invalid == "readonly":
        modify = []
    elif invalid == "line":
        hint["line"] = 99
    elif invalid == "changed":
        focused["inputs_unchanged"] = False
    runtime = SimpleNamespace(
        repo_root=tmp_path,
        packet={"scope": {"modify": modify}},
        validation=SimpleNamespace(
            configured_checks=[{"id": "ruff-check"}], focused_tests=focused
        ),
        _configured_check_repair_hint=lambda _checks: hint,
    )
    rules = selected()
    assert hasattr(rules, "diagnostics"), (
        "Flat adapter discarded the diagnostic provider"
    )
    actual = rules.diagnostics(runtime, binding)
    if invalid is not None:
        assert actual == []
    else:
        assert actual[0]["source_sha256"] == digest
        assert actual[0]["current_line"] == "    unused = 1"
        assert actual[0]["rule"] == "F841"


def test_installed_flat_error_then_repair_exposes_current_diagnostic():
    with tempfile.TemporaryDirectory(prefix="flat-diagnostic-") as directory:
        root = Path(directory)
        project(root, "labels", "flat-diagnostic-offline")
        config_path = root / ".agent/config.json"
        config = S.read(config_path)
        config["bounded_compatibility_profile"] = "flat-v1"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        correct = L.TASKS["labels"]["reference"]
        broken = correct.replace(
            "    result = dict(defaults)", "    unused = 1\n    result = dict(defaults)"
        )
        result = run(
            root, [{"kind": "replacement", "content": p} for p in (broken, correct)]
        )
        assert result.returncode == 0, result.stdout + result.stderr
        request = S.read(archive(root) / "proposal-request-2.json")
        text = request["messages"][1]["content"]
        assert "CURRENT_STATIC_DIAGNOSTIC\n" in text
        diagnostic, _ = json.JSONDecoder().raw_decode(
            text.split("CURRENT_STATIC_DIAGNOSTIC\n", 1)[1]
        )
        assert diagnostic[0]["rule"] == "F841"
        assert diagnostic[0]["path"] == "src/product/code.py"
        assert diagnostic[0]["source_sha256"] == request["binding"]["sha256"]
        assert diagnostic[0]["current_line"].strip() == "unused = 1"
        report = S.read(root / ".agent/unit-report.json")
        actual = report["consolidated_harness"]["actual"]
        assert actual["edits"] == actual["post_edit_checks"] == 2
        assert actual["initial_checks"] == 1
        assert actual["model_requests"] == 0
        summary = S.read(root / ".agent/unit-summary.json")
        assert summary["reviewer_input_authenticated"] is True
        assert summary["reviewer_started"] is False
