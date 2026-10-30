"""Guided semantic transfer on a fixed native-required diagnostic baseline."""

import argparse
import importlib.util
import sys
from pathlib import Path

from reviewer_required_tool_adapter import install as install_required
from reviewer_sampling_probe_adapter import install as install_probe

EXAMPLES = """
REVIEW METHOD EXAMPLES (analogy only, never evidence about the current repository):
1. A contract says to consume valid iterators and preserve ordinary records. Toy code
   `if hasattr(record, '__iter__'): return list(record)` is not enough: a record class
   with `__iter__ = None` has the attribute but is not iterable. A concrete counterexample
   defeats a broad 'preserves ordinary records' claim even when typical tests pass.
   Inspect the actual language/library protocol and branches before marking verified;
   attribute presence is not the same as protocol validity.
2. A contract forbids registering a second timer for a composite operation. Toy code
   has an outer timer of duration D, then stage A followed by another timer of duration D
   for stage B. Equal duration values do not make those registrations one timer. The
   outer timer may still cap total elapsed time: do not invent a longer-duration bug.
   A precise finding identifies the extra registration and the exact contract it breaks;
   preserve any enclosing guard when suggesting a bounded repair.
For each CURRENT obligation, test your proposed verification against a concrete normal,
error or boundary input from the actual source. A source citation identifies text,
not semantic proof. Report only source-grounded defects, not hypothetical issues copied
from these examples. Correct implementations must still pass; uncertainty escalates.
"""


def install(reviewer):
    original = reviewer.ReviewerRuntime.system_prompt

    def prompt(runtime):
        return original(runtime) + "\n" + EXAMPLES

    reviewer.ReviewerRuntime.system_prompt = prompt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "reasoning_examples_reviewer",
        args.snapshot / ".local-agents/reviewer-runtime.py",
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
