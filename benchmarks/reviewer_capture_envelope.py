"""Offline command-output boundary only; NOT canonical archive authentication.

Callers must first authenticate the canonical validation/run and input epoch.
No execution, model call, report assembly, or production integration is provided.
"""

import copy
import hashlib
import json
import stat
from pathlib import Path, PurePosixPath


class CaptureRejected(ValueError):
    pass


def source_manifest(root, paths, *, approved_paths):
    """Hash an explicit trusted manifest, not dynamic import coverage or scope discovery.

    No reads are permitted outside approved_paths. This does not authenticate
    its caller or prevent unrelated processes racing filesystem operations.
    """
    root = Path(root).resolve(strict=True)
    if not isinstance(paths, list) or not 1 <= len(paths) <= 128:
        raise CaptureRejected("invalid manifest size")
    files = {}
    aliases = set()
    for name in paths:
        if (
            not isinstance(name, str)
            or not name
            or "\\" in name
            or ":" in name
            or name not in approved_paths
        ):
            raise CaptureRejected("unapproved manifest path")
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or str(relative) != name
            or any(part in {".", ".."} for part in relative.parts)
            or name.casefold() in aliases
        ):
            raise CaptureRejected("ambiguous or escaping manifest path")
        aliases.add(name.casefold())
        target = root
        try:
            for part in relative.parts:
                target = target / part
                info = target.lstat()
                if (
                    stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400
                ):
                    raise CaptureRejected("reparse manifest path")
            if (
                not target.resolve(strict=True).is_relative_to(root)
                or not target.is_file()
            ):
                raise CaptureRejected("manifest path is not an in-scope file")
            files[name] = hashlib.sha256(target.read_bytes()).hexdigest()
        except OSError as exc:
            raise CaptureRejected("manifest file unavailable") from exc
    encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"files": files, "sha256": hashlib.sha256(encoded).hexdigest()}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CaptureRejected("duplicate JSON key")
        result[key] = value
    return result


def _constant(value):
    raise CaptureRejected("non-finite JSON value: " + value)


def parse_command_capture(checks, *, check_id, argv, bindings):
    """Check a caller-authenticated command record against trusted bindings.

    Bindings must come from independently verified archive/input facts, never
    from the capture's own claims. A parsed capture is not a behavior pass.
    This narrow envelope intentionally treats observations as opaque data;
    a family-specific factual DTO validator is still required before use.
    """
    if not isinstance(checks, list) or any(not isinstance(c, dict) for c in checks):
        raise CaptureRejected("configured checks must be objects")
    matches = [c for c in checks if c.get("id") == check_id]
    if len(matches) != 1:
        raise CaptureRejected("capture check missing or duplicated")
    check = matches[0]
    if (
        check.get("status") != "passed"
        or type(check.get("exit_code")) is not int
        or check["exit_code"] != 0
        or check.get("output_truncated") is not False
        or check.get("timed_out", False) is not False
        or check.get("argv") != argv
    ):
        raise CaptureRejected("command failed, truncated, or argv changed")
    output = check.get("output")
    if not isinstance(output, str) or len(output.encode("utf-8")) > 65536:
        raise CaptureRejected("invalid or oversized capture output")
    try:
        data = json.loads(output, object_pairs_hook=_object, parse_constant=_constant)
    except (ValueError, RecursionError) as exc:
        raise CaptureRejected("capture is not complete strict JSON") from exc
    if not isinstance(data, dict) or set(data) != {
        "schema_version",
        "bindings",
        "observations",
    }:
        raise CaptureRejected("unknown capture envelope fields")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise CaptureRejected("unsupported capture version")
    required = {
        "task_id",
        "run_id",
        "producer_sha256",
        "profile_sha256",
        "source_manifest_sha256",
    }
    if (
        not isinstance(bindings, dict)
        or set(bindings) != required
        or any(not isinstance(v, str) or not v for v in bindings.values())
        or not isinstance(data["bindings"], dict)
        or data["bindings"] != bindings
    ):
        raise CaptureRejected("capture does not match trusted bindings")
    if (
        not isinstance(data["observations"], list)
        or not 1 <= len(data["observations"]) <= 8
    ):
        raise CaptureRejected("invalid observation count")
    return copy.deepcopy(data["observations"])
