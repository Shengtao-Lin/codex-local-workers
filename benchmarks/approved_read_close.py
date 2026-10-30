"""Separate frozen test metrics from posthoc Primary semantic counterexamples."""

import importlib.util
from pathlib import Path

import bounded_evidence_support as S
import evidence_loop_trial as R


class FalseMap(dict):
    def __bool__(self):
        return False


def observe(path):
    spec = importlib.util.spec_from_file_location("posthoc_mapping", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = FalseMap({1: "value"})
    try:
        result = module.mapping(data, "event")
    except TypeError as exc:
        return {
            "correct_rejection": str(exc) == "Provider event keys must be strings",
            "error": str(exc),
        }
    return {"correct_rejection": False, "returned_same_invalid_mapping": result is data}


def close():
    registration = S.read(R.BATCH / "registration.json")
    rows = S.read(R.BATCH / "cells.json")
    observed = {}
    reference = observe(R.BATCH / "reference-checks/mapping/src/product/code.py")
    if not reference["correct_rejection"]:
        raise ValueError("Counterexample does not discriminate compliant reference")
    for cell in [c for c in registration["order"] if c.startswith("mapping-")]:
        source = Path(rows[cell]["root"]) / rows[cell]["target"]
        before = S.sha(source)
        observed[cell] = {**observe(source), "source_sha256": before}
        if S.sha(source) != before:
            raise ValueError("Observer altered source")
    S.save(
        R.BATCH / "posthoc-primary-mapping.json",
        {
            "registered_test": False,
            "worker_feedback": False,
            "contract": "Every top-level key must be string; arbitrary Mapping implementations accepted",
            "counterexample": "class FalseMap(dict): __bool__ returns False; input FalseMap({1:'value'})",
            "reference": reference,
            "cells": observed,
            "finding": "Truthiness must not guard mandatory key inspection. This is independent Primary review, not a retrospective change to frozen check results or a Reviewer false pass.",
        },
    )
    arms = {
        arm: {
            "executed": 0,
            "frozen_checks_pass": 0,
            "evidence_actions": 0,
            "requests": 0,
            "edits": 0,
            "noops": 0,
            "Primary_confirmed_defects": 0,
        }
        for arm in ("A", "B")
    }
    results = []
    for cell in registration["order"]:
        result = S.read(R.BATCH / "live-results" / cell / "result.json")
        if result["stop_batch"]:
            raise ValueError("Unexpected infrastructure/safety stop")
        arm = arms[cell.split("-")[1]]
        actual = result["ledger"]["actual"]
        arm["executed"] += 1
        arm["frozen_checks_pass"] += int(result["all_independent_pass"])
        for key in ("evidence_actions", "requests", "edits", "noops"):
            arm[key] += actual.get(key, 0)
        defect = cell in observed and not observed[cell]["correct_rejection"]
        arm["Primary_confirmed_defects"] += int(defect)
        results.append(
            {
                "cell": cell,
                "frozen_checks_pass": result["all_independent_pass"],
                "Primary_confirmed_defect": defect,
                "Reviewer": "NOT_RUN_DIAGNOSTIC",
                "full_chain_acceptance": "NOT_RUN_DIAGNOSTIC",
                "assisted": False,
            }
        )
    S.save(
        R.BATCH / "metrics.json",
        {
            "arms": arms,
            "cells": results,
            "Primary_during_worker_semantic_hints": 0,
            "Primary_code_takeovers": 0,
            "cloud_tokens": None,
            "Primary_active_seconds": None,
            "preparation_failures": "Four separate offline directories retained; zero model calls in them",
        },
    )
    S.save(
        R.BATCH / "decision.json",
        {
            "status": "NO_ADOPTION_EVIDENCE_UNEXERCISED_PRIMARY_DEFECTS_FOUND",
            "registered": 12,
            "executed": 12,
            "arms": arms,
            "conclusion": "Both arms6/6 registered independent checks; actual evidence requests0. No evidence-access benefit established. Three of four Mapping implementations skip mandatory key checks on false-valued mappings; Primary posthoc observer confirms and compliant reference rejects. Old tests lacked that behavior coverage.",
            "design_boundary": "Accurate persistence and permission-safe tools cannot guarantee semantic completeness. Keep optional features off by default; preserve host automatic repair and source-bound static diagnostics. No product/Coordinator release.",
            "next": "Reviewer output candidate already frozen and launched separately. Future Mapping recovery requires separately frozen contract-preserving protected coverage, not model hints or changing original scores.",
            "weekly_stop": 50,
            "production_enabled": False,
        },
    )
    with (R.BATCH / "handoff.md").open("x", encoding="utf-8") as stream:
        stream.write(
            "# Approved evidence access diagnostic\n\n12/12 executed. A6/6 and B6/6 frozen checks, but B READ/SEARCH0: capability unexercised, no adoption. All responses first-proposal implementations; no local repair or Primary semantic hint.\n\nPrimary source review independently found boolean-guarded Mapping key validation; a separate posthoc observer confirmed mapping-A-1/A-2/B-2 wrongly return FalseMap({1:'value'}), while B-1 and reference raise the required TypeError. Frozen metrics unchanged, no hidden feedback supplied, Reviewer NOT_RUN.\n\nFour preparation attempts failed offline and are preserved, including Primary test/helper mistakes and intentionally rejected capture binding. These are once-only experiment preparation costs, not Worker failures or recurring coordination savings.\n"
        )
    print(arms)


if __name__ == "__main__":
    close()
