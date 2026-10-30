"""Immutable progressive audit; unexecuted arms never enter model denominators."""

import argparse
import json
from pathlib import Path

import limit_recovery_audit as earlier
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes
from role_usage_facts import summarize

COHORTS = (
    "limit-focus-1",
    "limit-fresh-1",
    "limit-complete-1",
    "limit-release-1",
    "limit-recipe-1",
    "limit-budget-1",
    "limit-presented-1",
    "limit-multiref-1",
    "limit-plan-1",
    "limit-plan-2",
    "limit-echo-1",
    "limit-retention-1",
    "limit-schema-1",
    "limit-baseline-1",
    "limit-tagged-1",
    "limit-failure-1",
    "limit-failure-2",
    "limit-whitespace-1",
    "limit-block-1",
    "limit-reset-1",
    "limit-sampling-1",
    "limit-draft-1",
)


def audit(label, record_unaccepted=False):
    destination = WORK / "limit-iteration-23" / label
    if destination.exists():
        raise ValueError("audit label already exists")
    frozen = KIT / "benchmarks/fixtures/limit-recovery-v3"
    provenance = read(frozen / "provenance.json")
    verify_hashes(frozen, provenance["files"])
    verify_hashes(earlier.trial.SOURCE, provenance["sibling_current_hashes"])
    history = WORK / "limit-recovery-3/historical-task"
    for path in history.rglob("*"):
        if path.is_file() and digest(path) != digest(
            earlier.trial.TASK / path.relative_to(history)
        ):
            raise ValueError("original sibling history drift")
    snapshots = []
    for pattern in (
        "limit-*-runtime-*",
        "limit-*-runtime-1",
        "limit-*-runtime-2",
        "limit-*-runtime-3",
        "limit-*-runtime-4",
        "review-history-runtime-1",
        "reviewer-anchor-aware-runtime-1",
        "coder-tagged-runtime-1",
    ):
        for snapshot in WORK.glob(pattern):
            if snapshot not in snapshots and (snapshot / "freeze.json").is_file():
                verify_hashes(snapshot, read(snapshot / "freeze.json")["files"])
                snapshots.append(snapshot)
    cohorts = {}
    for name in COHORTS:
        parent = WORK / name
        rows = []
        if parent.exists():
            for root in sorted(parent.iterdir()):
                if not (root / ".agent/packet.json").is_file():
                    continue
                if not (root / ".agent/coder.json").is_file():
                    rows.append(
                        {
                            "root": str(root),
                            "state": "prepared_not_completed",
                            "model_credit": False,
                        }
                    )
                    continue
                report = read(root / ".agent/coder.json")
                if not report.get("evidence_refs", {}).get("run_archive"):
                    packet = read(root / ".agent/packet.json")
                    verify_hashes(root, read(root / ".agent/manifest.json")["files"])
                    rows.append(
                        {
                            "root": str(root),
                            "state": "launch_blocked_before_model",
                            "status": report["status"],
                            "blocked": report.get("blocked"),
                            "model_requests": 0,
                            "quality_denominator": False,
                            "operator_context": "Concurrent role lease launch is a Primary orchestration error, not model capability",
                            "identity": packet["run_id"],
                        }
                    )
                    continue
                result = earlier.observe(root)
                packet = read(root / ".agent/packet.json")
                if (
                    record_unaccepted
                    and result["status"] in {"failed", "blocked"}
                    and result["primary"] is None
                ):
                    decision = command(
                        root,
                        [
                            str(earlier.trial.PYTHON),
                            "-B",
                            str(KIT / ".local-agents/record-review.py"),
                            "--repo",
                            str(root),
                            "--task-id",
                            packet["task_id"],
                            "--run-id",
                            packet["run_id"],
                            "--decision",
                            "takeover",
                            "--summary",
                            "Bounded experimental candidate ended without verified acceptance. Preserve partial changes and histories; close this unchanged attempt. This routing is not a Primary implementation or sibling source write. Further experiments require a distinct evidence-backed approach.",
                        ],
                    )
                    if decision["exit"]:
                        raise ValueError(decision["output"])
                    result = earlier.observe(root)
                config = read(root / ".agent/config.json")
                archive = root / report["evidence_refs"]["run_archive"]
                usage = {
                    "coder": summarize(
                        [
                            json.loads(line)
                            for line in (archive / "events.jsonl")
                            .read_text(encoding="utf-8")
                            .splitlines()
                        ]
                    )
                }
                usage["reviewer_attempts"] = []
                reviews = root / ".agent/tasks" / packet["task_id"] / "reviews"
                for review_events in sorted(reviews.glob("*/events.jsonl")):
                    review_events.resolve().relative_to(reviews.resolve())
                    request = read(review_events.parent / "input.json")
                    if request.get("run_id") != packet["run_id"]:
                        continue
                    usage["reviewer_attempts"].append(
                        {
                            "review_id": request["review_id"],
                            "route": "automatic"
                            if request["review_id"].startswith("auto-")
                            else "diagnostic_recovery",
                            "events": summarize(
                                [
                                    json.loads(line)
                                    for line in review_events.read_text(
                                        encoding="utf-8"
                                    ).splitlines()
                                ]
                            ),
                            "terminal_completion_recorded": (
                                review_events.parent / "completed.json"
                            ).is_file(),
                        }
                    )
                if (
                    result["reviewer"]
                    and result["reviewer"].get("decision") == "failed"
                ):
                    stats = result["reviewer"].get("model_request")
                    if isinstance(stats, dict):
                        usage["terminal_failure_pointer"] = {
                            "usage": summarize(
                                [{"event": "model_request", "facts": stats}]
                            ),
                            "warning": "Convenience failure report, not reliably attributed to a review id; kept separately, never added to canonical event sums",
                        }
                rows.append(
                    {
                        "root": str(root),
                        "state": "completed",
                        "status": result["status"],
                        "failure_signature": result["failure_signature"],
                        "seconds": result["seconds"],
                        "model_requests": result["model_requests"],
                        "max_context": result["max_context_utilization"],
                        "protected_inputs_unchanged": result[
                            "protected_inputs_unchanged"
                        ],
                        "actual_diff_sha256": digest(
                            root
                            / read(root / ".agent/coder.json")["evidence_refs"][
                                "cumulative_diff"
                            ]
                        ),
                        "validation_attempts": [
                            {
                                "path": v["path"],
                                "sha256": v["sha256"],
                                "edit_revision": v["edit_revision"],
                                "status": v["validation"]["status"],
                            }
                            for v in result["attempts"]
                        ],
                        "reviewer": result["reviewer"],
                        "primary": result["primary"],
                        "local_main_loop_usage": usage,
                        "experimental_config": {
                            key: config.get(key)
                            for key in (
                                "coder_repair_focus_retention",
                                "coder_require_implementation_plan",
                                "coder_post_edit_source_echo",
                                "coder_diverse_failure_examples",
                                "reviewer_native_history",
                                "coder_max_tokens",
                                "reviewer_max_tokens",
                                "coder_temperature",
                                "coder_top_p",
                                "coder_top_k",
                                "coder_repeat_penalty",
                            )
                        },
                        "excluded_from_capability": name == "limit-plan-1",
                    }
                )
        cohorts[name] = rows
    direct = []
    diagnostic_roots = [
        root
        for group in ("limit-direct-1", "limit-reasoning-1")
        for root in (WORK / group).glob("semantic-*")
    ]
    for root in sorted(diagnostic_roots):
        if not (root / ".agent/direct-facts.json").is_file():
            continue
        direct.append(
            {
                "root": str(root),
                "facts": read(root / ".agent/direct-facts.json"),
                "closure": read(root / ".agent/primary-closure-facts.json")
                if (root / ".agent/primary-closure-facts.json").exists()
                else None,
                "agent_success_credit": False,
                "analysis_metadata": {
                    key: value
                    for key, value in read(root / ".agent/direct-analysis.json").items()
                    if key != "untrusted_analysis"
                }
                if (root / ".agent/direct-analysis.json").exists()
                else None,
            }
        )
    facts = {
        "weekly_ceiling": 23,
        "cohorts": cohorts,
        "direct_diagnostics": direct,
        "frozen_sources_and_sibling_history_unchanged": True,
        "verified_snapshots": [str(path) for path in snapshots],
        "exclude": {
            "limit-plan-1": "Primary transport omitted PLAN_IMPLEMENTATION; not worker capability"
        },
        "stop_conditions": "Stable qualified release OR actual weekly used >=23; a finding alone is not stopping",
        "cloud_token_savings": None,
        "broader_release": False,
        "warning": "Keep cohorts, guided/recovery credit and individual artifact acceptance distinct. This progressive audit is not a release decision.",
    }
    write(destination / "facts.json", facts)
    summary = {
        name: [
            (Path(row["root"]).name, row.get("status", row["state"])) for row in rows
        ]
        for name, rows in cohorts.items()
    }
    print(json.dumps({"path": str(destination), "cohorts": summary}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("label")
    parser.add_argument("--record-unaccepted", action="store_true")
    args = parser.parse_args()
    if not args.label or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.label
    ):
        raise ValueError("normalized audit label required")
    audit(args.label, args.record_unaccepted)
