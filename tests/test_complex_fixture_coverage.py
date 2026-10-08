"""Primary-only reference and seeded defects; never placed in worker snapshots."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "complex_cases", KIT / "benchmarks/complex_fixture_cases.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

EVIDENCE = """from copy import deepcopy

def copy_evidence(source, run_id):
    return dict(deepcopy(source), run_id=run_id, reused_from=source["run_id"])
"""
PUBLISH = """from product.evidence import copy_evidence

async def publish(store, source, run_id, lease):
    if source["status"] != "succeeded" or not source["cacheable"]:
        raise ValueError("ineligible")
    if not await store.check_lease(lease):
        raise RuntimeError("lease expired")
    evidence = copy_evidence(source, run_id)
    try:
        await store.write(evidence)
        await store.commit()
    except Exception:
        try:
            await store.rollback()
        except Exception:
            pass
        raise
    return evidence
"""
SUMMARY = """from copy import deepcopy

def summary(records, run_id):
    selected = [record for record in records if record["run_id"] == run_id]
    return {"total": len(selected),
            "reused": sum(record["status"] == "succeeded" and record.get("reused_from") is not None for record in selected),
            "records": deepcopy(selected)}
"""


@pytest.mark.parametrize(
    "defect",
    [
        "clean",
        "shallow",
        "no-lease",
        "no-rollback",
        "no-await",
        "eligibility",
        "wrong-filter",
        "failed-reuse",
        "summary-alias",
        "rollback-mask",
    ],
)
def test_complex_protected_tests_detect_seeded_defects(tmp_path, defect):
    case = MODULE.transaction_case()
    files = dict(case["files"])
    files.update(
        {
            "src/product/evidence.py": EVIDENCE,
            "src/product/publish.py": PUBLISH,
            "src/product/summary.py": SUMMARY,
        }
    )
    if defect == "shallow":
        files["src/product/evidence.py"] = EVIDENCE.replace(
            "deepcopy(source)", "source"
        )
    elif defect == "no-lease":
        files["src/product/publish.py"] = PUBLISH.replace(
            "if not await store.check_lease(lease):", "if False:"
        )
    elif defect == "no-rollback":
        files["src/product/publish.py"] = PUBLISH.replace(
            "await store.rollback()", "pass"
        )
    elif defect == "no-await":
        files["src/product/publish.py"] = PUBLISH.replace(
            "await store.commit()", "store.commit()"
        )
    elif defect == "rollback-mask":
        files["src/product/publish.py"] = PUBLISH.replace(
            "        try:\n            await store.rollback()\n        except Exception:\n            pass\n",
            "        await store.rollback()\n",
        )
    elif defect == "eligibility":
        files["src/product/publish.py"] = PUBLISH.replace(
            'source["status"] != "succeeded" or not source["cacheable"]', "False"
        )
    elif defect == "wrong-filter":
        files["src/product/summary.py"] = SUMMARY.replace(
            'record["run_id"] == run_id', "True"
        )
    elif defect == "failed-reuse":
        files["src/product/summary.py"] = SUMMARY.replace(
            'record["status"] == "succeeded" and ', ""
        )
    elif defect == "summary-alias":
        files["src/product/summary.py"] = SUMMARY.replace(
            "deepcopy(selected)", "selected"
        )
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["src"]\n'
    )
    result = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (0 if defect == "clean" else 1), (
        result.stdout + result.stderr
    )
    assert (
        "9 passed" in result.stdout if defect == "clean" else "failed" in result.stdout
    )


def test_atomic_contract_not_split_to_reduce_risk():
    case = MODULE.transaction_case()
    assert case["units"][0]["risk"] == "high"
    assert len(case["units"][0]["paths"]) == 2
    assert case["units"][1]["dependencies"] == ["atomic-publish"]
    assert len(case["units"][0]["required_order"]) == 3
    assert len(case["units"][0]["forbidden_orderings"]) == 2


def test_extension_preserves_frozen_v1():
    import json

    original = json.loads(
        (KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text()
    )
    snapshot = json.dumps(original, sort_keys=True)
    extended = MODULE.extend(original)
    assert json.dumps(original, sort_keys=True) == snapshot
    assert len(extended["cases"]) == 3
    assert '"２"' in extended["cases"][0]["files"]["tests/test_config.py"]


@pytest.mark.parametrize("access", ["tuple", "mapping"])
def test_sql_fixture_accepts_real_result_access_variants(tmp_path, access):
    import json

    corpus = MODULE.extend(
        json.loads((KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text())
    )
    files = dict(corpus["cases"][1]["files"])
    query = files["src/product/query.py"].split("async def summarize")[0]
    query += """async def summarize(session, evaluation_id):
    from sqlalchemy import case, func
    names = ["total", "succeeded", "failed", "skipped", "reused"]
    conditions = [results.c.status == "succeeded", results.c.status == "failed",
                  results.c.status == "skipped",
                  (results.c.status == "succeeded") & results.c.reused_from.is_not(None)]
    columns = [func.count().label("total")] + [
        func.coalesce(func.sum(case((condition, 1), else_=0)), 0).label(name)
        for condition, name in zip(conditions, names[1:])]
    result = await session.execute(select(*columns).where(results.c.evaluation_id == evaluation_id))
"""
    query += (
        "    return dict(zip(names, result.one()))\n"
        if access == "tuple"
        else "    return dict(result.mappings().one())\n"
    )
    files["src/product/query.py"] = query
    files["src/product/service.py"] = """from product.query import summarize

async def score_summary(session, evaluation_id):
    evaluation = await session.get_evaluation(evaluation_id)
    if evaluation is None:
        raise LookupError(evaluation_id)
    counts = await summarize(session, evaluation_id)
    return dict(counts, evaluation_id=evaluation_id, reuse_scores=evaluation.get("reuse_scores", False))
"""
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["src"]\n'
    )
    result = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
