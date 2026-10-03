"""Serialize this kit's LM Studio role calls with one loaded role model."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class ModelResidencyError(Exception):
    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def _inventory(url: str, timeout: int) -> dict[str, dict[str, Any]]:
    with urllib.request.urlopen(url, timeout=min(timeout, 30)) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise ValueError("LM Studio native model inventory has an invalid shape")
    models: dict[str, dict[str, Any]] = {}
    for item in payload["models"]:
        if not isinstance(item, dict) or not isinstance(item.get("key"), str):
            raise ValueError("LM Studio native model entry has an invalid shape")
        if not isinstance(item.get("loaded_instances"), list):
            raise ValueError("LM Studio loaded_instances has an invalid shape")
        models[item["key"]] = item
    return models


def _loaded(models: dict[str, dict[str, Any]]) -> list[tuple[str, str, dict[str, Any]]]:
    result = []
    for key, item in models.items():
        for instance in item["loaded_instances"]:
            if not isinstance(instance, dict) or not isinstance(instance.get("id"), str):
                raise ValueError("LM Studio loaded instance has an invalid shape")
            result.append((key, instance["id"], instance))
    return result


@contextmanager
def role_model_lease(client: Any, config: dict[str, Any]) -> Iterator[None]:
    """Keep kit roles sequential; never unload a model outside the role allowlist."""
    if config.get("single_model_residency") is not True:
        yield
        return
    base_url = client.base_url
    timeout = config.get("model_switch_timeout_seconds", 360)
    if not base_url.endswith("/v1") or type(timeout) is not int or not 1 <= timeout <= 900:
        raise ModelResidencyError(
            "model_switch_config", "invalid LM Studio model switch configuration"
        )
    roles = [config.get(f"{role}_model") for role in ("explorer", "coder", "reviewer")]
    if "coordinator_model" in config:
        roles.append(config["coordinator_model"])
    if any(not isinstance(role, str) or not role for role in roles) or client.model not in roles:
        raise ModelResidencyError(
            "model_switch_config", "role model is missing from the managed model list"
        )
    digest = hashlib.sha256(base_url.encode("utf-8")).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"local-worker-kit-lmstudio-{digest}.lock"
    token = uuid.uuid4().hex
    try:
        descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        try:
            owner = lock_path.read_text(encoding="utf-8-sig")[:500]
        except OSError:
            owner = "<unreadable>"
        raise ModelResidencyError(
            "model_switch_lock_held", f"LM Studio role lease is held: {owner}"
        ) from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({"pid": os.getpid(), "model": client.model, "token": token}, stream)
        native_url = base_url[:-3] + "/api/v1/models"
        try:
            models = _inventory(native_url, timeout)
            if client.model not in models:
                raise ModelResidencyError(
                    "model_unavailable", f"role model is not installed: {client.model}"
                )
            loaded = _loaded(models)
            foreign = sorted({key for key, _instance_id, _instance in loaded if key not in roles})
            if foreign:
                raise ModelResidencyError(
                    "foreign_model_loaded",
                    "non-kit LM Studio models are loaded; refusing to unload them: "
                    + ", ".join(foreign),
                )
            for key, instance_id, _instance in loaded:
                if key == client.model:
                    continue
                request = urllib.request.Request(
                    native_url + "/unload",
                    data=json.dumps({"instance_id": instance_id}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    result = json.load(response)
                if not isinstance(result, dict) or result.get("instance_id") != instance_id:
                    raise ValueError(f"LM Studio did not confirm unload: {instance_id}")
            models = _inventory(native_url, timeout)
            target = [instance for key, _id, instance in _loaded(models) if key == client.model]
            if not target:
                body: dict[str, Any] = {"model": client.model}
                if client.context_length is not None:
                    body["context_length"] = client.context_length
                request = urllib.request.Request(
                    native_url + "/load",
                    data=json.dumps(body).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    result = json.load(response)
                if not isinstance(result, dict) or result.get("status") != "loaded":
                    raise ValueError(f"LM Studio did not confirm load: {client.model}")
            loaded = _loaded(_inventory(native_url, timeout))
            if len(loaded) != 1 or loaded[0][0] != client.model:
                raise ModelResidencyError(
                    "model_switch_invariant", "exactly one role model is not loaded"
                )
            instance_config = loaded[0][2].get("config") or {}
            if not isinstance(instance_config, dict):
                raise ValueError("LM Studio loaded model config has an invalid shape")
            length = instance_config.get("context_length")
            if (
                client.context_length is not None
                and type(length) is int
                and length < client.context_length
            ):
                raise ModelResidencyError(
                    "model_context_too_small",
                    f"loaded {client.model} context {length} is below configured {client.context_length}",
                )
        except ModelResidencyError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise ModelResidencyError(
                "model_switch_failed", f"LM Studio role switch failed: {exc}"
            ) from exc
        yield
    finally:
        try:
            metadata = json.loads(lock_path.read_text(encoding="utf-8-sig"))
            if metadata.get("token") == token:
                lock_path.unlink()
        except (OSError, ValueError):
            pass
