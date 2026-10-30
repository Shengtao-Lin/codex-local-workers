"""Explicit Primary steps for capability-qualified proposals; never an agent loop.

Inputs and acceptance references are trusted Primary files. This is not an OS
sandbox. Model proposals cannot grant themselves capabilities or acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import importlib.util


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BRIEF = load("limited_brief", "coordinator-brief.py")
CONTRACT = BRIEF.CONTRACT


def read(path):
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Primary input must be a JSON object")
    return value


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_path(root, path):
    return CONTRACT._state_path(root, path)


def write_once(root, path, value):
    path = state_path(root, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)


def runtime_hashes():
    return {
        p.name: sha(p)
        for p in Path(__file__).parent.iterdir()
        if p.is_file() and p.suffix in {".py", ".ps1", ".toml"}
    }


def route_plan(plan, catalog):
    """An exact Primary catalog grants eligibility, never a model family label."""
    expected = {c["id"] for c in plan["contracts"]}
    if not isinstance(catalog, dict) or set(catalog) != expected:
        raise ValueError("complete Primary capability catalog required")
    for unit in plan["units"]:
        entries = [catalog[c] for c in unit["owned_contract_ids"]]
        if {e["owner"] for e in entries} != {unit["owner"]} or unit["owner"] not in {
            "primary",
            "local-coder",
        }:
            raise ValueError("capability owner mismatch or mixed-owner atomic unit")
        for entry in entries:
            if not entry.get("evidence") or entry.get("route") != (
                "direct_local" if unit["owner"] == "local-coder" else "primary_owned"
            ):
                raise ValueError("unqualified or unsupported capability route")
        if (
            set(unit["scope_authority"]["modify"]) != {p for e in entries for p in e["modify"]}
            or unit["scope_authority"]["create"]
        ):
            raise ValueError("unit write scope does not match capability catalog")
    return plan


def accepted_state(root, plan, initial_hashes, refs):
    """Use canonical independent accepts, then check the entire current snapshot.

    Primary-owned units additionally require hashed, nonempty passing tests and
    lint/format receipts. Protected inputs stay at their approved initial hashes.
    """
    # Check archive paths before the legacy reader follows any host reparse path.
    for unit_id, run_ref in refs.items():
        CONTRACT.identifier(unit_id, "accepted unit")
        if run_ref:
            task = CONTRACT.identifier(run_ref.get("task_id"), "accepted task")
            run = CONTRACT.identifier(run_ref.get("run_id"), "accepted run")
            state_path(root, root / ".agent/tasks" / task / "runs" / run)
        else:
            state_path(
                root, root / ".agent/primary-reviews" / plan["feature_id"] / (unit_id + ".json")
            )
    accepted = CONTRACT.accepted_units_from_archives(plan, root, refs)
    expected = dict(initial_hashes)
    units = {u["unit_id"]: u for u in plan["units"]}
    for unit_id, run_ref in refs.items():
        if not set(units[unit_id]["dependencies"]) <= accepted:
            raise ValueError("accepted reference omits its dependency")
        if units[unit_id]["owner"] == "primary":
            path = root / ".agent/primary-reviews" / plan["feature_id"] / (unit_id + ".json")
            record = read(state_path(root, path))
            changes = record["post_source_hashes"]
            if (
                set(changes) != set(record["changed_files"])
                or not set(changes) <= set(units[unit_id]["scope_authority"]["modify"])
                or record.get("primary_authorized") is not True
            ):
                raise ValueError("invalid Primary post-source attribution or authority")
            prefix = ".agent/" + unit_id + "-primary"
            checks = [prefix + "-" + s + ".json" for s in ("tests", "lint", "format")]
            junit = prefix + ".xml"
            if record.get("check_records") != checks or record.get("junit") != junit:
                raise ValueError("Primary required checks omitted")
            if {i["path"] for i in record["evidence"]} != {*checks, junit}:
                raise ValueError("Primary validation evidence incomplete")
            for item in record["evidence"]:
                if sha(state_path(root, root / item["path"])) != item["sha256"]:
                    raise ValueError("Primary validation evidence drift")
            if any(
                type(read(root / p).get("exit")) is not int or read(root / p)["exit"] != 0
                for p in checks
            ):
                raise ValueError("Primary check did not pass")
            cases = list(ET.parse(root / junit).iter("testcase"))
            if not cases or any(
                c.find(tag) is not None for c in cases for tag in ("failure", "error", "skipped")
            ):
                raise ValueError("Primary tests missing, failing or skipped")
        else:
            archive = root / ".agent/tasks" / run_ref["task_id"] / "runs" / run_ref["run_id"]
            record = read(state_path(root, archive / "handoff.json"))
            validation = read(state_path(root, archive / "validation.json"))
            focused = validation.get("focused_tests", {})
            if (
                validation.get("status") != "passed"
                or focused.get("status") != "passed"
                or (focused.get("inputs_unchanged") is not True)
                or any(c.get("status") != "passed" for c in validation.get("configured_checks", []))
            ):
                raise ValueError("accepted local validation is not current passed evidence")
            junit = state_path(root, root / focused["junit"]["path"])
            if not junit.is_relative_to(archive):
                raise ValueError("local JUnit does not belong to the accepted run")
            cases = list(ET.parse(junit).iter("testcase"))
            if not cases or any(
                c.find(tag) is not None for c in cases for tag in ("failure", "error", "skipped")
            ):
                raise ValueError("local tests missing, failing or skipped")
            primary = read(state_path(root, archive / "review.json"))
            review = CONTRACT.identifier(primary["local_review_id"], "accepted review")
            state_path(root, root / ".agent/tasks" / run_ref["task_id"] / "reviews" / review)
            changes = {c["path"]: c["final_sha256"] for c in record["changed_files"]}
        if not set(changes) <= initial_hashes.keys():
            raise ValueError("accepted change lacks approved source preimage")
        expected.update(changes)
    BRIEF.assert_sources_current({"source_hashes": expected}, root)
    return accepted


def require_authority(authorized):
    if authorized is not True:
        raise ValueError("explicit Primary step authorization required")


def approve(root, brief, proposal, approval_path, config_path, *, authorized, note):
    require_authority(authorized)
    plan = BRIEF.proposal_plan(brief, proposal)
    if plan is None:
        raise ValueError("unresolved proposal cannot execute")
    route_plan(plan, brief.get("capability_catalog"))
    approval_path = state_path(root, approval_path)
    binding = approval_path.with_suffix(".binding.json")
    if binding.exists() or approval_path.exists():
        raise ValueError("approval is immutable; use a new reviewed identity")
    BRIEF.approve(brief, proposal, root, approval_path, primary_review_note=note)
    write_once(
        root,
        binding,
        {
            "approval_sha256": sha(approval_path),
            "config_sha256": sha(config_path),
            "runtime_hashes": runtime_hashes(),
            "no_unattended_loop": True,
        },
    )
    return {"status": "approved", "plan": plan, "dispatch_allowed": False}


def approved(root, brief, proposal, approval_path, config_path, refs):
    """Do not compare accepted edits to initial bytes; verify their provenance."""
    approval_path = state_path(root, approval_path)
    record = read(approval_path)
    binding = read(state_path(root, approval_path.with_suffix(".binding.json")))
    plan = BRIEF.proposal_plan(brief, proposal)
    if (
        plan is None
        or record.get("approval_authority") != "trusted_primary_api"
        or not (
            isinstance(record.get("primary_review_note"), str)
            and record["primary_review_note"].strip()
        )
    ):
        raise ValueError("missing trusted Primary approval")
    if record.get("brief_sha256") != BRIEF.digest(brief) or (
        record.get("proposal_sha256"),
        record.get("approved_plan_sha256"),
        record.get("approved_plan"),
        record.get("source_hashes"),
    ) != (BRIEF.digest(proposal), BRIEF.digest(plan), plan, brief["source_hashes"]):
        raise ValueError("approval stale or contract drift")
    if binding != {
        "approval_sha256": sha(approval_path),
        "config_sha256": sha(config_path),
        "runtime_hashes": runtime_hashes(),
        "no_unattended_loop": True,
    }:
        raise ValueError("approval, configuration or runtime drift")
    route_plan(plan, brief.get("capability_catalog"))
    required = set(brief["authority"]["modify"] + brief["authority"]["readonly"])
    if not required <= brief["source_hashes"].keys():
        raise ValueError("approval lacks writable/protected input hashes")
    return plan, accepted_state(root, plan, brief["source_hashes"], refs)


def dispatch(
    root,
    brief,
    proposal,
    approval_path,
    config_path,
    refs,
    packet,
    *,
    authorized,
    runner=subprocess.run,
):
    require_authority(authorized)
    plan, accepted = approved(root, brief, proposal, approval_path, config_path, refs)
    packet = CONTRACT.validate_unit_packet(plan, packet)
    unit = next(u for u in plan["units"] if u["unit_id"] == packet["unit_id"])
    if unit["owner"] != "local-coder":
        raise ValueError("Primary-owned unit cannot enter a local worker")
    if unit["unit_id"] in accepted or not set(unit["dependencies"]) <= accepted:
        raise ValueError("duplicate or unaccepted dependency")
    config = read(config_path)
    if config.get("single_model_residency") is not True:
        raise ValueError("limited entry requires single model residency")
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    if state_path(root, archive).exists():
        raise ValueError("run identity already exists")
    step = root / ".agent/limited" / plan["feature_id"] / unit["unit_id"]
    # Exclusive file reservation also rejects replay of an unfinished/failed step.
    write_once(
        root,
        step / "authorization.json",
        {
            "primary_authorized": True,
            "run_id": packet["run_id"],
            "accepted_refs": refs,
            "approved_plan_sha256": BRIEF.digest(plan),
            "no_unattended_loop": True,
        },
    )
    write_once(root, step / "packet.json", packet)
    completed = runner(
        [
            config["python"],
            "-B",
            str(Path(__file__).with_name("local-unit.py")),
            "--packet",
            str(step / "packet.json"),
            "--config",
            str(config_path),
            "--coder-report",
            str(step / "coder.json"),
            "--review-report",
            str(step / "reviewer.json"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=config.get("invocation_timeout_seconds", 900) * 2 + 120,
    )
    result = {
        "exit": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "feature_accepted": False,
        "primary_review_required": True,
        "step_archive": str(step),
    }
    write_once(root, step / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("propose", "approve", "dispatch", "inspect"))
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--context", type=Path)
    parser.add_argument(
        "--routing-catalog",
        type=Path,
        help="Opt-in decomposition-only proposal with a trusted Primary qualification catalog",
    )
    parser.add_argument("--refs", type=Path)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--authorize-step", action="store_true")
    parser.add_argument("--note")
    args = parser.parse_args()
    root = Path.cwd().resolve()
    try:
        if args.routing_catalog is not None and args.action != "propose":
            raise ValueError(
                "--routing-catalog is proposal-only; approval and dispatch are unchanged"
            )
        brief = read(state_path(root, args.brief))
        proposal_path = state_path(root, args.proposal)
        config_path = args.config.resolve()
        if args.action == "propose":
            require_authority(args.authorize_step)
            config = read(config_path)
            if config.get("coordinator_enabled") is not True or (
                config.get("single_model_residency") is not True
            ):
                raise ValueError(
                    "proposal requires explicit Coordinator enablement and single residency"
                )
            if proposal_path.exists():
                raise ValueError("proposal identity already exists")
            invalid_path = None
            if args.routing_catalog is not None:
                invalid_path = state_path(root, proposal_path.with_suffix(".invalid.json"))
                if invalid_path.exists():
                    raise ValueError(
                        "invalidated proposal identity already exists; use a new identity"
                    )
            BRIEF.assert_sources_current(brief, root)
            if args.context is None:
                raise ValueError("Primary read-only context required")
            context = read(state_path(root, args.context))
            routing = binding = None
            if args.routing_catalog is not None:
                routing = load("limited_routing", "coordinator-routing.py")
                binding = routing.bind_catalog(brief, read(state_path(root, args.routing_catalog)))
            worker = load("limited_worker", "worker-runtime.py")
            residency = load("limited_residency", "model_residency.py")
            client = worker.LMStudioClient(
                config["lmstudio_base_url"],
                config["coordinator_model"],
                structured_output=False,
                timeout=config.get("coordinator_request_timeout_seconds", 360),
                max_tokens=config.get("coordinator_max_tokens", 4096),
                context_length=config.get("coordinator_context_length", 24576),
            )
            with residency.role_model_lease(client, config):
                selected = routing.probe if routing is not None else BRIEF.probe
                extra = {"binding": binding} if routing is not None else {}
                result = selected(
                    brief,
                    context,
                    client,
                    reasoning_strength=config.get("coordinator_reasoning_strength"),
                    **extra,
                )
            try:
                BRIEF.assert_sources_current(brief, root)
            except (ValueError, OSError) as exc:
                if invalid_path is not None:
                    write_once(
                        root,
                        invalid_path,
                        {
                            "status": "proposal_invalidated",
                            "reason": str(exc),
                            "untrusted_attempt": result,
                            "dispatch_allowed": False,
                        },
                    )
                raise
            write_once(root, proposal_path, result)
        else:
            if args.approval is None:
                raise ValueError("Primary approval path required")
            proposal = read(proposal_path)["proposal"]
            if args.action == "approve":
                result = approve(
                    root,
                    brief,
                    proposal,
                    args.approval,
                    config_path,
                    authorized=args.authorize_step,
                    note=args.note,
                )
            else:
                if args.refs is None:
                    raise ValueError("Primary-selected accepted references required")
                refs = read(state_path(root, args.refs))
                if args.action == "inspect":
                    plan, accepted = approved(
                        root, brief, proposal, args.approval, config_path, refs
                    )
                    result = {
                        "status": "verified",
                        "accepted_units": sorted(accepted),
                        "unit_count": len(plan["units"]),
                        "feature_accepted": False,
                    }
                else:
                    if args.packet is None:
                        raise ValueError("Primary materialized packet required")
                    result = dispatch(
                        root,
                        brief,
                        proposal,
                        args.approval,
                        config_path,
                        refs,
                        read(state_path(root, args.packet)),
                        authorized=args.authorize_step,
                    )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        StopIteration,
        subprocess.TimeoutExpired,
    ) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return result.get("exit", 0)


if __name__ == "__main__":
    raise SystemExit(main())
