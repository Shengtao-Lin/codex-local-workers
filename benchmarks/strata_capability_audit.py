"""Read-only, exact-file inventory. Installed plugins are NOT enabled tools.

Never import/launch the inspected harness, evaluate its YAML, read credentials,
or contact a provider. Output is create-only and contains hashes + short evidence.
"""

import argparse
import hashlib
import json
import stat
from pathlib import Path

from bounded_evidence_support import save

FILES = {
    "bundle": "BUNDLE.json",
    "sdk": "node_modules/@deepseek-ai/dsh-sdk-minimal/cordis.patch.yml",
    "files": "node_modules/@deepseek-ai/dsh-tool-fs/lib/types/index.d.ts",
    "web": "node_modules/@deepseek-ai/dsh-tool-web/lib/types/index.d.ts",
    "skills": "node_modules/@deepseek-ai/dsh-skill/lib/types/index.d.ts",
    "skill_roots": "node_modules/@deepseek-ai/dsh-skill-filesystem/lib/types/index.d.ts",
    "subagents": "node_modules/@deepseek-ai/dsh-tool-subagent/lib/types/index.d.ts",
    "rpc": "node_modules/@deepseek-ai/dsh-sdk-jsonrpc-server/lib/types/index.d.ts",
}
MARKERS = {
    "sdk": ["DEEPSEEK_API_KEY", "danger-full-access", "maxTokensAsSuccess: false"],
    "files": ["without one the tools use unconditional provider calls"],
    "web": ["never concrete providers", "provider is unavailable"],
    "skills": ["exposes the winning summaries and definitions"],
    "skill_roots": ["includeDefaultRoots?: boolean", "customSkillDirs?: string[]"],
    "subagents": ["provider: string", "maxDepth?: number"],
    "rpc": ["maxTokensAsSuccess?: boolean"],
}


def read_exact(root, relative):
    """Inspect only known regular files, without following reparse ancestors."""
    if relative not in FILES.values():
        raise ValueError("Not in the exact inspection manifest")
    root = Path(root).absolute()
    path = root / relative
    for item in reversed([path, *path.parents]):
        info = item.lstat()
        if item.is_symlink() or getattr(info, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
        ):
            raise ValueError("Inspection rejects reparse paths")
    if not path.is_file() or path.stat().st_size > 256_000:
        raise ValueError("Inspection requires a bounded regular file")
    raw = path.read_bytes()
    return raw.decode("utf-8-sig"), hashlib.sha256(raw).hexdigest()


def inspect(root):
    records = {}
    for key, relative in FILES.items():
        try:
            text, sha = read_exact(root, relative)
            records[key] = {
                "path": relative,
                "status": "PRESENT_STATIC_ONLY",
                "sha256": sha,
                "evidence": [
                    {"marker": marker, "line": n, "text": line.strip()[:240]}
                    for marker in MARKERS.get(key, [])
                    for n, line in enumerate(text.splitlines(), 1)
                    if marker in line
                ],
            }
            if key == "bundle":
                bundle = json.loads(text)
                if not isinstance(bundle, dict):
                    raise ValueError("Bundle metadata must be an object")
                records[key]["version"] = bundle.get("version", "unknown")
        except (OSError, ValueError) as exc:
            records[key] = {
                "path": relative,
                "status": "UNKNOWN_OR_REJECTED",
                "reason": str(exc),
            }
    observed = {
        e["marker"] for record in records.values() for e in record.get("evidence", [])
    }
    blockers = []
    for marker, explanation in (
        (
            "DEEPSEEK_API_KEY",
            "Bundled SDK declares a cloud credential adapter, not our verified local-only route.",
        ),
        (
            "danger-full-access",
            "Bundled SDK declares full host access; cwd is not an OS security boundary.",
        ),
        (
            "without one the tools use unconditional provider calls",
            "Filesystem tools need an explicit mutation policy before task-scope use.",
        ),
        (
            "provider is unavailable",
            "Installed Web tool schemas do not prove a working search/fetch provider.",
        ),
    ):
        if marker in observed:
            blockers.append(explanation)
    return {
        "schema_version": 1,
        "status": "STATIC_INVENTORY_ONLY_NOT_RUNTIME_QUALIFICATION",
        "root": str(Path(root).absolute()),
        "files": records,
        "observed_blockers": blockers,
        # Missing warning markers are NOT a safety certification.
        "native_launch_authorized_by_this_report": False,
        "provider_calls": 0,
        "commands_executed": 0,
        "credentials_read": False,
        "enabled_features": [],
        "unknown": [
            "effective running plugin tree and overrides",
            "local endpoint/model compatibility of native agent loop",
            "native task-scope enforcement and actual Web provider",
            "native context compaction retaining contracts and failure evidence",
            "independent acceptance correctness or Primary cost reduction",
        ],
    }


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("F:/Strata/harness"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.root)
    save(args.output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "blockers": result["observed_blockers"],
                "provider_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
