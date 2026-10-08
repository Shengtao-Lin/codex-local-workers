"""Primary-authored hidden/clean controls; never Coder performance or acceptance."""

import argparse
import json
import subprocess
import sys
import time

from capability_fit import WORK, load_worker, write


def run(family, variant, repetition, strength=None, focused_contract=False):
    base = WORK / "roleq-six-1"
    corpus = json.loads((base / "corpus.json").read_text(encoding="utf-8"))
    oracles = json.loads(
        (base / "primary-only-oracles.json").read_text(encoding="utf-8")
    )
    original = next(c for c in corpus["cases"] if c["case_id"] == family)
    reference = oracles[family]["reference"]["src/product/target.py"]
    hidden = original["files"]["src/product/target.py"]
    if family == "utf8-capacity":
        tests = "from product.target import fits\n\n\ndef test_ascii():\n    assert fits('ab', 2) is True\n    assert fits('abc', 2) is False\n"
        baseline = "def fits(text, limit):\n    raise RuntimeError('initial')\n"
        expected_defect = "Uses character length rather than UTF-8 byte length; fits('界',2) incorrectly True"
    elif family == "explicit-switch":
        tests = "from product.target import enabled\n\n\ndef test_normal():\n    assert enabled({}) is True\n    assert enabled({'enabled':True}) is True\n    assert enabled({'enabled':False}) is False\n"
        baseline = "def enabled(config):\n    raise RuntimeError('initial')\n"
        expected_defect = "Coerces non-bool present values; enabled({'enabled':0}) must raise ValueError"
    else:
        tests = original["files"]["tests/test_target.py"]
        baseline = "def groups(items, width):\n    raise RuntimeError('initial')\n"
        hidden = "def groups(items, width):\n    if not isinstance(width, int) or width < 1:\n        raise ValueError\n    if width is True:\n        raise ValueError\n    return [items[i:i+width] for i in range(0,len(items),width)]\n"
        expected_defect = "Accepts an int subclass contrary to exact-int contract; groups([], IntegerSubclass(2)) must raise ValueError"
    root = base / "reviewer-controls" / f"{family}-{variant}-r{repetition}"
    if strength is not None:
        root = root.with_name(root.name + "-" + strength)
    if focused_contract:
        root = root.with_name(root.name + "-focused")
    root.mkdir(parents=True, exist_ok=False)
    for path, source in {
        "src/product/__init__.py": "",
        "src/product/target.py": baseline,
        "tests/test_target.py": tests,
    }.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath=["src"]\n[tool.ruff.lint]\nselect=["E4","E7","E9","F"]\n',
        encoding="utf-8",
    )
    source_root = base / "runs/v1/roleq1" / f"{family}-round-1"
    config = json.loads(
        (source_root / ".agent/config.json").read_text(encoding="utf-8")
    )
    if strength is not None:
        config["reviewer_reasoning_strength"] = strength
    packet = json.loads(
        (source_root / ".agent/qual-unit-reference.json").read_text(encoding="utf-8")
    )
    identity = f"rolecontrol-{family}-{variant}-r{repetition}"
    if strength is not None:
        identity += "-" + strength
    if focused_contract:
        identity += "-focused"
        packet["review_feedback"] = [
            {
                "finding_id": "primary-exact-type-obligation",
                "contract_id": "qual-unit",
                "text": "Verify the exact integer requirement independently of passing tests. Exact runtime type excludes bool and custom int subclasses; inheritance membership is not exact type. Explain whether the changed source enforces this invariant and report any contract mismatch.",
                "source_anchor": "width",
                "verify_in_review": True,
            }
        ]
    packet.update(task_id=identity, feature_id=identity, run_id=identity + "-synthetic")
    write(root / ".agent/config.json", config)
    write(root / ".agent/packet.json", packet)
    final = reference if variant == "clean" else hidden
    temporary = root / "formatted-source.py"
    temporary.write_text(final, encoding="utf-8")
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", str(temporary), str(root / "tests")],
        check=True,
        capture_output=True,
    )
    final = temporary.read_text(encoding="utf-8")
    snapshot = WORK / "roleq-six-runtime-1"
    worker = load_worker(snapshot)
    runtime = worker.WorkerRuntime(root, packet, config, None)
    runtime.write_lock.acquire()
    try:
        runtime._prepare_run_archive()
        observed = runtime.read_file({"path": "src/product/target.py"})
        runtime.safe_replace(
            {
                "path": "src/product/target.py",
                "expected_sha256": observed["sha256"],
                "find": baseline,
                "replace": final,
            }
        )
        validation = runtime.validate(
            {"phase": "final", "contract_check": runtime.contract_check_template()}
        )
        assert validation["status"] == "passed"
        _, report = runtime.execute(
            {
                "action": "FINISH_SUCCESS",
                "arguments": {
                    "summary": [
                        "Primary-authored synthetic control, no Coder model invoked"
                    ]
                },
            }
        )
        report["synthetic_benchmark_archive"] = True
        runtime._complete_run(report)
    finally:
        runtime.close()
    request = {
        "schema_version": 1,
        "task_id": identity,
        "unit_id": "qual-unit",
        "run_id": identity + "-synthetic",
        "review_id": "control-1",
    }
    write(root / ".agent/request.json", request)
    started = time.monotonic()
    result = subprocess.run(
        [
            sys.executable,
            str(snapshot / ".local-agents/local-review.py"),
            "--request",
            str(root / ".agent/request.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/reviewer.json"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    reviewer = json.loads((root / ".agent/reviewer.json").read_text(encoding="utf-8"))
    summary = {
        "family": family,
        "variant": variant,
        "repetition": repetition,
        "synthetic_archive": True,
        "coder_calls": 0,
        "reviewer_exit": result.returncode,
        "decision": reviewer.get("decision"),
        "findings": reviewer.get("findings"),
        "effective_detection": None,
        "expected_defect_primary_only": expected_defect
        if variant == "hidden"
        else None,
        "seconds": round(time.monotonic() - started, 2),
        "primary_adjudication_required": True,
    }
    write(root / "control-result.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--family",
        choices=("utf8-capacity", "explicit-switch", "window-groups"),
        required=True,
    )
    parser.add_argument("--variant", choices=("hidden", "clean"), required=True)
    parser.add_argument("--repetition", type=int, choices=(1, 2), required=True)
    parser.add_argument("--strength", choices=("low", "high"))
    parser.add_argument("--focused-contract", action="store_true")
    args = parser.parse_args()
    if args.focused_contract and args.family != "window-groups":
        parser.error(
            "focused development obligation is registered for window-groups only"
        )
    run(
        args.family, args.variant, args.repetition, args.strength, args.focused_contract
    )
