"""Read-only Reviewer for the explicitly selected bounded-v1 profile."""

import argparse
import json
import sys
from pathlib import Path

from bounded import capture_fixture_support as F
from bounded import compatibility_profile as COMPAT
from bounded import reviewer_capture_entry as CAPTURE


def main():
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--inspect-only", action="store_true")
    options, remaining = parser.parse_known_args()
    required = argparse.ArgumentParser(allow_abbrev=False)
    required.add_argument("--request", type=Path, required=True)
    required.add_argument("--config", type=Path, required=True)
    required.add_argument("--report", type=Path, required=True)
    args = required.parse_args(remaining)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("bounded_execution_profile") != "bounded-v1":
        raise ValueError("Explicit bounded-v1 profile required")
    COMPAT.selected(config)
    path = Path(__file__).with_name("reviewer-runtime.py")
    module = F.load(path, "bounded_installed_reviewer")
    runtime_class = CAPTURE.install(
        module,
        F.POLICY_PATH,
        config["experimental_capture_policy_sha256"],
        forward_reasoning_effort=True,
    )
    runtime_class = COMPAT.reviewer_runtime(config, module, runtime_class)
    if options.inspect_only:
        runtime = runtime_class(
            Path.cwd(), json.loads(args.request.read_text(encoding="utf-8")), config, object()
        )
        # Authentication and evidence assembly do not dispatch a review. Calling
        # prepare() here would consume the run's single live-review allowance and
        # create a misleading review archive despite zero model calls.
        bundle = runtime.bundle()
        runtime._assert_inputs_current()
        module.RUN_STATE.write_json_once(
            args.report,
            {
                "mode": "offline-input-inspection",
                "model_calls": 0,
                "reviewer_dispatched": False,
                "reviewer_acceptance": False,
                "bundle": bundle,
                "provenance": runtime.observation_provenance,
            },
        )
        return 0
    sys.argv = [str(path), *remaining]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
