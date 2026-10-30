"""Versioned host facts; never reinterpret them as worker contract assessment."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

PROTOCOL = "host-proposal-v1"
PENDING = "validation_passed_pending_review"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_hash(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def bounded(root, relative):
    root = Path(root).resolve()
    path = root / relative
    if (
        Path(relative).is_absolute()
        or ".." in Path(relative).parts
        or not path.resolve().is_relative_to(root)
    ):
        raise ValueError("Host evidence path escapes archive")
    for current in (path, *path.parents):
        if current == root:
            break
        if current.exists() and (
            current.is_symlink() or getattr(current.stat(), "st_file_attributes", 0) & 0x400
        ):
            raise ValueError("Host evidence reparse path rejected")
    return path


def seal(runtime, report):
    archive = runtime.archive.run_root
    if report.get("status") != PENDING or not runtime.archive_finalized:
        raise ValueError("Cannot seal incomplete host run")
    paths = [p for p in archive.rglob("*") if p.is_file()]
    manifest = {
        "protocol": PROTOCOL,
        "status": PENDING,
        "worker_assessment": None,
        "identity": report["identity"],
        "validation_profile": runtime.packet["validation_profile"],
        "trusted_profile": runtime.validation_profile(),
        "trusted_config_sha256": object_hash(runtime.config),
        "validation_attempt": runtime.validation_count,
        "edit_revision": runtime.edit_revision,
        "artifact_hashes": {p.relative_to(archive).as_posix(): digest(p) for p in paths},
        "review_required": True,
        "primary_required": True,
    }
    runtime.RUN_STATE.write_json_once(archive / "host-validation-facts.json", manifest)


def verify(repo, archive, packet, handoff, validation, config):
    if config.get("host_proposal_enabled") is not True:
        raise ValueError("Host proposal protocol needs explicit trusted opt-in")
    manifest = json.loads((archive / "host-validation-facts.json").read_text(encoding="utf-8"))
    if (
        manifest.get("protocol") != PROTOCOL
        or manifest.get("status") != PENDING
        or manifest.get("worker_assessment") is not None
        or validation.get("contract_check") is not None
        or handoff.get("execution_protocol") != PROTOCOL
        or handoff.get("worker_assessment") is not None
    ):
        raise ValueError("Unknown host protocol or fabricated worker assessment")
    if manifest.get("identity") != handoff.get("identity") or handoff.get("status") != PENDING:
        raise ValueError("Host identity/status mismatch")
    if handoff.get("next_action_required") != "local_review":
        raise ValueError("Host review obligation missing")
    if manifest.get("review_required") is not True or manifest.get("primary_required") is not True:
        raise ValueError("Host review/Primary obligations missing")
    if object_hash(config) != manifest.get("trusted_config_sha256"):
        raise ValueError("Trusted host configuration changed")
    baseline = json.loads((archive / "baseline.json").read_text(encoding="utf-8"))
    if baseline.get("config_sha256") != manifest["trusted_config_sha256"]:
        raise ValueError("Host configuration is not the canonical baseline")
    profile = config.get("validation_profiles", {}).get(packet["validation_profile"])
    if not isinstance(profile, dict) or profile != manifest.get("trusted_profile"):
        raise ValueError("Host validation profile differs")
    hashes = manifest.get("artifact_hashes")
    required = {
        "packet.json",
        "baseline.json",
        "handoff.json",
        "completed.json",
        "validation.json",
        "changes.json",
        "post-state.json",
        "preimages.json",
        "cumulative.diff",
        "reverse.diff",
    }
    if not isinstance(hashes, dict) or not required <= set(hashes):
        raise ValueError("Host validation artifact manifest incomplete")
    for relative, sha in hashes.items():
        path = bounded(archive, relative)
        if not path.is_file() or digest(path) != sha:
            raise ValueError("Host canonical evidence changed: " + relative)
    if type(manifest.get("edit_revision")) is not int or manifest["edit_revision"] < 1:
        raise ValueError("Green baseline is not a host implementation")
    count = manifest.get("validation_attempt")
    if type(count) is not int or count < 1 or f"validation-attempt-{count}.json" not in hashes:
        raise ValueError("Host validation attempt missing")
    attempt = json.loads((archive / f"validation-attempt-{count}.json").read_text(encoding="utf-8"))
    if (
        attempt.get("validation") != validation
        or attempt.get("edit_revision") != manifest["edit_revision"]
    ):
        raise ValueError("Host attempt does not validate current edit")
    focused = validation.get("focused_tests") or {}
    junit = focused.get("junit") or {}
    if (
        validation.get("status") != "passed"
        or validation.get("py_compile", {}).get("status") != "passed"
    ):
        raise ValueError("Host deterministic checks failed")
    junit_path = bounded(repo, junit.get("path", ""))
    if (
        not junit_path.resolve().is_relative_to(archive.resolve())
        or junit_path.relative_to(archive).as_posix() not in hashes
    ):
        raise ValueError("Host JUnit is not bound to archive")
    tree = ET.parse(junit_path)
    cases = tree.findall(".//testcase")
    executed = sum(case.find("skipped") is None for case in cases)
    if (
        executed < 1
        or executed != junit.get("executed")
        or any(tree.findall(".//" + key) for key in ("failure", "error"))
    ):
        raise ValueError("Host JUnit failed, empty or inconsistent")
    expected = profile.get("commands", [])
    checks = validation.get("configured_checks") or []
    if len(checks) != len(expected) or len({c["id"] for c in expected}) != len(expected):
        raise ValueError("Host configured check set differs")
    python = str((repo / profile["python"]).resolve())
    for command, check in zip(expected, checks):
        argv = [
            arg.replace("{python}", python).replace("{repo}", str(repo)) for arg in command["argv"]
        ]
        if (
            check.get("id") != command["id"]
            or check.get("argv") != argv
            or check.get("status") != "passed"
            or check.get("exit_code") != 0
        ):
            raise ValueError("Host configured check failed or command changed")
    return manifest
