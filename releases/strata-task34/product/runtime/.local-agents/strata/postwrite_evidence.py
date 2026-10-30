"""Bounded current owned source returned with an actual failed write/check."""

import ast
import json
import re

from general_memory import observe
from general_state import StateError

MAX_BYTES = 16_000
MAX_LINES = 120
HEADER_LINES = 40
RADIUS = 6
MAX_ENCLOSING_LINES = 80


def enabled(host):
    config = host.config
    return (
        host.policy.get("profile") == "strata-unit-v1"
        and config.get("experimental_strata_continuation") == "task-rework-v1"
        and config.get("strata_version_references") == "observed-v1"
        and config.get("experimental_strata_edit_profile") == "observed-lines-v1"
        and not config.get("experimental_strata_capabilities")
        and not config.get("experimental_native_tools_trial")
        and not config.get("experimental_strata_recovery_evidence")
        and host.versions is not None
    )


def diagnostic_texts(validation):
    checks = [validation.focused_tests, *(validation.configured_checks or [])]
    result = []
    for check in checks:
        if isinstance(check.get("output"), str):
            result.append(check["output"].replace("\\", "/"))
        for failure in (check.get("diagnostic") or {}).get("failures", []):
            for key in ("message", "location"):
                if isinstance(failure.get(key), str):
                    result.append(failure[key].replace("\\", "/"))
    return result


def ranges_for(lines):
    result = []
    for number in sorted(lines):
        if result and result[-1][1] + 1 == number:
            result[-1][1] = number
        else:
            result.append([number, number])
    return result


def enclosing_ranges(source, locations):
    """Return complete small Python functions containing an actual failure line."""
    try:
        tree = ast.parse("\n".join(source))
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return []
    candidates = [
        (min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)]), node)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno is not None
    ]
    ranges = set()
    for location in locations:
        containing = [
            (start, node)
            for start, node in candidates
            if start <= location <= node.end_lineno
            and node.end_lineno - start + 1 <= MAX_ENCLOSING_LINES
        ]
        if containing:
            start, node = min(containing, key=lambda item: item[1].end_lineno - item[0])
            ranges.add((start, node.end_lineno))
    return sorted(ranges)


def preview_fits(result, source, visible, path, digest):
    preview = {**result, "sources": list(result["sources"])}
    for start, end in ranges_for(visible):
        preview["sources"].append(
            {
                "path": path,
                "sha256": digest,
                "start_line": start,
                "end_line": end,
                "content": "\n".join(f"{n}: {source[n - 1]}" for n in range(start, end + 1)),
                "version_ref": "v9999999999-ffffffffffffffff",
            }
        )
    return len(json.dumps(preview, ensure_ascii=False).encode("utf-8")) <= MAX_BYTES - 128


def feedback(host, paths):
    if (
        not enabled(host)
        or host.validation is None
        or host.validation.status != "failed"
        or host.ledger.state["used"]["edits"] < 1
    ):
        return None
    host.guard()
    host.assert_bound()
    owned = set(host.packet["scope"]["modify"]) | set(host.packet["scope"]["create"])
    texts = diagnostic_texts(host.validation)
    result = {
        "purpose": "failed_check_current_owned_source",
        "sources": [],
        "truncated": False,
        "displayed_lines": 0,
        "displayed_bytes": 0,
        "accounting": "Automatic write/check output;no extra read or model call. Lines/bytes recorded separately;context/output/time limits remain.",
    }
    eligible = []
    for path in sorted(set(paths) & owned)[:6]:
        absolute = str(host.repo_root / path).replace("\\", "/")
        expression = re.compile(
            r"(?<![\w/])(?:" + re.escape(absolute) + "|" + re.escape(path) + r"):(\d+)",
            re.IGNORECASE,
        )
        locations = {int(m[1]) for text in texts for m in expression.finditer(text)}
        if not locations:
            continue
        raw, digest = host.editor.read_bytes(path)
        if host.current_hashes().get(path) != digest:
            raise StateError("Postwrite source changed after checks")
        source = raw.decode("utf-8-sig").splitlines()
        locations = {n for n in locations if 1 <= n <= len(source)}
        if not locations:
            continue
        eligible.append((path, digest, source, locations))
    opted_in = host.config.get("experimental_strata_repair_context") == "enclosing-function-v1"
    for index, (path, digest, source, locations) in enumerate(eligible):
        if opted_in:
            # Reserve a fair portion for each remaining failing file; report
            # actual failure lines before headers when output is constrained.
            quota = (MAX_LINES - result["displayed_lines"]) // (len(eligible) - index)
            visible = set()
            for number in sorted(locations):
                if len(visible) < quota:
                    visible.add(number)
                else:
                    result["truncated"] = True
            for distance in range(1, RADIUS + 1):
                for number in sorted(locations):
                    for line in (number - distance, number + distance):
                        if 1 <= line <= len(source) and line not in visible:
                            if len(visible) < quota:
                                visible.add(line)
                            else:
                                result["truncated"] = True
        else:
            quota = MAX_LINES
            visible = set(range(1, min(HEADER_LINES, len(source)) + 1))
            for number in sorted(locations):
                for line in range(max(1, number - RADIUS), min(len(source), number + RADIUS) + 1):
                    if len(visible) < quota:
                        visible.add(line)
                    elif line not in visible:
                        result["truncated"] = True
        if opted_in and path.endswith(".py"):
            for start, end in enclosing_ranges(source, locations):
                missing = set(range(start, end + 1)) - visible
                expanded = visible | missing
                if len(expanded) <= quota and preview_fits(result, source, expanded, path, digest):
                    visible = expanded
                else:
                    result["truncated"] = True
        if opted_in:
            for line in range(1, min(HEADER_LINES, len(source)) + 1):
                if line not in visible:
                    if len(visible) < quota:
                        visible.add(line)
                    else:
                        result["truncated"] = True
        for start, end in ranges_for(visible):
            observation = {
                "path": path,
                "sha256": digest,
                "start_line": start,
                "end_line": end,
                "content": "\n".join(f"{n}: {source[n - 1]}" for n in range(start, end + 1)),
                "version_ref": "v9999999999-ffffffffffffffff",
            }
            result["sources"].append(observation)
            if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > MAX_BYTES - 128:
                result["sources"].pop()
                result["truncated"] = True
                continue
            displayed = range(start, end + 1)
            observe(host.ledger.state.setdefault("evidence_coverage", {}), path, digest, displayed)
            if host.context_coverage is not None:
                observe(host.context_coverage, path, digest, displayed)
            observation["version_ref"] = host.versions.issue(path, digest)
            host.observations.append({"observation": observation.copy(), "hashes": {path: digest}})
            result["displayed_lines"] += end - start + 1
            result["displayed_bytes"] += len(observation["content"].encode("utf-8"))
    if not result["sources"] and not result["truncated"]:
        return None
    wire_bytes = len(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    state = host.ledger.state.setdefault(
        "postwrite_feedback", {"batches": 0, "lines": 0, "bytes": 0}
    )
    state["batches"] += 1
    state["lines"] += result["displayed_lines"]
    state["bytes"] += wire_bytes
    host.ledger.record(
        "failed_check_source_presented",
        {
            "paths": sorted({s["path"] for s in result["sources"]}),
            "lines": result["displayed_lines"],
            "bytes": wire_bytes,
            "truncated": result["truncated"],
            "check": host.ledger.state["latest_check"],
        },
    )
    return result
