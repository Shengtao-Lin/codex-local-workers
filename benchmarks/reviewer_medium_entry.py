"""Experimental formal Reviewer: only the reasoning directive changes to medium."""

import argparse
import importlib.util
import sys
from pathlib import Path

import reviewer_experiment_entry as ENTRY


def install(module):
    base = ENTRY.install(module)

    class MediumReviewer(base):
        def system_prompt(self):
            prompt = super().system_prompt()
            if prompt.count("Reasoning strength: low.") != 1:
                raise module.ReviewError(
                    "medium experiment requires exact frozen low directive"
                )
            return prompt.replace(
                "Reasoning strength: low.", "Reasoning strength: medium."
            )

        def validate_report(self, args):
            report = super().validate_report(args)
            report["reviewer_experiment"] = {
                "axis": "system reasoning directive only",
                "archived_coder_config_strength": "low",
                "effective_reviewer_directive": "medium",
                "production_promoted": False,
            }
            return report

    module.ReviewerRuntime = MediumReviewer
    return MediumReviewer


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-dir", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location("medium_reviewer_runtime", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    install(module)
    sys.argv = [str(path), *remaining]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
