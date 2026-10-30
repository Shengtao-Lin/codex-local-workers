"""Optional observed-line transport; scope, versions and commit stay host-owned."""

from itertools import pairwise

from general_state import StateError

PROFILE = "observed-lines-v1"


class EditTargetError(ValueError):
    def __init__(self, message, details):
        super().__init__(message)
        self.details = details


def enabled(config):
    return config.get("experimental_strata_edit_profile") == PROFILE


def validate_profile(config):
    value = config.get("experimental_strata_edit_profile")
    if value not in (None, PROFILE):
        raise StateError("Unknown experimental Strata edit profile")
    if value and (
        config.get("strata_version_references") != "observed-v1"
        or config.get("experimental_native_tools_trial")
    ):
        raise StateError("Observed-line edits require observed-v1 references and kit editor")


def render(host, path, raw, digest, edits):
    """All disjoint inclusive ranges refer to the same observed original version.

    No guessed target, retyped old text, fuzzy match or line-number-only authority.
    Output still passes the existing SafeEditor, formatter and atomic transaction.
    """
    text = raw.decode("utf-8-sig")
    lines = text.splitlines(keepends=True)
    coverage = host.ledger.state.get("evidence_coverage", {}).get(path, {})
    seen = set(coverage.get("lines", [])) if coverage.get("sha256") == digest else set()
    spans = []
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {"start_line", "end_line", "replace"}:
            raise ValueError("Line edits require start_line,end_line,replace only")
        start, end, replacement = edit["start_line"], edit["end_line"], edit["replace"]
        if type(start) is not int or type(end) is not int or not isinstance(replacement, str):
            raise TypeError("Line range requires integer bounds and string replacement")
        details = {
            "path": path,
            "start_line": start,
            "end_line": end,
            "line_count": len(lines),
            "current_sha256": digest,
            "next_action": "read the intended current range;submit disjoint observed ranges",
        }
        if not 1 <= start <= end <= len(lines) or end - start + 1 > 120:
            raise EditTargetError("Invalid line range;read a legal1..120-line range", details)
        if not set(range(start, end + 1)) <= seen:
            raise EditTargetError("Edit range contains unobserved current source lines", details)
        if replacement and end < len(lines) and not replacement.endswith(("\n", "\r")):
            raise EditTargetError("Non-final line replacement must end with a newline", details)
        spans.append((start, end, replacement))
    spans.sort()
    if any(right[0] <= left[1] for left, right in pairwise(spans)):
        raise EditTargetError("Overlapping line edits are rejected", {"path": path})
    newline = "\r\n" if "\r\n" in text else "\n"
    for start, end, replacement in reversed(spans):
        normalized = replacement.replace("\r\n", "\n").replace("\r", "\n").replace("\n", newline)
        lines[start - 1 : end] = [normalized]
    return text, "".join(lines)
