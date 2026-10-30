"""Model-facing facts without repeated validation inventories or false summaries."""

import copy
import json

from general_versions import observation_view


def validation_view(value):
    if value is None:
        return None
    focused = value.get("focused_tests") or {}
    junit = focused.get("junit") or {}
    return {
        "status": value["status"],
        "syntax": value.get("py_compile"),
        "focused_tests": {
            "status": focused.get("status"),
            "junit": {
                k: junit.get(k)
                for k in ("available", "tests", "executed", "failures", "errors", "skipped")
            },
            "diagnostic": focused.get("diagnostic"),
            "inputs_unchanged": focused.get("inputs_unchanged"),
        },
        "configured_checks": [
            {
                k: c.get(k)
                for k in ("id", "status", "exit_code", "output", "timed_out", "output_truncated")
            }
            for c in value.get("configured_checks") or []
        ],
        "quality_gate": value.get("quality_gate"),
    }


def review_checks_view(checks):
    """Keep observed check facts; canonical inventories stay in the readable receipt."""
    commands = validation_view(checks["commands"])
    for current, original in zip(
        commands["configured_checks"],
        checks["commands"].get("configured_checks") or [],
        strict=True,
    ):
        for field in ("argv", "cwd"):
            if field in original:
                current[field] = copy.deepcopy(original[field])
        if isinstance(original.get("diagnostic"), dict):
            current["diagnostic"] = {
                key: copy.deepcopy(value)
                for key, value in original["diagnostic"].items()
                if key != "passed_test_ids"
            }
    result = {
        "canonical_path": checks["canonical_path"],
        "canonical_sha256": checks["canonical_sha256"],
        "commands": commands,
        "binding": "Host verifies current complete input inventory;full immutable receipt remains readable",
    }
    for field in ("contract_sha256", "limits"):
        if field in checks:
            result[field] = copy.deepcopy(checks[field])
    return result


def evidence_window(observations, current_hashes, *, byte_limit=16000, preferred_paths=()):
    result = []
    preferred = set(preferred_paths)

    def priority(item):
        observation = item["observation"]
        if observation.get("content"):
            return 0 if observation.get("path") in preferred else 1
        return 2 if observation.get("matches") else 3

    seen = set()
    for item in sorted(reversed(observations), key=priority):
        if any(current_hashes.get(p) != h for p, h in item["hashes"].items()):
            continue
        key = json.dumps(item["observation"], sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        candidate = [*result, item["observation"]]
        if len(json.dumps(candidate, ensure_ascii=False).encode("utf-8")) > byte_limit:
            continue
        result = candidate
    return result


def model_view(context, *, observations=(), writable_paths=None, preferred_evidence_paths=()):
    value = copy.deepcopy(context)
    all_files = value["files"]
    if "task" in value:
        scope = value["task"]["scope"]
        value["task"]["scope"] = {k: scope[k] for k in ("modify", "create", "forbidden")}
        value["task"]["scope"]["all_other_approved_files_readonly"] = True
        value["task"]["approved_readable_files"] = sorted(all_files)
    value["validation"] = validation_view(value.get("validation"))
    # This is a model projection only. Full failed checks, hashes and diagnostic
    # bindings remain in the immutable canonical material and readable receipt.
    # Only the explicit observed-line normal review also uses the compact view.
    material = value.get("task", {}).get("review_material")
    if (
        value.get("report_limits", {}).get("legal_statuses") == ["rework", "insufficient_evidence"]
        and isinstance(material, dict)
        and material.get("checks", {}).get("purpose") == "failed-draft-v1"
    ):
        checks = material["checks"]
        material["checks"] = {
            "purpose": checks["purpose"],
            "canonical_path": checks["canonical_path"],
            "canonical_sha256": checks["canonical_sha256"],
            "commands": validation_view(checks["commands"]),
            "binding": "Host verifies current complete input inventory;full immutable receipt remains readable",
        }
    elif (
        value.get("task", {}).get("mode") == "review"
        and value.get("report_limits", {}).get("citation_fields") == ["path", "line"]
        and value.get("report_limits", {}).get("legal_statuses")
        == ["pass_to_primary", "rework", "insufficient_evidence"]
        and isinstance(material, dict)
    ):
        material["checks"] = review_checks_view(material["checks"])
    check = value.get("current_check")
    if check:
        value["current_check"] = {
            "path": check["path"],
            "sha256": check["sha256"],
            "binding": "Host checks current complete input inventory; full receipt archived",
        }
    if observations:
        value["recent_evidence"] = evidence_window(
            observations, all_files, preferred_paths=preferred_evidence_paths
        )
    if writable_paths is not None:
        value["files"] = {p: h for p, h in all_files.items() if p in writable_paths}
    if "version_references" in value:
        references = value.pop("version_references")
        value = observation_view(value, references)
        value["files"] = {p: references.get(p) for p in value["files"]}
        value["version_reference_profile"] = "observed-v1"
    resources = value.pop("resources")
    value["tool_budget"] = {
        "remaining": {k: resources["limits"][k] - used for k, used in resources["used"].items()},
        "remaining_seconds": resources["remaining_seconds"],
        "read_max_lines": 120,
        "search_max_matches": 10,
        "note": "Reserve requests for edits and submit. Counters persist across attempts.",
    }
    if "continuation_stage" in resources:
        value["tool_budget"]["stage"] = resources["continuation_stage"]
        value["tool_budget"]["task_remaining"] = {
            k: resources["task_limits"][k] - used for k, used in resources["used"].items()
        }
        value["tool_budget"]["note"] = (
            "remaining is the current stage allowance;task_remaining is the shared total. "
            "One follow-up may use the original unspent total;no credits are replenished."
        )
    if "report_repair" in resources:
        value["tool_budget"]["report_repair"] = resources["report_repair"]
    return value
