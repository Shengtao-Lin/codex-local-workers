import ast
import copy
import json
import subprocess
import time
from . import capture_fixture_support as F
from . import harness_protocol as P
from . import generic_evidence as G

BUDGET = {
    "requests": 12,
    "edits": 3,
    "initial_checks": 1,
    "post_edit_checks": 3,
    "format_preparations": 12,
    "protocol_recoveries": 2,
    "noop_stop": 2,
    "seconds": 900,
}


def recovery_budget(config):
    """Trusted experiment may reduce credits, never enlarge the frozen ceiling."""
    limits = dict(BUDGET)
    credits = config.get("experimental_recovery_credits")
    if credits is None:
        return limits
    if not isinstance(credits, dict) or set(credits) - {
        "requests",
        "edits",
        "post_edit_checks",
        "format_preparations",
        "protocol_recoveries",
        "seconds",
    }:
        raise ValueError("Invalid recovery credit fields")
    for key, value in credits.items():
        if type(value) is not int or not 0 <= value <= BUDGET[key]:
            raise ValueError("Recovery credits may only reduce integer ceilings")
        limits[key] = value
    if limits["post_edit_checks"] < limits["edits"]:
        raise ValueError("Every effective edit needs a complete post-edit check")
    if not limits["requests"] or not limits["edits"] or (not limits["seconds"]):
        raise ValueError("No remaining recovery opportunity")
    return limits


def noop_recovery_allowed(runtime):
    """One explicit codec change may use remaining credits, never restore them."""
    return (
        runtime.noops >= 2
        and not runtime.ledger.get("proposal_profile_switches", 0)
        and runtime.validation.status == "failed"
        and runtime.validation.focused_tests.get("inputs_unchanged") is True
        and runtime.ledger["requests"] < runtime.budget["requests"]
        and runtime.ledger["edits"] < runtime.budget["edits"]
        and runtime.ledger["post_edit_checks"] < runtime.budget["post_edit_checks"]
        and time.monotonic() < runtime.deadline
        and runtime._validation_facts() == runtime.validation.focused_tests.get("input_facts")
    )


def make_runtime(worker, *, proposal_rules=P):
    P = proposal_rules
    interface = F.load(
        F.Path(worker.__file__).with_name("proposal-interface.py"), "consolidated_interface"
    )
    protocol = F.load(
        F.Path(worker.__file__).with_name("host-proposal-protocol.py"), "consolidated_protocol"
    )

    class Consolidated(worker.WorkerRuntime):
        RUN_STATE = worker.RUN_STATE

        def __init__(self, root, packet, config, client):
            super().__init__(root, packet, config, client)
            if (
                config.get("experimental_consolidated_harness") is not True
                or config.get("host_proposal_enabled") is not True
            ):
                raise worker.WorkerError("Explicit experimental opt-in required")
            if self.single_function is None or config.get("coordinator_enabled"):
                raise worker.WorkerError("One isolated behavior unit, no Coordinator")
            if (self.max_turns, self.hard_max_turns, self.invocation_timeout) != (
                12,
                12,
                900,
            ) or self._limit("max_validation_runs", 0) != 4:
                raise worker.WorkerError("Exact registered budget required")
            if config.get("autoformat_on_ruff_failure") is not False:
                raise worker.WorkerError("Formatting must be explicit pre-application preparation")
            self.budget = recovery_budget(config)
            self.allowed = {tuple(v) for v in config.get("experimental_approved_imports", [])}
            if not self.allowed <= P.IMPORT_CEILING:
                raise worker.PolicyViolation("Import authority exceeds ceiling")
            self.host_check_active = False
            self.feedback = None
            self.execution_memory = P.memory_factory() if hasattr(P, "memory_factory") else None
            self.extra_checks = []
            self.extra_check_input_facts = None
            self.noops = 0
            self.ledger = {
                k: 0
                for k in (
                    "requests",
                    "model_requests",
                    "scripted_requests",
                    "edits",
                    "initial_checks",
                    "post_edit_checks",
                    "format_preparations",
                    "protocol_recoveries",
                    "noops",
                    "envelope_normalizations",
                    "supplemental_commands",
                )
            }
            self.self_audit = getattr(P, "SELF_AUDIT", False)
            if self.self_audit:
                self.ledger.update(audit_requests=0, audit_unchanged=0)
            self.evidence_window = (
                P.evidence_factory(
                    self, policy_error=worker.PolicyViolation, progress_error=worker.WorkerError
                )
                if hasattr(P, "evidence_factory")
                else None
            )
            self.generic_evidence = G.selected(config)
            if self.generic_evidence:
                G.bind_before_coder(self)
            else:
                policy_path = F.POLICY_PATH
                policy = json.loads((self.repo_root / policy_path).read_text(encoding="utf-8"))
                sha = config["experimental_capture_policy_sha256"]
                if policy["identity"] != {
                    k: self.packet[k] for k in ("task_id", "unit_id", "run_id")
                }:
                    raise worker.PolicyViolation("Capture identity differs")
                F.bind_before_coder(self, policy, sha)

        def _contract_check(self, args, *, diagnostic=False):
            if self.host_check_active and diagnostic and (not args):
                return None
            return super()._contract_check(args, diagnostic=diagnostic)

        def _failure_signature(self, report):
            if report.get("status") == protocol.PENDING:
                return None
            return super()._failure_signature(report)

        def check(self):
            if self.generic_evidence:
                try:
                    G.policy_for(self)
                except ValueError as exc:
                    raise worker.PolicyViolation(str(exc)) from exc
            kind = "post_edit_checks" if self.ledger["edits"] else "initial_checks"
            if self.ledger[kind] >= self.budget[kind]:
                raise worker.WorkerError("Check budget exhausted")
            self.ledger[kind] += 1
            self.host_check_active = True
            try:
                result = self.validate({"phase": "check"})
            finally:
                self.host_check_active = False
            if self.generic_evidence:
                try:
                    G.policy_for(self)
                except ValueError as exc:
                    raise worker.PolicyViolation(str(exc)) from exc
            self.extra_checks = []
            self.extra_check_input_facts = None
            if self.validation.status != "failed":
                return result
            junit = self.validation.focused_tests.get("junit") or {}
            if not junit.get("available") or junit.get("executed", 0) < 1:
                return result
            commands = self.validation_profile().get("commands", [])
            required_ids = (
                G.CHECK_IDS
                if self.generic_evidence
                else {"ruff-format", "ruff-check", "pyright", "actual-observations"}
            )
            if len(commands) != len(required_ids) or {c["id"] for c in commands} != required_ids:
                raise worker.PolicyViolation("Exact configured profile required")
            completed = {c["id"] for c in self.validation.configured_checks or []}
            before = self._validation_facts()
            for command in commands:
                if command["id"] in completed:
                    continue
                if self.ledger["supplemental_commands"] >= 16:
                    raise worker.WorkerError("Supplemental command cap exhausted")
                self.ledger["supplemental_commands"] += 1
                argv = [
                    s.replace("{python}", str(self.python_path())).replace(
                        "{repo}", str(self.repo_root)
                    )
                    for s in command["argv"]
                ]
                observed = self._run_command(argv)
                if self._validation_facts() != before:
                    raise worker.PolicyViolation("Supplemental check input changed")
                self.extra_checks.append({"id": command["id"], **observed})
            self.extra_check_input_facts = copy.deepcopy(before)
            self.RUN_STATE.write_json_once(
                self.archive.run_root / f"diagnostics-{self.validation_count}.json",
                {
                    "input_facts": before,
                    "additional_checks": self.extra_checks,
                    "acceptance_credit": False,
                },
            )
            return result

        def context(self):
            spec = self.single_function
            raw, sha = self.editor.read_bytes(spec["path"])
            source = raw.decode("utf-8-sig").replace("\r\n", "\n")
            P.shape(source, spec["symbol"], self.allowed)
            self.observed_hashes[spec["path"]] = sha
            self.read_coverage.setdefault((spec["path"], sha), set()).update(
                range(1, len(source.splitlines()) + 1)
            )
            binding = {
                **spec,
                "sha256": sha,
                "start_line": 1,
                "end_line": len(source.splitlines()),
                "source": source,
            }
            fields = (
                "goal",
                "required_behavior",
                "required_order",
                "forbidden_orderings",
                "acceptance_criteria",
                "acceptance_scenarios",
                "scope",
                "focused_tests",
                "validation_profile",
                "owned_contract_ids",
                "dependencies",
            )
            facts = {k: copy.deepcopy(self.packet[k]) for k in fields}
            if self.packet.get("implementation_guidance"):
                facts["implementation_guidance"] = copy.deepcopy(
                    self.packet["implementation_guidance"]
                )
                facts["implementation_guidance_authority"] = (
                    "Advisory untrusted research notes, not a hard requirement or verified implementation. Follow the hard contract and actual evidence."
                )
            if self.packet.get("review_feedback"):
                facts["review_feedback"] = copy.deepcopy(self.packet["review_feedback"])
                if self.config.get("experimental_rework_feedback_projection") == "location-only":
                    projected = (self.packet.get("_experimental_reviewer_recovery") or {}).get(
                        "locator_feedback"
                    )
                    if not projected:
                        raise worker.WorkerError("Authenticated feedback projection missing")
                    facts["review_feedback"] = copy.deepcopy(projected)
                facts["review_feedback_authority"] = (
                    "Reconcile inherited observations with the unchanged hard contract and actual evidence; feedback grants no extra permissions."
                )
            if self.packet.get("_inheritance"):
                facts["inherited_execution"] = copy.deepcopy(self.packet["_inheritance"])
                facts["inherited_execution_authority"] = (
                    "Immutable parent history, not reusable validation. The current source and current complete checks remain authoritative."
                )
            facts.update(
                target=binding,
                repair_unit={
                    "kind": "function_and_approved_imports",
                    "symbol": spec["symbol"],
                    "approved_imports": [list(v) for v in sorted(self.allowed)],
                },
                validation_failure={
                    "diagnostics": [],
                    "configured_checks": [
                        c
                        for c in self.validation.configured_checks or []
                        if c["status"] != "passed"
                    ],
                    "focused_tests": self.validation.focused_tests.get("diagnostic"),
                    "status": self.validation.status,
                    "source_sha256": sha,
                },
                supplemental_host_diagnostics={
                    "checks": self.extra_checks,
                    "source_sha256": sha,
                    "acceptance_credit": False,
                },
                protocol_feedback=self.feedback,
                resource_ledger=dict(self.ledger),
            )
            if hasattr(P, "diagnostics"):
                facts["validation_failure"]["diagnostics"] = P.diagnostics(self, binding)
            if self.execution_memory is not None:
                facts["execution_memory"] = self.execution_memory.observe(
                    binding, self.validation, self.feedback, self.ledger
                )
            if self.evidence_window is not None:
                facts.update(self.evidence_window.state())
            if hasattr(P, "failure_evidence"):
                facts["failed_test_sources"] = P.failure_evidence(self, binding)
            return (
                [
                    {"role": "system", "content": P.PROMPT},
                    {
                        "role": "user",
                        "content": getattr(P, "render", interface.literal_input)(facts),
                    },
                ],
                binding,
            )

        def prepare(self, source, binding):
            if hasattr(P, "materialize"):
                source = P.materialize(binding["source"], source, binding["symbol"], self.allowed)
            P.guard(binding["source"], source, binding["symbol"], self.allowed)
            if self.ledger["format_preparations"] >= self.budget["format_preparations"]:
                raise worker.WorkerError("Preparation budget exhausted")
            self.ledger["format_preparations"] += 1
            before = self._validation_facts()
            started = time.monotonic()
            argv = [
                str(self.python_path()),
                "-B",
                "-m",
                "ruff",
                "format",
                "--stdin-filename",
                binding["path"],
                "-",
            ]
            result = subprocess.run(
                argv,
                input=source,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
                timeout=min(
                    self.command_timeout, max(1, int(self._remaining_seconds("format preparation")))
                ),
            )
            if result.returncode != 0:
                raise ValueError("Trusted format preparation failed: " + result.stderr[:500])
            formatted = result.stdout
            if ast.dump(ast.parse(source)) != ast.dump(ast.parse(formatted)):
                raise worker.PolicyViolation("Formatter changed proposal AST")
            if self._validation_facts() != before:
                raise worker.PolicyViolation("Inputs changed during preparation")
            P.guard(binding["source"], formatted, binding["symbol"], self.allowed)
            self.RUN_STATE.write_json_once(
                self.archive.run_root / f"preparation-{self.ledger['requests']}.json",
                {
                    "argv": argv,
                    "seconds": round(time.monotonic() - started, 3),
                    "stderr": result.stderr,
                    "source_sha256": binding["sha256"],
                    "ast_unchanged": True,
                    "candidate": formatted,
                    "acceptance_credit": False,
                },
            )
            return formatted

        def finish(self, status, reason=None):
            report = self.report(status, [], reason, [])
            report["consolidated_harness"] = {
                "budget": self.budget,
                "actual": dict(self.ledger),
                "seconds": round(time.monotonic() - self.started, 3),
            }
            if status == protocol.PENDING:
                self._assert_validation_current()
                if (
                    not self.changed
                    or self.validation.status != "passed"
                    or self.validation.contract_check is not None
                ):
                    raise worker.WorkerError("No current implementation validation")
                report.update(
                    execution_protocol=protocol.PROTOCOL,
                    worker_assessment=None,
                    next_action_required="local_review",
                )
            report = self._complete_run(report)
            if status == protocol.PENDING:
                protocol.seal(self, report)
            return report

        def run(self):
            self.started = time.monotonic()
            self.deadline = self.started + self.budget["seconds"]
            try:
                self.write_lock.acquire()
                self._prepare_run_archive()
                self.check()
                while self.ledger["requests"] < self.budget["requests"]:
                    auditing = (
                        self.self_audit
                        and self.ledger["edits"] > 0
                        and (self.validation.status == "passed")
                    )
                    if self.ledger["edits"] >= self.budget["edits"] and (not auditing):
                        return self.finish("failed", "Effective edit budget exhausted")
                    if auditing:
                        self._assert_validation_current()
                    messages, binding = self.context()
                    self.ledger["requests"] += 1
                    if auditing:
                        self.ledger["audit_requests"] += 1
                    n = self.ledger["requests"]
                    self.RUN_STATE.write_json_once(
                        self.archive.run_root / f"proposal-request-{n}.json",
                        {"messages": messages, "binding": binding, "schema": P.SCHEMA},
                    )
                    scripted = getattr(self.client, "offline", False)
                    self.ledger["scripted_requests" if scripted else "model_requests"] += 1
                    if not scripted:
                        self.archive.mark_model_started()
                    try:
                        timeout = self.client.timeout
                        self.client.timeout = min(
                            timeout, max(1, int(self._remaining_seconds("proposal")))
                        )
                        try:
                            raw = self.client.complete(messages)
                        finally:
                            self.client.timeout = timeout
                        self.RUN_STATE.write_json_once(
                            self.archive.run_root / f"proposal-response-{n}.json",
                            {"raw": raw, "stats": getattr(self.client, "last_request_stats", None)},
                        )
                        value, removed = P.decode(raw)
                        if self.evidence_window is not None and set(value) <= {"read", "search"}:
                            self.evidence_window.perform(value)
                            continue
                        if removed:
                            self.ledger["envelope_normalizations"] += 1
                            self.archive.event("inactive_null_normalized", {"keys": removed})
                        if "blocked_reason" in value:
                            return self.finish("blocked", value["blocked_reason"])
                        prepared = self.prepare(value["replacement"], binding)
                    except worker.ModelRequestError as exc:
                        self.RUN_STATE.write_json_once(
                            self.archive.run_root / f"proposal-response-{n}.json",
                            {"error": exc.reason_code, "diagnostics": exc.diagnostics},
                        )
                        if exc.reason_code != "output_token_limit":
                            report = self.report(
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
                            return self._complete_run(report)
                        if self.ledger["protocol_recoveries"] >= self.budget["protocol_recoveries"]:
                            return self.finish("failed", "Protocol recovery budget exhausted")
                        self.ledger["protocol_recoveries"] += 1
                        self.feedback = "Output truncated; no partial proposal was applied."
                        continue
                    except (ValueError, SyntaxError) as exc:
                        if self.ledger["protocol_recoveries"] >= self.budget["protocol_recoveries"]:
                            return self.finish("failed", "Protocol recovery budget exhausted")
                        self.ledger["protocol_recoveries"] += 1
                        self.feedback = str(exc)[:500]
                        continue
                    self.feedback = None
                    if prepared == binding["source"]:
                        if auditing:
                            self.ledger["audit_unchanged"] += 1
                            return self.finish(protocol.PENDING)
                        self.noops += 1
                        self.ledger["noops"] += 1
                        self.feedback = "no_op: prepared proposal is identical to current source; validation remains failed."
                        if self.noops >= 2:
                            recover = getattr(P, "recover_noop", None)
                            if (
                                callable(recover)
                                and noop_recovery_allowed(self)
                                and recover(self.client) is True
                            ):
                                self.ledger["proposal_profile_switches"] = 1
                                self.noops = 0
                                self.archive.event(
                                    "proposal_profile_switched",
                                    {
                                        "after_request": n,
                                        "source_sha256": binding["sha256"],
                                        "profile": getattr(
                                            P, "RECOVERY_PROFILE", "explicit-noop-recovery"
                                        ),
                                        "budget_reset": False,
                                    },
                                )
                                continue
                            return self.finish("failed", "Two unchanged prepared proposals")
                        continue
                    if self.ledger["edits"] >= self.budget["edits"]:
                        return self.finish(
                            "failed", "Audit requested change beyond effective edit budget"
                        )
                    spec = self.single_function
                    self.single_function = None
                    try:
                        self.safe_replace(
                            {
                                "path": binding["path"],
                                "expected_sha256": binding["sha256"],
                                "find": binding["source"],
                                "replace": prepared,
                            }
                        )
                    finally:
                        self.single_function = spec
                    self.ledger["edits"] += 1
                    self.noops = 0
                    if self.check()["status"] == "passed" and (not self.self_audit):
                        return self.finish(protocol.PENDING)
                return self.finish("failed", "Request budget exhausted")
            except worker.PolicyViolation as exc:
                return self.finish("policy_violation", str(exc))
            except worker.InvocationInterrupted as exc:
                return self._complete_run(self._interrupted_report(exc))
            except (
                worker.WorkerError,
                worker.SafeEditError,
                OSError,
                subprocess.TimeoutExpired,
            ) as exc:
                return self.finish("failed", str(exc))
            finally:
                self.close()

    return Consolidated
