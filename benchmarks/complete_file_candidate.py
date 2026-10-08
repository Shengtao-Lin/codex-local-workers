"""Default-off diagnostic adapter for complete-file content, never tool actions."""

import ast
import hashlib
import re
import subprocess
import sys

import contract_presentation_repair as original


def prepare_patch(raw, writable, *, enabled=False):
    metadata = {"enabled": enabled, "normalized": False, "original_error": None}
    try:
        patch, fence = original.decode(raw, writable)
        metadata["fence_removed"] = fence
    except ValueError as error:
        if not enabled:
            raise
        metadata["original_error"] = str(error)
        matches = list(
            re.finditer(
                r"(?m)^```(python|py|json)[ \t]*\r?\n(.*?)^```[ \t]*$", raw, re.S
            )
        )
        if len(matches) != 1 or raw.count("```") != 2:
            raise ValueError("ambiguous or missing complete-file code block") from error
        match = matches[0]
        expected = ("python", "py") if len(writable) == 1 else ("json",)
        if match[1] not in expected:
            raise ValueError("wrong code block language") from error
        patch, _ = original.decode(match[2], writable)
        metadata.update(normalized=True, fence_removed=True)
    # Parse every file before any edit; no scope additions or path repair.
    for item in patch:
        compile(item["content"], item["path"], "exec")
    if enabled:
        formatted = []
        for item in patch:
            source = item["content"]
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "format",
                    "--isolated",
                    "--line-length",
                    "100",
                    "--stdin-filename",
                    item["path"],
                    "-",
                ],
                input=source,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
                check=False,
            )
            if process.returncode:
                raise ValueError("trusted formatter failed: " + process.stderr[:500])
            if ast.dump(ast.parse(source)) != ast.dump(ast.parse(process.stdout)):
                raise ValueError("formatter changed AST")
            formatted.append({"path": item["path"], "content": process.stdout})
        patch = formatted
    metadata["source_hashes"] = {
        p["path"]: hashlib.sha256(p["content"].encode()).hexdigest() for p in patch
    }
    return patch, metadata
