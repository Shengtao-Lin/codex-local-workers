"""Fixed repeats/transfer using the unchanged installed snapshot-chain engine."""

import argparse
import copy
import shutil
import time
from pathlib import Path

import bounded_dependency_close as CLOSE
import bounded_dependency_smoke as D
import bounded_evidence_support as S

ROOT = D.I.BASE / "bounded-chain-matrix-20261021-1"
OLD = D.BATCH
ROUTE = copy.deepcopy(D.SPECS)
ORDER = ["route-r1", "tags-r1", "tags-r2", "route-r2"]
TAGS = {
    "encode": {
        "path": "src/product/dependencies.py",
        "symbol": "stable_unique",
        "module": "product.dependencies",
        "header": "from __future__ import annotations\n",
        "contract": "stable_unique(values: list[str]) -> list[str] returns a new list containing the first occurrence of each distinct string, in input order. Comparison is exact and case-sensitive. Preserve empty strings, whitespace, Unicode and the original string values without normalization or sorting. Never mutate the input list. Empty input returns an empty new list. Other input types are outside this string-list contract.",
        "start": "from __future__ import annotations\n\ndef stable_unique(values: list[str]) -> list[str]:\n    return sorted(set(values))\n",
        "reference": "from __future__ import annotations\n\ndef stable_unique(values: list[str]) -> list[str]:\n    result: list[str] = []\n    seen: set[str] = set()\n    for value in values:\n        if value not in seen:\n            seen.add(value)\n            result.append(value)\n    return result\n",
        "cases": [
            {"args": [["b", "a", "b", "", "雪"]], "kwargs": {}},
            {"args": [[]], "kwargs": {}},
        ],
    },
    "append": {
        "path": "src/product/code.py",
        "symbol": "render_tags",
        "module": "product.code",
        "header": "import json\nfrom product.dependencies import stable_unique\n",
        "contract": "render_tags(values: list[str]) -> str renders the stable_unique result as a compact JSON array string, preserving the accepted dependency's first-occurrence order and exact strings. Non-ASCII characters remain literal (not ASCII escaped); use no JSON separator whitespace or trailing newline. Correctly escape quotes, backslashes and control characters as JSON requires. Preserve whitespace inside string values. Do not mutate values or change/reimplement the read-only stable_unique dependency. Empty input renders exactly []. Other input types are outside this string-list contract.",
        "start": "import json\nfrom product.dependencies import stable_unique\n\ndef render_tags(values: list[str]) -> str:\n    return json.dumps(stable_unique(values))\n",
        "reference": "import json\nfrom product.dependencies import stable_unique\n\ndef render_tags(values: list[str]) -> str:\n    return json.dumps(stable_unique(values), ensure_ascii=False, separators=(',', ':'))\n",
        "cases": [
            {"args": [["b", "a", "b", "雪", ""]], "kwargs": {}},
            {"args": [[]], "kwargs": {}},
        ],
    },
}
PUBLIC_TAGS = {
    "encode": """from product.dependencies import stable_unique

def test_first_order_and_no_mutation():
    values = ["b", "a", "b", "", "雪", "a"]
    before = values.copy()
    result = stable_unique(values)
    assert result == ["b", "a", "", "雪"]
    assert values == before and result is not values

def test_empty_is_new():
    values = []
    result = stable_unique(values)
    assert result == [] and result is not values
""",
    "append": """from product.code import render_tags

def test_compact_unicode_order():
    values = ["b", "a", "b", "雪", ""]
    assert render_tags(values) == '["b","a","雪",""]'
    assert values == ["b", "a", "b", "雪", ""]

def test_empty():
    assert render_tags([]) == "[]"
""",
}
PRIVATE_TAGS = {
    "encode": """from product.dependencies import stable_unique

def test_exact_values_and_order():
    values = ["a", "A", " ", "a", "", "A", "雪", "雪"]
    assert stable_unique(values) == ["a", "A", " ", "", "雪"]
    assert values == ["a", "A", " ", "a", "", "A", "雪", "雪"]
""",
    "append": r"""import json
from product.code import render_tags

def test_escaping_and_exact_roundtrip():
    values = ['z', 'a"b', 'x\\y', '\n', ' ', '', '雪', 'z']
    expected = ['z', 'a"b', 'x\\y', '\n', ' ', '', '雪']
    before = values.copy()
    result = render_tags(values)
    assert json.loads(result) == expected
    assert result == json.dumps(expected, ensure_ascii=False, separators=(',', ':'))
    assert values == before
""",
}


def configure(cell):
    assert cell in ORDER
    D.BATCH = ROOT / "chains" / cell
    D.SPECS = copy.deepcopy(TAGS if cell.startswith("tags") else ROUTE)
    return D.BATCH


def real_files(root):
    return [
        p
        for p in root.rglob("*")
        if p.is_file()
        and not any(
            v in p.parts for v in ("__pycache__", ".pytest_cache", ".ruff_cache")
        )
    ]


def prepare(used):
    assert 0 <= used < 50
    gate = S.read(D.I.BASE / "coordinator-bounded-bridge-20261021-1/gate.json")
    assert all(S.sha(S.KIT / p) == h for p, h in gate["pins"].items())
    assert (
        S.read(OLD / "decision.json")["status"]
        == "PASS_ONE_SUPERVISED_SNAPSHOT_DEPENDENCY_SMOKE"
    )
    template_input = S.read(OLD / "input.json")
    for cell in ORDER:
        batch = configure(cell)
        public = (
            PUBLIC_TAGS
            if cell.startswith("tags")
            else {"encode": D.ENCODER_TEST, "append": D.L.TASKS["route"]["public"]}
        )
        private = (
            PRIVATE_TAGS
            if cell.startswith("tags")
            else {"encode": D.PRIVATE, "append": D.L.TASKS["route"]["private"]}
        )
        root = batch / "template"
        D.L.write(root / "src/product/__init__.py", "")
        for topic, spec in D.SPECS.items():
            D.L.write(root / spec["path"], spec["start"])
            D.L.write(root / f"tests/test_{topic}.py", public[topic])
            D.L.write(batch / f"private/test_private_{topic}.py", private[topic])
        shutil.copyfile(D.L.SEED / "pyproject.toml", root / "pyproject.toml")
        format_tree(root)
        proof = batch / "reference"
        shutil.copytree(root, proof)
        for spec in D.SPECS.values():
            (proof / spec["path"]).write_text(spec["reference"], encoding="utf-8")
        format_tree(proof)
        checks = D.L.checks(proof, batch / "private")
        baseline = D.T.run([S.PYTHON, "-B", "-m", "pytest", "-q", "tests"], root)
        S.save(
            batch / "reference-controls.json",
            {"reference": checks, "baseline": baseline},
        )
        assert baseline["exit_code"] == 1 and all(c["exit_code"] == 0 for c in checks)
        for topic, spec in D.SPECS.items():
            mutant = batch / "mutants" / topic
            shutil.copytree(proof, mutant)
            (mutant / spec["path"]).write_text(spec["start"], encoding="utf-8")
            negative = D.T.run(
                [S.PYTHON, "-B", "-m", "pytest", "-q", "tests", batch / "private"],
                mutant,
            )
            S.save(batch / "negative-controls" / (topic + ".json"), negative)
            assert negative["exit_code"] == 1
        data = copy.deepcopy(template_input)
        brief = data["brief"]
        brief.update(
            feature_id="matrix-" + cell,
            task_id="matrix-" + cell,
            goal="Implement the approved "
            + (
                "stable tag-list JSON rendering"
                if cell.startswith("tags")
                else "URL segment compatibility"
            )
            + " feature in cohesive one-function local units. Preserve the actual producer-consumer dependency and all contracts; propose decomposition, not new algorithms or acceptance rules.",
        )
        brief["risk_rationale"] = (
            "Primary: public ordered-list/serialization compatibility imposes high risk; scoped copies do not lower contract floors"
        )
        files = {p.relative_to(root).as_posix(): S.sha(p) for p in real_files(root)}
        brief["source_hashes"] = files
        brief["contracts"] = [
            {
                "id": k,
                "text": s["contract"],
                "risk_floor": "high",
                "implementation_ref": {"path": s["path"], "symbol": s["symbol"]},
            }
            for k, s in D.SPECS.items()
        ]
        for k, s in D.SPECS.items():
            brief["acceptance_catalog"][k]["acceptance_criteria"] = [
                {"id": k, "text": s["contract"]}
            ]
            brief["acceptance_catalog"][k]["acceptance_scenarios"][0].update(
                text="Normal and specified error/boundary behavior, no invented input requirements",
                observables={"contract": s["contract"]},
            )
        data["context"]["files"] = {p: (root / p).read_text("utf-8") for p in files}
        D.P.C.validate_brief(brief)
        S.save(batch / "input.json", data)
        S.save(
            batch / "catalog.json",
            {
                k: {
                    "family": D.BRIDGE.FAMILY,
                    "path": s["path"],
                    "symbol": s["symbol"],
                    "qualification_evidence": "Previously qualified bounded single-function transformation family; this task composition is registered testing, not production promotion",
                }
                for k, s in D.SPECS.items()
            },
        )
        control = {
            "status": "proposed",
            "questions": [],
            "rationale": "Offline only, excluded from Worker input",
            "units": [
                {
                    "id": k,
                    "goal": s["contract"],
                    "owner": "local-coder",
                    "risk": "high",
                    "contracts": [k],
                    "dependencies": ["encode"] if k == "append" else [],
                    "modify": [s["path"]],
                    "create": [],
                }
                for k, s in D.SPECS.items()
            ],
        }
        offline_plan = D.P.C.proposal_plan(brief, control)
        for topic, spec in D.SPECS.items():
            binding = D.materialize(topic, offline_plan=offline_plan)
            control_root = Path(binding["root"])
            replay = control_root.parent / "reference-only.json"
            S.save(
                replay,
                [{"replacement": D.T.extract(proof / spec["path"], spec["symbol"])}],
            )
            result = D.T.run(
                D.I.command(control_root, replay=replay), control_root, timeout=180
            )
            S.save(control_root.parent / "full-chain.json", result)
            assert result["exit_code"] == 0, result["stderr"][-1000:]
            assert (
                S.read(control_root / ".agent/unit-summary.json")["reviewer_started"]
                is False
            )
        paths = [
            Path(__file__),
            Path(D.__file__),
            Path(CLOSE.__file__),
            Path(S.__file__),
            Path(D.T.__file__),
            Path(D.F.__file__),
            Path(D.P.__file__),
            Path(D.I.__file__),
            Path(D.L.__file__),
            Path(D.INSTALL.__file__),
            D.L.SEED / ".agent/config.json",
            D.L.SEED / "pyproject.toml",
            batch / "input.json",
            batch / "catalog.json",
            *real_files(root),
            *list((batch / "private").glob("*.py")),
            *list((S.KIT / ".local-agents").rglob("*.py")),
        ]
        reg = S.read(OLD / "registration.json")
        reg.update(
            pins={str(p): S.sha(p) for p in paths if "__pycache__" not in p.parts},
            weekly_used_start=used,
            exposure="Exposed URL chain repeat"
            if cell.startswith("route")
            else "New local synthetic string-list dedup/serialization chain, no untrusted repository discovery; frozen before any live Worker exposure",
            Primary_cost="Primary authored complete contracts, source locations, public/private checks/reference controls and classification; model selects units/dependencies; per-unit/full review still required; runtime semantic hints or rescue disqualify autonomous credit",
            scope="Unchanged explicit bounded-v1 and bridge in two immutable snapshots; no default enablement or same-worktree scheduling",
        )
        S.save(batch / "registration.json", reg)
    pins = {
        str(ROOT / "chains" / c / "registration.json"): S.sha(
            ROOT / "chains" / c / "registration.json"
        )
        for c in ORDER
    }
    S.save(
        ROOT / "registration.json",
        {
            "order": ORDER,
            "pins": pins,
            "registered_chains": 4,
            "registered_units": 8,
            "gate": "4/4 complete independent accepts; each family2/2; no final false acceptance, safety drift, runtime semantic hint or takeover",
            "continue_rule": "Ordinary quality failure HOLD but finish other fixed diagnostic chains; downstream of unaccepted producer NOT_RUN. Infrastructure/safety/drift/time/weekly50 stop all. No replacements or same-code Reviewer resampling",
            "weekly_used_start": used,
            "weekly_stop": 50,
            "matrix_seconds": 14400,
            "candidate": "Unchanged installed bounded-v1, bridge and Qwen/Muse; single residency, original request/edit/check/output budgets",
            "primary_work": "Contracts/tests/location/classification preparation, decomposition approval, two unit reviews and final cumulative review per chain; active time/cloud tokens unknown, no savings claim",
        },
    )
    print(
        "Four fixed chains/eight units frozen after references, mutants and eight offline handoffs"
    )


def format_tree(root):
    for args in (("check", "--select", "I", "--fix"), ("format",)):
        assert (
            D.T.run([S.PYTHON, "-B", "-m", "ruff", *args, "src", "tests"], root)[
                "exit_code"
            ]
            == 0
        )


def frozen(cell, used=None, observed=None):
    reg = S.read(ROOT / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    if used is not None:
        assert 0 <= used < 50 and observed and 0 <= time.time() - observed <= 120
        clock = ROOT / "start.json"
        if not clock.exists():
            S.save(clock, {"epoch": time.time(), "weekly_used": used})
        assert time.time() - S.read(clock)["epoch"] < 14400
    for previous in ORDER[: ORDER.index(cell)]:
        result = S.read(ROOT / "chains" / previous / "decision.json")
        assert not result.get("stop_matrix", False)
    batch = configure(cell)
    chain = S.read(batch / "registration.json")
    assert all(S.sha(p) == h for p, h in chain["pins"].items())
    D.P.C.assert_sources_current(
        S.read(batch / "input.json")["brief"], batch / "template"
    )


def hold(cell, reason, stop=False):
    batch = configure(cell)
    rows = {}
    for topic in D.SPECS:
        result = batch / "units" / topic / "result.json"
        rows[topic] = S.read(result) if result.exists() else {"status": "NOT_RUN"}
    S.save(
        batch / "decision.json",
        {
            "status": "HOLD_FIXED_CHAIN",
            "reason": reason,
            "stop_matrix": stop,
            "rows": rows,
            "history": "No retry, score replacement or downstream dispatch after unaccepted prerequisite",
        },
    )


def collect(used):
    reg = S.read(ROOT / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    rows = []
    for cell in ORDER:
        batch = configure(cell)
        if not (batch / "decision.json").exists():
            rows.append({"cell": cell, "status": "NOT_RUN", "accepted": False})
            continue
        decision = S.read(batch / "decision.json")
        accepted = decision["status"] == "PASS_ONE_SUPERVISED_SNAPSHOT_DEPENDENCY_SMOKE"
        metrics = (
            S.read(batch / "metrics.json") if (batch / "metrics.json").exists() else {}
        )
        rows.append(
            {
                "cell": cell,
                "status": decision["status"],
                "accepted": accepted,
                "metrics": metrics,
            }
        )
    count = sum(r["accepted"] for r in rows)
    S.save(
        ROOT / "metrics.json",
        {
            "registered_chains": 4,
            "registered_units": 8,
            "accepted_chains": count,
            "rows": rows,
            "weekly_used": used,
            "weekly_stop": 50,
            "Primary_active_seconds": "unknown",
            "cloud_tokens": "unknown",
            "savings": "Not established; Primary provided substantial preparation and four review/approval decisions per complete chain",
        },
    )
    S.save(
        ROOT / "decision.json",
        {
            "status": "PASS_FIXED_SUPERVISED_SNAPSHOT_MATRIX"
            if count == 4
            else "HOLD_FIXED_SUPERVISED_SNAPSHOT_MATRIX",
            "accepted_chains": count,
            "registered_chains": 4,
            "gate": reg["gate"],
            "defaults": "Unchanged",
            "scope": "Only these two prelocated, approved task families and immutable snapshot routing; not generic same-worktree Coordinator enablement, unknown-boundary Reviewer or economic proof",
            "stop_reason": "Registered matrix complete or explicit stopping condition; no unregistered repeats",
        },
    )
    print(count, "/4 chains independently accepted")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "mode",
        choices=(
            "prepare",
            "plan",
            "approve",
            "execute",
            "accept",
            "close",
            "hold",
            "collect",
        ),
    )
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--topic", choices=("encode", "append"))
    p.add_argument("--weekly-used", type=int)
    p.add_argument("--observed-at", type=float)
    p.add_argument("--reason")
    p.add_argument("--stop-matrix", action="store_true")
    args = p.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    elif args.mode == "collect":
        collect(args.weekly_used)
    elif args.mode == "hold":
        hold(args.cell, args.reason, args.stop_matrix)
    else:
        live = args.mode in {"plan", "execute"}
        frozen(args.cell, args.weekly_used if live else None, args.observed_at)
        if args.mode == "plan":
            D.plan(args.weekly_used, args.observed_at)
        elif args.mode == "approve":
            D.approve(args.reason)
        elif args.mode == "execute":
            D.execute(args.topic, args.weekly_used, args.observed_at)
        elif args.mode == "accept":
            D.accept(args.topic, args.reason)
        else:
            CLOSE.close(args.weekly_used, args.reason)
