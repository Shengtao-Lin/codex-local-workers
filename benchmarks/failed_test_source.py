"""Mechanical, version-bound failing-test evidence from existing approved inputs."""

import re
from pathlib import Path


def collect(runtime, _binding):
    focused = runtime.validation.focused_tests
    if focused.get("status") != "failed" or focused.get("inputs_unchanged") is not True:
        return []
    allowed = {p.split("::", 1)[0] for p in runtime.packet["focused_tests"]}
    failures = (focused.get("diagnostic") or {}).get("failures", [])
    results = []
    for failure in failures[:3]:
        match = re.match(r"^(.+?):(\d+)(?::|$)", failure.get("location", ""))
        if match is None:
            continue
        path = Path(match[1].replace("\\", "/"))
        try:
            relative = (
                path.relative_to(runtime.repo_root).as_posix()
                if path.is_absolute()
                else path.as_posix()
            )
        except ValueError:
            continue
        if relative not in allowed:
            continue
        # Retain the original runtime path/reparse/scope checks, including forbidden.
        checked, _resolved = runtime._assert_read_allowed(relative)
        if checked != relative:
            continue
        raw, digest = runtime.editor.read_bytes(relative)
        if (focused.get("input_facts") or {}).get(relative, {}).get("sha256") != digest:
            continue
        lines = raw.decode("utf-8-sig").splitlines()
        line = int(match[2])
        if not 1 <= line <= len(lines):
            continue
        start, end = max(1, line - 30), min(len(lines), line + 15)
        key = (relative, digest, start, end)
        cache = getattr(runtime, "_failure_source_cache", None)
        if cache is None:
            cache = runtime._failure_source_cache = set()
        if key not in cache:
            runtime.read_file({"path": relative, "start_line": start, "end_line": end})
            cache.add(key)
            if hasattr(runtime, "ledger"):
                runtime.ledger["host_failure_reads"] = (
                    runtime.ledger.get("host_failure_reads", 0) + 1
                )
        results.append(
            {
                "path": relative,
                "sha256": digest,
                "start_line": start,
                "end_line": end,
                "failed_line": line,
                "test": failure["test"],
                "source": "\n".join(lines[start - 1 : end]),
                "validation_attempt": runtime.validation_count,
                "meaning": "Current approved test source only, not host repair advice or permission to change tests.",
            }
        )
    return results
