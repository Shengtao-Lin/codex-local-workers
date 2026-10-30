import copy
from unittest.mock import patch
from . import reviewer_semantic_entry as V1

PROTOCOL = "reviewer-semantic-transport-v2"
ORIGINAL_ASSEMBLE = V1.assemble


def assemble(runtime, args, error):
    working = copy.deepcopy(args)
    normalizations, file_level = ([], set())
    if isinstance(working, dict) and isinstance(working.get("obligations"), list):
        for row in working["obligations"]:
            if not isinstance(row, dict) or row.get("verdict") not in {
                "implementation_defect",
                "required_test_gap",
            }:
                continue
            ids = row.get("evidence_ids")
            if not isinstance(ids, list) or any(
                (not isinstance(key, str) or key not in runtime.evidence_catalog for key in ids)
            ):
                raise error("location requires actually displayed evidence IDs")
            refs = {key: runtime.evidence_catalog[key] for key in ids}
            line = row.get("line")
            if line is None and row["verdict"] == "required_test_gap":
                selected = {
                    ref["path"]
                    for ref in refs.values()
                    if ref["path"] in runtime.focused_test_paths()
                }
                if len(selected) != 1:
                    raise error("file-level required-test gap needs one selected focused-test file")
                path = next(iter(selected))
                chosen = next((key for key, ref in refs.items() if ref["path"] == path))
                file_level.add(row["id"])
                row["line"] = refs[chosen]["start_line"]
            else:
                if type(line) is not int or line < 1:
                    raise error("implementation defect needs a real displayed source line")
                candidates = [
                    key for key, ref in refs.items() if ref["start_line"] <= line <= ref["end_line"]
                ]
                if ids and ids[0] in candidates:
                    candidates = [ids[0]]
                locations = {(refs[key]["path"], line) for key in candidates}
                if len(locations) != 1:
                    raise error(
                        "defect line must identify one unambiguous selected source location"
                    )
                chosen = candidates[0]
            original = list(ids)
            row["evidence_ids"] = [chosen, *[key for key in ids if key != chosen]]
            normalizations.append(
                {
                    "obligation_id": row["id"],
                    "selected_evidence_ids": original,
                    "finding_evidence_id": chosen,
                    "file_level_absence": row["id"] in file_level,
                    "model_line": line,
                }
            )
    result = ORIGINAL_ASSEMBLE(runtime, working, error)
    for finding in result["findings"]:
        if finding["contract_id"] in file_level:
            finding["line"] = None
    kinds = {row["verdict"] for row in working["obligations"]}
    if result["findings"] and (not kinds & {"contract_conflict", "uncertain"}):
        result["assessment"] = (
            "implementation_defect" if "implementation_defect" in kinds else "required_test_gap"
        )
    runtime.location_normalizations = normalizations
    return result


def install(module):
    base = V1.install(module)

    class TransportReviewer(base):
        def validate_report(self, args):
            report = super().validate_report(args)
            report["semantic_transport_protocol"] = PROTOCOL
            report["location_normalizations"] = copy.deepcopy(
                getattr(self, "location_normalizations", [])
            )
            return report

        def run(self):
            with patch.object(V1, "assemble", assemble):
                return super().run()

    module.ReviewerRuntime = TransportReviewer
    return TransportReviewer
