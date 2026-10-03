"""Read-only replay of a selected supervised cohort, never release acceptance."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def within(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    target.relative_to(root.resolve())
    return target


def replay_refs(root: Path, run: Path, report: dict) -> int:
    """Match pre-edit citations to hashed preimages and actual successful reads."""
    if (
        report.get("status") != "success"
        or report.get("semantic_verdict") != "not_evaluated"
    ):
        raise ValueError("not a successful localization report")
    refs = report.get("source_refs", [])
    if (
        not refs
        or not any(ref.get("kind") == "test" for ref in refs)
        or not any(ref.get("kind") in {"implementation", "definition"} for ref in refs)
    ):
        raise ValueError("missing implementation/test source evidence")
    preimages = {item["path"]: item for item in load(run / "preimages.json")}
    events = [
        json.loads(line)
        for line in within(root, report["diagnostic_log"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    displayed: dict[str, set[int]] = {}
    for event in events:
        facts = event.get("facts", {})
        if (
            event.get("event") == "turn"
            and facts.get("action") == "READ_FILE"
            and facts.get("status") == "ok"
        ):
            displayed.setdefault(facts["path"], set()).update(
                range(facts["start_line"], facts["end_line"] + 1)
            )
    for ref in refs:
        relative = ref["path"]
        preimage = preimages.get(relative)
        source = within(root, preimage["archive_path"] if preimage else relative)
        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if ref.get("source_hash") != digest or (
            preimage and preimage["sha256"] != digest
        ):
            raise ValueError(f"citation hash mismatch: {relative}")
        start, end = ref["start_line"], ref["end_line"]
        lines = raw.decode("utf-8-sig").splitlines()
        if (
            type(start) is not int
            or type(end) is not int
            or not 1 <= start <= end <= len(lines)
        ):
            raise ValueError(f"citation range invalid: {relative}")
        if ref["quote"] != "\n".join(lines[start - 1 : end]):
            raise ValueError(f"citation quote mismatch: {relative}")
        if not set(range(start, end + 1)).issubset(displayed.get(relative, set())):
            raise ValueError(f"citation lacks successful read evidence: {relative}")
    return len(refs)


def replay_validation(root: Path, run: Path) -> dict:
    """Corroborate reported validation with real JUnit and current owned inputs.

    Cross-unit read-only inputs may legitimately change in a later unit; the
    feature's current integration archive proves those combined inputs instead.
    Each unit's changed sources and protected focused tests must still match.
    """
    validation = load(run / "validation.json")
    handoff = load(run / "handoff.json")
    packet = load(run / "packet.json")
    if validation != handoff.get("validation") or validation.get("status") != "passed":
        raise ValueError("canonical validation/handoff disagree or did not pass")
    focused = validation["focused_tests"]
    recorded = focused["junit"]
    junit_path = within(root, recorded["path"])
    junit_path.relative_to(run.resolve())
    cases = ET.parse(junit_path).getroot().findall(".//testcase")
    skipped = sum(case.find("skipped") is not None for case in cases)
    executed = len(cases) - skipped
    if (
        focused.get("status") != "passed"
        or focused.get("exit_code") != 0
        or not executed
        or any(
            case.find("failure") is not None or case.find("error") is not None
            for case in cases
        )
        or recorded.get("tests") != len(cases)
        or recorded.get("executed") != executed
        or recorded.get("skipped") != skipped
    ):
        raise ValueError("real focused JUnit does not prove the reported pass")
    changed = {item["path"]: item["final_sha256"] for item in handoff["changed_files"]}
    inputs = focused.get("input_facts", {})
    test_paths = {node_id.split("::", 1)[0] for node_id in packet["focused_tests"]}
    for relative in test_paths | set(changed):
        fact = inputs.get(relative, {})
        actual = hashlib.sha256(within(root, relative).read_bytes()).hexdigest()
        if fact.get("sha256") != actual or (
            relative in changed and changed[relative] != actual
        ):
            raise ValueError(
                f"owned source or focused test changed after validation: {relative}"
            )
    config = load(root / ".local-agents/config.json")
    required = {
        check["id"]
        for check in config["validation_profiles"][packet["validation_profile"]].get(
            "commands", []
        )
    }
    checks = validation.get("configured_checks", [])
    if {check["id"] for check in checks} != required or any(
        check.get("status") != "passed" or check.get("exit_code") != 0
        for check in checks
    ):
        raise ValueError("configured checks incomplete or did not pass")
    return {
        "executed_focused_tests": executed,
        "configured_check_ids": sorted(required),
    }


def verify_primary_takeover(
    root: Path, initial: Path, terminal: Path, selection: dict
) -> None:
    """Prove explicit Primary changes, never credit them as a Coder repair."""
    record = load(within(root, selection["primary_takeover_record"]))
    parent = load(initial / "packet.json")
    if (
        any(
            record.get(key) != parent.get(key)
            for key in ("feature_id", "task_id", "unit_id")
        )
        or record.get("initial_run_id") != parent["run_id"]
    ):
        raise ValueError("Primary takeover names another unit")
    if (
        record.get("coder_repair_success") is not False
        or record.get("protected_tests_changed") is not False
    ):
        raise ValueError(
            "takeover must not claim Coder repair or change protected tests"
        )
    failed_runs = record.get("quality_failed_runs", [])
    if (
        not failed_runs
        or failed_runs[0] != parent["run_id"]
        or len(set(failed_runs)) != len(failed_runs)
    ):
        raise ValueError("takeover lacks explicit failed history")
    for run_id in failed_runs:
        path = within(root, f".agent/tasks/{parent['task_id']}/runs/{run_id}")
        if path.parent != initial.parent:
            raise ValueError("takeover history escapes task runs")
        decision = load(path / "review.json").get("decision")
        if decision not in {"rework", "takeover"} or (
            run_id == failed_runs[-1] and decision != "takeover"
        ):
            raise ValueError("takeover lacks immutable Primary rejection/takeover")
    changes = load(initial / "handoff.json")["changed_files"]
    if (
        len(changes) != 1
        or changes[0]["path"] != record.get("source_path")
        or changes[0]["final_sha256"] != record.get("before_sha256")
    ):
        raise ValueError("takeover before source differs from rejected parent")
    if load(terminal / "handoff.json")["changed_files"]:
        raise ValueError("takeover verification must not obscure further Coder edits")
    preimages = {item["path"]: item for item in load(terminal / "preimages.json")}
    image = preimages.get(record["source_path"])
    if (
        not image
        or image["sha256"] != record.get("after_sha256")
        or any(
            hashlib.sha256(within(root, path).read_bytes()).hexdigest()
            != record["after_sha256"]
            for path in (image["archive_path"], record["source_path"])
        )
    ):
        raise ValueError("takeover corrected source or verification preimage differs")
    old_inputs = load(initial / "validation.json")["focused_tests"]["input_facts"]
    new_inputs = load(terminal / "validation.json")["focused_tests"]["input_facts"]
    for node in parent["focused_tests"]:
        path = node.split("::", 1)[0]
        actual = hashlib.sha256(within(root, path).read_bytes()).hexdigest()
        if (
            old_inputs.get(path, {}).get("sha256") != actual
            or new_inputs.get(path, {}).get("sha256") != actual
        ):
            raise ValueError("takeover protected test inputs changed")
    proof = record["primary_validation"]
    cases = ET.parse(within(root, proof["junit"])).getroot().findall(".//testcase")
    required = selection.get("required_primary_tests", [])
    if (
        not required
        or not set(required).issubset({case.get("name") for case in cases})
        or len(cases) != proof.get("executed")
        or any(
            any(case.find(tag) is not None for tag in ("failure", "error", "skipped"))
            for case in cases
        )
    ):
        raise ValueError("takeover actual boundary JUnit missing or not passing")


def select_primary_rework(root: Path, initial: Path, selection: dict) -> Path:
    """Select an explicit inherited run without erasing the rejected first run.

    Acceptance and current validation are checked separately by the existing
    canonical verifier. This only establishes the immutable rework lineage.
    """
    parent = load(initial / "packet.json")
    review = load(initial / "review.json")
    if selection.get("initial_run_id") != parent["run_id"] or any(
        selection.get(key) != parent[key] for key in ("task_id", "unit_id")
    ):
        raise ValueError("rework selection names another initial unit")
    if review.get("decision") != "rework":
        raise ValueError("initial run lacks immutable Primary rework")
    run_id = selection.get("run_id")
    if not isinstance(run_id, str) or not run_id or run_id == parent["run_id"]:
        raise ValueError("rework needs a distinct explicit run id")
    terminal = within(root, f".agent/tasks/{parent['task_id']}/runs/{run_id}")
    if terminal.parent != initial.parent:
        raise ValueError("rework archive escapes original task runs")
    child = load(terminal / "packet.json")
    if (
        child.get("parent_run_id") != parent["run_id"]
        or child.get("preserve_contract") is not True
        or child.get("attempt", 0) <= parent.get("attempt", 1)
        or child.get("packet_revision", 0) <= parent.get("packet_revision", 1)
        or not child.get("review_feedback")
    ):
        raise ValueError("rework is not an increased contract-preserving child")
    immutable = (
        "task_id",
        "feature_id",
        "unit_id",
        "plan_revision",
        "primary_plan_sha256",
        "risk",
        "dependencies",
        "owned_contract_ids",
        "scope",
        "required_behavior",
        "required_order",
        "forbidden_orderings",
        "focused_tests",
        "acceptance_criteria",
        "acceptance_scenarios",
        "validation_profile",
        "supplemental_tests",
    )
    if any(child.get(key) != parent.get(key) for key in immutable):
        raise ValueError("rework changed preserved Primary contract or inputs")
    if "primary_takeover_record" in selection:
        verify_primary_takeover(root, initial, terminal, selection)
        return terminal
    preimages = {item["path"]: item for item in load(terminal / "preimages.json")}
    for change in load(initial / "handoff.json")["changed_files"]:
        preimage = preimages.get(change["path"])
        if not preimage or preimage["sha256"] != change["final_sha256"]:
            raise ValueError("rework did not start from rejected parent source")
        if (
            hashlib.sha256(
                within(root, preimage["archive_path"]).read_bytes()
            ).hexdigest()
            != preimage["sha256"]
        ):
            raise ValueError("rework preimage archive was modified")
    return terminal


def audit(candidate: Path) -> dict:
    spec = importlib.util.spec_from_file_location(
        "candidate_contract", KIT / ".local-agents/coordinator-contract.py"
    )
    assert spec and spec.loader
    contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contract)
    freeze = load(candidate / "freeze.json")["runtime"]
    for relative, digest in freeze["runtime_manifest"]["files"].items():
        if hashlib.sha256(within(KIT, relative).read_bytes()).hexdigest() != digest:
            raise ValueError(f"current runtime changed: {relative}")
    config = load(KIT / ".local-agents/config.json")
    config["explorer_mode"] = "locate"
    encoded = json.dumps(
        config, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    if (
        hashlib.sha256(encoded).hexdigest()
        != freeze["runtime_manifest"]["role_config_sha256"]
    ):
        raise ValueError("current role configuration changed")
    if list(sys.version_info[:3]) != freeze["runtime_manifest"]["python_version"]:
        raise ValueError("Python version changed")
    units = []
    selection_path = candidate / "primary-rework-selection.json"
    selections = load(selection_path) if selection_path.exists() else {}
    if not isinstance(selections, dict):
        raise TypeError("Primary rework selections must be an object")
    used_selections = set()
    initial_reworks = []
    case_hashes = {}
    manifest = load(candidate / "freeze.json")["cohort"]
    expected_cases = set(manifest["standard_cases"])
    for round_number in (1, 2):
        cells = sorted((candidate / f"round-{round_number}").glob("*.json"))
        if (
            len(cells) != len(expected_cases)
            or {load(path)["case"] for path in cells} != expected_cases
        ):
            raise ValueError(
                "standard round must contain the exact frozen case identities"
            )
        for path in cells:
            cell = load(path)
            if (
                cell["provenance"]["runtime_sha256"] != freeze["runtime_sha256"]
                or not cell["qualified_pass"]
            ):
                raise ValueError(f"unqualified or foreign-runtime cell: {path}")
            key = cell["case"]
            digest = cell["provenance"]["case_input_sha256"]
            if key in case_hashes and case_hashes[key] != digest:
                raise ValueError(f"case inputs differ across rounds: {key}")
            case_hashes[key] = digest
            root = Path(cell["workspace"])
            initial_run_id = f"{key}-a1"
            run_id = initial_run_id
            selection_key = f"round-{round_number}/{key}"
            if selection_key in selections:
                initial = (
                    root / ".agent/tasks" / f"stability-{key}" / "runs" / initial_run_id
                )
                terminal = select_primary_rework(
                    root, initial, selections[selection_key]
                )
                run_id = terminal.name
                used_selections.add(selection_key)
                initial_reworks.append(
                    {
                        "cell": selection_key,
                        "initial_run_id": initial_run_id,
                        "terminal_run_id": run_id,
                        "initial_primary_decision": "rework",
                        "primary_takeover": "primary_takeover_record"
                        in selections[selection_key],
                    }
                )
            units.append(
                (
                    root,
                    f"stability-{key}",
                    key,
                    run_id,
                    Path(cell["explorer_report"]),
                    ".agent/feature-plan.json",
                )
            )
        reference = load(candidate / f"split-round-{round_number}-reference.json")
        root = Path(reference["workspace"])
        provenance = load(root / ".agent/split-provenance.json")
        if provenance["runtime_sha256"] != freeze["runtime_sha256"]:
            raise ValueError("split runtime differs from standard freeze")
        digest = provenance["case_input_sha256"]
        if (
            "sample-identity" in case_hashes
            and case_hashes["sample-identity"] != digest
        ):
            raise ValueError("split inputs differ across rounds")
        case_hashes["sample-identity"] = digest
        for unit in ("fingerprint", "reuse-key"):
            units.append(
                (
                    root,
                    "stability-sample-identity-split",
                    unit,
                    f"{unit}-a1",
                    root / f".agent/split-{unit}-explorer-report.json",
                    ".agent/split-feature-plan.json",
                )
            )
        if (
            load(
                root
                / ".agent/integration/stability-sample-identity-split/primary-review.json"
            ).get("decision")
            != "accept"
        ):
            raise ValueError("missing split Primary integration acceptance")
        handoff = contract.compact_primary_handoff(
            load(root / ".agent/split-feature-plan.json"),
            root,
            {
                unit: {
                    "task_id": "stability-sample-identity-split",
                    "run_id": f"{unit}-a1",
                }
                for unit in ("fingerprint", "reuse-key")
            },
        )
        if handoff.get("status") != "eligible_for_primary_final_review":
            raise ValueError("split final integration is not currently verified")
    evidence = []
    if set(selections) != used_selections:
        raise ValueError("unknown or unused Primary rework selection")
    for root, task, unit, run_id, report_path, plan_path in units:
        run = root / ".agent/tasks" / task / "runs" / run_id
        accepted = contract.accepted_units_from_archives(
            load(root / plan_path), root, {unit: {"task_id": task, "run_id": run_id}}
        )
        if unit not in accepted:
            raise ValueError(f"unaccepted canonical unit: {unit}")
        validation = replay_validation(root, run)
        # Explorer's original localization cites the original pre-edit snapshot,
        # not the already modified source observed by a subsequent Coder rework.
        citation_run = root / ".agent/tasks" / task / "runs" / f"{unit}-a1"
        refs = replay_refs(root, citation_run, load(report_path))
        evidence.append(
            {
                "workspace": str(root),
                "unit_id": unit,
                "run_id": run_id,
                "verified_source_refs": refs,
                "validation": validation,
            }
        )
    return {
        "assessment": "canonical_replay_not_release_acceptance",
        "runtime_sha256": freeze["runtime_sha256"],
        "behavior_cells": 22,
        "units": len(units),
        "accepted_units": len(evidence),
        "initial_primary_rework_count": len(initial_reworks),
        "primary_takeover_count": sum(
            item["primary_takeover"] for item in initial_reworks
        ),
        "initial_primary_accept_count": len(evidence) - len(initial_reworks),
        "primary_reworks": initial_reworks,
        "verified_source_refs": sum(item["verified_source_refs"] for item in evidence),
        "semantic_diagnosis": "not_evaluated",
        "evidence": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.candidate.resolve())
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
