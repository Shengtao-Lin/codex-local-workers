"""Audit the entire carried-forward preservation set with explicit edit scope."""
import argparse
from pathlib import Path

import harness_r3_prepare as P

B = P.B
ALLOWED = {
    ".local-agents/worker-runtime.py", ".local-agents/local-unit.py",
    ".local-agents/reviewer-runtime.py", ".local-agents/record-review.py",
    ".local-agents/task-policy.py", ".local-agents/proposal-interface.py",
    ".local-agents/host-proposal-protocol.py", "benchmarks/harness_r3_checkpoint.py",
    "docs/local-model-harness-convergence-plan.md",
}


def audit(label):
    baseline = B.read(P.BATCH / "baseline.json")
    intentional, unexpected = [], []
    for number, (name, expected) in enumerate(baseline.items(), 1):
        path = Path(name)
        actual = B.sha(path) if path.is_file() else None
        if actual != expected:
            relative = path.relative_to(B.KIT).as_posix() if path.is_relative_to(B.KIT) else name
            row = {"path": name, "before": expected, "after": actual}
            if relative in ALLOWED:
                checkpoint = P.BATCH / "checkpoint" / relative
                row["preimage_preserved"] = checkpoint.is_file() and B.sha(checkpoint) == expected
                intentional.append(row)
                if not row["preimage_preserved"]:
                    unexpected.append(row)
            else:
                unexpected.append(row)
        if number % 20000 == 0:
            print(f"Preservation {number}/{len(baseline)}", flush=True)
    result = {"checked": len(baseline), "intentional_edits": intentional, "unexpected_drift": unexpected, "passed": not unexpected}
    B.save(P.BATCH / f"preservation-{label}.json", result)
    print(f"Preserved {len(baseline)} prior paths; {len(intentional)} allowed edits; {len(unexpected)} unexpected drift", flush=True)
    if unexpected:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    args = parser.parse_args()
    audit(args.label)
