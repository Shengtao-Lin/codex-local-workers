"""Post-hoc, zero-call analysis of rejected outputs; never changes live scores."""

import json
import re
from pathlib import Path

import contract_presentation_repair as EXP
from capability_fit import load_worker, write
from inherited_context_recovery import digest, read


def extract(raw, writable):
    # Diagnostic only: exactly one tagged fence, no path/quote/code repairs.
    matches = list(
        re.finditer(r"(?m)^```(python|py|json)\s*\n(.*?)^```\s*$", raw, re.S)
    )
    if len(matches) != 1 or raw.count("```") != 2:
        raise ValueError("not exactly one unambiguous tagged code block")
    match = matches[0]
    if (len(writable) == 1 and match[1] not in ("python", "py")) or (
        len(writable) > 1 and match[1] != "json"
    ):
        raise ValueError("code block language does not match required output")
    return EXP.decode(match[2], writable)[0]


def run():
    base = EXP.BASE / "rejected-output-audit-1"
    base.mkdir(exist_ok=False)
    manifest = read(EXP.BASE / "manifest.json")
    selected = []
    for cell in manifest["cells"]:
        for attempt in (0, 1):
            root = Path(cell["root"])
            result = root / f".agent/attempt-{attempt}-result.json"
            if result.exists() and read(result)["semantic_pass"] is None:
                response = root / f".agent/attempt-{attempt}-response.json"
                selected.append(
                    {
                        "cell": cell,
                        "attempt": attempt,
                        "response": str(response),
                        "sha256": digest(response),
                    }
                )
    write(
        base / "manifest.json",
        {
            "selected": selected,
            "selection": "ALL outputs with unevaluated semantics in completed cohort",
            "model_calls": 0,
            "post_hoc": True,
            "live_score_changes": False,
            "rule": "Exactly one tagged fence, no code/path edits, all scope and compile guards retained",
            "driver_sha256": digest(Path(__file__)),
        },
    )
    EXP.FA.MIXED.CORPUS, EXP.FA.MIXED.WORK = EXP.BASE / "corpus.json", base / "runs"
    worker = load_worker(EXP.SNAPSHOT)
    outcomes = []
    for i, item in enumerate(selected):
        cell = item["cell"]
        original = Path(cell["root"])
        packet = read(original / ".agent/qual-unit-reference.json")
        result = {
            "cell": cell["id"],
            "attempt": item["attempt"],
            "semantic_pass": None,
            "error": None,
        }
        runtime = None
        try:
            patch = extract(
                read(Path(item["response"]))["raw"], packet["scope"]["modify"]
            )
            for entry in patch:
                compile(entry["content"], entry["path"], "exec")
            root = Path(
                EXP.FA.MIXED.prepare(
                    cell["case"],
                    1,
                    EXP.SNAPSHOT / ".local-agents/config.json",
                    f"audit-{i}",
                )["root"]
            )
            hashes = {
                p: sha
                for p, sha in cell["hashes"].items()
                if not p.startswith(".agent/")
            }
            EXP.FA.LAYER.verify_hashes(root, hashes)
            runtime = worker.WorkerRuntime(
                root,
                read(root / ".agent/qual-unit-reference.json"),
                read(root / ".agent/config.json"),
                None,
            )
            runtime.write_lock.acquire()
            runtime._prepare_run_archive()
            EXP.apply_complete_files(runtime, root, patch)
            validation = EXP.FA.LAYER.check(root, "audit")
            EXP.FA.LAYER.verify_hashes(
                root,
                {
                    p: sha
                    for p, sha in hashes.items()
                    if p not in packet["scope"]["modify"]
                },
            )
            result.update(
                semantic_pass=validation["semantic_pass"], validation=validation
            )
        except (ValueError, SyntaxError) as error:
            result["error"] = str(error)
        finally:
            if runtime:
                runtime.close()
        write(base / f"audit-{i}.json", result)
        outcomes.append(result)
    write(
        base / "summary.json",
        {
            "selected": len(outcomes),
            "executed": sum(r["semantic_pass"] is not None for r in outcomes),
            "semantic_pass": sum(r["semantic_pass"] is True for r in outcomes),
            "results": outcomes,
            "qualification_credit": False,
        },
    )
    print(
        json.dumps(
            {
                "selected": len(outcomes),
                "executed": sum(r["semantic_pass"] is not None for r in outcomes),
                "semantic_pass": sum(r["semantic_pass"] is True for r in outcomes),
            }
        )
    )


if __name__ == "__main__":
    run()
