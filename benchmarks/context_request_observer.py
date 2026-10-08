"""Observe retained evidence metadata without changing model input or output."""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def evidence(messages):
    paths, validation_refs = {}, set()

    def visit(value):
        if isinstance(value, dict):
            path, content = value.get("path"), value.get("content")
            if isinstance(path, str) and isinstance(content, str):
                lines = [
                    int(s.partition(": ")[0])
                    for s in content.splitlines()
                    if s.partition(": ")[1] and s.partition(": ")[0].isdigit()
                ]
                if lines:
                    paths.setdefault(path, set()).update(lines)
            for key, child in value.items():
                if key == "validation_attempt_ref" and isinstance(child, str):
                    validation_refs.add(child)
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for message in messages:
        if message.get("role") != "user":
            continue
        prefix, _, body = message.get("content", "").partition("\n")
        if prefix in {"OBSERVATION", "REPAIR_REQUIRED"}:
            try:
                visit(json.loads(body))
            except ValueError:
                pass
    return {p: sorted(lines) for p, lines in paths.items()}, sorted(validation_refs)


class Observer:
    def __init__(self, complete, path):
        self.original = complete
        self.path = path
        path.open("x", encoding="utf-8").close()
        self.seen = set()
        self.count = 0

    def __call__(self, client, messages):
        paths, validations = evidence(messages)
        self.count += 1
        record = {
            "request": self.count,
            "messages": len(messages),
            "visible_source_lines": paths,
            "evicted_previously_visible_paths": sorted(self.seen - paths.keys()),
            "visible_validation_refs": validations,
            "method": "structured observation lines only; free-text replay and packet are not parsed",
        }
        self.seen.update(paths)
        try:
            response = self.original(client, messages)
            record["status"] = "completed"
            record["response_sha256"] = hashlib.sha256(response.encode()).hexdigest()
            try:
                action = json.loads(response).get("action")
                if isinstance(action, str):
                    record["response_action"] = action[:80]
            except (ValueError, AttributeError):
                pass
            return response
        except Exception as error:
            record.update(status="failed", error_type=type(error).__name__)
            raise
        finally:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--role", choices=("coder", "reviewer"), required=True)
    parser.add_argument("--trace", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    name = "worker-runtime.py" if args.role == "coder" else "reviewer-runtime.py"
    spec = importlib.util.spec_from_file_location(
        "observed_role", args.snapshot / ".local-agents" / name
    )
    runtime = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runtime
    spec.loader.exec_module(runtime)
    client_type = (
        runtime.LMStudioClient
        if args.role == "coder"
        else runtime.WORKER.LMStudioClient
    )
    observer = Observer(client_type.complete, args.trace)
    client_type.complete = lambda client, messages: observer(client, messages)
    sys.argv = [name, *remaining]
    return runtime.main()


if __name__ == "__main__":
    raise SystemExit(main())
