"""Preserve the current dirty baseline before an opt-in supervised candidate."""

import subprocess

import bounded_evidence_support as S

BATCH = S.KIT / "benchmarks/work/harness-convergence/supervised-release-20261019-1"


def main():
    paths = (
        subprocess.check_output(
            ["git", "ls-files", "-m", "-o", "--exclude-standard", "-z"], cwd=S.KIT
        )
        .decode()
        .split("\0")
    )
    S.save(
        BATCH / "baseline.json",
        {
            "weekly_used": 15,
            "weekly_stop": 40,
            "files": {
                p: S.sha(S.KIT / p) for p in paths if p and (S.KIT / p).is_file()
            },
            "authorization": "User authorizes supervised release iteration; optional Coordinator only after E/C/R qualification",
        },
    )
    for name in (
        "consolidated_harness.py",
        "consolidated_entry.py",
        "function_proposal_rules.py",
        "preserved_import_guard.py",
    ):
        dest = BATCH / "candidate-preimages" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("xb") as stream:
            stream.write((S.KIT / "benchmarks" / name).read_bytes())
    print("Baseline frozen; no model calls")


if __name__ == "__main__":
    main()
