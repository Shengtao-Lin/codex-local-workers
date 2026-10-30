"""Experimental transport/readiness adapter around unmodified installed entries.

It never loads/unloads either backend. Operator-loaded IQ3_S is checked before
each request; switching/lifecycle qualification is deliberately separate.
"""

import contextlib
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:47831/v1"


def validate(native, lm, model, context, instance_id=None):
    instances = native.get("instances", [])
    active = [i for i in instances if i.get("status") == "ready"]
    if len(active) != 1 or len(instances) != 1:
        raise ValueError("Expected exactly one ready Strata instance")
    instance = active[0]
    if instance.get("model") != model or model != "iq3_s":
        raise ValueError("Unexpected Strata model")
    if instance_id is not None and instance.get("id") != instance_id:
        raise ValueError("Strata instance changed")
    if instance.get("parallel") != 1 or type(instance.get("context")) is not int:
        raise ValueError("Strata parallel/context configuration not verified")
    if instance["context"] < context:
        raise ValueError("Strata context too small")
    if any(m.get("loaded_instances") for m in lm["models"]):
        raise ValueError("LM Studio has a resident model")
    return {
        key: instance.get(key)
        for key in ("id", "model", "context", "parallel", "vision")
    }


def guard(model, context, instance_id=None):
    def fetch(url):
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.load(r)

    return validate(
        fetch(BASE[:-3] + "/api/native"),
        fetch("http://127.0.0.1:12345/api/v1/models"),
        model,
        context,
        instance_id,
    )


def patch_worker(worker, config):
    if getattr(worker, "_strata_transport_installed", False):
        return
    expected = config["experimental_strata_instance_id"]
    original = worker.LMStudioClient

    class StrataClient(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.base_url != BASE or self.model != "iq3_s":
                raise ValueError("Experimental Strata endpoint/model mismatch")
            self.reasoning_effort = "low"

        def preflight(self):
            guard(self.model, self.context_length, expected)
            return super().preflight()

        def ensure_loaded(self, **_kwargs):
            observed = guard(self.model, self.context_length, expected)
            return {
                "status": "already_loaded",
                "model": self.model,
                "observed": observed,
            }

        def complete(self, messages):
            observed = guard(self.model, self.context_length, expected)
            value = super().complete(messages)
            self.last_request_stats["strata_residency_observed"] = observed
            return value

    @contextlib.contextmanager
    def lease(client, cfg):
        if cfg.get("single_model_residency") is not True:
            raise ValueError("Strata experiment requires residency checks")
        path = Path(tempfile.gettempdir()) / "local-worker-kit-strata-experiment.lock"
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump({"pid": os.getpid(), "model": client.model}, stream)
            guard(client.model, client.context_length, expected)
            yield
            guard(client.model, client.context_length, expected)
        finally:
            path.unlink()

    worker.LMStudioClient = StrataClient
    worker.MODEL_RESIDENCY.role_model_lease = lease
    worker._strata_transport_installed = True


def main():
    role = sys.argv[1]
    assert role in {"unit", "review"}
    args = sys.argv[2:]
    config = json.loads(
        Path(args[args.index("--config") + 1]).read_text(encoding="utf-8")
    )
    assert config.get("experimental_strata_transport") is True
    root = Path.cwd() / ".local-agents"
    sys.path.insert(0, str(root))
    from bounded import capture_fixture_support as F

    original_load = F.load

    def load(path, name):
        module = original_load(path, name)
        if hasattr(module, "LMStudioClient"):
            patch_worker(module, config)
        if hasattr(module, "WORKER") and hasattr(module.WORKER, "LMStudioClient"):
            patch_worker(module.WORKER, config)
        return module

    F.load = load
    filename = "local-bounded-unit.py" if role == "unit" else "local-bounded-review.py"
    module = F.load(root / filename, "strata_experimental_" + role)
    if role == "unit":
        original_run = module.subprocess.run

        def run(argv, *a, **kw):
            if (
                isinstance(argv, list)
                and len(argv) > 2
                and str(argv[2]).endswith("local-bounded-review.py")
            ):
                argv = [*argv[:2], str(Path(__file__).resolve()), "review", *argv[3:]]
            return original_run(argv, *a, **kw)

        module.subprocess.run = run
    sys.argv = [str(root / filename), *args]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
