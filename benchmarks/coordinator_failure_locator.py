"""Fresh failure-site question after Primary terminal recovery, not identical replay."""

import json
from pathlib import Path

import coordinator_failure_terminal_retry as candidate
from capability_fit import write
from inherited_context_recovery import digest, read

if __name__ == "__main__":
    candidate.configure()
    root, _, _, _, _ = candidate.retry.original.context()
    transition = read(root / ".agent/primary-recovery-transition.json")
    if transition["status"] != "primary_authorized_rework":
        raise ValueError("Primary recovery must precede new localization")
    candidate.retry.original.QUESTION = (
        "Locate the CURRENT normalize_labels predicate in src/product/labels.py, "
        "the parse_code definition in src/product/schema.py, and the actual zero-key "
        "assertions in tests/test_target.py test_normalize/test_batch_roundtrip. "
        "The executed seven-test failure reports omitted integer zero. This is one "
        "new failure-site localization question after an edit and failed validation. "
        "Read those three actual files and cite small current definition/assertion "
        "ranges. No predicted repair or validation, no stale previous source quote."
    )
    write(
        candidate.BASE / "failure-locator-registration.json",
        {
            "driver_sha256": digest(Path(__file__)),
            "question": candidate.retry.original.QUESTION,
            "reason": "New actual failure-site localization after changed draft and Primary terminal recovery; same role/budgets, no synthetic citations",
        },
    )
    candidate.retry.original.explore("recovery")
    print(json.dumps({"new_failure_site_question": True}))
