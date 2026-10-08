"""Canonical multi-cohort facts; Primary must make the release decision."""

import json
from pathlib import Path

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read

OUT = WORK / "coordinator-mixed-release-2"


def main():
    OUT.mkdir(exist_ok=False)
    rows = []
    for cohort, identities in (
        ("coordinator-label-pilot-4", ["coordinator-r1", "control-r1"]),
        ("coordinator-mixed-resume-1", ["control-r2", "coordinator-r2"]),
        ("coordinator-numeric-pilot-1", ["control-r1", "coordinator-r1"]),
    ):
        base = WORK / cohort
        manifest = read(base / "manifest.json")
        for identity in identities:
            cell = next(c for c in manifest["cells"] if c["id"] == identity)
            root = Path(cell["root"])
            explorer = read(root / ".agent/explorer.json")
            if explorer["status"] != "success":
                if list((root / ".agent").glob("*-coder.json")):
                    raise ValueError("writer ran despite failed Explorer screen")
                rows.append(
                    {
                        "cohort": cohort,
                        "identity": identity,
                        "units": [],
                        "explorer_status": explorer["status"],
                        "failure_reason": explorer["failure_reason"],
                        "coder_not_executed": True,
                        "quality_passed": False,
                    }
                )
                continue
            adjudication = read(root / ".agent/explorer-primary-adjudication.json")
            for ref in explorer["source_refs"]:
                source = root / ref["path"]
                if digest(source) != ref["source_hash"]:
                    candidates = list(
                        (root / ".agent/tasks").glob(
                            "*/runs/*/preimages/" + ref["path"]
                        )
                    )
                    matches = [p for p in candidates if digest(p) == ref["source_hash"]]
                    if not matches:
                        raise ValueError("missing original citation source")
                    source = matches[0]
                lines = source.read_text(encoding="utf-8").splitlines()
                start, end = ref["start_line"], ref["end_line"]
                if not (1 <= start <= end <= len(lines)) or ref["quote"] != "\n".join(
                    lines[start - 1 : end]
                ):
                    raise ValueError("invalid actual Explorer citation")
            units, final_hashes = [], dict(cell["hashes"])
            for uid in cell["units"]:
                packet = read(root / f".agent/{uid}-bound.json")
                archive = (
                    root
                    / ".agent/tasks"
                    / packet["task_id"]
                    / "runs"
                    / packet["run_id"]
                )
                coder = read(archive / "handoff.json")
                primary = read(archive / "review.json")
                actual = read(archive / "packet.json")
                for key in (
                    "required_behavior",
                    "acceptance_criteria",
                    "acceptance_scenarios",
                    "dependencies",
                    "focused_tests",
                    "validation_profile",
                    "owned_contract_ids",
                ):
                    if actual[key] != packet[key]:
                        raise ValueError("hard contract drift: " + uid + "/" + key)
                if any(
                    actual["risk"][level] != packet["risk"][level]
                    for level in ("feature", "unit", "integration")
                ):
                    raise ValueError("risk changed")
                reviewer = read(
                    root
                    / ".agent/tasks"
                    / packet["task_id"]
                    / "reviews"
                    / primary["local_review_id"]
                    / "handoff.json"
                )
                independent = read(root / f".agent/{uid}-independent-1.json")
                validation = coder["validation"]
                focused = validation["focused_tests"]
                proposal_good = True
                if cell["arm"] == "coordinator":
                    context = read(root / f".agent/{uid}-proposal-input.json")
                    proposal = read(root / f".agent/{uid}-proposal.json")
                    proposal_good = proposal["status"] == "protocol_valid" and set(
                        context
                    ) == {"identity", "feature_goal", "source_refs", "question"}
                good = (
                    proposal_good
                    and coder["status"] == "ready_for_review"
                    and primary["decision"] == "accept"
                    and reviewer["decision"] == "pass_to_primary"
                    and reviewer["runtime_facts"]["inputs_unchanged"] is True
                    and independent["passed"] is True
                    and validation["status"] == "passed"
                    and focused["junit"]["executed"] > 0
                    and focused["inputs_unchanged"] is True
                    and all(
                        c["status"] == "passed" for c in validation["configured_checks"]
                    )
                )
                for change in coder["changed_files"]:
                    final_hashes[change["path"]] = change["final_sha256"]
                units.append(
                    {
                        "id": uid,
                        "canonical_review_id": primary["local_review_id"],
                        "passed": good,
                        "coder": coder["status"],
                        "reviewer": reviewer["decision"],
                        "primary": primary["decision"],
                    }
                )
            for path, sha in final_hashes.items():
                if digest(root / path) != sha:
                    raise ValueError("workspace drift: " + str(root / path))
            integration = read(root / ".agent/feature-integration.json")
            good = (
                all(u["passed"] for u in units)
                and explorer["status"] == "success"
                and not explorer.get("cache", {}).get("hit")
                and adjudication["success"] is True
                and integration["checks"]["all_checks_pass"] is True
                and integration["junit"]
                == {"tests": 7, "failures": 0, "errors": 0, "skipped": 0}
            )
            rows.append(
                {
                    "cohort": cohort,
                    "identity": identity,
                    "units": units,
                    "explorer_original_credit": cohort != "coordinator-mixed-resume-1",
                    "original_explorer_hash": digest(root / ".agent/explorer.json"),
                    "integration_tests": 7,
                    "quality_passed": good,
                }
            )
    frozen = read(WORK / "coordinator-loader-baseline-1/freeze.json")["files"]
    if any(digest(KIT / path) != sha for path, sha in frozen.items()):
        raise ValueError("candidate production drift")
    facts = {
        "rows": rows,
        "all_quality_passed": all(r["quality_passed"] for r in rows),
        "chain_count": len(rows),
        "unit_count": sum(len(r["units"]) for r in rows),
        "loader_methods_mixed_across_history": True,
        "historical_reviewer_startup_failures": 1,
        "historical_explorer_failed_cohort": "coordinator-label-pilot-3",
        "cost_savings_established": False,
        "primary_feature_acceptance_not_inferred": True,
        "driver_sha256": digest(Path(__file__)),
    }
    write(OUT / "facts-1.json", facts)
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    main()
