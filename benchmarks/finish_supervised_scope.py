"""Aggregate immutable evidence and restore the initial empty residency."""

import json
from pathlib import Path

import supervised_scope_check as experiment
from capability_fit import load_worker, write
from inherited_context_recovery import read


def guard_reviewer(screen, model):
    items = screen.residents()
    if (
        len(items) != 1
        or items[0]["identifier"] != model
        or items[0]["status"] != "idle"
        or items[0]["queued"] != 0
    ):
        raise ValueError("expected only idle configured Reviewer; refuse unload")


def finish():
    manifest = experiment.verify()
    units = []
    seconds = 0
    for cell in manifest["cells"]:
        root = Path(cell["root"])
        packet = read(root / ".agent/qual-unit-reference.json")
        run = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        decision = read(run / "review.json")["decision"]
        checks = read(root / ".agent/primary-checks.json")
        seconds += read(root / ".agent/unit-invocation.json")["seconds"]
        explorer_path = root / ".agent/explorer-invocation.json"
        if explorer_path.exists():
            seconds += read(explorer_path)["seconds"]
        units.append(
            {
                "id": cell["id"],
                "primary": decision,
                "all_checks": checks["all_checks_pass"],
                "tests_executed": checks["tests_executed"],
            }
        )
    controls = []
    for cell in manifest["controls"]:
        root = Path(cell["root"])
        report = read(root / ".agent/reviewer.json")
        observed = read(root / ".agent/primary-boundary-observation.json")
        controls.append(
            {
                "id": cell["id"],
                "has_defect": cell["has_defect_primary_only"],
                "reviewer": report["decision"],
                "boundary_correct": observed["boundary_correct"],
            }
        )
    config = read(experiment.SNAPSHOT / ".local-agents/config.json")
    worker = load_worker(experiment.SNAPSHOT)
    model = config["reviewer_model"]
    screen = experiment.TYPED.PRIOR.SCREEN
    guard_reviewer(screen, model)
    client = worker.LMStudioClient(
        config["lmstudio_base_url"],
        model,
        600,
        context_length=config["reviewer_context_length"],
    )
    with worker.MODEL_RESIDENCY.role_model_lease(client, config):
        guard_reviewer(screen, model)
        instance = screen.loaded_config(model)
        write(
            experiment.BASE / "final-unloaded.json",
            experiment.FA.api("/unload", {"instance_id": instance["id"]}),
        )
        if screen.residents():
            raise ValueError("residency not empty")
    assessment = {
        "units": units,
        "primary_accepted": sum(x["primary"] == "accept" for x in units),
        "explorer_independent_success": 2,
        "explorer_invocations": 2,
        "controls": controls,
        "clean_passes": sum(
            not c["has_defect"] and c["reviewer"] == "pass_to_primary" for c in controls
        ),
        "hidden_effective_detections": sum(
            c["has_defect"] and c["reviewer"] == "rework" and not c["boundary_correct"]
            for c in controls
        ),
        "unit_plus_explorer_seconds": seconds,
        "primary_implementation_takeovers": 0,
        "primary_active_seconds": None,
        "cloud_tokens": None,
        "cost_saving_proven": False,
        "classification": "Known-family supervised scope evidence, not full qualification",
        "coordinator_released": False,
        "production_changes": False,
        "final_residency": [],
    }
    write(experiment.BASE / "primary-assessment-1.json", assessment)
    print(json.dumps(assessment))


if __name__ == "__main__":
    finish()
