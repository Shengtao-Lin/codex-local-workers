"""Primary-only read-only semantic probe; never part of worker context or retries."""

import argparse
import sys
from pathlib import Path

import harness_convergence as B


def main(root, output):
    source = root / "src/evaluation_harness/adapters/common.py"
    before_hash = B.sha(source)
    sys.path.insert(0, str(root / "src"))
    from evaluation_harness.adapters.common import collect_tools
    from evaluation_harness.canonical.models import (
        CanonicalMessage,
        ToolCallPart,
        ToolResultPart,
    )

    rows = []
    for value in (None, False, 0, "", [], {}):
        messages = [
            CanonicalMessage(
                message_id="probe",
                role="assistant",
                content=[
                    ToolCallPart(call_id="known", name="tool", arguments={}),
                    ToolResultPart(call_id="known", result=value),
                ],
            )
        ]
        original = [message.model_dump() for message in messages]
        result = collect_tools(messages)
        rows.append(
            {
                "input_result": value,
                "observed": [call.model_dump(mode="json") for call in result],
                "expected_status": "succeeded",
                "expected_result": value,
                "satisfies_explicit_falsy_contract": len(result) == 1
                and result[0].status == "succeeded"
                and result[0].result == value,
                "input_unchanged": original
                == [message.model_dump() for message in messages],
            }
        )
    assert B.sha(source) == before_hash
    B.save(
        output,
        {
            "source_sha256": before_hash,
            "source_unchanged": True,
            "rows": rows,
            "fixed_protected_tests_not_modified": True,
            "primary_probe_not_a_model_retry": True,
        },
    )
    print(
        {
            "source": str(source),
            "passed": sum(row["satisfies_explicit_falsy_contract"] for row in rows),
            "total": len(rows),
        },
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.root.resolve(), args.output.resolve())
