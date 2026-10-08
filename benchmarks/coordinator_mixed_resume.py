"""Resume two untouched queued chains under an explicitly registered loader."""

import argparse
import copy
import json
import shutil
from pathlib import Path

import coordinator_label_evidence as evidence
import coordinator_label_pilot as pilot
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-mixed-resume-1"
SOURCE = WORK / "coordinator-label-pilot-4"
SNAPSHOT = WORK / "coordinator-loader-baseline-1"


def configure():
    pilot.BASE, pilot.SNAPSHOT = BASE, SNAPSHOT
    return pilot.configure()


def prepare():
    BASE.mkdir(exist_ok=False)
    manifest = copy.deepcopy(read(SOURCE / "manifest.json"))
    manifest["cells"] = [c for c in manifest["cells"] if c["id"].endswith("r2")]
    manifest["runtime"] = str(SNAPSHOT)
    manifest["drivers"][str(Path(__file__).resolve())] = digest(Path(__file__))
    origins = []
    for cell in manifest["cells"]:
        old = Path(cell["root"])
        if list((old / ".agent").glob("*-coder.json")):
            raise ValueError("queued cell already has Coder execution")
        pilot.matrix.SCOPE.FA.LAYER.verify_hashes(old, cell["hashes"])
        if not read(old / ".agent/explorer-primary-adjudication.json")["success"]:
            raise ValueError("missing original Explorer acceptance")
        root = BASE / "runs" / cell["id"]
        shutil.copytree(old, root)
        config = read(root / ".agent/config.json")
        config.update(
            model_load_backend="cli",
            model_load_cli_path="C:/Users/Lin/.lmstudio/bin/lms.exe",
        )
        # Only this new workspace's config changes. The source cohort remains immutable.
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        cell["root"] = str(root)
        cell["hashes"][".agent/config.json"] = digest(root / ".agent/config.json")
        origins.append(
            {
                "cell": cell["id"],
                "source_root": str(old),
                "explorer_report_sha256": digest(old / ".agent/explorer.json"),
                "new_explorer_credit": False,
            }
        )
    write(BASE / "manifest.json", manifest)
    for name in ("corpus.json", "primary-oracles.json", "preflight-1.json"):
        shutil.copyfile(SOURCE / name, BASE / name)
    write(
        BASE / "registration.json",
        {
            "order": ["control-r2", "coordinator-r2"],
            "origins": origins,
            "runtime": str(SNAPSHOT),
            "weekly_used_ceiling": 10,
            "qualification_risk": "high",
            "functional_risk": "medium",
            "classification": "Continuation of untouched queued units; unchanged original Explorer evidence, not fresh Explorer calls or a single-runtime four-chain causal comparison",
            "hard_contract_or_model_changes": False,
            "config_change": "explicit CLI loader only, same models/budgets",
        },
    )
    print("Registered untouched queued chains", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action", choices=("prepare", "run", "check", "record", "integrate")
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--unit", default="normalize-unit")
    parser.add_argument("--summary")
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        prepare()
    elif args.action == "run":
        pilot.run(args.identity, args.unit)
    elif args.action == "check":
        evidence.unit_check(args.identity, args.unit)
    elif args.action == "integrate":
        evidence.integrate(args.identity)
    else:
        import qualification_controls as controls

        controls.record(args.identity, args.unit, "accept", args.summary)
