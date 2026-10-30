"""Freeze Primary locating judgments with mechanical citation/drift verification."""

import argparse
from pathlib import Path

import bounded_evidence_support as S


def close(batch, accepted, used):
    registration = S.read(batch / "registration.json")
    if not set(accepted) <= set(registration["order"]):
        raise ValueError("Unknown cell")
    rows = []
    for cell in registration["order"]:
        row = registration["cells"][cell]
        root = Path(row["root"])
        process = S.read(batch / "results" / cell / "process.json")
        report = S.read(root / ".agent/explorer.json")
        for name, digest in row["files"].items():
            if S.sha(root / name) != digest:
                raise ValueError("Protected drift")
        if cell in accepted:
            if process["stop_batch"] or report["status"] != "success":
                raise ValueError("Cannot accept failed run")
            for ref in report["source_refs"]:
                path = root / ref["path"]
                if S.sha(path) != ref["source_hash"]:
                    raise ValueError("Citation source changed")
                lines = path.read_text(encoding="utf-8-sig").splitlines()
                actual = "\n".join(lines[ref["start_line"] - 1 : ref["end_line"]])
                if actual != ref["quote"]:
                    raise ValueError("Citation mismatch")
        rows.append(
            {
                "cell": cell,
                "runtime": report["status"],
                "primary_accepted": cell in accepted,
                "seconds": process["seconds"],
                "usage": report["budget_usage"],
            }
        )
    S.save(
        batch / "metrics.json",
        {
            "registered": len(rows),
            "executed": len(rows),
            "not_run": 0,
            "accepted": len(accepted),
            "rows": rows,
            "primary_active_seconds": "unknown",
            "cloud_tokens": "unknown",
            "preparation": registration["primary_cost"],
        },
    )
    S.save(
        batch / "decision.json",
        {
            "status": "PASS_SCOPED_LOCATING" if len(accepted) == len(rows) else "HOLD",
            "accepted": len(accepted),
            "registered": len(rows),
            "weekly_used": used,
            "weekly_stop": 40,
            "scope": "Exposed two locating questions with Primary-selected required source/test paths; no autonomous unknown-repository or Coordinator qualification",
            "primary_evidence": "All returned source/test ranges independently inspected. Raw reports locate parsing/rejection and actual adapter caller; quoted tests are normal adapter tests, not claims of malformed-input coverage. Fingerprint reports locate exclusion, serialization call and actual identity/metadata test; the test does not independently exercise labels.",
            "history": "Original and navigation-only2/4 remain; no denominator pooling",
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("batch", type=Path)
    p.add_argument("--accept", nargs="+", required=True)
    p.add_argument("--weekly-used", type=int, required=True)
    a = p.parse_args()
    close(a.batch.resolve(), a.accept, a.weekly_used)
