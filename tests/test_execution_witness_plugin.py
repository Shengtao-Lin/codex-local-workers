"""Diagnostic plugin retains actual pass/fail/JUnit and does not inspect objects."""

import importlib.util
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

PLUGIN = Path(__file__).resolve().parents[1] / "benchmarks/execution_witness_plugin.py"
SPEC = importlib.util.spec_from_file_location("witness", PLUGIN)
WITNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WITNESS)


def test_nonbuiltin_values_never_invoke_custom_hooks():
    class Child(int):
        def __repr__(self):
            raise AssertionError("repr called")

        def __int__(self):
            raise AssertionError("int called")

    assert WITNESS.value_fact(Child(2)) == {"type": "Child"}
    assert WITNESS.value_fact({"v": None}) == {"v": None}
    assert len(WITNESS.value_fact("x" * 200)) == 48


def test_real_pytest_witness_preserves_failure_and_source_scope(tmp_path):
    shutil.copyfile(PLUGIN, tmp_path / "witness_plugin.py")
    (tmp_path / "subject.py").write_text(
        "def choose(config):\n    v = config.get('v')\n    if v is None:\n        return 1000\n    return v\n",
        encoding="utf-8",
    )
    (tmp_path / "test_subject.py").write_text(
        "import pytest\nfrom subject import choose\ndef test_ok():\n    assert choose({'v':2}) == 2\ndef test_error():\n    with pytest.raises(ValueError):\n        choose({'v':None})\n",
        encoding="utf-8",
    )
    env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    for enabled in (False, True):
        argv = [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "test_subject.py",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--junitxml={enabled}.xml",
        ]
        if enabled:
            argv += ["-p", "witness_plugin", "--witness-source", "subject.py"]
        result = subprocess.run(
            argv,
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert result.returncode == 1, result.stdout + result.stderr
        cases = ET.parse(tmp_path / f"{enabled}.xml").findall(".//testcase")
        assert len(cases) == 2
        failures = [c.find("failure") for c in cases if c.find("failure") is not None]
        assert len(failures) == 1
        failure = failures[0]
        evidence = failure.get("message", "") + (failure.text or "")
        assert "DID NOT RAISE" in evidence
        properties = ET.parse(tmp_path / f"{enabled}.xml").findall(
            ".//property[@name='execution_witness_v1']"
        )
        assert len(properties) == int(enabled)
        if enabled:
            evidence = properties[0].get("value")
            assert '"return_event":1000' in evidence
            assert '"v":null' in evidence
            assert '"source":"test_subject.py"' not in evidence


def test_adapter_preserves_failure_identity_and_guards_witness_sources():
    sys.path.insert(0, str(PLUGIN.parent))
    import execution_witness_adapter as adapter

    original = {
        "test": "t::fails",
        "message": "original failure",
        "location": "test.py:3",
    }

    class Runtime:
        _junit_failures = staticmethod(lambda root: [dict(original)])

        def _compact_repair_payload(self, focus):
            return {"repair_focus": focus}

        def _validation_observation(self, validation):
            return {"status": validation.status}

        def _assert_read_allowed(self, path):
            if path != "src/a.py":
                raise ValueError("forbidden")

    adapter.install(
        SimpleNamespace(
            WorkerRuntime=Runtime, WorkerError=ValueError, SafeEditError=ValueError
        )
    )
    root = ET.fromstring(
        '<testsuite><testcase classname="t" name="fails"><failure message="original failure"/><properties><property name="execution_witness_v1" value=\'[{"source":"src/a.py","return_event":1000},{"source":"secret.py"}]\'/></properties></testcase></testsuite>'
    )
    rows = Runtime._junit_failures(root)
    assert {key: rows[0][key] for key in original} == original
    runtime = Runtime()
    runtime.validation = SimpleNamespace(
        status="failed", focused_tests={"diagnostic": {"failures": rows}}
    )
    evidence = runtime._compact_repair_payload({})["execution_witnesses"]
    assert len(evidence) == 1
    assert evidence[0]["observed_events_not_diagnosis"] == [
        {"source": "src/a.py", "return_event": 1000}
    ]
    runtime.validation = None
    assert runtime._compact_repair_payload({})["execution_witnesses"] == []
