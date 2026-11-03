"""Mechanical preparation must never grant semantic or execution authority."""

import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "prepare_return", Path(__file__).parents[1] / "tools/prepare-strata-return.py"
)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def draft(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("def f():\n    return 1\n", encoding="utf-8")
    task = tmp_path / ".agent/tasks/t"
    state = {
        "task_id": "t",
        "status": "ready_for_primary",
        "active": None,
        "pending_model": None,
        "attempts": ["first"],
        "expected_hashes": {"source.py": helper.digest(source)},
        "latest_check": {"sha256": "host-check-digest"},
    }
    put(task / "general/ledger/0001.json", {"state": state})
    put(
        task / "general/contract.json",
        {"material": {"packet": {"required_behavior": [{"id": "c"}]}}},
    )
    put(task / "workflow/runs/first/result.json", {"status": "ready_for_primary"})
    finding = {
        "id": "defect",
        "contract_id": "c",
        "text": "Confirmed counterexample",
        "path": "source.py",
        "line": 2,
    }
    return tmp_path, task, state, finding


def test_binds_host_check_and_exact_indentation_without_writing(draft):
    root, _, _, finding = draft
    before = {
        p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }
    value = helper.build(root, "t", [finding], assisted=True)
    assert value["defect"]["check_sha256"] == "host-check-digest"
    assert value["defect"]["findings"][0]["source"]["quote"] == "    return 1"
    assert value["assisted"] is True
    assert {
        p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
    } == before


def evidence_draft(draft):
    root, task, state, _ = draft
    material = helper.read(task / "general/contract.json")["material"]
    material["packet"]["task_id"] = "t"
    material.update(
        config={"experimental_strata_continuation": "task-v1"},
        policy={"role": "investigate"},
    )
    put(task / "general/contract.json", {"material": material})
    return root, task, state, material


def test_evidence_feedback_passes_actual_frozen_validator(draft, monkeypatch):
    from types import SimpleNamespace

    root, _, state, material = evidence_draft(draft)
    frozen = (
        Path(__file__).parents[1]
        / "releases/strata-task34/product/runtime/.local-agents/strata"
    )
    monkeypatch.syspath_prepend(str(frozen))
    from task_continuation import feedback_shape

    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    value = helper.build_evidence(
        root,
        "t",
        {
            "contract_ids": ["c"],
            "text": "Verify the original question against the current source.",
        },
        assisted=False,
    )
    host = SimpleNamespace(
        config=material["config"],
        packet=material["packet"],
        resume_requested=True,
        ledger=SimpleNamespace(state=state),
        repo_root=root,
        current_hashes=lambda: state["expected_hashes"],
        policy=material["policy"],
    )
    assert feedback_shape(host, value)["status"] == "ready_for_primary"
    assert "defect" not in value and "review_disposition" not in value
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    value["result_sha256"] = "stale"
    with pytest.raises(ValueError, match="Prior workflow result mismatch"):
        feedback_shape(host, value)


@pytest.mark.parametrize(
    "change", ["profile", "role", "consumed", "attempts", "drift", "active"]
)
def test_evidence_requires_existing_unused_bound_route(draft, change):
    root, task, state, material = evidence_draft(draft)
    if change == "profile":
        material["config"].clear()
    if change == "role":
        material["policy"]["role"] = "implement"
    if change == "consumed":
        state["task_followup"] = {"used": True}
    if change == "attempts":
        state["attempts"].append("second")
        put(task / "workflow/runs/second/result.json", {"status": "ready_for_primary"})
    if change == "drift":
        (root / "source.py").write_text("drift", encoding="utf-8")
    if change == "active":
        state["active"] = {"pid": 1}
    put(task / "general/contract.json", {"material": material})
    put(task / "general/ledger/0002.json", {"state": state})
    with pytest.raises(ValueError):
        helper.build_evidence(
            root, "t", {"contract_ids": ["c"], "text": "Verify."}, assisted=False
        )


@pytest.mark.parametrize(
    "evidence_request",
    [
        {"contract_ids": ["other"], "text": "Verify."},
        {"contract_ids": ["c", "c"], "text": "Verify."},
        {"contract_ids": ["c"], "text": ""},
        {"contract_ids": ["c"], "text": "Verify.", "scope": ["outside"]},
    ],
)
def test_evidence_cannot_add_contract_or_scope(draft, evidence_request):
    root, _, _, _ = evidence_draft(draft)
    with pytest.raises(ValueError):
        helper.build_evidence(root, "t", evidence_request, assisted=False)


def test_stale_source_rejected(draft):
    root, _, _, finding = draft
    (root / "source.py").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="no longer matches"):
        helper.build(root, "t", [finding], assisted=True)


@pytest.mark.parametrize("change", ["active", "pending_model", "primary_return"])
def test_active_or_consumed_task_rejected(draft, change):
    root, task, state, finding = draft
    state[change] = {"occupied": True}
    put(task / "general/ledger/0002.json", {"state": state})
    with pytest.raises(ValueError, match="settled"):
        helper.build(root, "t", [finding], assisted=True)


@pytest.mark.parametrize(
    "field,value",
    [
        ("path", "../outside.py"),
        ("contract_id", "other"),
        ("line", 999),
        ("line", True),
    ],
)
def test_scope_contract_and_line_rejected(draft, field, value):
    root, _, _, finding = draft
    finding[field] = value
    with pytest.raises(ValueError):
        helper.build(root, "t", [finding], assisted=True)


def test_no_assumed_assistance_or_duplicate_findings(draft):
    root, _, _, finding = draft
    with pytest.raises(ValueError):
        helper.build(root, "t", [finding], assisted=None)
    with pytest.raises(ValueError):
        helper.build(root, "t", [finding, finding], assisted=True)


def test_existing_output_cannot_be_overwritten(draft, monkeypatch):
    root, _, _, finding = draft
    request, output = root / "findings.json", root / "existing.json"
    put(request, [finding])
    output.write_text("prior immutable evidence", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepare",
            "--project",
            str(root),
            "--task-id",
            "t",
            "--findings",
            str(request),
            "--output",
            str(output),
            "--assistance",
            "assisted",
        ],
    )
    with pytest.raises(FileExistsError):
        helper.main()
    assert output.read_text(encoding="utf-8") == "prior immutable evidence"


def test_nonready_workflow_rejected(draft):
    root, task, _, finding = draft
    put(task / "workflow/runs/first/result.json", {"status": "conflicted"})
    with pytest.raises(ValueError, match="workflow is not ready"):
        helper.build(root, "t", [finding], assisted=True)


def test_unused_optional_create_target_stays_absent(draft):
    root, task, state, finding = draft
    state["expected_hashes"]["optional.py"] = None
    put(task / "general/ledger/0002.json", {"state": state})
    value = helper.build(root, "t", [finding], assisted=True)
    assert value["source_hashes"]["optional.py"] is None
    assert not (root / "optional.py").exists()


def test_unexpected_creation_is_stale_evidence(draft):
    root, task, state, finding = draft
    state["expected_hashes"]["optional.py"] = None
    put(task / "general/ledger/0002.json", {"state": state})
    (root / "optional.py").write_text("unexpected", encoding="utf-8")
    with pytest.raises(ValueError, match="no longer matches"):
        helper.build(root, "t", [finding], assisted=True)


def test_generated_defect_passes_existing_frozen_host_validator(draft, monkeypatch):
    from types import SimpleNamespace

    root, _, state, finding = draft
    frozen = (
        Path(__file__).parents[1]
        / "releases/strata-task34/product/runtime"
        / ".local-agents/strata"
    )
    monkeypatch.syspath_prepend(str(frozen))
    from general_return import record_primary_return

    value = helper.build(root, "t", [finding], assisted=True)
    state["used"] = {"edits": 1}
    host = SimpleNamespace(
        config={},
        resume_requested=True,
        ledger=SimpleNamespace(state=state),
        packet={"required_behavior": [{"id": "c"}]},
        policy={"initial_hashes": state["expected_hashes"], "create": []},
        current_hashes=lambda: state["expected_hashes"],
        submission_state=lambda: {"status": "submission_available"},
        editor=SimpleNamespace(
            read_bytes=lambda path: ((root / path).read_bytes(), None)
        ),
    )
    validated = record_primary_return(host, value["defect"], record=False)
    assert validated["acceptance"] is False
    assert validated["edit_count"] == 1
    assert "primary_return" not in state
