"""Probe documented native reasoning controls; no worker or acceptance credit."""

import json
import urllib.error
import urllib.request

from capability_fit import WORK, write


def run():
    base = WORK / "roleq-native-reasoning-probe-1"
    base.mkdir(exist_ok=False)
    config = json.loads(
        (
            WORK
            / "roleq-six-1/reviewer-controls/window-groups-hidden-r1-low/.agent/config.json"
        ).read_text(encoding="utf-8")
    )
    source = (
        WORK
        / "roleq-six-1/reviewer-controls/window-groups-hidden-r1-low/src/product/target.py"
    ).read_text(encoding="utf-8")
    write(
        base / "plan.json",
        {
            "classification": "Native API compatibility probe, not Reviewer qualification",
            "endpoint": "/api/v1/chat",
            "axis": "reasoning low/high",
            "model": config["reviewer_model"],
            "source": "https://lmstudio.ai/docs/developer/rest/chat",
            "max_calls": 2,
            "single_model_residency": True,
            "precondition": "Only Muse already resident, after prior reviews complete",
            "production_config_change": False,
        },
    )
    for strength in ("low", "high"):
        body = {
            "model": config["reviewer_model"],
            "input": "Independently review this source against the contract: width must have EXACT int type >=1; bool and custom int subclasses must raise ValueError even on empty items. Return compact JSON with verdict and causal reason. No tools or code execution.\n"
            + source,
            "reasoning": strength,
            "max_output_tokens": 4096,
            "context_length": 24576,
            "store": False,
            "temperature": config["reviewer_temperature"],
            "top_p": config["reviewer_top_p"],
            "top_k": config["reviewer_top_k"],
            "min_p": config["reviewer_min_p"],
            "repeat_penalty": config["reviewer_repeat_penalty"],
        }
        endpoint = config["lmstudio_base_url"].removesuffix("/v1") + "/api/v1/chat"
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=360) as response:
                result = json.load(response)
                status = response.status
            record = {
                "http_status": status,
                "reasoning_requested": strength,
                "stats": result.get("stats"),
                "model_instance_id": result.get("model_instance_id"),
                "messages": [
                    item.get("content", "")[:2000]
                    for item in result.get("output", [])
                    if item.get("type") == "message"
                ],
            }
        except urllib.error.HTTPError as error:
            record = {
                "http_status": error.code,
                "reasoning_requested": strength,
                "error": error.read().decode("utf-8", errors="replace")[:2000],
            }
        write(base / f"{strength}.json", record)
        print(json.dumps(record), flush=True)


if __name__ == "__main__":
    run()
