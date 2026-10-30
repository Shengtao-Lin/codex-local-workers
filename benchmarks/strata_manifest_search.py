"""Offline candidate: directory SEARCH over exact approved files, NOT a walk.

Keeps ApprovedEvidence's read/duplicate/evidence limits and current host scope.
No production/default change; not wired into the closed first live candidate.
"""

import json
from pathlib import PurePosixPath

from approved_evidence import ApprovedEvidence


class ManifestSearchEvidence(ApprovedEvidence):
    def perform(self, value):
        if set(value) != {"search"}:
            return super().perform(value)
        args = value["search"]
        if not isinstance(args, dict):
            return super().perform(value)
        path = args.get("path")
        if path in self.paths:
            return super().perform(value)
        p = PurePosixPath(path) if isinstance(path, str) else None
        if (
            p is None
            or not p.parts
            or p.is_absolute()
            or str(p) != path
            or ".." in p.parts
            or "\\" in path
            or ":" in path
            or p.parts[0] not in {"src", "tests", "docs"}
        ):
            raise self.policy_error("Search root outside approved manifest")
        # Never enumerate a directory. Only select already-approved exact files.
        selected = [name for name in self.paths if name.startswith(path + "/")]
        if not selected:
            raise self.policy_error("No approved facts under search root")
        self.runtime._assert_read_allowed(path)
        if (
            set(args) != {"path", "query"}
            or not isinstance(args["query"], str)
            or not 1 <= len(args["query"]) <= 200
        ):
            raise ValueError("SEARCH requires a bounded literal query")
        r = self.runtime
        if r.ledger["evidence_actions"] >= self.max_actions:
            raise self.progress_error(f"{self.max_actions} evidence requests exhausted")
        matches, hashes, scanned = [], {}, []
        for name in selected:
            self.check_path(name)
            before = r.editor.read_bytes(name)[1]
            result = r.search(
                {
                    "path": name,
                    "query": args["query"],
                    "mode": "literal",
                    "max_results": 10 - len(matches),
                }
            )
            after = r.editor.read_bytes(name)[1]
            if before != after:
                raise self.policy_error("Evidence source changed during search")
            for hit in result.get("results", []):
                if hit.get("path") != name:
                    raise self.policy_error("Search result escaped exact file")
            matches.extend(result.get("results", []))
            if len(matches) > 10:
                raise self.policy_error("Search result cap exceeded")
            scanned.append(name)
            hashes[name] = after
            if len(matches) == 10:
                break
        r.ledger["evidence_actions"] += 1
        item = {
            "request": value,
            "observation": {
                "results": matches,
                "scanned_approved_files": scanned,
                "remaining_approved_files": len(selected) - len(scanned),
                "scope": "exact approved manifest only, not repository-wide search",
            },
            "hashes": hashes,
        }
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
