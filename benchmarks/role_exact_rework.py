"""One inherited repair per exposed unit using Primary-reviewed Reviewer findings."""

import json

from capability_fit import WORK, write


def prepare():
    for case in ("window-groups", "timeout-roundtrip"):
        for repetition in (1, 2):
            root = WORK / "roleq-six-1/runs/v1/roleq1" / f"{case}-round-{repetition}"
            parent = json.loads(
                (root / ".agent/boundary-a2.json").read_text(encoding="utf-8")
            )
            child = {
                key: parent[key] for key in ("schema_version", "task_id", "unit_id")
            }
            text = "Primary reviewed Reviewer exact-type-not-enforced finding: exact integer type is expressed by type(value) is int, not isinstance(value,int) and not bool-only rejection. Change the current guard to enforce this exact identity and preserve all valid behavior."
            if case == "timeout-roundtrip":
                text += " Preserve the current separate absent-key default and explicit None rejection, zero and fractional seconds."
            child.update(
                run_id=parent["run_id"].replace("-a2", "-a3"),
                parent_run_id=parent["run_id"],
                preserve_contract=True,
                attempt=3,
                plan_revision=3,
                packet_revision=3,
                review_feedback=[
                    {
                        "finding_id": "primary-reviewed-exact-type",
                        "contract_id": "qual-unit",
                        "text": text,
                        "source_anchor": "type",
                        "verify_in_review": True,
                    }
                ],
            )
            write(root / ".agent/exact-a3.json", child)
    write(
        WORK / "roleq-six-1/exact-rework-plan-1.json",
        {
            "classification": "Guided inherited semantic recovery, never initial autonomous score",
            "calls_max": 4,
            "source": "Primary reviewed first focused Reviewer finding and independently reproduced subtype violations",
            "criterion": "Protected validation, source-backed Reviewer, Primary independent subtype/None/bool probes and full current source review",
            "coordinator_started": False,
            "weekly_ceiling": 40,
            "stop_per_unit": "One correction then Primary takeover if still wrong; no same-signature replay",
        },
    )


if __name__ == "__main__":
    prepare()
