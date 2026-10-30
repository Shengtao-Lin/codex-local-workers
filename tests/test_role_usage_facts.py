"""Missing local usage is unknown, not zero; cloud savings are not inferred."""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "role_usage_facts_test",
    Path(__file__).resolve().parents[1] / "benchmarks/role_usage_facts.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_main_loop_roles_report_actual_sums_and_coverage():
    result = MODULE.summarize(
        [
            {
                "event": "model_request",
                "facts": {
                    "response_usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 3,
                        "total_tokens": 15,
                    }
                },
            },
            {
                "event": "model_turn",
                "facts": {
                    "model_request": {
                        "finish_reason": "length",
                        "response_usage": {
                            "prompt_tokens": 7,
                            "completion_tokens": 4,
                            "total_tokens": 11,
                        },
                    }
                },
            },
            {"event": "model_request", "facts": {"error": "transport error"}},
            {
                "event": "tool_action",
                "facts": {"response_usage": {"total_tokens": 9999}},
            },
        ]
    )
    assert result["main_loop_request_events"] == 3
    assert result["reported_token_sums"] == {
        "prompt_tokens": 19,
        "completion_tokens": 7,
        "total_tokens": 26,
    }
    assert result["token_field_coverage"] == {
        "prompt_tokens": 2,
        "completion_tokens": 2,
        "total_tokens": 2,
    }
    assert result["output_limit_events"] == 1


def test_missing_invalid_and_partial_usage_is_not_fabricated():
    result = MODULE.summarize(
        [
            {
                "event": "model_request",
                "facts": {
                    "response_usage": {
                        "prompt_tokens": True,
                        "completion_tokens": -1,
                        "total_tokens": "20",
                    }
                },
            },
            {
                "event": "model_turn",
                "facts": {
                    "model_request": {"response_usage": {"completion_tokens": 0}}
                },
            },
        ]
    )
    assert result["reported_token_sums"] == {
        "prompt_tokens": None,
        "completion_tokens": 0,
        "total_tokens": None,
    }
    assert result["token_field_coverage"]["completion_tokens"] == 1
    assert "not Codex cloud tokens" in result["scope"]
