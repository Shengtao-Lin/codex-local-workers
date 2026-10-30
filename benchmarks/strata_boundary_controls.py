"""Prove the new protected regression rejects both retained wrong drafts."""

import shutil
from pathlib import Path

import strata_boundary_trial as B


def run():
    public = "tests/unit/test_local_worker_message.py"
    target = "src/evaluation_harness/adapters/common.py"
    assert (B.BATCH / "registration.json").exists()
    for cell in ("message-1", "message-2"):
        root = B.BATCH / "negative-controls" / cell / "isolated"
        B.J.copy_project(B.BATCH / "templates/message", root)
        old = B.P.I.BASE / "strata-project-20261023-2/cells" / cell / "isolated"
        shutil.copyfile(old / target, root / target)
        result = B.J.T.run(
            [
                B.S.PYTHON,
                "-B",
                "-m",
                "pytest",
                public,
                "-k",
                "falsey_int_subclass",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
            root,
        )
        B.S.save(
            root.parent / "result.json",
            {
                "source": str(old / target),
                "source_sha256": B.S.sha(old / target),
                "protected_test_sha256": B.S.sha(root / public),
                "script_sha256": B.S.sha(Path(__file__)),
                "command": result,
                "model_calls": 0,
            },
        )
        assert result["exit_code"] == 1 and "2 failed" in result["stdout"], result
    print(
        "Both retained wrong drafts rejected by two protected boundary cases; zero model calls"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--batch",
        choices=["strata-boundary-20261023-2", "strata-boundary-20261023-3"],
        required=True,
    )
    args = parser.parse_args()
    B.BATCH = B.P.I.BASE / args.batch
    run()
