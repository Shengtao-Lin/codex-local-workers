"""Fresh installed v4 candidate, fixed known-contract matrix, create-only records."""

import argparse
import os

import bounded_evidence_support as S
import project_caller_trial as J
from strata_native_trial import command

BATCH = S.KIT / "benchmarks/work/harness-convergence/strata-release-v4-20261023-2"
CASES = ["control", "raw-1", "tools-1", "hash-1", "raw-2", "tools-2", "hash-2"]


def origin(topic):
    return BATCH.parent / (
        "strata-subagent-20261023-1" if topic == "hash" else "strata-complex-20261023-2"
    )


def prepare(used):
    assert used < 50 and not BATCH.exists()
    S.save(
        BATCH / "registration.json",
        {
            "batch_id": BATCH.name,
            "candidate": "installed preview-candidate.4 + pytest-source-v1",
            "feature_id": "portable-native-subagent",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Public parser/event/hash compatibility; current independent full source review mandatory",
            "owned_contract_ids": [
                "same-contract",
                "finite-recovery",
                "local-only",
                "complete-current-checks",
                "no-autoaccept",
            ],
            "dependencies": [
                "strata-native-v3-20261023-1 HOLD5/6",
                "strata-generic-evidence-20261023-1 offline-only",
            ],
            "order": CASES,
            "live_registered": 6,
            "offline_controls": 1,
            "changes": "Default-off generic source policy replaces specialized typed producer; same public/private tests. Portable fresh install, explicit tool limits, six evidence actions and eighteen shared model+host credits (host<=12,model<=8). Not a causal single-variable A/B.",
            "budget": "3edits,1initial+3postchecks,900s; model<=8,host<=12,combined<=18,evidence<=6,120lines/read,10matches/search;12288output/request=>98304 conservative total,thinking4096,64Kdeclared; no reset/pluginretry",
            "model": "Same iq3_s native instance,128Kcontext,parallel1,temp1/top_p.95/top_k20; no reload/switch",
            "roles": "native implementation Agent -> full trusted host checks -> Primary independent acceptance; no fresh Local Reviewer/Explorer/Coordinator",
            "qualification": "Three exposed known-contract families,not holdout,all6current independent accepts required; no generic/multifile/semanticrepair inference from first-pass success",
            "continue": "ordinary failure=>HOLD but finish remaining fixed cells; unsafe/infra/residency/protected drift/weekly50/user stop=>no new dispatch; no reroll/assisted semantics",
            "weekly_used_start": used,
            "weekly_stop": 50,
            "primary": "Detailed frozen contracts/tests reused; new adapter/install work one-time, final full diff/check work repeats; cloud savings and active time unknown",
        },
    )
    for case in CASES:
        topic = "raw" if case == "control" else case.split("-")[0]
        prior = origin(topic)
        seed = (
            prior
            / "cells"
            / ("hash-1" if topic == "hash" else topic + "-1")
            / "isolated"
        )
        root = BATCH / "cells" / case / "isolated"
        J.copy_project(prior / "templates" / topic, root)
        install = command(
            [
                S.PYTHON,
                "-B",
                S.KIT / "tools/install-strata-preview.py",
                "--target",
                root,
            ],
            S.KIT,
        )
        S.save(root.parent / "install.json", install)
        assert install["exit_code"] == 0, install
        packet = S.read(seed / ".agent/packet.json")
        packet.update(
            {k: BATCH.name + "-" + case for k in ("task_id", "unit_id", "run_id")}
        )
        config = S.read(seed / ".agent/config.json")
        config.update(
            bounded_evidence_profile="pytest-source-v1",
            experimental_strata_subagent=True,
            strata_node_path="F:/Strata/node/node.exe",
            strata_harness_root="F:/Strata/harness",
            strata_base_url="http://127.0.0.1:47831/v1",
        )
        config.pop("experimental_capture_policy_sha256", None)
        profile = config["validation_profiles"][packet["validation_profile"]]
        profile["commands"] = [
            c for c in profile["commands"] if c["id"] != "actual-observations"
        ]
        spec = S.read(seed / ".agent/capture-spec.json")
        spec.update(family="pytest-source-v1", cases=[])
        for name, value in (("packet", packet), ("config", config), ("spec", spec)):
            S.save(root / f".agent/{name}.json", value)
        prepared = command(
            [
                S.PYTHON,
                "-B",
                root / ".local-agents/local-bounded-prepare.py",
                "--packet",
                ".agent/packet.json",
                "--config",
                ".agent/config.json",
                "--capture-spec",
                ".agent/spec.json",
                "--apply",
            ],
            root,
        )
        S.save(root.parent / "prepare.json", prepared)
        assert prepared["exit_code"] == 0, prepared
        if case == "control":
            target = packet["scope"]["modify"][0]
            good = J.function_source(prior / "references/raw" / target, "mapping_raw")
            bad = good.replace('decode("utf-8"', 'decode("latin-1"')
            assert bad != good
            S.save(
                root.parent / "frontend.json",
                {
                    "mode": "control",
                    "actions": [
                        {
                            "name": "kit_read",
                            "arguments": {
                                "path": "src/evaluation_harness/trace_sources/base.py",
                                "start_line": 1,
                                "end_line": 60,
                            },
                        },
                        {
                            "name": "kit_propose",
                            "arguments": {
                                "path": target,
                                "expected_sha256": "@current",
                                "content": bad,
                            },
                        },
                        {
                            "name": "kit_propose",
                            "arguments": {
                                "path": target,
                                "expected_sha256": "@current",
                                "content": good,
                            },
                        },
                    ],
                },
            )
    # Freeze exact installed bytes; subsequent root edits cannot change these cells.
    S.save(
        BATCH / "candidate-pins.json",
        {
            case: S.read(
                BATCH
                / "cells"
                / case
                / "isolated/.local-agents/strata/installation.json"
            )
            for case in CASES
        },
    )
    print(
        "Registered fresh installed offline recovery control+six live known-contract units;0 model"
    )


def run(case, used):
    assert used < 50
    if case != "control":
        assert (
            S.read(BATCH / "cells/control/result.json")["host_handoff_verified"] is True
        )
    root = BATCH / "cells" / case / "isolated"
    pins = S.read(BATCH / "candidate-pins.json")[case]["files"]
    assert all(S.sha(root / ".local-agents" / p) == h for p, h in pins.items())
    packet = S.read(root / ".agent/packet.json")
    prepared = root / ".agent/prepared" / packet["run_id"]
    if case == "control":
        args = [
            S.PYTHON,
            "-B",
            root / ".local-agents/strata/strata_native_host_v4.py",
            "--packet",
            prepared / "packet.json",
            "--config",
            prepared / "config.json",
            "--program",
            root.parent / "frontend.json",
        ]
    else:
        doctor = command(
            [
                S.PYTHON,
                "-B",
                root / ".local-agents/strata-worker.py",
                "doctor",
                "--config",
                prepared / "config.json",
            ],
            root,
        )
        S.save(root.parent / "doctor.json", doctor)
        assert doctor["exit_code"] == 0, doctor
        args = [
            S.PYTHON,
            "-B",
            root / ".local-agents/strata-worker.py",
            "run",
            "--packet",
            prepared / "packet.json",
            "--config",
            prepared / "config.json",
        ]
    result = command(args, root, timeout=1020)
    S.save(root.parent / "process.json", result)
    if not (root / ".agent/native-host-summary.json").exists():
        raise AssertionError(result)
    summary = S.read(root / ".agent/native-host-summary.json")
    S.save(root.parent / "result.json", {"exit_code": result["exit_code"], **summary})
    print(result["stdout"][-1500:], result["stderr"][-2000:])
    if case == "control":
        assert result["exit_code"] == 0 and summary["host_handoff_verified"], result
        actual = summary["actual"]
        assert (
            actual["edits"] == 2
            and actual["post_edit_checks"] == 2
            and actual["native_http_requests"] == 0
        ), actual
    elif result["exit_code"] != 0:
        report = S.read(root / ".agent/native-host-report.json")
        print("RETAINED FAILURE:", report.get("status"), report.get("failure_reason"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", *CASES])
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        run(args.mode, args.weekly_used)


if __name__ == "__main__":
    main()
