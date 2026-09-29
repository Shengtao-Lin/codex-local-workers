from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

MODULE_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "codex_usage.py"
SPEC = importlib.util.spec_from_file_location("codex_usage_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
USAGE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = USAGE
SPEC.loader.exec_module(USAGE)


class CodexUsageTests(unittest.TestCase):
    def test_one_completed_turn_counts_cached_only_once(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text(
                json.dumps({"type": "thread.started", "thread_id": "t"})
                + "\n"
                + json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 13143,
                            "cached_input_tokens": 6912,
                            "output_tokens": 5,
                            "reasoning_output_tokens": 0,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            before = path.read_bytes()
            result = USAGE.extract(path)
            self.assertEqual(result["primary_tokens"], 13148)
            self.assertEqual(result["cached_input_tokens"], 6912)
            self.assertTrue(
                result["token_source"].startswith("codex-exec-jsonl-sha256:")
            )
            self.assertEqual(path.read_bytes(), before)

    def test_missing_or_failed_usage_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text('{"type":"turn.completed"}\n', encoding="utf-8")
            with self.assertRaisesRegex(USAGE.UsageError, "no usage"):
                USAGE.extract(path)
            path.write_text(
                '{"type":"turn.failed"}\n{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":1}}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(USAGE.UsageError, "failed turn"):
                USAGE.extract(path)

    def test_multiple_turns_and_invalid_subcounts_are_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            event = '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":1}}\n'
            path.write_text(event * 2, encoding="utf-8")
            with self.assertRaisesRegex(USAGE.UsageError, "exactly one"):
                USAGE.extract(path)
            path.write_text(
                '{"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":2,"output_tokens":1}}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(USAGE.UsageError, "subcounts exceed"):
                USAGE.extract(path)

    def test_multiple_cli_streams_are_summed_once(self) -> None:
        with TemporaryDirectory() as directory:
            first = Path(directory) / "first.jsonl"
            second = Path(directory) / "second.jsonl"
            first.write_text(
                '{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":2}}\n',
                encoding="utf-8",
            )
            second.write_text(
                '{"type":"turn.completed","usage":{"input_tokens":20,"output_tokens":3}}\n',
                encoding="utf-8",
            )
            result = USAGE.aggregate([first, second])
            self.assertEqual(result["primary_tokens"], 35)
            self.assertEqual(result["streams"], 2)
            with self.assertRaisesRegex(USAGE.UsageError, "duplicate"):
                USAGE.aggregate([first, first])


if __name__ == "__main__":
    unittest.main()
