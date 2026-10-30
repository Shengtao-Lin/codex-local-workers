"""Default-off portable/generic candidate with explicit finite evidence credits."""

import strata_bridge_host as HOST
from strata_native_host_v2 import NativeV2Client
from strata_protected_manifest import ProtectedManifestEvidence
from strata_subagent_rules import select


class SourceEvidence(ProtectedManifestEvidence):
    max_actions = 6

    def __init__(self, runtime, *, policy_error, progress_error):
        from bounded import generic_evidence as G

        if not G.selected(runtime.config):
            super().__init__(
                runtime, policy_error=policy_error, progress_error=progress_error
            )
            return
        self.runtime, self.policy_error, self.progress_error = (
            runtime,
            policy_error,
            progress_error,
        )
        policy, _ = G.policy_for(runtime, initial=True)
        self.paths = sorted(policy["source_paths"])
        self.observations, self.keys, self.duplicate_streak = [], set(), 0
        runtime.ledger["evidence_actions"] = 0
        for path in self.paths:
            self.check_path(path)


def rules(base):
    chosen = select(base)
    chosen.evidence_factory = SourceEvidence
    return chosen


class NativeV4Client(NativeV2Client):
    shared_limit = 18
    model_limit = 8

    def receive(self):
        value = super().receive()
        if value.get("kind") == "host_action":
            ledger = self.runtime.ledger
            if (
                ledger["requests"] + ledger["native_request_reservations"]
                > self.shared_limit
            ):
                raise self.worker.WorkerError(
                    "Shared native model/tool task budget exhausted"
                )
        return value

    def send(self, value):
        if value.get("kind") == "host_context":
            ledger = self.runtime.ledger
            value["context"]["tool_budget"] = {
                "shared_model_plus_host_limit": self.shared_limit,
                "shared_remaining": max(
                    0,
                    self.shared_limit
                    - ledger["requests"]
                    - ledger["native_request_reservations"],
                ),
                "model_requests_remaining": max(
                    0, self.model_limit - ledger["native_request_reservations"]
                ),
                "host_actions_remaining": max(0, 12 - ledger["requests"]),
                "evidence_actions_remaining": max(0, 6 - ledger["evidence_actions"]),
                "read_max_lines": 120,
                "search_max_matches": 10,
                "edits_remaining": max(0, 3 - ledger["edits"]),
                "note": "All limits simultaneously apply; no retry resets. Leave credits for proposal/repair.",
            }
        return super().send(value)


if __name__ == "__main__":
    raise SystemExit(HOST.main(client_type=NativeV4Client, rules_selector=rules))
