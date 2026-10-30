from evaluation_harness.trace_sources.mlflow import MlflowTraceSource


def test_flatten_mlflow_trace_decodes_otel_attributes() -> None:
    raw = {
        "info": {"tags": {"service.name": "support-agent"}},
        "data": {
            "spans": [
                {
                    "parent_span_id": None,
                    "span_id": "encoded-span-id",
                    "status": {"code": "STATUS_CODE_OK", "message": ""},
                    "attributes": {
                        "agent.runtime.version": '"1.2.3"',
                        "agent.message.content": (
                            '["{\\"role\\":\\"user\\",\\"content\\":\\"hi\\"}"]'
                        ),
                    },
                }
            ]
        },
    }

    flattened = MlflowTraceSource._flatten_otel_trace(raw)

    assert flattened["attributes"]["agent.runtime.version"] == "1.2.3"
    assert flattened["attributes"]["agent.message.content"] == ['{"role":"user","content":"hi"}']
    assert flattened["span_ids"] == ["encoded-span-id"]
    assert flattened["status"] == "STATUS_CODE_OK"
    assert flattened["resource"]["service.name"] == "support-agent"
