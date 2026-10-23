import copy
import json
import time
from . import reviewer_contract_status_probe as PREDICT
from . import reviewer_discriminating_status as DISCRIMINATING
from . import approved_provider as FACTS
from . import reviewer_observation_accounting as ACCOUNTING
from . import reviewer_semantic_entry as V1
from . import reviewer_semantic_policy as POLICY
from . import reviewer_semantic_transport as TRANSPORT
from . import approved_provider as TYPED

PROTOCOL = "contract-first-shared-budget-v1"


def prediction_tools(count):
    if type(count) is not int or not 1 <= count <= 8:
        raise ValueError("unsupported prediction count")
    tools = copy.deepcopy(DISCRIMINATING.TOOLS)
    items = tools[0]["function"]["parameters"]["properties"]["predictions"]
    items["minItems"] = items["maxItems"] = count
    items["items"]["properties"]["case_index"]["maximum"] = count - 1
    return tools


def parse_predictions(raw, count):
    action = json.loads(raw)
    if (
        not isinstance(action, dict)
        or set(action) != {"action", "arguments"}
        or action["action"] != "PREDICT_STATUS"
    ):
        raise ValueError("requires PREDICT_STATUS")
    args = action["arguments"]
    if (
        not isinstance(args, dict)
        or set(args) != {"predictions"}
        or (not isinstance(args["predictions"], list))
        or (len(args["predictions"]) != count)
    ):
        raise ValueError("one prediction required for every supplied case")
    for i, row in enumerate(args["predictions"]):
        if (
            not isinstance(row, dict)
            or set(row) != {"case_index", "status", "reason"}
            or type(row["case_index"]) is not int
            or (row["case_index"] != i)
            or (row["status"] not in {"requested", "succeeded", "failed", "unknown"})
            or (not isinstance(row["reason"], str))
            or (not row["reason"].strip())
            or (len(row["reason"]) > 400)
        ):
            raise ValueError("invalid prediction identity/status/reason")
    return args["predictions"]


def prediction_inputs(runtime, bundle, error):
    profiles = [
        p
        for p in bundle["approved_observations"]
        if p["profile_id"] == "collect-tools-json-observation-v1"
    ]
    if not profiles:
        return (None, [])
    if len(profiles) != 1 or len(runtime.packet["owned_contract_ids"]) != 1:
        raise error(
            "contract-first prototype requires one supported profile and one owned contract"
        )
    profile, sequences, actual = (profiles[0], [], [])
    for i, example in enumerate(profile["examples"]):
        parts = example["input"]["parts"]
        target = next((part["call_id"] for part in parts if part["type"] == "tool_call"), None)
        if target is None:
            raise error("supported projection requires an existing target call")
        outcome = example["outcome"]
        if outcome.get("kind") != "returned" or not isinstance(outcome.get("value"), list):
            raise error("unsupported actual observation outcome")
        selected = [call for call in outcome["value"] if call["call_id"] == target]
        if len(selected) != 1 or selected[0]["status"] not in {
            "requested",
            "succeeded",
            "failed",
            "unknown",
        }:
            raise error("prediction target missing, duplicate or invalid")
        sequences.append({"case_index": i, "input": example["input"], "target_call_id": target})
        actual.append(
            {
                "profile_id": profile["profile_id"],
                "case_index": i,
                "target_call_id": target,
                "contract_id": runtime.packet["owned_contract_ids"][0],
                "observed_status": selected[0]["status"],
            }
        )
    tests = []
    for path in runtime.focused_test_paths():
        _, resolved = runtime._assert_read_allowed(path)
        tests.append(resolved.read_text(encoding="utf-8-sig"))
    if sum((len(t) for t in tests)) > 16000:
        raise error("normative test context exceeds fixed bound")
    return (
        {
            "hard_contract": runtime.packet["required_behavior"],
            "dependency_declarations": bundle["dependencies"],
            "event_sequences": sequences,
            "approved_acceptance_tests": "\n\n".join(tests),
        },
        actual,
    )


def install(module, *, forward_reasoning_effort=False):
    if type(forward_reasoning_effort) is not bool:
        raise ValueError("Explicit reasoning forwarding must be boolean")
    base = POLICY.install(module)

    class ContractFirstReviewer(base):
        forward_effort = forward_reasoning_effort

        def bundle(self):
            result = super().bundle()
            observations, self.observation_provenance = FACTS.facts(self, module.ReviewError)
            result["approved_observations"], self.typed_input_provenance = TYPED.restore(
                self, observations, module.ReviewError
            )
            self.expected_observations = [
                (p["profile_id"], i)
                for p in result["approved_observations"]
                for i, _ in enumerate(p["examples"])
            ]
            return result

        def validate_report(self, args):
            report = super().validate_report(args)
            report["observation_assessments"] = ACCOUNTING.validate_accounting(
                self.pending_observation_assessments,
                self.expected_observations,
                report["contract_review"],
                module.ReviewError,
            )
            statuses = {r["obligation_id"]: r["status"] for r in report["contract_review"]}
            for claim in self.prediction_claims:
                if (
                    claim["model_claimed_required_status"] != claim["observed_status"]
                    and statuses[claim["contract_id"]] == "verified"
                ):
                    raise module.ReviewError(
                        "verified obligation contradicts prior explicit model contract prediction versus actual observation: "
                        + claim["profile_id"]
                        + "/"
                        + str(claim["case_index"])
                        + "; resolve the disagreement without treating implementation behavior as specification"
                    )
            report["model_contract_predictions"] = copy.deepcopy(self.prediction_claims)
            report["contract_first_protocol"] = PROTOCOL
            report["prediction_provenance"] = (
                "Untrusted same-model source-blind semantic claims, not gold, test execution, or a positive acceptance certificate. Host checks explicit claim consistency only."
            )
            report["approved_observation_provenance"] = self.observation_provenance
            report["typed_observation_input"] = {
                "protocol": TYPED.PROTOCOL,
                "provenance": self.typed_input_provenance,
            }
            return report

        def _request_phase_completion(self, messages, tools, stage):
            pending = copy.deepcopy(messages)
            while True:
                remaining = self.deadline - time.monotonic()
                if remaining <= 0 or self.actual_requests >= self.max_turns:
                    raise module.ReviewError(
                        "shared contract-first request/deadline budget exhausted"
                    )
                if self.protocol_errors + len(self.output_failures) >= self.max_protocol_errors:
                    raise module.ReviewError("shared contract-first error budget exhausted")
                self._assert_inputs_current()
                if self.fallback_active:
                    pending[0]["content"] = pending[0]["content"].replace(
                        "Reasoning strength: medium.", "Reasoning strength: low."
                    )
                self.client.native_tools = copy.deepcopy(tools)
                self.client.native_tool_choice = "required" if self.fallback_active else "auto"
                forward_effort = self.forward_effort
                if forward_effort:
                    if not hasattr(self.client, "reasoning_effort"):
                        raise module.ReviewError("Installed client cannot forward reasoning effort")
                    self.client.reasoning_effort = "low" if self.fallback_active else "medium"
                old_timeout = self.client.timeout
                self.client.timeout = min(old_timeout, remaining)
                self.actual_requests += 1
                self.request_profiles.append(
                    {
                        "request": self.actual_requests,
                        "stage": stage,
                        "fallback_active": self.fallback_active,
                        "tool_choice": self.client.native_tool_choice,
                    }
                )
                if forward_effort:
                    self.request_profiles[-1]["reasoning_effort"] = self.client.reasoning_effort
                try:
                    raw = self.client.complete(pending)
                    module.RUN_STATE.write_json_once(
                        self.review_root / f"phase-response-{self.actual_requests}.json",
                        {
                            "stage": stage,
                            "raw": raw,
                            "request_stats": self.client.last_request_stats,
                        },
                    )
                    self._assert_inputs_current()
                    return raw
                except module.WORKER.ModelRequestError as exc:
                    if exc.reason_code != "output_token_limit":
                        raise
                    failure = {
                        "request": self.actual_requests,
                        "stage": stage,
                        "reason_code": exc.reason_code,
                        "diagnostics": copy.deepcopy(exc.diagnostics),
                        "partial_action_executed": False,
                    }
                    self.output_failures.append(failure)
                    module.RUN_STATE.write_json_once(
                        self.review_root / f"output-limit-failure-{len(self.output_failures)}.json",
                        failure,
                    )
                    self._assert_inputs_current()
                    if len(self.output_failures) > 1:
                        raise
                    self.fallback_active = True
                    pending = copy.deepcopy(messages)
                    pending[-1]["content"] += (
                        "\nOUTPUT_LIMIT_RECOVERY\nNo partial action executed. Submit a concise "
                        + tools[0]["function"]["name"]
                        + " using unchanged evidence."
                    )
                finally:
                    self.client.timeout = old_timeout

        def reject(self, stage, exc):
            self.protocol_errors += 1
            self.event("contract_first_action_rejected", {"stage": stage, "error": str(exc)})
            if self.protocol_errors + len(self.output_failures) >= self.max_protocol_errors:
                raise module.ReviewError(
                    "shared contract-first protocol/error budget exhausted: " + str(exc)
                ) from exc

        def run(self):
            self.actual_requests, self.output_failures, self.request_profiles = (0, [], [])
            self.prediction_claims, self.fallback_active = ([], False)
            self.pending_observation_assessments = None
            original = (
                self.client.temperature,
                self.client.native_tools,
                self.client.native_tool_choice,
                self.client.timeout,
            )
            original_effort = getattr(self.client, "reasoning_effort", None)
            if original[0] != 1:
                raise module.ReviewError(
                    "contract-first experiment requires frozen temperature-one origin"
                )
            self.client.temperature = 0
            try:
                if self.config.get("reviewer_preload_model") is True:
                    self.client.ensure_loaded(
                        timeout_seconds=int(
                            self.config.get("reviewer_model_load_timeout_seconds", 360)
                        )
                    )
                self.client.preflight()
                self.client.probe_structured_output()
                self.prepare()
                self.deadline = time.monotonic() + self.invocation_timeout
                bundle = self.bundle()
                normative, actual = prediction_inputs(self, bundle, module.ReviewError)
                if normative is not None:
                    module.RUN_STATE.write_json_once(
                        self.review_root / "normative-input.json", normative
                    )
                    messages = [
                        {"role": "system", "content": PREDICT.SYSTEM},
                        {"role": "user", "content": json.dumps(normative, ensure_ascii=False)},
                    ]
                    while True:
                        raw = self._request_phase_completion(
                            messages, prediction_tools(len(actual)), "contract_prediction"
                        )
                        try:
                            predictions = parse_predictions(raw, len(actual))
                            self.prediction_claims = [
                                {
                                    **fact,
                                    "model_claimed_required_status": prediction["status"],
                                    "model_reason": prediction["reason"],
                                }
                                for fact, prediction in zip(actual, predictions, strict=True)
                            ]
                            break
                        except (ValueError, TypeError, KeyError) as exc:
                            self.reject("contract_prediction", exc)
                            messages[1]["content"] = (
                                json.dumps(normative, ensure_ascii=False)
                                + "\nPREDICTION_SHAPE_CORRECTION\n"
                                + str(exc)
                            )
                    bundle["model_contract_prediction_review"] = {
                        "provenance": "Untrusted model contract predictions before seeing implementation or actual outcomes; not gold or acceptance.",
                        "claims": self.prediction_claims,
                    }
                module.RUN_STATE.write_json_once(self.review_root / "semantic-input.json", bundle)
                messages = [
                    {"role": "system", "content": V1.SYSTEM},
                    {"role": "user", "content": json.dumps(bundle, ensure_ascii=False)},
                ]
                report_turns = 0
                while True:
                    raw = self._request_phase_completion(
                        messages, ACCOUNTING.TOOLS, "source_review"
                    )
                    report_turns += 1
                    try:
                        action = module.WORKER.parse_action(raw)
                        if action["action"] != "REPORT" or not isinstance(
                            action["arguments"], dict
                        ):
                            raise module.ReviewError("only REPORT is available in source review")
                        args = copy.deepcopy(action["arguments"])
                        self.pending_observation_assessments = args.pop(
                            "observation_assessments", None
                        )
                        report = self.validate_report(
                            TRANSPORT.assemble(self, args, module.ReviewError)
                        )
                        report.update(
                            {
                                "semantic_review_protocol": V1.PROTOCOL,
                                "semantic_verdicts": args,
                                "reviewer_model_calls": self.actual_requests,
                                "semantic_report_turns": report_turns,
                                "output_limit_failures": len(self.output_failures),
                                "recovered_from_output_limit": bool(self.output_failures),
                                "shared_error_budget_used": self.protocol_errors
                                + len(self.output_failures),
                                "request_profiles": copy.deepcopy(self.request_profiles),
                                "normative_model_calls": sum(
                                    (
                                        p["stage"] == "contract_prediction"
                                        for p in self.request_profiles
                                    )
                                ),
                            }
                        )
                        module.RUN_STATE.write_json_once(
                            self.review_root / "runtime-validation.json", self.validation
                        )
                        self._assert_inputs_current()
                        if time.monotonic() >= self.deadline:
                            raise module.ReviewError("shared contract-first deadline exhausted")
                        return self.finalize(report)
                    except (
                        module.ReviewError,
                        module.WORKER.WorkerError,
                        ValueError,
                        TypeError,
                        KeyError,
                    ) as exc:
                        self.reject("source_review", exc)
                        messages[1]["content"] = (
                            json.dumps(bundle, ensure_ascii=False)
                            + "\nREPORT_SHAPE_CORRECTION\n"
                            + str(exc)
                            + ". Submit a corrected REPORT with unchanged evidence."
                        )
            finally:
                (
                    self.client.temperature,
                    self.client.native_tools,
                    self.client.native_tool_choice,
                    self.client.timeout,
                ) = original
                if self.forward_effort:
                    self.client.reasoning_effort = original_effort
                if hasattr(self, "review_root") and self.review_root.exists():
                    module.RUN_STATE.write_json_once(
                        self.review_root / "contract-first-budget.json",
                        {
                            "actual_requests": self.actual_requests,
                            "request_profiles": self.request_profiles,
                            "protocol_errors": self.protocol_errors,
                            "output_limit_failures": len(self.output_failures),
                            "shared_error_budget_used": self.protocol_errors
                            + len(self.output_failures),
                            "max_requests": self.max_turns,
                            "max_errors": self.max_protocol_errors,
                            "invocation_timeout": self.invocation_timeout,
                        },
                    )

    module.ReviewerRuntime = ContractFirstReviewer
    return ContractFirstReviewer
