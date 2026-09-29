"""Try the frozen sample-identity feature as two cohesive local units.

The source repositories are only read by stability_e2e.prepare(). Every run
uses a fresh copied workspace and retains its own .agent evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from stability_e2e import CASES, KIT, WORK, prepare, run_command, write_json


def packet_for_unit(base: dict, *, fingerprint: bool, task_id: str) -> dict:
    packet = json.loads(json.dumps(base))
    packet["task_id"] = task_id
    packet["feature_id"] = task_id
    packet["unit_id"] = "fingerprint" if fingerprint else "score-reuse"
    packet["run_id"] = f"{packet['unit_id']}-a1"
    packet["goal"] = (
        "Restore content_fingerprint's existing volatile-field exclusion, "
        "including sample_id and source_metadata, without changing the field set."
        if fingerprint
        else "Restore score_reuse_key's sample_id-only exclusion while retaining "
        "source_metadata as scoring input and deterministic effective_config."
    )
    packet["dependencies"] = [] if fingerprint else ["fingerprint"]
    packet["owned_contract_ids"] = ["behavior-1" if fingerprint else "behavior-2"]
    packet["scope"]["modify"] = [
        "src/evaluation_harness/canonical/fingerprint.py"
        if fingerprint
        else "src/evaluation_harness/evaluations/dedup.py"
    ]
    packet["edit_targets"] = [base["edit_targets"][0 if fingerprint else 1]]
    packet["required_behavior"] = [
        {
            "id": packet["owned_contract_ids"][0],
            "text": (
                "content_fingerprint excludes the unchanged existing "
                "VOLATILE_CONTENT_FIELDS set from CanonicalSample serialization. "
                "That set includes sample_id and source_metadata."
                if fingerprint
                else "score_reuse_key excludes only sample_id from the sample "
                "dump; source_metadata and other scoring inputs remain in the "
                "payload, whose schema/scorer/config and hash shape are preserved."
            ),
            "risk_floor": "medium",
        }
    ]
    packet["acceptance_scenarios"] = [
        {
            "id": "scenario-fingerprint" if fingerprint else "scenario-score-reuse",
            "text": (
                "Changing sample_id leaves the content fingerprint unchanged."
                if fingerprint
                else "Changing sample_id does not change the reuse key; changing "
                "source_metadata does, and effective_config mapping order does not."
            ),
            "observables": {"protected_test_assertion": True},
        }
    ]
    packet["implementation_guidance"] = [
        (
            "CanonicalSample has a sample_id field and no row_identity field. "
            "The targeted model_dump is one line. Preserve all other source lines."
        )
    ]
    packet["focused_tests"] = [
        "tests/test_sample_identity.py::test_content_fingerprint_ignores_existing_volatile_fields"
        if fingerprint
        else "tests/test_sample_identity.py"
    ]
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=KIT / ".local-agents/config.json"
    )
    args = parser.parse_args()
    case = next(case for case in CASES if case.name == "sample-identity")
    source_config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    root = WORK / f"sample-identity-decomposed-{uuid.uuid4().hex[:12]}"
    config_path, base_path = prepare(case, root, source_config)
    base = json.loads(base_path.read_text(encoding="utf-8"))
    task_id = "stability-sample-identity-decomposed"
    results = []
    for fingerprint in (True, False):
        packet = packet_for_unit(base, fingerprint=fingerprint, task_id=task_id)
        packet_path = root / ".agent" / f"packet-{packet['unit_id']}.json"
        write_json(packet_path, packet)
        result = run_command(
            root,
            [
                sys.executable,
                str(root / ".local-agents/local-unit.py"),
                "--packet",
                str(packet_path),
                "--config",
                str(config_path),
            ],
            1200,
        )
        try:
            handoff = json.loads(result.stdout)
        except ValueError:
            handoff = {"output_tail": (result.stdout + result.stderr)[-1000:]}
        results.append(
            {
                "unit_id": packet["unit_id"],
                "exit_code": result.returncode,
                "handoff": handoff,
            }
        )
        write_json(
            root / "decomposition-result.json",
            {"workspace": str(root), "units": results},
        )
        if (
            result.returncode != 0
            or handoff.get("reviewer_decision") != "pass_to_primary"
        ):
            print(
                json.dumps(
                    {"workspace": str(root), "units": results}, ensure_ascii=False
                )
            )
            return 2
    independent = {
        name: run_command(root, argv, 90)
        for name, argv in {
            "pytest": [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_sample_identity.py",
                "-q",
            ],
            "format": [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "src",
                "tests",
            ],
            "lint": [sys.executable, "-m", "ruff", "check", "src", "tests"],
        }.items()
    }
    summary = {
        "workspace": str(root),
        "units": results,
        "integration": {
            name: {
                "passed": result.returncode == 0,
                "output_tail": result.stdout[-500:],
            }
            for name, result in independent.items()
        },
    }
    write_json(root / "decomposition-result.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if all(result.returncode == 0 for result in independent.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
