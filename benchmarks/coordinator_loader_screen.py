"""Frozen candidate serial load/inference screen, no worker quality credit."""

import hashlib
import importlib.util
import json
import time
from pathlib import Path

from capability_fit import WORK, load_worker, write

SNAPSHOT = WORK / "coordinator-loader-baseline-1"
BASE = WORK / "coordinator-loader-screen-1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    BASE.mkdir(exist_ok=False)
    frozen = json.loads((SNAPSHOT / "freeze.json").read_text())["files"]
    for path, sha in frozen.items():
        if digest(SNAPSHOT / path) != sha:
            raise ValueError("frozen source drift: " + path)
    write(
        BASE / "registration.json",
        {
            "snapshot": str(SNAPSHOT),
            "driver_sha256": digest(Path(__file__)),
            "order": ["qwen/qwen3-coder-30b", "meta/muse-glimmer"],
            "context_length": 24576,
            "parallel": 1,
            "weekly_used_ceiling": 10,
            "classification": "Two sequential switches and real inference; not substantive E/C/R or Coordinator quality credit",
            "global_config_changed": False,
        },
    )
    worker = load_worker(SNAPSHOT)
    spec = importlib.util.spec_from_file_location(
        "loader_screen_residency", SNAPSHOT / ".local-agents/model_residency.py"
    )
    residency = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(residency)
    config = {
        "single_model_residency": True,
        "model_load_backend": "cli",
        "model_load_cli_path": "C:/Users/Lin/.lmstudio/bin/lms.exe",
        "model_switch_timeout_seconds": 360,
        "explorer_model": "openai/gpt-oss-20b",
        "coder_model": "qwen/qwen3-coder-30b",
        "reviewer_model": "meta/muse-glimmer",
        "coordinator_model": "meta/muse-glimmer",
    }
    write(BASE / "config.json", config)
    for index, model in enumerate((config["coder_model"], config["reviewer_model"]), 1):
        client = worker.LMStudioClient(
            "http://127.0.0.1:12345/v1",
            model,
            context_length=24576,
            max_tokens=512,
            structured_output=False,
        )
        result = {"model": model, "quality_credit": False}
        started = time.monotonic()
        try:
            print("Switching exclusively to " + model, flush=True)
            with residency.role_model_lease(client, config):
                result["load_seconds"] = time.monotonic() - started
                before = residency._loaded(
                    residency._inventory("http://127.0.0.1:12345/api/v1/models", 30)
                )
                result["loaded"] = before
                answer = client.complete(
                    [
                        {
                            "role": "system",
                            "content": "Reply only with the requested JSON, without explanation.",
                        },
                        {"role": "user", "content": 'Return exactly {"ready":true}.'},
                    ]
                )
                if json.loads(answer) != {"ready": True}:
                    raise ValueError("unexpected real inference JSON")
                after = residency._loaded(
                    residency._inventory("http://127.0.0.1:12345/api/v1/models", 30)
                )
                if before != after:
                    raise ValueError("inventory changed during model turn")
                result["request_stats"] = client.last_request_stats
                result["real_inference_verified"] = True
                result["decision"] = "pass"
        except Exception as exc:
            result["decision"] = "fail_closed"
            result["error"] = {"type": type(exc).__name__, "message": str(exc)[:1000]}
            raise
        finally:
            result["total_seconds"] = time.monotonic() - started
            write(BASE / f"switch-{index}.json", result)
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
