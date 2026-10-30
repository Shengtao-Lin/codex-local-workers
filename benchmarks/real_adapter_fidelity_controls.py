"""Independent positive reference and historical-wrapper negative controls."""

import json
import shutil

import real_adapter_fidelity as trial
from capability_fit import WORK, write
from inherited_context_recovery import digest, read


def main():
    trial.configure(1)
    base = WORK / "real-adapter-fidelity-controls-1"
    original = read(trial.live.FROZEN / "provenance.json")
    paths = [*original["copied_original_files"], original["primary_added_test"]["path"]]
    outcomes = []
    for name in ("reference", "historical-wrapper"):
        root = base / name
        root.mkdir(parents=True, exist_ok=False)
        for path in paths:
            source = trial.live.FROZEN / path
            if name == "historical-wrapper" and path == trial.live.COMMON:
                source = WORK / "real-adapter-live-2/candidate" / path
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        shutil.copyfile(trial.SUPPORT, root / trial.EXTRA)
        checks = trial.live.pilot.matrix.SCOPE.FA.LAYER.check(root, "control")
        counts = trial.live.evidence.counts(root / ".agent/control.xml")
        valid = (
            counts
            == {
                "tests": trial.EXPECTED_COUNT,
                "failures": 0 if name == "reference" else 19,
                "errors": 0,
                "skipped": 0,
            }
            and checks["static_pass"]
        )
        outcomes.append(
            {"name": name, "checks": checks, "junit": counts, "valid": valid}
        )
    write(
        base / "controls.json",
        {
            "outcomes": outcomes,
            "passed": all(o["valid"] for o in outcomes),
            "protected_test_sha256": digest(trial.SUPPORT),
            "historical_wrapper": "Accepted under older type-only contract, not relabeled a historical failure",
        },
    )
    print(json.dumps([{k: v for k, v in o.items() if k != "checks"} for o in outcomes]))
    if not all(o["valid"] for o in outcomes):
        raise ValueError("control failure; do not start model cohort")


if __name__ == "__main__":
    main()
