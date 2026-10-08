"""Primary's executable check of the Reviewer control's untested boundary."""

import asyncio
import json
import sys
from pathlib import Path

from capability_fit import write


def run(root):
    sys.path.insert(0, str(root / "src"))
    from product.target import collect_until

    calls = []
    values = [0, False, "", None, 99]

    async def fetch(key):
        calls.append(key)
        return values[key]

    result = asyncio.run(collect_until(fetch, [0, 1, 2, 3, 4]))
    correct = (
        result == [0, False, ""]
        and result[0] is not False
        and result[1] is False
        and calls == [0, 1, 2, 3]
    )
    evidence = {
        "actual_result": repr(result),
        "calls": calls,
        "expected_result": "[0, False, '']",
        "boundary_correct": correct,
    }
    write(root / ".agent/primary-boundary-observation.json", evidence)
    print(json.dumps(evidence))


if __name__ == "__main__":
    run(Path(sys.argv[1]).resolve())
