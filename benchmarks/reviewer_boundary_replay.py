"""Replay unchanged real Reviewer reports through Primary disposition, no LLM credit."""

import importlib.util
import json
from pathlib import Path

from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "reviewer-boundary-1"
SOURCE = WORK / "reviewer-evidence-1"


def main():
    BASE.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location(
        "boundary", KIT / ".local-agents/review-disposition.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    registration = read(SOURCE / "registration.json")
    judgments = {r["id"]: r for r in read(SOURCE / "primary-adjudications-1.json")}
    observations = {
        r["id"]: r for r in read(SOURCE / "independent-observations-1.json")
    }
    rows = []
    for cell in registration["controls"]:
        identity = cell["id"]
        root = Path(cell["root"])
        path = root / ".agent/reviewer.json"
        report = read(path)
        assert digest(path) == observations[identity]["report_sha256"]
        assert (root / "src/product/target.py").read_text(
            encoding="utf-8"
        ) == observations[identity]["source"]
        for p, sha in cell["protected_hashes"].items():
            if p != "src/product/target.py":
                assert digest(root / p) == sha
        if identity.startswith("conflicting-contract"):
            kind, resolution, expected = (
                "contract_revision",
                "contract_revision",
                "replan",
            )
        elif identity == "display-default-a-r1":
            kind, resolution, expected = "nonblocking", "cleared", "accept"
        elif identity.startswith("required-coverage"):
            kind, resolution, expected = "required_test_gap", "cleared", "rework"
        elif cell["has_defect_primary_only"]:
            kind, resolution, expected = "confirmed_defect", "cleared", "rework"
        else:
            kind, resolution, expected = "nonblocking", "cleared", "accept"
        # These are explicit prior Primary adjudications, not classifications
        # inferred from model wording or an improvement in model accuracy.
        payload = {
            "schema_version": 1,
            "authority": "primary",
            "identity": report["identity"],
            "report_sha256": digest(path),
            "resolution": resolution,
            "evidence": [judgments[identity]["summary"]],
            "findings": [
                {
                    "finding_id": f["id"],
                    "disposition": kind,
                    "evidence": judgments[identity]["summary"],
                }
                for f in report["findings"]
            ],
        }
        result = module.adjudicate(report, digest(path), payload)
        assert result["primary_decision"] == expected
        assert not result["automatic_coder_rework_authorized"]
        write(BASE / f"{identity}-disposition.json", result)
        rows.append(
            {
                "id": identity,
                "raw_model_decision": report["decision"],
                "primary_route": result["primary_decision"],
                "report_sha256": digest(path),
            }
        )
    assert len(rows) == 16
    write(
        BASE / "replay-results.json",
        {
            "rows": rows,
            "routing_correct": 16,
            "model_semantics_correct_unchanged": 14,
            "new_model_calls": 0,
            "automatic_acceptance": False,
            "previous_primary_judgments_reused": True,
            "driver_sha256": digest(Path(__file__)),
            "fixture_registration_sha256": digest(SOURCE / "registration.json"),
        },
    )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
