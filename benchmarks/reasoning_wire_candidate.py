"""Narrow request-parameter patch on isolated installed clients only."""

from pathlib import Path

import bounded_evidence_support as S


def patch_client(path, allowed_root=None):
    path = Path(path).resolve()
    base = (
        Path(allowed_root).resolve()
        if allowed_root is not None
        else S.KIT / "benchmarks/work"
    )
    if (
        not path.is_relative_to(base)
        or path.name != "worker-runtime.py"
        or path == S.KIT / ".local-agents/worker-runtime.py"
    ):
        raise ValueError("Only an isolated benchmark client copy may be patched")
    old = path.read_text(encoding="utf-8")
    changes = [
        (
            "        self.last_request_stats: dict[str, Any] = {}\n",
            "        self.last_request_stats: dict[str, Any] = {}\n        self.reasoning_effort: str | None = None\n",
        ),
        (
            '        if self.native_tools is not None:\n            payload["tools"] = self.native_tools\n',
            '        if self.reasoning_effort is not None:\n            if self.reasoning_effort not in {"low", "medium", "high", "xhigh"}:\n                raise WorkerError("Unsupported explicit reasoning effort")\n            payload["reasoning_effort"] = self.reasoning_effort\n        if self.native_tools is not None:\n            payload["tools"] = self.native_tools\n',
        ),
    ]
    for before, after in changes:
        if old.count(before) != 1:
            raise ValueError("Client patch anchor differs or already patched")
        old = old.replace(before, after, 1)
    before_sha = S.sha(path)
    compile(old, str(path), "exec")
    path.write_text(old, encoding="utf-8", newline="\n")
    return {
        "path": str(path),
        "before_sha256": before_sha,
        "after_sha256": S.sha(path),
        "default": "No request parameter when None; Coder/default client behavior unchanged",
        "scope": "Only request parameter plumbing, existing response parsing and action validation retained",
    }
