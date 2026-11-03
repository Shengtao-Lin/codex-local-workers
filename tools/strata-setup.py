"""Create-only release acquisition and supervised Strata project setup.

Standard library only. Never starts a model, installs dependencies or changes
Strata. Project checks are reviewed data supplied by Primary, not model tools.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path, PurePosixPath

MAX_ZIP = 20 * 1024 * 1024
MAX_EXPANDED = 80 * 1024 * 1024
LAST_ATTEMPT = None
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}


class SetupError(ValueError):
    pass


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def ordinary(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if (
            item.is_symlink()
            or item.exists()
            and getattr(item.stat(), "st_file_attributes", 0) & 0x400
        ):
            raise SetupError("Reparse/symlink path rejected")
    return path


def safe_name(name):
    pure = PurePosixPath(name)
    parts = name.split("/")
    if (
        not name
        or "\\" in name
        or ":" in name
        or pure.is_absolute()
        or any(p in ("", ".", "..") or p.rstrip(" .") != p for p in parts)
    ):
        raise SetupError("Invalid archive/manifest path")
    if any(
        p.split(".")[0].upper()
        in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *[f"COM{i}" for i in range(1, 10)],
            *[f"LPT{i}" for i in range(1, 10)],
        }
        for p in parts
    ):
        raise SetupError("Windows device path rejected")
    return name


def verify_bundle(bundle):
    bundle = ordinary(bundle).resolve(strict=True)
    manifest = read(bundle / "manifest.json")
    if not isinstance(manifest, dict) or not manifest:
        raise SetupError("Missing flat SHA256 manifest")
    for name, expected in manifest.items():
        safe_name(name)
        if not isinstance(expected, str) or not re.fullmatch("[a-f0-9]{64}", expected):
            raise SetupError("Invalid manifest digest")
        path = ordinary(bundle / name)
        if not path.is_file() or sha(path) != expected:
            raise SetupError("Bundle file drift: " + name)
    actual = {
        p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()
    }
    if actual != set(manifest) | {"manifest.json"}:
        raise SetupError("Unmanifested bundle files")
    return manifest


def unpack(archive, expected, destination):
    archive, destination = Path(archive), ordinary(destination)
    if destination.exists():
        raise FileExistsError("Bundle destination already exists")
    if (
        not re.fullmatch("[a-f0-9]{64}", expected)
        or archive.stat().st_size > MAX_ZIP
        or sha(archive) != expected
    ):
        raise SetupError("Archive checksum/size mismatch")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        names = [safe_name(i.filename) for i in members if not i.is_dir()]
        if len(names) != len({n.casefold() for n in names}) or len(names) > 2000:
            raise SetupError("Duplicate/case-colliding archive names")
        if any(stat.S_ISLNK(i.external_attr >> 16) or i.flag_bits & 1 for i in members):
            raise SetupError("Symlink/encrypted archive rejected")
        if sum(i.file_size for i in members) > MAX_EXPANDED:
            raise SetupError("Expanded archive too large")
        material = {name: z.read(name) for name in names}
    manifest = json.loads(material.get("manifest.json", b"null"))
    if not isinstance(manifest, dict) or set(material) != set(manifest) | {
        "manifest.json"
    }:
        raise SetupError("Archive manifest inventory mismatch")
    if any(digest(material[name]) != value for name, value in manifest.items()):
        raise SetupError("Archive manifest hash mismatch")
    destination.mkdir(parents=True)
    for name, raw in material.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    return {"status": "VERIFIED_BUNDLE", "bundle": str(destination), "sha256": expected}


def fetch_release(repository, tag, asset, expected, destination):
    if (
        not re.fullmatch(r"[\w.-]+/[\w.-]+", repository)
        or not re.fullmatch(r"[\w.+-]+", tag)
        or not re.fullmatch(r"[\w.+-]+\.zip", asset)
    ):
        raise SetupError("Explicit GitHub repository/tag/ZIP asset required")
    destination = ordinary(destination)
    if destination.exists():
        raise FileExistsError("Download destination already exists")
    url = f"https://github.com/{repository}/releases/download/{tag}/{asset}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "strata-supervised-setup"}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        final = urllib.parse.urlsplit(response.url)
        if final.scheme != "https" or final.hostname not in {
            "github.com",
            "release-assets.githubusercontent.com",
            "objects.githubusercontent.com",
        }:
            raise SetupError("Unexpected release download origin")
        raw = response.read(MAX_ZIP + 1)
    if len(raw) > MAX_ZIP or digest(raw) != expected:
        raise SetupError("Downloaded archive checksum/size mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(raw)
    return {
        "status": "VERIFIED_DOWNLOAD",
        "url": url,
        "sha256": expected,
        "bytes": len(raw),
        "archive": str(destination),
    }


def install(bundle, project):
    bundle, project = Path(bundle), ordinary(project).resolve(strict=True)
    manifest = verify_bundle(bundle)
    required = "runtime/.local-agents/strata/task_workflow.py"
    if (
        required not in manifest
        or "runtime/.local-agents/strata/general_token_counter.py" not in manifest
    ):
        raise SetupError(
            "UNSUPPORTED_RELEASE: task.34-compatible supervised bundle required; old preview not upgraded silently"
        )
    source = bundle / "runtime/.local-agents"
    receipt = read(source / "strata/installation.json")
    if receipt.get("version") != "0.3.0-task.34-binding-preflight-candidate":
        raise SetupError(
            "UNSUPPORTED_RELEASE: this setup profile requires the exact tested task.34 runtime"
        )
    target = project / ".local-agents"
    if target.exists():
        ordinary(target)
        expected = {
            **receipt["files"],
            "strata/installation.json": sha(source / "strata/installation.json"),
        }
        actual = {
            p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()
        }
        if actual != set(expected) or any(
            sha(ordinary(target / name)) != value for name, value in expected.items()
        ):
            raise SetupError("EXISTING_INSTALL_DIFFERS: no merge, upgrade or overwrite")
        return {"status": "REUSED_IDENTICAL_INSTALL", "files": len(expected)}
    spec = importlib.util.spec_from_file_location(
        "verified_strata_install", bundle / "install.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"status": "INSTALLED", **module.install(source, project)}


def discover(home=None):
    candidates = []
    if home or os.environ.get("STRATA_HOME"):
        candidates.append(Path(home or os.environ["STRATA_HOME"]))
    else:
        for path in (Path.home() / ".strata/data/native-instances").glob("*.json"):
            data = read(path)
            if data.get("cwd"):
                candidates.append(Path(data["cwd"]).parent)
        candidates += [
            Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
            / "Programs/Strata",
            Path("C:/Program Files/Strata"),
        ]
    valid = {
        str(p.resolve()): p.resolve()
        for p in candidates
        if (p / "node/node.exe").is_file()
        and any(
            (p / entry).is_file()
            for entry in ("harness/lib/bin.js", "harness/apps/cli/lib/bin.js")
        )
        and (p / "control/python/python.exe").is_file()
    }
    if len(valid) != 1:
        raise SetupError(
            "NEEDS_STRATA_LOCATION: Primary supplies --strata-home; installation not modified"
        )
    return next(iter(valid.values()))


def check_spec(spec, project, python):
    if set(spec) != {"input_roots", "focused_tests", "commands"}:
        raise SetupError(
            "Primary-reviewed check mapping needs input_roots/focused_tests/commands"
        )
    for name in [*spec["input_roots"], *spec["focused_tests"]]:
        safe_name(name)
        if not ordinary(project / name).exists():
            raise SetupError("Missing project check input: " + name)
    commands = spec["commands"]
    if not commands or len({c.get("id") for c in commands}) != len(commands):
        raise SetupError("Nonempty unique project checks required")
    for command in commands:
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", str(command.get("id", ""))):
            raise SetupError("Invalid project check id")
        if (
            set(command) != {"id", "argv"}
            or not command["id"]
            or not isinstance(command["argv"], list)
            or not command["argv"]
        ):
            raise SetupError("Invalid check command shape")
        if command["argv"][0] != "{python}" or not all(
            isinstance(a, str) for a in command["argv"]
        ):
            raise SetupError("Trusted Python check commands only; no shell")
        args = command["argv"]
        if any(arg in {"--fix", "--fix-only", "--unsafe-fixes"} for arg in args):
            raise SetupError("Mutating validation flags rejected")
        if "ruff" in args and (
            "check" in args
            and "--no-fix" not in args
            or "format" in args
            and "--check" not in args
        ):
            raise SetupError("Ruff validation must not modify inputs")
    if not Path(python).is_file():
        raise SetupError(
            "NEEDS_PROJECT_PYTHON: use an existing environment; no dependency installation"
        )
    return spec


def discover_tokenizer(explicit=None):
    candidates = []
    if explicit:
        candidates = [Path(explicit)]
    else:
        for path in (Path.home() / ".strata/data/native-instances").glob("*.json"):
            native = read(path)
            if native.get("tokenizer") and (
                "iq3_s" in native.get("aliases", [])
                or str(native.get("model_name", "")).endswith("iq3_s")
            ):
                candidates.append(Path(native["tokenizer"]))
        if not candidates:
            candidates = [Path.home() / "Documents/Strata/packs/iq3_s/tokenizer"]
    valid = {
        str(p.resolve()): p.resolve()
        for p in candidates
        if all(
            (p / name).is_file()
            for name in (
                "chat_template.jinja",
                "merges.txt",
                "tokenizer.json",
                "token_type.json",
                "vocab.json",
            )
        )
    }
    if len(valid) != 1:
        raise SetupError(
            "NEEDS_TOKENIZER_LOCATION: Primary supplies --tokenizer-root; no model/pack changes"
        )
    return next(iter(valid.values()))


def run(argv, cwd, timeout=90, payload=None):
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=ENV,
        input=None if payload is None else json.dumps(payload).encode(),
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def inventory(project, roots):
    result = {}
    for root in roots:
        path = project / root
        for item in [path] if path.is_file() else path.rglob("*"):
            ordinary(item)
            if item.is_file() and not any(
                p in item.parts for p in ("__pycache__", ".pytest_cache", ".ruff_cache")
            ):
                result[item.relative_to(project).as_posix()] = sha(item)
    return result


def guidance(bundle, project, out):
    directory = project / ".agent/strata-setup"
    document = directory / "README.md"
    content = (
        "# Local Strata setup\n\nPrimary reads the verified bundle guide at "
        + str(bundle / "AGENTS.strata.md")
        + ". Preserve project rules and independent final acceptance.\n"
        "Setup journals are immutable per-attempt directories here. Use only a READY result's config.json; "
        "config.pending.json is not qualified. If WAITING_FOR_STRATA, ask the user to start iq3_s "
        "and repeat the same setup command with the saved checks.json. Do not start/unload models, "
        "replace hashes blindly, use a stale READY config after drift, or reset task budgets.\n"
    )
    if document.exists() and document.read_text(encoding="utf-8") != content:
        raise SetupError(
            "Existing setup guide differs; Primary reviews upgrade, no overwrite"
        )
    if not document.exists():
        with document.open("x", encoding="utf-8") as stream:
            stream.write(content)
    agents = ordinary(project / "AGENTS.md")
    raw = agents.read_bytes() if agents.exists() else b""
    marker = b"<!-- strata-supervised-setup -->"
    if marker in raw:
        return
    with (out / "AGENTS.preimage.bin").open("xb") as stream:
        stream.write(raw)
    block = (
        b"\n\n<!-- strata-supervised-setup -->\nFor local Strata tasks, read "
        b"[the project setup guide](.agent/strata-setup/README.md) and its verified bundle guidance. "
        b"Existing project/user rules and Primary final acceptance remain authoritative.\n"
        b"<!-- /strata-supervised-setup -->\n"
    )
    # Deliberately append; retain all existing bytes and archive the exact preimage.
    with agents.open("ab") as stream:
        stream.write(block)
    save(
        out / "guidance.json",
        {
            "agents_before_sha256": digest(raw),
            "agents_after_sha256": sha(agents),
            "existing_bytes_preserved": True,
        },
    )


def body(text, tools=None, messages=None):
    return {
        "model": "iq3_s",
        "max_tokens": 12288,
        "thinking": {"type": "enabled", "budget_tokens": 4096},
        "output_config": {"effort": "medium"},
        "messages": messages or [{"role": "user", "content": text}],
        "tools": tools or [],
    }


def calibrate(bundle, config, resident, out):
    identity = resident.get("id", "")
    if (
        not re.fullmatch(r"[a-f0-9-]{36}", identity)
        or type(resident.get("port")) is not int
        or not 1 <= resident["port"] <= 65535
    ):
        raise SetupError("Resident instance identity/port missing")
    native = read(Path.home() / ".strata/data/native-instances" / (identity + ".json"))
    tokenizer = Path(native["tokenizer"])
    profile = config["strata_token_counter"]
    if (
        tokenizer.resolve() != Path(profile["tokenizer_root"]).resolve()
        or native.get("effort_end", False) is not False
    ):
        raise SetupError("Uncalibrated resident tokenizer/effort placement")
    key = native.get("api_key")
    if isinstance(key, list):
        key = key[0]
    if not isinstance(key, str) or not key:
        raise SetupError(
            "Resident backend credential unavailable; no authentication changes"
        )
    # Credential only goes to this local resident; never return or archive it.
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key.split(",")[0].strip(),
    }
    tools = [
        {
            "name": "kit_read",
            "description": "Read approved text",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }
    ]
    fixtures = [
        body("Implement a bounded local function; preserve caller behavior.", tools),
        body("Review a diff independently; report concrete defects.", tools),
        body("Investigate approved source without claiming execution.", tools),
        body(
            "unused",
            tools,
            [
                {"role": "user", "content": "Read source"},
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "r1",
                            "name": "kit_read",
                            "input": {"path": "source.py"},
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "r1",
                            "content": "def f(): return 1",
                        }
                    ],
                },
            ],
        ),
        body(
            "中文 é 😀 \\n\n<think></think><|im_start|><|im_end|><|endoftext|>", tools
        ),
        body("def f(x):\n    return x+1\n" * 200, tools),
    ]
    helper = Path(bundle) / "runtime/.local-agents/strata/general_token_counter.py"
    code, raw, _ = run(
        [profile["python"], "-B", str(helper)],
        out,
        60,
        {"profile": profile, "bodies": fixtures},
    )
    if code:
        raise SetupError("Local counter incompatible; no READY config written")
    local = json.loads(raw)["input_tokens"]
    rows = []
    for fixture, count in zip(fixtures, local, strict=True):
        request = urllib.request.Request(
            f"http://127.0.0.1:{resident['port']}/v1/messages/count_tokens",
            json.dumps(fixture).encode(),
            headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            remote = json.load(response)["input_tokens"]
        rows.append({"local": count, "server": remote, "match": count == remote})
    if not all(row["match"] for row in rows):
        raise SetupError("Counter/server mismatch; no READY config written")
    bad = copy.deepcopy(profile)
    bad["files"][next(iter(bad["files"]))] = "0" * 64
    code, _, _ = run(
        [profile["python"], "-B", str(helper)],
        out,
        60,
        {"profile": bad, "bodies": fixtures[:1]},
    )
    if code == 0:
        raise SetupError("Drift negative control failed")
    if any(sha(path) != value for path, value in profile["files"].items()):
        raise SetupError("Counter changed during calibration")
    result = {
        "status": "PASS",
        "rows": rows,
        "drift_negative": "rejected",
        "generation_requests": 0,
    }
    save(out / "calibration.json", result)
    return result


def configure(
    bundle,
    project,
    python,
    checks,
    strata_home=None,
    base_url="http://127.0.0.1:47831/v1",
    profile="coding",
    tokenizer_root=None,
):
    global LAST_ATTEMPT
    LAST_ATTEMPT = None
    bundle, project = Path(bundle), ordinary(project).resolve(strict=True)
    parts = urllib.parse.urlsplit(base_url)
    if (
        parts.scheme != "http"
        or parts.hostname not in {"127.0.0.1", "localhost"}
        or parts.path != "/v1"
        or parts.query
        or parts.fragment
        or parts.username
    ):
        raise SetupError("Only explicit local Strata /v1 endpoints supported")
    checked = check_spec(checks, project, python)
    installation = install(bundle, project)
    home = discover(strata_home)
    out = (
        project
        / ".agent/strata-setup"
        / (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    )
    out.mkdir(parents=True)
    LAST_ATTEMPT = out
    guidance(bundle, project, out)
    config = read(
        bundle
        / "examples"
        / (
            "config.coding.json"
            if profile == "coding"
            else "config.investigation-followup.json"
        )
    )
    config.update(
        strata_node_path=str(home / "node/node.exe"),
        strata_harness_root=str(home / "harness"),
        strata_base_url=base_url,
    )
    control = home / "control"
    tokenizer = discover_tokenizer(tokenizer_root)
    counter_python = control / "python/python.exe"
    pins = [
        control / "serve/server.py",
        control / "serve/frontend.py",
        control / "tools/strata_tokenizer.py",
        counter_python,
        *[
            tokenizer / n
            for n in (
                "chat_template.jinja",
                "merges.txt",
                "tokenizer.json",
                "token_type.json",
                "vocab.json",
            )
        ],
    ]
    config["strata_token_counter"] = {
        "python": str(counter_python),
        "source_root": str(control),
        "tokenizer_root": str(tokenizer),
        "effort_end": False,
        "files": {str(path): sha(path) for path in pins},
    }
    config["check_input_roots"] = checked["input_roots"]
    config["required_check_ids"] = [c["id"] for c in checked["commands"]]
    config["validation_profiles"] = {
        "project-strict": {
            "python": str(Path(python).resolve()),
            "pytest_argv": [
                "-B",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=.agent/focused-temp",
            ],
            "compile": True,
            "commands": checked["commands"],
        }
    }
    save(out / "config.pending.json", config)
    save(out / "checks.json", checked)
    save(out / "installation.json", installation)
    code, raw, _ = run(
        [
            python,
            "-B",
            str(project / ".local-agents/strata-worker.py"),
            "doctor",
            "--config",
            str(out / "config.pending.json"),
        ],
        project,
    )
    try:
        doctor = json.loads(raw)
    except json.JSONDecodeError:
        doctor = {}
    resident = doctor.get("resident") or {}
    if code or doctor.get("status") != "ready" or resident.get("status") != "ready":
        result = {
            "status": "WAITING_FOR_STRATA",
            "directory": str(out),
            "installed": True,
            "ready": False,
            "next": "Start Strata with iq3_s, then repeat setup; no model is started by this tool",
        }
        save(out / "result.json", result)
        return result
    if (
        resident.get("model") != "iq3_s"
        or resident.get("parallel") != 1
        or resident.get("context", 0) < 65536
    ):
        raise SetupError("Single iq3_s/parallel1/context>=65536 required")
    calibrate(bundle, config, resident, out)
    baseline = []
    inputs_before = inventory(project, checked["input_roots"])
    for command in checked["commands"]:
        code, raw, err = run(
            [arg.replace("{python}", python) for arg in command["argv"]], project, 240
        )
        save(
            out / (command["id"] + ".json"),
            {
                "exit_code": code,
                "stdout": raw.decode("utf-8", "replace"),
                "stderr": err.decode("utf-8", "replace"),
            },
        )
        baseline.append({"id": command["id"], "exit_code": code})
    if inventory(project, checked["input_roots"]) != inputs_before or any(
        row["exit_code"] for row in baseline
    ):
        raise SetupError("Project baseline failed or changed inputs; no READY config")
    if any(
        sha(path) != expected
        for path, expected in config["strata_token_counter"]["files"].items()
    ):
        raise SetupError("Counter changed after baseline; no READY config")
    save(out / "config.json", config)
    result = {
        "status": "READY",
        "ready": True,
        "directory": str(out),
        "config": str(out / "config.json"),
        "profile": profile,
        "checks": baseline,
        "model": "iq3_s",
        "parallel": 1,
        "context": resident["context"],
        "client_context": 65536,
        "acceptance": False,
        "next": "Primary reads bundled AGENTS.strata.md, prepares a scoped task contract and copies this config; run through installed strata-task.py; independently accept results",
    }
    save(out / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    acquire = sub.add_parser("fetch")
    for name in ("repository", "tag", "asset", "sha256", "output"):
        acquire.add_argument("--" + name, required=True)
    extract = sub.add_parser("unpack")
    for name in ("archive", "sha256", "output"):
        extract.add_argument("--" + name, required=True)
    setup = sub.add_parser("project")
    for name in ("bundle", "project", "python", "checks"):
        setup.add_argument("--" + name, required=True)
    setup.add_argument("--strata-home")
    setup.add_argument("--tokenizer-root")
    setup.add_argument("--base-url", default="http://127.0.0.1:47831/v1")
    setup.add_argument(
        "--profile", choices=["coding", "investigation"], default="coding"
    )
    args = parser.parse_args()
    try:
        if args.command == "fetch":
            result = fetch_release(
                args.repository, args.tag, args.asset, args.sha256, args.output
            )
        elif args.command == "unpack":
            result = unpack(args.archive, args.sha256, args.output)
        else:
            result = configure(
                args.bundle,
                args.project,
                args.python,
                read(args.checks),
                args.strata_home,
                args.base_url,
                args.profile,
                args.tokenizer_root,
            )
    except (SetupError, OSError, ValueError, subprocess.SubprocessError) as error:
        # Never include arbitrary exception repr: a backend error may contain secrets.
        result = {
            "status": "NEEDS_PRIMARY_ATTENTION",
            "ready": False,
            "error_type": type(error).__name__,
            "reason": str(error)
            if isinstance(error, SetupError)
            else "Operation failed; inputs and prior records retained",
        }
        if LAST_ATTEMPT is not None and not (LAST_ATTEMPT / "result.json").exists():
            save(LAST_ATTEMPT / "result.json", result)
        print(json.dumps(result))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
