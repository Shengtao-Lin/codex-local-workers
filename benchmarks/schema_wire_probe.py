"""Four preregistered mechanical requests; exact outgoing bodies, no code task."""

import copy
import json
from pathlib import Path

import bounded_evidence_support as S
import capture_fixture_support as F

BATCH = S.KIT / "benchmarks/work/harness-convergence/schema-wire-20261022-1"


def main():
    assert not BATCH.exists()
    worker = F.load(S.KIT / ".local-agents/worker-runtime.py", "schema_probe_worker")
    protocol = F.load(S.KIT / ".local-agents/bounded/harness_protocol.py", "schema_probe_protocol")
    config = S.read(S.KIT / "benchmarks/work/harness-convergence/stable-recovery-20261022-1/cells/destination-2/isolated/.agent/config.json")
    flat = {"type":"object","properties":{"replacement":{"type":"string"}},"required":["replacement"],"additionalProperties":False}
    S.save(BATCH / "registration.json", {"authorization":"Approved autonomous infrastructure diagnosis after preserved task failures","weekly_used_start":33,"weekly_stop":60,"registered_requests":4,"order":["union-1","flat-1","flat-2","union-2"],"scope":"Mechanical schema enforcement only, no Worker/task/review acceptance credit","model":config["coder_model"],"context":config["coder_context_length"],"max_tokens":128,"single_residency":True,"schemas":{"union":protocol.SCHEMA,"flat":flat},"pins":{str(Path(__file__)):S.sha(__file__),str(S.KIT / ".local-agents/worker-runtime.py"):S.sha(S.KIT / ".local-agents/worker-runtime.py")}})
    client = worker.LMStudioClient(config["lmstudio_base_url"],config["coder_model"],180,max_tokens=128,structured_output=True,action_schema=copy.deepcopy(protocol.SCHEMA),context_length=24576,temperature=0.1,top_p=0.9,top_k=40,min_p=0.0,repeat_penalty=1.0)
    original = worker.urllib.request.urlopen
    current = None
    def capture(request, *args, **kwargs):
        if getattr(request,"full_url","").endswith("/chat/completions"):
            S.save(BATCH / (current + "-wire.json"),json.loads(request.data.decode("utf-8")))
        return original(request,*args,**kwargs)
    worker.urllib.request.urlopen = capture
    rows = []
    try:
        with worker.MODEL_RESIDENCY.role_model_lease(client,config):
            for current in ("union-1","flat-1","flat-2","union-2"):
                client.action_schema = copy.deepcopy(protocol.SCHEMA if current.startswith("union") else flat)
                client.schema_name = "proposal_wire_diagnostic"
                messages = [{"role":"system","content":"Return a JSON object only."},{"role":"user","content":'Return exactly this object: {"replacement":["line1","line2"]}'}]
                try:
                    raw = client.complete(messages)
                    data = json.loads(raw)
                    legal = isinstance(data,dict) and isinstance(data.get("replacement"),str) and set(data)=={"replacement"}
                    if current.startswith("union"):
                        try:
                            protocol.decode(raw)
                            legal = True
                        except ValueError:
                            legal = False
                    row = {"cell":current,"raw":raw,"schema_valid":legal,"stats":client.last_request_stats}
                except (worker.WorkerError,ValueError) as exc:
                    row = {"cell":current,"error":str(exc),"schema_valid":False,"stats":client.last_request_stats}
                S.save(BATCH / (current + "-response.json"),row)
                rows.append(row)
    finally:
        worker.urllib.request.urlopen = original
    valid = sum(r["schema_valid"] for r in rows)
    decision = {"status":"MECHANICAL_SCHEMA_OBSERVATION","valid":valid,"executed":len(rows),"rows":[{"cell":r["cell"],"schema_valid":r["schema_valid"],"error":r.get("error")} for r in rows],"interpretation":"Outgoing response_format is captured exactly. Violations establish non-enforcement for that request; valid outputs alone do not prove hard enforcement. No semantic task qualification."}
    S.save(BATCH / "decision.json",decision)
    print(json.dumps(decision))


if __name__ == "__main__":
    main()
