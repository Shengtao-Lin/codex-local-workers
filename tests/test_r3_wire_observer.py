import importlib.util
import io
import json
import urllib.request
from pathlib import Path


def test_observer_preserves_request_response_and_errors(tmp_path, monkeypatch):
    path = (
        Path(__file__).resolve().parents[1] / "benchmarks/r3_capture/sitecustomize.py"
    )
    spec = importlib.util.spec_from_file_location("r3_capture_test", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.delenv("R3_WIRE_DIR", raising=False)
    original = urllib.request.urlopen
    spec.loader.exec_module(module)
    assert urllib.request.urlopen is original
    monkeypatch.setenv("R3_WIRE_DIR", str(tmp_path))
    request = urllib.request.Request(
        "http://127.0.0.1:12345/v1/chat/completions",
        data=b'{"model":"fixture","messages":[]}',
        method="POST",
    )
    seen = []

    def fake_open(value, **kwargs):
        seen.append((value, kwargs))
        return io.BytesIO(b'{"choices":[],"usage":{"prompt_tokens":1}}')

    module._open = fake_open
    with module.observed_open(request, timeout=12) as response:
        assert response.read() == b'{"choices":[],"usage":{"prompt_tokens":1}}'
        assert response.read() == b""
    assert seen == [(request, {"timeout": 12})]
    assert (
        json.loads(next(tmp_path.glob("*-request.json")).read_text())["body"]["model"]
        == "fixture"
    )
    assert len(list(tmp_path.glob("*-response.json"))) == 1
    assert urllib.request.urlopen is original
