"""Offline evidence inventory; never grants dispatch authority or calls a model."""

import argparse
import hashlib
import json
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
WORK = Path("benchmarks/work")
TRANSFER = WORK / "harness-convergence/unified-transfer-20261018-1"
CURRENT = WORK / "harness-convergence/consolidated-harness-20261018-1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def disposition(accepted, executed, required, same_candidate=False):
    """Evidence labels, NOT permissions. Even exact repeats need Primary approval."""
    if not 0 <= accepted <= executed <= required:
        raise ValueError("Invalid counts")
    if executed == 0:
        return "NOT_EVALUATED"
    if accepted == required:
        return "EXACT_REPEAT_EVIDENCE" if same_candidate else "HISTORICAL_ONLY"
    return "UNQUALIFIED_WITHIN_RECORDED_SCOPE"


def audit(root=KIT):
    pins = {}

    def evidence(relative):
        path = root / relative
        pins[str(relative).replace("\\", "/")] = sha(path)
        return read(path)

    transfer = evidence(TRANSFER / "decision.json")
    current = evidence(CURRENT / "decision.json")
    rows = []
    for task in ("request_keys", "single_content", "messages_output"):
        accepted = 0
        for repeat in (1, 2):
            record = evidence(
                TRANSFER / "cases" / f"{task}-candidate-{repeat}/primary-decision.json"
            )
            canonical = Path(record["canonical_review"])
            # Fixed trusted history only; no Worker-supplied reference or traversal.
            relative = canonical.resolve().relative_to(root.resolve())
            review = evidence(relative)
            if sha(canonical) != record["sha256"]:
                raise ValueError("Canonical Primary evidence drift")
            if review["decision"] != record["decision"]:
                raise ValueError("Primary decisions disagree")
            accepted += record["decision"] == "accept"
        if accepted != transfer["per_task"][task]:
            raise ValueError("Aggregate disagrees with canonical decisions")
        rows.append(
            {
                "scenario": task,
                "mode": "implementation_from_registered_start",
                "candidate": "coder_unified_preparation.py (historical frozen version)",
                "accepted": accepted,
                "executed": 2,
                "required": 2,
                "status": disposition(accepted, 2, 2),
            }
        )
    if current["live"]["accepted"] != 0 or current["live"]["executed"] != 4:
        raise ValueError("Latest decision changed; manual reconciliation required")
    for task in ("T1_sse_draft", "T2_iterator_draft"):
        rows.append(
            {
                "scenario": task,
                "mode": "repair_frozen_erroneous_draft",
                "candidate": "consolidated_harness.py (frozen 20261018-1)",
                "accepted": 0,
                "executed": 2,
                "required": 2,
                "status": disposition(0, 2, 2, same_candidate=True),
            }
        )
    comparison = evidence(
        WORK / "capability-fit/limit-startpoint-comparison-1/stage-decision.json"
    )
    for start in ("draft", "legacy"):
        successes, trials = (
            comparison[start + "_successes"],
            comparison[start + "_trials"],
        )
        rows.append(
            {
                "scenario": "limit_optimization",
                "mode": start + "_start",
                "candidate": comparison["candidate"],
                "accepted": successes,
                "executed": trials,
                "required": trials,
                "status": disposition(successes, trials, trials),
            }
        )
    assisted = evidence(WORK / "capability-fit/limit-assisted-1/stage-decision.json")
    rows.append(
        {
            "scenario": "limit_optimization",
            "mode": "Primary_algorithm_assisted",
            "candidate": assisted["candidate"],
            "accepted": assisted["primary_accepts"],
            "executed": assisted["completed_cells"],
            "required": assisted["registered_cells"],
            "status": disposition(
                assisted["primary_accepts"],
                assisted["completed_cells"],
                assisted["registered_cells"],
            ),
        }
    )
    for row in rows:
        row["current_dispatch"] = "PRIMARY_DECISION_REQUIRED"
    return {
        "status": "OFFLINE_BOUNDARY_INVENTORY_ONLY",
        "rows": rows,
        "evidence_sha256": pins,
        "models_called": 0,
        "new_qualification": False,
        "current_local_dispatch_grants": 0,
        "release": "R4 HOLD; R5 not admitted; production unchanged",
        "limits": [
            "No transfer of qualification between candidate versions or startpoints",
            "No claim that all Iterator, typing, or correct-baseline tasks fail",
            "Historical success is not unknown-task qualification or current deployment authority",
            "Primary-owned means decision required, not proof Primary implemented or saved cost",
            "Existing route_plan checks owner/scope/evidence presence, not semantic qualification",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
    print(json.dumps({"status": result["status"], "rows": len(result["rows"])}))
