"""Distributable pure controls for the default-off bounded-v1 components."""

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
NAME = "installed_bounded_test_package"
SPEC = importlib.util.spec_from_file_location(
    NAME, ROOT / "bounded/__init__.py", submodule_search_locations=[str(ROOT / "bounded")]
)
PACKAGE = importlib.util.module_from_spec(SPEC)
sys.modules[NAME] = PACKAGE
SPEC.loader.exec_module(PACKAGE)
RULES = __import__(NAME + ".static_focus_rules", fromlist=["SCHEMA"])
PROVIDER = __import__(NAME + ".approved_provider", fromlist=["facts"])
SUPPORT = __import__(NAME + ".capture_fixture_support", fromlist=["load"])
WORKER = SUPPORT.load(ROOT / "worker-runtime.py", "bounded_wire_test_worker")


class BoundedEntryTests(unittest.TestCase):
    def test_unknown_or_conflicting_proposal_fields_fail_closed(self):
        for raw in ('{"replacement":"x","shell":null}', '{"replacement":"x","blocked_reason":"y"}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                RULES.decode(raw)

    def test_guard_preserves_other_definitions_and_imports(self):
        original = "import json\n\ndef target(x):\n    return x\n\ndef other():\n    return 2\n"
        updated = "def target(x):\n    return x + 1\n"
        material = RULES.materialize(original, updated, "target", set())
        self.assertIn("import json", material)
        self.assertIn("return 2", material)
        with self.assertRaises(ValueError):
            RULES.guard(original, material.replace("return 2", "return 3"), "target", set())
        with self.assertRaises(ValueError):
            RULES.materialize(
                original, updated.replace("target(x)", "target(x, y)"), "target", set()
            )

    def test_no_implicit_historical_facts_provider(self):
        with self.assertRaisesRegex(ValueError, "canonical capture policy"):
            PROVIDER.facts(object(), ValueError)

    def test_reasoning_wire_is_opt_in_and_leaves_default_payload_unchanged(self):
        seen = []
        reply = {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]}

        def fake_http(request, **_kwargs):
            seen.append(json.loads(request.data))
            return io.BytesIO(json.dumps(reply).encode())

        client = WORKER.LMStudioClient("http://localhost:12345/v1", "unchanged-model")
        with patch.object(WORKER.urllib.request, "urlopen", side_effect=fake_http):
            client.complete([{"role": "user", "content": "control"}])
            client.reasoning_effort = "low"
            client.complete([{"role": "user", "content": "control"}])
        self.assertNotIn("reasoning_effort", seen[0])
        self.assertEqual(seen[1].pop("reasoning_effort"), "low")
        self.assertEqual(seen[0], seen[1])
        client.reasoning_effort = "unsupported"
        with self.assertRaisesRegex(WORKER.WorkerError, "Unsupported explicit"):
            client.complete([{"role": "user", "content": "control"}])


if __name__ == "__main__":
    unittest.main()
