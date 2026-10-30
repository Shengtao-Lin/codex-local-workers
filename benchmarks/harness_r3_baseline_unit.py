"""One Reviewer invocation, without changing the frozen baseline review protocol."""

import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "r3_baseline_unit", Path(__file__).with_name("local-unit.py")
)
unit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = unit
spec.loader.exec_module(unit)
unit._retryable_reviewer_startup_failure = lambda report: False
if __name__ == "__main__":
    raise SystemExit(unit.main())
