"""Deterministic delta projection, not model memory or generated summarization."""

import ast
import copy
import json


class FeedbackProjection:
    def __init__(self):
        self.started = False
        self.source_sha = None
        self.seen = set()

    def project(self, facts, context, task_material):
        result = copy.deepcopy(context)
        target = facts["target"]
        result.pop("task_material", None)
        if not self.started:
            result["task_material"] = task_material
            result["projection"] = "initial-full"
            self.started = True
        else:
            result["projection"] = "delta-not-new-instructions"
            if target["sha256"] != self.source_sha:
                node = next(
                    n
                    for n in ast.parse(target["source"]).body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and n.name == target["symbol"]
                )
                lines = target["source"].splitlines()
                result["current_target"] = {
                    "path": target["path"],
                    "symbol": target["symbol"],
                    "sha256": target["sha256"],
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "source": "\n".join(lines[node.lineno - 1 : node.end_lineno])
                    + "\n",
                }
                result["validation_failure"] = copy.deepcopy(
                    facts["validation_failure"]
                )
                result["supplemental_host_diagnostics"] = copy.deepcopy(
                    facts.get("supplemental_host_diagnostics", {})
                )
            if facts.get("protocol_feedback"):
                result["protocol_feedback"] = facts["protocol_feedback"]
        self.source_sha = target["sha256"]
        observations = []
        for item in result.get("evidence_observations", []):
            key = json.dumps([item["request"], item["hashes"]], sort_keys=True)
            if key not in self.seen:
                observations.append(item)
                self.seen.add(key)
        result["evidence_observations"] = observations
        return result
