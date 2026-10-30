"""Remove only duplicate canonical quotes whose real source stays visible."""

import copy
import json


def source_index(evidence):
    result = {}
    for item in evidence:
        lines = result.setdefault(item["path"], {})
        for line in item["content"].splitlines():
            number, separator, source = line.partition(": ")
            if separator and number.isdigit():
                lines[int(number)] = source
    return result


def compact(value, sources):
    if isinstance(value, list):
        return [compact(item, sources) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: compact(item, sources) for key, item in value.items()}
    ref = value.get("source_ref", value)
    if not isinstance(ref, dict):
        return result
    path, start, end = ref.get("path"), ref.get("start_line"), ref.get("end_line")
    if not isinstance(path, str):
        return result
    if type(start) is not int or type(end) is not int or not 1 <= start <= end:
        return result
    lines = sources.get(path, {})
    if not all(number in lines for number in range(start, end + 1)):
        return result
    expected = "\n".join(lines[number] for number in range(start, end + 1))
    for field in ("source_quote", "canonical_quote"):
        if value.get(field) == expected:
            result.pop(field)
            result[field + "_location"] = (
                f"LOCAL_REVIEW_INPUT.provided_read_evidence:{path}:{start}-{end}"
            )
    return result


def compact_messages(messages, evidence):
    if not evidence:
        return copy.deepcopy(messages)
    sources = source_index(evidence)
    result = copy.deepcopy(messages)
    for message in result:
        content = message.get("content", "")
        if message.get("role") in {"user", "tool"} and content.startswith(
            "OBSERVATION\n"
        ):
            try:
                observation = json.loads(content.split("\n", 1)[1])
            except ValueError:
                continue
            message["content"] = "OBSERVATION\n" + json.dumps(
                compact(observation, sources), ensure_ascii=False
            )
    return result


def install(reviewer):
    original = reviewer.ReviewerRuntime.run

    def run(runtime):
        complete = runtime.client.complete

        def compacted(messages):
            runtime._assert_observed_sources_current()
            presented = compact_messages(
                messages, getattr(runtime, "provided_read_evidence", [])
            )
            return complete(presented)

        runtime.client.complete = compacted
        try:
            return original(runtime)
        finally:
            runtime.client.complete = complete

    reviewer.ReviewerRuntime.run = run
