"""One explicitly authorized model-Coordinator step; no automatic acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import importlib.util
import sys
import subprocess


def _load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MODEL = _load("supervised_coordinator_model", "coordinator-runtime.py")
ROUTE = _load("supervised_coordinator_route", "coordinator-localization.py")
CONTRACT = MODEL.CONTRACT
EXPLORATION = _load("supervised_coordinator_exploration", "coordinator-exploration.py")


def _write_once(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def run_step(
    *,
    root: Path,
    plan: dict,
    context: dict,
    request: dict,
    explorer: dict,
    run_refs: dict,
    config: dict,
    config_path: Path,
    authorized: bool,
    expected_sequence: int,
    client: Any,
    router: Callable = ROUTE.run_localization_unit,
    manage_exploration: bool = False,
    explorer_runner: Callable = EXPLORATION.run_explorer,
    recovery_authorization_path: Path | None = None,
    proposal_id: str | None = None,
) -> tuple[int, dict]:
    if authorized is not True:
        raise ValueError("explicit Primary authorization is required for each supervised step")
    CONTRACT.validate_feature_plan(plan)
    identity = context.get("identity") if isinstance(context, dict) else None
    if not isinstance(identity, dict) or set(identity) != {
        "unit_id",
        "run_id",
        "attempt",
        "packet_revision",
    }:
        raise ValueError("Primary context must grant exact proposal identity")
    for key in ("unit_id", "run_id"):
        CONTRACT.identifier(identity[key], key)
    proposal_id = CONTRACT.identifier(proposal_id or identity["run_id"], "proposal_id")
    execution_root = root / ".agent/tasks" / plan["task_id"] / "runs" / identity["run_id"]
    CONTRACT._state_path(root, execution_root / "packet.json")
    if execution_root.exists():
        raise ValueError("Coder run archive already exists; proposal retry cannot replay execution")
    if manage_exploration:
        if config.get("explorer_mode") != "locate":
            raise ValueError("managed exploration requires locate mode")
        if (
            set(request) != {"capability", "task_id", "unit_id", "question"}
            or request.get("capability") != "localization_only"
            or request.get("task_id") != plan["task_id"]
            or request.get("unit_id") != identity["unit_id"]
            or not isinstance(request.get("question"), str)
            or not request["question"].strip()
        ):
            raise ValueError(
                "managed exploration requires a Primary-approved localization question"
            )
    state_path = root / ".agent/coordinator" / plan["feature_id"] / "state.json"
    state = CONTRACT.load_coordinator_state(plan, root, state_path)
    if type(expected_sequence) is not int or state["sequence"] != expected_sequence:
        raise ValueError("Primary-authorized sequence is stale")
    recovery = None
    if recovery_authorization_path is not None:
        recovery = ROUTE.authorized_rework_context(
            repo_root=root,
            plan=plan,
            state=state,
            identity=identity,
            authorization_path=recovery_authorization_path,
            run_refs=run_refs,
        )
    archive = root / ".agent/coordinator" / plan["feature_id"] / "proposals" / proposal_id
    CONTRACT._state_path(root, archive / "packet.json")
    archive.mkdir(parents=True, exist_ok=False)
    _write_once(
        archive / "authorization.json",
        {
            "identity": identity,
            "proposal_id": proposal_id,
            "expected_sequence": expected_sequence,
            "primary_plan_sha256": CONTRACT.authority_fingerprint(plan),
            "context_sha256": hashlib.sha256(
                json.dumps(context, sort_keys=True).encode()
            ).hexdigest(),
            "capability": "localization_only",
            "feature_accepted": False,
            "primary_recovery": recovery,
        },
    )
    with MODEL.RESIDENCY.role_model_lease(client, config):
        execution = CONTRACT.verified_execution_evidence(plan, root, state, run_refs)
        execution["primary_authorized_rework"] = recovery
        _write_once(archive / "execution-input.json", execution)
        decision = MODEL.probe(
            plan,
            context,
            "decision",
            client,
            execution_evidence=execution,
            reasoning_strength=config.get("coordinator_reasoning_strength"),
        )
        _write_once(archive / "decision.json", decision)
        if decision["status"] != "protocol_valid":
            return 1, {
                "status": "primary_attention_required",
                "stage": "decision",
                "archive": str(archive),
            }
        current = CONTRACT.load_coordinator_state(plan, root, state_path)
        candidate = CONTRACT.validate_decision(plan, decision["output"])
        if recovery and candidate["decision"] == "REWORK_LOCAL":
            if (
                candidate["unit_id"] != identity["unit_id"]
                or current["sequence"] != expected_sequence
            ):
                raise ValueError("rework decision differs from Primary identity or sequence")
            fresh = ROUTE.authorized_rework_context(
                repo_root=root,
                plan=plan,
                state=current,
                identity=identity,
                authorization_path=recovery_authorization_path,
                run_refs=run_refs,
            )
            if fresh != recovery:
                raise ValueError("Primary recovery authorization changed during inference")
            gate = {
                "decision": candidate,
                "state_sequence": expected_sequence,
                "primary_recovery": fresh,
                "dispatch_allowed": False,
                "feature_accepted": False,
            }
        else:
            gate = CONTRACT.gate_model_decision(
                plan, root, current, candidate, run_refs, expected_sequence=expected_sequence
            )
        _write_once(archive / "decision-gate.json", gate)
        if gate["decision"]["decision"] not in {"CONTINUE", "REWORK_LOCAL"}:
            result = {
                "status": "primary_final_review_required"
                if gate["decision"]["decision"] == "FEATURE_READY"
                else "primary_attention_required",
                "gate": gate,
                "archive": str(archive),
                "feature_accepted": False,
            }
            if gate["decision"]["decision"] == "FEATURE_READY":
                result["handoff"] = CONTRACT.compact_primary_handoff(plan, root, run_refs)
                _write_once(archive / "primary-handoff.json", result["handoff"])
            _write_once(archive / "result.json", result)
            return 0, result
        if gate["decision"]["unit_id"] != identity["unit_id"]:
            raise ValueError("model selected a unit outside this Primary authorization")
    if manage_exploration:
        _write_once(archive / "explorer-input.json", explorer)
        try:
            proof = CONTRACT.validate_localization_evidence(
                plan, identity["unit_id"], request, explorer, repo_root=root
            )
            evidence_status = {"valid": True, "source_refs": proof["source_refs"]}
        except ValueError as exc:
            evidence_status = {"valid": False, "reason": str(exc)}
        _write_once(archive / "explorer-input-gate.json", evidence_status)
        with MODEL.RESIDENCY.role_model_lease(client, config):
            exploration = EXPLORATION.choose(
                context,
                request,
                explorer,
                client,
                evidence_valid=evidence_status["valid"],
                reasoning_strength=config.get("coordinator_reasoning_strength"),
            )
        _write_once(archive / "exploration-choice.json", exploration)
        if (
            exploration["status"] != "protocol_valid"
            or exploration["output"]["action"] == "ESCALATE_PRIMARY"
        ):
            return 1, {
                "status": "primary_attention_required",
                "stage": "exploration",
                "archive": str(archive),
                "feature_accepted": False,
            }
        if exploration["output"]["action"] == "RUN_EXPLORER":
            observed = explorer_runner(root, request, config_path, archive / "explorer-report.json")
            _write_once(archive / "explorer-execution.json", observed)
            explorer = observed["report"]
            if observed["exit_code"] != 0:
                return 1, {
                    "status": "primary_attention_required",
                    "stage": "explorer",
                    "archive": str(archive),
                    "feature_accepted": False,
                }
    proposal_context = dict(context)
    proposal_context["source_refs"] = explorer.get("source_refs", [])
    _write_once(archive / "proposal-context.json", proposal_context)
    with MODEL.RESIDENCY.role_model_lease(client, config):
        proposal = MODEL.probe(
            plan,
            proposal_context,
            "proposal",
            client,
            reasoning_strength=config.get("coordinator_reasoning_strength"),
        )
    _write_once(archive / "proposal.json", proposal)
    if proposal["status"] != "protocol_valid":
        return 1, {
            "status": "primary_attention_required",
            "stage": "proposal",
            "archive": str(archive),
        }
    packet = CONTRACT.materialize_bounded_packet(plan, proposal["output"])
    CONTRACT.validate_localization_dispatch(plan, packet, request, explorer, repo_root=root)
    packet_path = archive / "packet.json"
    _write_once(packet_path, packet)
    code, result = router(
        repo_root=root,
        plan=plan,
        packet_path=packet_path,
        request=request,
        explorer_report=explorer,
        state_path=state_path,
        run_refs=run_refs,
        config_path=config_path,
        coder_report_path=archive / "coder-report.json",
        review_report_path=archive / "review-report.json",
        authorized_sequence=expected_sequence,
        recovery_authorization_path=recovery_authorization_path,
    )
    _write_once(archive / "result.json", result)
    return code, {
        "status": result["status"],
        "archive": str(archive),
        "unit_result": result,
        "feature_accepted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for field in ("plan", "context", "request", "run-refs"):
        parser.add_argument("--" + field, type=Path, required=True)
    parser.add_argument("--explorer-report", type=Path)
    parser.add_argument("--manage-exploration", action="store_true")
    parser.add_argument("--recovery-authorization", type=Path)
    parser.add_argument("--proposal-id")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--authorize-step", action="store_true")
    parser.add_argument("--expected-sequence", type=int, required=True)
    args = parser.parse_args()
    try:

        def read(path: Path) -> dict:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(value, dict):
                raise ValueError("step inputs must be objects")
            return value

        config = read(args.config)
        client = MODEL.WORKER.LMStudioClient(
            config["lmstudio_base_url"],
            config["coordinator_model"],
            structured_output=False,
            timeout=config.get("coordinator_request_timeout_seconds", 360),
            max_tokens=config.get("coordinator_max_tokens", 4096),
            context_length=config.get("coordinator_context_length", 24576),
        )
        code, result = run_step(
            root=Path.cwd(),
            plan=read(args.plan),
            context=read(args.context),
            request=read(args.request),
            explorer=read(args.explorer_report) if args.explorer_report else {},
            run_refs=read(args.run_refs),
            config=config,
            config_path=args.config.resolve(),
            authorized=args.authorize_step,
            expected_sequence=args.expected_sequence,
            client=client,
            manage_exploration=args.manage_exploration,
            recovery_authorization_path=args.recovery_authorization,
            proposal_id=args.proposal_id,
        )
    except (
        OSError,
        ValueError,
        KeyError,
        MODEL.RESIDENCY.ModelResidencyError,
        MODEL.WORKER.WorkerError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
