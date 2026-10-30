"""Schema-only negative controls; unchanged scope/edit/semantic execution guards."""

import copy
import io
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import test_worker_runtime as helpers

RUNTIME = helpers.RUNTIME


def matches(schema, value):
    """Independent focused reference for the emitted schema's used keywords, not a general validator."""
    if "anyOf" in schema:
        return any(matches(branch, value) for branch in schema["anyOf"])
    if "not" in schema and matches(schema["not"], value):
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict) or not set(schema.get("required", [])) <= set(value):
            return False
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            return False
        return all(matches(properties[k], v) for k, v in value.items() if k in properties)
    if kind == "array":
        return isinstance(value, list) and all(matches(schema.get("items", {}), v) for v in value)
    if kind == "integer" and (
        type(value) is not int or value < schema.get("minimum", -float("inf"))
    ):
        return False
    if (kind == "string" or "pattern" in schema) and not isinstance(value, str):
        return False
    if "pattern" in schema and re.search(schema["pattern"], value) is None:
        return False
    return True


class CoderSchemaControls(unittest.TestCase):
    def schema(self, required=True, base=None):
        return RUNTIME.typed_coder_action_schema(
            base or RUNTIME.CODER_ACTION_SCHEMA, contract_check_required=required
        )

    def test_missing_or_nonobject_acknowledgement_fails_schema_before_validation(self):
        schema = self.schema()
        for arguments in (
            {},
            {"phase": "check"},
            {"contract_check": None},
            {"contract_check": []},
            {"contract_check": True},
        ):
            with self.subTest(arguments=arguments):
                self.assertFalse(matches(schema, {"action": "VALIDATE", "arguments": arguments}))
        self.assertTrue(
            matches(schema, {"action": "VALIDATE", "arguments": {"contract_check": {}}})
        )
        # Presence is not acceptance; actual contract IDs/flags remain runtime-owned checks.
        self.assertTrue(matches(self.schema(False), {"action": "VALIDATE", "arguments": {}}))

    def test_embedded_trailing_cr_lf_and_crlf_rejected_but_empty_and_escaped_literals_allowed(self):
        schema = self.schema()
        args = {"path": "src/a.py", "line": 1, "expected_sha256": "current", "replacement": ""}
        for replacement in ("a\nb", "a\rb", "a\r\nb", "a\n", "a\r", "\n", "\r\n"):
            with self.subTest(replacement=replacement):
                self.assertFalse(
                    matches(
                        schema,
                        {
                            "action": "SAFE_REPLACE_LINE",
                            "arguments": {**args, "replacement": replacement},
                        },
                    )
                )
                self.assertFalse(matches(RUNTIME.SINGLE_LINE_SCHEMA, replacement))
        for replacement in ("", "VALUE = 2", r'text = "\n"', "中文 = 2"):
            with self.subTest(replacement=replacement):
                self.assertTrue(
                    matches(
                        schema,
                        {
                            "action": "SAFE_REPLACE_LINE",
                            "arguments": {**args, "replacement": replacement},
                        },
                    )
                )
        self.assertTrue(
            matches(
                schema,
                {
                    "action": "SAFE_REPLACE",
                    "arguments": {
                        "path": "src/a.py",
                        "expected_sha256": "current",
                        "find": "one\ntwo",
                        "replace": "three\nfour",
                    },
                },
            )
        )

    def test_dollar_pattern_alone_would_accept_final_lf_under_schema_search_semantics(self):
        self.assertIsNotNone(re.search(RUNTIME.SINGLE_LINE_SCHEMA["pattern"], "VALUE = 2\n"))
        self.assertFalse(matches(RUNTIME.SINGLE_LINE_SCHEMA, "VALUE = 2\n"))

    def test_schema_copies_base_and_preserves_every_narrowed_action_set(self):
        bases = [
            RUNTIME.CODER_ACTION_SCHEMA,
            RUNTIME.repair_only_action_schema(RUNTIME.CODER_ACTION_SCHEMA, "SAFE_REPLACE"),
            RUNTIME.post_edit_progress_schema(RUNTIME.CODER_ACTION_SCHEMA),
            RUNTIME.validation_only_action_schema(RUNTIME.CODER_ACTION_SCHEMA),
        ]
        for base in bases:
            before = copy.deepcopy(base)
            schema = self.schema(base=base)
            self.assertEqual(base, before)
            branches = {b["properties"]["action"]["enum"][0]: b for b in schema["anyOf"]}
            self.assertEqual(set(branches), set(base["properties"]["action"]["enum"]))
            if "VALIDATE" in branches:
                self.assertEqual(
                    branches["VALIDATE"]["properties"]["arguments"]["required"], ["contract_check"]
                )
            if "SAFE_REPLACE_LINE" in branches:
                self.assertFalse(
                    matches(
                        branches["SAFE_REPLACE_LINE"]["properties"]["arguments"]["properties"][
                            "replacement"
                        ],
                        "x\n",
                    )
                )
            schema["anyOf"][0]["properties"]["arguments"]["properties"].clear()
            self.assertEqual(base, before)

    def test_wire_is_packet_aware_and_constructor_does_not_fabricate_acknowledgement(self):
        for required in (False, True):
            with self.subTest(required=required), TemporaryDirectory() as directory:
                root = Path(directory)
                helpers.WorkerRuntimeTests().make_tree(root)
                packet = helpers.packet_v2()
                packet["contract_check_required"] = required
                client = RUNTIME.LMStudioClient(
                    "http://unused/v1", "same-model", typed_action_arguments=True
                )
                runtime = RUNTIME.WorkerRuntime(root, packet, {"python": sys.executable}, client)
                self.assertEqual(client.contract_check_required, required)
                client.action_schema = RUNTIME.validation_only_action_schema(
                    RUNTIME.CODER_ACTION_SCHEMA
                )
                captured = []

                def response(request, **_kwargs):
                    captured.append(json.loads(request.data))
                    return io.BytesIO(
                        json.dumps(
                            {
                                "choices": [
                                    {
                                        "message": {
                                            "content": '{"action":"VALIDATE","arguments":{}}'
                                        },
                                        "finish_reason": "stop",
                                    }
                                ]
                            }
                        ).encode()
                    )

                with patch.object(RUNTIME.urllib.request, "urlopen", side_effect=response):
                    raw = client.complete([{"role": "user", "content": "controlled stub"}])
                wire = captured[0]["response_format"]["json_schema"]["schema"]
                action = RUNTIME.parse_action(raw)
                self.assertEqual(matches(wire, json.loads(raw)), not required)
                self.assertEqual(action["arguments"], {})
                self.assertEqual(runtime.validation_count, 0)
                if required:
                    with self.assertRaisesRegex(RUNTIME.WorkerError, "contract_check"):
                        runtime.validate(action["arguments"])
                self.assertEqual((root / "src/example.py").read_text(), "VALUE = 1\n")

    def test_invalid_transport_flags_fail_closed(self):
        for value in (None, "true", 1):
            with self.subTest(value=value), self.assertRaisesRegex(RUNTIME.WorkerError, "boolean"):
                self.schema(value)
