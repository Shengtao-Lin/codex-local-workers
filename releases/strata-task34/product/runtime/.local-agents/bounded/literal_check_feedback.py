import copy
import json


def fields(facts):
    yield ("target.source", facts["target"], "source")
    for index, item in enumerate(facts.get("failed_test_sources", [])):
        yield (f"failed_test_sources[{index}].source", item, "source")
    for group in ("validation_failure", "supplemental_host_diagnostics"):
        key = "configured_checks" if group == "validation_failure" else "checks"
        for index, check in enumerate(facts[group][key]):
            if isinstance(check.get("output"), str) and check.get("status") != "passed":
                yield (f"{group}.{key}[{index}].output", check, "output")


def render(facts):
    metadata = copy.deepcopy(facts)
    blocks = []
    for name, parent, key in fields(metadata):
        value = parent[key]
        if "\n<BEGIN " in value or "\n<END " in value:
            raise ValueError("Display delimiters in untrusted data")
        parent[key] = {"display_block": name}
        blocks.append(f"\n\n<BEGIN {name}>\n{value}\n<END {name}>")
    return json.dumps(metadata, ensure_ascii=False) + "".join(blocks)


def restore(text):
    metadata, offset = json.JSONDecoder().raw_decode(text)
    rest = text[offset:]
    candidates = [("target.source", metadata["target"], "source")]
    for index, item in enumerate(metadata.get("failed_test_sources", [])):
        candidates.append((f"failed_test_sources[{index}].source", item, "source"))
    for group in ("validation_failure", "supplemental_host_diagnostics"):
        key = "configured_checks" if group == "validation_failure" else "checks"
        for index, check in enumerate(metadata[group][key]):
            if isinstance(check.get("output"), dict):
                candidates.append((f"{group}.{key}[{index}].output", check, "output"))
    for name, parent, key in candidates:
        begin, end = (f"\n\n<BEGIN {name}>\n", f"\n<END {name}>")
        if (
            parent[key] != {"display_block": name}
            or not rest.startswith(begin)
            or rest.count(end) != 1
        ):
            raise ValueError("Display binding mismatch")
        value, rest = rest[len(begin) :].split(end, 1)
        parent[key] = value
    if rest:
        raise ValueError("Unexpected trailing data")
    return metadata
