"""Audit candidate 6 provenance/cost facts; never grants Primary acceptance."""

from pathlib import Path

import qualification_matrix_v6 as candidate
from capability_fit import write
from inherited_context_recovery import digest, read


def main():
    candidate.configure()
    matrix = candidate.previous.prior.MATRIX
    manifest = matrix.verify()
    frozen = read(candidate.SNAPSHOT / "freeze.json")["files"]
    for path, expected_hash in frozen.items():
        if digest(Path(path)) != expected_hash:
            raise ValueError("production drift: " + path)
    policy = read(candidate.BASE / "presentation-policy.json")
    for path, expected_hash in policy["drivers"].items():
        if digest(Path(path)) != expected_hash:
            raise ValueError("registered driver drift: " + path)
    expected = {
        "explorer_model": "openai/gpt-oss-20b",
        "explorer_context_length": 32768,
        "coder_model": "qwen/qwen3-coder-30b",
        "coder_context_length": 24576,
        "reviewer_model": "meta/muse-glimmer",
        "reviewer_context_length": 24576,
        "single_model_residency": True,
        "coordinator_enabled": False,
        "coder_context_retention": "budgeted",
        "reviewer_context_retention": "budgeted",
        "coder_repair_focus_retention": "latest",
        "explorer_output_limit_recovery": True,
        "explorer_duplicate_action_report_recovery": True,
        "coder_post_edit_validation_hint": True,
    }
    units, explorers, controls = [], [], []
    for cell in manifest["cells"]:
        root = Path(cell["root"])
        config = read(root / ".agent/config.json")
        if any(config[key] != value for key, value in expected.items()):
            raise ValueError("qualification configuration drift: " + cell["id"])
        for unit in cell["units"]:
            invocation = read(root / f".agent/{unit}-unit-invocation.json")
            units.append({"id": cell["id"] + "/" + unit, **invocation})
        if cell["explorer_required"]:
            invocation = read(root / ".agent/explorer-invocation.json")
            explorers.append({"id": cell["id"], **invocation})
    for cell in candidate.previous.prior.CONTROLS.verify()["controls"]:
        invocation = read(Path(cell["root"]) / ".agent/reviewer-invocation.json")
        controls.append({"id": cell["id"], **invocation})
    facts = {
        "production_files_match_snapshot": len(frozen),
        "registered_drivers_match": len(policy["drivers"]),
        "configuration_cells_match": len(manifest["cells"]),
        "qualified_configuration": expected,
        "invocations": {"units": units, "explorers": explorers, "controls": controls},
        "invocation_seconds": {
            key: sum(row["seconds"] for row in rows)
            for key, rows in (
                ("units", units),
                ("explorers", explorers),
                ("controls", controls),
            )
        },
        "seconds_interpretation": "Outer local invocation elapsed, includes model loading and runtime checks; not full experiment elapsed or Primary active time.",
        "cloud_tokens": None,
        "primary_active_seconds": None,
        "model_loading_seconds_separately": None,
        "qualification_credit": False,
        "primary_acceptance_not_inferred": True,
        "audit_driver_sha256": digest(Path(__file__)),
    }
    write(candidate.BASE / "primary-release-facts-1.json", facts)
    print({key: value for key, value in facts.items() if key != "invocations"})


if __name__ == "__main__":
    main()
