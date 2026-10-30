"""Close the fixed installed repetition only from reverified current evidence."""

import argparse
from pathlib import Path

import installed_identity_repeats as R

S, D = R.S, R.D


def close(used):
    parent = R.PARENT
    registration = S.read(parent / "registration.json")
    assert all(S.sha(p) == h for p, h in registration["pins"].items())
    chains, rows = [], []
    for index in (1, 2):
        batch = parent / ("chain-" + str(index))
        reg = S.read(batch / "registration.json")
        assert all(S.sha(p) == h for p, h in reg["pins"].items())
        assert S.read(batch / "decision.json")["accepted_chains"] == 1
        metrics = S.read(batch / "metrics.json")
        plan, catalog = (
            S.read(batch / "approved-plan.json"),
            S.read(batch / "catalog.json"),
        )
        integration = S.read(batch / "integration.json")
        for topic in ("encode", "append"):
            binding = S.read(batch / "units" / topic / "binding.json")
            root, packet = Path(binding["root"]), binding["packet"]
            receipt = D.BRIDGE.verify_accepted_unit(
                plan,
                root,
                packet["unit_id"],
                {k: packet[k] for k in ("task_id", "run_id")},
                binding["config"],
                catalog,
                bridge_profile="bounded-v1",
            )
            assert receipt == S.read(root.parent / "acceptance.json")
            assert receipt == integration["unit_receipts"][topic]
            assert all(S.sha(root / p) == h for p, h in binding["protected"].items())
            result = S.read(root.parent / "result.json")
            assert result["all_checks_pass"] and not result["protected_drift"]
            row = next(r for r in metrics["rows"] if r["topic"] == topic)
            rows.append(
                {
                    "chain": index,
                    **row,
                    "independent_tests": result["independent_checks"][0]["stdout"]
                    .strip()
                    .splitlines()[-1],
                }
            )
        final_root = Path(S.read(batch / "units/append/binding.json")["root"])
        assert all(
            S.sha(final_root / p) == h for p, h in integration["current_files"].items()
        )
        chains.append(
            {
                "chain": index,
                "accepted": True,
                "coordinator_requests": metrics["coordinator_requests"],
                "integration_sha256": S.sha(batch / "integration.json"),
            }
        )
    S.save(
        parent / "metrics.json",
        {
            "registered": {"chains": 2, "units": 4},
            "executed": {"chains": 2, "units": 4},
            "accepted": {"chains": 2, "units": 4},
            "not_run": 0,
            "chains": chains,
            "rows": rows,
            "local_unit_seconds": sum(r["seconds"] for r in rows),
            "Primary_runtime_semantic_hints": 0,
            "Primary_implementation_edits": 0,
            "Primary_active_seconds": "unknown",
            "cloud_tokens": "unknown",
            "cost_savings": "Not established",
            "weekly_used": used,
            "weekly_limit": None,
        },
    )
    S.save(
        parent / "decision.json",
        {
            "status": "PASS_TWO_INSTALLED_KNOWN_CONTRACT_CHAINS",
            "gate": registration["gate"],
            "accepted_chains": 2,
            "accepted_units": 4,
            "scope": "Two fixed exposed real-package immutable snapshot repetitions, exact accepted producer transfer, no general planning/new-task/DB concurrency or persistence migration qualification",
            "qualification": "Explicit supervised installed path only; per-unit coordinator_enabled stays false; Primary still prepares contracts/tests/risk and reviews/accepts; no automatic dispatch or production enablement",
            "production_enabled": False,
            "Explorer": "NOT_RUN, no new location question; prior evidence-only qualification unchanged",
            "histories": "Earlier routing HOLDs, fixture failure and NOT_RUN preserved; no failure rerolled or score replaced",
            "next": "Keep this frozen live evidence; separate offline early Primary-input preflight correction, no change during completed batch",
        },
    )
    D.T.write(
        parent / "handoff.md",
        """# Installed known-contract repetition: 2/2 chains accepted

Both fixed Coordinator proposals were reviewed, then four bounded Coder/fresh Reviewer units independently accepted. Each chain ends with169 non-DB project/private/caller/round-trip tests and all strict static checks. Exact accepted producer bytes were protected in the consumer; complete project manifests and canonical acceptance evidence were reverified at closure.

Each Coder used one effective edit and one post-edit complete check. Each fresh Reviewer used one request, without findings or protocol errors. No runtime semantic hint, source rescue, no-op or favorable-review resampling. Primary reused frozen tasks/tests/reference, still classified risk and reviewed proposals/current full source and canonical facts. Byte-identical implementations were compared to the earlier fully read file, not accepted from a model summary. Active Primary time and cloud tokens unknown; no savings estimate.

This is repeated stability of two exposed contracts, not new-task competence. Explorer was not called without a new investigation question. General algorithm/type-repair failures and unknown Reviewer boundaries remain. The earlier two routing HOLDs, incomplete-snapshot failure and every NOT_RUN remain separate. Production defaults unchanged; this API does not dispatch or accept anything automatically.

The batch is closed, not an instruction to stop ongoing autonomous work. A separate offline correction will reject malformed Primary acceptance recipes before model calls; valid-input wire equivalence must remain unchanged.
""",
    )
    print(
        "Two installed known-contract chains accepted; all current evidence verified",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekly-used", type=int, required=True)
    close(parser.parse_args().weekly_used)
