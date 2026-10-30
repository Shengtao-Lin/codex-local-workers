"""Restore canonical issue definitions lost when building the task-local brief."""

import argparse
import importlib.util
import sys
from pathlib import Path

import reviewer_semantic_greedy as BASE

MAPPING = {
    "satisfied": "consistent",
    "implementation_defect": "implementation_defect",
    "required_test_gap": "required_test_gap",
    "contract_conflict": "contract_conflict",
    "uncertain": "insufficient_evidence",
}
PROTOCOL = "reviewer-canonical-policy-v1"


def definitions(prompt, error):
    original = {}
    for line in prompt.splitlines():
        if line.startswith("- ") and ": " in line:
            key, value = line[2:].split(": ", 1)
            original[key] = value
    if not (set(MAPPING.values()) | {"optional_test_gap"}) <= set(original):
        raise error("canonical Reviewer issue definitions missing")
    result = {
        target: original[source].replace(
            "unverified_claims", "uncertainties with contract_id=null"
        )
        for target, source in MAPPING.items()
    }
    result["satisfied"] += " Optional advice: " + original["optional_test_gap"].replace(
        "unverified_claims", "uncertainties with contract_id=null"
    )
    return result


def install(module):
    base = BASE.install(module)

    class PolicyReviewer(base):
        def bundle(self):
            result = super().bundle()
            result["verdict_definitions"] = definitions(
                self.system_prompt(), module.ReviewError
            )
            return result

        def validate_report(self, args):
            report = super().validate_report(args)
            report["semantic_policy_protocol"] = PROTOCOL
            report["semantic_policy_provenance"] = (
                "Canonical definitions from this frozen original Reviewer system_prompt; enum names/uncertainty field mechanically adapted, no case-specific policy."
            )
            return report

    module.ReviewerRuntime = PolicyReviewer
    return PolicyReviewer


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-dir", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location("semantic_policy_runtime", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    install(module)
    sys.argv = [str(path), *remaining]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
