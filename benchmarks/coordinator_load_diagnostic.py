"""One bounded CLI load and real inference; preserve the failed HTTP trial."""

import hashlib
import json
import os
import subprocess
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path

from capability_fit import WORK, write

BASE = WORK / "coordinator-load-diagnostic-1"
MODEL = "meta/muse-glimmer"
URL = "http://127.0.0.1:12345"
CLI = Path("C:/Users/Lin/.lmstudio/bin/lms.exe")


def inventory():
    with urllib.request.urlopen(URL + "/api/v1/models", timeout=30) as response:
        payload = json.load(response)
    return [
        {"key": model["key"], **instance}
        for model in payload["models"]
        for instance in model["loaded_instances"]
    ]


def main():
    BASE.mkdir(exist_ok=False)
    write(
        BASE / "registration.json",
        {
            "model": MODEL,
            "context_length": 24576,
            "parallel": 1,
            "load_deadline_seconds": 360,
            "inference_deadline_seconds": 180,
            "previous_http_trial": "coordinator-label-pilot-4/reviewer-startup-witness-1.json",
            "classification": "load-only diagnostic; not a paired causal estimate or role-quality credit",
            "runtime_changed": False,
            "weekly_used_ceiling": 10,
            "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
    )
    digest = hashlib.sha256((URL + "/v1").encode()).hexdigest()[:16]
    lock = Path(tempfile.gettempdir()) / f"local-worker-kit-lmstudio-{digest}.lock"
    token = uuid.uuid4().hex
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    result = {}
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({"pid": os.getpid(), "model": MODEL, "token": token}, stream)
        before = inventory()
        result["before"] = before
        if before:
            raise ValueError(
                "cold CLI trial requires no loaded model; refusing to unload"
            )
        if not CLI.is_file():
            raise ValueError("verified CLI is missing")
        argv = [
            str(CLI),
            "load",
            MODEL,
            "--context-length",
            "24576",
            "--parallel",
            "1",
            "--identifier",
            MODEL,
            "--yes",
        ]
        print("Starting bounded cold CLI load", flush=True)
        started = time.monotonic()
        loaded = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=360,
            encoding="utf-8",
            errors="replace",
            shell=False,
            check=False,
        )
        result["cli"] = {
            "argv": argv,
            "exit_code": loaded.returncode,
            "elapsed_seconds": time.monotonic() - started,
            "stdout": loaded.stdout[-3000:],
            "stderr": loaded.stderr[-3000:],
        }
        if loaded.returncode:
            raise ValueError("CLI load failed")
        after = inventory()
        result["after"] = after
        if len(after) != 1 or after[0]["key"] != MODEL or after[0]["id"] != MODEL:
            raise ValueError("single expected model invariant failed")
        config = after[0]["config"]
        if config.get("context_length") != 24576 or config.get("parallel") != 1:
            raise ValueError("context/concurrency differs from registered settings")
        print("CLI confirmed; testing real bounded structured inference", flush=True)
        body = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": 'Return only this JSON object: {"ready":true}',
                }
            ],
            "max_tokens": 64,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            URL + "/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=180) as response:
            answer = json.load(response)
        content = answer["choices"][0]["message"]["content"]
        if json.loads(content) != {"ready": True}:
            raise ValueError("real inference did not return expected JSON")
        result["inference"] = {
            "elapsed_seconds": time.monotonic() - started,
            "json_verified": True,
            "usage": answer.get("usage"),
        }
        result["final_inventory"] = inventory()
        if result["final_inventory"] != after:
            raise ValueError("model inventory changed during inference")
        result["decision"] = "CLI_LOAD_AND_REAL_INFERENCE_PASS"
    except Exception as exc:
        result["decision"] = "FAIL_CLOSED"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)[:1000]}
        raise
    finally:
        write(BASE / "result.json", result)
        if json.loads(lock.read_text(encoding="utf-8-sig")).get("token") == token:
            lock.unlink()
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
