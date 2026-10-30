"""Offline only: audit every unique B patch, including protocol-rejected payloads."""

import ast
import json
import shutil
from pathlib import Path

import behavior_unit_candidate as GUARD
import bounded_evidence_support as S
import bounded_evidence_tasks as T
from behavior_unit_close import BATCH


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def main():
    cells = S.read(BATCH / "cells.json")
    seen = {}
    origins = []
    for cell, row in cells.items():
        if row["arm"] != "B":
            continue
        root = Path(row["root"])
        packet = S.read(root / ".agent/packet.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        config = S.read(root / ".agent/config.json")
        symbol = config["coder_single_function"]["symbol"]
        allowed = {tuple(p) for p in config["experimental_approved_imports"]}
        template = BATCH / "templates" / row["task"]
        initial = (template / "src/product/code.py").read_text(encoding="utf-8")
        for path in sorted(archive.glob("proposal-response-*.json")):
            try:
                data = json.loads(S.read(path)["raw"], object_pairs_hook=unique)
                source = data["replacement"]
                GUARD.guard(initial, source, symbol, allowed)
                shape = ast.dump(ast.parse(source))
            except (KeyError, ValueError, TypeError, SyntaxError):
                origins.append(
                    {
                        "cell": cell,
                        "response": path.name,
                        "status": "NOT_SAFE_PARSEABLE_MODULE",
                    }
                )
                continue
            key = (row["task"], shape)
            if key not in seen:
                number = len(seen) + 1
                target = BATCH / "offline-payload-replay" / str(number)
                shutil.copytree(template, target)
                (target / "src/product/code.py").write_text(source, encoding="utf-8")
                before = ast.dump(
                    ast.parse(
                        (target / "src/product/code.py").read_text(encoding="utf-8")
                    )
                )
                formatted = T.run(
                    [S.PYTHON, "-B", "-m", "ruff", "format", "src/product/code.py"],
                    target,
                )
                after = ast.dump(
                    ast.parse(
                        (target / "src/product/code.py").read_text(encoding="utf-8")
                    )
                )
                assert before == after and formatted["exit_code"] == 0
                checks = [
                    T.run(cmd, target)
                    for cmd in (
                        [
                            S.PYTHON,
                            "-B",
                            "-m",
                            "pytest",
                            "-q",
                            "tests",
                            row["private_tests"],
                        ],
                        [
                            S.PYTHON,
                            "-B",
                            "-m",
                            "ruff",
                            "format",
                            "--check",
                            "src",
                            "tests",
                        ],
                        [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
                        [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON],
                    )
                ]
                record = {
                    "id": number,
                    "task": row["task"],
                    "source_sha256": S.sha(target / "src/product/code.py"),
                    "source_origin": str(path),
                    "trusted_format_only": formatted,
                    "checks": checks,
                    "all_pass": all(c["exit_code"] == 0 for c in checks),
                    "model_calls": 0,
                    "live_acceptance_credit": False,
                }
                S.save(target / "checks.json", record)
                seen[key] = record
            origins.append(
                {
                    "cell": cell,
                    "response": path.name,
                    "json_keys": sorted(data),
                    "unique_patch": seen[key]["id"],
                }
            )
    S.save(
        BATCH / "offline-payload-replay/decision.json",
        {
            "unique_safe_ast_patches": len(seen),
            "all_check_pass_patches": sum(r["all_pass"] for r in seen.values()),
            "patches": list(seen.values()),
            "all_response_origins": origins,
            "model_calls": 0,
            "historical_scores_changed": False,
            "interpretation": "This audits observed payloads only. Formatting and extracting a replacement for inspection do not demonstrate the next unobserved repair would fail or succeed. No previously rejected payload is promoted to live acceptance.",
        },
    )
    print(
        "Unique safe AST patches",
        len(seen),
        "all-check pass",
        sum(r["all_pass"] for r in seen.values()),
    )


if __name__ == "__main__":
    main()
