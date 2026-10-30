"""Opt-in diagnostic feedback; preserve the original decoder's accepted language."""

import json


def wrap_decode(original):
    def decode(raw):
        try:
            return original(raw)
        except ValueError as exc:
            if str(exc) != "Proposal must be a nonempty string":
                raise
            value = json.loads(raw)
            active = {k: v for k, v in value.items() if v is not None}
            field, received = next(iter(active.items()))
            kind = (
                "boolean" if isinstance(received, bool)
                else "array" if isinstance(received, list)
                else "object" if isinstance(received, dict)
                else "string" if isinstance(received, str)
                else "number"
            )
            example = (
                '{"replacement":"<complete function source as one string>"}'
                if field == "replacement"
                else '{"blocked_reason":"<concrete missing evidence or permission>"}'
            )
            raise ValueError(
                f"Protocol error: field '{field}' expects a nonempty string; received {kind}. "
                "No proposal was applied; current source is unchanged. "
                f"Return {example}. Encode source newlines inside the JSON string as \\n."
            ) from exc

    return decode


def install(root):
    """Apply only to a newly prepared isolated installation, before any run."""
    import shutil
    from pathlib import Path

    root = Path(root).resolve()
    allowed = Path(__file__).resolve().parent / "work/harness-convergence"
    if not root.is_relative_to(allowed):
        raise ValueError("Feedback candidate requires an isolated experiment root")
    target = root / ".local-agents/bounded/harness_protocol.py"
    source = target.read_text(encoding="utf-8")
    marker = "from .proposal_field_feedback import wrap_decode"
    if marker in source:
        raise ValueError("Candidate already installed")
    shutil.copyfile(__file__, target.with_name("proposal_field_feedback.py"))
    target.write_text(
        source + "\n" + marker + "\ndecode = wrap_decode(decode)\n",
        encoding="utf-8",
    )
