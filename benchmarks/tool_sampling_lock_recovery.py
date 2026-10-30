"""Retry only an infrastructure launch that reached no Reviewer model turn."""

from capability_fit import KIT, write
from inherited_context_recovery import read
from layer_isolation import command, verify_hashes
from tool_awaitable_trial import PYTHON, TARGET
from tool_reviewer_sampling_trial import ADAPTER, ARTIFACTS, BASE, SNAPSHOT


def run():
    arm = "clean-control-1"
    previous = read(BASE / (arm + ".report.json"))
    if previous.get("infra_failure", {}).get("reason_code") != "model_switch_lock_held":
        raise ValueError("not the registered no-model infrastructure failure")
    root = ARTIFACTS["clean"][0]
    inputs = read(BASE / (arm + ".inputs.json"))
    verify_hashes(root, {TARGET: inputs["source_sha256"]})
    verify_hashes(BASE, inputs["files"])
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    verify_hashes(KIT / "benchmarks", read(BASE / "registration.json")["files"])
    request = read(BASE / (arm + ".request.json"))
    review_root = (
        root / ".agent/tasks" / request["task_id"] / "reviews" / request["review_id"]
    )
    if review_root.exists():
        raise ValueError("previous runtime archive exists: no retry allowed")
    write(
        BASE / "clean-control-1.after-lock-registration.json",
        {
            "reason": "Same bounded call after verified dead PID 37264 and idle model, exact stale residency lock archived rather than deleted. Original failed report retained. Prior lease failed before runtime initialization/model turn.",
            "actual_order_deviation": "candidate-1 began before recovered control-1; actual order retained, not falsely called counterbalanced",
            "driver_sha256": __import__("inherited_context_recovery").digest(
                KIT / "benchmarks/tool_sampling_lock_recovery.py"
            ),
        },
    )
    invoked = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(KIT / "benchmarks" / ADAPTER),
            "--snapshot",
            str(SNAPSHOT),
            "--request",
            str(BASE / (arm + ".request.json")),
            "--config",
            str(BASE / (arm + ".config.json")),
            "--report",
            str(BASE / (arm + ".after-lock-report.json")),
        ],
        timeout=900,
    )
    write(BASE / "clean-control-1.after-lock-invocation.json", invoked)
    print(
        {
            "decision": read(BASE / "clean-control-1.after-lock-report.json")[
                "decision"
            ],
            "seconds": invoked["seconds"],
        }
    )


if __name__ == "__main__":
    run()
