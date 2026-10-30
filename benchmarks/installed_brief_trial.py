"""Small conditional Coordinator decomposition probe; never dispatches workers."""

import argparse
import copy
import os
import subprocess
import time
from pathlib import Path

import bounded_evidence_support as S
import capture_fixture_support as F
import installed_real_trial as R

BATCH = R.I.BASE / "installed-brief-20261021-2"
ORDER = ["single-1", "pair-1", "pair-2", "single-2"]
ENTRY = S.KIT / ".local-agents"
C = F.load(ENTRY / "coordinator-brief.py", "installed_brief_probe")
W = F.load(ENTRY / "worker-runtime.py", "installed_brief_worker")
PATHS = {"binding": "src/product/binding.py", "hash": "src/product/hashing.py"}


def eligibility(brief, plan):
    """Extra qualified-family boundary, not a replacement for Primary approval."""
    expected = {c["id"] for c in brief["contracts"]}
    if not plan or len(plan["units"]) != len(expected):
        return False
    return all(
        u["owner"] == "local-coder"
        and len(u["owned_contract_ids"]) == 1
        and u["owned_contract_ids"][0] in expected
        and u["scope_authority"]["modify"] == [PATHS[u["owned_contract_ids"][0]]]
        and not u["scope_authority"]["create"]
        for u in plan["units"]
    )


def prepare(used):
    assert 0 <= used < 50 and S.read(R.BATCH / "decision.json")["accepted"] == 4
    rows = {}
    for kind, topics in (("single", ["binding"]), ("pair", ["binding", "hash"])):
        root = BATCH / "fixtures" / kind
        texts, catalog = {"src/product/__init__.py": ""}, {}
        for topic in topics:
            template = R.BATCH / "templates" / topic
            texts[PATHS[topic]] = (template / "src/product/code.py").read_text("utf-8")
            module = "binding" if topic == "binding" else "hashing"
            test = f"tests/test_{topic}.py"
            texts[test] = (
                (template / "tests/test_contract.py")
                .read_text("utf-8")
                .replace("from product.code import", f"from product.{module} import")
            )
            dependency = template / "src/product/dependencies.py"
            if dependency.exists():
                texts["src/product/dependencies.py"] = dependency.read_text("utf-8")
            catalog[topic] = {
                "acceptance_criteria": [
                    {"id": topic, "text": R.TASKS[topic]["contract"]}
                ],
                "acceptance_scenarios": [
                    {
                        "id": topic + "-compatibility",
                        "text": "Normal, error and boundary behavior as specified; original protected tests retained",
                        "observables": {"contract": R.TASKS[topic]["contract"]},
                    }
                ],
                "required_order": [],
                "forbidden_orderings": [],
                "required_focused_tests": [test],
            }
        for path, text in texts.items():
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
        writable = [PATHS[t] for t in topics]
        brief = {
            "schema_version": 1,
            "revision": 1,
            "feature_id": "installed-brief-" + kind,
            "task_id": "installed-brief-" + kind,
            "goal": "Implement the approved compatibility improvements. Identify cohesive executable units from the contracts and supplied current source; do not invent a dependency between independent behaviors.",
            "risk_rationale": "Primary classifies public serialization and request identity compatibility high; copying does not lower the risk floor.",
            "feature_risk": "high",
            "integration_risk": "high",
            "authority": {
                "read_roots": ["src", "tests"],
                "modify": writable,
                "create": [],
                "readonly": [p for p in texts if p not in writable],
                "forbidden": [".agent", ".git", ".local-agents", "AGENTS.md"],
            },
            "max_units": len(topics),
            "contracts": [
                {"id": t, "text": R.TASKS[t]["contract"], "risk_floor": "high"}
                for t in topics
            ],
            "atomic_contract_groups": [],
            "contract_edges": [],
            "source_hashes": {p: S.sha(root / p) for p in texts},
            "integration_tests": [f"tests/test_{t}.py" for t in topics],
            "validation_profile": "real-trace-strict",
            "acceptance_catalog": catalog,
        }
        context = {
            "files": texts,
            "qualified_local_capability": "Existing single-function local transformations only, one writable function file per unit. No new imports, files, architecture, shell, classification or permission decisions. Primary owns classification and final acceptance.",
            "exposure": "Reused already exposed frozen real slices; tests are protected. This probes decomposition, not novel discovery or upstream integration.",
        }
        # No proposal or prebuilt unit list is placed in the model's input.
        C.validate_brief(brief)
        reference = {
            "status": "proposed",
            "questions": [],
            "rationale": "Offline structural control only",
            "units": [
                {
                    "id": t,
                    "goal": R.TASKS[t]["contract"],
                    "owner": "local-coder",
                    "risk": "high",
                    "contracts": [t],
                    "dependencies": [],
                    "modify": [PATHS[t]],
                    "create": [],
                }
                for t in topics
            ],
        }
        assert eligibility(brief, C.proposal_plan(brief, reference))
        for mutation in ("floor", "scope", "duplicate"):
            bad = copy.deepcopy(reference)
            if mutation == "floor":
                bad["units"][0]["risk"] = "small"
            elif mutation == "scope":
                bad["units"][0]["modify"] = ["tests/test_binding.py"]
            else:
                bad["units"].append(copy.deepcopy(bad["units"][0]))
            try:
                C.proposal_plan(brief, bad)
            except ValueError:
                pass
            else:
                raise AssertionError("negative control accepted " + mutation)
        S.save(
            BATCH / "inputs" / (kind + ".json"),
            {"root": str(root), "brief": brief, "context": context},
        )
        rows[kind] = {"reference_valid": True, "risk_scope_duplicate_negatives": 3}
    S.save(BATCH / "offline-controls.json", rows)
    config = S.read(R.BATCH / "cells/binding-1/isolated/.agent/config.json")
    S.save(BATCH / "config.json", config)
    controls = subprocess.run(
        [
            str(S.PYTHON),
            "-B",
            "-m",
            "pytest",
            "-q",
            ".local-agents/tests/test_coordinator_brief.py",
            ".local-agents/tests/test_coordinator_contract.py",
            "--basetemp=" + str(BATCH / "control-temp"),
            "--junitxml=" + str(BATCH / "controls.xml"),
        ],
        cwd=S.KIT,
        capture_output=True,
        text=True,
        check=False,
    )
    S.save(
        BATCH / "controls-process.json",
        {
            "exit_code": controls.returncode,
            "stdout": controls.stdout,
            "stderr": controls.stderr,
        },
    )
    assert controls.returncode == 0
    pins = [
        Path(__file__),
        BATCH / "config.json",
        *list((BATCH / "inputs").glob("*.json")),
        *list(ENTRY.glob("*.py")),
    ]
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 4,
            "weekly_used_start": used,
            "weekly_stop": 50,
            "pins": {str(p): S.sha(p) for p in pins},
            "gate": "4/4 semantically approved qualified task decompositions; sources/protected contracts unchanged; no Worker dispatch",
            "models": {
                "coordinator": "meta/muse-glimmer",
                "context": 24576,
                "parallel": 1,
                "reasoning_effort": "low",
                "temperature": 0.1,
                "max_tokens": 4096,
            },
            "budget": {
                "requests_per_cell": 2,
                "request_seconds": 360,
                "load_seconds": 360,
                "batch_seconds": 7200,
            },
            "continue_rule": "Ordinary proposal/eligibility failure HOLD and continue fixed order; transport/residency/safety/drift/weekly50/time stops; no resampling",
            "Primary_work": "Primary supplied risks, complete contracts, located source, public tests and trusted acceptance catalog. Coordinator only chooses units, ownership, contracts, scope and dependencies; does not originate feature design or tests.",
            "not_proven": "No Worker execution, dependency-chain integration, open repository discovery, production enablement or cost savings",
        },
    )
    print("Four conditional brief probes frozen; controls passed; zero live so far")


def run(cell, used, observed):
    reg = S.read(BATCH / "registration.json")
    assert (
        0 <= used < 50 and observed is not None and 0 <= time.time() - observed <= 120
    )
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    for previous in ORDER[: ORDER.index(cell)]:
        assert not S.read(BATCH / "live-results" / previous / "result.json")[
            "stop_batch"
        ]
    first = BATCH / "live-results" / ORDER[0] / "start.json"
    assert not first.exists() or time.time() - S.read(first)["epoch"] < 7200
    inputs = S.read(BATCH / "inputs" / (cell.split("-")[0] + ".json"))
    root, brief = Path(inputs["root"]), inputs["brief"]
    C.assert_sources_current(brief, root)
    dest = BATCH / "live-results" / cell
    S.save(
        dest / "start.json",
        {"epoch": time.time(), "weekly_used": used, "usage_observed_at": observed},
    )

    class Trace(W.LMStudioClient):
        count = 0

        def complete(self, messages):
            self.count += 1
            S.save(
                dest / f"request-{self.count}.json",
                {
                    "messages": messages,
                    "model": self.model,
                    "reasoning_effort": self.reasoning_effort,
                },
            )
            raw = super().complete(messages)
            S.save(
                dest / f"response-{self.count}.json",
                {"raw": raw, "stats": self.last_request_stats},
            )
            return raw

    config = S.read(BATCH / "config.json")
    client = Trace(
        config["lmstudio_base_url"],
        config["coordinator_model"],
        timeout=360,
        max_tokens=4096,
        temperature=0.1,
        structured_output=False,
        context_length=24576,
    )
    client.reasoning_effort = "low"
    started = time.monotonic()
    try:
        with W.MODEL_RESIDENCY.role_model_lease(client, config):
            loaded = time.monotonic()
            client.preflight()
            result = C.probe(brief, inputs["context"], client, reasoning_strength="low")
        C.assert_sources_current(brief, root)
        result.update(
            stop_batch=False,
            family_eligible=eligibility(brief, result.get("untrusted_plan")),
            load_seconds=loaded - started,
        )
    except (W.WorkerError, W.MODEL_RESIDENCY.ModelResidencyError, OSError, ValueError) as exc:
        result = {
            "status": "infrastructure_or_input_failure",
            "error": str(exc),
            "reason_code": getattr(exc, "reason_code", type(exc).__name__),
            "stop_batch": True,
        }
    result.update(
        seconds=time.monotonic() - started,
        model_requests=client.count,
        Primary_decision="PENDING",
        dispatch_allowed=False,
    )
    S.save(dest / "result.json", result)
    print(cell, result["status"], "Primary semantic review required; no dispatch")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--weekly-used", type=int, required=True)
    p.add_argument("--observed-at", type=float)
    args = p.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        run(args.cell, args.weekly_used, args.observed_at)
