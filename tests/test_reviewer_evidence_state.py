"""Truthful observation controls; metadata never grants semantic acceptance."""

import copy
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "benchmarks"))
sys.path.insert(0, str(KIT / ".local-agents/tests"))
import harness_r4_evidence as E
import reviewer_evidence_state as A
import test_reviewer_compact_dto as T
import test_reviewer_runtime as H


@pytest.fixture
def runtime(tmp_path):
    request = H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = E.R.load(
        E.D.BATCH / "runtime/reviewer-runtime.py", "evidence_control_" + tmp_path.name
    )
    r = A.install(module)(
        tmp_path,
        request,
        {
            "reviewer_compact_report": True,
            "reviewer_evidence_state": True,
            "reviewer_assessment_protocol": True,
            "reviewer_evidence_ids": True,
            "reviewer_require_source_and_test_reads": True,
        },
        H.FakeClient([]),
    )
    r.review_root.mkdir(parents=True)
    return r, module


def test_same_prompt_schema_and_no_prefetch(runtime):
    r, module = runtime
    base_module = E.R.load(
        E.D.BATCH / "runtime/reviewer-runtime.py", "evidence_base_comparison"
    )
    base = T.A.install(base_module)(
        r.repo_root,
        {**r.request, "review_id": "baseline-comparison"},
        r.config,
        H.FakeClient([]),
    )
    assert r.system_prompt() == base.system_prompt()
    assert module.REVIEW_NATIVE_TOOLS == base_module.REVIEW_NATIVE_TOOLS
    payload = r.initial_payload()
    assert not r.read_lines and not r.evidence_catalog
    state = payload.pop("current_evidence_state")
    payload["identity"]["review_id"] = "baseline-comparison"
    assert payload == base.initial_payload()
    assert not state["required_reads_complete"]
    assert not state["source_read_requirement"]["satisfied"]


def test_test_first_full_file_and_duplicate_keep_source_missing(runtime):
    r, _ = runtime
    r.initial_payload()
    first = r.read_file({"path": "tests/test_example.py"})
    assert (
        first["file_extent"]["at_eof"] and first["file_extent"]["whole_file_displayed"]
    )
    state = first["current_evidence_state"]
    assert state["test_read_requirement"]["satisfied"]
    assert not state["source_read_requirement"]["satisfied"]
    assert not state["required_reads_complete"]
    ledger = copy.deepcopy(r.read_lines)
    repeat = r.read_file({"path": "tests/test_example.py", "end_line": 999})
    assert repeat["status"] == "already_read"
    assert repeat["file_extent"] == first["file_extent"]
    assert r.read_lines == ledger
    assert "required_next_action" not in repeat
    last = r.read_file({"path": "src/example.py"})
    assert last["current_evidence_state"]["required_reads_complete"]


@pytest.mark.parametrize(
    "kind", ["empty", "long", "truncated", "past_eof", "crlf", "partial_tail"]
)
def test_exact_file_extent_without_fabricated_display(runtime, kind):
    r, _ = runtime
    path = r.repo_root / "src/extra.py"
    raw = (
        b""
        if kind == "empty"
        else b"alpha\r\nbeta\r\n"
        if kind == "crlf"
        else b"abc\n" * 200
    )
    path.write_bytes(raw)
    args = {"path": "src/extra.py"}
    if kind == "long":
        args.update(start_line=1, end_line=10)
    if kind == "truncated":
        r.max_output = 10
    if kind == "past_eof":
        args.update(start_line=999, end_line=1000)
    if kind == "partial_tail":
        args.update(start_line=195, end_line=200)
    result = r.read_file(args)
    extent = result["file_extent"]
    total = len(raw.decode().splitlines())
    assert extent["total_lines"] == total and extent["size_bytes"] == len(raw)
    assert extent["source_sha256"] == E.B.sha(path)
    assert extent["whole_file_displayed"] == (kind in {"empty", "crlf"})
    assert extent["at_eof"] == (kind in {"empty", "crlf", "past_eof", "partial_tail"})
    assert extent["unread_line_count"] == total - len(r.read_lines["src/extra.py"])
    if kind == "past_eof":
        assert not result["citation_evidence"] and not r.read_lines["src/extra.py"]
    if kind == "partial_tail":
        assert extent["first_unread_line"] == 1
    assert not result["current_evidence_state"]["required_reads_complete"]


def test_search_does_not_fake_read_and_stale_sources_fail(runtime):
    r, module = runtime
    result = r.search({"query": "VALUE", "path": "src"})
    assert not result["current_evidence_state"]["required_reads_complete"]
    r.read_file({"path": "src/example.py"})
    (r.repo_root / "src/example.py").write_text("VALUE = 3\n", encoding="utf-8")
    with pytest.raises(module.ReviewError, match="changed"):
        r.read_file({"path": "src/example.py"})
    with pytest.raises(module.ReviewError, match="changed"):
        r.evidence_state()


def test_forbidden_and_out_of_scope_still_rejected(runtime):
    r, module = runtime
    for path in (".agent/config.json", "../outside.py", "unknown.py"):
        with pytest.raises((module.ReviewError, module.SAFE_EDIT.SafeEditError)):
            r.read_file({"path": path})
    assert not r.read_lines


@pytest.mark.parametrize(
    "change",
    [
        "uncertain",
        "missing",
        "unknown",
        "duplicate",
        "unread",
        "drift",
        "failed_check",
        "observed_failure",
        "contradiction",
        "missing_finding",
        "injected_index",
    ],
)
def test_all_dto_semantic_negatives_preserved(runtime, change):
    r, _ = runtime
    r.read_file({"path": "src/example.py"})
    r.read_file({"path": "tests/test_example.py"})
    T.test_fail_closed(runtime, change)


def test_report_semantics_and_schema_preserved(runtime):
    r, _ = runtime
    r.read_file({"path": "src/example.py"})
    r.read_file({"path": "tests/test_example.py"})
    T.test_explicit_status_only_and_truthful_host_check_provenance(runtime)
    T.test_defect_and_conflict_preserve_explicit_model_judgments(runtime)
    T.test_schema_template_and_citation_repair_are_consistent(runtime)
    assert r.validate_report(T.report())["evidence_observation_protocol"] == A.PROTOCOL


def test_duplicate_read_guard_still_stops_without_report(tmp_path):
    request = H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = E.R.load(
        E.D.BATCH / "runtime/reviewer-runtime.py", "evidence_duplicate_guard"
    )
    actions = [
        {"action": "READ_FILE", "arguments": {"path": "tests/test_example.py"}}
    ] * 5
    r = A.install(module)(
        tmp_path,
        request,
        {
            "reviewer_compact_report": True,
            "reviewer_evidence_state": True,
            "reviewer_assessment_protocol": True,
            "reviewer_evidence_ids": True,
            "reviewer_require_source_and_test_reads": True,
        },
        H.FakeClient(actions),
    )
    with pytest.raises(module.ReviewError, match="repeated reads made no progress"):
        r.run()
    assert not (tmp_path / ".agent/current-task.json").exists()
    assert not r.required_reads_complete()


def test_actual_cli_uses_existing_http_stub_without_new_model_calls(
    tmp_path, monkeypatch
):
    # Reuse the unchanged three-action CLI control, with only the new opt-in.
    save = T.D.B.save

    def save_config(path, value):
        if path.name == "config.json":
            value = {**value, "reviewer_evidence_state": True}
        return save(path, value)

    monkeypatch.setattr(T.D, "ADAPTER", E.ADAPTER)
    monkeypatch.setattr(T.D.B, "save", save_config)
    T.test_actual_cli_serializes_provenance_with_http_stub(tmp_path)
    result = E.B.read(tmp_path / "result.json")
    assert result["evidence_observation_protocol"] == A.PROTOCOL


def test_original_inputs_and_budgets_are_exact_before_live():
    old = {r["id"]: r for r in E.B.read(E.D.OLD.BATCH / "registration.json")["cells"]}
    rows = E.B.read(E.BATCH / "registration.json")["cells"]
    assert len(rows) == 16 and [r["id"] for r in rows] == list(old)
    for row in rows:
        root = Path(row["root"])
        E.R.assert_files(root, old[row["id"]]["files"])
        config = E.B.read(root / ".agent/experiment-config.json")
        assert config.pop("reviewer_compact_report") and config.pop(
            "reviewer_evidence_state"
        )
        assert config == E.B.read(root / ".agent/config.json")
        assert not (root / ".agent/current-task.json").exists()
        assert row["expected_decision"] == old[row["id"]]["expected_decision"]
