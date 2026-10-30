"""One guarded formatter preparation and location-bound static header repairs."""

import re
from pathlib import Path

import coder_static_span as SPAN


def locate(facts, binding, source, repo_root):
    old = SPAN.locate(facts, binding, source, repo_root)
    if old is not None:
        return old
    return locate_ruff(facts, binding, source, repo_root)


def locate_ruff(facts, binding, source, repo_root):
    checks = facts["validation_failure"]["configured_checks"]
    if (
        len(checks) != 1
        or checks[0].get("id") != "ruff-check"
        or checks[0].get("status") != "failed"
    ):
        return None
    output = checks[0].get("output", "")
    locations = re.findall(
        r"^\s*--> (.+\.py):([1-9]\d*):[1-9]\d*\s*$", output, re.MULTILINE
    )
    rules = re.findall(r"^([A-Z][A-Z0-9]+) .+$", output, re.MULTILINE)
    if (
        len(locations) != 1
        or len(rules) != 1
        or not re.search(r"^Found 1 error\.", output, re.MULTILINE)
    ):
        return None
    path, line = locations[0][0], int(locations[0][1])
    path = Path(path)
    if not path.is_absolute():
        path = Path(repo_root) / path
    if path.resolve() != (Path(repo_root) / binding["path"]).resolve():
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
        SPAN.D.header_shape(span["source"])
        tree = SPAN.D.ast.parse(binding["source"])
    except (ValueError, SyntaxError):
        return None
    nodes = [
        n
        for n in SPAN.D.ast.walk(tree)
        if isinstance(n, SPAN.D.ast.FunctionDef)
        and n.lineno + binding["start_line"] - 1 == line
    ]
    if len(nodes) != 1 or nodes[0] is tree.body[0]:
        return None
    return span


def make_runtime(worker, host, parent):
    base = SPAN.make_runtime(worker, host, parent)

    class UnifiedPreparation(base):
        def __init__(self, root, packet, config, client):
            if config.get("experimental_unified_preparation") is not True:
                raise worker.WorkerError("Unified preparation requires explicit opt-in")
            super().__init__(root, packet, config, client)

        def host_validate(self):
            if self.validation_count >= self.host_check_cap:
                raise worker.WorkerError("Host validation budget exhausted")
            if (
                self.changed
                and not self.autoformat_used
                and self.config.get("autoformat_on_ruff_failure", True) is not False
            ):
                python = self.python_path()
                commands = self.validation_profile().get("commands", [])
                trusted = any(
                    c.get("id") == "ruff-format"
                    and "--check" in c.get("argv", [])
                    and self._trusted_ruff_format_command(
                        [
                            a.replace("{python}", str(python)).replace(
                                "{repo}", str(self.repo_root)
                            )
                            for a in c["argv"]
                        ],
                        python,
                    )
                    for c in commands
                )
                if trusted:
                    count = self.validation_count
                    before = self._validation_facts()
                    changed = self._try_autoformat(python)
                    if self.validation_count != count:
                        raise worker.PolicyViolation(
                            "Formatter altered validation counter"
                        )
                    self.RUN_STATE.write_json_once(
                        self.archive.run_root / "unified-format-preparation.json",
                        {
                            "kind": "preparation_not_validation",
                            "before": before,
                            "after": self._validation_facts(),
                            "changed": changed,
                            "validation_count_before": count,
                            "validation_count_after": self.validation_count,
                            "formatter_cap": 1,
                            "acceptance_credit": False,
                        },
                    )
            return super().host_validate()

        def proposal_context(self):
            original = SPAN.locate

            # SPAN's implementation resolves its locator at call time. Keep the
            # override local to this invocation of context construction, and
            # invoke the captured original directly to avoid recursive patching.
            def combined(facts, binding, source, root):
                prior = original(facts, binding, source, root)
                return (
                    prior
                    if prior is not None
                    else locate_ruff(facts, binding, source, root)
                )

            SPAN.locate = combined
            try:
                return super().proposal_context()
            finally:
                SPAN.locate = original

    return UnifiedPreparation
