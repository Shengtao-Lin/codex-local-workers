"""Primary-selected pure-function observations, never model-selected execution."""

import argparse
import ast
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import harness_observed_facts as OLD
import reviewer_observed_facts as REAL

B = OLD.B
BATCH = OLD.BATCH.parent / "r4-fixed-observation-recovery-20261017-1"
SEAL = BATCH / "observations-v2.json"
TARGET = "src/product/target.py"
PYTHON = REAL.OBS.PYTHON


def manifest(row):
    return {p: sha for p, sha in row["files"].items() if p.startswith("src/")}


def child(name):
    # Only Primary's registered immutable fixture id is accepted; no data/code API.
    row = next(
        r for r in B.read(BATCH / "registration.json")["cells"] if r["id"] == name
    )
    root = Path(row["root"])
    if not root.resolve().is_relative_to(BATCH.resolve()):
        raise ValueError("fixture escaped registered batch")
    OLD.R.assert_files(root, row["files"])
    path = root / TARGET
    nodes = ast.parse(path.read_text(encoding="utf-8-sig")).body
    names = [n.name for n in nodes if isinstance(n, ast.FunctionDef)]
    if len(names) != 1 or names[0] not in {"display_name", "lookup_or", "increment"}:
        raise ValueError("unsupported pure-function fixture")
    spec = importlib.util.spec_from_file_location("fixed_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    function = getattr(module, names[0])
    examples = []
    if names[0] == "display_name":
        for record in ({"name": "Ada"}, {}, {"name": ""}, {"name": None}):
            before = dict(record)
            value = function(record)
            examples.append(
                {
                    "input": before,
                    "outcome": {"kind": "returned", "value": value},
                    "input_unchanged": record == before,
                }
            )
    elif names[0] == "increment":
        for value in (2, -2, 0):
            examples.append(
                {
                    "input": value,
                    "outcome": {"kind": "returned", "value": function(value)},
                }
            )
    else:
        for behavior, value in [("return", v) for v in (7, None, False, 0, "")] + [
            ("raise", "KeyError"),
            ("raise", "RuntimeError"),
        ]:
            calls = []
            original = (
                KeyError("missing") if value == "KeyError" else RuntimeError("failure")
            )

            def fetch(
                key, calls=calls, behavior=behavior, original=original, value=value
            ):
                calls.append(key)
                if behavior == "raise":
                    raise original
                return value

            try:
                outcome = {
                    "kind": "returned",
                    "value": function(fetch, "key", "fallback"),
                }
            except (KeyError, RuntimeError) as exc:
                outcome = {
                    "kind": "raised",
                    "type": type(exc).__name__,
                    "same_exception_instance": exc is original,
                }
            examples.append(
                {
                    "input": {
                        "fetch_behavior": behavior,
                        "fetch_value_or_exception": value,
                        "key": "key",
                        "default": "fallback",
                    },
                    "fetch_calls": calls,
                    "outcome": outcome,
                }
            )
    OLD.R.assert_files(root, row["files"])
    return {
        "profile_id": "fixed-pure-" + names[0] + "-v1",
        "source": {"path": TARGET, "sha256": B.sha(path)},
        "examples": examples,
    }


def generate():
    entries, pins = [], {}
    for row in B.read(BATCH / "registration.json")["cells"]:
        source_manifest = manifest(row)
        if any(e["source_manifest"] == source_manifest for e in entries):
            continue
        root = Path(row["root"])
        OLD.R.assert_files(root, row["files"])
        if TARGET not in source_manifest:
            # Reuse actual sealed real-type observations without executing again.
            real = B.read(REAL.SEAL)
            for p, sha in real["pins"].items():
                if B.sha(Path(p)) != sha:
                    raise ValueError("real observation drift")
            source = next(
                e for e in real["sources"] if e["source_manifest"] == source_manifest
            )
            request = B.read(Path(source["request"]))
            result = B.read(Path(source["observation"]))
            assert result["execution_completed"] and result["semantic_verdict"] is None
            observation = {
                "profile_id": result["profile_id"],
                "source": result["source"],
                "shared_setup": "One existing tool call a followed by result a; output projected to call_id/name/arguments/result/status.",
                "examples": [
                    {
                        "result_input": case["parts"][1]["result"],
                        "outcome": obs["outcome"],
                        "input_unchanged": obs["input_before"] == obs["input_after"],
                    }
                    for case, obs in zip(
                        request["cases"], result["observations"], strict=True
                    )
                ],
            }
            pins.update(real["pins"])
            pins[str(REAL.SEAL)] = B.sha(REAL.SEAL)
        else:
            argv = [
                str(PYTHON),
                "-B",
                str(Path(__file__).resolve()),
                "child",
                "--case",
                row["id"],
            ]
            proc = subprocess.run(
                argv,
                cwd=root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
                check=False,
            )
            artifact = BATCH / "observations" / (row["id"] + ".json")
            B.save(
                artifact,
                {
                    "argv": argv,
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                },
            )
            if proc.returncode != 0:
                raise ValueError("fixed observation child failed: " + str(artifact))
            observation = json.loads(proc.stdout)
            pins[str(artifact)] = B.sha(artifact)
        OLD.R.assert_files(root, row["files"])
        observation["meaning"] = (
            "Actual outcomes for this exact source in the fixed evaluation environment, not expected results or a contract verdict. Ephemeral observations did not add or modify project tests."
        )
        entries.append({"source_manifest": source_manifest, "observation": observation})
    assert len(entries) == 8
    pins[str(Path(__file__))] = B.sha(Path(__file__))
    pins[str(PYTHON)] = B.sha(PYTHON)
    B.save(
        SEAL,
        {
            "entries": entries,
            "pins": pins,
            "model_calls": 0,
            "scope": "Same-session fixed interpreter/dependencies; trusted pure copied fixtures only, not an OS sandbox or a portable execution proof.",
        },
    )
    print({"source_versions": len(entries), "model_calls": 0})


def facts(runtime, error):
    seal = B.read(SEAL)
    for p, sha in seal["pins"].items():
        if B.sha(Path(p)) != sha:
            raise error("fixed observation artifact drift: " + p)
    runtime._assert_inputs_current()
    for entry in seal["entries"]:
        if any(not (runtime.repo_root / p).is_file() for p in entry["source_manifest"]):
            continue
        current = {
            p: B.sha(runtime._assert_read_allowed(p)[1])
            for p in entry["source_manifest"]
        }
        if current == entry["source_manifest"]:
            runtime._assert_inputs_current()
            return [entry["observation"]], {
                "seal_sha256": B.sha(SEAL),
                "source_manifest": current,
                "scope": seal["scope"],
            }
    raise error("unsupported source version for fixed observations")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["generate", "child"])
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "generate":
        generate()
    else:
        print(json.dumps(child(args.case), ensure_ascii=False, allow_nan=False))
