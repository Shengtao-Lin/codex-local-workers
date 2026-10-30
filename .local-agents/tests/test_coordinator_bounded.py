"""Installed bridge is explicitly opted in and never expands file authority."""

import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "installed_coordinator_bounded", Path(__file__).resolve().parents[1] / "coordinator-bounded.py"
)
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)


class InstalledBridgeTests(unittest.TestCase):
    def test_default_verification_does_not_accept_or_open_an_archive(self):
        with self.assertRaisesRegex(ValueError, "Explicit bounded-v1"):
            BRIDGE.verify_accepted_unit({}, Path.cwd(), "unit", {}, {}, {})

    def test_default_readiness_does_not_dispatch(self):
        with self.assertRaisesRegex(ValueError, "Explicit bounded-v1"):
            BRIDGE.dependency_readiness({}, Path.cwd(), {}, {}, {}, {}, {})

    def test_archive_traversal_rejected_before_open(self):
        with self.assertRaisesRegex(ValueError, "escapes archive"):
            BRIDGE._object(Path.cwd(), "../unapproved.json")


if __name__ == "__main__":
    unittest.main()
