"""Re-observe the four already archived legacy-equivalence probes, read-only."""

import argparse
import copy
import json
import sys
from pathlib import Path


def observe(root):
    root = Path(root).resolve()
    sys.path.insert(0, str(root / "src"))
    from evaluation_harness.adapters import common

    assert Path(common.__file__).resolve().is_relative_to(root)

    def result(part):
        value = {"id": "fixed", "role": "assistant", "content": copy.deepcopy(part)}
        before = copy.deepcopy(value)
        try:
            parsed = common.parse_message("probe", 0, value)
            return {
                "kind": "return",
                "content": [p.model_dump(mode="json") for p in parsed.content],
                "input_unchanged": value == before,
            }
        except (common.AdapterError, ValueError, TypeError) as error:
            return {
                "kind": "error",
                "type": type(error).__name__,
                "input_unchanged": value == before,
            }

    rows = []
    for part in (
        {"type": "text", "text": None},
        {"type": "text"},
        {"type": "tool_call"},
        {"type": "tool_result"},
    ):
        single, wrapped = result(part), result([part])
        rows.append(
            {
                "part": part,
                "single": single,
                "singleton_list": wrapped,
                "equivalent": single == wrapped,
            }
        )
    return {"module": str(Path(common.__file__).resolve()), "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(observe(args.root), ensure_ascii=False))
