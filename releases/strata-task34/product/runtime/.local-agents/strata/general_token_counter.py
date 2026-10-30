"""Read-only adapter to the installed Strata prompt encoder, never an engine.

Only an explicitly pinned trusted profile enables this helper. No model weights,
credentials, network, subprocesses or repository imports are used.
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace


def readonly(event, args):
    if event.startswith(
        ("socket.", "subprocess.", "os.system", "os.spawn", "os.startfile")
    ) or event in {
        "os.remove",
        "os.rename",
        "os.rmdir",
        "os.mkdir",
        "os.chmod",
        "os.chown",
        "os.link",
        "os.symlink",
        "os.truncate",
        "os.utime",
    }:
        raise PermissionError("Token counter cannot execute or use network")
    if event == "open":
        _, mode, flags = args
        if (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        ):
            raise PermissionError("Token counter cannot write files")


def count(profile, bodies):
    sys.dont_write_bytecode = True
    sys.addaudithook(readonly)
    source = Path(profile["source_root"]).resolve()
    tokenizer_root = Path(profile["tokenizer_root"]).resolve()
    required = {
        Path(profile["python"]).resolve(),
        source / "serve/server.py",
        source / "serve/frontend.py",
        source / "tools/strata_tokenizer.py",
        *[
            tokenizer_root / p
            for p in ("vocab.json", "merges.txt", "token_type.json", "chat_template.jinja")
        ],
    }
    pins = profile["files"]
    if not required.issubset({Path(p).resolve() for p in pins}):
        raise ValueError("Missing tokenizer/source pins")
    for path, expected in pins.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError("Token counter input drift: " + path)
    if profile.get("effort_end") is not False:
        raise ValueError("Only calibrated default effort placement supported")
    sys.path[:0] = [str(source), str(source / "tools")]
    from serve.frontend import ChatTemplate, anthropic_to_messages, literal_tags
    from serve.server import Service
    from strata_tokenizer import Tokenizer

    vocab = json.loads((tokenizer_root / "vocab.json").read_text(encoding="utf-8"))
    tokens = [None] * len(vocab)
    for token, index in vocab.items():
        tokens[index] = token
    tokenizer = Tokenizer(
        tokens,
        (tokenizer_root / "merges.txt").read_text(encoding="utf-8").split("\n"),
        json.loads((tokenizer_root / "token_type.json").read_text(encoding="utf-8")),
    )
    # Bind only pure methods, not Service.__init__, load(), prepare() or Engine.
    renderer = SimpleNamespace(
        tok=tokenizer,
        template=ChatTemplate(tokenizer_root / "chat_template.jinja"),
        literals=literal_tags(tokenizer.control_tokens),
        effort_end=False,
        prompts=None,
    )
    renderer.render_prompt = lambda *a, **kw: Service.render_prompt(renderer, *a, **kw)
    results = []
    for body in bodies:
        if body.get("model") != "iq3_s" or body.get("max_tokens") != 12288:
            raise ValueError("Unexpected model/output route")
        if body.get("tool_choice") not in (None, {"type": "auto"}):
            raise ValueError("Uncalibrated forced tool rendering")
        if body.get("thinking") != {"type": "enabled", "budget_tokens": 4096} or body.get(
            "output_config"
        ) != {"effort": "medium"}:
            raise ValueError("Uncalibrated thinking configuration")
        for message in body.get("messages", []):
            for block in (
                message.get("content", []) if isinstance(message.get("content"), list) else []
            ):
                if block.get("type") in {"image", "document"}:
                    raise ValueError("Text-only counter")
        messages, tools, kwargs = anthropic_to_messages(body)
        results.append(len(Service.encode_prompt(renderer, messages, tools, kwargs, store=False)))
    return results


if __name__ == "__main__":
    request = json.load(sys.stdin)
    print(json.dumps({"input_tokens": count(request["profile"], request["bodies"])}))
