import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reviewer_contract_test_read_adapter import install
from reviewer_staged_assessment_adapter import install as install_staged
from test_reviewer_staged_assessment_adapter import assessment, fixture_runtime


def configured(reviewer):
    install_staged(reviewer)
    original = reviewer.ReviewerRuntime.__init__

    def init(runtime, root, request, config, client):
        config = {
            **config,
            "reviewer_contract_test_reads": [
                {"contract_id": "behavior-1", "path": "tests/test_example.py"}
            ],
        }
        return original(runtime, root, request, config, client)

    reviewer.ReviewerRuntime.__init__ = init
    install(reviewer)


def test_provisional_any_status_requires_actual_entire_protected_test(tmp_path):
    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=configured)
    runtime.read_file({"path": "src/example.py"})
    for status in ("verified", "violated", "uncertain"):
        with pytest.raises(
            reviewer.ReviewError, match="protected contract test read missing"
        ):
            runtime.validate_report(assessment(status))
        assert not runtime.staged_assessments
    hint = runtime.report_repair(
        "protected contract test read missing: tests/test_example.py", assessment()
    )
    assert hint["suggested_action"]["arguments"]["path"] == "tests/test_example.py"
    runtime.read_file({"path": "tests/test_example.py", "start_line": 1, "end_line": 1})
    with pytest.raises(
        reviewer.ReviewError, match="protected contract test read missing"
    ):
        runtime.validate_report(assessment())
    runtime.read_file({"path": "tests/test_example.py"})
    proposal = assessment("uncertain")
    result = runtime.validate_report(proposal)
    assert result["contract_review"][0]["status"] == "uncertain"
    assert not (runtime.review_root / "completed.json").exists()
    (tmp_path / "tests/test_example.py").write_text(
        "CHANGED = True\n", encoding="utf-8"
    )
    with pytest.raises(reviewer.ReviewError, match="changed"):
        runtime.validate_report(assessment())


def test_no_opt_in_preserves_original_behavior(tmp_path):
    def combined(reviewer):
        install_staged(reviewer)
        install(reviewer)

    _, runtime = fixture_runtime(tmp_path, install_adapter=combined)
    runtime.read_file({"path": "src/example.py"})
    assert (
        runtime.validate_report(assessment())["contract_review"][0]["status"]
        == "verified"
    )


def test_navigation_uses_only_read_handles_and_preserves_semantic_state(tmp_path):
    from reviewer_anchored_catalog_adapter import install as install_anchors
    from reviewer_catalog_staged_adapter import install as install_catalog
    from reviewer_contract_test_read_adapter import citation_navigation
    from reviewer_range_staged_adapter import install as install_range

    def combined(reviewer):
        install_range(reviewer)
        install_catalog(reviewer)
        install_anchors(reviewer)

    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=combined)
    runtime.config["reviewer_dependency_evidence"] = [
        {
            "contract_id": "behavior-1",
            "path": "src/example.py",
            "anchors": ["VALUE", "missing"],
        }
    ]
    assert citation_navigation(runtime)[0]["actual_read_options"] == []
    runtime.read_file({"path": "src/example.py"})
    options = citation_navigation(runtime)[0]
    assert options["required_anchors"] == ["VALUE", "missing"]
    assert options["actual_read_options"] == [{"id": "E1", "covers_anchors": ["VALUE"]}]
    assert not runtime.staged_assessments
    assert not (runtime.review_root / "completed.json").exists()
    (tmp_path / "src/example.py").write_text("VALUE = 3\n", encoding="utf-8")
    with pytest.raises(reviewer.ReviewError, match="changed"):
        citation_navigation(runtime)
