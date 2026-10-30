"""Default-off formal adapter: eligible static failure -> bound header repair."""

import copy
import re
from pathlib import Path

import repair_representation_diagnostic as D


def locate(facts, binding, source, repo_root):
    checks = facts["validation_failure"]["configured_checks"]
    if (
        len(checks) != 1
        or checks[0].get("id") != "pyright"
        or checks[0].get("status") != "failed"
    ):
        return None
    output = checks[0].get("output", "")
    if output.count(" - error:") != 1:
        return None
    match = re.search(
        r'^\s*(.+\.py):([1-9]\d*):[1-9]\d* - error: Type annotation is missing for parameter "([A-Za-z_]\w*)" \(reportMissingParameterType\)\s*$',
        output,
        re.MULTILINE,
    )
    if match is None:
        return None
    path, line, parameter = match.group(1), int(match.group(2)), match.group(3)
    if Path(path).resolve() != (Path(repo_root) / binding["path"]).resolve():
        return None
    if not binding["start_line"] < line <= binding["end_line"]:
        return None
    lines = source.splitlines()
    if line > len(lines):
        return None
    span = {"path": binding["path"], "line": line, "source": lines[line - 1]}
    if binding["source"].count(span["source"]) != 1:
        return None
    try:
        D.header_shape(span["source"])
        tree = D.ast.parse(binding["source"])
    except (ValueError, SyntaxError):
        return None
    nodes = [
        n
        for n in D.ast.walk(tree)
        if isinstance(n, D.ast.FunctionDef)
        and n.lineno + binding["start_line"] - 1 == line
    ]
    if len(nodes) != 1 or nodes[0] is tree.body[0]:
        return None
    args = [*nodes[0].args.posonlyargs, *nodes[0].args.args, *nodes[0].args.kwonlyargs]
    args += [a for a in (nodes[0].args.vararg, nodes[0].args.kwarg) if a is not None]
    if not any(a.arg == parameter and a.annotation is None for a in args):
        return None
    return span


def make_runtime(worker, host, parent):
    original_interface = host.INTERFACE
    original_normalize = original_interface.normalize_whole
    original_prompt = original_interface.WHOLE_PROMPT

    class StaticSpanRuntime(parent):
        def __init__(self, root, packet, config, client):
            if config.get("experimental_static_span_repair") is not True:
                raise worker.WorkerError("Static span requires explicit opt-in")
            super().__init__(root, packet, config, client)
            self.active_span = None
            self.span_source = None
            self.span_binding = None
            # The loaded host is per invocation, with one writer/runtime. No
            # production file or shared live worker module is modified.
            host.INTERFACE.normalize_whole = self.normalize_proposal

        def proposal_context(self):
            host.INTERFACE.WHOLE_PROMPT = original_prompt
            messages, binding = super().proposal_context()
            facts = host.INTERFACE.restore_literal(messages[1]["content"])
            self.active_span = None
            self.span_source = None
            self.span_binding = None
            if facts["validation_failure"]["configured_checks"]:
                raw, digest = self.editor.read_bytes(binding["path"])
                if digest != binding["sha256"]:
                    raise worker.PolicyViolation(
                        "Source changed while binding static repair"
                    )
                source = raw.decode("utf-8-sig").replace("\r\n", "\n")
                span = locate(facts, binding, source, self.repo_root)
                if span is not None:
                    self.active_span = span
                    self.span_source = source
                    self.span_binding = copy.deepcopy(binding)
                    facts["repair_span"] = span
                    messages = [
                        {"role": "system", "content": D.PROMPTS["span"]},
                        {
                            "role": "user",
                            "content": host.INTERFACE.literal_input(facts),
                        },
                    ]
            self.RUN_STATE.write_json_once(
                self.archive.run_root
                / f"static-span-route-{self.host_requests + 1}.json",
                {
                    "mode": "span" if self.active_span else "whole",
                    "span": self.active_span,
                    "source_sha256": binding["sha256"],
                    "safety_scope_changed": False,
                },
            )
            return messages, binding

        def normalize_proposal(self, raw, binding):
            if self.active_span is None:
                return original_normalize(raw, binding)
            if binding != self.span_binding:
                raise ValueError("Static span binding changed before apply")
            args = D.normalize(raw, "span", binding, self.active_span, self.span_source)
            if "blocked_reason" in args:
                return args
            # Mechanical range substitution only. The model supplies the exact
            # line; host does not infer an annotation, fix syntax or format it.
            expanded = {
                "path": binding["path"],
                "expected_sha256": binding["sha256"],
                "find": binding["source"],
                "replace": binding["source"].replace(args["find"], args["replace"], 1),
            }
            self.RUN_STATE.write_json_once(
                self.archive.run_root
                / f"static-span-binding-{self.host_requests}.json",
                {
                    "span_arguments": args,
                    "expanded_arguments": expanded,
                    "code_repair_by_host": False,
                },
            )
            return expanded

    return StaticSpanRuntime
