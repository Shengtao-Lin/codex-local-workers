"""Summarize reported local main-loop usage without inventing missing tokens."""


def summarize(events):
    requests = []
    for event in events:
        facts = event.get("facts", {})
        if event.get("event") == "model_request":
            requests.append(facts)
        elif event.get("event") == "model_turn":
            requests.append(facts.get("model_request", {}))
    totals = {
        name: 0 for name in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    known = {name: 0 for name in totals}
    truncated = 0
    for request in requests:
        usage = request.get("response_usage", {})
        for name in totals:
            value = usage.get(name)
            if type(value) is int and value >= 0:
                totals[name] += value
                known[name] += 1
        truncated += request.get("finish_reason") == "length"
    return {
        "main_loop_request_events": len(requests),
        "reported_token_sums": {
            name: totals[name] if known[name] else None for name in totals
        },
        "token_field_coverage": known,
        "output_limit_events": truncated,
        "scope": "Recorded main-loop response usage only; excludes unrecorded probes/retries, loading and validation; local tokens are not Codex cloud tokens or cached-token savings",
    }
