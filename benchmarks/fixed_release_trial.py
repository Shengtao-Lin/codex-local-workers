"""Fixed release trial entrypoint: immutable registration and isolated CLI gate."""

import argparse
import json
import time
import urllib.request

from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes

BASE = WORK / "fixed-release-1"
SNAPSHOT = WORK / "fixed-release-runtime-1"


def prepare():
    BASE.mkdir(exist_ok=False)
    freeze(SNAPSHOT.name)
    config = read(SNAPSHOT / ".local-agents/config.json")
    config.update(
        model_load_backend="cli",
        model_load_cli_path="C:/Users/Lin/.lmstudio/bin/lms.exe",
    )
    write(BASE / "cli-config.json", config)
    write(
        BASE / "registration.json",
        {
            "plan": "docs/fixed-release-decision-plan.md",
            "plan_sha256": digest(KIT / "docs/fixed-release-decision-plan.md"),
            "driver_sha256": digest(KIT / "benchmarks/fixed_release_trial.py"),
            "config_sha256": digest(BASE / "cli-config.json"),
            "weekly_used_start": 40,
            "weekly_used_ceiling": 50,
            "fixed_cases": ["display-default", "label-rollup", "async-receipt"],
            "repetitions": 2,
            "loading_cycles": 3,
            "loading_successes_required": 9,
            "complete_chains_required": 5,
            "dependent_chains_required": 2,
            "blind_controls_required": 8,
            "primary_production_edits_allowed": 0,
            "max_external_rework_packets_per_chain": 1,
            "max_assisted_explorer_recovery_per_investigation": 1,
            "candidate_limit": 2,
            "same_failure_streak_stop": 2,
        },
    )
    print("Frozen plan, candidate and CLI config", flush=True)


def verify():
    reg = read(BASE / "registration.json")
    for path, key in (
        (KIT / reg["plan"], "plan_sha256"),
        (KIT / "benchmarks/fixed_release_trial.py", "driver_sha256"),
        (BASE / "cli-config.json", "config_sha256"),
    ):
        if digest(path) != reg[key]:
            raise ValueError("registered input drift: " + str(path))
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])


def load_cycle(cycle):
    verify()
    worker = load_worker(SNAPSHOT)
    residency = worker.MODEL_RESIDENCY
    config = read(BASE / "cli-config.json")
    url = config["lmstudio_base_url"]
    rows = []
    for role in ("explorer", "coder", "reviewer"):
        output = BASE / f"load-{cycle}-{role}.json"
        if output.exists():
            raise FileExistsError("historical load cannot be replayed")
        model, length = config[f"{role}_model"], config[f"{role}_context_length"]
        client = worker.LMStudioClient(url, model, context_length=length)
        started = time.monotonic()
        row = {"cycle": cycle, "role": role, "model": model, "context": length}
        try:
            with residency.role_model_lease(client, config):
                row["switch_seconds"] = time.monotonic() - started
                for phase in ("before", "after"):
                    loaded = residency._loaded(
                        residency._inventory(url[:-3] + "/api/v1/models", 30)
                    )
                    if len(loaded) != 1 or loaded[0][0] != model:
                        raise ValueError("residency invariant")
                    actual = loaded[0][2]["config"]
                    if (
                        actual.get("parallel") != 1
                        or actual.get("context_length") != length
                    ):
                        raise ValueError("context/parallel invariant")
                    row[phase] = loaded[0][2]
                    if phase == "after":
                        break
                    request = urllib.request.Request(
                        url + "/chat/completions",
                        data=json.dumps(
                            {
                                "model": model,
                                "messages": [
                                    {"role": "user", "content": "Reply with OK."}
                                ],
                                "max_tokens": 256,
                                "temperature": 0,
                            }
                        ).encode(),
                        headers={"Content-Type": "application/json"},
                    )
                    inference_started = time.monotonic()
                    with urllib.request.urlopen(request, timeout=180) as response:
                        reply = json.load(response)
                    row["inference_seconds"] = time.monotonic() - inference_started
                    row["reply"] = reply
                    if (
                        not reply.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                        .strip()
                    ):
                        raise ValueError("no final content in smoke response")
            row["success"] = True
        except (
            OSError,
            ValueError,
            KeyError,
            IndexError,
            residency.ModelResidencyError,
        ) as exc:
            row.update(success=False, error_type=type(exc).__name__, error=str(exc))
        row["total_seconds"] = time.monotonic() - started
        write(output, row)
        rows.append(row)
        print(
            json.dumps(
                {k: v for k, v in row.items() if k not in ("before", "after", "reply")}
            ),
            flush=True,
        )
        if not row["success"]:
            break
    return all(row["success"] for row in rows) and len(rows) == 3


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "load-cycle"))
    parser.add_argument("--cycle", type=int, choices=(1, 2, 3))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.cycle is None:
        parser.error("--cycle required")
    else:
        raise SystemExit(0 if load_cycle(args.cycle) else 1)
