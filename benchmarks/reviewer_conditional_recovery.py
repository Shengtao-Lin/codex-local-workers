"""Use known low instruction only for the sole output-cap recovery request."""

import argparse
import copy
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import reviewer_bounded_recovery as BASE

PROTOCOL = "conditional-known-low-output-recovery-v1"


def install(module):
    base = BASE.install(module)

    class ConditionalReviewer(base):
        def finalize(self, report):
            report["conditional_output_recovery"] = {
                "protocol": PROTOCOL,
                "recovery_requests_at_low": self.low_recovery_requests,
                "first_request_strength": "medium",
                "changes_on_recovery_only": True,
            }
            return super().finalize(report)

        def run(self):
            original = self.client.complete
            self.low_recovery_requests = 0

            def complete(messages):
                if messages[-1]["content"].endswith(BASE.NUDGE):
                    if messages[0]["content"].count("Reasoning strength: medium.") != 1:
                        raise module.ReviewError(
                            "conditional recovery requires exact medium origin"
                        )
                    messages = copy.deepcopy(messages)
                    messages[0]["content"] = messages[0]["content"].replace(
                        "Reasoning strength: medium.", "Reasoning strength: low."
                    )
                    self.low_recovery_requests += 1
                return original(messages)

            with patch.object(self.client, "complete", complete):
                return super().run()

    module.ReviewerRuntime = ConditionalReviewer
    return ConditionalReviewer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-dir", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location("conditional_reviewer_runtime", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    install(module)
    sys.argv = [str(path), *remaining]
    raise SystemExit(module.main())
