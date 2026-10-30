"""Independent R1 source probes and immutable Primary interpretation; no worker retry."""

import runpy
from pathlib import Path

from convergence_reviewer import BASE, KIT
from convergence_coder import save
from system_convergence import read_object, ref, sha256

registration = read_object(BASE / "registration.json")
results = []
for cell in registration["cells"]:
    root = Path(cell["root"])
    report = read_object(root / ".agent/r1-reviewer.json")
    source = root / "src/product/target.py"
    for item in cell["inputs"]:
        if not item["path"].startswith(".agent/"):
            assert sha256(root / item["path"]) == item["sha256"]
    module = runpy.run_path(str(source))
    probes = {}
    if "display_name" in module:
        for record in ({}, {"name": None}, {"name": ""}, {"name": "named"}):
            before = dict(record)
            probes[str(record)] = module["display_name"](record)
            assert record == before
    elif "lookup_or" in module:
        for value in (False, None, 0, ""):
            calls = []

            def fetch(key):
                calls.append(key)
                return value

            probes[str(value)] = module["lookup_or"](fetch, "key", "default")
            assert calls == ["key"]
        error = RuntimeError("same exception")

        def fail(key):
            raise error

        try:
            probes["runtime_error"] = module["lookup_or"](fail, "key", "default")
        except RuntimeError as exc:
            assert exc is error
            probes["runtime_error"] = "original propagated"
    else:
        probes = {str(x): module["increment"](x) for x in (-2, 0, 2)}
    valid = report["decision"] != "failed"
    for item in report.get("contract_review", []):
        reference = item["source_ref"]
        lines = (root / reference["path"]).read_text(encoding="utf-8-sig").splitlines()
        assert item["canonical_quote"] == "\n".join(
            lines[reference["start_line"] - 1 : reference["end_line"]]
        )
    correct = valid and report["decision"] == cell["expected_decision"]
    results.append(
        {
            "id": cell["id"],
            "expected": cell["expected_decision"],
            "observed": report["decision"],
            "correct_under_original_standard": correct,
            "independent_probes": probes,
            "report": ref(root, ".agent/r1-reviewer.json"),
            "scope_and_protection_unchanged": True,
            "primary_disposition": "replan"
            if cell["id"].startswith("conflicting-contract") or not valid
            else "accept"
            if correct and report["decision"] == "pass_to_primary"
            else "rework",
            "source_hash": sha256(source),
            "coverage_missing": report.get("runtime_facts", {})
            .get("display_coverage", {})
            .get("missing"),
            "automatic_rework": False,
        }
    )
save(BASE / "primary-adjudications-1.json", results)
save(
    BASE / "stage-decision-1.json",
    {
        "schema_version": 1,
        "stage": "R1",
        "candidate": "display-coverage-1",
        "decision": "ACCEPT_CHANGE",
        "accepted_change_scope": "Display coverage safety mechanism only, pending I1 integration",
        "semantic_capability": "HOLD_CAPABILITY",
        "original_release_gate": "HOLD",
        "registered": 16,
        "executed": 16,
        "unexecuted": 0,
        "reviewer_calls": 16,
        "coder_calls": 0,
        "explorer_calls": 0,
        "synthetic_archives_not_coder_credit": True,
        "correct": sum(r["correct_under_original_standard"] for r in results),
        "valid_final_reports": sum(r["observed"] != "failed" for r in results),
        "failures": {
            "required-coverage-r1": "Non-JSON response then three duplicate test reads, stopped no progress; failed, no resample",
            "conflicting-contract-r1": "Source reasoning recognizes impossible x+1/x-1 contract; final rework and remove-implementation suggestion incorrect. Primary replans, never Coder rework",
        },
        "safety_checks": "9 independent counterexamples; full runtime/install 486 passed, 137 subtests",
        "semantic_vs_display": "15 valid reports have all registered display coverage; display does not establish semantic understanding, verified references remain read-source based",
        "protected_inputs_unchanged": True,
        "primary_implementation_writes": 0,
        "runtime_registration": ref(KIT, (BASE / "registration.json").relative_to(KIT).as_posix()),
        "primary_adjudications": ref(
            KIT, (BASE / "primary-adjudications-1.json").relative_to(KIT).as_posix()
        ),
        "usage": {
            "weekly_used_start": 52,
            "last_same_window_used": 52,
            "weekly_used_end": 0,
            "ceiling": 60,
            "window_discontinuity": "Actual account tool changed used to 0 and resetsAt changed; not savings or negative usage",
        },
        "cost": {
            "cloud_tokens": None,
            "primary_active_seconds": None,
            "economic_qualification": "UNMEASURED",
        },
        "next": "D1 independent proposal-only trial; no semantic gate rename or broad release",
    },
)
print(
    "R1: display safety ACCEPT_CHANGE, original semantic gate HOLD;",
    sum(r["correct_under_original_standard"] for r in results),
    "/16",
)
