"""Small opt-in evidence window over the existing worker's read/search guards."""

import json
from pathlib import PurePosixPath


class ApprovedEvidence:
    max_actions = 4
    def __init__(self, runtime, *, policy_error, progress_error):
        self.runtime = runtime
        self.policy_error = policy_error
        self.progress_error = progress_error
        paths = runtime.config.get("experimental_evidence_files")
        if (
            not isinstance(paths, list)
            or not 1 <= len(paths) <= 30
            or not all(isinstance(p, str) for p in paths)
            or len(set(paths)) != len(paths)
        ):
            raise ValueError("Exact approved evidence file manifest required")
        self.paths = sorted(paths)
        self.observations = []
        self.keys = set()
        self.duplicate_streak = 0
        runtime.ledger["evidence_actions"] = 0
        for path in self.paths:
            self.check_path(path)

    def check_path(self, path):
        p = PurePosixPath(path) if isinstance(path, str) else None
        if (
            p is None
            or path not in self.paths
            or p.is_absolute()
            or ".." in p.parts
            or "\\" in path
            or ":" in path
            or p.parts[0] not in {"src", "tests", "docs"}
        ):
            raise self.policy_error("Evidence outside exact approved fact manifest")
        relative, resolved = self.runtime._assert_read_allowed(path)
        if relative != path or not resolved.is_file():
            raise self.policy_error("Evidence must name an approved existing file")

    def state(self):
        current = []
        for item in self.observations:
            if all(
                self.runtime.editor.read_bytes(p)[1] == sha
                for p, sha in item["hashes"].items()
            ):
                current.append(item)
        return {
            "approved_evidence_files": self.paths,
            "evidence_observations": current,
            "stale_observations_omitted": len(self.observations) - len(current),
        }

    def perform(self, value):
        r = self.runtime
        if r.ledger["evidence_actions"] >= self.max_actions:
            raise self.progress_error(f"{self.max_actions} evidence requests exhausted")
        name = next(iter(value))
        args = value[name]
        if not isinstance(args, dict):
            raise ValueError("Evidence arguments must be an object")  # noqa: TRY004 - protocol recovery uses ValueError
        self.check_path(args.get("path"))
        if name == "read":
            if (
                set(args) != {"path", "start_line", "end_line"}
                or type(args["start_line"]) is not int
                or type(args["end_line"]) is not int
                or not 1 <= args["start_line"] <= args["end_line"]
                or args["end_line"] - args["start_line"] + 1 > 120
            ):
                raise ValueError("READ requires 1..120 lines")
            result = r.read_file(args)
        elif name == "search":
            if (
                set(args) != {"path", "query"}
                or not isinstance(args["query"], str)
                or not 1 <= len(args["query"]) <= 200
            ):
                raise ValueError("SEARCH requires a bounded literal query")
            result = r.search({**args, "mode": "literal", "max_results": 10})
        else:
            raise ValueError("Only read/search evidence actions allowed")
        r.ledger["evidence_actions"] += 1
        for key in ("next_step", "navigation_hint", "source_context"):
            result.pop(key, None)
        paths = {args["path"]} | {item["path"] for item in result.get("results", [])}
        for path in paths:
            self.check_path(path)
        hashes = {p: r.editor.read_bytes(p)[1] for p in paths}
        item = {"request": value, "observation": result, "hashes": hashes}
        self.observations.append(item)
        r.RUN_STATE.write_json_once(
            r.archive.run_root / f"evidence-{r.ledger['requests']}.json", item
        )
        key = json.dumps([value, hashes], sort_keys=True)
        self.duplicate_streak = self.duplicate_streak + 1 if key in self.keys else 0
        self.keys.add(key)
        if self.duplicate_streak >= 2:
            raise self.progress_error(
                "Three duplicate evidence requests made no progress"
            )
