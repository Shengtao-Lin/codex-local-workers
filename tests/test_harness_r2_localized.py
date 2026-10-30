"""Real frozen-draft controls, without a model or acceptance credit."""
import json
import shutil
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r2_localized as trial


@pytest.fixture
def root(tmp_path):
    for folder in ("src", "tests"):
        shutil.copytree(trial.B.FIXTURE / folder, tmp_path / folder,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copyfile(trial.B.LONG / trial.B.SOURCE, tmp_path / trial.B.SOURCE)
    shutil.copyfile(trial.B.FIXTURE / "pyproject.toml", tmp_path / "pyproject.toml")
    (tmp_path / ".agent").mkdir()
    for name in ("packet.json", "config.json"):
        shutil.copyfile(trial.B.LONG / ".agent" / name, tmp_path / ".agent" / name)
    return tmp_path


def diagnostics(root):
    return [{"filename": str(root / trial.B.SOURCE), "code": "E501",
             "location": {"row": line, "column": 101},
             "message": f"Line too long ({size} > 100)"}
            for line, size in ((84, 156), (90, 150))]


def facts():
    return {"checks": [{"exit_code": 0, "stdout": ""}, {"exit_code": 0, "stdout": ""},
                       {"exit_code": 1, "stdout": "Full raw two-error output"},
                       {"exit_code": 0, "stdout": ""}]}


def test_only_failure_representation_changes(root):
    old = json.loads(trial.old.messages_for(root, "minimal", facts())[1]["content"])
    messages = trial.localized_messages(root, facts(), diagnostics(root))
    candidate = json.loads(messages[1]["content"])
    assert messages[0] == trial.old.messages_for(root, "minimal", facts())[0]
    assert {k: v for k, v in old.items() if k != "validation_failure"} == {
        k: v for k, v in candidate.items() if k != "validation_failure"}
    assert len(candidate["target"]["source"]) == 648
    errors = candidate["validation_failure"]["diagnostics"]
    lines = (root / trial.B.SOURCE).read_text().splitlines()
    assert [(e["line"], e["column"]) for e in errors] == [(84, 101), (90, 101)]
    for error in errors:
        assert error["current_source_line"] == lines[error["line"] - 1]
        assert error["source_sha256"] == trial.B.sha(root / trial.B.SOURCE)


@pytest.mark.parametrize("bad", ["missing", "scope", "rule", "location"])
def test_missing_or_unbound_error_prevents_live_render(root, bad):
    errors = diagnostics(root)
    if bad == "missing":
        errors.pop()
    elif bad == "scope":
        errors[0]["filename"] = str(root / "tests/test_get_many.py")
    elif bad == "rule":
        errors[0]["code"] = "F821"
    else:
        errors[0]["location"]["row"] = 85
    with pytest.raises(ValueError):
        trial.localized_messages(root, facts(), errors)


def test_archived_actual_feedback_was_complete_and_bound():
    for arm in ("minimal", "formal"):
        for repeat in range(1, 4):
            case = trial.PREVIOUS / "cases" / f"failed-draft-{arm}-{repeat}"
            request = trial.B.read(case / "request.json")["body"]
            body = json.loads(request["messages"][1]["content"])
            failure = body["validation_failure"]
            assert "156 > 100" in failure["output"] and "150 > 100" in failure["output"]
            assert "84:101" in failure["output"] and "90:101" in failure["output"]
            assert failure["source_sha256"] == body["target"]["sha256"]
            assert len(body["target"]["source"]) == 648
            packet = trial.B.read(case / "isolated/.agent/packet.json")
            contract = body if arm == "minimal" else body["packet"]
            assert all(contract[k] == packet[k] for k in trial.CHECK_KEYS)


@pytest.mark.parametrize("change", ["correct", "partial", "noop", "stale", "signature", "neighbor"])
def test_real_patch_controls(root, tmp_path, change):
    module = trial.old.load_runtime()
    before = (root / trial.B.SOURCE).read_bytes()
    block = trial.B.method(before.decode("utf-8-sig"))
    # Reference is control-only, never included in model requests.
    edited = block
    for line in block.splitlines():
        if len(line) > 100:
            if change == "partial" and "\"\"\"" in line:
                continue
            indent = line[:len(line) - len(line.lstrip())]
            edited = edited.replace(line, textwrap.fill(line.strip(), width=96,
                                                       initial_indent=indent, subsequent_indent=indent))
    args = {"path": trial.B.SOURCE, "expected_sha256": trial.B.sha(root / trial.B.SOURCE),
            "find": block, "replace": edited}
    if change == "noop":
        args["replace"] = block
    elif change == "stale":
        args["expected_sha256"] = "0" * 64
    elif change == "signature":
        args["replace"] = edited.replace("source_trace_ids: list[str]", "source_trace_ids: str")
    elif change == "neighbor":
        args["replace"] += "\n    def unrelated(self):\n        return 1\n"
    lock = module.RepoWriteLock(root, "localized-offline-" + change)
    lock.acquire()
    try:
        if change in ("correct", "partial"):
            trial.old.apply_proposal(module, root, json.dumps(args), trial.B.sha(root / trial.B.SOURCE), lock)
            evidence = trial.old.checks(root, tmp_path, "control-" + change)
            assert evidence["junit"]["all_behavior_pass"]
            assert [r["exit_code"] for r in evidence["checks"]] == ([0, 0, 0, 0] if change == "correct" else [0, 0, 1, 0])
        else:
            with pytest.raises((ValueError, module.SafeEditError)):
                trial.old.apply_proposal(module, root, json.dumps(args), trial.B.sha(root / trial.B.SOURCE), lock)
            assert (root / trial.B.SOURCE).read_bytes() == before
    finally:
        lock.release()
