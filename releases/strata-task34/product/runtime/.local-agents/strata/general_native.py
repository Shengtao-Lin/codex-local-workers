"""Thin native transport: the shared host retains editing and verification."""

import json
import os
import queue
import subprocess
import threading
from pathlib import Path

from general_counter_host import consume_receipt, preflight, verify_provider_usage
from general_editing import EditTargetError
from general_prepare import W
from general_projection import model_view
from general_state import BudgetExhausted, StateError
from general_versions import observation_view
from investigation_delivery import assert_action, report_failure, reserve_request
from investigation_delivery import enabled as delivery_enabled
from strata_artifacts import save


class NativeProtocolError(ValueError):
    pass


def reserve_context_rebuild(host):
    """Task-wide, host-only progress gate; native restarts never replenish it."""
    rebuilds = host.ledger.state.get("context_rebuilds", 0)
    edit_revision = host.ledger.state["used"]["edits"]
    prior_revision = host.ledger.state.get("context_rebuild_edit_revision", -1)
    if rebuilds >= 2 or (rebuilds and edit_revision <= prior_revision):
        raise BudgetExhausted(
            "Post-rebuild context bound exhausted; no new effective edit or rebuild quota exhausted"
        )
    host.ledger.state["context_rebuilds"] = rebuilds + 1
    host.ledger.state["context_rebuild_edit_revision"] = edit_revision
    host.ledger.record("deterministic_context_rebuild", {"edit_revision": edit_revision})
    return {"kind": "native_context_rebuilt", "edit_revision": edit_revision}


def run_process(host, mode="live", actions=None, *, sequence=1, recovery_note=None):
    root = host.archive.run_root
    program = root / f"native-program-{sequence}.json"
    identity = host.identity()
    save(
        program,
        {
            "mode": mode,
            "profile": getattr(host, "native_profile", "strata-unit-v1"),
            "instance_id": host.config.get("strata_instance_id"),
            "actions": actions or [],
            "token_counter": bool(host.config.get("strata_token_counter")) and mode == "live",
            "version_reference_profile": host.config.get("strata_version_references"),
            "edit_profile": host.config.get("experimental_strata_edit_profile"),
            "native_tools_trial": host.config.get("experimental_native_tools_trial"),
            "capability_reporting": getattr(host, "native_profile", None) == "strata-readonly-v1"
            and host.config.get("experimental_strata_capabilities") is True,
            "report_delivery": getattr(host, "report_delivery_enabled", lambda: False)(),
            "report_binding": getattr(host, "report_binding_enabled", lambda: False)(),
            "review_delivery": getattr(host, "review_delivery_enabled", lambda: False)(),
            "failed_draft_diagnostic": host.config.get("experimental_strata_failed_draft_diagnostic") == "failed-draft-v1",
            "investigation_delivery": delivery_enabled(host.config),
            "compact_answer": host.config.get("experimental_strata_answer_transport")
            == "compact-v1",
        },
    )
    frames = queue.Queue()
    stderr = (root / f"native-stderr-{sequence}.log").open("x", encoding="utf-8")
    process = subprocess.Popen(
        [
            host.config["strata_node_path"],
            str(Path(__file__).with_name("strata_native_agent.mjs")),
            str(program),
        ],
        cwd=host.repo_root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=stderr,
        text=True,
        encoding="utf-8",
        env={
            **os.environ,
            "KIT_STRATA_HARNESS_ROOT": host.config["strata_harness_root"],
            "KIT_STRATA_BASE_URL": host.config["strata_base_url"],
        },
    )

    def reader():
        try:
            for line in process.stdout:
                if len(line) > 4_000_000:
                    break
                frames.put(json.loads(line))
        except (OSError, ValueError):
            pass
        finally:
            frames.put(None)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    def send(value):
        process.stdin.write(json.dumps({**value, "identity": identity}, ensure_ascii=False) + "\n")
        process.stdin.flush()

    rendered = {"edit": None, "check": None}

    def context(initial=False, *, snapshot=False):
        writable = (
            host.material["packet"]["scope"]["modify"] + host.material["packet"]["scope"]["create"]
        )
        value = model_view(
            host.context(initial=initial),
            observations=host.observations if snapshot else (),
            writable_paths=writable,
            preferred_evidence_paths=[
                *writable,
                *[p.split("::", 1)[0] for p in host.packet["focused_tests"]],
            ],
        )
        if not snapshot:
            edit = host.ledger.state["used"]["edits"]
            check = host.ledger.state.get("latest_check", {}).get("sha256")
            if not initial and rendered["edit"] == edit:
                value["work_state"].pop("current_diff", None)
                value["work_state"]["changes_unchanged"] = True
            if not initial and rendered["check"] == check:
                value.pop("validation", None)
                value["validation_unchanged"] = True
            rendered.update(edit=edit, check=check)
        if initial:
            value["task_material"] = {
                "task": value.pop("task"),
                "recovery_note": recovery_note,
            }
            if "primary_return" in value:
                value["task_material"]["primary_return"] = value.pop("primary_return")
        return value

    send({"kind": "host_context", "context": context(True)})
    settled = False
    action_sequence = 0
    try:
        while True:
            host.guard()
            try:
                value = frames.get(timeout=0.25)
            except queue.Empty:
                continue
            if value is None:
                raise NativeProtocolError("Native process ended before host settlement")
            if value.get("identity") != identity:
                raise StateError("Native task identity changed")
            kind = value.get("kind")
            if kind == "native_model_permit":
                body = value.get("body", {})
                if body.get("model") != "iq3_s" or body.get("max_tokens") != 12288:
                    raise StateError("Unexpected model/output route")
                if host.ledger.state["pending_model"] is not None:
                    raise StateError("Overlapping native requests")
                if mode == "live" and host.config.get("strata_token_counter"):
                    consume_receipt(host, body)
                reserve_request(host)
                number = host.ledger.state["used"]["model_requests"]
                host.ledger.state["pending_model"] = number
                host.ledger.record("native_request_reserved")
                save(root / f"native-model-request-{number}.json", value)
                send(
                    {
                        "kind": "native_model_permitted",
                        "remaining_ms": min(
                            600000, max(1, int(host.ledger.remaining_seconds() * 1000))
                        ),
                    }
                )
            elif kind == "native_http_started":
                if not host.ledger.state["pending_model"]:
                    raise StateError("HTTP without reservation")
                host.archive.mark_model_started()
                host.ledger.state["native_http_requests"] = (
                    host.ledger.state.get("native_http_requests", 0) + 1
                )
                host.ledger.record("native_http_started")
            elif kind == "native_model_result":
                number = host.ledger.state["pending_model"]
                if not number:
                    raise StateError("Duplicate/unreserved model response")
                save(root / f"native-model-response-{number}.json", value)
                if mode == "live" and host.config.get("strata_token_counter"):
                    verify_provider_usage(host, value)
                host.ledger.state["pending_model"] = None
                host.ledger.record("native_request_settled")
                if (
                    "residency" in str(value.get("error", "")).lower()
                    or value.get("status", 200) >= 400
                ):
                    raise StateError(
                        "Local infrastructure/residency error; no new dispatch: "
                        + str(value.get("error") or value.get("status"))
                    )
            elif kind == "native_context_count":
                if host.ledger.state["pending_model"] is not None:
                    raise StateError("Counter overlaps inference")
                send(preflight(host, value.get("body", {})))
            elif kind == "native_context_rebuild":
                send(reserve_context_rebuild(host))
            elif kind == "native_context_stop":
                if value.get("category") == "bound":
                    raise BudgetExhausted(str(value.get("reason", "Context bound exhausted")))
                raise StateError(str(value.get("reason", "Native conversation prefix changed")))
            elif kind == "native_argument_error":
                if (
                    not delivery_enabled(host.config)
                    or host.ledger.state["pending_model"] is not None
                ):
                    raise StateError("Unexpected native argument rejection")
                if (
                    value.get("action") not in {"read", "search", "report", "blocked"}
                    or not isinstance(value.get("errors"), list)
                    or not 1 <= len(value["errors"]) <= 16
                ):
                    raise StateError("Invalid native argument rejection metadata")
                host.guard()
                host.assert_bound()
                assert_action(host, value["action"])
                action_sequence += 1
                save(root / f"native-bridge-rejection-{sequence}-{action_sequence}.json", value)
                host.ledger.spend("tool_actions")
                host.ledger.spend("protocol_recoveries")
                host.ledger.record(
                    "native_bridge_rejected", {"action": value["action"], "errors": value["errors"]}
                )
                report_failure(host, value["action"], bridge=True)
                send(
                    {
                        "kind": "host_context",
                        "context": {
                            **context(),
                            "tool_result": {
                                "status": "rejected_no_write",
                                "reason": "Correct the listed field types and resubmit the complete tool input",
                                "field_errors": value["errors"],
                                "acceptance": False,
                            },
                        },
                        "snapshot": context(snapshot=True),
                    }
                )
            elif kind == "host_action":
                if host.ledger.state["pending_model"] is not None:
                    raise StateError("Tool before complete settled model response")
                assert_action(host, value["action"])
                action_sequence += 1
                save(root / f"native-action-{sequence}-{action_sequence}.json", value)
                try:
                    result = host.action(value["action"], value["arguments"])
                except (W.SafeEditError, ValueError, TypeError) as exc:
                    if isinstance(exc, (StateError, BudgetExhausted)):
                        raise
                    category = "edit_target" if isinstance(exc, EditTargetError) else "protocol"
                    host.ledger.state["last_rejection"] = {
                        "action": value["action"],
                        "category": category,
                        "reason": str(exc),
                        "details": getattr(exc, "details", {}),
                    }
                    host.ledger.record("tool_rejected", host.ledger.state["last_rejection"])
                    host.ledger.spend(
                        "edit_recoveries" if category == "edit_target" else "protocol_recoveries"
                    )
                    report_failure(host, value["action"], exc)
                    result = {
                        "observation": {
                            "status": "rejected_no_write",
                            "reason": str(exc),
                            "details": getattr(exc, "details", {}),
                        },
                        "context": host.context(),
                    }
                if host.completion:
                    send(
                        {
                            "kind": "host_terminal",
                            "status": host.completion,
                            "host_handoff_verified": host.completion == "ready_for_primary",
                        }
                    )
                else:
                    observation = result["observation"]
                    if host.versions:
                        observation = observation_view(
                            observation, host.versions.view(host.current_hashes())
                        )
                    send(
                        {
                            "kind": "host_context",
                            "context": {
                                **context(),
                                "tool_result": observation,
                            },
                            "snapshot": context(snapshot=True),
                        }
                    )
            elif kind == "driver_done":
                save(root / f"native-session-events-{sequence}.json", value)
                process.wait(timeout=min(10, max(0.1, host.ledger.remaining_seconds())))
                if not host.completion or process.returncode != 0:
                    raise NativeProtocolError("Native idle/exit without settled host handoff")
                settled = True
                return
            else:
                raise NativeProtocolError("Unknown native frame: " + str(kind))
    finally:
        if process.poll() is None:
            process.terminate()  # Only this invocation's owned Node frontend.
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if host.ledger.state["pending_model"] is not None:
            host.ledger.state["pending_model"] = None
            host.ledger.record(
                "aborted_request_discarded",
                {"charged": True, "frontend_exit": process.returncode},
            )
        for stream in (process.stdin, process.stdout, stderr):
            try:
                stream.close()
            except (OSError, ValueError):
                pass
        thread.join(timeout=1)
        save(
            root / f"native-settlement-{sequence}.json",
            {
                "settled": settled,
                "exit_code": process.returncode,
                "identity": identity,
                "seconds_remaining": host.ledger.remaining_seconds(),
            },
        )


def run_native(host, mode="live", actions=None):
    for sequence in range(1, 4):
        try:
            run_process(
                host,
                mode,
                actions,
                sequence=sequence,
                recovery_note=None
                if sequence == 1
                else "Previous native output/transport did not finish. Use current host state; no permission or resource reset.",
            )
            return
        except NativeProtocolError:
            if host.completion:
                raise
            host.ledger.spend("protocol_recoveries")
            if mode != "live":
                raise
            # A new frontend gets current host facts, not another free task.
            host.assert_bound()
    raise NativeProtocolError("Native recovery exhausted")
