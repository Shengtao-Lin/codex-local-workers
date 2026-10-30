"""Output representation must preserve editing authority and real acceptance."""

import copy
import json
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r2_output as trial
import test_harness_r2_localized as localized_controls

root = localized_controls.root


def binding(root):
    return {
        "path": trial.B.SOURCE,
        "symbol": trial.B.SYMBOL,
        "sha256": trial.B.sha(root / trial.B.SOURCE),
        "source": trial.B.method(
            (root / trial.B.SOURCE).read_text(encoding="utf-8-sig")
        ),
    }


def repaired(block, *, partial=False):
    # Reference belongs to verifier only; never rendered in a worker request.
    for line in block.splitlines():
        if len(line) > 100 and not (partial and '"""' in line):
            indent = line[: len(line) - len(line.lstrip())]
            block = block.replace(
                line,
                textwrap.fill(
                    line.strip(),
                    width=96,
                    initial_indent=indent,
                    subsequent_indent=indent,
                ),
            )
    return block


@pytest.mark.parametrize("arm", ["exact", "whole"])
@pytest.mark.parametrize("newline", ["lf", "crlf", "bom-crlf"])
def test_both_interfaces_apply_reference_and_real_checks(root, arm, newline):
    path = root / trial.B.SOURCE
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if newline != "lf":
        text = text.replace("\n", "\r\n")
    path.write_bytes(
        ("\ufeff" if newline == "bom-crlf" else "").encode() + text.encode()
    )
    if newline == "bom-crlf":
        baseline = trial.old.checks(root, root, "bom-baseline")
        assert [r["exit_code"] for r in baseline["checks"]] == [1, 1, 1, 0]
        assert "U+FEFF" in baseline["checks"][0]["stdout"]
    bound = binding(root)
    replacement = repaired(bound["source"])
    raw = (
        json.dumps({"replacement": replacement})
        if arm == "whole"
        else json.dumps(
            {
                "path": bound["path"],
                "expected_sha256": bound["sha256"],
                "find": bound["source"],
                "replace": replacement,
            }
        )
    )
    module = trial.old.load_runtime()
    before = {
        p: trial.B.sha(root / p) for p in trial.file_map(root) if p != trial.B.SOURCE
    }
    lock = module.RepoWriteLock(root, "output-reference")
    lock.acquire()
    try:
        with trial.interface(module, arm, bound):
            result = trial.old.apply_proposal(module, root, raw, bound["sha256"], lock)
        assert result["status"] == "applied"
        facts = trial.old.checks(root, root, "reference")
        if newline == "bom-crlf":
            # Existing protected AST tests and formatter reject BOM even before
            # editing. Preserve that rejection and the original BOM, never strip
            # it to claim fixture acceptance. Registered live input has no BOM.
            assert path.read_bytes().startswith(b"\xef\xbb\xbf")
            assert facts["junit"] == baseline["junit"]
            assert [r["exit_code"] for r in facts["checks"]] == [1, 1, 0, 0]
            assert "U+FEFF" in facts["checks"][0]["stdout"]
        else:
            assert facts["junit"]["all_behavior_pass"]
            assert [r["exit_code"] for r in facts["checks"]] == [0, 0, 0, 0]
        assert all(trial.B.sha(root / p) == digest for p, digest in before.items())
    finally:
        lock.release()


@pytest.mark.parametrize(
    "case",
    [
        "noop",
        "newline-noop",
        "stale",
        "signature",
        "neighbor",
        "decorator",
        "not-function",
        "path",
        "extra",
        "mixed-blocked",
        "empty",
        "array",
        "duplicate-key",
        "invalid-json",
    ],
)
def test_whole_rejects_invalid_outputs_without_edit(root, case):
    bound = binding(root)
    replacement = repaired(bound["source"])
    value = {"replacement": replacement}
    if case == "noop":
        value["replacement"] = bound["source"]
    elif case == "newline-noop":
        value["replacement"] = bound["source"].replace("\n", "\r\n")
    elif case == "signature":
        value["replacement"] = replacement.replace(
            "source_trace_ids: list[str]", "source_trace_ids: str"
        )
    elif case == "neighbor":
        value["replacement"] += "\n    def unrelated(self):\n        return 1\n"
    elif case == "decorator":
        value["replacement"] = "    @staticmethod\n" + replacement
    elif case == "not-function":
        value["replacement"] = "    pass\n"
    elif case == "path":
        value["path"] = "tests/test_get_many.py"
    elif case == "extra":
        value["expected_sha256"] = "0" * 64
    elif case == "mixed-blocked":
        value["blocked_reason"] = "unable"
    elif case == "empty":
        value["replacement"] = ""
    elif case == "array":
        value = []
    raw = json.dumps(value)
    if case == "duplicate-key":
        raw = '{"replacement":"first","replacement":"second"}'
    elif case == "invalid-json":
        raw = "not JSON"
    if case == "stale":
        with (root / trial.B.SOURCE).open("ab") as handle:
            handle.write(b"\n# external version\n")
    before = (root / trial.B.SOURCE).read_bytes()
    module = trial.old.load_runtime()
    lock = module.RepoWriteLock(root, "output-negative")
    lock.acquire()
    try:
        with (
            trial.interface(module, "whole", bound),
            pytest.raises((ValueError, SyntaxError, module.SafeEditError)),
        ):
            trial.old.apply_proposal(module, root, raw, bound["sha256"], lock)
        assert (root / trial.B.SOURCE).read_bytes() == before
    finally:
        lock.release()


def test_partial_repair_still_fails_real_acceptance(root):
    bound = binding(root)
    module = trial.old.load_runtime()
    lock = module.RepoWriteLock(root, "output-partial")
    lock.acquire()
    try:
        with trial.interface(module, "whole", bound):
            trial.old.apply_proposal(
                module,
                root,
                json.dumps({"replacement": repaired(bound["source"], partial=True)}),
                bound["sha256"],
                lock,
            )
        facts = trial.old.checks(root, root, "partial")
        assert facts["junit"]["all_behavior_pass"]
        assert [r["exit_code"] for r in facts["checks"]] == [0, 0, 1, 0]
    finally:
        lock.release()


@pytest.mark.parametrize("error", [False, True])
def test_interface_restores_parser_schema_and_captures_original_binding(root, error):
    module = trial.old.load_runtime()
    bound = binding(root)
    frozen = copy.deepcopy(bound)
    original_schema = module.SINGLE_FUNCTION.PATCH_SCHEMA
    original_parser = module.SINGLE_FUNCTION.patch_action
    try:
        with trial.interface(module, "whole", bound):
            bound["sha256"] = "0" * 64
            result = module.SINGLE_FUNCTION.patch_action(
                json.dumps({"replacement": repaired(frozen["source"])})
            )
            assert result["arguments"]["expected_sha256"] == frozen["sha256"]
            assert result["arguments"]["find"] == frozen["source"]
            blocked = module.SINGLE_FUNCTION.patch_action(
                '{"blocked_reason":"missing dependency"}'
            )
            assert blocked["action"] == "FINISH_BLOCKED"
            if error:
                raise RuntimeError("simulated transport failure")
    except RuntimeError:
        assert error
    assert module.SINGLE_FUNCTION.patch_action is original_parser
    assert module.SINGLE_FUNCTION.PATCH_SCHEMA is original_schema


def test_host_never_reads_new_source_to_construct_patch(root):
    bound = binding(root)
    with patch.object(
        Path, "read_text", side_effect=AssertionError("Unexpected reread")
    ):
        args = trial.normalize_whole(
            json.dumps({"replacement": repaired(bound["source"])}), bound
        )
    assert args["find"] == bound["source"]
    assert args["expected_sha256"] == bound["sha256"]


def test_wrong_binding_rejected(root):
    bound = binding(root)
    bound["path"] = "tests/test_get_many.py"
    with pytest.raises(ValueError, match="outside"):
        trial.normalize_whole(json.dumps({"replacement": bound["source"]}), bound)
