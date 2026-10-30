"""Opt-in receiver, leaving all historical candidate files unchanged."""

import bounded_evidence_entry as ENTRY
import feedback_receipt_candidate as RECEIPT

original = ENTRY.C.make_runtime


def make_runtime(worker, host):
    return RECEIPT.wrap(original(worker, host), host)


if __name__ == "__main__":
    ENTRY.C.make_runtime = make_runtime
    raise SystemExit(ENTRY.main())
