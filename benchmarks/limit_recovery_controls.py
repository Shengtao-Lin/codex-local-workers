"""Required positive control and identical-start proof before valid model cohort."""

import json
import shutil

import limit_recovery_v2 as version
from capability_fit import WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import command

trial = version.trial


def main():
    root = trial.BASE / "primary-oracle"
    root.mkdir(parents=True, exist_ok=False)
    provenance = read(trial.FROZEN / "provenance.json")
    for path in provenance["files"]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(trial.FROZEN / path, target)
    # Primary-authored reference stays outside every worker-readable root.
    shutil.copyfile(
        WORK / "limit-recovery-1/primary-oracle" / trial.COMMON, root / trial.COMMON
    )
    checks = [
        command(
            root,
            [
                str(trial.PYTHON),
                "-B",
                "-m",
                "pytest",
                "tests",
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=.agent/oracle-temp",
                "--junitxml=.agent/oracle.xml",
            ],
        )
    ]
    for argv in (
        ["ruff", "check", "src", "tests"],
        ["ruff", "format", "--check", "src", "tests"],
        ["pyright", str(root / trial.COMMON), "--pythonpath", str(trial.PYTHON)],
    ):
        checks.append(command(root, [str(trial.PYTHON), "-B", "-m", *argv]))
    initial = [
        read(trial.BASE / arm / ".agent/manifest.json")["files"] for arm in trial.ARMS
    ]
    if not all(hashes == initial[0] for hashes in initial):
        raise ValueError("experimental arms do not have identical source/test inputs")
    counts = trial.selection.evidence.counts(root / ".agent/oracle.xml")
    passed = all(c["exit"] == 0 for c in checks) and counts == {
        "tests": 38,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    write(
        trial.BASE / "positive-preflight.json",
        {
            "passed": passed,
            "checks": checks,
            "junit": counts,
            "identical_arm_inputs": True,
            "primary_reference_only": True,
            "reference_sha256": digest(root / trial.COMMON),
            "v1_exclusion": "Primary protected assertion E501 prevented clean acceptance; preparation failure and old control invocation retained, not used in model comparison",
            "identity_note": "v1/v2 task labels reused but canonical roots distinct; all reports identify workspace. No archive overwritten.",
        },
    )
    print(json.dumps({"passed": passed, "junit": counts}))
    if not passed:
        raise ValueError("do not run models until positive control passes all checks")


if __name__ == "__main__":
    main()
