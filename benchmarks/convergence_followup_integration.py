"""Combine accepted safety/decomposition changes, preserve all old gate identities."""

import argparse
import shutil
import subprocess
import xml.etree.ElementTree as ET

from convergence_coder import KIT, save
from convergence_followup import BASE
from system_convergence import read_object, ref, sha256

TARGET = BASE / "i1-candidate-kit"


def assemble():
    shutil.copytree(
        BASE / "candidate-kit",
        TARGET,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"),
    )
    for relative in (
        ".local-agents/coordinator-brief.py",
        ".local-agents/tests/test_coordinator_brief.py",
        "AGENTS.md",
    ):
        source = BASE / "coordinator-kit" / relative
        destination = TARGET / relative
        if destination.exists():
            # The new isolated AGENTS file replaces only another disposable copy.
            assert relative == "AGENTS.md"
        shutil.copyfile(source, destination)
    save(
        BASE / "i1-assembly.json",
        {
            "selected": [
                "P0 baseline",
                "R1 display coverage plus first-observation freshness",
                "D1 small proposal DTO/trusted materialization",
            ],
            "excluded": ["C1/C2 KEEP_BASELINE", "E1 receipt candidate KEEP_BASELINE"],
            "source": str(TARGET),
            "production_promoted": False,
            "files": [
                ref(TARGET, p.relative_to(TARGET).as_posix())
                for p in (TARGET / ".local-agents").rglob("*.py")
            ],
        },
    )


def audit():
    p0 = KIT / "benchmarks/work/system-convergence/p0p1-20261010-1"
    manifest = read_object(p0 / "baseline-manifest.json")
    changed = [
        i["path"]
        for i in manifest["files"]
        if (sha256(KIT / i["path"]) if (KIT / i["path"]).is_file() else None)
        != i.get("sha256")
    ]
    history = [
        i["path"]
        for i in manifest["history_inputs"]
        if sha256(KIT / i["path"]) != i["sha256"]
    ]
    peers = [
        name + "/" + i["path"]
        for name, files in manifest["sibling_comparisons"].items()
        for i in files
        if (
            sha256(KIT.parent / name / i["path"])
            if (KIT.parent / name / i["path"]).is_file()
            else None
        )
        != i["peer_sha256"]
    ]
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=KIT, text=True
    ).strip()
    assert not changed and not history and not peers and head == manifest["head"]
    assembly = read_object(BASE / "i1-assembly.json")
    assert all(
        sha256(TARGET / item["path"]) == item["sha256"] for item in assembly["files"]
    )
    tree = ET.parse(BASE / "i1-full-regression-2.xml")
    cases = list(tree.iter("testcase"))
    failures = [
        case.get("name")
        for case in cases
        if any(child.tag in {"failure", "error"} for child in case)
    ]
    skipped = [
        case.get("name")
        for case in cases
        if any(child.tag == "skipped" for child in case)
    ]
    assert not failures and skipped == ["test_symlink_path_is_rejected"]
    save(
        BASE / "i1-validation-summary.json",
        {
            "full_regression": "1065 passed, 1 skipped, 157 subtests",
            "xml": ref(BASE, "i1-full-regression-2.xml"),
            "failed": failures,
            "skipped": skipped,
            "host_skip": "OS does not permit real symlink creation; retained, not counted passed",
            "additional_actual_windows_junction_control": ref(
                BASE, "reparse-control/results.json"
            ),
            "static": {
                "ruff_check": "pass",
                "format_check": "8 current selected files pass",
                "pyright_selected_runtime": "0 errors, warnings or information",
            },
            "inherited_benchmark_format_failure": ref(
                BASE, "i1-format-only-change.json"
            ),
            "runtime_hashes_current": True,
            "fresh_live_smoke": "NOT_RUN_DEPENDENCY: cannot replace with old or synthetic successes",
        },
    )
    save(
        BASE / "preservation-audit-1.json",
        {
            "preexisting_files": len(manifest["files"]),
            "changed": changed,
            "history_inputs": len(manifest["history_inputs"]),
            "history_changed": history,
            "sibling_paths": sum(
                len(files) for files in manifest["sibling_comparisons"].values()
            ),
            "sibling_changed": peers,
            "head_unchanged": True,
            "production_runtime_changed": False,
            "commit_push": False,
        },
    )
    prior = read_object(BASE / "baseline.json")["previous_gates"]
    gates = prior["gates"]
    replacements = {
        "v12-explorer-independent-completion": (
            "HOLD",
            "New E1 same six questions: runtime success 6/6 but independent truthful/completeness 4/6. Both negative cells fabricate SEARCH; old failures unchanged.",
        ),
        "reviewer-original-sixteen-semantic": (
            "HOLD",
            "New fixed sixteen 13/16, 14 valid reports: optional test-gap false positive and two required-coverage protocol/no-progress failures. Contract conflicts now both correct; not a statistically demonstrated gain.",
        ),
        "reviewer-input-freshness-and-adapter-compatibility": (
            "PASS",
            "First observed hashes preserved before repeated initial_payload; 11 new coverage controls, original retained/staged adapters and complete 1047-test suite pass apart from host-symlink skip.",
        ),
        "coordinator-decomposition-proposal": (
            "PASS_LIMITED",
            "Same previously exposed briefs: 12/12 correct initial drafts, zero protocol corrections or semantic revisions; separate source/hash-bound Primary approvals. No dispatch.",
        ),
        "coordinator-approved-supervised-execution": (
            "NOT_RUN_DEPENDENCY",
            "D2/combined live smoke not started. Proposal qualification cannot silently waive E/C/R qualification/old gates.",
        ),
        "complete-runtime-http-example-install-validation": (
            "PASS_APPLICABLE_WITH_HOST_SKIP",
            "Combined 1065 pass, 1 OS-symlink skip retained (never counted pass), 157 subtests. Additional actual Windows junction rejected by collector and approval source guard. Runtime/check/format/Pyright current; D2 live smoke still NOT_RUN.",
        ),
        "source-scope-config-history-preservation": (
            "PASS",
            "1552 pre-existing files, 216 old history inputs, 100 sibling deployment paths and HEAD unchanged. All role controls immutable.",
        ),
    }
    for gate in gates:
        if gate["id"] in replacements:
            gate["status"], gate["evidence"] = replacements[gate["id"]]
    save(
        BASE / "release-gates-1.json",
        {
            **prior,
            "version": "convergence-followup-1",
            "implementation_gate": "HOLD",
            "release_gate": "HOLD",
            "gates": gates,
            "previous_gates_preserved": True,
            "new_product_boundaries_approved": False,
        },
    )
    save(
        BASE / "stage-decision-1.json",
        {
            "stage": "I1-followup",
            "decision": "HOLD_CAPABILITY",
            "explorer": "4/6 independent complete; KEEP_BASELINE",
            "reviewer": "13/16 original semantic gate HOLD; deterministic freshness safety repair passes",
            "coordinator": "12/12 supervised proposal qualification; execution/economics unqualified",
            "actual_role_calls": {
                "explorer": 6,
                "reviewer": 16,
                "coordinator": 12,
                "coder": 0,
            },
            "new_candidate_after_live": False,
            "old_denominators_and_failures_preserved": True,
            "production_promoted": False,
            "weekly_used_start": 0,
            "latest_observed_used": 1,
            "weekly_used_ceiling": 15,
            "cloud_tokens": None,
            "primary_active_seconds": None,
            "economic_claim_allowed": False,
            "next_authority_needed": "Original plan requires separate authorization for a second live role candidate; async question asks for independent report-protocol convergence phase. Cannot change frozen candidates, declare model narrative truthful, silently waive original gates, or burn budget on resampling.",
            "budget_exhausted": False,
            "goal_achieved": False,
            "interrupted_freeze_attempt": "followup-20261011-1 empty directory retained: unpruned history traversal interrupted; new attempt uses pruned walk, no writer/model interrupted",
            "retained_infrastructure_failures": "full-regression-1: 1045 pass, 2 failures from relocated sibling interpreter. Explicit readonly interpreter bootstrap fixes paths, no test assertions changed; follow-up full-regression-2 1047 pass/1 skip",
        },
    )
    print(
        "Preservation passed; original I1 capability gates HOLD; no commit/push/promotion"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("assemble", "audit"))
    args = parser.parse_args()
    assemble() if args.action == "assemble" else audit()
