"""I1 immutable preservation and release-gate decision; no model calls or promotion."""

import subprocess
import xml.etree.ElementTree as ET

from convergence_coder import KIT, save
from system_convergence import read_object, ref, sha256

BASE = KIT / "benchmarks/work/system-convergence/i1-20261011-1"
P0 = KIT / "benchmarks/work/system-convergence/p0p1-20261010-1"
manifest = read_object(P0 / "baseline-manifest.json")
changed = [
    item["path"]
    for item in manifest["files"]
    if (sha256(KIT / item["path"]) if (KIT / item["path"]).is_file() else None)
    != item.get("sha256")
]
snapshot_changed = [
    item["path"]
    for item in manifest["files"]
    if item["exists"] and sha256(P0 / "source-snapshot" / item["path"]) != item["sha256"]
]
history_changed = [
    item["path"]
    for item in manifest["history_inputs"]
    if sha256(KIT / item["path"]) != item["sha256"]
]
peer_changed = []
for name, files in manifest["sibling_comparisons"].items():
    for item in files:
        path = KIT.parent / name / item["path"]
        if (sha256(path) if path.is_file() else None) != item["peer_sha256"]:
            peer_changed.append(name + "/" + item["path"])
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=KIT, text=True).strip()
assert not changed and not snapshot_changed and not history_changed and not peer_changed
assert head == manifest["head"]
save(
    BASE / "preservation-audit-1.json",
    {
        "baseline": ref(KIT, (P0 / "baseline-manifest.json").relative_to(KIT).as_posix()),
        "preexisting_files_checked": len(manifest["files"]),
        "changed": changed,
        "history_files_checked": len(manifest["history_inputs"]),
        "history_changed": history_changed,
        "source_snapshot_changed": snapshot_changed,
        "sibling_deployment_paths_checked": 100,
        "sibling_deployment_changed": peer_changed,
        "head_unchanged": True,
        "production_runtime_changed": False,
        "global_coordinator_enabled": False,
        "private_config_not_for_publication": True,
    },
)

tree = ET.parse(BASE / "full-regression-2.xml")
cases = list(tree.iter("testcase"))
failures = [
    {"id": c.get("classname", "") + "::" + c.get("name", ""), "message": child.get("message")}
    for c in cases
    for child in c
    if child.tag in {"failure", "error"}
]
skips = [
    {"id": c.get("classname", "") + "::" + c.get("name", ""), "reason": child.get("message")}
    for c in cases
    for child in c
    if child.tag == "skipped"
]
http = [
    {
        "id": c.get("name"),
        "passed": not any(child.tag in {"failure", "error", "skipped"} for child in c),
    }
    for c in cases
    if "test_e2e_pipeline" in c.get("classname", "")
]
save(
    BASE / "validation-summary-1.json",
    {
        "full_regression": "1041 passed, 4 failed, 1 skipped, 143 subtests",
        "xml": ref(KIT, (BASE / "full-regression-2.xml").relative_to(KIT).as_posix()),
        "failed": failures,
        "skipped": skips,
        "http_e2e": http,
        "baseline_countercontrol": "Two same adapter tests pass on unchanged P0 baseline",
        "retained_invalid_launch": "full-regression-1.xml: nonexistent top-level examples path, zero tests; not passed",
        "static": {"ruff": "pass", "pyright_reviewer": "0 errors, warnings, informations"},
        "examples": "Existing example-packet validation and example-feature-plan compatibility are inside runtime tests; no top-level examples directory",
    },
)

runtime = BASE / "candidate-kit/.local-agents"
save(
    BASE / "version-manifest.json",
    {
        "version": "convergence-i1-safety-only-1",
        "promoted": False,
        "selected": ["P0 baseline", "R1 display coverage only"],
        "excluded": ["C1 KEEP_BASELINE", "C2 KEEP_BASELINE", "D1 HOLD"],
        "files": [ref(runtime, p.relative_to(runtime).as_posix()) for p in runtime.rglob("*.py")],
        "fresh_smoke": "NOT_RUN: D2 prerequisite missing; no synthetic replacement credited",
    },
)
gates = [
    {
        "id": "v12-explorer-independent-completion",
        "source": "docs/stability-plan-v1.2.md; docs/improvement-plan-v2.1.md Phase0",
        "status": "HOLD",
        "evidence": "E1 4/6 independent obligation-complete; Coder success does not compensate",
    },
    {
        "id": "coder-normal-supervised-families",
        "source": "docs/worker-system-convergence-plan.md C1/C2",
        "status": "LIMITED_EVIDENCE",
        "evidence": "C1 both arms 4/4 accepts; C2 all 4 Coder valid, 3 Reviewer accepts. No live target field/path improvement, preserve baseline",
    },
    {
        "id": "reviewer-original-sixteen-semantic",
        "source": "docs/reviewer-evidence-candidate-plan.md; docs/worker-system-convergence-plan.md R1",
        "status": "HOLD",
        "evidence": "Fresh fixed R1 14/16. Required-coverage-r1 no progress; conflicting-contract-r1 wrong rework. No gate renaming",
    },
    {
        "id": "reviewer-input-freshness-and-adapter-compatibility",
        "source": "tests/test_reviewer_retained_evidence.py; tests/test_reviewer_staged_assessment_adapter.py",
        "status": "HOLD_SAFETY",
        "evidence": "I1 overwrites observed hash during repeated initial_payload; baseline same controls 2/2 pass; original frozen R1 promotion revoked",
    },
    {
        "id": "coordinator-decomposition-proposal",
        "source": "docs/worker-system-convergence-plan.md D1",
        "status": "HOLD",
        "evidence": "12 registered, 3 executed, 0 valid final plans, 9 unrun; deep full-packet schema failures. Approval module offline controls pass, no dispatch",
    },
    {
        "id": "coordinator-approved-supervised-execution",
        "source": "docs/improvement-plan-v2.1.md Phase2; docs/worker-system-convergence-plan.md D2/I1",
        "status": "NOT_RUN_DEPENDENCY",
        "evidence": "D1 unmet. No paired execution, no combined live smoke",
    },
    {
        "id": "complete-runtime-http-example-install-validation",
        "source": "docs/release-checklist.md; docs/worker-system-convergence-plan.md I1",
        "status": "INCOMPLETE",
        "evidence": "I1 1041 pass, 4 fail, 1 skip. HTTP fake E2E/installer tests pass but whole suite not green; two historical-input failures retained",
    },
    {
        "id": "source-scope-config-history-preservation",
        "source": "AGENTS.md; docs/worker-system-convergence-plan.md P0/I1",
        "status": "PASS",
        "evidence": "1552 original files, 216 history inputs and 100 sibling deployment paths unchanged; HEAD unchanged; no commit/push",
    },
    {
        "id": "paired-primary-cost-and-token-savings",
        "source": "docs/improvement-plan-v2.1.md Phase5; docs/release-checklist.md; docs/worker-system-convergence-plan.md D2",
        "status": "UNMEASURED",
        "evidence": "No attributable cloud tokens or Primary active-time measurement; changed usage window is budget telemetry only",
    },
    {
        "id": "external-postgresql-mlflow",
        "source": "docs/release-checklist.md",
        "status": "NOT_RUN_OUT_OF_SCOPE",
        "evidence": "No target-project integration or sibling writes authorized",
    },
    {
        "id": "git-publication",
        "source": "docs/release-checklist.md",
        "status": "NOT_RUN_USER_PROHIBITED",
        "evidence": "No commit/push; this is not a published product version",
    },
]
save(
    BASE / "release-gates.json",
    {
        "schema_version": 1,
        "version": "convergence-i1-safety-only-1",
        "implementation_gate": "HOLD",
        "release_gate": "HOLD",
        "gates": gates,
        "historical_evidence": "Older GO/checkboxes apply only to their original version and scope; not silently removed or reused as current pass",
        "new_product_boundaries_approved": False,
        "economic_claim_allowed": False,
    },
)
save(
    BASE / "r1-promotion-revocation.json",
    {
        "stage": "R1",
        "original_stage_decision_unchanged": True,
        "original_decision": "ACCEPT_CHANGE: display coverage only, pending I1",
        "effective_decision": "HOLD_SAFETY",
        "reason": "Integration negative control proves initial_payload overwrites prior observed source hashes, invalidating drift detection",
        "production_promoted": False,
        "candidate_changed_after_live": False,
        "fix_boundary": "A new independently frozen candidate must check existing observed hashes before any assignment and preserve first-observation identity; run retained/staged adapters and full suite before live. Do not patch the old live candidate.",
    },
)
save(
    BASE / "stage-decision-1.json",
    {
        "schema_version": 1,
        "stage": "I1",
        "decision": "HOLD_SAFETY",
        "candidate": "convergence-i1-safety-only-1",
        "production_runtime_changed": False,
        "actual_live_calls": {
            "E1_explorer": 6,
            "C1_coder": 8,
            "C1_reviewer": 8,
            "C2_coder": 4,
            "C2_reviewer": 4,
            "R1_reviewer": 16,
            "D1_coordinator": 3,
            "D2": 0,
            "I1": 0,
        },
        "regression": "1041 passed, 4 failed, 1 skipped, 143 subtests; not a passing full suite",
        "failures": failures,
        "protected_inputs_unchanged": True,
        "historical_results_unchanged": True,
        "primary_intervention": "All safety candidates authored/reviewed by Primary in isolated copies; no business fixture takeover implementation or sibling writes",
        "usage": {
            "initial_weekly_used": 50,
            "last_previous_window_used": 52,
            "latest_observed_used": 0,
            "ceiling": 60,
            "window_changed": True,
            "budget_stop": False,
        },
        "cost": {"cloud_tokens": None, "primary_active_seconds": None, "net_savings": "UNMEASURED"},
        "stop": "Reached I1 decision; safety counterexample failed, frozen candidate cannot be promoted or revised after live. D2 blocked by D1 qualification.",
        "next": "Authorize a new bounded candidate: fix Reviewer first-observation freshness before any model rerun; replace full packet authoring in Coordinator proposal with small decomposition DTO plus trusted deterministic materialization. Keep original gates, models and historical denominators.",
    },
)
print("I1 HOLD_SAFETY; baseline, history, siblings and HEAD unchanged; release gates preserved")
