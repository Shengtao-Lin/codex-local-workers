"""Verified dependency filename for the second locator control, before freezing."""

import argparse
import time
from pathlib import Path

import bounded_evidence_support as S
import explorer_locator_profile_trial as V


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--weekly-used", type=int, required=True)
    a = p.parse_args()
    V.QUESTIONS["request"]["anchors"][1]["path"] = "src/evaluation_harness/canonical/fingerprint.py"
    V.OLD.BATCH, V.OLD.TASK = V.BASE / "request", V.QUESTIONS["request"]["task"]
    if a.mode == "prepare":
        original = S.save
        def save(path, value):
            if Path(path) == V.BASE / "request/registration.json":
                value["pins"][str(Path(__file__))] = S.sha(__file__)
                value["preparation"] = "Actual definition located in canonical/fingerprint.py before registration; no wrong-path Worker call"
            original(path, value)
        S.save = save
        try:
            V.prepare("request", a.weekly_used)
        finally:
            S.save = original
    else:
        V.OLD.run(a.weekly_used, time.time())
