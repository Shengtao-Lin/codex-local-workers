"""Observed source coverage, never a generated implementation/contract summary."""


def observe(memory, path, digest, line_numbers):
    previous = memory.get(path)
    seen = set(previous["lines"]) if previous and previous["sha256"] == digest else set()
    fresh = not previous or previous["sha256"] != digest or bool(set(line_numbers) - seen)
    memory[path] = {"sha256": digest, "lines": sorted(seen | set(line_numbers))}
    return fresh


def coverage_view(memory, current):
    result = []
    for path, entry in memory.items():
        if current.get(path) != entry["sha256"]:
            continue
        ranges = []
        for line in entry["lines"]:
            if ranges and line == ranges[-1][1] + 1:
                ranges[-1][1] = line
            else:
                ranges.append([line, line])
        result.append({"path": path, "sha256": entry["sha256"], "observed_ranges": ranges})
    return result
