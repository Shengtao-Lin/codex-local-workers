import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

KIT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(KIT / "benchmarks"))
import verified_cli_completion as C


@pytest.mark.parametrize("state,passes",[
    ({"context_length":24576,"parallel":1},True),
    ({"context_length":1000,"parallel":1},False),
    ({"context_length":24576,"parallel":2},False),
    ({"parallel":1},False),
    (None,False),
    ("extra",False),
])
def test_timeout_only_succeeds_after_original_readiness_invariants(tmp_path,monkeypatch,state,passes):
    spec=importlib.util.spec_from_file_location("load_completion_control",KIT / ".local-agents/model_residency.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    C.extend(vars(module))
    client=SimpleNamespace(base_url="http://127.0.0.1:12345/v1",model="meta/muse-glimmer",context_length=24576)
    config={"single_model_residency":True,"model_load_backend":"cli","model_switch_timeout_seconds":1,"explorer_model":"openai/gpt-oss-20b","coder_model":"qwen/qwen3-coder-30b","reviewer_model":client.model}
    empty={client.model:{"loaded_instances":[]}}
    instances=[] if state is None else [{"id":client.model,"config":state if state!="extra" else {"parallel":1,"context_length":24576}}]
    after={client.model:{"loaded_instances":instances}}
    if state=="extra":
        after["qwen/qwen3-coder-30b"]={"loaded_instances":[{"id":"other","config":{}}]}
    monkeypatch.chdir(tmp_path)
    with patch.object(module,"_cli_path",return_value=Path(__file__)), patch.object(module,"_inventory",side_effect=[empty,empty,after]), patch.object(module.tempfile,"gettempdir",return_value=str(tmp_path)), patch.object(module.subprocess,"run",side_effect=subprocess.TimeoutExpired("lms load",1)):
        if passes:
            with module.role_model_lease(client,config):
                assert client.load_completion_events[0]["kind"]=="cli_timeout"
        else:
            with pytest.raises(module.ModelResidencyError):
                with module.role_model_lease(client,config):
                    pytest.fail("Readiness was not established")
    import json
    receipts=list((tmp_path / ".agent").glob("model-load-*.json"))
    assert len(receipts)==1
    assert json.loads(receipts[0].read_text())["api_readiness_verified"] is passes
    assert not list(tmp_path.glob("*.lock"))
