import importlib.util
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]


@pytest.fixture
def challenge(monkeypatch):
    monkeypatch.syspath_prepend(str(KIT / "benchmarks"))
    spec = importlib.util.spec_from_file_location(
        "complex_reviewer_test", KIT / "benchmarks/complex_reviewer_challenge.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "decision,line,path,expected",
    [
        ("rework", 14, "src/product/publish.py", True),
        ("pass_to_primary", 14, "src/product/publish.py", False),
        ("rework", 1, "src/product/publish.py", False),
        ("rework", 14, "src/product/evidence.py", False),
    ],
)
def test_hidden_score_requires_concrete_exception_path(
    challenge, decision, line, path, expected
):
    report = {
        "decision": decision,
        "findings": [
            {
                "path": path,
                "line": line,
                "evidence": "rollback masks original exception",
            }
        ],
    }
    assert challenge.classify(report, "hidden", (13, 14, 15)) is expected


def test_exception_evidence_tracks_source_not_fixed_lines(challenge):
    source = (
        "\n" * 20 + "try:\n    write()\nexcept Exception:\n    rollback()\n    raise\n"
    )
    lines = challenge.exception_lines(source)
    assert lines == [23, 24, 25]
    report = {
        "decision": "rework",
        "findings": [
            {
                "path": "src/product/publish.py",
                "line": 24,
                "evidence": "rollback masks original exception",
            }
        ],
    }
    assert challenge.classify(report, "hidden", lines)
    assert not challenge.classify(report, "hidden")


def test_finally_path_is_scored_from_source(challenge):
    source = "try:\n    operation()\nfinally:\n    release()\n"
    assert challenge.exception_lines(source) == [1, 2, 3, 4]
    report = {
        "decision": "rework",
        "findings": [
            {
                "path": "src/product/target.py",
                "line": 4,
                "evidence": "release masks original exception",
            }
        ],
    }
    assert challenge.classify(
        report,
        "hidden",
        challenge.exception_lines(source),
        "src/product/target.py",
        "release",
    )


def test_clean_control_rejects_false_positive(challenge):
    assert challenge.classify({"decision": "pass_to_primary", "findings": []}, "clean")
    assert not challenge.classify({"decision": "rework", "findings": []}, "clean")
    assert not challenge.classify(
        {"decision": "pass_to_primary", "findings": [{}]}, "clean"
    )


def test_keyword_match_never_establishes_semantic_detection(challenge):
    report = {"decision": "rework", "findings": [{"evidence": "incorrect explanation"}]}
    grade = challenge.grading_status(report, "hidden", True)
    assert grade["structural_outcome"] is True
    assert grade["effective_detection"] is None
    assert grade["requires_primary_adjudication"] is True
    assert grade["clean_control_passed"] is False


def test_clean_grade_does_not_grant_feature_acceptance(challenge):
    grade = challenge.grading_status(
        {"decision": "pass_to_primary", "findings": []}, "clean", True
    )
    assert grade["clean_control_passed"] is True
    assert grade["effective_detection"] is None


def test_challenge_source_cannot_escape_workspace(challenge):
    with pytest.raises(ValueError):
        challenge.run(KIT / "tests", "hidden")
