"""Explicit v2 receiver, same editor/checks/Reviewer and registered repair unit."""

import behavior_unit_candidate_v2 as UNIT
import bounded_evidence_entry as ENTRY

if __name__ == "__main__":
    ENTRY.C.make_runtime = UNIT.make_runtime
    raise SystemExit(ENTRY.main())
