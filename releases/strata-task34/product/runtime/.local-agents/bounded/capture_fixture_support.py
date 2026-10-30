import importlib.util
import sys
from pathlib import Path as Path
from types import SimpleNamespace
from . import capture_validation_facts as P

POLICY_PATH = "acceptance/capture-policy.json"
PRODUCER = "acceptance/capture_validation_facts.py"
HELPER = "acceptance/reviewer_capture_envelope.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def preflight_material(runtime):
    """Reuse final policy authentication before paying for model residency.

    This validates declared material only: it neither executes capture nor
    certifies a complete import graph, current passing checks, or semantics.
    Final handoff must still authenticate the actual canonical validation epoch.
    """
    from . import generic_evidence as generic

    if generic.selected(runtime.config):
        return generic.preflight_material(runtime)
    from . import reviewer_canonical_capture as capture

    view = SimpleNamespace(
        repo_root=runtime.repo_root,
        packet=runtime.packet,
        config=runtime.config,
        _assert_read_allowed=runtime._assert_read_allowed,
        **{key: runtime.packet[key] for key in ("task_id", "unit_id", "run_id")},
    )
    sha = runtime.config["experimental_capture_policy_sha256"]
    policy, manifest = capture.policy_material(view, POLICY_PATH, sha)
    return {
        "policy_sha256": sha,
        "target": dict(policy["target"]),
        "source_manifest_sha256": manifest["sha256"],
        "validation_credit": False,
    }


def bind_before_coder(runtime, policy, policy_sha):
    """Trusted wrapper reads bytes for epoch coverage, not model-visible evidence.

    The existing runtime still owns validation, execution and archive creation.
    This grants no new read/write scope or model evidence IDs.
    """
    if P.digest(runtime.repo_root / POLICY_PATH) != policy_sha:
        raise ValueError("capture policy changed before dispatch")
    manifest = P.manifest_for(runtime.repo_root, POLICY_PATH, policy)
    for path, sha in manifest["files"].items():
        runtime.read_file({"path": path, "start_line": 1, "end_line": 1})
        if runtime.observed_hashes.get(path) != sha:
            raise ValueError("capture initialization hash mismatch")
