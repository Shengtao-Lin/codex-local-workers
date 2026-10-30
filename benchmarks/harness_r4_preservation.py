"""Resumable, streaming R4 preservation audit after a lost command session."""

import hashlib
from pathlib import Path

import harness_r4_prepare as H

B = H.B


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    batch = H.BATCH
    baseline_path = batch / "baseline.json"
    baseline_hash = digest(baseline_path)
    entries = sorted(B.read(baseline_path).items())
    output = batch / "preservation-recovery"
    allowed = {B.KIT / "docs/local-model-harness-convergence-plan.md"}
    changes = []
    for offset in range(0, len(entries), 2000):
        chunk = entries[offset : offset + 2000]
        result_path = output / f"chunk-{offset:06d}.json"
        if result_path.exists():
            result = B.read(result_path)
            assert result["baseline_sha256"] == baseline_hash
            assert result["offset"] == offset and result["checked"] == len(chunk)
        else:
            drift = []
            for name, expected in chunk:
                path = Path(name)
                actual = digest(path) if path.is_file() else None
                if actual != expected:
                    drift.append(
                        {
                            "path": name,
                            "current_sha256": actual,
                            "intentional_stage_change": path in allowed,
                        }
                    )
            result = {
                "baseline_sha256": baseline_hash,
                "offset": offset,
                "checked": len(chunk),
                "changed": drift,
            }
            B.save(result_path, result)
        changes.extend(result["changed"])
        print({"checked": offset + len(chunk), "total": len(entries)}, flush=True)
    frozen = B.read(batch / "live-freeze-approved.json")
    H.R.assert_files(B.KIT, frozen["candidate_and_driver"])
    B.save(
        batch / "preservation-final.json",
        {
            "checked": len(entries),
            "baseline_sha256": baseline_hash,
            "changed": changes,
            "unrelated_and_historical_paths_preserved": all(
                row["intentional_stage_change"] for row in changes
            ),
            "frozen_candidate_unchanged": True,
            "recovery": "Prior process handle lost, no remaining Python process and no preservation-final output; resumable streaming audit only, no model retry.",
        },
    )
    print({"changes": changes}, flush=True)


if __name__ == "__main__":
    main()
