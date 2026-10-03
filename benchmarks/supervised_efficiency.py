"""Serial paired measurement of existing and supervised routes, not acceptance.

Both arms retain Primary review. The observer records actual Coordinator
requests without changing the product runtime or its model inputs.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import localization_route_smoke as ROUTE
import stability_e2e as STABILITY
from supervised_candidate_audit import replay_refs

SPEC = importlib.util.spec_from_file_location(
    "efficiency_supervised", STABILITY.KIT / ".local-agents/coordinator-supervised.py"
)
assert SPEC and SPEC.loader
SUPERVISED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUPERVISED)
CONTRACT = SUPERVISED.CONTRACT


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_once(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)


class RequestObserver:
    """Transparent client observer; never adds messages or changes responses."""

    def __init__(self, client, path: Path):
        self.client = client
        self.path = path
        self.requests = []
        # Reserve the diagnostic file before any inference. Never overwrite.
        path.open("x", encoding="utf-8").close()

    def __getattr__(self, name):
        return getattr(self.client, name)

    def complete(self, messages):
        started = datetime.now(UTC).isoformat()
        clock = time.monotonic()
        record = {"started_at": started}
        try:
            response = self.client.complete(messages)
            record["status"] = "completed"
            record["response_sha256"] = hashlib.sha256(response.encode()).hexdigest()
            return response
        except Exception as exc:
            record.update(status="failed", error_type=type(exc).__name__)
            raise
        finally:
            record.update(
                finished_at=datetime.now(UTC).isoformat(),
                seconds=time.monotonic() - clock,
                request_stats=copy.deepcopy(self.client.last_request_stats),
            )
            self.requests.append(record)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")


def usage(requests: list[dict]) -> dict:
    total = 0
    missing = 0
    maximum = None
    for request in requests:
        stats = request.get("request_stats", {})
        tokens = stats.get("response_usage", {}).get("total_tokens")
        if type(tokens) is int:
            total += tokens
        else:
            missing += 1
        context = stats.get("reported_context_utilization")
        if isinstance(context, (int, float)):
            maximum = max(maximum or 0, context)
    return {
        "requests": len(requests),
        "reported_total_tokens": total if missing == 0 else None,
        "known_reported_tokens": total,
        "requests_missing_token_usage": missing,
        "max_reported_context_utilization": maximum,
    }


def event_requests(path: Path) -> list[dict]:
    result = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        event = json.loads(line)
        if event["event"] == "model_request":
            result.append({"request_stats": event["facts"]})
        elif event["event"] == "model_turn" and event["facts"].get("model_request"):
            result.append({"request_stats": event["facts"]["model_request"]})
    return result


def run(pair: Path, case_name: str, mode: str) -> dict:
    source_config = read(STABILITY.KIT / ".local-agents/config.json")
    source_config["explorer_mode"] = "locate"
    frozen = {
        "runtime": ROUTE.runtime_manifest(source_config),
        "observer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "case": case_name,
        "protocol": "paired-medium-risk-no-primary-review-bypass-v1",
    }
    if pair.parent != STABILITY.WORK.resolve():
        raise ValueError("pair must be directly inside stability work")
    pair.mkdir(exist_ok=True)
    freeze_path = pair / "freeze.json"
    if freeze_path.exists():
        if read(freeze_path) != frozen:
            raise ValueError("paired code, role config or case changed")
    else:
        write_once(freeze_path, frozen)
    root = pair / mode
    if root.exists():
        raise ValueError("existing measurement arm cannot be replayed")
    started = datetime.now(UTC).isoformat()
    clock = time.monotonic()
    case = next(case for case in STABILITY.CASES if case.name == case_name)
    config_path, packet_path = STABILITY.prepare(case, root, source_config)
    packet = read(packet_path)
    packet.update(required_order=[], forbidden_orderings=[])
    plan = ROUTE.primary_plan_for_packet(packet)
    proposal = {
        key: packet.get(key, [])
        for key in (
            "unit_id",
            "run_id",
            "attempt",
            "packet_revision",
            "goal",
            "scope",
            "edit_targets",
            "focused_tests",
            "supplemental_tests",
            "implementation_guidance",
        )
    }
    proposal["scope"] = {
        key: packet["scope"][key] for key in ("read", "modify", "create")
    }
    packet = CONTRACT.materialize_bounded_packet(plan, proposal)
    # Trusted benchmark preparation, not model edits or acceptance.
    STABILITY.write_json(packet_path, packet)
    write_once(root / ".agent/feature-plan.json", plan)
    test_path = f"tests/test_{case_name.replace('-', '_')}.py"
    config = read(config_path)
    config.update(
        explorer_required_citation_paths=[test_path],
        explorer_require_test_assertion_citation=True,
    )
    STABILITY.write_json(config_path, config)
    question = (
        f"Locate each implementation of {case.anchor.split('=', 1)[0].strip()} that controls the behavior in "
        f"{test_path}. Find the real files and line ranges with READ_FILE/SEARCH, "
        "and cite the focused test assertions. Return locations only, not a repair "
        "or a prediction that tests pass."
    )
    request = {
        "capability": "localization_only",
        "task_id": packet["task_id"],
        "unit_id": packet["unit_id"],
        "question": question,
    }
    write_once(root / ".agent/localization-request.json", request)
    inputs = {
        "reference_packet": packet,
        "primary_plan": plan,
        "request": request,
        "source_sha256": {
            relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
            for relative in packet["scope"]["modify"] + [test_path, "conftest.py"]
        },
        "role_config_sha256": ROUTE._sha256_json(config),
    }
    write_once(root / "paired-inputs.json", inputs)
    other = (
        pair
        / ("coordinator" if mode == "control" else "control")
        / "paired-inputs.json"
    )
    if other.exists() and read(other) != inputs:
        raise ValueError(
            "paired arms do not have identical actual source, contracts and config"
        )
    baseline = STABILITY.run_command(
        root, [sys.executable, "-m", "pytest", test_path, "-q"], 90
    )
    if baseline.returncode == 0:
        raise ValueError("injected baseline did not fail")
    explorer_path = root / ".agent/explorer-report.json"
    coordinator_requests = []
    if mode == "control":
        observed = SUPERVISED.EXPLORATION.run_explorer(
            root, request, config_path, explorer_path
        )
        if observed["exit_code"] != 0:
            raise ValueError("control Explorer failed; preserve arm, do not retry")
        code, routed = SUPERVISED.ROUTE.run_localization_unit(
            repo_root=root,
            plan=plan,
            packet_path=packet_path,
            request=request,
            explorer_report=observed["report"],
            state_path=root / ".agent/coordinator" / plan["feature_id"] / "state.json",
            run_refs={},
            config_path=config_path,
            coder_report_path=root / ".agent/coder-report.json",
            review_report_path=root / ".agent/review-report.json",
            authorized_sequence=0,
        )
    else:
        context = {
            "identity": {
                key: packet[key]
                for key in ("unit_id", "run_id", "attempt", "packet_revision")
            },
            "goal": packet["goal"],
            "navigation_targets": packet["edit_targets"],
            "question": "Generate a bounded proposal inside Primary ceilings with unchanged protected tests; no acceptance or scope expansion.",
        }
        write_once(root / ".agent/coordinator-context.json", context)
        client = SUPERVISED.MODEL.WORKER.LMStudioClient(
            config["lmstudio_base_url"],
            config["coordinator_model"],
            structured_output=False,
            context_length=config["coordinator_context_length"],
            max_tokens=config["coordinator_max_tokens"],
            timeout=config["coordinator_request_timeout_seconds"],
        )
        observer = RequestObserver(client, root / ".agent/coordinator-requests.jsonl")
        code, output = SUPERVISED.run_step(
            root=root,
            plan=plan,
            context=context,
            request=request,
            explorer={},
            run_refs={},
            config=config,
            config_path=config_path,
            authorized=True,
            expected_sequence=0,
            client=observer,
            manage_exploration=True,
        )
        routed = output.get("unit_result", output)
        coordinator_requests = observer.requests
        explorer_path = Path(output["archive"]) / "explorer-report.json"
    checks = {
        "pytest": STABILITY.run_command(
            root, [sys.executable, "-m", "pytest", test_path, "-q"], 90
        ),
        "ruff-format": STABILITY.run_command(
            root,
            [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"],
            90,
        ),
        "ruff-check": STABILITY.run_command(
            root, [sys.executable, "-m", "ruff", "check", "src", "tests"], 90
        ),
    }
    task_root = root / ".agent/tasks" / packet["task_id"]
    run_root = task_root / "runs" / packet["run_id"]
    explorer = read(explorer_path)
    refs = replay_refs(root, run_root, explorer)
    reviewer_id = routed["unit_result"]["review_attempts"][-1]["review_id"]
    measured = {
        "coordinator": usage(coordinator_requests),
        "explorer": usage(event_requests(root / explorer["diagnostic_log"])),
        "coder": usage(event_requests(run_root / "events.jsonl")),
        "reviewer": usage(
            event_requests(task_root / "reviews" / reviewer_id / "events.jsonl")
        ),
    }
    unchanged = ROUTE.runtime_manifest(source_config) == frozen["runtime"]
    result = {
        "workspace": str(root),
        "case": case_name,
        "mode": mode,
        "runtime_sha256": frozen["runtime"]["runtime_sha256"],
        "inputs_sha256": ROUTE._sha256_json(inputs),
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "wall_seconds_including_model_switches": time.monotonic() - clock,
        "model_usage": measured,
        "verified_explorer_source_refs": refs,
        "route_exit": code,
        "route": routed,
        "independent_checks": {
            key: {
                "exit_code": value.returncode,
                "output_tail": (value.stdout + value.stderr)[-800:],
            }
            for key, value in checks.items()
        },
        "runtime_unchanged": unchanged,
        "qualified_execution": code == 0
        and unchanged
        and routed.get("status") == "primary_review_required"
        and all(check.returncode == 0 for check in checks.values()),
        "primary_review": "required_not_inferred",
        "primary_packet_authoring_effort": "fixture_prebuilt_not_measured",
        "production_primary_work_savings": "not_inferred",
        "feature_accepted": False,
    }
    write_once(root / "measurement.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", type=Path, required=True)
    parser.add_argument(
        "--case",
        choices=("selection-random-seed", "mapping-message-sequence", "metadata-limit"),
        required=True,
    )
    parser.add_argument("--mode", choices=("control", "coordinator"), required=True)
    args = parser.parse_args()
    result = run(args.pair.resolve(), args.case, args.mode)
    print(json.dumps(result, indent=2))
    return 0 if result["qualified_execution"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
