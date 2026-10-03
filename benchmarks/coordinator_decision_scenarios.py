"""Evidence-aligned Coordinator choices; no synthetic unsafe enum injection."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import uuid
from pathlib import Path

from coordinator_qualification import KIT, fingerprints, write_once


def main() -> int:
    original = json.loads((KIT / ".local-agents/example-feature-plan.json").read_text())
    # An independent documentation feature, not a weakening of lease finalization.
    documentation = copy.deepcopy(original)
    documentation["feature_id"] = "coordinator-documentation-scenario"
    documentation["units"] = [documentation["units"][-1]]
    documentation["units"][0]["dependencies"] = []
    documentation["contracts"] = [documentation["contracts"][-1]]
    scenarios = [
        ("eligible-documentation", documentation, "CONTINUE", "lease-documentation"),
        (
            "primary-dependency-pending",
            original,
            "ESCALATE_PRIMARY",
            "lease-test-support",
        ),
    ]
    root = (
        KIT
        / ".agent/coordinator-qualification"
        / f"muse-scenarios-{uuid.uuid4().hex[:12]}"
    )
    root.mkdir(parents=True)
    frozen = fingerprints()
    frozen["scenario_runner"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    write_once(root / "freeze.json", frozen)
    write_once(root / "run-refs.json", {})
    outcomes = []
    for name, plan, expected_choice, expected_unit in scenarios:
        folder = root / name
        folder.mkdir()
        plan_path, context_path, report_path = (
            folder / filename
            for filename in ("plan.json", "context.json", "report.json")
        )
        write_once(plan_path, plan)
        write_once(
            context_path,
            {
                "question": "Inspect Primary's plan and runtime_execution. Choose the next appropriate "
                "closed-enum decision from verified acceptance and eligibility facts. "
                "Do not invent accepted units or feature completion. This is a read-only "
                "decision scenario, not authorization to launch any worker.",
            },
        )
        run = subprocess.run(
            [
                sys.executable,
                str(KIT / ".local-agents/coordinator-runtime.py"),
                "--plan",
                str(plan_path),
                "--context",
                str(context_path),
                "--mode",
                "decision",
                "--check-transition",
                "--run-refs",
                str(root / "run-refs.json"),
                "--state",
                str(folder / "state.json"),
                "--report",
                str(report_path),
            ],
            cwd=KIT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=900,
            check=False,
        )
        report = json.loads(report_path.read_text()) if report_path.is_file() else {}
        current = fingerprints()
        current["scenario_runner"] = hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest()
        choice = report.get("output", {})
        passed = (
            run.returncode == 0
            and report.get("status") == "transition_valid"
            and choice.get("decision") == expected_choice
            and choice.get("unit_id") == expected_unit
            and current == frozen
            and not (folder / "state.json").exists()
        )
        outcome = {
            "scenario": name,
            "passed": passed,
            "output": choice,
            "status": report.get("status"),
            "model_turns": report.get("model_turns"),
        }
        if not report:
            outcome["output_tail"] = (run.stdout + run.stderr)[-1000:]
        outcomes.append(outcome)
        print(json.dumps(outcome), flush=True)
        if not passed:
            break
    result = {
        "passed": len(outcomes) == len(scenarios)
        and all(item["passed"] for item in outcomes),
        "outcomes": outcomes,
        "qualification_scope": "two_readonly_decision_scenarios",
        "full_role_qualified": False,
        "dispatch_allowed": False,
    }
    write_once(root / "result.json", result)
    print(json.dumps({"root": str(root), "passed": result["passed"]}), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
