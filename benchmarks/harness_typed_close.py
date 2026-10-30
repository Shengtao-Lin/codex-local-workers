"""Do not confuse restored event identity with correct normative interpretation."""

import argparse
from pathlib import Path

import harness_reviewer_stage_close as C
import harness_typed_observations as H


def close(used):
    C.close(
        H,
        {
            "sample-17-candidate": (
                "output_cap_after_incomplete_report",
                "Three requests: first cap, recovered REPORT omits a required observation, then correction request returns to medium/auto and caps again. Preserve intermediate false pass and omission; complete gate never accepted it.",
            ),
            "sample-20-candidate": (
                "implementation_as_normative_reference",
                "False pass despite complete typed ToolResultPart(None) input. It explicitly reads requested status and says consistent because implementation skips None. Event-presence omission is therefore not the sole explanation; model substitutes implementation behavior for hard-contract requirements.",
            ),
        },
        used,
        "typed-observation-input",
        "Stop DTO/wording/sampling micro-tuning. Run one matched source-blind versus source-present contract-status diagnostic, same prompt/schema/inputs/limits, to separate contract interpretation capability from implementation anchoring. No production/handoff change or R4 credit.",
    )
    rows = []
    for row in H.B.read(H.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        paths = list(root.rglob("bounded-request-accounting.json"))
        assert len(paths) == 1
        rows.append({"id": row["id"], **H.B.read(paths[0])})
    H.B.save(
        H.BATCH / "recovery-audit.json",
        {
            "cells": rows,
            "requests": sum(r["actual_requests"] for r in rows),
            "event_presence_restoration_did_not_remove_false_pass": True,
            "recovery_profile_reverts_after_protocol_correction": True,
            "secondary_hypothesis": "Keeping a recovery profile might reduce completion failures, but cannot repair the already valid semantic false pass in sample20; do not promote a completion-only fix.",
            "new_coder_or_holdout_credit": False,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
