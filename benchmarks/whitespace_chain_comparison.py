"""Preregister the whitespace candidate's live on/off dependent-chain check."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from capability_fit import KIT, WORK, write

BASE = WORK / "roleq-whitespace-live-1"
SNAPSHOT = WORK / "roleq-whitespace-candidate-1"


def main():
    BASE.mkdir(exist_ok=False)
    write(
        BASE / "plan.json",
        {
            "feature_id": "whitespace-preparation-live",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "contracts": [
                "immutable-evidence",
                "accepted-dependencies",
                "no-semantic-gate-bypass",
            ],
            "risk_rationale": "Qualification authority; no automatic acceptance; underlying functional units medium",
            "classification": "Known development fixture. Single runtime/config axis, not unseen qualification",
            "axis": "autoformat_on_diff_whitespace false/true; same candidate binary, models, context, sampling and protected tests",
            "order": "on r1 provider/consumer; off r1 provider/consumer; off r2 then on r2",
            "stop": "Any unit failure stops that arm; other arm remains an independent comparator. No identical replays. Primary acceptance required between dependent units.",
            "max_calls": "8 Coder plus automatic Reviewer for successes; no Explorer or Coordinator",
            "criterion": "Preparation must actually trigger before causal benefit is claimed; complete validated/reviewed/Primary accepted chains and preserved old failure evidence required",
            "weekly_used_ceiling": 40,
            "snapshot": str(SNAPSHOT),
        },
    )
    for enabled in (True, False):
        label = "on" if enabled else "off"
        config = json.loads(
            (SNAPSHOT / ".local-agents/config.json").read_text(encoding="utf-8")
        )
        config["autoformat_on_diff_whitespace"] = enabled
        path = BASE / f"config-{label}.json"
        write(path, config)
        subprocess.run(
            [
                sys.executable,
                str(KIT / "benchmarks/dependent_retention_chain.py"),
                "--prepare",
                "--cohort",
                "roleq-whitespace-" + label + "-1",
                "--snapshot",
                SNAPSHOT.name,
                "--config",
                str(path),
                "--batch",
                "wson1" if enabled else "wsoff1",
            ],
            check=True,
        )
    write(
        BASE / "drivers.json",
        {
            name: hashlib.sha256((KIT / "benchmarks" / name).read_bytes()).hexdigest()
            for name in (Path(__file__).name, "dependent_retention_chain.py")
        },
    )
    print(BASE)


if __name__ == "__main__":
    main()
