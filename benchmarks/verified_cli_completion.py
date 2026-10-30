"""Defer only CLI timeout to the existing mandatory native readiness checks."""

import json
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


def extend(namespace):
    cli,lease=namespace["_cli_load"],namespace["role_model_lease"]
    timeout_type=namespace["subprocess"].TimeoutExpired
    def cli_load(path,client,timeout):
        started=time.monotonic()
        try:
            return cli(path,client,timeout)
        except timeout_type:
            events=getattr(client,"load_completion_events",[])
            events.append({"kind":"cli_timeout","model":client.model,"cli_timeout_seconds":timeout,"elapsed_seconds":round(time.monotonic()-started,3)})
            client.load_completion_events=events
            # Returning does NOT grant readiness. The original lease next checks
            # native inventory, sole-model identity, context and parallel=1.
    def receipt(client,start,verified):
        events=getattr(client,"load_completion_events",[])[start:]
        if events:
            target=Path.cwd() / ".agent" / ("model-load-"+uuid.uuid4().hex+".json")
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open("x",encoding="utf-8") as stream:
                json.dump({"events":events,"api_readiness_verified":verified,"model":client.model},stream,indent=2)
    @contextmanager
    def verified_lease(client,config):
        start=len(getattr(client,"load_completion_events",[]))
        verified=False
        try:
            with lease(client,config):
                verified=True
                receipt(client,start,True)
                yield
        except Exception:
            if not verified:
                receipt(client,start,False)
            raise
    namespace["_cli_load"],namespace["role_model_lease"]=cli_load,verified_lease
