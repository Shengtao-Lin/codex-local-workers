"""Only v3 change: exact evidence pool matches authenticated preparation inputs."""

import strata_bridge_host as HOST
from strata_native_host_v2 import NativeV2Client
from strata_protected_manifest import ProtectedManifestEvidence
from strata_subagent_rules import select


def rules(base):
    selected = select(base)
    selected.evidence_factory = ProtectedManifestEvidence
    return selected


if __name__ == "__main__":
    raise SystemExit(HOST.main(client_type=NativeV2Client, rules_selector=rules))
