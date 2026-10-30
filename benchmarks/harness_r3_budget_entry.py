"""Registered budget-only observer for the frozen R0 baseline entry."""

import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "bounded_frozen_worker", Path(__file__).with_name("worker-runtime.py")
)
worker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = worker
spec.loader.exec_module(worker)
Original = worker.WorkerRuntime


class BoundedFrozenWorker(Original):
    def validate(self, args):
        if self.validation_count >= 3:
            raise worker.WorkerError("Registered R3 validation cap exhausted")
        return super().validate(args)

    def _begin_edit(self):
        if self.edit_revision >= 3:
            raise worker.WorkerError("Registered R3 edit cap exhausted")
        return super()._begin_edit()


worker.WorkerRuntime = BoundedFrozenWorker
if __name__ == "__main__":
    raise SystemExit(worker.main())
