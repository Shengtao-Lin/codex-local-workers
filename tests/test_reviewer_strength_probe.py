import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import reviewer_strength_probe as H


def test_only_strength_changes_and_all_inputs_are_source_matched():
    rows = H.B.read(H.BATCH / "registration.json")["cells"]
    assert len(rows) == 8
    for row in rows:
        messages = H.B.read(H.BATCH / "cells" / row["id"] / "messages.json")
        expected = H.B.read(
            H.OLD / "cells" / row["matched_low_origin"] / "messages.json"
        )
        expected[0]["content"] = expected[0]["content"].replace(
            H.L.TO, f"Reasoning strength: {row['strength']}."
        )
        assert messages == expected
        assert (
            H.B.sha(H.BATCH / "cells" / row["id"] / "messages.json")
            == row["messages_sha256"]
        )
        config = H.B.read(Path(row["origin_root"]) / ".agent/experiment-config.json")
        assert config["reviewer_model"] == "meta/muse-glimmer"
        assert config["reviewer_max_tokens"] == 4096
        assert config["reviewer_temperature"] == 1.0


def test_fixed_balanced_order_and_no_new_holdout_credit():
    registry = H.B.read(H.BATCH / "registration.json")
    rows = registry["cells"]
    assert [(r["strength"], r["matched_low_origin"]) for r in rows] == H.ORDER
    for strength in ("medium", "high"):
        for implementation in ("draft", "reference"):
            assert (
                sum(
                    r["strength"] == strength and r["implementation"] == implementation
                    for r in rows
                )
                == 2
            )
    assert registry["no_acceptance_or_holdout_credit"]
    assert registry["usage_ceiling"] == 45
