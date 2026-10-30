"""Mechanical runtime-only extraction, preserving frozen experimental sources."""

import argparse
import ast
import subprocess

import bounded_evidence_support as S

BATCH = S.KIT / "benchmarks/work/harness-convergence/installable-bounded-20261021-1"
DEST = S.KIT / ".local-agents/bounded"
MODULES = [
    "consolidated_harness",
    "harness_protocol",
    "preserved_import_guard",
    "function_proposal_rules",
    "bounded_source_rules",
    "literal_check_feedback",
    "repair_phase_rules",
    "static_focus_rules",
    "capture_fixture_support",
    "capture_validation_facts",
    "reviewer_capture_envelope",
    "reviewer_canonical_capture",
    "reviewer_compact_dto",
    "reviewer_evidence_state",
    "reviewer_experiment_entry",
    "reviewer_semantic_entry",
    "reviewer_semantic_transport",
    "reviewer_semantic_greedy",
    "reviewer_semantic_policy",
    "reviewer_contract_first",
    "reviewer_observation_accounting",
    "reviewer_capture_entry",
    "reviewer_contract_status_probe",
    "reviewer_discriminating_status",
]
DROP_IMPORTS = {
    "reviewer_conditional_recovery",
    "reviewer_observation_probe",
    "harness_typed_observations",
    "reviewer_observed_facts",
}
ALIASES = {
    "reviewer_fixed_observations": "approved_provider",
    "reviewer_typed_observations": "approved_provider",
}


def freeze(used):
    assert 0 <= used < 50 and not DEST.exists()
    paths = [S.KIT / "benchmarks" / (m + ".py") for m in MODULES]
    paths += [
        S.KIT / "AGENTS.md",
        *[
            p
            for p in (S.KIT / ".local-agents").rglob("*")
            if p.is_file()
            and not any(
                v in p.parts for v in ("__pycache__", ".ruff_cache", ".pytest_cache")
            )
        ],
    ]
    digests = {}
    for source in paths:
        name = source.relative_to(S.KIT).as_posix()
        target = BATCH / "preimages" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(source.read_bytes())
        digests[name] = S.sha(source)
    S.save(
        BATCH / "baseline.json",
        {
            "weekly_used": used,
            "weekly_stop": 50,
            "files": digests,
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT)
            .decode()
            .strip(),
            "status": subprocess.check_output(
                ["git", "status", "--short"], cwd=S.KIT
            ).decode(),
            "authority": "Approved automatic staged convergence; offline parity/install first, no live before gate",
            "unchanged": [
                "models",
                "default config",
                "Primary acceptance",
                "no automatic semantic rework",
                "old results",
                "sibling repositories",
            ],
        },
    )


def globals_of(node):
    targets = (
        node.targets
        if isinstance(node, ast.Assign)
        else [node.target]
        if isinstance(node, ast.AnnAssign)
        else []
    )
    return {n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name)}


def extract():
    baseline = S.read(BATCH / "baseline.json")
    assert all(S.sha(S.KIT / p) == h for p, h in baseline["files"].items())
    DEST.mkdir(exist_ok=False)
    (DEST / "__init__.py").write_text(
        '"""Opt-in bounded single-function execution; no activation by import."""\n',
        encoding="utf-8",
    )
    recipes = {}
    for name in MODULES:
        source = S.KIT / "benchmarks" / (name + ".py")
        tree = ast.parse(source.read_text(encoding="utf-8"))
        selected = []
        for node in tree.body:
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                continue
            if isinstance(node, ast.If):
                if name == "capture_validation_facts":
                    selected.append(node)
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "main":
                    continue
                if name == "capture_fixture_support" and node.name not in {
                    "load",
                    "bind_before_coder",
                }:
                    continue
                if (
                    name == "reviewer_observation_accounting"
                    and node.name != "validate_accounting"
                ):
                    continue
                if name in {
                    "reviewer_contract_status_probe",
                    "reviewer_discriminating_status",
                }:
                    continue
            if globals_of(node) & {
                "B",
                "BATCH",
                "CONTROL",
                "SEAL",
                "TARGET",
                "PYTHON",
                "KIT",
                "ORDER",
                "_old_facts",
                "_old_restore",
            }:
                continue
            if name == "reviewer_contract_status_probe" and not (
                globals_of(node) & {"SYSTEM", "TOOLS"}
            ):
                continue
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in DROP_IMPORTS:
                        continue
                    dest = ALIASES.get(alias.name, alias.name)
                    if alias.name in MODULES or alias.name in ALIASES:
                        selected.append(
                            ast.ImportFrom(
                                module=None,
                                names=[ast.alias(dest, alias.asname or alias.name)],
                                level=1,
                            )
                        )
                    else:
                        selected.append(ast.Import(names=[alias]))
                continue
            if isinstance(node, ast.ImportFrom) and node.module in MODULES:
                node.level = 1
            selected.append(node)
        tree.body = selected
        text = ast.unparse(ast.fix_missing_locations(tree)) + "\n"
        if name == "capture_validation_facts":
            old = "from .reviewer_capture_envelope import CaptureRejected, source_manifest"
            assert old in text
            text = text.replace(
                old,
                "if __package__:\n    from .reviewer_capture_envelope import CaptureRejected, source_manifest\nelse:\n    from reviewer_capture_envelope import CaptureRejected, source_manifest",
                1,
            )
        if name == "reviewer_capture_entry":
            text = text.replace(
                "_old_facts(runtime, error)",
                "SEMANTIC.FACTS.facts_unavailable(runtime, error)",
            )
            text = text.replace(
                "_old_restore(runtime, profiles, error)",
                "SEMANTIC.TYPED.restore_unavailable(runtime, profiles, error)",
            )
        target = DEST / (name + ".py")
        target.write_text(text, encoding="utf-8")
        recipes[name] = {
            "from": source.relative_to(S.KIT).as_posix(),
            "original_sha256": S.sha(source),
            "method": "AST mechanical extraction; relative imports; no CLI/historical fixture globals",
        }
    (DEST / "approved_provider.py").write_text(
        '"""No historical sealed-file provider in installed execution."""\n'
        'PROTOCOL = "lossless-typed-observation-input-v1"\n'
        'def facts_unavailable(runtime, error):\n    raise error("Explicit canonical capture policy required")\n'
        'def restore_unavailable(runtime, profiles, error):\n    raise error("Explicit canonical capture policy required")\n'
        "facts = facts_unavailable\nrestore = restore_unavailable\n",
        encoding="utf-8",
    )
    S.save(BATCH / "extraction.json", recipes)
    print("Runtime-only shared package extracted; no default activation or model calls")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("freeze", "extract"))
    p.add_argument("--weekly-used", type=int)
    args = p.parse_args()
    freeze(args.weekly_used) if args.mode == "freeze" else extract()
