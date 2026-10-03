from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "model_residency_under_test", Path(__file__).resolve().parents[1] / "model_residency.py"
)
assert SPEC is not None and SPEC.loader is not None
RESIDENCY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RESIDENCY
SPEC.loader.exec_module(RESIDENCY)


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class Client:
    base_url = "http://127.0.0.1:12345/v1"
    model = "meta/muse-glimmer"
    context_length = 24576


class ModelResidencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "single_model_residency": True,
            "explorer_model": "openai/gpt-oss-20b",
            "coder_model": "qwen/qwen3-coder-30b",
            "reviewer_model": "meta/muse-glimmer",
        }

    def test_switch_unloads_old_role_before_loading_target_and_holds_lock(self) -> None:
        loaded = {"qwen/qwen3-coder-30b"}
        actions = []

        def urlopen(request, timeout):
            url = request.full_url if hasattr(request, "full_url") else request
            if url.endswith("/models"):
                models = [
                    {
                        "key": key,
                        "loaded_instances": [{"id": key, "config": {"context_length": 24576}}]
                        if key in loaded
                        else [],
                    }
                    for key in self.config.values()
                    if isinstance(key, str) and "/" in key
                ]
                return Response(json.dumps({"models": models}).encode())
            body = json.loads(request.data)
            if url.endswith("/unload"):
                actions.append(("unload", body["instance_id"]))
                loaded.remove(body["instance_id"])
                return Response(json.dumps({"instance_id": body["instance_id"]}).encode())
            actions.append(("load", body["model"], body["context_length"]))
            loaded.add(body["model"])
            return Response(b'{"status":"loaded"}')

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(RESIDENCY.tempfile, "gettempdir", return_value=temp_dir):
                with patch.object(RESIDENCY.urllib.request, "urlopen", side_effect=urlopen):
                    with RESIDENCY.role_model_lease(Client(), self.config):
                        self.assertEqual(loaded, {"meta/muse-glimmer"})
                        with self.assertRaises(RESIDENCY.ModelResidencyError) as raised:
                            with RESIDENCY.role_model_lease(Client(), self.config):
                                pass
                        self.assertEqual(raised.exception.reason_code, "model_switch_lock_held")
                self.assertEqual(list(Path(temp_dir).iterdir()), [])
        self.assertEqual(
            actions,
            [("unload", "qwen/qwen3-coder-30b"), ("load", "meta/muse-glimmer", 24576)],
        )

    def test_foreign_model_blocks_without_unloading(self) -> None:
        inventory = {
            "models": [
                {
                    "key": "mistralai/devstral-small-2-2512",
                    "loaded_instances": [{"id": "mistralai/devstral-small-2-2512"}],
                },
                {"key": "meta/muse-glimmer", "loaded_instances": []},
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(RESIDENCY.tempfile, "gettempdir", return_value=temp_dir):
                with patch.object(
                    RESIDENCY.urllib.request,
                    "urlopen",
                    return_value=Response(json.dumps(inventory).encode()),
                ) as request:
                    with self.assertRaises(RESIDENCY.ModelResidencyError) as raised:
                        with RESIDENCY.role_model_lease(Client(), self.config):
                            pass
                self.assertEqual(list(Path(temp_dir).iterdir()), [])
        self.assertEqual(raised.exception.reason_code, "foreign_model_loaded")
        self.assertEqual(request.call_count, 1)

    def test_opt_out_does_not_touch_lm_studio(self) -> None:
        with patch.object(RESIDENCY.urllib.request, "urlopen") as request:
            with RESIDENCY.role_model_lease(Client(), {}):
                pass
        request.assert_not_called()

    def test_optional_coordinator_model_is_managed_without_changing_other_roles(self) -> None:
        self.config["coordinator_model"] = "coordinator/test-model"
        client = Client()
        client.model = self.config["coordinator_model"]
        inventory = {
            "models": [
                {
                    "key": client.model,
                    "loaded_instances": [{"id": client.model, "config": {"context_length": 24576}}],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(RESIDENCY.tempfile, "gettempdir", return_value=temp_dir):
                with patch.object(
                    RESIDENCY.urllib.request,
                    "urlopen",
                    side_effect=lambda *a, **k: Response(json.dumps(inventory).encode()),
                ):
                    with RESIDENCY.role_model_lease(client, self.config):
                        self.assertEqual(self.config["reviewer_model"], "meta/muse-glimmer")


if __name__ == "__main__":
    unittest.main()
