"""Host-owned observed versions. Short references never confer edit authority."""

import re
import secrets

from general_state import StateError

PROFILE = "observed-v1"


def enabled(config):
    return config.get("strata_version_references") == PROFILE


class VersionReferences:
    def __init__(self, host):
        self.host = host

    def begin(self):
        self.host.ledger.state["version_references"] = {
            "attempt": self.host.packet["run_id"],
            "contract": self.host.contract_digest,
            "namespace": secrets.token_hex(8),
            "entries": {},
        }
        self.host.ledger.record("observed_version_epoch_started")

    def state(self):
        value = self.host.ledger.state.get("version_references")
        if (
            not value
            or value["attempt"] != self.host.packet["run_id"]
            or value["contract"] != self.host.contract_digest
        ):
            raise StateError("Observed-version epoch/contract mismatch")
        return value

    def issue(self, path, digest):
        """Called only for actual source lines returned by read/search."""
        value = self.state()
        for ref, entry in value["entries"].items():
            if entry["path"] == path and entry["sha256"] == digest and entry["active"]:
                return ref
        ref = f"v{len(value['entries']) + 1}-{value['namespace']}"
        value["entries"][ref] = {
            "path": path,
            "sha256": digest,
            "active": True,
            "task_id": self.host.packet["task_id"],
            "attempt": self.host.packet["run_id"],
            "contract": self.host.contract_digest,
        }
        self.host.ledger.record(
            "observed_version_issued", {"reference": ref, "path": path, "sha256": digest}
        )
        return ref

    def resolve(self, ref, path, digest):
        if not isinstance(ref, str) or not re.fullmatch(r"v[1-9][0-9]*-[a-f0-9]{16}", ref):
            raise ValueError(
                "Malformed version_ref; use the exact reference from current source evidence"
            )
        entry = self.state()["entries"].get(ref)
        if entry is None:
            raise ValueError("Unknown version_ref for this task/attempt; read current source")
        if entry["path"] != path:
            raise ValueError("version_ref path mismatch; read the intended file")
        if (
            entry["task_id"] != self.host.packet["task_id"]
            or entry["attempt"] != self.host.packet["run_id"]
            or entry["contract"] != self.host.contract_digest
        ):
            raise StateError("Observed-version identity mismatch")
        if not entry["active"] or entry["sha256"] != digest:
            raise ValueError("Stale version_ref; read current source")
        return entry["sha256"]

    def invalidate(self, paths):
        for entry in self.state()["entries"].values():
            if entry["path"] in paths:
                entry["active"] = False
        self.host.ledger.record("observed_versions_invalidated", {"paths": sorted(paths)})

    def view(self, hashes):
        return {
            entry["path"]: ref
            for ref, entry in self.state()["entries"].items()
            if entry["active"] and hashes.get(entry["path"]) == entry["sha256"]
        }


def observation_view(value, references):
    """Canonical observations retain hashes; native wire uses observed references."""
    if isinstance(value, list):
        return [observation_view(item, references) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: observation_view(item, references) for key, item in value.items()}
    if isinstance(result.get("path"), str) and result["path"] in references and "sha256" in result:
        result.pop("sha256")
        result["version_ref"] = references.get(result["path"])
    return result
