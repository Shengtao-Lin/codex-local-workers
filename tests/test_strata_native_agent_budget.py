import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from strata_native_agent_host import NativeAgentClient


def client():
    worker = SimpleNamespace(WorkerError=RuntimeError, PolicyViolation=ValueError)
    c = NativeAgentClient(Path("unused-offline.json"), worker)
    c.identity = {"task_id": "t", "unit_id": "u", "run_id": "r"}
    c.runtime = SimpleNamespace(
        ledger={
            "requests": 1,
            "native_request_reservations": 0,
            "native_http_requests": 0,
        },
        deadline=time.monotonic() + 100,
        archive=SimpleNamespace(
            run_root=Path("unused-archive"), mark_model_started=lambda: None
        ),
        RUN_STATE=SimpleNamespace(write_json_once=lambda *args: None),
    )
    c.sent = []
    c.send = c.sent.append
    return c


def frame(c, kind, **fields):
    c.frames.put({"kind": kind, "identity": c.identity, **fields})


@pytest.mark.parametrize("requests,reservations", [(1, 11), (6, 6), (12, 0)])
def test_shared_credit_exhaustion_never_grants_another_model_call(
    requests, reservations
):
    c = client()
    c.runtime.ledger.update(requests=requests, native_request_reservations=reservations)
    frame(c, "native_model_permit", body={"model": "iq3_s", "max_tokens": 12288})
    with pytest.raises(RuntimeError, match="Shared model/tool"):
        c.receive()
    assert not c.sent


def test_permit_and_tool_counts_stay_in_same_ledger():
    c = client()
    frame(c, "native_model_permit", body={"model": "iq3_s", "max_tokens": 12288})
    frame(c, "host_action", action="read")
    assert c.receive()["kind"] == "host_action"
    assert c.runtime.ledger["native_request_reservations"] == 1
    assert c.runtime.ledger["requests"] == 1
    assert c.sent[0]["remaining_ms"] <= 100000
    assert c.runtime.ledger["native_http_requests"] == 0


def test_actual_http_counter_is_not_reservation_counter():
    c = client()
    c.runtime.ledger["native_request_reservations"] = 1
    frame(c, "native_http_started")
    frame(
        c, "native_model_result", provider_call=True, status=400, body="retained error"
    )
    frame(c, "host_action")
    c.receive()
    assert c.runtime.ledger["native_http_requests"] == 1


@pytest.mark.parametrize(
    "body",
    [{"model": "cloud", "max_tokens": 12288}, {"model": "iq3_s", "max_tokens": 999999}],
)
def test_provider_or_output_budget_change_fails_before_permit(body):
    c = client()
    frame(c, "native_model_permit", body=body)
    with pytest.raises(ValueError):
        c.receive()
    assert not c.sent


def test_deadline_denies_even_with_remaining_request_credits():
    c = client()
    c.runtime.deadline = time.monotonic() - 1
    frame(c, "native_model_permit", body={"model": "iq3_s", "max_tokens": 12288})
    with pytest.raises(RuntimeError, match="deadline"):
        c.receive()
    assert not c.sent


def test_wrong_identity_is_denied_before_budget():
    c = client()
    c.frames.put({"kind": "native_model_permit", "identity": {"run_id": "forged"}})
    with pytest.raises(ValueError, match="identity"):
        c.receive()
    assert not c.sent
