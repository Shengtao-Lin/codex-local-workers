"""Prepare, never dispatch, a Primary-confirmed return for an installed task.

Semantic findings are supplied by Primary. This helper only binds current
mechanical evidence; the installed host remains the authority on resume.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def settled(project, task_id, *, assisted):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", task_id):
        raise ValueError("Invalid task identity")
    if type(assisted) is not bool:
        raise ValueError("Primary must classify assistance explicitly")
    project = project.resolve(strict=True)
    task = project / ".agent/tasks" / task_id
    ledger = sorted((task / "general/ledger").glob("*.json"))
    if not ledger:
        raise ValueError("Missing canonical ledger")
    state = read(ledger[-1])["state"]
    if (
        state["task_id"] != task_id
        or state["status"] != "ready_for_primary"
        or state.get("active")
        or state.get("pending_model")
        or state.get("primary_return")
    ):
        raise ValueError("One settled, unused ready draft is required")
    hashes = state["expected_hashes"]
    for relative, expected in hashes.items():
        path = project / relative
        if not path.resolve(strict=False).is_relative_to(project):
            raise ValueError("Source outside the project")
        if expected is None:
            if path.exists():
                raise ValueError("Source no longer matches the settled draft")
            continue
        if digest(path) != expected:
            raise ValueError("Source no longer matches the settled draft")
    attempt = state["attempts"][-1]
    result = task / "workflow/runs" / attempt / "result.json"
    if read(result).get("status") != "ready_for_primary":
        raise ValueError("Canonical workflow is not ready")
    material = read(task / "general/contract.json")["material"]
    owned = {b["id"] for b in material["packet"]["required_behavior"]}
    return project, task, state, hashes, attempt, result, owned, material


def build_evidence(project, task_id, request, *, assisted):
    """Bind one readonly evidence question; never dispatch or alter credits."""
    _, _, state, hashes, attempt, result, owned, material = settled(
        project, task_id, assisted=assisted
    )
    if (
        material.get("config", {}).get("experimental_strata_continuation") != "task-v1"
        or material.get("policy", {}).get("role") != "investigate"
        or len(state["attempts"]) != 1
        or state.get("task_followup")
    ):
        raise ValueError("One preselected task-v1 investigation follow-up required")
    if not isinstance(request, dict) or set(request) != {"contract_ids", "text"}:
        raise ValueError("Evidence request fields: contract_ids, text")
    ids, text = request["contract_ids"], request["text"]
    if (
        not isinstance(ids, list)
        or not ids
        or any(not isinstance(i, str) or i not in owned for i in ids)
        or len(set(ids)) != len(ids)
        or not isinstance(text, str)
        or not 1 <= len(text) <= 2000
    ):
        raise ValueError("Existing contract IDs and bounded question required")
    return {
        "kind": "verify_or_extend_evidence",
        "previous_attempt": attempt,
        "result_sha256": digest(result),
        "source_hashes": hashes,
        "contract_ids": ids,
        "text": text,
        "assisted": assisted,
    }


def build(project, task_id, findings, *, assisted):
    project, _, state, hashes, attempt, result, owned, _ = settled(
        project, task_id, assisted=assisted
    )
    if not isinstance(findings, list) or not 1 <= len(findings) <= 8:
        raise ValueError("Supply 1..8 Primary-confirmed findings")
    bound, ids = [], set()
    for finding in findings:
        if set(finding) != {"id", "contract_id", "text", "path", "line"}:
            raise ValueError("Finding requires id, contract_id, text, path, line")
        identity, text = finding["id"], finding["text"]
        if (
            not isinstance(identity, str)
            or not identity
            or identity in ids
            or finding["contract_id"] not in owned
            or not isinstance(text, str)
            or not 1 <= len(text) <= 2000
        ):
            raise ValueError("Invalid or duplicate finding / unowned contract")
        ids.add(identity)
        relative, line = finding["path"], finding["line"]
        if relative not in hashes or type(line) is not int:
            raise ValueError("Source must be a current approved input")
        lines = (project / relative).read_text(encoding="utf-8-sig").splitlines()
        if not 1 <= line <= len(lines):
            raise ValueError("Source line outside observed file")
        bound.append(
            {
                "id": identity,
                "contract_id": finding["contract_id"],
                "text": text,
                "source": {
                    "path": relative,
                    "sha256": hashes[relative],
                    "line": line,
                    "quote": lines[line - 1],
                },
            }
        )
    return {
        "kind": "confirmed_defect",
        "previous_attempt": attempt,
        "result_sha256": digest(result),
        "source_hashes": hashes,
        "contract_ids": list(dict.fromkeys(f["contract_id"] for f in bound)),
        "text": "\n".join(f["text"] for f in bound),
        "assisted": assisted,
        "defect": {
            "check_sha256": state["latest_check"]["sha256"],
            "assisted": assisted,
            "findings": bound,
        },
        "review_disposition": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--findings", type=Path)
    inputs.add_argument("--evidence-request", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--assistance", choices=["assisted", "unassisted"], required=True
    )
    args = parser.parse_args()
    builder = build if args.findings is not None else build_evidence
    value = builder(
        args.project,
        args.task_id,
        read(args.findings if args.findings is not None else args.evidence_request),
        assisted=args.assistance == "assisted",
    )
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
