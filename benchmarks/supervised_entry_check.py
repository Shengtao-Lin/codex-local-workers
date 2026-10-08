"""Primary integration assertions for the public entry-to-helper boundary."""

import asyncio
import json
import sys
from pathlib import Path

from capability_fit import write


def run(root):
    sys.path.insert(0, str(root / "src"))
    from product.entry import read_batch

    calls = []
    values = [0, False, "", None, "unvisited"]

    async def fetch(key):
        calls.append(key)
        return values[key]

    keys = [0, 1, 2, 3, 4]
    result = asyncio.run(read_batch(fetch, keys))
    assert result == [0, False, ""] and result[0] is not False and result[1] is False
    assert calls == [0, 1, 2, 3] and keys == [0, 1, 2, 3, 4]
    error = RuntimeError("integration")
    calls.clear()

    async def failing(key):
        calls.append(key)
        if key == 1:
            raise error
        return key

    try:
        asyncio.run(read_batch(failing, [0, 1, 2]))
    except RuntimeError as observed:
        assert observed is error
    else:
        raise AssertionError("entry suppressed exception")
    assert calls == [0, 1]
    evidence = {
        "public_entry_roundtrip": "passed",
        "sentinel_false_values": "passed",
        "exception_identity_and_stop": "passed",
    }
    write(root / ".agent/primary-entry-integration.json", evidence)
    print(json.dumps(evidence))


if __name__ == "__main__":
    run(Path(sys.argv[1]).resolve())
