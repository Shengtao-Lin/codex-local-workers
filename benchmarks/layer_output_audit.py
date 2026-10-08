"""Offline adjudication of frozen output; never reruns models or rewrites scores."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import layer_isolation as LAYER
import mixed_feature_benchmark as MIXED
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "roleq-layer-output-audit-1"
BOUNDARY_TEST = """from product.codec import encode_segment
from product.target import path_for


def test_plus_must_be_percent_encoded():
    assert encode_segment("a+b") == "a%2Bb"
    assert path_for("a+b") == "/items/a%2Bb"
"""


def unwrap_fence(raw):
    """Only remove one complete outer JSON fence; never repair quotes or code."""
    stripped = raw.strip()
    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0] in {"```json", "```"} and lines[-1] == "```":
        if any("```" in line for line in lines[1:-1]):
            raise ValueError("nested fence")
        return "\n".join(lines[1:-1]), True
    return raw, False


def main():
    BASE.mkdir(exist_ok=False)
    manifest = read(LAYER.BASE / "manifest.json")
    for path, sha in manifest["drivers"].items():
        if digest(Path(path)) != sha:
            raise ValueError("direct driver drift")
        dest = BASE / "direct-driver-snapshot" / Path(path).relative_to(KIT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    LAYER.verify_hashes(LAYER.SNAPSHOT, read(LAYER.SNAPSHOT / "freeze.json")["files"])
    data = read(LAYER.BASE / "corpus.json")
    write(BASE / "corpus.json", data)
    write(
        BASE / "manifest.json",
        {
            "classification": "Post-hoc offline interpretation only; original format failures and validation scores unchanged",
            "feature_id": "layer-output-audit",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "contracts": ["no-code-repair", "no-history-overwrite", "no-acceptance"],
            "risk_rationale": "Replay generated code in new trusted-local workspaces with unchanged production edit guards",
            "model_calls": 0,
            "qualification_credit": False,
            "driver_sha256": digest(Path(__file__)),
            "source_manifest_sha256": digest(LAYER.BASE / "manifest.json"),
            "boundary_test": BOUNDARY_TEST,
            "fixture_gap": "Original encoded-path checks roundtrip/slash but not canonical encoding of plus; extra assertion is independent, not a rewrite of frozen tests.",
            "exposure_correction": "duration-pair reuses the previously exposed ASCII-digit semantic family; all eight cases already had zero qualification credit.",
        },
    )
    MIXED.CORPUS, MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    worker = load_worker(LAYER.SNAPSHOT)
    results = []
    for cell in manifest["cells"]:
        original = read(LAYER.BASE / f"{cell['id']}-result.json")
        if original["format_pass"] and cell["case"] != "encoded-path":
            continue
        oldroot = Path(cell["root"])
        response_path = oldroot / ".agent/model-response.json"
        raw = read(response_path)["raw"]
        result = {
            "cell": cell["id"],
            "original_format_pass": original["format_pass"],
            "original_response_sha256": digest(response_path),
            "semantic_evaluated": False,
            "original_result_sha256": digest(LAYER.BASE / f"{cell['id']}-result.json"),
            "primary_accepted": False,
        }
        try:
            normalized, removed = unwrap_fence(raw)
            packet = read(oldroot / ".agent/qual-unit-reference.json")
            patch = LAYER.parse_patch(normalized, packet["scope"]["modify"])
        except ValueError as error:
            result["error"] = str(error)
            results.append(result)
            continue
        root = Path(
            MIXED.prepare(
                cell["case"],
                cell["repetition"],
                LAYER.SNAPSHOT / ".local-agents/config.json",
                "loa1",
            )["root"]
        )
        packet = read(root / ".agent/qual-unit-reference.json")
        config = read(root / ".agent/config.json")
        # New independent assertion supplements, never edits, original protection.
        if cell["case"] == "encoded-path":
            extra = root / "tests/test_primary_boundary.py"
            with extra.open("x", encoding="utf-8") as stream:
                stream.write(BOUNDARY_TEST)
            packet["scope"]["readonly"].append("tests/test_primary_boundary.py")
            packet["focused_tests"].append("tests/test_primary_boundary.py")
        protected = {p: digest(root / p) for p in packet["scope"]["readonly"]}
        runtime = worker.WorkerRuntime(root, packet, config, None)
        try:
            runtime.write_lock.acquire()
            runtime._prepare_run_archive()
            for item in patch:
                path = item["path"]
                observed = runtime.read_file({"path": path})
                runtime.safe_replace(
                    {
                        "path": path,
                        "expected_sha256": observed["sha256"],
                        "find": (root / path).read_text(encoding="utf-8"),
                        "replace": item["content"],
                    }
                )
            result["validation"] = LAYER.check(root, "independent-audit")
            LAYER.verify_hashes(root, protected)
            result.update(
                semantic_evaluated=True,
                fence_removed=removed,
                root=str(root),
                protected_unchanged=True,
            )
        finally:
            runtime.close()
        write(root / "audit.json", result)
        results.append(result)
    write(BASE / "results.json", results)
    print(
        json.dumps(
            [
                {
                    "cell": r["cell"],
                    "evaluated": r["semantic_evaluated"],
                    "semantic_pass": r.get("validation", {}).get("semantic_pass"),
                    "error": r.get("error"),
                }
                for r in results
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
