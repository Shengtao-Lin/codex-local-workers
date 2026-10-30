"""One observation-only replay: retain response shapes/hashes, never source text."""

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import explorer_report_recovery_trial as V

BATCH = V.I.BASE / "explorer-wire-shapes-20261022-1"


def shape(value):
    return {str(k): ("array:" + str(len(v)) if isinstance(v, list) else type(v).__name__)
            for k, v in value.items()} if isinstance(value, dict) else type(value).__name__


def child(root):
    path = root / ".local-agents/explorer-runtime.py"
    spec = importlib.util.spec_from_file_location("wire_shape_explorer", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    original = module.LMStudioClient._post

    def observed(client, messages, **kwargs):
        payload = original(client, messages, **kwargs)
        choice = payload["choices"][0]
        message = choice["message"]
        content = message.get("content")
        prefix = None
        trailing = None
        if isinstance(content, str):
            try:
                prefix, end = json.JSONDecoder().raw_decode(content.lstrip())
                trailing = len(content.lstrip()[end:].strip())
            except ValueError:
                pass
        record = {"tool_choice": client.native_tool_choice,
                  "content_chars": len(content) if isinstance(content, str) else 0,
                  "content_prefix_shape": shape(prefix),
                  "content_argument_shape": shape(prefix.get("arguments")) if isinstance(prefix, dict) else None,
                  "trailing_chars": trailing, "finish_reason": choice.get("finish_reason"), "tool_calls": []}
        for call in message.get("tool_calls", []):
            function = call.get("function", {})
            arguments = function.get("arguments")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except ValueError:
                    arguments = None
            record["tool_calls"].append({"name": function.get("name"), "argument_shape": shape(arguments)})
        S.save(BATCH / "wire-shapes" / f"{len(list((BATCH / 'wire-shapes').glob('*.json'))) if (BATCH / 'wire-shapes').exists() else 0:02}.json", record)
        return payload

    module.LMStudioClient._post = observed
    sys.argv = [str(path), "--task", V.INV.TASK, "--task-id", "packaged-revision-impact",
                "--report", str(root / ".agent/explorer-report.json"), "--full-report"]
    raise SystemExit(module.main())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run", "child"))
    p.add_argument("--weekly-used", type=int)
    a = p.parse_args()
    if a.mode == "child":
        child(BATCH / "isolated")
    elif a.mode == "prepare":
        V.BATCH = BATCH
        V.prepare(a.weekly_used)
        S.save(BATCH / "diagnostic-registration.json", {"scope": "One observation-only diagnostic, unchanged inputs/model/candidate/budgets; no success-rate denominator merge",
               "reason": "No archived raw provider shape: determine content-vs-tool dispatch, valid-prefix/trailing metadata and missing report fields without source/raw-output logging",
               "script_sha256": S.sha(__file__), "weekly_stop": 60})
    else:
        assert 0 <= a.weekly_used < 60
        reg = S.read(BATCH / "registration.json")
        assert all(S.sha(path) == digest for path, digest in reg["pins"].items())
        S.save(BATCH / "start.json", {"weekly_used": a.weekly_used, "epoch": time.time()})
        result = T.run([S.PYTHON, "-B", __file__, "child"], BATCH / "isolated", timeout=1200)
        S.save(BATCH / "process.json", result)
        print("Observation-only run complete; original failures unchanged", result["exit_code"])
