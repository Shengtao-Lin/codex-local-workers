import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "supervised_candidate_audit",
    Path(__file__).resolve().parents[1] / "benchmarks/supervised_candidate_audit.py",
)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


@pytest.fixture
def rework_fixture(tmp_path):
    runs = tmp_path / ".agent/tasks/task/runs"
    initial, terminal = runs / "unit-a1", runs / "unit-a2"
    initial.mkdir(parents=True)
    terminal.mkdir()
    parent = {
        "task_id": "task",
        "feature_id": "feature",
        "unit_id": "unit",
        "run_id": "unit-a1",
        "attempt": 1,
        "packet_revision": 1,
        "plan_revision": 1,
        "risk": {"unit": "high"},
        "scope": {"modify": ["source.py"]},
        "focused_tests": ["test_source.py"],
        "required_behavior": [{"id": "b1", "text": "Reject None"}],
    }
    child = copy.deepcopy(parent)
    child.update(
        run_id="unit-a2",
        attempt=2,
        packet_revision=2,
        parent_run_id="unit-a1",
        preserve_contract=True,
        review_feedback=[{"finding_id": "none-001"}],
    )
    preimage = terminal / "preimage.py"
    preimage.write_text("rejected source\n", encoding="utf-8")
    digest = hashlib.sha256(preimage.read_bytes()).hexdigest()
    records = {
        initial / "packet.json": parent,
        initial / "review.json": {"decision": "rework"},
        initial / "handoff.json": {
            "changed_files": [{"path": "source.py", "final_sha256": digest}]
        },
        terminal / "packet.json": child,
        terminal / "preimages.json": [
            {
                "path": "source.py",
                "sha256": digest,
                "archive_path": preimage.relative_to(tmp_path).as_posix(),
            }
        ],
    }
    for path, value in records.items():
        path.write_text(json.dumps(value), encoding="utf-8")
    selection = {
        "task_id": "task",
        "unit_id": "unit",
        "initial_run_id": "unit-a1",
        "run_id": "unit-a2",
    }
    return tmp_path, initial, terminal, selection


def test_primary_rework_selection_preserves_initial_decision(rework_fixture):
    root, initial, terminal, selection = rework_fixture
    assert AUDIT.select_primary_rework(root, initial, selection) == terminal
    assert AUDIT.load(initial / "review.json")["decision"] == "rework"


@pytest.mark.parametrize(
    "field", ["risk", "scope", "focused_tests", "required_behavior"]
)
def test_primary_rework_cannot_change_contract_or_tests(rework_fixture, field):
    root, initial, terminal, selection = rework_fixture
    child = AUDIT.load(terminal / "packet.json")
    child[field] = "changed"
    (terminal / "packet.json").write_text(json.dumps(child), encoding="utf-8")
    with pytest.raises(ValueError, match="preserved Primary"):
        AUDIT.select_primary_rework(root, initial, selection)


def test_primary_rework_requires_rejected_initial_run(rework_fixture):
    root, initial, _, selection = rework_fixture
    (initial / "review.json").write_text('{"decision":"accept"}', encoding="utf-8")
    with pytest.raises(ValueError, match="immutable Primary rework"):
        AUDIT.select_primary_rework(root, initial, selection)


def test_primary_rework_rejects_wrong_parent_and_tampered_preimage(rework_fixture):
    root, initial, terminal, selection = rework_fixture
    child = AUDIT.load(terminal / "packet.json")
    child["parent_run_id"] = "other"
    (terminal / "packet.json").write_text(json.dumps(child), encoding="utf-8")
    with pytest.raises(ValueError, match="contract-preserving child"):
        AUDIT.select_primary_rework(root, initial, selection)
    child["parent_run_id"] = "unit-a1"
    (terminal / "packet.json").write_text(json.dumps(child), encoding="utf-8")
    (terminal / "preimage.py").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="preimage archive was modified"):
        AUDIT.select_primary_rework(root, initial, selection)


def test_primary_rework_rejects_path_escape(rework_fixture):
    root, initial, _, selection = rework_fixture
    selection["run_id"] = "../other/unit-a2"
    with pytest.raises(ValueError, match="escapes original task"):
        AUDIT.select_primary_rework(root, initial, selection)


@pytest.fixture
def takeover_fixture(rework_fixture):
    root, initial, terminal, selection = rework_fixture
    source = root / "source.py"
    source.write_text("corrected source\n", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    image = terminal / "preimage.py"
    image.write_bytes(source.read_bytes())
    images = AUDIT.load(terminal / "preimages.json")
    before = images[0]["sha256"]
    images[0]["sha256"] = digest
    (terminal / "preimages.json").write_text(json.dumps(images), encoding="utf-8")
    (terminal / "handoff.json").write_text('{"changed_files":[]}', encoding="utf-8")
    failed = initial.parent / "unit-a3"
    failed.mkdir()
    (failed / "review.json").write_text('{"decision":"takeover"}', encoding="utf-8")
    test = root / "test_source.py"
    test.write_text("assert source()\n", encoding="utf-8")
    inputs = {
        "test_source.py": {"sha256": hashlib.sha256(test.read_bytes()).hexdigest()}
    }
    for run in (initial, terminal):
        (run / "validation.json").write_text(
            json.dumps({"focused_tests": {"input_facts": inputs}}), encoding="utf-8"
        )
    junit = root / "boundary.xml"
    junit.write_text(
        '<testsuites><testsuite><testcase name="explicit_none" /></testsuite></testsuites>',
        encoding="utf-8",
    )
    record = {
        "feature_id": "feature",
        "task_id": "task",
        "unit_id": "unit",
        "initial_run_id": "unit-a1",
        "quality_failed_runs": ["unit-a1", "unit-a3"],
        "coder_repair_success": False,
        "protected_tests_changed": False,
        "source_path": "source.py",
        "before_sha256": before,
        "after_sha256": digest,
        "primary_validation": {"junit": "boundary.xml", "executed": 1},
    }
    (root / "takeover.json").write_text(json.dumps(record), encoding="utf-8")
    selection.update(
        primary_takeover_record="takeover.json",
        required_primary_tests=["explicit_none"],
    )
    return root, initial, terminal, selection


def test_explicit_takeover_provenance_allows_verified_primary_source(takeover_fixture):
    root, initial, terminal, selection = takeover_fixture
    assert AUDIT.select_primary_rework(root, initial, selection) == terminal
    assert AUDIT.load(root / "takeover.json")["coder_repair_success"] is False


@pytest.mark.parametrize("path", ["source.py", "test_source.py"])
def test_takeover_rejects_changed_source_or_protected_tests(takeover_fixture, path):
    root, initial, _, selection = takeover_fixture
    (root / path).write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="differs|inputs changed"):
        AUDIT.select_primary_rework(root, initial, selection)


def test_takeover_rejects_fake_boundary_junit(takeover_fixture):
    root, initial, _, selection = takeover_fixture
    (root / "boundary.xml").write_text(
        '<testsuites><testcase name="explicit_none"><failure /></testcase></testsuites>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="boundary JUnit"):
        AUDIT.select_primary_rework(root, initial, selection)


def test_takeover_cannot_be_credited_as_coder_repair(takeover_fixture):
    root, initial, _, selection = takeover_fixture
    record = AUDIT.load(root / "takeover.json")
    record["coder_repair_success"] = True
    (root / "takeover.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="must not claim Coder repair"):
        AUDIT.select_primary_rework(root, initial, selection)


@pytest.fixture
def citation_fixture(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("changed after validation\n", encoding="utf-8")
    preimage = tmp_path / "preimage.py"
    preimage.write_text("def original():\n    return 1\n", encoding="utf-8")
    test = tmp_path / "test_original.py"
    test.write_text("assert original() == 1\n", encoding="utf-8")
    (tmp_path / "preimages.json").write_text(
        json.dumps(
            [
                {
                    "path": "source.py",
                    "archive_path": "preimage.py",
                    "sha256": hashlib.sha256(preimage.read_bytes()).hexdigest(),
                }
            ]
        ),
        encoding="utf-8",
    )
    events = [
        {
            "event": "turn",
            "facts": {
                "action": "READ_FILE",
                "status": "ok",
                "path": path,
                "start_line": 1,
                "end_line": end,
            },
        }
        for path, end in (("source.py", 2), ("test_original.py", 1))
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events), encoding="utf-8"
    )
    report = {
        "status": "success",
        "semantic_verdict": "not_evaluated",
        "diagnostic_log": "events.jsonl",
        "source_refs": [
            {
                "path": path,
                "kind": kind,
                "source_hash": hashlib.sha256(file.read_bytes()).hexdigest(),
                "start_line": 1,
                "end_line": end,
                "quote": file.read_text().rstrip("\n"),
            }
            for path, file, kind, end in (
                ("source.py", preimage, "implementation", 2),
                ("test_original.py", test, "test", 1),
            )
        ],
    }
    return tmp_path, report


def test_preimage_not_post_edit_source_is_citation_authority(citation_fixture):
    root, report = citation_fixture
    assert AUDIT.replay_refs(root, root, report) == 2


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("quote", "fabricated", "quote mismatch"),
        ("source_hash", "0" * 64, "hash mismatch"),
        ("end_line", 3, "range invalid"),
    ],
)
def test_citation_tampering_rejected(citation_fixture, field, value, match):
    root, original = citation_fixture
    report = copy.deepcopy(original)
    report["source_refs"][0][field] = value
    with pytest.raises(ValueError, match=match):
        AUDIT.replay_refs(root, root, report)


def test_no_actual_read_is_not_proof(citation_fixture):
    root, report = citation_fixture
    (root / "events.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="successful read"):
        AUDIT.replay_refs(root, root, report)


def test_missing_implementation_reference_rejected(citation_fixture):
    root, report = citation_fixture
    report["source_refs"] = report["source_refs"][1:]
    with pytest.raises(ValueError, match="implementation/test"):
        AUDIT.replay_refs(root, root, report)


def test_relative_path_escape_rejected(tmp_path):
    with pytest.raises(ValueError):
        AUDIT.within(tmp_path, "../other.py")


@pytest.fixture
def validated_fixture(tmp_path):
    source = tmp_path / "source.py"
    test = tmp_path / "test_source.py"
    source.write_text("value = 1\n")
    test.write_text("assert value == 1\n")
    run = tmp_path / ".agent/tasks/fixture/runs/a1"
    run.mkdir(parents=True)
    junit = run / "junit.xml"
    junit.write_text(
        '<testsuites><testsuite><testcase name="test_value" /></testsuite></testsuites>'
    )
    facts = {
        path.name: {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in (source, test)
    }
    validation = {
        "status": "passed",
        "focused_tests": {
            "status": "passed",
            "exit_code": 0,
            "junit": {
                "path": junit.relative_to(tmp_path).as_posix(),
                "tests": 1,
                "executed": 1,
                "skipped": 0,
            },
            "input_facts": facts,
        },
        "configured_checks": [{"id": "ruff", "status": "passed", "exit_code": 0}],
    }
    (run / "validation.json").write_text(json.dumps(validation))
    (run / "handoff.json").write_text(
        json.dumps(
            {
                "validation": validation,
                "changed_files": [
                    {"path": "source.py", "final_sha256": facts["source.py"]["sha256"]}
                ],
            }
        )
    )
    (run / "packet.json").write_text(
        json.dumps(
            {"focused_tests": ["test_source.py"], "validation_profile": "fixture"}
        )
    )
    config = tmp_path / ".local-agents/config.json"
    config.parent.mkdir()
    config.write_text(
        json.dumps({"validation_profiles": {"fixture": {"commands": [{"id": "ruff"}]}}})
    )
    return tmp_path, run


@pytest.mark.parametrize("focused", ["test_source.py", "test_source.py::test_value"])
def test_real_validation_replay(validated_fixture, focused):
    root, run = validated_fixture
    path = run / "packet.json"
    value = AUDIT.load(path)
    value["focused_tests"] = [focused]
    path.write_text(json.dumps(value))
    assert AUDIT.replay_validation(root, run) == {
        "executed_focused_tests": 1,
        "configured_check_ids": ["ruff"],
    }


@pytest.mark.parametrize("path", ["source.py", "test_source.py"])
def test_post_validation_source_and_protected_test_change_rejected(
    validated_fixture, path
):
    root, run = validated_fixture
    (root / path).write_text("changed\n")
    with pytest.raises(ValueError, match="changed after validation"):
        AUDIT.replay_validation(root, run)


@pytest.mark.parametrize("outcome", ["failure", "skipped"])
def test_actual_failed_or_all_skipped_junit_rejected(validated_fixture, outcome):
    root, run = validated_fixture
    (run / "junit.xml").write_text(
        f"<testsuites><testsuite><testcase><{outcome} /></testcase></testsuite></testsuites>"
    )
    with pytest.raises(ValueError, match="real focused JUnit"):
        AUDIT.replay_validation(root, run)


def test_missing_registered_check_rejected(validated_fixture):
    root, run = validated_fixture
    config = root / ".local-agents/config.json"
    value = AUDIT.load(config)
    value["validation_profiles"]["fixture"]["commands"].append({"id": "second-check"})
    config.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="configured checks incomplete"):
        AUDIT.replay_validation(root, run)
