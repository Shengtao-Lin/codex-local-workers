"""Immutable role-separated audit; real current bytes, no inferred acceptance."""

import argparse
import json

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes
from role_usage_facts import summarize


def audit(label):
    if not label or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label
    ):
        raise ValueError("safe audit label required")
    cohorts = {}
    for version in (3, 4, 5):
        frozen = KIT / f"benchmarks/fixtures/tool-awaitable-v{version}"
        provenance = read(frozen / "provenance.json")
        verify_hashes(frozen, provenance["files"])
        verify_hashes(KIT.parent / "agent-runtime-kit", provenance["original_files"])
        rows = []
        for root in sorted((WORK / f"tool-awaitable-{version}").glob("fresh-*")):
            verify_hashes(
                root,
                {
                    p: sha
                    for p, sha in provenance["files"].items()
                    if p != "src/agent_runtime/tools/registry.py"
                },
            )
            row = {
                "root": str(root),
                "protected_unchanged": True,
                "primary_acceptance": False,
            }
            canonical_runs = []
            for archive in sorted((root / ".agent/tasks").glob("*/runs/*")):
                completed = archive / "completed.json"
                if not completed.is_file():
                    continue
                events_path = archive / "events.jsonl"
                events = (
                    [
                        json.loads(line)
                        for line in events_path.read_text(encoding="utf-8").splitlines()
                    ]
                    if events_path.exists()
                    else []
                )
                canonical_runs.append(
                    {
                        "archive": str(archive),
                        "completed": read(completed),
                        "usage": summarize(events),
                        "primary": read(archive / "review.json")
                        if (archive / "review.json").exists()
                        else None,
                        "forward_diff_sha256": digest(archive / "cumulative.diff")
                        if (archive / "cumulative.diff").exists()
                        else None,
                    }
                )
            row["canonical_runs"] = canonical_runs
            review_attempts = []
            for archive in sorted((root / ".agent/tasks").glob("*/reviews/*")):
                events_path = archive / "events.jsonl"
                if not events_path.is_file():
                    continue
                events = [
                    json.loads(line)
                    for line in events_path.read_text(encoding="utf-8").splitlines()
                ]
                review_attempts.append(
                    {
                        "archive": str(archive),
                        "usage": summarize(events),
                        "completed": read(archive / "completed.json")
                        if (archive / "completed.json").exists()
                        else None,
                    }
                )
            row["canonical_review_attempts_including_failures"] = review_attempts
            recovered = root / ".agent/primary-recovered-verification.json"
            if recovered.is_file():
                row["recovered_artifact_verification"] = read(recovered)
                row["recovery_is_fresh_success"] = False
            explorer = root / ".agent/explorer.json"
            if explorer.is_file():
                report = read(explorer)
                trace = root / report["diagnostic_log"]
                trace.resolve().relative_to(root.resolve())
                events = [
                    json.loads(line)
                    for line in trace.read_text(encoding="utf-8").splitlines()
                ]
                row["explorer"] = {
                    "runtime_status": report["status"],
                    "mode": report["explorer_mode"],
                    "usage": summarize(events),
                    "report_sha256": digest(explorer),
                    "primary": read(root / ".agent/explorer-primary.json")
                    if (root / ".agent/explorer-primary.json").exists()
                    else None,
                }
            coder = root / ".agent/coder.json"
            if coder.is_file():
                report = read(coder)
                archive = root / report["evidence_refs"]["run_archive"]
                archive.resolve().relative_to(root.resolve())
                events = [
                    json.loads(line)
                    for line in (archive / "events.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()
                ]
                row["coder"] = {
                    "status": report["status"],
                    "failure_reason": report.get("failure_reason"),
                    "usage": summarize(events),
                    "report_sha256": digest(coder),
                    "canonical_run": str(archive),
                    "primary": read(archive / "review.json")
                    if (archive / "review.json").exists()
                    else None,
                }
                row["primary_acceptance"] = bool(
                    row["coder"]["primary"]
                    and row["coder"]["primary"].get("decision") == "accept"
                )
            if (root / ".agent/reviewer.json").exists():
                report = read(root / ".agent/reviewer.json")
                row["reviewer"] = {
                    "decision": report["decision"],
                    "findings": report.get("findings"),
                    "report_sha256": digest(root / ".agent/reviewer.json"),
                }
            if (root / ".agent/invocation.json").exists():
                invocation = read(root / ".agent/invocation.json")
                row["whole_chain_seconds"] = invocation["seconds"]
                row["whole_chain_exit"] = invocation["exit"]
            if (root / ".agent/primary-verification.json").exists():
                row["independent_validation"] = read(
                    root / ".agent/primary-verification.json"
                )
            rows.append(row)
        cohorts[str(version)] = rows
    facts = {
        "weekly_ceiling": 23,
        "cohorts": cohorts,
        "sibling_source_unchanged": True,
        "stable_release": False,
        "cloud_savings": None,
        "exclusions": {
            "v1": "Primary packet field-shape error before model",
            "v2": "Primary fixture lint error before model",
            "v3-fresh-2-handoff": "Explicit false ack conflicts with ordering gate; not Reviewer/model failure",
        },
        "warning": "Prepared/incomplete runs are not success; actual E failures cannot be overridden by C success. v4 omitted already-qualified post-edit hint; v5 uses full role profile and exact locator targets, not a one-axis comparison.",
    }
    path = WORK / "tool-awaitable-audits" / label / "facts.json"
    write(path, facts)
    print(json.dumps({"path": str(path), "stable_release": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("label")
    audit(parser.parse_args().label)
