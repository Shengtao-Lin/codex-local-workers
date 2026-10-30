"""Fixture orchestration guards; no LM Studio calls or sibling writes."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import tool_awaitable_trial as trial


def test_trial_retains_qualified_role_profile_without_switching_models():
    overrides = trial.role_overrides()
    assert overrides["coder_post_edit_validation_hint"] is True
    assert overrides["coder_repair_focus_retention"] == "latest"
    assert overrides["explorer_mode"] == "locate"
    assert overrides["explorer_output_limit_recovery"] is True
    assert overrides["explorer_duplicate_action_report_recovery"] is True
    assert overrides["coordinator_enabled"] is False
    assert not any(key.endswith("_model") for key in overrides)


def test_oracle_never_reaches_model_or_normal_preparation():
    with patch.object(trial, "command") as command:
        with pytest.raises(ValueError, match="oracle must never"):
            trial.run("primary-oracle")
        with pytest.raises(ValueError, match="model arms only"):
            trial.prepare("primary-oracle")
        command.assert_not_called()


def test_failed_positive_control_blocks_model_launch():
    with (
        patch.object(trial, "read", return_value={"passed": False}),
        patch.object(trial, "command") as command,
    ):
        with pytest.raises(ValueError, match="positive fixture preflight required"):
            trial.run("fresh-1")
        command.assert_not_called()
