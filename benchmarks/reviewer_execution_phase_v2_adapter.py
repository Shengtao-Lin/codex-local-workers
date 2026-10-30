"""Offer actual approved checks before assessment, never execute for the model."""

import copy
import json


def pending_executions(runtime):
    if not runtime.config.get("reviewer_require_approved_execution", False):
        return []
    attempted = {
        (item.get("kind"), item.get("id")) for item in runtime.approved_execution
    }
    # A failing actual execution releases the phase for an evidence-backed
    # rejection/escalation. Original final gates still disallow a false pass.
    if any(item.get("status") != "passed" for item in runtime.approved_execution):
        return []
    catalog = runtime.approved_execution_catalog()
    result = []
    for kind, key in (("test", "tests"), ("static_check", "static_checks")):
        result.extend(
            item for item in catalog[key] if (kind, item["id"]) not in attempted
        )
    return result


def execution_tools(tools, pending, approved_tools=()):
    if not pending:
        return copy.deepcopy(tools)
    ids = {}
    for item in pending:
        ids.setdefault(item["action"], []).append(item["id"])
    available = copy.deepcopy(tools)
    names = {item["function"]["name"] for item in available}
    for tool in approved_tools:
        name = tool["function"]["name"]
        if name in ids and name not in names:
            available.append(copy.deepcopy(tool))
            names.add(name)
    result = []
    for tool in available:
        name = tool["function"]["name"]
        if name in {"READ_FILE", "SEARCH"}:
            result.append(tool)
        elif name in ids:
            field = "test_id" if name == "RUN_APPROVED_TEST" else "check_id"
            tool["function"]["parameters"]["properties"][field]["enum"] = ids[name]
            result.append(tool)
    return result


def install(reviewer):
    original = reviewer.ReviewerRuntime.run

    def run(runtime):
        complete = runtime.client.complete

        def phased(messages):
            pending = pending_executions(runtime)
            tools = runtime.client.native_tools
            try:
                if isinstance(tools, list):
                    runtime.client.native_tools = execution_tools(
                        tools, pending, reviewer.REVIEW_NATIVE_TOOLS
                    )
                    if pending and not runtime.client.native_tools:
                        raise reviewer.ReviewError(
                            "execution phase has no approved native tool schema; request rejected locally"
                        )
                supplied = list(messages)
                if pending:
                    supplied.append(
                        {
                            "role": "user",
                            "content": "REQUIRED_EXECUTION_PHASE\n"
                            + json.dumps(
                                {
                                    "pending_actual_actions": pending,
                                    "instruction": "Choose a listed approved execution action before contract assessment or final report. No command is run automatically; only actual runtime results count. A failed execution permits evidence-backed rejection. Original final gates, source obligations and statuses remain unchanged.",
                                }
                            ),
                        }
                    )
                return complete(supplied)
            finally:
                runtime.client.native_tools = tools

        runtime.client.complete = phased
        try:
            return original(runtime)
        finally:
            runtime.client.complete = complete

    reviewer.ReviewerRuntime.run = run
