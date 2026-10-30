"""Lossless literal display of the existing pytest excerpt; no new evidence."""

import json
import shutil
from pathlib import Path

NAME = "validation_failure.focused_tests.excerpt"


def extend(namespace):
    original_fields, original_restore = namespace["fields"], namespace["restore"]

    def fields(facts):
        yield from original_fields(facts)
        focused = facts.get("validation_failure", {}).get("focused_tests")
        if isinstance(focused, dict) and isinstance(focused.get("excerpt"), str):
            yield NAME, focused, "excerpt"

    def restore(text):
        metadata, _ = json.JSONDecoder().raw_decode(text)
        focused = metadata.get("validation_failure", {}).get("focused_tests")
        if not isinstance(focused, dict) or focused.get("excerpt") != {"display_block": NAME}:
            return original_restore(text)
        begin, end = f"\n\n<BEGIN {NAME}>\n", f"\n<END {NAME}>"
        prefix, separator, tail = text.rpartition(begin)
        if not separator or not tail.endswith(end) or tail.count(end) != 1:
            raise ValueError("Failure excerpt display binding mismatch")
        result = original_restore(prefix)
        result["validation_failure"]["focused_tests"]["excerpt"] = tail[:-len(end)]
        return result

    namespace["fields"], namespace["restore"] = fields, restore


def install(root):
    root = Path(root).resolve()
    allowed = Path(__file__).resolve().parent / "work/harness-convergence"
    if not root.is_relative_to(allowed):
        raise ValueError("Literal failure candidate requires isolated experiment root")
    target = root / ".local-agents/bounded/literal_check_feedback.py"
    source = target.read_text(encoding="utf-8")
    marker = "from .literal_failure_feedback import extend"
    if marker in source:
        raise ValueError("Literal failure candidate already installed")
    shutil.copyfile(__file__, target.with_name("literal_failure_feedback.py"))
    target.write_text(source + "\n" + marker + "\nextend(globals())\n", encoding="utf-8")
