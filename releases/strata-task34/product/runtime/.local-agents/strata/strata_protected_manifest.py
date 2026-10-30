"""Opt-in v3: use prepared, hashed packet-readable source facts, not four hints.

No discovery/walk or source authority expansion: preparation already froze and
protected these files for this exact run. Same4 actions/120lines/10matches.
"""

import hashlib
import json
from pathlib import PurePosixPath

from strata_manifest_search import ManifestSearchEvidence


class ProtectedManifestEvidence(ManifestSearchEvidence):
    def __init__(self, runtime, *, policy_error, progress_error):
        self.runtime = runtime
        self.policy_error = policy_error
        self.progress_error = progress_error
        raw, _sha = runtime.editor.read_bytes("acceptance/capture-policy.json")
        if (
            hashlib.sha256(raw).hexdigest()
            != runtime.config["experimental_capture_policy_sha256"]
        ):
            raise policy_error("Protected evidence policy differs from preparation")
        policy = json.loads(raw)
        if policy.get("identity") != {
            k: runtime.packet[k] for k in ("task_id", "unit_id", "run_id")
        }:
            raise policy_error("Protected evidence policy identity differs")
        paths = policy.get("source_paths")
        if (
            not isinstance(paths, list)
            or not 1 <= len(paths) <= 125
            or not all(isinstance(p, str) for p in paths)
            or len(set(paths)) != len(paths)
        ):
            raise policy_error("Bounded prepared source list required")
        self.paths = sorted(paths)
        self.observations = []
        self.keys = set()
        self.duplicate_streak = 0
        runtime.ledger["evidence_actions"] = 0
        for path in self.paths:
            self.check_path(path)

    def check_path(self, path):
        p = PurePosixPath(path) if isinstance(path, str) else None
        if (
            p is None
            or path not in self.paths
            or p.is_absolute()
            or str(p) != path
            or ".." in p.parts
            or "\\" in path
            or ":" in path
        ):
            raise self.policy_error("File outside prepared exact source manifest")
        relative, resolved = self.runtime._assert_read_allowed(path)
        if relative != path or not resolved.is_file():
            raise self.policy_error(
                "Protected evidence must be an existing scoped file"
            )
