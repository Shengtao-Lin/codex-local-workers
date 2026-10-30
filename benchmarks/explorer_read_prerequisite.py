"""Narrow isolated-copy fix: source acquisition precedes report-only repair."""

from pathlib import Path

import bounded_evidence_support as S

WORK = S.KIT / "benchmarks/work/harness-convergence"


def install(path, allowed_root):
    path, root = Path(path).resolve(), Path(allowed_root).resolve()
    if not root.is_relative_to(WORK) or not path.is_relative_to(root):
        raise ValueError("Isolated experimental copy required")
    if path.name != "explorer-runtime.py" or path.parent.name != ".local-agents":
        raise ValueError("Unexpected Explorer runtime path")
    source = path.read_text(encoding="utf-8")
    old = (
        '                    needs_read = self.mode == "locate" and (\n'
        "                        isinstance(exc, ExplorerSourceReferenceError) and bool(exc.read_paths)\n"
        "                    )\n"
    )
    new = (
        "                    missing_required_reads = [\n"
        "                        normalize_relative_path(p)\n"
        '                        for p in self.config.get("explorer_required_citation_paths", [])\n'
        "                        if normalize_relative_path(p) not in self.read_files\n"
        "                    ]\n"
        "                    needs_read = bool(missing_required_reads) or (\n"
        '                        self.mode == "locate" and isinstance(exc, ExplorerSourceReferenceError)\n'
        "                        and bool(exc.read_paths)\n"
        "                    )\n"
    )
    line = '                        observation["next_step"] += " Required reads: " + ", ".join(exc.read_paths)\n'
    replacement = (
        '                        observation["next_step"] += " Required reads: " + ", ".join(\n'
        '                            getattr(exc, "read_paths", ()) or missing_required_reads\n'
        "                        )\n"
    )
    if source.count(old) != 1 or source.count(line) != 1:
        raise ValueError("Unrecognized source; refuse broad patch")
    before = S.sha(path)
    path.write_text(
        source.replace(old, new, 1).replace(line, replacement, 1), encoding="utf-8"
    )
    return {
        "before": before,
        "after": S.sha(path),
        "scope": "Missing already-required source acquisition only; no report acceptance, permissions or budget expansion",
    }
