"""Default-off proposal loop, reusing the existing editor, checks and archive."""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), Path(__file__).with_name(name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INTERFACE = load("proposal-interface")
PROTOCOL = load("host-proposal-protocol")


def make_runtime_class(worker):
    class HostProposalRuntime(worker.WorkerRuntime):
        RUN_STATE = worker.RUN_STATE

        def __init__(self, repo_root, packet, config, client):
            if config.get("host_proposal_enabled") is not True:
                raise worker.WorkerError("Host proposals require trusted opt-in")
            if any(
                config.get(key)
                for key in ("coder_single_function_patch_repair", "coder_typed_action_arguments")
            ):
                raise worker.WorkerError("Host proposals cannot mix legacy action/patch modes")
            if config.get("coder_structured_output", True):
                raise worker.WorkerError("Qualified host proposals require plain JSON transport")
            super().__init__(repo_root, packet, config, client)
            if self.single_function is None:
                raise worker.WorkerError("Host proposals require a single existing function")
            if (
                self.packet["risk"]["unit"] == "high"
                and config.get("host_proposal_isolated_high_risk_fixture") is not True
            ):
                raise worker.WorkerError(
                    "High-risk host proposals are limited to explicit isolated fixtures"
                )
            if config.get("coordinator_enabled") is True:
                raise worker.WorkerError(
                    "Host proposal candidate is not qualified for Coordinator dispatch"
                )
            self.host_check_active = False
            self.host_requests = 0
            self.host_edits = 0
            self.host_receipts = []
            self.host_request_cap = min(6, self.max_turns, self.hard_max_turns)
            self.host_check_cap = min(3, int(self._limit("max_validation_runs", 3)))
            self.host_edit_cap = min(3, 1 + self.max_repairs)
            if min(self.host_request_cap, self.host_check_cap, self.host_edit_cap) < 1:
                raise worker.WorkerError("Host proposal budgets must be positive")

        def _contract_check(self, args, *, diagnostic=False):
            if self.host_check_active and diagnostic and not args:
                return None
            return super()._contract_check(args, diagnostic=diagnostic)

        def validate(self, args):
            # Includes recursive checks after trusted formatting. No extra budget.
            if not self.host_check_active:
                raise worker.WorkerError("Host checks are not model actions")
            if self.validation_count >= self.host_check_cap:
                raise worker.WorkerError("Host validation budget exhausted")
            return super().validate(args)

        def host_validate(self):
            self.host_check_active = True
            try:
                return self.validate({"phase": "check"})
            finally:
                self.host_check_active = False

        def proposal_context(self):
            # Retain the qualified representation, not the legacy action envelope.
            base = worker.SINGLE_FUNCTION.messages(self, [])
            original = json.loads(base[1]["content"])
            facts = dict(original["packet"])
            facts["target"] = original["target"]
            checks = self.validation.configured_checks if self.validation else []
            facts["validation_failure"] = {
                "diagnostics": [],
                "configured_checks": [
                    {
                        key: check.get(key)
                        for key in ("id", "status", "exit_code", "output", "diagnostic")
                    }
                    for check in checks
                    if check.get("status") != "passed"
                ],
                "focused_tests": (
                    self.validation.focused_tests.get("diagnostic") if self.validation else None
                ),
                "status": self.validation.status if self.validation else "not_run",
                "source_sha256": facts["target"]["sha256"],
            }
            facts["host_receipt"] = {
                "edit_revision": self.edit_revision,
                "recent": self.host_receipts[-2:],
                "remaining_requests": self.host_request_cap - self.host_requests,
                "remaining_checks": self.host_check_cap - self.validation_count,
                "remaining_patches": self.host_edit_cap - self.host_edits,
                "worker_assessment": None,
            }
            content = INTERFACE.literal_input(facts)
            if INTERFACE.restore_literal(content) != facts:
                raise worker.WorkerError("Proposal rendering changed facts")
            return [
                {"role": "system", "content": INTERFACE.WHOLE_PROMPT},
                {"role": "user", "content": content},
            ], facts["target"]

        def _failure_signature(self, report):
            if report.get("status") == PROTOCOL.PENDING:
                return None
            return super()._failure_signature(report)

        def finish_pending(self):
            if (
                not self.changed
                or self.edit_revision < 1
                or not self.validation
                or self.validation.status != "passed"
            ):
                raise worker.WorkerError("No current edited implementation passed checks")
            self._assert_validation_current()
            if self.validation.contract_check is not None or self.last_contract_check is not None:
                raise worker.WorkerError("Host checks cannot contain worker assessment")
            report = self.report(
                PROTOCOL.PENDING,
                [],
                None,
                ["Independent semantic review and Primary acceptance required."],
            )
            report.update(
                execution_protocol=PROTOCOL.PROTOCOL,
                worker_assessment=None,
                next_action_required="local_review",
            )
            report["runtime_facts"]["host_requests"] = self.host_requests
            report = self._complete_run(report)
            PROTOCOL.seal(self, report)
            return report

        def run(self):
            self.deadline = time.monotonic() + self.invocation_timeout
            try:
                self.write_lock.acquire()
                self._prepare_run_archive()
                # Bind read-scope dependencies/configuration before checks, not
                # merely the writable function and selected test entry points.
                for relative in self.read_roots:
                    base = self.repo_root / relative
                    paths = sorted(base.rglob("*")) if base.is_dir() else [base]
                    if len(paths) > 1000:
                        raise worker.WorkerError("Host read scope exceeds narrow adapter boundary")
                    for path in paths:
                        if path.is_file() and not any(
                            part in worker.EXCLUDED_PARTS
                            for part in path.relative_to(self.repo_root).parts
                        ):
                            name, _ = self._assert_read_allowed(
                                path.relative_to(self.repo_root).as_posix()
                            )
                            _, digest = self.editor.read_bytes(name)
                            self.observed_hashes[name] = digest
                # Establish fresh initial errors. This consumes one of the THREE
                # registered checks; green unedited baselines never qualify.
                self.host_validate()
                noops = 0
                while self.host_requests < self.host_request_cap:
                    self._remaining_seconds("proposal")
                    if (
                        self.host_edits >= self.host_edit_cap
                        or self.validation_count >= self.host_check_cap
                    ):
                        raise worker.WorkerError("Host patch/check budget exhausted")
                    messages, binding = self.proposal_context()
                    self.host_requests += 1
                    number = self.host_requests
                    self.RUN_STATE.write_json_once(
                        self.archive.run_root / f"proposal-request-{number}.json",
                        {"messages": messages, "binding": binding},
                    )
                    timeout = self.client.timeout
                    try:
                        self.client.timeout = min(
                            timeout, max(1, int(self._remaining_seconds("model request")))
                        )
                        self.archive.mark_model_started()
                        raw = self.client.complete(messages)
                        stats = getattr(self.client, "last_request_stats", None)
                        if isinstance(stats, dict):
                            self.archive.event("model_request", stats)
                        self._remaining_seconds("model request")
                    finally:
                        self.client.timeout = timeout
                    self.RUN_STATE.write_json_once(
                        self.archive.run_root / f"proposal-response-{number}.json",
                        {"raw": raw, "stats": getattr(self.client, "last_request_stats", None)},
                    )
                    try:
                        args = INTERFACE.terminal_boundary(INTERFACE.normalize_whole(raw, binding))
                        self.RUN_STATE.write_json_once(
                            self.archive.run_root / f"proposal-bound-{number}.json", args
                        )
                        if "blocked_reason" in args:
                            return self._complete_run(
                                self.report(
                                    "blocked",
                                    [],
                                    args["blocked_reason"],
                                    [],
                                    blocked={
                                        "reason_code": "proposal_blocked",
                                        "reason": args["blocked_reason"],
                                    },
                                )
                            )
                        if args["find"] == args["replace"]:
                            noops += 1
                            self.host_receipts.append(
                                {"status": "no_op", "source_sha256": binding["sha256"]}
                            )
                            if noops >= 2:
                                raise worker.WorkerError("Two unchanged proposals; no progress")
                            continue
                        self.safe_replace(args)
                        noops = 0
                        self.host_edits += 1
                    except (ValueError, SyntaxError, worker.SafeEditError) as exc:
                        self.host_receipts.append(
                            {
                                "status": "rejected",
                                "reason": str(exc),
                                "source_sha256": binding["sha256"],
                            }
                        )
                        self.archive.event("host_proposal_rejected", self.host_receipts[-1])
                        continue
                    result = self.host_validate()
                    self.host_receipts.append(
                        {"status": result["status"], "edit_revision": self.edit_revision}
                    )
                    if result["status"] == "passed":
                        return self.finish_pending()
                raise worker.WorkerError("Host request budget exhausted")
            except worker.InvocationInterrupted as exc:
                return self._complete_run(self._interrupted_report(exc))
            except KeyboardInterrupt:
                return self._complete_run(
                    self._interrupted_report(
                        worker.InvocationInterrupted(
                            "user_interrupt", "User interrupted the host proposal call"
                        )
                    )
                )
            except worker.ModelRequestError as exc:
                self.archive.event(
                    "model_request", getattr(self.client, "last_request_stats", {}) or {}
                )
                return self._complete_run(
                    self.report(
                        "failed",
                        [],
                        str(exc),
                        [],
                        infra_failure={
                            "reason_code": exc.reason_code,
                            "reason": str(exc),
                            "diagnostics": exc.diagnostics,
                        },
                    )
                )
            except worker.PolicyViolation as exc:
                return self._complete_run(self.report("policy_violation", [], str(exc), []))
            except (worker.WorkerError, worker.SafeEditError, ValueError, OSError) as exc:
                return self._complete_run(self.report("failed", [], str(exc), []))
            finally:
                self.close()

    return HostProposalRuntime
