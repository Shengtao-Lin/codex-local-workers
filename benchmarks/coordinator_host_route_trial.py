"""Two fixed proposals for default-off host routing, then conditional chain only."""

import argparse
import time
from pathlib import Path

import coordinator_host_route as H

R, S = H.R, H.R.S
BATCH = R.D.I.BASE / "coordinator-host-route-20261022-1"
ORDER = ["one", "two"]


def prepare(used):
    assert not BATCH.exists()
    S.save(
        BATCH / "preparation.json",
        {
            "authority": "Current autonomous isolated iteration, no weekly cap; no defaults changed",
            "offline_first_attempt": "20 behavior controls passed; seven lint issues in new adapter/tests, corrected before candidate freeze. No model calls during preparation.",
            "basis": "Identical catalog-augmented request routed local2/2 in earlier A/B but Primary in conditional chain; decomp correct in all. Retain both historical outcomes, no routing resampling.",
        },
    )
    data = S.read(R.BATCH / "inputs-B.json")
    binding = H.bind_catalog(data["brief"], S.read(R.SOURCE / "catalog.json"))
    S.save(BATCH / "input.json", data)
    S.save(BATCH / "binding.json", binding)
    tests = [
        "benchmarks/test_coordinator_host_route.py",
        ".local-agents/tests/test_coordinator_brief.py",
    ]
    checks = [
        R.D.T.run(args, S.KIT, timeout=120)
        for args in (
            [
                S.PYTHON,
                "-B",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                *tests,
                "--basetemp=C:/Users/Lin/.codex/local-workers/coordinator-host-route-20261022-control2",
            ],
            [
                S.PYTHON,
                "-B",
                "-m",
                "ruff",
                "check",
                str(Path(H.__file__)),
                tests[0],
                str(Path(__file__)),
            ],
        )
    ]
    S.save(BATCH / "offline-controls.json", checks)
    assert all(c["exit_code"] == 0 for c in checks), checks
    paths = [
        Path(__file__),
        Path(H.__file__),
        S.KIT / tests[0],
        Path(R.__file__),
        BATCH / "input.json",
        BATCH / "binding.json",
        *list((S.KIT / ".local-agents").rglob("*.py")),
    ]
    S.save(
        BATCH / "registration.json",
        {
            "candidate": "Model DTO omits owner; host assigns suggested owner only from Primary catalog bound to exact full brief and existing validator. Raw decomposition, materialized proposal and routing reasons separate. No approval/dispatch by this adapter.",
            "registered": 2,
            "order": ORDER,
            "model": "meta/muse-glimmer Q4_K_M24576 low temp0.1 output4096; one resident; same existing config",
            "budget": "max2requests each solely for protocol correction;360s/request;batch3600s; no semantic reroll",
            "gate": "Both proposals independently reviewed: valid exact two high-risk units/paths/contracts/dependency, no invented owner or scope; host matches both qualified routes. 2/2 permits one separately frozen same-real-package full chain, not production promotion.",
            "continuation": "Complete ordinary unresolved/protocol/model outcomes in order; halt infrastructure/drift/safety/time/user stop. No replacement cells. Any ordinary failure HOLD, downstream chain NOT_RUN.",
            "qualification": "Only known detailed brief, no new behavior or broad planning credit; Primary supplied contracts, exact refs, tests, risk and edge. Owner determinism is a host property, not model intelligence.",
            "primary_cost": "Adapter development/control preparation one-time; per-task Primary still vets evidence/catalog, contracts/tests/classification and complete proposal. Active time/cloud tokens unknown.",
            "weekly_used_start": used,
            "weekly_limit": None,
            "pins": {str(p): S.sha(p) for p in paths if "__pycache__" not in p.parts},
        },
    )
    print("Two host-routed proposals frozen after offline controls", flush=True)


def run(cell, used):
    reg = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    if cell == "two":
        assert not S.read(BATCH / "one/result.json")["infrastructure_failure"]
    clock = BATCH / "start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    assert time.time() - S.read(clock)["epoch"] < 3600
    root = BATCH / cell
    S.save(root / "start.json", {"epoch": time.time(), "weekly_used": used})
    data = S.read(BATCH / "input.json")
    config = S.read(R.D.L.SEED / ".agent/config.json")
    client = R.W.LMStudioClient(
        config["lmstudio_base_url"],
        config["coordinator_model"],
        timeout=360,
        max_tokens=4096,
        temperature=0.1,
        structured_output=False,
        context_length=24576,
    )
    client.reasoning_effort = "low"
    started = time.monotonic()
    try:
        with R.W.MODEL_RESIDENCY.role_model_lease(client, config):
            client.preflight()
            result = H.probe(
                data["brief"],
                data["context"],
                R.CaptureClient(client, root),
                S.read(BATCH / "binding.json"),
            )
    except Exception as exc:
        S.save(
            root / "result.json", {"infrastructure_failure": True, "error": str(exc)}
        )
        raise
    S.save(root / "proposal.json", result)
    S.save(
        root / "result.json",
        {
            "infrastructure_failure": False,
            "status": result["status"],
            "seconds": time.monotonic() - started,
            "requests": len(result["attempts"]),
            "primary_review": "PENDING",
        },
    )
    print(cell, result["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        run(args.cell, args.weekly_used)
