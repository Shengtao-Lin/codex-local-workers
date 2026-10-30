"""Two complex full-project units on the frozen direct-Primary candidate."""

import argparse
import os
from pathlib import Path

import strata_complex_tasks as TASKS
import strata_subagent_trial as BASE

J, P, S = BASE.J, BASE.P, BASE.S
BATCH = P.I.BASE / "strata-complex-20261023-2"
ORDER = ["tools-1", "raw-1"]


def save(path, value):
    path = Path(path)
    if path.name == "capture-spec.json":
        topic = path.parent.parent.parent.name.split("-")[0]
        value = {**value, "family": TASKS.tasks()[topic]["family"]}
    if (
        path.name == "config.json"
        and ".agent" in path.parts
        and "prepared" not in path.parts
    ):
        topic = path.parent.parent.parent.name.split("-")[0]
        value = {
            **value,
            "experimental_strata_subagent": True,
            "experimental_evidence_files": [
                TASKS.TARGET,
                "src/evaluation_harness/canonical/models.py",
                "src/evaluation_harness/adapters/generic_otel.py",
                f"tests/unit/test_local_worker_{topic}.py",
            ],
        }
    if path == BATCH / "registration.json":
        value = {
            **value,
            "registered": 2,
            "weekly_cap": 40,
            "candidate": "Unchanged strata-subagent-20261023-1 B candidate, guarded reads/edits/checks -> direct full Primary review",
            "model": "Same resident iq3_s128K/parallel1; client64K,medium,4096 thinking/12288 total output,temp1/top_p.95/top_k20",
            "budget": "Per unit12 requests/3 effective edits/1 initial+3 postchecks/2 protocol recoveries/900s; max4 read/search within12. Cell2220s,batch5400s. No Reviewer/Explorer/Coordinator calls.",
            "exposure": "Two new behavior contracts on previously exposed frozen sibling module/domain, not unseen-repository or public benchmark holdout. Detailed Primary contract/protected tests; independent acceptance outside scope. No old score replacement.",
            "gate": "2/2 verified canonical host handoffs, full independent project tests/statics, full Primary source/diff/contract acceptance and zero drift; complexity smoke only, not stability/release. Reads optional; zero reads means exploration still unexercised.",
            "continue_rule": "Ordinary failure HOLD, finish other fixed unit for diagnosis. Stop immediately infrastructure/residency/drift/safety/deadline/weekly40; inspect each cell before next. No rerolls or new hints.",
            "Primary": "Creates new task contracts/public-private controls/reference; one-time preparation distinct from per-task review. No live algorithm hints or code takeover. Costs unknown; no savings claim.",
            "not_tested": [
                "multi-file edits",
                "general planning",
                "Coordinator",
                "production rollout",
                "cloud savings",
                "build_samples typed capture",
            ],
            "production_acceptance": False,
        }
        for filename in (
            "strata_complex_trial.py",
            "strata_complex_tasks.py",
            "strata_subagent_rules.py",
            "strata_subagent_entry.py",
            "strata_model_entry.py",
            "strata_entry.py",
            "approved_evidence.py",
        ):
            p = Path(__file__).with_name(filename)
            value["pins"][str(p)] = S.sha(p)
        return BASE.B.MODEL.BASE_SAVE(path, value)
    if path == BATCH / "preparation.json":
        value = {
            **value,
            "authorization": "User requested more complex isolated examples and architecture review; weekly40 stop, no production/sibling changes/commit/push",
            "feature_id": "complex-bounded-agent-units",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Public parsing compatibility and stream-event identity/status invariants; full Primary review and real caller tests, no risk reduction by function sizing.",
            "exposure": "New task contracts on exposed frozen module; tools eventstream and raw UTF8 parser, separate independent units not one combined feature. Runtime propagation remains unregistered because typed capture unsupported.",
        }
    return BASE.READY.save(path, value)


def configure():
    BASE.B.BATCH = BASE.B.MODEL.BATCH = BASE.B.FIRST.BATCH = BATCH
    BASE.B.FIRST.ENTRY = BASE.ENTRY
    BASE.B.FIRST.configure()
    BASE.B.FIRST.ORIGINAL_SAVE = save
    J.ORDER = P.ORDER = ORDER
    J.copy_project = BASE.COPY
    J.TASKS.tasks = TASKS.tasks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    assert args.weekly_used < 40
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    configure()
    if args.mode == "prepare":
        J.prepare(args.weekly_used)
    else:
        P.TARGET = S.read(BATCH / "cells.json")[args.cell]["target"]
        P.run(args.cell, args.weekly_used)
