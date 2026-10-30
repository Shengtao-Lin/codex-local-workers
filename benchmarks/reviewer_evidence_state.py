"""Experimental current evidence facts; no semantic inference or new actions."""

import argparse
import importlib.util
import sys
from pathlib import Path

import reviewer_compact_dto as DTO

PROTOCOL = "reviewer-evidence-state-v1"


def install(module):
    base = DTO.install(module)

    class EvidenceReviewer(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.config.get("reviewer_evidence_state") is not True:
                raise module.ReviewError("evidence-state experiment must be enabled")

        def evidence_state(self):
            self._assert_inputs_current()
            tests = self.focused_test_paths()
            sources = [
                p for p in self.diff_paths() if p.endswith(".py") and p not in tests
            ]
            return {
                "protocol": PROTOCOL,
                "snapshot": "current_after_this_observation",
                "source_read_requirement": {
                    "satisfied": not sources
                    or any(self.read_lines.get(p) for p in sources),
                    "candidate_paths": sources,
                },
                "test_read_requirement": {
                    "satisfied": not tests
                    or any(self.read_lines.get(p) for p in tests),
                    "candidate_paths": tests,
                },
                "missing_display_ranges": self.coverage_facts()["missing"],
                "required_reads_complete": self.required_reads_complete(),
                "semantic_understanding": "not_inferred_from_display",
            }

        def initial_payload(self):
            result = super().initial_payload()
            result["current_evidence_state"] = self.evidence_state()
            return result

        def read_file(self, args):
            result = super().read_file(args)
            relative, path = self._assert_read_allowed(result["path"])
            raw = path.read_bytes()
            sha = module.RUN_STATE.sha256_bytes(raw)
            if sha != self.observed_read_hashes[relative]:
                raise module.ReviewError(
                    "read source changed during observation: " + relative
                )
            total = len(raw.decode("utf-8-sig").splitlines())
            seen = self.read_lines.get(relative, set())
            missing = set(range(1, total + 1)) - seen
            result["file_extent"] = {
                "source_sha256": sha,
                "size_bytes": len(raw),
                "total_lines": total,
                "at_eof": total == 0
                or result.get("end_line") == total
                or args.get("start_line", 1) > total,
                "whole_file_displayed": not missing,
                "first_unread_line": min(missing) if missing else None,
                "unread_line_count": len(missing),
            }
            result["current_evidence_state"] = self.evidence_state()
            return result

        def search(self, args):
            result = super().search(args)
            result["current_evidence_state"] = self.evidence_state()
            return result

        def validate_report(self, args):
            result = super().validate_report(args)
            result["evidence_observation_protocol"] = PROTOCOL
            return result

    module.ReviewerRuntime = EvidenceReviewer
    return EvidenceReviewer


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-dir", required=True)
    args, remaining = parser.parse_known_args()
    path = Path(args.runtime_dir) / "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location("evidence_reviewer_runtime", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    install(module)
    sys.argv = [str(path), *remaining]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
