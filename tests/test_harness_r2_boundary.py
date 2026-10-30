"""Host owns only the function's terminal line ending, never semantic repair."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r2_boundary as trial
import test_harness_r2_output as prior

root = prior.root


def apply(root, raw, bound, arm="owned"):
    module = trial.old.load_runtime()
    lock = module.RepoWriteLock(root, "boundary-control")
    lock.acquire()
    try:
        with trial.boundary_interface(module, arm, bound):
            return trial.old.apply_proposal(module, root, raw, bound["sha256"], lock)
    finally:
        lock.release()


@pytest.mark.parametrize("newline", ["lf", "crlf"])
@pytest.mark.parametrize("terminal", [False, True])
def test_reference_preserves_external_bytes_and_all_checks(root, newline, terminal):
    path = root / trial.B.SOURCE
    source = path.read_text(encoding="utf-8-sig")
    path.write_bytes(
        source.replace("\n", "\r\n" if newline == "crlf" else "\n").encode()
    )
    bound = prior.binding(root)
    replacement = prior.repaired(bound["source"]).rstrip("\n") + (
        "\n" if terminal else ""
    )
    raw = json.dumps({"replacement": replacement})
    before = path.read_bytes()
    normalized = trial.terminal_boundary(trial.output.normalize_whole(raw, bound))
    assert apply(root, raw, bound)["status"] == "applied"
    file_newline = "\r\n" if newline == "crlf" else "\n"
    assert path.read_bytes() == before.replace(
        bound["source"].replace("\n", file_newline).encode(),
        normalized["replace"].replace("\n", file_newline).encode(),
        1,
    )
    facts = trial.old.checks(root, root, "boundary-reference")
    assert facts["junit"]["all_behavior_pass"]
    assert [c["exit_code"] for c in facts["checks"]] == [0, 0, 0, 0]


@pytest.mark.parametrize("arm", ["raw", "owned"])
def test_archived_model_output_without_new_model_call(root, arm):
    bound = prior.binding(root)
    response = trial.B.read(trial.PREVIOUS / "cases/literal-1/response.json")["content"]
    assert apply(root, response, bound, arm)["status"] == "applied"
    facts = trial.old.checks(root, root, "archived-replay")
    assert [c["exit_code"] for c in facts["checks"]] == (
        [0, 0, 0, 0] if arm == "owned" else [0, 1, 0, 0]
    )


@pytest.mark.parametrize("source_terminal", [False, True])
@pytest.mark.parametrize("reply_terminal", [False, True])
def test_eof_preserves_original_terminal_contract(
    root, source_terminal, reply_terminal
):
    path = root / trial.B.SOURCE
    original = (
        "class MlflowTraceSource:\n    async def get_many(self, source_trace_ids):\n        return []"
        + ("\n" if source_terminal else "")
    )
    path.write_bytes(original.encode())
    bound = prior.binding(root)
    replacement = bound["source"].rstrip("\n").replace(
        "return []", "return list(source_trace_ids)"
    ) + ("\n" if reply_terminal else "")
    assert (
        apply(root, json.dumps({"replacement": replacement}), bound)["status"]
        == "applied"
    )
    assert path.read_bytes().endswith(b"\n") is source_terminal
    assert path.read_text() == original.replace(
        "return []", "return list(source_trace_ids)"
    )


@pytest.mark.parametrize(
    "kind",
    [
        "noop",
        "newline-noop",
        "crlf-noop",
        "multiple-tail",
        "trailing-comment",
        "signature",
        "decorator",
        "neighbor",
        "invalid-json",
        "mixed-blocked",
        "path",
        "stale",
        "bad-indent",
    ],
)
def test_boundary_keeps_rejections_and_never_writes(root, kind):
    bound = prior.binding(root)
    value = {"replacement": prior.repaired(bound["source"]).rstrip("\n")}
    if kind in ("noop", "newline-noop", "crlf-noop"):
        value["replacement"] = bound["source"]
        if kind == "newline-noop":
            value["replacement"] = value["replacement"].rstrip("\n")
        if kind == "crlf-noop":
            value["replacement"] = value["replacement"].replace("\n", "\r\n")
    elif kind == "multiple-tail":
        value["replacement"] += "\n\n"
    elif kind == "trailing-comment":
        value["replacement"] += "\n# outside target"
    elif kind == "signature":
        value["replacement"] = value["replacement"].replace(
            "source_trace_ids: list[str]", "source_trace_ids: str"
        )
    elif kind == "decorator":
        value["replacement"] = "    @staticmethod\n" + value["replacement"]
    elif kind == "neighbor":
        value["replacement"] += "\n    def injected(self):\n        return 1"
    elif kind == "mixed-blocked":
        value["blocked_reason"] = "unable"
    elif kind == "path":
        value["path"] = "tests/test_get_many.py"
    elif kind == "stale":
        with (root / trial.B.SOURCE).open("ab") as stream:
            stream.write(b"\n# external modification\n")
    elif kind == "bad-indent":
        value["replacement"] = value["replacement"].replace(
            "        return result", "return result"
        )
    raw = "not-json" if kind == "invalid-json" else json.dumps(value)
    before = (root / trial.B.SOURCE).read_bytes()
    with pytest.raises((ValueError, SyntaxError)):
        apply(root, raw, bound)
    assert (root / trial.B.SOURCE).read_bytes() == before


@pytest.mark.parametrize("error", [False, True])
def test_parser_restored_and_binding_immutable(root, error):
    module = trial.old.load_runtime()
    bound = prior.binding(root)
    frozen = copy.deepcopy(bound)
    parser = module.SINGLE_FUNCTION.patch_action
    schema = module.SINGLE_FUNCTION.PATCH_SCHEMA
    try:
        with trial.boundary_interface(module, "owned", bound):
            bound["sha256"] = "0" * 64
            result = module.SINGLE_FUNCTION.patch_action(
                json.dumps(
                    {"replacement": prior.repaired(frozen["source"]).rstrip("\n")}
                )
            )
            assert result["arguments"]["expected_sha256"] == frozen["sha256"]
            assert result["arguments"]["replace"].endswith("\n")
            assert (
                module.SINGLE_FUNCTION.patch_action(
                    '{"blocked_reason":"dependency missing"}'
                )["action"]
                == "FINISH_BLOCKED"
            )
            if error:
                raise RuntimeError("failure")
    except RuntimeError:
        assert error
    assert module.SINGLE_FUNCTION.patch_action is parser
    assert module.SINGLE_FUNCTION.PATCH_SCHEMA is schema
