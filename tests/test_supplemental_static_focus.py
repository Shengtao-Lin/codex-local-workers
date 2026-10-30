"""Current-epoch supplemental checks must not disappear from repair evidence."""

import copy
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
from bounded import capture_fixture_support as F
from bounded import static_focus_rules as R
from test_installable_bounded import archive, project, run

W = F.load(KIT / ".local-agents/worker-runtime.py", "supplemental_static_parser")


def material(tmp_path):
    path = "src/product/code.py"
    facts = {
        path: {"sha256": "current"},
        "tests/test_contract.py": {"sha256": "protected"},
    }
    check = {
        "id": "ruff-check",
        "status": "failed",
        "exit_code": 1,
        "output_truncated": False,
        "argv": ["python", "ruff"],
        "output": "F841 Local variable `unused` is assigned to but never used\n  --> src/product/code.py:2:5\n",
    }
    runtime = SimpleNamespace(
        repo_root=tmp_path,
        packet={"scope": {"modify": [path]}},
        validation=SimpleNamespace(
            configured_checks=[],
            focused_tests={
                "input_facts": copy.deepcopy(facts),
                "inputs_unchanged": True,
            },
        ),
        extra_checks=[check],
        extra_check_input_facts=copy.deepcopy(facts),
        _validation_facts=lambda: copy.deepcopy(facts),
        _configured_check_repair_hint=W.WorkerRuntime._configured_check_repair_hint,
    )
    return (
        runtime,
        {"path": path, "sha256": "current", "source": "def f():\n    unused = 1\n"},
        facts,
    )


def test_current_supplemental_failure_reuses_existing_parser(tmp_path):
    runtime, binding, _ = material(tmp_path)
    focus = R.diagnostics(runtime, binding)
    assert len(focus) == 1
    assert focus[0]["rule"] == "F841" and focus[0]["source_sha256"] == "current"
    assert focus[0]["current_line"] == "    unused = 1"
    assert "instruction" not in focus[0]


@pytest.mark.parametrize(
    "bad",
    [
        "unbound",
        "stale_epoch",
        "changed_test",
        "changed_source",
        "truncated",
        "timeout",
        "success",
        "boolean_exit",
        "unknown_check",
        "readonly",
        "bad_line",
    ],
)
def test_rejects_untrustworthy_supplemental_focus(tmp_path, bad):
    runtime, binding, facts = material(tmp_path)
    check = runtime.extra_checks[0]
    if bad == "unbound":
        runtime.extra_check_input_facts = None
    elif bad == "stale_epoch":
        runtime.extra_check_input_facts[binding["path"]]["sha256"] = "old"
    elif bad == "changed_test":
        facts["tests/test_contract.py"]["sha256"] = "changed"
    elif bad == "changed_source":
        binding["sha256"] = "new"
    elif bad == "truncated":
        check["output_truncated"] = True
    elif bad == "timeout":
        check["timed_out"] = True
    elif bad == "success":
        check["exit_code"] = 0
    elif bad == "boolean_exit":
        check["exit_code"] = True
    elif bad == "unknown_check":
        check["id"] = "model_supplied_check"
    elif bad == "readonly":
        runtime.packet["scope"]["modify"] = []
    else:
        check["output"] = check["output"].replace(":2:5", ":99:5")
    assert R.diagnostics(runtime, binding) == []


def test_configured_result_takes_precedence_over_duplicate_supplement(tmp_path):
    runtime, binding, _ = material(tmp_path)
    runtime.validation.configured_checks = [{"id": "ruff-check", "status": "passed"}]
    assert R.diagnostics(runtime, binding) == []


def test_installed_mixed_failure_exposes_source_bound_static_focus():
    with tempfile.TemporaryDirectory(prefix="supplemental-focus-") as directory:
        root = Path(directory)
        project(root, "labels", "mixed-static-control")
        config_path = root / ".agent/config.json"
        config = S.read(config_path)
        config["bounded_compatibility_profile"] = "flat-v1"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        correct = L.TASKS["labels"]["reference"]
        broken = correct.replace(
            "    result = dict(defaults)", "    unused = 1\n    result = {}"
        )
        assert broken != correct
        result = run(
            root, [{"kind": "replacement", "content": p} for p in (broken, correct)]
        )
        assert result.returncode == 0, result.stdout + result.stderr
        request = S.read(archive(root) / "proposal-request-2.json")
        text = request["messages"][1]["content"]
        assert "CURRENT_STATIC_DIAGNOSTIC\n" in text
        focus, _ = json.JSONDecoder().raw_decode(
            text.split("CURRENT_STATIC_DIAGNOSTIC\n", 1)[1]
        )
        assert focus[0]["rule"] == "F841"
        assert focus[0]["source_sha256"] == request["binding"]["sha256"]
        diagnostics = S.read(archive(root) / "diagnostics-2.json")
        assert any(
            c["id"] == "ruff-check" and c["exit_code"] == 1
            for c in diagnostics["additional_checks"]
        )
        report = S.read(root / ".agent/unit-report.json")
        assert report["consolidated_harness"]["actual"]["edits"] == 2
        assert report["consolidated_harness"]["actual"]["post_edit_checks"] == 2
        assert report["consolidated_harness"]["actual"]["model_requests"] == 0
        assert S.read(root / ".agent/unit-summary.json")["reviewer_started"] is False
