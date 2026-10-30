"""Diagnostic entry: preserve exact Coder config while enabling Reviewer adapters."""

import argparse
import importlib.util
import sys
from pathlib import Path

import reviewer_evidence_state as OBS

SWITCHES = {"reviewer_compact_report", "reviewer_evidence_state"}


def install(module):
    original = module.ReviewerRuntime

    class ArchivedConfigReviewer(original):
        def __init__(self, repo_root, request, config, client):
            if any(config.get(key) is not True for key in SWITCHES):
                raise module.ReviewError(
                    "Both registered diagnostic adapters must be explicitly enabled"
                )
            # Only these new adapter flags are not Coder validation inputs. Every
            # other field goes unchanged to the original host hash verifier.
            trusted = {
                key: value for key, value in config.items() if key not in SWITCHES
            }
            super().__init__(repo_root, request, trusted, client)
            self.config = dict(config)

    module.ReviewerRuntime = ArchivedConfigReviewer
    return OBS.install(module)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-dir", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location("experiment_reviewer_runtime", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    install(module)
    sys.argv = [str(path), *remaining]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
