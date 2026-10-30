import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import reviewer_matched_low_probe as H


def test_only_reasoning_directive_changes_in_all_four_cells():
    old = H.B.read(H.OLD / "registration.json")
    new = H.B.read(H.BATCH / "registration.json")
    assert len(old["cells"]) == len(new["cells"]) == 4
    for before, after in zip(old["cells"], new["cells"], strict=True):
        assert {k: v for k, v in before.items() if k != "messages_sha256"} == {
            k: v for k, v in after.items() if k != "messages_sha256"
        }
        messages = H.B.read(H.BATCH / "cells" / after["id"] / "messages.json")
        expected = copy.deepcopy(
            H.B.read(H.OLD / "cells" / before["id"] / "messages.json")
        )
        expected[0]["content"] = expected[0]["content"].replace(H.FROM, H.TO)
        assert messages == expected
        assert messages[0]["content"].endswith(H.TO)
        assert (
            H.B.sha(H.BATCH / "cells" / after["id"] / "messages.json")
            == after["messages_sha256"]
        )


def test_exact_directive_matches_frozen_production_runtime():
    row = H.B.read(H.BATCH / "registration.json")["cells"][0]
    runtime_source = (
        Path(row["origin_root"]) / ".local-agents/reviewer-runtime.py"
    ).read_text(encoding="utf-8")
    assert 'prompt += f"Reasoning strength: {strength}.\\n"' in runtime_source
    assert H.TO == "Reasoning strength: low."
    assert (
        H.B.read(Path(row["origin_root"]) / ".agent/experiment-config.json")[
            "reviewer_reasoning_strength"
        ]
        == "low"
    )


def test_template_audit_does_not_claim_active_render_or_budget_change():
    audit = H.B.read(H.BATCH / "reasoning-template-audit.json")
    assert audit["active_rendered_prompt"] == "not_observed"
    assert not audit["model_settings_modified"]
    assert H.B.read(H.BATCH / "registration.json")["no_acceptance_or_holdout_credit"]
