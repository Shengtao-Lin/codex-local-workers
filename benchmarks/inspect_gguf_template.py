"""Read only GGUF header metadata; never load weights or change model settings."""

import argparse
import hashlib
import json
import struct
from pathlib import Path


def inspect(path):
    widths = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
    with path.open("rb") as stream:

        def integer(fmt):
            return struct.unpack("<" + fmt, stream.read(struct.calcsize(fmt)))[0]

        def string(capture=False):
            length = integer("Q")
            if length > path.stat().st_size - stream.tell():
                raise ValueError("invalid metadata string extent")
            if capture:
                if length > 1_000_000:
                    raise ValueError("metadata string exceeds inspection cap")
                return stream.read(length).decode("utf-8")
            stream.seek(length, 1)

        def skip(kind):
            if kind in widths:
                stream.seek(widths[kind], 1)
            elif kind == 8:
                string()
            elif kind == 9:
                subtype, count = integer("I"), integer("Q")
                if count > 10_000_000:
                    raise ValueError("metadata array exceeds inspection cap")
                if subtype in widths:
                    stream.seek(widths[subtype] * count, 1)
                else:
                    for _ in range(count):
                        skip(subtype)
            else:
                raise ValueError("unknown GGUF metadata type")

        if stream.read(4) != b"GGUF" or integer("I") not in (2, 3):
            raise ValueError("unsupported GGUF header")
        integer("Q")  # tensor count: weights are never read
        count = integer("Q")
        if count > 10_000:
            raise ValueError("metadata count exceeds inspection cap")
        for _ in range(count):
            key, kind = string(True), integer("I")
            if key == "tokenizer.chat_template" and kind == 8:
                template = string(True)
                lines = template.splitlines()
                selected = set()
                for number, line in enumerate(lines):
                    if "reasoning" in line.lower():
                        selected.update(
                            range(max(0, number - 2), min(len(lines), number + 3))
                        )
                return {
                    "path": str(path.resolve()),
                    "size": path.stat().st_size,
                    "template_sha256": hashlib.sha256(template.encode()).hexdigest(),
                    "template_lines": len(lines),
                    "header_bytes_read_or_skipped": stream.tell(),
                    "reasoning_template_excerpt": [
                        f"{n + 1}: {lines[n]}" for n in sorted(selected)
                    ],
                    "qualification": "Embedded template only; does not establish active LM Studio overrides or rendered prompt",
                }
            skip(kind)
    raise ValueError("chat template not found")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("path", type=Path)
    print(json.dumps(inspect(parser.parse_args().path), indent=2))
