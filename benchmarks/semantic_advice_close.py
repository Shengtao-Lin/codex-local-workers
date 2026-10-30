"""Independent immutable collector for the registered advice diagnostic."""

import argparse
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import semantic_advice_diagnostic as S


def audit_snapshot():
    """Independent offline check of peripheral Muse claims; no proposal/model call."""
    row = S.T.read(S.BATCH / "cells.json")["direct-1"]
    sys.path.insert(0, str(Path(row["root"]) / "src"))
    spec = importlib.util.spec_from_file_location("frozen_failed_mapping", S.BATCH / "snapshot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    typed = module.Message(role="user", content=[{"type": "text", "text": "hello"}])
    same = module.messages_output({"messages": typed}, None).messages[0] is typed
    observations = []
    for value in (False, 0, "text", b"text", {}, {"role": "unknown"}):
        try:
            module.messages_output({"messages": value}, None)
            outcome = "returned"
        except Exception as exc:
            outcome = type(exc).__name__
        observations.append({"input": repr(value), "outcome": outcome})
    S.T.save(S.BATCH / "independent-snapshot-audit.json", {
        "model_calls": 0, "source_sha256": S.T.sha(S.BATCH / "snapshot.py"),
        "typed_identity_preserved": same, "observations": observations,
        "conclusion": "Old draft already preserves typed identity and scalar TypeError; wrong Mapping exception translation is the real defect. Muse1/2 peripheral contrary claims are unsupported."})


def close(used):
    T, batch = S.T, S.BATCH
    fixture = T.read(batch / "fixture.json")
    judgments = T.read(batch / "primary-adjudications.json")
    grid, requests = [], []
    for name in S.ORDER:
        cell = batch / "cases" / name
        if not (cell / "result.json").exists():
            grid.append({"case": name, "status": "NOT_RUN", "all_checks_passed": False})
            continue
        result = T.read(cell / "result.json")
        wires = [T.read(p)["body"] for p in sorted((cell / "wire").glob("*-request.json"))
                 if T.read(p)["url"].endswith("/chat/completions")]
        assert len(wires) == result["model_requests"] <= (2 if name.startswith("advised-") else 1)
        expected_models = ["meta/muse-glimmer", "qwen/qwen3-coder-30b"] if name.startswith("advised-") else ["qwen/qwen3-coder-30b"]
        assert [w["model"] for w in wires] == expected_models[:len(wires)]
        for w in wires:
            assert w["max_tokens"] == 4096
            requests.append({"case": name, "model": w["model"]})
        if (cell / "advice.json").exists():
            saved = T.read(cell / "advice.json")
            raw = T.read(cell / "advice-response.json")["raw"]
            assert S.advice(raw, fixture) == saved
            assert wires[0]["messages"] == S.messages(fixture, consult=True)
        if (cell / "response.json").exists():
            suggestion = T.read(cell / "advice.json") if name.startswith("advised-") else None
            assert wires[-1]["messages"] == S.messages(fixture, suggestion)
        assert not result["protected_drift"]
        tests = ET.parse(cell / "checks/junit.xml").findall(".//testcase")
        assert len(tests) == 25
        failures = [t.attrib["name"] for t in tests
                    if t.find("failure") is not None or t.find("error") is not None]
        grid.append({**result, "behavior_passed": 25 - len(failures),
                     "behavior_total": 25, "failed_tests": failures})
    assert len(requests) <= 9
    counts = {a: sum(r["all_checks_passed"] for r in grid if r["case"].startswith(a + "-"))
              for a in ("direct", "advised")}
    sound = sum(j["semantically_sound"] for j in judgments)
    qualified = counts["advised"] == sound == 3 and len(judgments) == 3
    pins = T.read(batch / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    baseline = T.read(batch / "baseline.json")
    assert T.git("rev-parse", "HEAD") == baseline["head"]
    assert all(T.sha(S.KIT / p) == sha for p, sha in baseline["tracked_files"].items())
    assert T.git("-C", "F:/ChatGPT/agent-runtime-kit", "status", "--short") == baseline["sibling_status"]
    T.save(batch / "grid-results.json", grid)
    T.save(batch / "metrics.json", {
        "actual_chat_requests": len(requests), "requests": requests,
        "all_checks_passed": counts, "denominator_per_arm": 3,
        "sound_advice": sound, "formal_reviewer_calls": 0, "extra_probes": 0,
        "full_chains": 0, "fresh_credit": False,
        "seconds": sum(r.get("seconds", 0) for r in grid),
        "primary_active_seconds": None, "cloud_tokens": None})
    decision = {
        "status": "DIAGNOSTIC_CRITERION_MET_NOT_FORMAL_RELEASE" if qualified else "NO_ADVICE_STAGE_QUALIFICATION",
        "all_checks_passed": counts, "sound_advice": sound,
        "registered": 6, "executed": sum(r.get("status") != "NOT_RUN" for r in grid),
        "r4_passed": False, "formal_candidate_authorized_by_result": False,
        "fresh_credit": False, "full_chain_credit": False,
        "weekly_used_registration": 5, "weekly_used_dispatch": 6,
        "weekly_used_end": used, "weekly_used_ceiling": 15,
        "next": "Only discuss a newly registered shared-budget formal candidate" if qualified else
                "Do not install consultation in runtime; distinguish sound explanation, implementation transfer and protocol failures using per-cell evidence. No automatic prompt/repair retry."}
    T.save(batch / "decision.json", decision)
    T.save(batch / "preservation.json", {
        "frozen_pins_verified": len(pins), "tracked_inherited_changes_unchanged": True,
        "production_not_modified": True, "sibling_status_unchanged": True,
        "head_unchanged": True, "commit_push": False,
        "prelive_failures_preserved": ["prepare baseline git helper signature", "controls-v1 13passed/3temp-permission errors"],
        "usage_correction": "usage-correction.json",
        "close_script_sha256": T.sha(Path(__file__)),
        "primary_judgments_sha256": T.sha(batch / "primary-adjudications.json")})
    print(json.dumps(decision), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--used", type=int)
    p.add_argument("--audit-only", action="store_true")
    args = p.parse_args()
    audit_snapshot() if args.audit_only else close(args.used)
