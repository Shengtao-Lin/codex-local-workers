"""One fixed decoding contrast; every other frozen Reviewer responsibility stays."""

import argparse
import importlib.util
import sys
from pathlib import Path

import reviewer_semantic_transport as BASE


def install(module):
    base = BASE.install(module)

    class GreedyReviewer(base):
        def validate_report(self, args):
            report = super().validate_report(args)
            report["reviewer_decoding_experiment"] = {
                "archived_temperature": self.config.get("reviewer_temperature"),
                "effective_temperature": self.client.temperature,
                "axis": "temperature 1 to 0 only",
                "production_promoted": False,
            }
            return report

        def run(self):
            if self.client.temperature != 1.0:
                raise module.ReviewError(
                    "greedy experiment requires frozen temperature-one origin"
                )
            previous = self.client.temperature
            self.client.temperature = 0.0
            try:
                return super().run()
            finally:
                self.client.temperature = previous

    module.ReviewerRuntime = GreedyReviewer
    return GreedyReviewer


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-dir", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location("semantic_greedy_runtime", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    install(module)
    sys.argv = [str(path), *remaining]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
