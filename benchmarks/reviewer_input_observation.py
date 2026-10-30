"""Experiment-only, one-shot input observation before the existing final report.

Only the frozen event encoder is supported. Reuses the installed capture producer,
canonical input authentication and shared Reviewer request/error/deadline budget.
No acceptance policy changes, arbitrary code, shell, expected results or retries of
a completed semantic report. Not installed or selected by production configuration.
"""

import copy
import json
import subprocess
import sys
import time
from pathlib import Path

SYSTEM = (
    "You are selecting concrete inputs to resolve uncertainty in this code review. "
    "Read the same contract, source, tests and evidence as the final reviewer. "
    "Choose at most two informative calls to the approved function _sse(event, data), "
    "both arguments strings of at most 128 characters. Choose zero if no execution "
    "would help. Return SELECT_CASES only. Do not supply code, commands or expected "
    "answers. The host returns actual outcomes, not the specification or acceptance."
)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "SELECT_CASES",
            "description": "Select bounded data-only calls to the approved event encoder.",
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["cases"],
                "properties": {
                    "cases": {
                        "type": "array",
                        "maxItems": 2,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["args", "kwargs"],
                            "properties": {
                                "args": {
                                    "type": "array",
                                    "minItems": 2,
                                    "maxItems": 2,
                                    "items": {"type": "string", "maxLength": 128},
                                },
                                "kwargs": {
                                    "type": "object",
                                    "additionalProperties": False,
                                },
                            },
                        },
                    }
                },
            },
        },
    }
]
TARGET = {"path": "src/product/code.py", "module": "product.code", "symbol": "_sse"}


def parse(raw):
    action = json.loads(raw)
    if (
        not isinstance(action, dict)
        or set(action) != {"action", "arguments"}
        or action["action"] != "SELECT_CASES"
    ):
        raise ValueError("Only SELECT_CASES data is allowed")
    args = action["arguments"]
    if not isinstance(args, dict) or set(args) != {"cases"}:
        raise ValueError("Exactly cases is required")
    cases = args["cases"]
    if not isinstance(cases, list) or len(cases) > 2:
        raise ValueError("At most two cases")
    for case in cases:
        if (
            not isinstance(case, dict)
            or set(case) != {"args", "kwargs"}
            or not isinstance(case["args"], list)
            or len(case["args"]) != 2
            or any(not isinstance(v, str) or len(v) > 128 for v in case["args"])
            or case["kwargs"] != {}
        ):
            raise ValueError("Two bounded strings, no keyword arguments")
    if len({json.dumps(c, sort_keys=True) for c in cases}) != len(cases):
        raise ValueError("Duplicate observations are not useful")
    return cases


def observe(runtime, cases, module):
    from bounded import capture_fixture_support as F
    from bounded import reviewer_canonical_capture as AUTH

    runtime._assert_inputs_current()
    policy, before = AUTH.policy_material(runtime, *runtime._capture_spec)
    if policy["target"] != TARGET or policy["family"] != "json-call-model-dump-v1":
        raise module.ReviewError("Unsupported observation target/family")
    if not cases:
        return {
            "cases": [],
            "observations": [],
            "execution_seconds": 0,
            "source_manifest_sha256": before["sha256"],
        }
    remaining = runtime.deadline - time.monotonic()
    if remaining <= 0:
        raise module.ReviewError("No remaining time for observation")
    # The input values are the only policy difference; source, interpreter, helper,
    # producer and import restrictions remain authenticated by the existing code.
    selected = {**copy.deepcopy(policy), "cases": cases}
    relative = (
        (runtime.review_root / "selected-observation-policy.json")
        .relative_to(runtime.repo_root)
        .as_posix()
    )
    module.RUN_STATE.write_json_once(runtime.repo_root / relative, selected)
    argv = [
        policy["python"]["path"],
        "-B",
        str(runtime.repo_root / policy["producer_path"]),
        "--policy",
        relative,
    ]
    started = time.monotonic()
    result = subprocess.run(
        argv,
        cwd=runtime.repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=min(20, remaining),
        check=False,
    )
    receipt = {
        "argv": argv,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "seconds": time.monotonic() - started,
    }
    module.RUN_STATE.write_json_once(
        runtime.review_root / "observation-process.json", receipt
    )
    if result.returncode or len(result.stdout.encode()) > 16000:
        raise module.ReviewError("Bounded observation execution failed")
    value = json.loads(result.stdout)
    runtime._assert_inputs_current()
    _, after = AUTH.policy_material(runtime, *runtime._capture_spec)
    if before != after:
        raise module.ReviewError("Canonical source changed during observation")
    selected_manifest = F.P.manifest_for(runtime.repo_root, relative, selected)
    expected = {
        "task_id": policy["identity"]["task_id"],
        "run_id": policy["identity"]["run_id"],
        "producer_sha256": policy["producer_sha256"],
        "profile_sha256": F.P.digest(runtime.repo_root / relative),
        "source_manifest_sha256": selected_manifest["sha256"],
    }
    if value["bindings"] != expected:
        raise module.ReviewError("Observation identity/source/input binding mismatch")
    profiles = AUTH.validate_profiles(
        value["observations"], selected, selected_manifest
    )
    return {
        "cases": cases,
        "observations": profiles,
        "execution_seconds": receipt["seconds"],
        "source_manifest_sha256": before["sha256"],
        "authority": "Actual outcomes, not expected results or acceptance. Original contract and checks remain authoritative.",
    }


def install(module, base):
    class ObservationReviewer(base):
        def _request_phase_completion(self, messages, tools, stage):
            if stage != "source_review":
                return super()._request_phase_completion(messages, tools, stage)
            if not hasattr(self, "selected_observations"):
                selection = [
                    {"role": "system", "content": SYSTEM},
                    copy.deepcopy(messages[1]),
                ]
                while True:
                    raw = super()._request_phase_completion(
                        selection, TOOLS, "input_selection"
                    )
                    try:
                        cases = parse(raw)
                        break
                    except (ValueError, TypeError, KeyError) as exc:
                        self.reject("input_selection", exc)
                        selection[1]["content"] = (
                            messages[1]["content"] + "\nInvalid data shape: " + str(exc)
                        )
                module.RUN_STATE.write_json_once(
                    self.review_root / "selected-inputs.json", cases
                )
                self.selected_observations = observe(self, cases, module)
                module.RUN_STATE.write_json_once(
                    self.review_root / "selected-observations.json",
                    self.selected_observations,
                )
            enhanced = copy.deepcopy(messages)
            enhanced[1]["content"] += (
                "\nSUPPLEMENTARY_ACTUAL_INPUT_OBSERVATIONS\n"
                + json.dumps(self.selected_observations, ensure_ascii=False)
            )
            if not getattr(self, "observation_input_saved", False):
                module.RUN_STATE.write_json_once(
                    self.review_root / "observation-report-input.json", enhanced
                )
                self.observation_input_saved = True
            # The existing semantic validator, source citations, observation
            # accounting, immutable final report and Primary gate are unchanged.
            return super()._request_phase_completion(enhanced, tools, stage)

    module.ReviewerRuntime = ObservationReviewer
    return ObservationReviewer


def main():
    root = Path.cwd()
    sys.path.insert(0, str(root / ".local-agents"))
    from bounded import capture_fixture_support as F

    entry = F.load(
        root / ".local-agents/local-bounded-review.py", "observation_review_entry"
    )
    original = entry.COMPAT.reviewer_runtime
    entry.COMPAT.reviewer_runtime = lambda config, module, base: install(
        module, original(config, module, base)
    )
    return entry.main()


if __name__ == "__main__":
    raise SystemExit(main())
