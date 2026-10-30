"""Immutable canonical facts, separating incomplete runs from worker success."""

import argparse
import json

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes
from role_usage_facts import summarize

COHORTS = {
    "tool-native-block-1": 5,
    "tool-compatibility-1": 6,
    "tool-compatibility-2": 7,
    "tool-native-history-1": 7,
    "tool-compatibility-3": 8,
    "tool-native-history-2": 8,
    "tool-native-history-3": 8,
    "tool-contract-scope-1": 9,
    "tool-context-scope-1": 10,
    "tool-context-proposal-1": 10,
    "tool-context-compact-1": 10,
    "tool-context-salience-1": 10,
    "tool-context-reference-1": 10,
    "tool-native-nudge-1": 10,
    "tool-plain-result-1": 11,
    "tool-plain-result-2": 12,
    "tool-plain-result-3": 12,
    "tool-deadline-fresh-1": 14,
}


def events(path):
    return (
        [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        if path.is_file()
        else []
    )


def audit(label):
    if not label or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label
    ):
        raise ValueError("safe unique audit label required")
    rows = []
    for cohort, version in COHORTS.items():
        frozen = KIT / f"benchmarks/fixtures/tool-awaitable-v{version}"
        provenance = read(frozen / "provenance.json")
        verify_hashes(frozen, provenance["files"])
        verify_hashes(KIT.parent / "agent-runtime-kit", provenance["original_files"])
        for root in sorted((WORK / cohort).iterdir()):
            if not root.is_dir() or not (root / "src").is_dir():
                continue
            verify_hashes(
                root,
                {
                    p: sha
                    for p, sha in provenance["files"].items()
                    if p != "src/agent_runtime/tools/registry.py"
                },
            )
            runs = []
            for archive in sorted((root / ".agent/tasks").glob("*/runs/*")):
                runs.append(
                    {
                        "archive": str(archive),
                        "completed": read(archive / "completed.json")
                        if (archive / "completed.json").exists()
                        else None,
                        "handoff": read(archive / "handoff.json")
                        if (archive / "handoff.json").exists()
                        else None,
                        "primary": read(archive / "review.json")
                        if (archive / "review.json").exists()
                        else None,
                        "usage": summarize(events(archive / "events.jsonl")),
                        "diff_sha256": digest(archive / "cumulative.diff")
                        if (archive / "cumulative.diff").exists()
                        else None,
                    }
                )
            reviews = [
                {
                    "archive": str(archive),
                    "usage": summarize(events(archive / "events.jsonl")),
                    "completed": read(archive / "completed.json")
                    if (archive / "completed.json").exists()
                    else None,
                    "handoff": read(archive / "handoff.json")
                    if (archive / "handoff.json").exists()
                    else None,
                }
                for archive in sorted((root / ".agent/tasks").glob("*/reviews/*"))
            ]
            rows.append(
                {
                    "root": str(root),
                    "fixture_version": version,
                    "source_sha256": digest(
                        root / "src/agent_runtime/tools/registry.py"
                    ),
                    "protected_unchanged": True,
                    "sibling_unchanged": True,
                    "canonical_runs": runs,
                    "canonical_reviews_including_failures": reviews,
                }
            )
    write(
        WORK / "tool-continuation-audits" / label / "facts.json",
        {
            "rows": rows,
            "scope": "Only listed frozen experiments. Completed runtime facts and immutable Primary decisions retained separately; no inferred acceptance, no Explorer or cloud-saving credit.",
            "global_config_sha256": digest(KIT / ".local-agents/config.json"),
        },
    )
    print(
        {
            "audited_roots": len(rows),
            "canonical_runs": sum(len(row["canonical_runs"]) for row in rows),
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("label")
    audit(parser.parse_args().label)
