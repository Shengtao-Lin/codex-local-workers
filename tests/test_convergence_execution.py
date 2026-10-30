"""Thin experiment guard controls; no live calls or inferred Primary accepts."""

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


class GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys

        sys.path.insert(0, str(ROOT / "benchmarks"))
        spec = importlib.util.spec_from_file_location(
            "execution_guard", ROOT / "benchmarks/convergence_execution.py"
        )
        cls.driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.driver)

    def api(self, accepted=(), fail=False):
        def archives(plan, root, refs):
            if fail:
                raise ValueError("invalid canonical acceptance")
            return set(accepted)

        def sources(brief, root):
            if fail:
                raise ValueError("stale source")

        return SimpleNamespace(
            CONTRACT=SimpleNamespace(accepted_units_from_archives=archives),
            assert_sources_current=sources,
        )

    def test_authority_is_explicit_not_truthy(self):
        for value in (False, None, 1, "true"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.driver.dispatch_guard(
                    self.api(), ROOT, {}, {}, {}, "x", primary_authorized=value
                )

    def test_dependency_and_duplicate_blocked(self):
        plan = {"units": [{"unit_id": "consumer", "dependencies": ["producer"]}]}
        for accepted in ([], ["producer", "consumer"]):
            with self.subTest(accepted=accepted), self.assertRaises(ValueError):
                self.driver.dispatch_guard(
                    self.api(accepted),
                    ROOT,
                    plan,
                    {},
                    {},
                    "consumer",
                    primary_authorized=True,
                )

    def test_verified_dependency_permits_only_requested_step(self):
        plan = {"units": [{"unit_id": "consumer", "dependencies": ["producer"]}]}
        observed = self.driver.dispatch_guard(
            self.api(["producer"]),
            ROOT,
            plan,
            {},
            {},
            "consumer",
            primary_authorized=True,
        )
        self.assertEqual(observed, plan["units"][0])

    def test_invalid_acceptance_fails_closed(self):
        with self.assertRaises(ValueError):
            self.driver.dispatch_guard(
                self.api(fail=True), ROOT, {}, {}, {}, "x", primary_authorized=True
            )

    def test_source_drift_fails_closed(self):
        api = self.api()

        def stale(brief, root):
            raise ValueError("source drift")

        api.assert_sources_current = stale
        with self.assertRaises(ValueError):
            self.driver.dispatch_guard(
                api,
                ROOT,
                {"units": [{"unit_id": "x", "dependencies": []}]},
                {},
                {},
                "x",
                primary_authorized=True,
            )
