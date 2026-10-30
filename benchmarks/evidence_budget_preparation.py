"""Offline feasibility adapter only; not a live runner or production setting."""

import json

import capture_fixture_support as F

BUDGET = {
    "model_requests": 12,
    "effective_edits": 3,
    "initial_checks": 1,
    "post_edit_checks": 3,
    "formatter_commands": 1,
    "output_tokens_per_request": 4096,
    "invocation_seconds": 900,
}


def install_offline_capture_binding(worker, policy_path, policy_sha):
    """Reuse identical binding, avoiding the old wrapper's hardcoded 3/3 caps.

    Model edits are counted by host_edits; format mutations still increment the
    source epoch. Neither the epoch nor original records are ever decremented.
    """
    original = worker.WorkerRuntime

    class OfflineCaptureBinding(original):
        def __init__(self, root, packet, config, client):
            if config.get("offline_budget_feasibility") is not True:
                raise worker.WorkerError("Offline binding opt-in required")
            super().__init__(root, packet, config, client)
            if policy_path != F.POLICY_PATH:
                raise worker.WorkerError("Unregistered capture path")
            policy = json.loads(
                (self.repo_root / policy_path).read_text(encoding="utf-8")
            )
            if policy["identity"] != {
                k: self.packet[k] for k in ("task_id", "unit_id", "run_id")
            }:
                raise worker.WorkerError("Capture identity differs from packet")
            F.bind_before_coder(self, policy, policy_sha)

    worker.WorkerRuntime = OfflineCaptureBinding


def align_for_offline_replay(worker, parent):
    """Prove the unchanged host can check edit3, without refunding old checks.

    This does NOT implement B's read dispatcher or protocol recovery. No caller
    should interpret this feasibility class as a qualified A/B candidate.
    """

    class OfflineAlignedBudget(parent):
        def __init__(self, root, packet, config, client):
            if config.get("offline_budget_feasibility") is not True:
                raise worker.WorkerError("Offline feasibility opt-in required")
            super().__init__(root, packet, config, client)
            if min(self.max_turns, self.hard_max_turns) < BUDGET["model_requests"]:
                raise worker.WorkerError(
                    "Requested budget exceeds configured request ceiling"
                )
            self.host_request_cap = BUDGET["model_requests"]
            self.host_check_cap = BUDGET["initial_checks"] + BUDGET["post_edit_checks"]
            self.host_edit_cap = BUDGET["effective_edits"]

    return OfflineAlignedBudget
