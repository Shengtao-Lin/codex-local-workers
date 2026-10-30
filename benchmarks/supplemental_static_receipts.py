"""Freeze/close the narrow current-epoch supplemental diagnostic parity fix."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import flat_diagnostics_receipts as F

S = F.S
BATCH = S.KIT / "benchmarks/work/harness-convergence/supplemental-static-20261022-1"
CHANGED = {
    ".local-agents/bounded/consolidated_harness.py",
    ".local-agents/bounded/static_focus_rules.py",
}


def freeze(used):
    original = S.save

    def save(path, value):
        if Path(path) == BATCH / "registration.json":
            value.update(
                feature_id="supplemental-static-diagnostic-parity",
                dependencies=[
                    "flat-diagnostics-20261022-1",
                    "checked-research-transfer-20261022-1",
                ],
                finding="Pytest failure causes configured static commands to be run as supplemental observations. Existing diagnostics reads only validation.configured_checks, so actual Ruff/Pyright failures lose the structured current-source focus despite raw output remaining visible.",
                candidate="Pass existing supplemental checks to the same parser only when their full input facts match the current validation and live inputs. Preserve all prior source/scope checks; never treat these observations as validation success.",
                scope=[*sorted(CHANGED), "tests/test_supplemental_static_focus.py"],
                controls=[
                    "red installed mixed pytest/static reproduction",
                    "current epoch and approved source positives",
                    "stale/unbound/truncated/unsafe/out-of-scope negatives",
                    "installed full check and original budget parity",
                ],
                weekly_used_observed=used,
                live_policy="Zero live here; separately freeze new mixed-error task comparison after offline verification. No further ID-family retries.",
            )
        original(path, value)

    F.BATCH, S.save = BATCH, save
    try:
        F.freeze()
    finally:
        S.save = original


def close():
    reg = S.read(BATCH / "registration.json")
    changed = {
        name: S.sha(S.KIT / name)
        for name, digest in reg["preimages"].items()
        if S.sha(S.KIT / name) != digest
    }
    assert set(changed) == CHANGED
    assert all(S.sha(BATCH / "preimages" / n) == d for n, d in reg["preimages"].items())
    counts = {}
    for label in ("red", "green"):
        suites = ET.parse(BATCH / (label + ".xml")).getroot().findall("testsuite")
        counts[label] = {
            k: sum(int(s.get(k, 0)) for s in suites)
            for k in ("tests", "failures", "errors", "skipped")
        }
    assert counts["red"]["failures"] >= 1 and counts["red"]["errors"] == 0
    assert counts["green"]["tests"] > 0 and all(
        counts["green"][k] == 0 for k in ("failures", "errors", "skipped")
    )
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_CURRENT_SUPPLEMENTAL_DIAGNOSTIC_PARITY",
            "model_calls": 0,
            "changed_existing": changed,
            "controls": counts,
            "adopted": "Repair evidence delivery only, no parser/rule/prompt/action/budget/default or acceptance change.",
            "not_proven": "Live improvement or cause of historical semantic failures; raw check output had already been visible.",
            "old_results": "Unchanged; checked-research transfer remains0/2 and original frame transfer2/4 HOLD.",
            "next": "Separate fixed cross-task mixed behavior/static comparison; no old ID retry.",
        },
    )
    S.save(
        BATCH / "handoff.json",
        {
            "phase": "closed",
            "decision": "decision.json",
            "next": "Register a small mixed-error comparison on different previously qualified task families",
            "live_calls": 0,
        },
    )
    print(counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["freeze", "close"])
    parser.add_argument("--weekly-used", type=int)
    args = parser.parse_args()
    freeze(args.weekly_used) if args.mode == "freeze" else close()
