from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
FIXTURE = ROOT / "benchmarks" / "capability-matrix-v1.2.json"


class CapabilityMatrixFixtureTests(unittest.TestCase):
    def test_frozen_matrix_covers_every_role_and_resolves_real_tests(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["protocol_version"], "v1.2")
        self.assertEqual(set(fixture["roles"]), {"Explorer", "Coder", "Reviewer"})
        for role, sections in fixture["roles"].items():
            self.assertTrue(sections["allowed"], role)
            self.assertTrue(sections["prohibited"], role)
            for category in ("allowed", "prohibited"):
                for capability, nodes in sections[category].items():
                    self.assertTrue(nodes, f"{role}.{category}.{capability}")
                    for node in nodes:
                        path_text, class_name, method_name = node.split("::")
                        path = ROOT / path_text
                        tree = ast.parse(path.read_text(encoding="utf-8"))
                        classes = {
                            item.name: item for item in tree.body if isinstance(item, ast.ClassDef)
                        }
                        self.assertIn(class_name, classes, node)
                        methods = {
                            item.name
                            for item in classes[class_name].body
                            if isinstance(item, ast.FunctionDef)
                        }
                        self.assertIn(method_name, methods, node)


if __name__ == "__main__":
    unittest.main()
