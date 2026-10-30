"""Offline diagnostics of observed rejected payloads; never a live result.

Exact function assembly is a diagnostic hypothesis, not an enabled production
decoder. No reference implementation or semantic edits are used.
"""

import ast
import hashlib
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import normal_task_trial as N
import preserved_import_guard as G


def main():
    out = N.BATCH / "payload-diagnostic"
    payloads = {}
    for cell in ("single_content-1", "single_content-2"):
        row = S.read(N.BATCH / "cells.json")[cell]
        archive = (
            Path(row["root"])
            / ".agent/tasks"
            / row["identity"]["task_id"]
            / "runs"
            / row["identity"]["run_id"]
        )
        for path in sorted(archive.glob("proposal-response-*.json")):
            response = S.read(path)
            value = __import__("json").loads(response["raw"])["replacement"]
            digest = hashlib.sha256(value.encode()).hexdigest()
            payloads.setdefault(digest, {"text": value, "evidence": []})[
                "evidence"
            ].append(str(path))
    results = []
    for index, (digest, item) in enumerate(payloads.items(), 1):
        # Actual payloads already contain normal newlines. Do not unescape code.
        raw = item["text"]
        if "\n" not in raw:
            raise ValueError(
                "Unexpected payload form; manual diagnostic decision required"
            )
        normalized = raw
        tree = ast.parse(normalized)
        if (
            len(tree.body) != 1
            or not isinstance(tree.body[0], ast.FunctionDef)
            or tree.body[0].name != "parse_message"
        ):
            raise ValueError("Not exactly the observed target function")
        row_path = out / f"payload-{index}" / "prepared-row.json"
        if row_path.exists():
            row = S.read(row_path)
        elif (out / f"payload-{index}" / "isolated").exists():
            # Recover metadata of first diagnostic's already-applied source;
            # do not replay or overwrite its original process/failure evidence.
            root = out / f"payload-{index}" / "isolated"
            row = {
                "root": str(root),
                "target": "src/evaluation_harness/adapters/common.py",
                "private_tests": str(
                    N.OLD / "private/single_content/test_private_single_content.py"
                ),
            }
        else:
            row = N.prepare_cell(
                "single_content", out / f"payload-{index}", f"payload-{index}"
            )
            S.save(row_path, row)
        root = Path(row["root"])
        source = (root / row["target"]).read_text(encoding="utf-8-sig")
        target = next(
            node
            for node in ast.parse(source).body
            if isinstance(node, ast.FunctionDef) and node.name == "parse_message"
        )
        lines = source.splitlines(keepends=True)
        module = (
            "".join(lines[: target.lineno - 1])
            + normalized.rstrip("\n")
            + "\n"
            + "".join(lines[target.end_lineno :])
        )
        G.guard(source, module, "parse_message", set())
        replay = root.parent / "reconstructed-replay.json"
        process_path = root.parent / "entry-process.json"
        if not process_path.exists():
            S.save(
                replay,
                [
                    {"replacement": module},
                    {
                        "blocked_reason": "End of scripted observed-payload diagnostic; no additional proposal available"
                    },
                ],
            )
            command = T.run(N.command(root, replay=replay), root, timeout=180)
            S.save(process_path, command)
        command = S.read(process_path)
        private_path = root.parent / "independent-private-check.json"
        if not private_path.exists():
            private = T.run(
                [S.PYTHON, "-B", "-m", "pytest", "-q", "tests", row["private_tests"]],
                root,
                timeout=120,
            )
            S.save(private_path, private)
        private = S.read(private_path)
        report_path = root / ".agent/unit-report.json"
        report = S.read(report_path) if report_path.exists() else {}
        profile = []
        for name, argv in (
            (
                "format",
                [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
            ),
            ("lint", [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"]),
            ("types", [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON]),
            (
                "observations",
                [
                    S.PYTHON,
                    "-B",
                    root / "acceptance/capture_validation_facts.py",
                    "--policy",
                    "acceptance/capture-policy.json",
                ],
            ),
        ):
            path = root.parent / (name + "-check.json")
            if not path.exists():
                S.save(path, T.run(argv, root, timeout=120))
            profile.append(S.read(path))
        results.append(
            {
                "payload_sha256": digest,
                "observed_at": item["evidence"],
                "transformations": [
                    "assemble exact function into unchanged registered module",
                ],
                "semantic_edits": 0,
                "reference_used": False,
                "model_calls": 0,
                "entry_exit": command["exit_code"],
                "entry_status": report.get(
                    "status", "SCRIPTED_REPLAY_EXHAUSTED_AFTER_CHECK_FAILURE"
                ),
                "scripted_ledger": (report.get("consolidated_harness") or {}).get(
                    "actual"
                ),
                "private_exit": private["exit_code"],
                "private_stdout": private["stdout"],
                "configured_check_exits": [c["exit_code"] for c in profile],
                "all_checks_pass": private["exit_code"] == 0
                and all(c["exit_code"] == 0 for c in profile),
                "Reviewer_semantic": "NOT_RUN",
                "live_acceptance_credit": 0,
            }
        )
    S.save(
        out / "decision.json",
        {
            "status": "OFFLINE_OBSERVED_PAYLOAD_DIAGNOSTIC",
            "observed_responses": sum(len(i["evidence"]) for i in payloads.values()),
            "unique_payloads": len(payloads),
            "results": results,
            "limits": "Success would show observed function content can satisfy fixed checks after diagnostic reconstruction, not prove a safe general decoder, model recovery, or fresh Reviewer pass. No live score changes.",
        },
    )
    print([(r["entry_status"], r["private_exit"]) for r in results])


if __name__ == "__main__":
    main()
