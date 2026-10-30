import copy
import importlib.util
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from . import capture_validation_facts as PRODUCER
from .reviewer_capture_envelope import CaptureRejected, parse_command_capture, source_manifest

PROTOCOL = "canonical-validation-capture-v1"
ORIGINAL_FLAGS = {"reviewer_compact_report", "reviewer_evidence_state"}


def policy_material(runtime, policy_path, expected_sha):
    _, path = runtime._assert_read_allowed(policy_path)
    if PRODUCER.digest(path) != expected_sha:
        raise CaptureRejected("policy differs from trusted registration")
    policy = PRODUCER.validate_policy(json.loads(path.read_text(encoding="utf-8")))
    identity = {k: getattr(runtime, k) for k in ("task_id", "unit_id", "run_id")}
    if policy["identity"] != identity:
        raise CaptureRejected("capture policy belongs to another run")
    manifest = PRODUCER.manifest_for(runtime.repo_root, policy_path, policy)
    scope = runtime.packet["scope"]
    protected = {
        policy_path,
        policy["producer_path"],
        policy["helper_path"],
        *policy["readonly_hashes"],
    }
    writable = scope["modify"] + scope["create"]

    def matches(path, roots):
        return any(path == p or path.startswith(p + "/") for p in roots)

    for name in manifest["files"]:
        runtime._assert_read_allowed(name)
        if name in protected and (
            matches(name, writable) or not matches(name, scope.get("readonly", []))
        ):
            raise CaptureRejected("capture dependency is not protected readonly: " + name)
        if (
            name in policy["source_paths"]
            and (not matches(name, writable))
            and (name not in policy["readonly_hashes"])
        ):
            raise CaptureRejected("unversioned readonly source dependency: " + name)
    binding = runtime.config.get("coder_single_function")
    if binding and (
        binding.get("path") != policy["target"]["path"]
        or binding.get("symbol") != policy["target"]["symbol"]
    ):
        raise CaptureRejected("capture target differs from trusted function binding")
    python = Path(policy["python"]["path"])
    if PRODUCER.digest(python) != policy["python"]["sha256"]:
        raise CaptureRejected("capture interpreter changed")
    return (policy, manifest)


def validate_profiles(profiles, policy, manifest):
    if not isinstance(profiles, list) or len(profiles) != 1:
        raise CaptureRejected("exactly one factual profile required")
    profile = profiles[0]
    if not isinstance(profile, dict) or set(profile) != {
        "profile_id",
        "source",
        "examples",
        "meaning",
    }:
        raise CaptureRejected("unknown factual profile fields")
    if (
        profile["profile_id"] != policy["family"]
        or profile["source"]
        != {"path": policy["target"]["path"], "sha256": manifest["files"][policy["target"]["path"]]}
        or profile["meaning"] != PRODUCER.MEANING
    ):
        raise CaptureRejected("factual source/profile binding disagrees")
    examples = profile["examples"]
    if not isinstance(examples, list) or len(examples) != len(policy["cases"]):
        raise CaptureRejected("factual case count disagrees")
    family = policy["family"]
    for example, case in zip(examples, policy["cases"], strict=True):
        expected_fields = {"input", "outcome"}
        if family.endswith("lookup_or-v1"):
            expected_fields.add("fetch_calls")
        elif (
            family.endswith("display_name-v1")
            or family == "json-call-model-dump-v1"
            or family == "collect-tools-json-observation-v1"
            or (family in {"canonical-json-bytes-v1", "mapping-raw-utf8-v1"})
        ):
            expected_fields.add("input_unchanged")
        if (
            not isinstance(example, dict)
            or set(example) != expected_fields
            or json.dumps(example["input"], sort_keys=True) != json.dumps(case, sort_keys=True)
        ):
            raise CaptureRejected("factual input loss or unknown semantic fields")
        if "input_unchanged" in example and type(example["input_unchanged"]) is not bool:
            raise CaptureRejected("input mutation fact must be boolean")
        if "fetch_calls" in example and (
            not isinstance(example["fetch_calls"], list) or len(example["fetch_calls"]) > 32
        ):
            raise CaptureRejected("invalid fetch observation")
        outcome = example["outcome"]
        if not isinstance(outcome, dict):
            raise CaptureRejected("outcome must be factual data")
        if outcome.get("kind") == "returned":
            if set(outcome) != {"kind", "value"}:
                raise CaptureRejected("invalid returned observation")
            PRODUCER.bounded_json(outcome["value"])
            if family == "canonical-json-bytes-v1":
                value = outcome["value"]
                if (
                    not isinstance(value, dict)
                    or set(value) != {"type", "hex"}
                    or value["type"] != "bytes"
                    or (not isinstance(value["hex"], str))
                    or len(value["hex"]) % 2
                    or any((c not in "0123456789abcdef" for c in value["hex"]))
                ):
                    raise CaptureRejected("invalid lossless byte observation")
            if family == "collect-tools-json-observation-v1":
                if not isinstance(outcome["value"], list) or len(outcome["value"]) > 16:
                    raise CaptureRejected("invalid returned tool calls")
                for call in outcome["value"]:
                    if (
                        not isinstance(call, dict)
                        or set(call) != {"call_id", "name", "arguments", "result", "status"}
                        or call["status"] not in {"requested", "succeeded", "failed", "unknown"}
                        or (not isinstance(call["call_id"], str))
                        or (not isinstance(call["name"], str))
                        or (not isinstance(call["arguments"], dict))
                    ):
                        raise CaptureRejected("invalid typed tool-call projection")
        elif outcome.get("kind") == "raised":
            keys = (
                {"kind", "type", "same_exception_instance"}
                if family.endswith("lookup_or-v1")
                else {"kind", "type", "message"}
            )
            if set(outcome) != keys or not isinstance(outcome["type"], str):
                raise CaptureRejected("invalid raised observation")
            if (
                "same_exception_instance" in outcome
                and type(outcome["same_exception_instance"]) is not bool
            ):
                raise CaptureRejected("exception identity must be boolean")
            if "message" in outcome and (
                not isinstance(outcome["message"], str) or len(outcome["message"]) > 1000
            ):
                raise CaptureRejected("invalid exception message")
        else:
            raise CaptureRejected("unsupported observation kind")
    return copy.deepcopy(profiles)


def load_capture(runtime, policy_path, expected_sha):
    runtime._assert_inputs_current()
    policy, manifest = policy_material(runtime, policy_path, expected_sha)
    run = runtime.run_root
    canonical = [
        "packet.json",
        "completed.json",
        "handoff.json",
        "validation.json",
        "post-state.json",
        "changes.json",
        "cumulative.diff",
        "preimages.json",
    ]
    junit = runtime.validation.get("focused_tests", {}).get("junit", {})
    junit_path = junit.get("path")
    if not isinstance(junit_path, str) or not junit_path.startswith(
        run.relative_to(runtime.repo_root).as_posix() + "/"
    ):
        raise CaptureRejected("JUnit does not belong to canonical run")
    canonical.append(str((runtime.repo_root / junit_path).relative_to(run)))
    relative = [
        p.relative_to(runtime.repo_root).as_posix() for p in [run / name for name in canonical]
    ]
    before = source_manifest(runtime.repo_root, relative, approved_paths=relative)
    handoff = json.loads((run / "handoff.json").read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location(
        "capture_original_unit_gate", runtime.repo_root / ".local-agents/local-unit.py"
    )
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    config = {k: v for k, v in runtime.config.items() if k not in ORIGINAL_FLAGS}
    identity = gate.verify_handoff(runtime.repo_root, handoff, config=config)
    if identity != policy["identity"] or handoff != runtime.handoff:
        raise CaptureRejected("canonical handoff identity changed")
    validation = json.loads((run / "validation.json").read_text(encoding="utf-8"))
    if validation != runtime.validation:
        raise CaptureRejected("canonical validation differs from loaded review")
    try:
        cases = list(ET.parse(runtime.repo_root / junit_path).getroot().iter("testcase"))
    except ET.ParseError as exc:
        raise CaptureRejected("canonical JUnit is malformed") from exc
    totals = {
        "tests": len(cases),
        "failures": sum((c.find("failure") is not None for c in cases)),
        "errors": sum((c.find("error") is not None for c in cases)),
        "skipped": sum((c.find("skipped") is not None for c in cases)),
    }
    totals["executed"] = totals["tests"] - totals["skipped"]
    if (
        totals["executed"] < 1
        or totals["failures"]
        or totals["errors"]
        or any((junit.get(k) != v for k, v in totals.items()))
    ):
        raise CaptureRejected("actual canonical JUnit does not establish executed passing tests")
    for path, sha in manifest["files"].items():
        fact = runtime.expected_inputs.get(path)
        if (
            not isinstance(fact, dict)
            or fact.get("exists") is not True
            or fact.get("kind") != "file"
            or (fact.get("sha256") != sha)
        ):
            raise CaptureRejected("capture file absent from canonical validation epoch: " + path)
    profile = runtime.validation_profile()
    commands = profile.get("commands", [])
    commands = [c for c in commands if c.get("id") == policy["check_id"]]
    expected_argv = [
        str(Path(policy["python"]["path"])),
        "-B",
        "{repo}/" + policy["producer_path"],
        "--policy",
        policy_path,
    ]
    template = ["{python}", *expected_argv[1:]]
    if len(commands) != 1 or commands[0].get("argv") != template:
        raise CaptureRejected("capture command differs from trusted configured profile")
    expanded = [s.replace("{repo}", str(runtime.repo_root)) for s in expected_argv]
    bindings = {
        "task_id": runtime.task_id,
        "run_id": runtime.run_id,
        "producer_sha256": policy["producer_sha256"],
        "profile_sha256": expected_sha,
        "source_manifest_sha256": manifest["sha256"],
    }
    facts = parse_command_capture(
        validation["configured_checks"],
        check_id=policy["check_id"],
        argv=expanded,
        bindings=bindings,
    )
    facts = validate_profiles(facts, policy, manifest)
    after = source_manifest(runtime.repo_root, relative, approved_paths=relative)
    runtime._assert_inputs_current()
    if before != after or PRODUCER.manifest_for(runtime.repo_root, policy_path, policy) != manifest:
        raise CaptureRejected("capture inputs/archive changed while loading")
    if getattr(runtime, "_canonical_capture_epoch", before) != before:
        raise CaptureRejected("canonical capture archive changed during review")
    runtime._canonical_capture_epoch = before
    return (
        facts,
        {
            "protocol": PROTOCOL,
            "policy_sha256": expected_sha,
            "canonical_sha256": before["sha256"],
            "source_manifest": manifest["files"],
            "scope": "Trusted local canonical validation command, not OS isolation or semantic acceptance.",
        },
    )
