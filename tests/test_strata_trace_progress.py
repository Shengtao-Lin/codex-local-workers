import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from strata_trace_progress import trace_progress


def legacy_progress(value):
    # Exact predicate observed at ExplorerRuntime.run's no-progress gate.
    return bool(value.get("files", value.get("results", value.get("content", ""))))


def observation(symbol):
    return {
        "status": "ok",
        "symbol": symbol,
        "definitions": [{"path": "src/a.py", "line": 10, "symbol": symbol}],
        "incoming": [
            {"path": "src/b.py", "line": 20, "caller": "caller", "callee": symbol}
        ],
        "outgoing": [],
        "observed_files": ["src/a.py", "src/b.py"],
    }


def test_legacy_gate_misses_valid_trace_graph():
    assert not legacy_progress(observation("request_hash"))


def test_three_distinct_trace_symbols_are_real_progress_without_new_permissions():
    seen = set()
    for name in ("request_hash", "submit_job", "canonical_json"):
        original = observation(name)
        before = copy.deepcopy(original)
        result = trace_progress(original, seen)
        assert legacy_progress(result)
        assert result["new_trace_evidence_count"] == 2
        assert original == before
        assert "source_refs" not in result and "citation_rights" not in result


def test_identical_edges_do_not_keep_resetting_progress():
    seen = set()
    first = trace_progress(observation("f"), seen)
    assert legacy_progress(first)
    assert not legacy_progress(trace_progress(observation("f"), seen))


def test_empty_or_failed_trace_still_has_no_progress():
    seen = set()
    for value in (
        {"status": "ok", "definitions": [], "incoming": [], "outgoing": []},
        {"status": "error", "error": "scope denied"},
    ):
        assert not legacy_progress(trace_progress(value, seen))
    assert not seen
