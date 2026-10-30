import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

KIT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(KIT / "benchmarks"))
import tagged_proposal_wire as C


def decoder():
    spec=importlib.util.spec_from_file_location("tagged_wire_base",KIT / ".local-agents/bounded/harness_protocol.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    C.extend(vars(module))
    return module.decode


@pytest.mark.parametrize("kind,key",[("replacement","replacement"),("blocked","blocked_reason")])
def test_lossless_normalization_preserves_source_or_block_reason(kind,key):
    value='def f():\n    return "雪"\n' if kind=="replacement" else "need approved caller"
    assert decoder()(json.dumps({"kind":kind,"content":value})) == ({key:value},[])


@pytest.mark.parametrize("value",[
    {"kind":"replacement","content":["source"]},
    {"kind":"shell","content":"command"},
    {"kind":"blocked","content":""},
    {"kind":"replacement","content":False},
    {"kind":"replacement","content":"source","path":"escape"},
    {"replacement":"old envelope"},
])
def test_bad_types_unknown_actions_or_fields_fail_closed(value):
    with pytest.raises(ValueError):
        decoder()(json.dumps(value))


def test_duplicate_keys_rejected():
    with pytest.raises(ValueError):
        decoder()('{"kind":"replacement","kind":"blocked","content":"x"}')


def test_actual_installed_entry_keeps_editor_checks_and_canonical_gate():
    from test_installable_bounded import project,run
    import bounded_evidence_support as S
    import limited_family_trial as L
    with tempfile.TemporaryDirectory(prefix="tagged-wire-control-") as directory:
        root=Path(directory)
        project(root,"labels","tagged-offline")
        folder=root / ".local-agents/bounded"
        (folder / "tagged_proposal_wire.py").write_bytes(Path(C.__file__).read_bytes())
        path=folder / "harness_protocol.py"
        path.write_text(path.read_text(encoding="utf-8")+"\nfrom .tagged_proposal_wire import extend\nextend(globals())\n",encoding="utf-8")
        result=run(root,[{"kind":"replacement","content":L.TASKS["labels"]["reference"]}])
        assert result.returncode==0,result.stderr
        report=S.read(root / ".agent/unit-report.json")
        assert report["status"]=="validation_passed_pending_review"
        actual=report["consolidated_harness"]["actual"]
        assert actual["edits"]==actual["post_edit_checks"]==1
        assert actual["protocol_recoveries"]==0
