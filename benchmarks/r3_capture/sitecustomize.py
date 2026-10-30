"""Opt-in diagnostic observer: preserve localhost HTTP bytes, never alter them."""

import json
import os
import time
import urllib.request
import uuid
from pathlib import Path

_open = urllib.request.urlopen


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def observed_open(request, *args, **kwargs):
    destination = os.environ.get("R3_WIRE_DIR")
    if (
        not destination
        or not isinstance(request, urllib.request.Request)
        or not request.full_url.startswith("http://127.0.0.1:12345/")
        or request.get_method() != "POST"
    ):
        return _open(request, *args, **kwargs)
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    key = str(time.time_ns()) + "-" + uuid.uuid4().hex
    started = time.monotonic()
    save(
        root / (key + "-request.json"),
        {"url": request.full_url, "body": json.loads(request.data), "pid": os.getpid()},
    )
    try:
        response = _open(request, *args, **kwargs)
    except Exception as exc:
        save(
            root / (key + "-error.json"),
            {
                "type": type(exc).__name__,
                "message": str(exc),
                "seconds": time.monotonic() - started,
            },
        )
        raise

    class ObservedResponse:
        reads = 0

        def __enter__(self):
            response.__enter__()
            return self

        def __exit__(self, *arguments):
            return response.__exit__(*arguments)

        def __getattr__(self, name):
            return getattr(response, name)

        def read(self, *arguments):
            raw = response.read(*arguments)
            self.reads += 1
            suffix = (
                "-response.json"
                if self.reads == 1
                else f"-response-read-{self.reads}.json"
            )
            save(
                root / (key + suffix),
                {
                    "raw": raw.decode("utf-8", errors="replace"),
                    "seconds": time.monotonic() - started,
                },
            )
            return raw

    return ObservedResponse()


if os.environ.get("R3_WIRE_DIR"):
    urllib.request.urlopen = observed_open
