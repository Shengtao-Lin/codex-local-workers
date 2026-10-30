"""Proposal generation is not edit permission or worker-success evidence."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import tool_module_proposal as proposal


def test_proposal_has_one_existing_authorized_target_and_no_model_success_fields():
    good = {"path": proposal.trial.TARGET, "content": "# draft\n"}
    assert proposal.checked_proposal(good) == good
    for invalid in (
        {**good, "path": "../sibling.py"},
        {**good, "path": proposal.trial.EXTRA},
        {**good, "accepted": True},
        {**good, "content": ""},
        {**good, "content": 1},
        {**good, "content": "x" * 20001},
    ):
        with pytest.raises(ValueError):
            proposal.checked_proposal(invalid)


def test_exact_proposal_primary_review_is_required_before_editor_construction(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(proposal, "BASE", tmp_path)
    root = tmp_path / "proposal-1"
    proposal.write(root / ".agent/manifest.json", {"files": {}})
    proposal.write(
        root / ".agent/proposal.json",
        {"path": proposal.trial.TARGET, "content": "# draft"},
    )
    proposal.write(
        root / ".agent/primary-proposal-review.json",
        {"proposal_sha256": "wrong", "safe_to_validate": True},
    )
    monkeypatch.setattr(
        proposal,
        "load_worker",
        lambda _: pytest.fail("No editor before exact hash approval"),
    )
    with pytest.raises(ValueError, match="Primary review required"):
        proposal.apply_reviewed("proposal-1")
    with pytest.raises(ValueError, match="registered diagnostic arm"):
        proposal.apply_reviewed("../../outside")
