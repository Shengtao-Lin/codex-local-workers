"""Fixed empirical inputs and one within-budget output-limit recovery experiment."""

import argparse
import copy
import importlib.util
import sys
import time
from pathlib import Path
from unittest.mock import patch

import reviewer_fixed_observations as FACTS
import reviewer_semantic_policy as BASE

PROTOCOL = "fixed-facts-bounded-recovery-v1"
NUDGE = "\nOUTPUT_LIMIT_RECOVERY\nThe previous request reached its output limit before a valid action. No partial action was executed. Submit a concise REPORT using the unchanged contract and displayed evidence."


def install(module):
    base = BASE.install(module)

    class BoundedReviewer(base):
        def bundle(self):
            result = super().bundle()
            observations, self.observation_provenance = FACTS.facts(
                self, module.ReviewError
            )
            result["approved_observations"] = observations
            return result

        def finalize(self, report):
            report["semantic_report_turns"] = report["reviewer_model_calls"]
            report["reviewer_model_calls"] = self.actual_requests
            report["output_limit_failures"] = len(self.output_failures)
            report["first_request_output_capped"] = bool(
                self.output_failures and self.output_failures[0]["request"] == 1
            )
            report["recovered_from_output_limit"] = bool(self.output_failures)
            report["shared_error_budget_used"] = self.protocol_errors + len(
                self.output_failures
            )
            report["bounded_recovery_protocol"] = PROTOCOL
            report["approved_observation_provenance"] = self.observation_provenance
            return super().finalize(report)

        def run(self):
            self.actual_requests, self.output_failures = 0, []
            original_prepare, original_complete = self.prepare, self.client.complete

            def prepare():
                result = original_prepare()
                self.recovery_deadline = time.monotonic() + self.invocation_timeout
                return result

            def complete(messages):
                pending = messages
                recovery = False
                while True:
                    remaining = self.recovery_deadline - time.monotonic()
                    if remaining <= 0 or self.actual_requests >= self.max_turns:
                        raise module.ReviewError(
                            "shared recovery request/deadline budget exhausted"
                        )
                    if (
                        self.protocol_errors + len(self.output_failures)
                        >= self.max_protocol_errors
                    ):
                        raise module.ReviewError(
                            "shared recovery error budget exhausted"
                        )
                    self._assert_inputs_current()
                    old_timeout, choice = (
                        self.client.timeout,
                        self.client.native_tool_choice,
                    )
                    self.client.timeout = min(old_timeout, remaining)
                    if recovery:
                        self.client.native_tool_choice = "required"
                    self.actual_requests += 1
                    try:
                        result = original_complete(pending)
                        self._assert_inputs_current()
                        return result
                    except module.WORKER.ModelRequestError as exc:
                        if exc.reason_code != "output_token_limit":
                            raise
                        failure = {
                            "request": self.actual_requests,
                            "reason_code": exc.reason_code,
                            "diagnostics": copy.deepcopy(exc.diagnostics),
                            "partial_action_executed": False,
                        }
                        self.output_failures.append(failure)
                        module.RUN_STATE.write_json_once(
                            self.review_root
                            / f"output-limit-failure-{len(self.output_failures)}.json",
                            failure,
                        )
                        self._assert_inputs_current()
                        if len(self.output_failures) > 1:
                            raise
                        # No partial reasoning or rejected report is forwarded.
                        pending = copy.deepcopy(messages)
                        pending[-1]["content"] += NUDGE
                        recovery = True
                    finally:
                        self.client.timeout, self.client.native_tool_choice = (
                            old_timeout,
                            choice,
                        )

            try:
                with (
                    patch.object(self, "prepare", prepare),
                    patch.object(self.client, "complete", complete),
                ):
                    return super().run()
            finally:
                if hasattr(self, "review_root") and self.review_root.exists():
                    module.RUN_STATE.write_json_once(
                        self.review_root / "bounded-request-accounting.json",
                        {
                            "actual_requests": self.actual_requests,
                            "output_limit_failures": len(self.output_failures),
                            "protocol_errors": self.protocol_errors,
                            "shared_error_budget_used": self.protocol_errors
                            + len(self.output_failures),
                            "max_requests": self.max_turns,
                            "max_errors": self.max_protocol_errors,
                            "invocation_timeout": self.invocation_timeout,
                        },
                    )

    module.ReviewerRuntime = BoundedReviewer
    return BoundedReviewer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-dir", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location("bounded_reviewer_runtime", path)
    runtime_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runtime_module
    spec.loader.exec_module(runtime_module)
    install(runtime_module)
    sys.argv = [str(path), *remaining]
    raise SystemExit(runtime_module.main())
