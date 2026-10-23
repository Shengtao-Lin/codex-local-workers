"""Versioned opt-in: approved-manifest search + deterministic feedback deltas."""

import strata_bridge_host as HOST
from strata_manifest_search import ManifestSearchEvidence
from strata_native_agent_host import NativeAgentClient
from strata_native_feedback import FeedbackProjection
from strata_subagent_rules import select


def rules(base):
    selected = select(base)
    selected.evidence_factory = ManifestSearchEvidence
    return selected


class NativeV2Client(NativeAgentClient):
    def complete(self, messages):
        from bounded import capture_fixture_support as F

        if not hasattr(self, "projection"):
            self.projection = FeedbackProjection()
            self.literal = F.load(
                self.runtime.repo_root / ".local-agents/proposal-interface.py",
                "native_delta_literal",
            )
        self.facts = self.literal.restore_literal(
            messages[1]["content"].partition("\n")[2]
        )
        return super().complete(messages)

    def send(self, value):
        if value.get("kind") == "host_context":
            value = {
                **value,
                "context": self.projection.project(
                    self.facts, value["context"], self.task_material
                ),
            }
            r = self.runtime
            r.RUN_STATE.write_json_once(
                r.archive.run_root / f"native-feedback-{r.ledger['requests']}.json",
                value,
            )
        # Bypass v1's repeated full-task insertion, retaining transport identity.
        return HOST.NativeReplayClient.send(self, value)


if __name__ == "__main__":
    raise SystemExit(HOST.main(client_type=NativeV2Client, rules_selector=rules))
