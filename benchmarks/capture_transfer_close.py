"""Close the fixed failed matrix; replay invalid proposals, never repair them."""

import argparse
import json
from pathlib import Path

import capture_fixture_support as F
import capture_transfer_matrix as M
import harness_capture_transport as T


def close(used):
    batch = M.BATCH
    frozen = T.read(batch / "live-freeze.json")
    for path, sha in frozen["pins"].items():
        assert T.sha(path) == sha, path
    executed, unrun = [], []
    audits = []
    for name in M.ORDER:
        row = frozen["cells"][name]
        root = Path(row["root"])
        cell = root.parent
        result_path = cell / "result.json"
        if not result_path.exists():
            assert not (cell / "started.json").exists()
            assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
            unrun.append(
                {
                    "case": name,
                    "status": "NOT_RUN",
                    "reason": "fixed candidate6/6 gate unreachable after first candidate failed",
                }
            )
            continue
        result = T.read(result_path)
        assert not result["protected_drift"]
        packet = T.read(root / ".agent/packet.json")
        run = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        primary = T.read(run / "review.json")
        assert primary["decision"] == "replan"
        T.save(
            cell / "primary-decision.json",
            {
                "decision": "replan",
                "canonical_review": str(run / "review.json"),
                "sha256": T.sha(run / "review.json"),
                "semantic_takeover": False,
            },
        )
        wire = [T.read(p) for p in sorted((cell / "wire").glob("*-request.json"))]
        chat = [p for p in wire if p["url"].endswith("/chat/completions")]
        executed.append(
            {
                **result,
                "actual_chat_requests": len(chat),
                "primary": "replan",
                "reviewer_exercised": False,
            }
        )
        if "-candidate-" in name:
            interface = F.load(
                root / ".local-agents/proposal-interface.py",
                "closed_frozen_proposal_interface",
            )
            proposals = sorted(run.glob("proposal-response-*.json"))
            assert len(proposals) == len(chat) == 6
            records = []
            for path in proposals:
                number = path.stem.rsplit("-", 1)[1]
                raw, stats = (T.read(path)[k] for k in ("raw", "stats"))
                binding = T.read(run / ("proposal-request-" + number + ".json"))[
                    "binding"
                ]
                try:
                    interface.normalize_whole(raw, binding)
                except json.JSONDecodeError as exc:
                    records.append(
                        {
                            "proposal": int(number),
                            "raw_sha256": T.sha(path),
                            "valid_json": False,
                            "stage": "json_decode_before_source_edit",
                            "error": exc.msg,
                            "line": exc.lineno,
                            "column": exc.colno,
                            "bounded_error_context": raw[
                                max(0, exc.pos - 12) : exc.pos + 36
                            ],
                            "reported_input_tokens": stats.get("reported_input_tokens"),
                            "reported_context_utilization": stats.get(
                                "reported_context_utilization"
                            ),
                            "finish_reason": stats.get("finish_reason"),
                            "response_usage": stats.get("response_usage"),
                        }
                    )
                else:
                    raise AssertionError(
                        "Expected actual malformed JSON, not semantic rejection"
                    )
            assert all(r["finish_reason"] == "stop" for r in records)
            assert not (run / "cumulative.diff").read_text(encoding="utf-8").strip()
            assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
            audits.append(
                {
                    "case": name,
                    "source_unchanged": True,
                    "edits_applied": 0,
                    "decoder_replays": records,
                    "semantic_implementation_result": "UNASSESSED: invalid JSON never reached AST/edit/validation",
                }
            )
    assert len(executed) == 2 and len(unrun) == 10
    T.save(
        batch / "proposal-replay-audit.json",
        {"model_calls": 0, "repairs_or_reconstruction": False, "cases": audits},
    )
    T.save(batch / "grid-results.json", {"executed": executed, "not_run": unrun})
    baseline = T.read(T.BATCH / "baseline.json")
    permitted = {
        "benchmarks/harness_capture_transport.py",
        "docs/local-model-harness-convergence-plan.md",
    }
    drift = [
        p
        for p, sha in baseline["files"].items()
        if p not in permitted and (not (F.KIT / p).is_file() or T.sha(F.KIT / p) != sha)
    ]
    assert not drift, drift
    T.save(
        batch / "preservation.json",
        {
            "inherited_worktree_drift": drift,
            "all_freeze_pins_unchanged": True,
            "remaining_ten_inputs_unchanged": True,
            "sibling_writes": False,
            "production_runtime_handoff_changes": False,
            "commit_push": False,
        },
    )
    T.save(
        batch / "decision.json",
        {
            "qualification": "HOLD_FIXED_GATE_UNREACHABLE",
            "registered": 12,
            "executed": 2,
            "not_run": 10,
            "weekly_used_start": T.read(batch / "registration.json")[
                "weekly_used_start"
            ],
            "weekly_used_end": used,
            "weekly_used_ceiling": 15,
            "stop_reason": "Fixed6/6 candidate gate impossible; next change requires a separately registered Coder representation candidate, not in-place retry or easier task selection.",
            "actual_chat_requests": sum(r["actual_chat_requests"] for r in executed),
            "baseline": "Six requests: source eventually passed all fixed visible/private/static checks; final request attempted a no-op edit after validation, terminal gate rejected it, call ended turn limit. No Reviewer or acceptance.",
            "candidate": "Six requests: all malformed replacement JSON rejected at docstring quoting before any edit. Source unchanged; subsequent5 failing behavior tests reflect original source, not an applied incorrect repair. No Reviewer or acceptance.",
            "failure_classification": "Coder output serialization/protocol fit; not HTTP400, context exhaustion, model output cap, patch mismatch, stale observation transport or Reviewer semantic failure.",
            "model_semantic_capacity": "Not established by candidate: apparent solution text is not valid executable proposal. Baseline fixed checks pass, but no general capability or full-chain inference.",
            "offline_transport": "Prior114 controls plus54 overlapping engine/parity controls remain passed; no new successful host Coder-to-Reviewer live-chain credit.",
            "next_unique_recommendation": "A new bounded Coder output-channel comparison on this now-exposed metadata case: eliminate code-in-JSON-string escaping versus a genuinely schema-constrained string. Keep raw failures, current models, six requests, same source/tests/guards, frozen Reviewer. No semantic code reconstruction or prompt stacking; no new matrix until representation is qualified.",
            "primary_cost": "Unknown active-time/cloud-token cost; preparation and diagnosis required substantial Primary work, no savings proven.",
            "r4_passed": False,
            "product_default_enabled": False,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
