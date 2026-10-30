"""Offline candidate: count real TRACE graph evidence, never grant citation rights."""


def trace_progress(observation, seen):
    if observation.get("status") != "ok":
        return observation
    edges = set()
    for category in ("definitions", "incoming", "outgoing"):
        for row in observation.get(category, []):
            path, line = row.get("path"), row.get("line")
            if not isinstance(path, str) or type(line) is not int or line < 1:
                continue
            edges.add(
                (
                    category,
                    path,
                    line,
                    row.get("symbol"),
                    row.get("caller"),
                    row.get("callee"),
                )
            )
    new = edges - seen
    seen.update(edges)
    result = {**observation, "new_trace_evidence_count": len(new)}
    if new:
        # Existing no-progress predicate recognizes `files`. These paths already
        # occur in trusted TRACE rows; read/display/citation authority is unchanged.
        result["files"] = sorted({edge[1] for edge in new})
    return result


def install(module):
    base = module.ExplorerRuntime

    class TraceProgressRuntime(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._trace_graph_seen = set()

        def execute(self, name, args):
            observation, final = super().execute(name, args)
            if name == "TRACE" and final is None:
                observation = trace_progress(observation, self._trace_graph_seen)
            return observation, final

    module.ExplorerRuntime = TraceProgressRuntime
    return TraceProgressRuntime


if __name__ == "__main__":
    import json
    from pathlib import Path

    import bounded_evidence_support as S

    batch = (
        S.KIT / "benchmarks/work/harness-convergence/strata-trace-progress-20261023-1"
    )
    origin = (
        S.KIT
        / "benchmarks/work/harness-convergence/strata-explorer-20261023-4/hash-1/isolated/.agent/strata-wire"
    )
    found = None
    for path in sorted(origin.glob("*.request.json")):
        for message in S.read(path)["messages"]:
            content = message.get("content", "")
            if not content.startswith("OBSERVATION\n"):
                continue
            try:
                value = json.loads(content.partition("\n")[2])
            except ValueError:
                continue
            if value.get("symbol") == "request_hash" and value.get("definitions"):
                found = path, value
                break
        if found:
            break
    assert found is not None
    path, value = found
    legacy = bool(value.get("files", value.get("results", value.get("content", ""))))
    adjusted = trace_progress(value, set())
    corrected = bool(
        adjusted.get("files", adjusted.get("results", adjusted.get("content", "")))
    )
    assert not legacy and corrected
    S.save(
        batch / "actual-observation-replay.json",
        {
            "source": str(path),
            "sha256": S.sha(path),
            "observation": value,
            "legacy_progress": legacy,
            "candidate_progress": corrected,
            "new_trace_evidence_count": adjusted["new_trace_evidence_count"],
            "model_calls": 0,
            "counterfactual_live_acceptance": None,
            "candidate_sha256": S.sha(Path(__file__)),
        },
    )
    print(
        "Actual request_hash TRACE replay: legacy false, candidate true; zero model calls"
    )
