"""Experimental interactive Coder -> Primary route, production defaults intact."""

import json
import sys
from pathlib import Path

import bounded_evidence_support as S
import strata_model_entry as MODEL
from strata_subagent_rules import coder_arguments, select


def main():
    role, args = sys.argv[1], sys.argv[2:]
    config = S.read(Path(args[args.index("--config") + 1]))
    enabled = role == "unit" and config.get("experimental_strata_subagent") is True
    routed = False
    report_path = None
    if enabled:
        sys.path.insert(0, str(Path.cwd() / ".local-agents"))
        from bounded import compatibility_profile as compat

        original = compat.proposal_rules
        compat.proposal_rules = lambda c, base: select(original(c, base))
        report_path = Path(args[args.index("--report") + 1])
        args, routed = coder_arguments(args)
    MODEL.ENTRY.patch_worker = MODEL.patch
    MODEL.ENTRY.__file__ = __file__
    sys.argv = [__file__, role, *args]
    exit_code = MODEL.ENTRY.main()
    if routed:
        report = S.read(report_path)
        verified = False
        if report.get("status") == "validation_passed_pending_review":
            from bounded import capture_fixture_support as F

            gate = F.load(
                Path.cwd() / ".local-agents/local-unit.py", "subagent_host_gate"
            )
            gate.verify_handoff(Path.cwd(), report, config=config)
            verified = True
        S.save(
            Path.cwd() / ".agent/unit-summary.json",
            {
                "coder_status": report["status"],
                "reviewer_started": False,
                "reviewer_decision": "NOT_RUN_EXPERIMENT_PRIMARY_ROUTE",
                "automatic_coder_rework": False,
                "host_handoff_verified": verified,
                "experiment_only": True,
                "production_acceptance": False,
                "primary_acceptance": "PENDING",
            },
        )
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "host_handoff_verified": verified,
                    "primary_required": True,
                    "production_acceptance": False,
                }
            )
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
