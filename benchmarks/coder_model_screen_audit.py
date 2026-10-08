"""Offline replay of the archived no-op-containing response; no new inference."""

from pathlib import Path

import coder_model_screen as screen
from capability_fit import load_worker, write
from inherited_context_recovery import digest, read


def apply_complete_files(runtime, root, patch):
    skipped = []
    for item in patch:
        current = (root / item["path"]).read_text(encoding="utf-8")
        if current == item["content"]:
            skipped.append(item["path"])
            continue
        observed = runtime.read_file({"path": item["path"]})
        runtime.safe_replace(
            {
                "path": item["path"],
                "expected_sha256": observed["sha256"],
                "find": current,
                "replace": item["content"],
            }
        )
    return skipped


def audit():
    base = screen.BASE
    manifest = read(base / "manifest.json")
    cell = next(c for c in manifest["cells"] if c["id"] == "m2-encoded-path")
    source = Path(cell["root"]) / ".agent/response.json"
    directory = base / "offline-noop-audit-1"
    directory.mkdir(exist_ok=False)
    screen.FA.MIXED.CORPUS = base / "corpus.json"
    screen.FA.MIXED.WORK = directory / "runs"
    root = Path(
        screen.FA.MIXED.prepare(
            cell["case"], 1, screen.SNAPSHOT / ".local-agents/config.json", "audit"
        )["root"]
    )
    hashes = {
        p: sha for p, sha in cell["hashes"].items() if not p.startswith(".agent/")
    }
    screen.FA.LAYER.verify_hashes(root, hashes)
    packet = read(root / ".agent/qual-unit-reference.json")
    patch = screen.FA.LAYER.parse_patch(read(source)["raw"], packet["scope"]["modify"])
    for item in patch:
        compile(item["content"], item["path"], "exec")
    worker = load_worker(screen.SNAPSHOT)
    runtime = worker.WorkerRuntime(
        root, packet, read(root / ".agent/config.json"), None
    )
    try:
        runtime.write_lock.acquire()
        runtime._prepare_run_archive()
        skipped = apply_complete_files(runtime, root, patch)
        checks = screen.FA.LAYER.check(root, "independent")
        screen.FA.LAYER.verify_hashes(
            root,
            {p: sha for p, sha in hashes.items() if p not in packet["scope"]["modify"]},
        )
        write(
            directory / "result.json",
            {
                "response_path": str(source),
                "response_sha256": digest(source),
                "model_calls": 0,
                "skipped_identical_files": skipped,
                "semantic_pass": checks["semantic_pass"],
                "format_pass": True,
                "validation": checks,
                "original_failure_retained": True,
            },
        )
    finally:
        runtime.close()
    # Return to initial empty residency, under the same kit lease.
    config = read(screen.SNAPSHOT / ".local-agents/config.json")
    model = screen.MODELS[2]
    config.update(coder_model=model, model_switch_timeout_seconds=900)
    screen.guard_residents(screen.residents(), model)
    client = worker.LMStudioClient(
        config["lmstudio_base_url"], model, 600, context_length=24576
    )
    with worker.MODEL_RESIDENCY.role_model_lease(client, config):
        screen.guard_residents(screen.residents(), model)
        instance = screen.loaded_config(model)
        write(
            directory / "unloaded.json",
            screen.FA.api("/unload", {"instance_id": instance["id"]}),
        )
        if screen.residents():
            raise ValueError("residency not empty after unload")
    print(
        {
            "semantic_pass": checks["semantic_pass"],
            "new_model_calls": 0,
            "skipped": skipped,
        }
    )


if __name__ == "__main__":
    audit()
