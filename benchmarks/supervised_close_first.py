"""Close the first pilot on observed capture infrastructure failures."""

from pathlib import Path

import bounded_evidence_support as S
from supervised_release_checkpoint import BATCH

NEXT = BATCH.with_name("supervised-release-20261019-2")


def main():
    S.save(BATCH / "decision.json", {
        "status": "HOLD_INFRASTRUCTURE", "registered": 6, "executed": 3,
        "not_run": ["raw-2", "json-2", "ids-2"], "accepted_strict": 1,
        "accepted_supervised": 1, "model_failures_clean_denominator": "not estimated",
        "per_cell": {"ids-1": "accept", "json-1": "Coder static failure plus capture infrastructure noise; no Reviewer", "raw-1": "Coder full independent checks pass; Reviewer input target binding rejected before model"},
        "diagnosis": ["json capture cannot serialize bytes; faulty observation traceback was included in repair context, so json failure is confounded", "raw capture proxy target differs from actual edited function; no-model preflight did not exercise post-edit Reviewer capture"],
        "remedy": "Add bounded typed observations and require scripted complete Coder->Reviewer input replay on all three references before fresh live",
        "history": "No old cell overwritten/retried; independent Pyright missing-annotation defect is real but no pure capability conclusion",
        "weekly_stop": 40,
    })
    NEXT.mkdir(parents=True, exist_ok=False)
    for name in ("capture_validation_facts.py", "supervised_tasks.py", "normal_task_trial.py"):
        path = S.KIT / "benchmarks" / name
        dest = NEXT / "candidate-preimages" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("xb") as stream:
            stream.write(path.read_bytes())
    S.save(NEXT / "preimages.json", {str(S.KIT / "benchmarks" / p.name): {"sha256": S.sha(p), "saved_at": str(p)} for p in (NEXT / "candidate-preimages").iterdir()})
    for cell in ("json-1", "raw-1"):
        import subprocess
        row = S.read(BATCH / "cells.json")[cell]
        root = Path(row["root"])
        name = row["identity"]["run_id"]
        cmd = [str(S.PYTHON), "-B", str(root / ".local-agents/record-review.py"), "--repo", str(root), "--task-id", name, "--run-id", name, "--decision", "replan", "--summary", "Preserve failure: experiment observation infrastructure requires correction; no final acceptance and no model incapability inference."]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        S.save(BATCH / "primary" / cell / "record.json", {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            raise ValueError(result.stdout)
    print("First batch closed; collector and runner preimages preserved")


if __name__ == "__main__":
    main()
