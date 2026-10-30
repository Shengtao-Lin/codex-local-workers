"""Real R4 artifact controls; no model calls or fixture edits."""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r4_prepare as H


def test_admission_and_fixed_denominator():
    assert H.B.read(H.S.BATCH / "decision.json")["candidate_accepted"] == 6
    assert len(H.ORDER) == len(set(H.ORDER)) == 12
    assert sum("-candidate-" in name for name in H.ORDER) == 6
    assert H.B.read(H.REVIEWER_REGISTRATION)["registered"] == 16
    assert H.B.read(H.BATCH / "controls-approved.json")["ready"]


@pytest.mark.parametrize("topic", H.TOPICS)
def test_copied_tests_keep_exact_ast_and_reference_source(topic):
    original = H.P.BATCH / "holdouts-v2" / topic
    for arm in ("visible", "private-reference"):
        prepared = H.BATCH / "prepared-fixtures" / topic / arm
        for source in (original / arm / "src").rglob("*.py"):
            assert H.B.sha(source) == H.B.sha(
                prepared / source.relative_to(original / arm)
            )
        for test in (original / arm / "tests").glob("*.py"):
            before = ast.dump(
                ast.parse(test.read_text(encoding="utf-8")), include_attributes=False
            )
            after = ast.dump(
                ast.parse((prepared / "tests" / test.name).read_text(encoding="utf-8")),
                include_attributes=False,
            )
            assert before == after


def test_all_packets_have_same_pair_contract_and_protected_tests():
    for topic in H.TOPICS:
        for repeat in (1, 2):
            packets = []
            for arm in ("baseline", "candidate"):
                root = H.BATCH / "cases" / f"{topic}-{arm}-{repeat}" / "isolated"
                packet = H.B.read(root / ".agent/packet.json")
                config = H.B.read(root / ".agent/config.json")
                assert packet["risk"]["unit"] == "high"
                assert packet["limits"]["hard_max_model_turns"] == 6
                assert config["max_local_repairs"] == 2
                assert len(packet["scope"]["modify"]) == 1
                assert not packet["scope"]["create"]
                assert set(packet["focused_tests"]) <= set(packet["scope"]["readonly"])
                assert (
                    packet["required_behavior"][0]["implementation_ref"]["path"]
                    == packet["scope"]["modify"][0]
                )
                assert not (root / "private-reference").exists()
                assert not any(
                    "private-reference" in path for path in packet["scope"]["read"]
                )
                packet.pop("run_id")
                packets.append(packet)
            assert packets[0] == packets[1]


def test_both_arms_wrong_source_still_rejected(tmp_path):
    original = H.BATCH / "prepared-fixtures/datetime/visible"
    path = "src/evaluation_harness/adapters/common.py"
    expected = {path: H.B.sha(original / path)}
    for arm in ("baseline", "candidate"):
        root = tmp_path / arm
        wrong = root / path
        wrong.parent.mkdir(parents=True)
        wrong.write_text("# identical wrong source in both arms\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Frozen paths changed"):
            H.R.assert_files(root, expected)


def test_candidate_runtime_not_retuned_for_holdouts():
    original = H.B.read(H.S.BATCH / "live-freeze-approved.json")
    H.R.assert_files(H.B.KIT, original["candidate_and_driver"])
    for name in H.ORDER:
        if "-candidate-" not in name:
            continue
        root = H.BATCH / "cases" / name / "isolated"
        for path, digest in original["candidate_and_driver"].items():
            if path.startswith(".local-agents/") and "/tests/" not in path:
                assert H.B.sha(root / path) == digest
