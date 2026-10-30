"""Trusted experiment wrapper: bind capture inputs, retain existing Coder loop."""

import argparse
import json
import sys
from pathlib import Path

import capture_fixture_support as F


def install(worker, policy_path, policy_sha):
    original = worker.WorkerRuntime

    class CaptureBoundWorker(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if policy_path != F.POLICY_PATH:
                raise worker.WorkerError("unregistered capture path")
            policy = json.loads(
                (self.repo_root / policy_path).read_text(encoding="utf-8")
            )
            if policy["identity"] != {
                k: self.packet[k] for k in ("task_id", "unit_id", "run_id")
            }:
                raise worker.WorkerError("capture identity differs from packet")
            F.bind_before_coder(self, policy, policy_sha)

        def validate(self, args):
            if self.validation_count >= 3:
                raise worker.WorkerError("Registered validation cap exhausted")
            return super().validate(args)

        def _begin_edit(self):
            if self.edit_revision >= 3:
                raise worker.WorkerError("Registered edit cap exhausted")
            return super()._begin_edit()

    worker.WorkerRuntime = CaptureBoundWorker
    return CaptureBoundWorker


def main():
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--capture-policy", required=True)
    parser.add_argument("--capture-policy-sha256", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "worker-runtime.py"
    worker = F.load(path, "capture_bounded_coder")
    install(worker, args.capture_policy, args.capture_policy_sha256)
    sys.argv = [str(path), *remaining]
    return worker.main()


if __name__ == "__main__":
    raise SystemExit(main())
