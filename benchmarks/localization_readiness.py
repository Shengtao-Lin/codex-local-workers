"""Separate localization-only gate; never certify general semantic investigation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import explorer_semantic_audit as SEMANTIC
import stability_e2e as STABILITY
import v1_2_readiness as PIPELINE


def verify_materialized_refs(result: dict) -> bool:
    workspace = Path(result["workspace"]).resolve()
    compact = json.loads(Path(result["explorer_report"]).read_text(encoding="utf-8"))
    report = STABILITY.full_explorer_report(workspace, compact)
    if report.get("explorer_mode") != "locate":
        raise ValueError("investigation results cannot enter a localization-only gate")
    if report.get("status") != "success":
        return False
    if report.get("semantic_verdict") != "not_evaluated":
        raise ValueError("localization must not assert a semantic verdict")
    packet = json.loads((workspace / ".agent/packet.json").read_text(encoding="utf-8"))
    archive = workspace / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    index = json.loads((archive / "preimages.json").read_text(encoding="utf-8"))
    preimages = {item["path"]: item for item in index}
    refs = report.get("source_refs")
    if not isinstance(refs, list) or not 1 <= len(refs) <= 6:
        raise ValueError("invalid canonical reference count")
    total = 0
    for ref in refs:
        relative = ref["path"]
        if relative in preimages:
            source = (workspace / preimages[relative]["archive_path"]).resolve()
            if not source.is_relative_to(archive.resolve()):
                raise ValueError("reference preimage escapes archive")
        else:
            source = (workspace / relative).resolve()
            if not source.is_relative_to(workspace):
                raise ValueError("reference escapes workspace")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != ref.get("source_hash"):
            raise ValueError("reference hash differs from frozen source")
        start, end = ref["start_line"], ref["end_line"]
        lines = data.decode("utf-8-sig").splitlines()
        if (
            type(start) is not int
            or type(end) is not int
            or not 1 <= start <= end <= len(lines)
        ):
            raise ValueError("invalid canonical reference range")
        total += end - start + 1
        if total > 80 or ref.get("quote") != "\n".join(lines[start - 1 : end]):
            raise ValueError("reference quote is not the frozen source range")
    case = next(item for item in STABILITY.CASES if item.name == result["case"])
    return STABILITY.localization_has_relevant_evidence(
        report, case, f"tests/test_{case.name.replace('-', '_')}.py"
    )


def assess(summary: dict) -> dict:
    results = summary["results"]
    by_round: dict[str, set[str]] = {}
    seen = set()
    reasons = []
    for result in results:
        key = (Path(result["workspace"]).parent.name, result["case"])
        if key in seen:
            raise ValueError("duplicate localization cell")
        seen.add(key)
        by_round.setdefault(key[0], set()).add(key[1])
    if (
        set(by_round) != {"round-1", "round-2"}
        or by_round.get("round-1") != by_round.get("round-2")
        or len(by_round.get("round-1", set())) < 11
    ):
        reasons.append("localization gate requires identical 11+ cases in two rounds")
    good = sum(item.get("localization_verified") is True for item in results)
    if good < math.ceil(0.9 * len(results)):
        reasons.append("verified relevant localization is below 90%")
    for case in by_round.get("round-1", set()) & by_round.get("round-2", set()):
        if all(
            item.get("localization_verified") is not True
            for item in results
            if item["case"] == case
        ):
            reasons.append("repeated localization miss: " + case)
    explorer = {
        "capability": "localization_only",
        "semantic_diagnosis": "not_evaluated",
        "verified_locations": good,
        "cells": len(results),
        "reasons": reasons,
        "explorer_gate": "GO" if not reasons else "NO-GO",
    }
    decision = PIPELINE.assess_worker_pipeline(
        explorer, summary, gate_version="role-aligned-v1"
    )
    decision["gate_version"] = "localization-v1"
    decision["general_semantic_routing"] = "NOT_QUALIFIED"
    return decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    args = parser.parse_args()
    batch = args.batch.resolve()
    if batch.parent != STABILITY.WORK.resolve():
        raise ValueError("batch must be a direct stability work directory")
    summary = json.loads((batch / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((batch / "candidate-inputs.json").read_text(encoding="utf-8"))
    if manifest.get("explorer_mode") != "locate":
        raise ValueError("candidate is not a frozen localization-mode batch")
    for relative, digest in manifest["files"].items():
        if (
            hashlib.sha256((STABILITY.KIT / relative).read_bytes()).hexdigest()
            != digest
        ):
            raise ValueError(
                "candidate runtime no longer matches current implementation"
            )
    SEMANTIC.verify_full_reports(summary)
    SEMANTIC.verify_repeat_inputs(summary)
    for result in summary["results"]:
        result["localization_verified"] = verify_materialized_refs(result)
        if result["localization_verified"] != result["explorer_evidence_valid"]:
            raise ValueError(
                "runner location verdict differs from canonical source verification"
            )
        result["primary_decision"] = PIPELINE.primary_decision(result)
    decision = assess(summary)
    decision["remaining_release_checks"] = [
        "current role compatibility including locator mode",
        "capability matrix and full regression suite",
        "unknown-source localization handoff and Primary integration review",
        "explicit Primary takeover for semantic investigations",
    ]
    print(json.dumps(decision, indent=2))
    return int(decision["pipeline_decision"] != "GO")


if __name__ == "__main__":
    raise SystemExit(main())
