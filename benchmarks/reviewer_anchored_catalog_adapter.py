"""Optional anchor-centered handles formed only from actual displayed read lines."""

import argparse
import copy
import importlib.util
import sys
from pathlib import Path

from reviewer_catalog_staged_adapter import install as install_catalog
from reviewer_dependency_evidence_adapter import install as install_dependencies
from reviewer_dependency_investigation_adapter import install as install_investigation
from reviewer_evidence_catalog_adapter_v2 import EvidenceCatalog
from reviewer_range_staged_adapter import install as install_range
from reviewer_required_tool_adapter import install as install_required
from reviewer_sampling_probe_adapter import install as install_probe


class AnchoredCatalog(EvidenceCatalog):
    def observe_anchors(self, read_lines, hashes, path, content, anchors):
        added = []
        if not isinstance(content, str):
            return added
        for display in content.splitlines():
            prefix, separator, text = display.partition(": ")
            if not separator or not prefix.isdecimal():
                continue
            number = int(prefix)
            if number not in read_lines.get(path, set()):
                continue
            for anchor in anchors:
                if not isinstance(anchor, str) or not anchor or anchor not in text:
                    continue
                end = number
                while end < number + 19 and end + 1 in read_lines[path]:
                    end += 1
                key = (path, hashes[path], number, end)
                if key in self.keys:
                    continue
                evidence_id = "E" + str(len(self.entries) + 1)
                self.keys[key] = evidence_id
                entry = {
                    "id": evidence_id,
                    "path": path,
                    "start_line": number,
                    "end_line": end,
                    "source_hash": hashes[path],
                    "navigation_anchor": anchor,
                    "anchor_window": True,
                }
                self.entries[evidence_id] = entry
                added.append(copy.deepcopy(entry))
        return added


def install(reviewer):
    original_init = reviewer.ReviewerRuntime.__init__
    original_read = reviewer.ReviewerRuntime.read_file

    def init(runtime, *args, **kwargs):
        original_init(runtime, *args, **kwargs)
        runtime.evidence_catalog = AnchoredCatalog()

    def read(runtime, args):
        result = original_read(runtime, args)
        path = result["path"]
        anchors = [
            target.get("anchor")
            for target in runtime.packet["edit_targets"]
            if target.get("path") == path
        ]
        result["new_source_evidence"].extend(
            runtime.evidence_catalog.observe_anchors(
                runtime.read_lines,
                runtime.observed_read_hashes,
                path,
                result.get("content"),
                anchors,
            )
        )
        return result

    reviewer.ReviewerRuntime.__init__ = init
    reviewer.ReviewerRuntime.read_file = read


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--staged", action="store_true")
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "anchored_catalog_reviewer", args.snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    (install_range if args.staged else install_dependencies)(reviewer)
    install_investigation(reviewer)
    install_catalog(reviewer)
    install(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
