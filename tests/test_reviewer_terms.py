"""Fixed terms/source factorial retains all original semantics and provenance."""

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_reviewer_terms as H


def rows():
    return H.B.read(H.BATCH / "registration.json")["cells"]


def normalized(packet):
    value = copy.deepcopy(packet)
    value.pop("run_id")
    return json.loads(json.dumps(value).replace(H.NEW_TERM, H.OLD_TERM))


def test_only_one_contract_term_differs_and_no_answer_is_inserted():
    packets = []
    for row in rows():
        root = Path(row["root"])
        packet = H.B.read(root / ".agent/packet.json")
        raw = json.dumps(packet)
        assert "None" not in packet["goal"]
        assert raw.count(H.NEW_TERM) == (3 if row["wording"] == "clarified" else 0)
        assert raw.count(H.OLD_TERM) == (3 if row["wording"] == "original" else 0)
        assert "draft" not in raw and "reference" not in packet["goal"]
        packets.append(normalized(packet))
    assert all(packet == packets[0] for packet in packets)


def test_same_sources_tests_configs_for_matched_cells_and_known_oracles():
    source_hashes = {}
    test_hashes = set()
    configs = []
    for row in rows():
        root = Path(row["root"])
        source_hashes.setdefault(row["implementation"], set()).add(
            H.B.sha(root / H.TARGET)
        )
        test_hashes.add(H.B.sha(root / "tests/test_collect_tools.py"))
        configs.append(H.B.read(root / ".agent/experiment-config.json"))
        H.R.assert_files(root, row["files"])
    assert len(test_hashes) == 1 and all(config == configs[0] for config in configs)
    old = H.E.D.OLD.H.BATCH
    reference = old / "prepared-fixtures/collect_tools/private-reference" / H.TARGET
    assert (
        H.B.sha(reference)
        == H.B.read(old / "reference-falsy-probe.json")["source_sha256"]
    )
    assert source_hashes["reference"] == {
        hashlib.sha256(reference.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    }
    assert source_hashes["draft"] == {
        H.B.read(old / "candidate-falsy-probe.json")["source_sha256"]
    }
    assert len(rows()) == 8
    for wording in ("original", "clarified"):
        assert (
            sum(
                r["wording"] == wording and r["implementation"] == "draft"
                for r in rows()
            )
            == 2
        )
        assert (
            sum(
                r["wording"] == wording and r["implementation"] == "reference"
                for r in rows()
            )
            == 2
        )


def test_archives_are_actual_validated_primary_fixtures_not_model_results():
    for row in rows():
        root = Path(row["root"])
        build = H.B.read(root.parent / "fixture-build.json")
        assert (
            build["synthetic_primary_archive"] and build["live_coder_model_calls"] == 0
        )
        assert build["static_fixture_materializations"] == 1
        run = root / ".agent/tasks/semantic-terms/runs" / row["identity"]["run_id"]
        validation = H.B.read(run / "validation.json")
        assert validation["status"] == "passed"
        assert validation["focused_tests"]["junit"]["executed"] > 0
        assert validation["contract_check"] is None
        assert all(
            check["status"] == "passed" for check in validation["configured_checks"]
        )
        assert (
            not (run / "review.json").exists()
            and not (run / "host-review-dispatch.json").exists()
        )
        assert not (root / "static-fixture.json").exists()
        assert not (root / "registration.json").exists()


def test_unmodified_reviewer_and_host_verifier_accept_all_preconditions():
    for row in rows():
        root = Path(row["root"])
        config = H.B.read(root / ".agent/experiment-config.json")
        module = H.R.load(
            root / ".local-agents/reviewer-runtime.py",
            "terms_precondition_" + row["id"],
        )
        runtime = H.PREV.A.install(module)(
            root, row["identity"], config, type("NoModel", (), {"native_tools": None})()
        )
        assert runtime.max_turns == 16 and runtime.max_protocol_errors == 4
        payload = runtime.initial_payload()
        assert "expected_decision" not in json.dumps(payload)
        assert "static-fixture" not in json.dumps(payload)
        assert not runtime.read_lines
