"""Offline fixture preparation, never an implicit production installation."""

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import capture_validation_facts as P

KIT = Path(__file__).resolve().parents[1]
POLICY_PATH = "acceptance/capture-policy.json"
PRODUCER = "acceptance/capture_validation_facts.py"
HELPER = "acceptance/reviewer_capture_envelope.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def install_material(
    root, identity, *, source_paths, target, family, cases, writable, python
):
    root = Path(root)
    (root / "acceptance").mkdir(exist_ok=True)
    for path in (PRODUCER, HELPER):
        destination = root / path
        if destination.exists():
            raise ValueError("refuse to overwrite capture material")
        shutil.copyfile(KIT / "benchmarks" / destination.name, destination)
    policy = {
        "schema_version": 1,
        "identity": identity,
        "check_id": "actual-observations",
        "producer_path": PRODUCER,
        "producer_sha256": P.digest(root / PRODUCER),
        "helper_path": HELPER,
        "helper_sha256": P.digest(root / HELPER),
        "python": {"path": str(Path(python)), "sha256": P.digest(python)},
        "target": target,
        "source_paths": source_paths,
        "readonly_hashes": {
            p: P.digest(root / p) for p in source_paths if p not in writable
        },
        "family": family,
        "cases": cases,
    }
    P.validate_policy(policy)
    with (root / POLICY_PATH).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(policy, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return policy, P.digest(root / POLICY_PATH)


def bind_before_coder(runtime, policy, policy_sha):
    """Trusted wrapper reads bytes for epoch coverage, not model-visible evidence.

    The existing runtime still owns validation, execution and archive creation.
    This grants no new read/write scope or model evidence IDs.
    """
    if P.digest(runtime.repo_root / POLICY_PATH) != policy_sha:
        raise ValueError("capture policy changed before dispatch")
    manifest = P.manifest_for(runtime.repo_root, POLICY_PATH, policy)
    for path, sha in manifest["files"].items():
        # Existing Coder path/scope check remains authoritative.
        runtime.read_file({"path": path, "start_line": 1, "end_line": 1})
        if runtime.observed_hashes.get(path) != sha:
            raise ValueError("capture initialization hash mismatch")


def command():
    return {
        "id": "actual-observations",
        "argv": ["{python}", "-B", "{repo}/" + PRODUCER, "--policy", POLICY_PATH],
    }
