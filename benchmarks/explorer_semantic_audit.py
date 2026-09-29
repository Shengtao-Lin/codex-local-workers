"""Validate a Primary-reviewed Explorer semantic audit against frozen E2E cells."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
VALID_STATUSES = {"correct", "incomplete", "incorrect", "failed"}


def verify_full_reports(summary: dict) -> None:
    """Refuse a release audit whose canonical full Explorer evidence is absent."""
    for result in summary.get("results", []):
        workspace = Path(result["workspace"]).resolve()
        compact_path = Path(result["explorer_report"]).resolve()
        if not compact_path.is_relative_to(workspace) or not compact_path.is_file():
            raise ValueError(f"missing in-workspace Explorer report: {workspace}")
        compact = json.loads(compact_path.read_text(encoding="utf-8"))
        diagnostic = compact.get("diagnostic_report")
        if not isinstance(diagnostic, str):
            raise TypeError(f"missing full Explorer report path: {workspace}")
        full_path = (workspace / diagnostic).resolve()
        if not full_path.is_relative_to(workspace) or not full_path.is_file():
            raise ValueError(f"missing full Explorer report: {workspace}")
        full = json.loads(full_path.read_text(encoding="utf-8"))
        if full.get("status") != compact.get("status") or full.get(
            "status"
        ) != result.get("explorer_status"):
            raise ValueError(f"Explorer report status mismatch: {workspace}")


def verify_repeat_inputs(summary: dict) -> None:
    """Compare frozen source manifests, contracts, and protected files by case."""
    identities: dict[str, bytes] = {}
    for result in summary.get("results", []):
        workspace = Path(result["workspace"]).resolve()
        manifest_path = workspace / "fixture-source.json"
        packet_path = workspace / ".agent" / "packet.json"
        if not manifest_path.is_file() or not packet_path.is_file():
            raise ValueError(f"missing frozen input manifest or packet: {workspace}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        if packet.get("unit_id") != result["case"]:
            raise ValueError(f"packet case identity mismatch: {workspace}")
        run_id = packet.pop("run_id", None)
        protected: dict[str, str] = {}
        for relative in packet.get("scope", {}).get("readonly", []):
            path = (workspace / relative).resolve()
            if not path.is_relative_to(workspace) or not path.is_file():
                raise ValueError(f"missing in-workspace protected input: {path}")
            protected[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        if not protected:
            raise ValueError(f"no protected inputs in packet: {workspace}")
        task_id = packet.get("task_id")
        archive = (workspace / ".agent" / "tasks" / task_id / "runs" / run_id).resolve()
        preimage_index = archive / "preimages.json"
        if not archive.is_relative_to(workspace) or not preimage_index.is_file():
            raise ValueError(f"missing in-workspace Coder preimages: {workspace}")
        preimages = {
            item["path"]: item
            for item in json.loads(preimage_index.read_text(encoding="utf-8"))
        }
        sources: dict[str, str] = {}
        modified = set(packet["scope"]["modify"])
        for item in manifest:
            relative = item["path"]
            if relative in modified:
                entry = preimages.get(relative)
                if not entry or not entry.get("existed"):
                    raise ValueError(f"missing modified source preimage: {relative}")
                path = (workspace / entry["archive_path"]).resolve()
                if not path.is_relative_to(archive) or not path.is_file():
                    raise ValueError(f"missing archived source preimage: {relative}")
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest != entry["sha256"]:
                    raise ValueError(
                        f"archived source preimage hash mismatch: {relative}"
                    )
            else:
                path = (workspace / relative).resolve()
                if not path.is_relative_to(workspace) or not path.is_file():
                    raise ValueError(f"missing in-workspace source: {relative}")
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            sources[relative] = digest
        identity = json.dumps(
            {
                "manifest": manifest,
                "packet": packet,
                "protected": protected,
                "sources": sources,
            },
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        case = result["case"]
        if case in identities and identities[case] != identity:
            raise ValueError(f"repeat input mismatch: {case}")
        identities[case] = identity


def summarize(audit: dict, summary: dict) -> dict:
    if audit.get("schema_version") != 1 or summary.get("schema_version") != 1:
        raise ValueError("audit and batch must use schema version 1")
    results = summary.get("results")
    ratings = audit.get("ratings")
    if not isinstance(results, list) or not isinstance(ratings, list):
        raise TypeError("batch results and audit ratings must be lists")
    cells: dict[tuple[int, str], dict] = {}
    for result in results:
        workspace = Path(result["workspace"])
        match = re.fullmatch(r"round-(\d+)", workspace.parent.name)
        if not match or workspace.name != result.get("case"):
            raise ValueError("batch result has inconsistent workspace identity")
        key = (int(match.group(1)), result["case"])
        if key in cells:
            raise ValueError(f"duplicate batch cell: {key}")
        cells[key] = result
    seen: set[tuple[int, str]] = set()
    counts: Counter[str] = Counter()
    release_qualified = 0
    for rating in ratings:
        key = (rating.get("round"), rating.get("case"))
        if key not in cells or key in seen:
            raise ValueError(f"audit cell is missing or duplicated: {key}")
        status = rating.get("status")
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid Explorer semantic rating: {status}")
        if status != "correct" and not str(rating.get("reason", "")).strip():
            raise ValueError(f"non-correct rating needs a reason: {key}")
        result = cells[key]
        if status == "correct" and not (
            result.get("explorer_status") == "success"
            and result.get("explorer_evidence_valid") is True
        ):
            raise ValueError(
                f"correct semantic rating lacks mechanical evidence: {key}"
            )
        counts[status] += 1
        release_qualified += bool(status == "correct" and result.get("qualified_pass"))
        seen.add(key)
    if seen != set(cells):
        raise ValueError(f"missing audit cells: {sorted(set(cells) - seen)}")
    total = len(cells)
    return {
        "cells": total,
        "ratings": dict(counts),
        "explorer_mechanical": sum(
            item.get("explorer_status") == "success"
            and item.get("explorer_evidence_valid") is True
            for item in cells.values()
        ),
        "explorer_strict_semantic": counts["correct"],
        "protocol_e2e": sum(
            bool(item.get("qualified_pass")) for item in cells.values()
        ),
        "semantic_release_qualified": release_qualified,
    }


def assess_release(
    audit: dict, summary: dict, *, gate_version: str = "original"
) -> dict:
    """Apply a named Explorer gate without rewriting the frozen historical score."""
    if gate_version not in {"original", "role-aligned-v1"}:
        raise ValueError(f"unknown Explorer gate version: {gate_version}")
    metrics = summarize(audit, summary)
    reasons: list[str] = []
    if not str(audit.get("reviewer", "")).strip():
        reasons.append("semantic ratings require an identified Primary reviewer")

    by_round: dict[int, set[str]] = {}
    for result in summary["results"]:
        workspace = Path(result["workspace"])
        round_number = int(re.fullmatch(r"round-(\d+)", workspace.parent.name).group(1))
        by_round.setdefault(round_number, set()).add(result["case"])
    if set(by_round) != {1, 2} or len(by_round.get(1, set())) < 11:
        reasons.append("release sample requires two rounds of at least 11 cases")
    if by_round.get(1) != by_round.get(2):
        reasons.append("both rounds must contain the same case identities")

    ratings = {
        (rating["round"], rating["case"]): rating["status"]
        for rating in audit["ratings"]
    }
    repeated_misses = []
    for case in by_round.get(1, set()) & by_round.get(2, set()):
        if gate_version == "original":
            missed_both = (
                ratings[(1, case)] != "correct" and ratings[(2, case)] != "correct"
            )
        else:
            missed_both = all(
                not (
                    item.get("explorer_status") == "success"
                    and item.get("explorer_evidence_valid") is True
                )
                for item in summary["results"]
                if item["case"] == case
            )
        if missed_both:
            repeated_misses.append(case)
    repeated_misses.sort()
    if repeated_misses:
        label = "strict" if gate_version == "original" else "evidence"
        reasons.append(f"repeated {label} miss: " + ", ".join(repeated_misses))
    minimum = math.ceil(metrics["cells"] * 0.9)
    if gate_version == "original":
        if metrics["explorer_strict_semantic"] < minimum:
            reasons.append(
                f"strict Explorer diagnosis {metrics['explorer_strict_semantic']}/"
                f"{metrics['cells']} is below {minimum}/{metrics['cells']}"
            )
    else:
        if metrics["explorer_mechanical"] < minimum:
            reasons.append(
                f"Explorer file/line evidence {metrics['explorer_mechanical']}/"
                f"{metrics['cells']} is below {minimum}/{metrics['cells']}"
            )
        if metrics["ratings"].get("incorrect", 0):
            reasons.append(
                f"Explorer made {metrics['ratings']['incorrect']} incorrect "
                "source claims; Primary must correct these before any handoff"
            )
    return {
        **metrics,
        "gate_version": gate_version,
        "explorer_gate": "GO" if not reasons else "NO-GO",
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audit",
        type=Path,
        default=KIT / "benchmarks/V1.2-EXPLORER-SEMANTIC-AUDIT.json",
    )
    parser.add_argument(
        "--release-gate",
        action="store_true",
        help="Apply the v1.2 §12.7 Explorer-only gate; does not certify all v1.2 exits.",
    )
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    batch = (KIT / audit["batch"]).resolve()
    work = (KIT / "benchmarks/work/stability-v1").resolve()
    if batch.parent != work:
        raise ValueError("audit batch must be a direct frozen stability work directory")
    summary = json.loads((batch / "summary.json").read_text(encoding="utf-8"))
    verify_full_reports(summary)
    if args.release_gate:
        verify_repeat_inputs(summary)
    result = (
        assess_release(audit, summary)
        if args.release_gate
        else summarize(audit, summary)
    )
    print(json.dumps(result, indent=2))
    return int(args.release_gate and result["explorer_gate"] != "GO")


if __name__ == "__main__":
    raise SystemExit(main())
