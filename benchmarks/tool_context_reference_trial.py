"""Fresh qualification with exact read-only dependency evidence, not an oracle patch."""

import argparse
import shutil

import tool_context_qualification as qualification
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes

BASE = WORK / "tool-context-reference-1"
SNAPSHOT = WORK / "tool-context-reference-runtime-10"
REFERENCE = KIT / "benchmarks/fixtures/tool-library-reference-v1"
ARMS = ("fresh-1", "fresh-2")
GUIDANCE = (
    "The existing implementation already delegates plain synchronous handlers to "
    "asyncio.to_thread. A frozen copy of this installed dependency helper is readable "
    "at reference/asyncio_threads.py. Inspect it if its thread or caller ContextVar "
    "semantics are unclear. This is dependency evidence, not a solution or required "
    "implementation shape; do not import or replace it. Preserve existing semantics "
    "while extending returned-awaitable handling. No task implementation is provided."
)


def configure():
    qualification.BASE = BASE
    qualification.configure()
    qualification.scope.ARMS = ARMS
    qualification.scope.SNAPSHOT = SNAPSHOT
    qualification.scope.configure()


def register():
    if not SNAPSHOT.exists():
        freeze(SNAPSHOT.name)
    write(BASE / "preflight.json", read(WORK / "tool-context-scope-1/preflight.json"))
    write(
        BASE / "registration.json",
        {
            "arms": list(ARMS),
            "weekly_ceiling": 23,
            "reason": "Actual inherited Coder repair succeeded after source-backed dependency API evidence; test transfer to clean frozen original source without prior repair diff",
            "risk": "Same high feature/unit/integration atomic deadline/cancellation/public compatibility invariant; no decomposition below risk floor",
            "constants": "Original v10 source, all eighteen protected tests, same models/context/sampling/budgets, single source writable; validation and independent Reviewer/Primary gates unchanged",
            "change": "One exact small read-only dependency helper and license; generic API-navigation advice, no patch, preferred code shape or failure-specific recipe",
            "explorer": "At most one focused initial investigation of existing helper guarantees/callsite; later repetitions reuse verified facts, no extra Explorer success credit",
            "credit": "Fresh API-evidence-guided qualification, not causal comparison with old cohorts or cloud savings. All historical failures remain in their denominators",
            "reference_files": read(REFERENCE / "provenance.json")["files"],
            "driver_sha256": digest(KIT / "benchmarks/tool_context_reference_trial.py"),
            "adapter_sha256": {
                name: digest(KIT / "benchmarks" / name)
                for name in qualification.scope.ADAPTERS
            },
        },
    )


def prepare(arm):
    configure()
    qualification.prepare(arm)
    root = BASE / arm
    verify_hashes(REFERENCE, read(BASE / "registration.json")["reference_files"])
    shutil.copytree(REFERENCE, root / "reference")
    packet = read(root / ".agent/context-packet.json")
    for name in ("asyncio_threads.py", "PSF-LICENSE.txt"):
        path = "reference/" + name
        packet["scope"]["read"].append(path)
        packet["scope"]["readonly"].append(path)
    packet["implementation_guidance"].append(GUIDANCE)
    load_worker(SNAPSHOT).validate_packet(packet)
    write(root / ".agent/reference-packet.json", packet)
    write(
        root / ".agent/reference-config.json", read(root / ".agent/context-config.json")
    )
    write(
        root / ".agent/reference-inputs.json",
        {
            "source_sha256": digest(root / qualification.scope.TARGET),
            "files": {
                path: digest(root / path)
                for path in (
                    ".agent/reference-packet.json",
                    ".agent/reference-config.json",
                )
            },
        },
    )


def run(arm):
    configure()
    root = BASE / arm
    registration = read(BASE / "registration.json")
    verify_hashes(
        KIT / "benchmarks",
        {
            "tool_context_reference_trial.py": registration["driver_sha256"],
            **registration["adapter_sha256"],
        },
    )
    verify_hashes(root / "reference", registration["reference_files"])
    inputs = read(root / ".agent/reference-inputs.json")
    verify_hashes(
        root, {qualification.scope.TARGET: inputs["source_sha256"], **inputs["files"]}
    )
    # The common unit driver reads these convenience paths; originals are retained.
    shutil.copyfile(
        root / ".agent/reference-packet.json", root / ".agent/compat-packet.json"
    )
    shutil.copyfile(
        root / ".agent/reference-config.json", root / ".agent/compat-config.json"
    )
    qualification.scope.native.run(arm)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--arm", choices=ARMS, default=ARMS[0])
    args = parser.parse_args()
    {"register": lambda _: register(), "prepare": prepare, "run": run}[args.action](
        args.arm
    )
