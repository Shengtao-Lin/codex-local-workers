"""Correct experiment materialization; same frozen model/contract candidate."""

import argparse
import time
from pathlib import Path

import complete_project_snapshot as SNAP
import project_identity_chain_host_routed as H

J, D, S = H.J, H.D, H.S
BATCH = D.I.BASE / "project-identity-chain-20261022-4"
OLD_REFRESH = J.refresh


def refresh(root, config):
    overrides = {}
    if root.parent.name == "append":
        origin = (
            BATCH / "reference"
            if "offline" in root.parts
            else Path(S.read(BATCH / "units/encode/binding.json")["root"])
        )
        overrides[J.PRODUCER] = S.sha(origin / J.PRODUCER)
    manifest = SNAP.complete(BATCH / "template", root, accepted_overrides=overrides)
    S.save(root.parent / "project-inputs.json", manifest)
    OLD_REFRESH(root, config)


def save_with_parity(original):
    def save(path, value):
        path = Path(path)
        if path.name == "binding.json" and path.parent.name in {"encode", "append"}:
            root = Path(value["root"])
            project = S.read(root.parent / "project-inputs.json")
            writable = set(value["packet"]["scope"]["modify"])
            value["protected"].update(
                {p: h for p, h in project.items() if p not in writable}
            )
        elif path == BATCH / "registration.json":
            # Full installed checks, not just original template/reference or focused replay.
            full = {}
            for topic in D.SPECS:
                root = BATCH / "offline" / topic / "isolated"
                test = "tests/test_encode.py" if topic == "encode" else "tests"
                private = (
                    BATCH / "private/test_private_encode.py"
                    if topic == "encode"
                    else BATCH / "private"
                )
                argv = [S.PYTHON, "-B", "-m", "pytest", "-q", test, private]
                full[topic] = D.T.run(argv, root, timeout=120)
            original(BATCH / "installed-full-controls.json", full)
            assert all(c["exit_code"] == 0 for c in full.values()), full
            value["fixture_fix"] = (
                "Copy/check every frozen project input, including alembic; exact accepted producer override only. Full installed offline tests before live. Entire project non-owned manifest protected before/after each unit. No new model privilege, behavior contract or budget."
            )
            value["prior"] += (
                "; -3 producer correct but full project infrastructure failure due omitted alembic; downstream NOT_RUN, zero final accepts preserved"
            )
            value["pins"].update(
                {str(p): S.sha(p) for p in (Path(__file__), Path(SNAP.__file__))}
            )
            value["pins"].update(
                {
                    str(BATCH / "template" / p): h
                    for p, h in SNAP.inventory(BATCH / "template").items()
                }
            )
        original(path, value)

    return save


def configure():
    H.BATCH = J.BATCH = BATCH
    J.configure()
    D.I.refresh_material = refresh
    S.save = save_with_parity(S.save)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=["prepare", "plan", "approve", "execute", "accept", "close"]
    )
    parser.add_argument("--topic", choices=["encode", "append"])
    parser.add_argument("--weekly-used", type=int, required=True)
    parser.add_argument("--reason")
    args = parser.parse_args()
    configure()
    if args.mode == "prepare":
        H.prepare(args.weekly_used)
    elif args.mode == "plan":
        H.plan(args.weekly_used)
    elif args.mode == "execute":
        D.execute(args.topic, args.weekly_used, time.time())
    else:
        J.fresh(args.weekly_used, time.time())
        if args.mode == "approve":
            D.approve(args.reason)
        elif args.mode == "accept":
            D.accept(args.topic, args.reason)
        else:
            H.close(args.weekly_used, args.reason)
