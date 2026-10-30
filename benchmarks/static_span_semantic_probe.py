"""Read-only contract counterexample, never modifies frozen acceptance tests."""

import json
from pathlib import Path

import capture_fixture_support as F
import static_span_trial as S


def run():
    baseline = Path(
        S.T.read(S.D.S.O.M.BATCH / "prepared-cells-v3.json")["metadata-candidate-1"][
            "root"
        ]
    )
    candidate = Path(S.T.read(S.BATCH / "cells.json")["new-1"]["root"])
    rows = []
    for label, root in (("original", baseline), ("candidate", candidate)):
        path = root / "src/product/metadata.py"
        module = F.load(path, "cyclic_metadata_probe_" + label)
        observations = []
        for kind in ("mapping_self_cycle", "list_self_cycle", "shared_noncyclic_child"):
            if kind == "mapping_self_cycle":
                value = {}
                value["self"] = value
                intact = lambda value=value: value["self"] is value and len(value) == 1
            elif kind == "list_self_cycle":
                child = []
                child.append(child)
                value = {"child": child}
                intact = lambda value=value: value["child"][0] is value["child"]
            else:
                child = {"ok": [False, 0, None, ""]}
                value = {"first": child, "second": child}
                intact = lambda value=value: (
                    value["first"] is value["second"]
                    and value["first"] == {"ok": [False, 0, None, ""]}
                )
            try:
                result = module.validate_metadata(value)
                outcome = {"kind": "returned", "same_mapping": result is value}
            except (ValueError, RecursionError) as exc:
                outcome = {
                    "kind": "raised",
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "is_ValueError": isinstance(exc, ValueError),
                }
            observations.append(
                {"case": kind, "outcome": outcome, "input_topology_unchanged": intact()}
            )
        rows.append(
            {
                "label": label,
                "source": str(path),
                "sha256": S.T.sha(path),
                "observations": observations,
            }
        )
    assert all(o["input_topology_unchanged"] for r in rows for o in r["observations"])
    assert all(
        o["outcome"]["type"] == "ValueError" for o in rows[0]["observations"][:2]
    )
    assert all(
        o["outcome"]["type"] == "RecursionError" for o in rows[1]["observations"][:2]
    )
    S.T.save(
        S.BATCH / "primary-semantic-counterexample.json",
        {
            "authority": "Independent Primary probe after frozen live candidate; no tests/candidate edits",
            "owned_contract_id": "metadata",
            "contract_quote": "in addition to its existing non-JSON rejection",
            "classification": "Primary-confirmed implementation compatibility defect, not schema/patch/timeout failure",
            "observations": rows,
            "model_calls": 0,
            "fixed_tests_changed": False,
            "finding": {
                "id": "PRIMARY-METADATA-CYCLE-1",
                "severity": "medium",
                "category": "correctness",
                "source_anchor": "check_finite(value)",
                "cause": "Unbounded recursive prewalk executes before json.dumps can reject circular references via the existing ValueError handler",
                "bounded_fix": "Preserve original invalid/circular-input rejection while rejecting nonfinite floats; do not mutate inputs or change protected tests",
            },
        },
    )
    print(
        json.dumps(
            {
                "original_cycles": "ValueError",
                "candidate_cycles": "RecursionError",
                "read_only": True,
            }
        )
    )


if __name__ == "__main__":
    run()
