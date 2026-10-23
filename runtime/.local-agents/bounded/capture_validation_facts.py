import argparse
import copy
import hashlib
import importlib
import importlib.util
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

if __package__:
    from .reviewer_capture_envelope import CaptureRejected, source_manifest
else:
    from reviewer_capture_envelope import CaptureRejected, source_manifest
MEANING = "Actual outcomes for this exact source in the fixed evaluation environment, not expected results or a contract verdict. Ephemeral observations did not add or modify project tests."
FAMILIES = {
    "json-call-model-dump-v1": None,
    "fixed-pure-display_name-v1": "display_name",
    "fixed-pure-lookup_or-v1": "lookup_or",
    "fixed-pure-increment-v1": "increment",
    "collect-tools-json-observation-v1": "collect_tools",
    "canonical-json-bytes-v1": "canonical_json",
    "mapping-raw-utf8-v1": "mapping_raw",
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bounded_json(value, depth=0):
    if depth > 10:
        raise CaptureRejected("data nesting exceeds limit")
    if value is None or type(value) is bool:
        return
    if type(value) in {int, float} and abs(value) <= 1000000 and math.isfinite(value):
        return
    if isinstance(value, str) and len(value) <= 2048:
        return
    if isinstance(value, (list, dict)) and len(value) <= 32:
        items = value.items() if isinstance(value, dict) else enumerate(value)
        for key, item in items:
            if isinstance(value, dict) and (not isinstance(key, str) or len(key) > 128):
                raise CaptureRejected("invalid data key")
            bounded_json(item, depth + 1)
        return
    raise CaptureRejected("only bounded finite JSON data is allowed")


def validate_policy(policy):
    fields = {
        "schema_version",
        "identity",
        "check_id",
        "producer_path",
        "producer_sha256",
        "helper_path",
        "helper_sha256",
        "python",
        "target",
        "source_paths",
        "readonly_hashes",
        "family",
        "cases",
    }
    if (
        not isinstance(policy, dict)
        or set(policy) != fields
        or type(policy["schema_version"]) is not int
        or (policy["schema_version"] != 1)
    ):
        raise CaptureRejected("invalid capture policy fields")
    if not isinstance(policy["identity"], dict) or set(policy["identity"]) != {
        "task_id",
        "unit_id",
        "run_id",
    }:
        raise CaptureRejected("invalid capture identity")
    for value in [*policy["identity"].values(), policy["check_id"]]:
        if (
            not isinstance(value, str)
            or not value
            or len(value) > 128
            or any(
                (
                    c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
                    for c in value
                )
            )
        ):
            raise CaptureRejected("invalid identity value")
    if not isinstance(policy["target"], dict) or set(policy["target"]) != {
        "path",
        "module",
        "symbol",
    }:
        raise CaptureRejected("invalid target")
    if (
        policy["family"] not in FAMILIES
        or not isinstance(policy["target"]["symbol"], str)
        or (not policy["target"]["symbol"].isidentifier())
        or (
            FAMILIES[policy["family"]] is not None
            and policy["target"]["symbol"] != FAMILIES[policy["family"]]
        )
    ):
        raise CaptureRejected("unsupported capture family/symbol")
    module = policy["target"]["module"]
    if not isinstance(module, str) or not all((part.isidentifier() for part in module.split("."))):
        raise CaptureRejected("invalid module")
    if (
        not isinstance(policy["source_paths"], list)
        or not policy["source_paths"]
        or policy["target"]["path"] not in policy["source_paths"]
    ):
        raise CaptureRejected("target missing from explicit dependency manifest")
    if not isinstance(policy["readonly_hashes"], dict):
        raise CaptureRejected("readonly hashes missing")
    if not isinstance(policy["python"], dict) or set(policy["python"]) != {"path", "sha256"}:
        raise CaptureRejected("invalid interpreter binding")
    for sha in [
        policy["producer_sha256"],
        policy["helper_sha256"],
        policy["python"]["sha256"],
        *policy["readonly_hashes"].values(),
    ]:
        if (
            not isinstance(sha, str)
            or len(sha) != 64
            or any((c not in "0123456789abcdef" for c in sha))
        ):
            raise CaptureRejected("invalid digest")
    cases = policy["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 8:
        raise CaptureRejected("requires one to eight cases")
    bounded_json(cases)
    if len(json.dumps(cases, allow_nan=False).encode()) > 8192:
        raise CaptureRejected("case data exceeds eight KiB")
    family = policy["family"]
    for case in cases:
        if family in {"json-call-model-dump-v1", "canonical-json-bytes-v1"} and (
            not isinstance(case, dict)
            or set(case) != {"args", "kwargs"}
            or (not isinstance(case["args"], list))
            or (not isinstance(case["kwargs"], dict))
        ):
            raise CaptureRejected("generic calls require bounded positional and keyword data")
        if family == "mapping-raw-utf8-v1" and (
            not isinstance(case, dict)
            or set(case) != {"text", "kind"}
            or (not isinstance(case["text"], str))
            or (case["kind"] not in {"str", "bytes", "bytearray"})
        ):
            raise CaptureRejected("raw mapping requires bounded text and fixed input kind")
        if family.endswith("display_name-v1") and (not isinstance(case, dict)):
            raise CaptureRejected("display_name requires record data")
        if family.endswith("increment-v1") and type(case) is not int:
            raise CaptureRejected("increment requires integers")
        if family.endswith("lookup_or-v1"):
            if (
                not isinstance(case, dict)
                or set(case) != {"fetch_behavior", "fetch_value_or_exception", "key", "default"}
                or case["fetch_behavior"] not in {"return", "raise"}
            ):
                raise CaptureRejected("invalid lookup case")
            if case["fetch_behavior"] == "raise" and case["fetch_value_or_exception"] not in {
                "KeyError",
                "RuntimeError",
            }:
                raise CaptureRejected("unsupported lookup exception")
        if family == "collect-tools-json-observation-v1":
            if (
                not isinstance(case, dict)
                or set(case) != {"parts"}
                or (not isinstance(case["parts"], list))
                or (not 1 <= len(case["parts"]) <= 16)
            ):
                raise CaptureRejected("invalid typed event sequence")
            for part in case["parts"]:
                if not isinstance(part, dict):
                    raise CaptureRejected("part must be data")
                kind = part.get("type")
                keys = (
                    {"type", "call_id", "name", "arguments"}
                    if kind == "tool_call"
                    else {"type", "call_id", "result"}
                )
                if (
                    kind not in {"tool_call", "tool_result"}
                    or set(part) != keys
                    or (not isinstance(part["call_id"], str))
                    or (not 1 <= len(part["call_id"]) <= 128)
                ):
                    raise CaptureRejected("invalid event fields")
                if kind == "tool_call" and (
                    not isinstance(part["name"], str) or not isinstance(part["arguments"], dict)
                ):
                    raise CaptureRejected("invalid tool call")
    return policy


def manifest_for(root, policy_path, policy):
    paths = [*policy["source_paths"], policy["producer_path"], policy["helper_path"], policy_path]
    manifest = source_manifest(root, paths, approved_paths=paths)
    for path, sha in {
        **policy["readonly_hashes"],
        policy["producer_path"]: policy["producer_sha256"],
        policy["helper_path"]: policy["helper_sha256"],
    }.items():
        if manifest["files"].get(path) != sha:
            raise CaptureRejected("pinned capture dependency changed: " + path)
    return manifest


def observe(module, policy):
    function = getattr(module, policy["target"]["symbol"])
    examples = []
    family = policy["family"]
    for original in policy["cases"]:
        case = copy.deepcopy(original)
        example = {"input": copy.deepcopy(case)}
        calls = []
        raised = None
        before = None
        if family == "collect-tools-json-observation-v1":
            parts = [
                (module.ToolCallPart if p["type"] == "tool_call" else module.ToolResultPart)(
                    **{k: v for k, v in p.items() if k != "type"}
                )
                for p in case["parts"]
            ]
            messages = [
                module.CanonicalMessage(message_id="observation", role="assistant", content=parts)
            ]
            before = [m.model_dump(mode="json") for m in messages]
        try:
            if family in {"json-call-model-dump-v1", "canonical-json-bytes-v1"}:
                value = function(*case["args"], **case["kwargs"])
                if hasattr(value, "model_dump"):
                    value = value.model_dump(mode="json")
                if family == "canonical-json-bytes-v1":
                    if not isinstance(value, bytes):
                        raise CaptureRejected("canonical JSON observation requires bytes")
                    value = {"type": "bytes", "hex": value.hex()}
            elif family == "mapping-raw-utf8-v1":
                raw = case["text"]
                if case["kind"] in {"bytes", "bytearray"}:
                    raw = raw.encode("utf-8")
                    if case["kind"] == "bytearray":
                        raw = bytearray(raw)
                trace = module.SourceTrace(
                    source_trace_id="observation",
                    observed_at=datetime(2026, 1, 1, tzinfo=UTC),
                    raw=raw,
                )
                before = copy.deepcopy(trace.raw)
                value = function(trace)
            elif family.endswith("lookup_or-v1"):
                raised = (
                    KeyError("missing")
                    if case["fetch_value_or_exception"] == "KeyError"
                    else RuntimeError("failure")
                )

                def fetch(key, calls=calls, case=case, raised=raised):
                    calls.append(key)
                    if case["fetch_behavior"] == "raise":
                        raise raised
                    return case["fetch_value_or_exception"]

                value = function(fetch, case["key"], case["default"])
            elif family == "collect-tools-json-observation-v1":
                value = [
                    {
                        k: item.model_dump(mode="json")[k]
                        for k in ("call_id", "name", "arguments", "result", "status")
                    }
                    for item in function(messages)
                ]
            else:
                value = function(case)
            outcome = {"kind": "returned", "value": value}
        except (TypeError, ValueError, AttributeError, KeyError, IndexError, RuntimeError) as exc:
            outcome = {"kind": "raised", "type": type(exc).__name__}
            if family.endswith("lookup_or-v1"):
                outcome["same_exception_instance"] = exc is raised
            else:
                outcome["message"] = str(exc)[:1000]
        example["outcome"] = outcome
        if family.endswith("lookup_or-v1"):
            example["fetch_calls"] = calls
        elif family.endswith("display_name-v1") or family in {
            "json-call-model-dump-v1",
            "canonical-json-bytes-v1",
        }:
            example["input_unchanged"] = original == case
        elif family == "mapping-raw-utf8-v1":
            example["input_unchanged"] = before == trace.raw
        elif family == "collect-tools-json-observation-v1":
            example["input_unchanged"] = before == [m.model_dump(mode="json") for m in messages]
        examples.append(example)
    return examples


def capture(root, policy_path):
    root = Path(root).resolve(strict=True)
    source_manifest(root, [policy_path], approved_paths=[policy_path])
    policy = validate_policy(json.loads((root / policy_path).read_text(encoding="utf-8")))
    before = manifest_for(root, policy_path, policy)
    if (
        digest(sys.executable) != policy["python"]["sha256"]
        or Path(sys.executable).resolve() != Path(policy["python"]["path"]).resolve()
    ):
        raise CaptureRejected("wrong interpreter")
    if Path(__file__).resolve() != (root / policy["producer_path"]).resolve():
        raise CaptureRejected("wrong producer location")
    helper = sys.modules["reviewer_capture_envelope"]
    if Path(helper.__file__).resolve() != (root / policy["helper_path"]).resolve():
        raise CaptureRejected("wrong helper import")
    sys.path.insert(0, str(root / "src"))
    target = policy["target"]
    if target["module"] == "_capture_pure_target":
        spec = importlib.util.spec_from_file_location(target["module"], root / target["path"])
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    else:
        module = importlib.import_module(target["module"])
    if Path(module.__file__).resolve() != (root / target["path"]).resolve():
        raise CaptureRejected("imported different repository source")
    examples = observe(module, policy)
    prefix = target["module"].split(".")[0]
    for name, loaded in list(sys.modules.items()):
        filename = getattr(loaded, "__file__", None)
        if not filename or not str(filename).endswith(".py"):
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(root) and path.relative_to(root).as_posix() not in before["files"]:
            raise CaptureRejected("unmanifested local import: " + name)
        if name.split(".")[0] == prefix and (not path.is_relative_to(root)):
            raise CaptureRejected("module loaded from outside snapshot")
    after = manifest_for(root, policy_path, policy)
    if before != after:
        raise CaptureRejected("source changed during capture")
    profile = {
        "profile_id": policy["family"],
        "source": {"path": target["path"], "sha256": after["files"][target["path"]]},
        "examples": examples,
        "meaning": MEANING,
    }
    result = {
        "schema_version": 1,
        "bindings": {
            "task_id": policy["identity"]["task_id"],
            "run_id": policy["identity"]["run_id"],
            "producer_sha256": policy["producer_sha256"],
            "profile_sha256": after["files"][policy_path],
            "source_manifest_sha256": after["sha256"],
        },
        "observations": [profile],
    }
    output = json.dumps(result, ensure_ascii=False, allow_nan=False)
    if len(output.encode()) > 16000:
        raise CaptureRejected("capture output exceeds trusted command window")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--policy", required=True)
    args = parser.parse_args()
    print(capture(Path.cwd(), args.policy))
