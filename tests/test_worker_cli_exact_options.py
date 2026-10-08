"""Unknown/abbreviated options must fail before loading config or invoking workers."""

import importlib.util
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

KIT = Path(__file__).resolve().parents[1]
ENTRIES = (
    ("explorer-runtime.py", "--task", "probe", "load_json", "--repo"),
    ("worker-runtime.py", "--packet", "packet.json", "load_json", "--repo"),
    ("reviewer-runtime.py", "--request", "request.json", "load_object", "--repo"),
    ("local-unit.py", "--packet", "packet.json", "run_unit", "--coder-rep"),
)


def module(name):
    spec = importlib.util.spec_from_file_location(
        "exact_cli_" + name.replace("-", "_").replace(".", "_"),
        KIT / ".local-agents" / name,
    )
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e[0])
@pytest.mark.parametrize("option", ("specific-prefix", "--conf", "--not-a-real-option"))
def test_invalid_option_fails_before_config_or_dispatch(entry, option):
    name, required, value, downstream, prefix = entry
    runtime = module(name)
    argv = [
        name,
        required,
        value,
        prefix if option == "specific-prefix" else option,
        "unused",
    ]
    with (
        patch.object(sys, "argv", argv),
        patch.object(
            runtime,
            downstream,
            side_effect=AssertionError("unexpected config/dispatch"),
        ) as called,
        redirect_stderr(io.StringIO()),
        redirect_stdout(io.StringIO()),
        pytest.raises(SystemExit) as exited,
    ):
        runtime.main()
    assert exited.value.code == 2
    called.assert_not_called()


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e[0])
def test_help_remains_available_without_worker_invocation(entry):
    runtime = module(entry[0])
    with (
        patch.object(sys, "argv", [entry[0], "--help"]),
        patch.object(
            runtime, entry[3], side_effect=AssertionError("unexpected invocation")
        ) as called,
        redirect_stdout(io.StringIO()) as output,
        pytest.raises(SystemExit) as exited,
    ):
        runtime.main()
    assert exited.value.code == 0
    assert entry[1] in output.getvalue()
    called.assert_not_called()
