"""Validate documented minimal configuration against frozen installed runtime."""

import os
import shutil

import bounded_evidence_support as S
import project_caller_trial as J
import strata_release_matrix as M
from strata_native_trial import command

BATCH = M.BATCH.parent / "strata-doc-example-20261023-3"


def main():
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    seed = M.BATCH / "cells/raw-1/isolated"
    root = BATCH / "isolated"
    J.copy_project(M.origin("raw") / "templates/raw", root)
    shutil.copytree(seed / ".local-agents", root / ".local-agents")
    packet = S.read(seed / ".agent/packet.json")
    packet.update({k: BATCH.name for k in ("task_id", "unit_id", "run_id")})
    packet["validation_profile"] = "project-strict"
    cfg = S.read(S.KIT / "examples/strata-preview/config.example.json")
    cfg.update(
        python=str(S.PYTHON),
        strata_node_path="F:/Strata/node/node.exe",
        strata_harness_root="F:/Strata/harness",
        coder_single_function={
            "path": packet["scope"]["modify"][0],
            "symbol": "mapping_raw",
            "dependencies": cfg["coder_single_function"]["dependencies"],
        },
    )
    cfg["validation_profiles"]["project-strict"]["python"] = str(S.PYTHON)
    # Preserve this project's existing wider formatter/linter scope.
    for check in cfg["validation_profiles"]["project-strict"]["commands"][:2]:
        check["argv"].extend(["examples", "scripts"])
    for name, value in (
        ("packet", packet),
        ("config", cfg),
        ("spec", S.read(seed / ".agent/spec.json")),
    ):
        S.save(root / f".agent/{name}.json", value)
    result = command(
        [
            S.PYTHON,
            "-B",
            root / ".local-agents/local-bounded-prepare.py",
            "--packet",
            ".agent/packet.json",
            "--config",
            ".agent/config.json",
            "--capture-spec",
            ".agent/spec.json",
            "--apply",
        ],
        root,
    )
    S.save(BATCH / "prepare.json", result)
    assert result["exit_code"] == 0, result
    target = packet["scope"]["modify"][0]
    S.save(
        BATCH / "frontend.json",
        {
            "mode": "control",
            "actions": [
                {
                    "name": "kit_propose",
                    "arguments": {
                        "path": target,
                        "expected_sha256": "@current",
                        "content": J.function_source(
                            M.origin("raw") / "references/raw" / target, "mapping_raw"
                        ),
                    },
                }
            ],
        },
    )
    prepared = root / ".agent/prepared" / packet["run_id"]
    result = command(
        [
            S.PYTHON,
            "-B",
            root / ".local-agents/strata/strata_native_host_v4.py",
            "--packet",
            prepared / "packet.json",
            "--config",
            prepared / "config.json",
            "--program",
            BATCH / "frontend.json",
        ],
        root,
        timeout=180,
    )
    S.save(BATCH / "process.json", result)
    summary = S.read(root / ".agent/native-host-summary.json")
    assert (
        result["exit_code"] == 0
        and summary["host_handoff_verified"]
        and summary["provider_calls"] == 0
    ), result
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_DOCUMENTED_CONFIG_OFFLINE",
            "real_llm_calls": 0,
            "production_acceptance": False,
            "example_sha256": S.sha(
                S.KIT / "examples/strata-preview/config.example.json"
            ),
            "summary": summary,
        },
    )
    print(
        "PASS documented minimal config, existing wide project checks preserved, real host;0 model"
    )


if __name__ == "__main__":
    main()
