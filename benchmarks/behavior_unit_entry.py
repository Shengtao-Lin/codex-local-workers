"""New isolated receiver; immutable earlier candidate remains unchanged."""

import behavior_unit_candidate as UNIT
import bounded_evidence_entry as ENTRY

if __name__ == "__main__":
    ENTRY.C.make_runtime = UNIT.make_runtime
    raise SystemExit(ENTRY.main())
