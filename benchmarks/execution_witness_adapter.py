"""Expose protected-test execution witnesses without changing failure signatures."""

import argparse
import json
import sys
from pathlib import Path

from capability_fit import load_worker


def witness_map(root):
    result = {}
    for case in root.iter("testcase"):
        if case.find("failure") is None and case.find("error") is None:
            continue
        prop = case.find("./properties/property[@name='execution_witness_v1']")
        if prop is None or len(prop.get("value", "")) > 550:
            continue
        try:
            rows = json.loads(prop.get("value", ""))
        except ValueError:
            continue
        if not isinstance(rows, list) or not all(
            isinstance(r, dict) and isinstance(r.get("source"), str) for r in rows
        ):
            continue
        identity = f"{case.get('classname', '')}::{case.get('name', '')}"[:250]
        result[identity] = rows
    return result


def install(worker):
    old_failures = worker.WorkerRuntime._junit_failures
    old_compact = worker.WorkerRuntime._compact_repair_payload
    old_observation = worker.WorkerRuntime._validation_observation

    def failures(root):
        rows = old_failures(root)
        witnesses = witness_map(root)
        for row in rows:
            if row["test"] in witnesses:
                row["execution_witness"] = witnesses[row["test"]]
        return rows

    def evidence(runtime, validation):
        if validation is None or validation.status != "failed":
            return []
        result = []
        for failure in (validation.focused_tests.get("diagnostic") or {}).get(
            "failures", []
        )[:4]:
            rows = failure.get("execution_witness", [])
            allowed = []
            for row in rows:
                try:
                    runtime._assert_read_allowed(row["source"])
                except (worker.WorkerError, worker.SafeEditError, OSError):
                    continue
                allowed.append(row)
            if allowed:
                result.append(
                    {"test": failure["test"], "observed_events_not_diagnosis": allowed}
                )
        return result

    def compact(runtime, focus):
        result = old_compact(runtime, focus)
        result["execution_witnesses"] = evidence(runtime, runtime.validation)
        return result

    def observation(runtime, validation):
        result = old_observation(runtime, validation)
        result["execution_witnesses"] = evidence(runtime, validation)
        return result

    worker.WorkerRuntime._junit_failures = staticmethod(failures)
    worker.WorkerRuntime._compact_repair_payload = compact
    worker.WorkerRuntime._validation_observation = observation


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    worker = load_worker(args.snapshot)
    install(worker)
    sys.argv = ["worker-runtime.py", *remaining]
    raise SystemExit(worker.main())
