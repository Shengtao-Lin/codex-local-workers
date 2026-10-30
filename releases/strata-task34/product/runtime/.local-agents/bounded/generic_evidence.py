"""Default-off pytest/source evidence, independent of typed example producers.

No invented observations: real configured checks/JUnit and canonical host gate
remain mandatory. Existing capture-v1 behavior is unchanged when not selected.
"""

import hashlib
import json
from pathlib import Path

from .reviewer_capture_envelope import _constant, _object, source_manifest

PROFILE = "pytest-source-v1"
POLICY_PATH = "acceptance/source-policy.json"
CONFIG_SHA = "experimental_source_policy_sha256"
CHECK_IDS = {"ruff-format", "ruff-check", "pyright"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def selected(config):
    value = config.get("bounded_evidence_profile")
    if value not in (None, PROFILE):
        raise ValueError("Unknown bounded_evidence_profile; no implicit fallback")
    return value == PROFILE


def build_policy(runtime, target, source_facts):
    if runtime.config.get("experimental_strata_subagent") is not True:
        raise ValueError("Generic profile requires explicit direct-Primary subagent")
    writable = set(runtime.packet["scope"]["modify"] + runtime.packet["scope"]["create"])
    if target["path"] not in source_facts:
        raise ValueError("Source evidence must include the implementation target")
    return {
        "schema_version": 1,
        "profile": PROFILE,
        "identity": {k: runtime.packet[k] for k in ("task_id", "unit_id", "run_id")},
        "target": target,
        "source_paths": list(source_facts),
        "initial_hashes": dict(source_facts),
        "readonly_hashes": {p: h for p, h in source_facts.items() if p not in writable},
        "python": {"path": str(runtime.python_path()), "sha256": digest(runtime.python_path())},
    }


def policy_for(runtime, *, initial=False):
    if runtime.config.get("experimental_strata_subagent") is not True:
        raise ValueError("Generic profile requires explicit direct-Primary subagent")
    _, path = runtime._assert_read_allowed(POLICY_PATH)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != runtime.config.get(CONFIG_SHA):
        raise ValueError("Source evidence policy differs from trusted preparation")
    policy = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant)
    if (
        not isinstance(policy, dict)
        or set(policy)
        != {
            "schema_version",
            "profile",
            "identity",
            "target",
            "source_paths",
            "initial_hashes",
            "readonly_hashes",
            "python",
        }
        or type(policy["schema_version"]) is not int
        or policy["schema_version"] != 1
        or policy["profile"] != PROFILE
    ):
        raise ValueError("Invalid generic evidence policy")
    if policy["identity"] != {k: runtime.packet[k] for k in ("task_id", "unit_id", "run_id")}:
        raise ValueError("Source evidence belongs to another run")
    if (
        not isinstance(policy["target"], dict)
        or set(policy["target"]) != {"path", "module", "symbol"}
        or any(not isinstance(v, str) or not v for v in policy["target"].values())
        or any(policy["target"].get(k) != runtime.single_function[k] for k in ("path", "symbol"))
    ):
        raise ValueError("Source evidence target differs from scope")
    paths = policy["source_paths"]
    if (
        not isinstance(paths, list)
        or not 1 <= len(paths) <= 125
        or any(not isinstance(p, str) for p in paths)
        or policy["target"]["path"] not in paths
    ):
        raise ValueError("Invalid generic source manifest")
    if POLICY_PATH in paths:
        raise ValueError("Source evidence cannot include itself")
    for key in ("initial_hashes", "readonly_hashes"):
        if not isinstance(policy[key], dict) or any(
            not isinstance(h, str) or len(h) != 64 or any(c not in "0123456789abcdef" for c in h)
            for h in policy[key].values()
        ):
            raise ValueError("Invalid source version bindings")
    for name in paths:
        runtime._assert_read_allowed(name)
    facts = source_manifest(runtime.repo_root, paths, approved_paths=paths)["files"]
    writable = set(runtime.packet["scope"]["modify"] + runtime.packet["scope"]["create"])
    if (
        set(policy["initial_hashes"]) != set(facts)
        or set(policy["readonly_hashes"]) != set(facts) - writable
    ):
        raise ValueError("Source evidence coverage differs")
    if any(facts[p] != sha for p, sha in policy["readonly_hashes"].items()):
        raise ValueError("Protected source evidence changed")
    if initial and facts != policy["initial_hashes"]:
        raise ValueError("Initial source version differs")
    if policy["python"] != {
        "path": str(runtime.python_path()),
        "sha256": digest(runtime.python_path()),
    }:
        raise ValueError("Trusted check interpreter changed")
    commands = runtime.validation_profile().get("commands", [])
    if (
        len(commands) != 3
        or any(not isinstance(c, dict) for c in commands)
        or {c.get("id") for c in commands} != CHECK_IDS
    ):
        raise ValueError("Generic profile requires exact full static-check set")
    return policy, facts


def bind_before_coder(runtime):
    policy, facts = policy_for(runtime, initial=True)
    for name, sha in {**facts, POLICY_PATH: runtime.config[CONFIG_SHA]}.items():
        runtime.read_file({"path": name, "start_line": 1, "end_line": 1})
        if runtime.observed_hashes.get(name) != sha:
            raise ValueError("Source evidence initialization changed")
    return policy


def preflight_material(runtime):
    policy, facts = policy_for(runtime, initial=True)
    return {
        "profile": PROFILE,
        "target": policy["target"],
        "policy_sha256": runtime.config[CONFIG_SHA],
        "source_count": len(facts),
        "validation_credit": False,
        "typed_observations": "NOT_REQUESTED_BY_PROFILE",
    }
