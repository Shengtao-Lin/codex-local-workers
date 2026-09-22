from __future__ import annotations

import importlib.util
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory


MODULE_PATH = Path(__file__).parents[1] / "safe-edit.py"
SPEC = importlib.util.spec_from_file_location("safe_edit_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SAFE_EDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SAFE_EDIT)


class SafeEditTests(unittest.TestCase):
    def test_replace_requires_authorized_path_and_current_hash(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "src" / "example.py"
            target.parent.mkdir()
            target.write_bytes(b"one\r\ntwo\r\n")
            editor = SAFE_EDIT.SafeEditor(root, allowed_modify=["src/example.py"], allowed_create=[])
            _, digest = editor.read_bytes("src/example.py")
            result = editor.replace("src/example.py", "two\n", "three\n", digest)
            self.assertEqual(result["operation"], "modified")
            self.assertEqual(target.read_bytes(), b"one\r\nthree\r\n")
            with self.assertRaisesRegex(SAFE_EDIT.SafeEditError, "changed since it was read"):
                editor.replace("src/example.py", "three\n", "four\n", digest)

    def test_create_refuses_unlisted_and_existing_paths(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            editor = SAFE_EDIT.SafeEditor(root, allowed_modify=[], allowed_create=["tests/new_test.py"])
            with self.assertRaisesRegex(SAFE_EDIT.SafeEditError, "not authorized"):
                editor.create("src/no.py", "x")
            editor.create("tests/new_test.py", "x\n")
            with self.assertRaisesRegex(SAFE_EDIT.SafeEditError, "overwrite"):
                editor.create("tests/new_test.py", "y\n")

    def test_path_escape_and_non_normal_paths_are_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ("../escape.py", "C:/escape.py", "/escape.py", "a//b.py"):
                with self.subTest(path=path):
                    with self.assertRaises(SAFE_EDIT.SafeEditError):
                        SAFE_EDIT.SafeEditor(root, allowed_modify=[path], allowed_create=[])

    def test_reparse_component_is_rejected_before_access(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "linked").mkdir()
            (root / "linked" / "example.py").write_text("x = 1\n", encoding="utf-8")
            editor = SAFE_EDIT.SafeEditor(
                root, allowed_modify=["linked/example.py"], allowed_create=[]
            )
            with patch.object(
                SAFE_EDIT, "is_reparse_point", side_effect=lambda path: path.name == "linked"
            ):
                with self.assertRaisesRegex(SAFE_EDIT.SafeEditError, "reparse point"):
                    editor.read_bytes("linked/example.py")

    def test_mutation_guard_is_required_for_each_write(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "src" / "example.py"
            target.parent.mkdir()
            target.write_text("x = 1\n", encoding="utf-8")
            calls: list[str] = []
            editor = SAFE_EDIT.SafeEditor(
                root,
                allowed_modify=["src/example.py"],
                allowed_create=["src/new.py"],
                mutation_guard=lambda: calls.append("checked"),
            )
            _, digest = editor.read_bytes("src/example.py")
            editor.replace("src/example.py", "x = 1", "x = 2", digest)
            editor.create("src/new.py", "x = 3\n")
            self.assertEqual(calls, ["checked", "checked"])


if __name__ == "__main__":
    unittest.main()
