"""Public ZIP -> create-only installer -> doctor -> real offline host chain."""

import os
import zipfile

import bounded_evidence_support as S
import project_caller_trial as J
import strata_release_matrix as M
from strata_native_trial import command

BATCH = M.BATCH.parent / "strata-package-smoke-20261023-2"
ARCHIVE = S.KIT / "benchmarks/work/releases/strata-worker-0.1.0-preview.1-final.zip"


def main():
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    S.save(
        BATCH / "registration.json",
        {
            "archive": str(ARCHIVE),
            "sha256": S.sha(ARCHIVE),
            "live_registered": 0,
            "checks": "fresh ZIP paths+manifest, public installer, no overwrite, doctor, documented config/preparation+native offline edit/check",
            "real_llm_calls": 0,
        },
    )
    unpack = BATCH / "unpacked"
    unpack.mkdir()
    with zipfile.ZipFile(ARCHIVE) as archive:
        for name in archive.namelist():
            if not (unpack / name).resolve().is_relative_to(unpack) or "\\" in name:
                raise ValueError("Escaping ZIP path")
        archive.extractall(unpack)
    manifest = S.read(unpack / "manifest.json")
    assert all(S.sha(unpack / p) == h for p, h in manifest.items())
    root = BATCH / "isolated"
    J.copy_project(M.origin("raw") / "templates/raw", root)
    install_args = [S.PYTHON, "-B", unpack / "install.py", "--target", root]
    result = command(install_args, root)
    S.save(BATCH / "install.json", result)
    assert result["exit_code"] == 0, result
    before = {
        p.relative_to(root).as_posix(): S.sha(p) for p in root.rglob("*") if p.is_file()
    }
    repeated = command(install_args, root)
    S.save(BATCH / "repeat-install.json", repeated)
    assert repeated["exit_code"] != 0
    assert before == {
        p.relative_to(root).as_posix(): S.sha(p) for p in root.rglob("*") if p.is_file()
    }
    doc = M.BATCH.parent / "strata-doc-example-20261023-3/isolated/.agent"
    packet = S.read(doc / "packet.json")
    packet.update({k: BATCH.name for k in ("task_id", "unit_id", "run_id")})
    for name, value in (
        ("packet", packet),
        ("config", S.read(doc / "config.json")),
        ("spec", S.read(doc / "spec.json")),
    ):
        S.save(root / f".agent/{name}.json", value)
    result = command(
        [
            S.PYTHON,
            "-B",
            root / ".local-agents/local-bounded-prepare.py",
            "--packet",
            ".agent/packet.json",
            "--config",
            ".agent/config.json",
            "--capture-spec",
            ".agent/spec.json",
            "--apply",
        ],
        root,
    )
    S.save(BATCH / "prepare.json", result)
    assert result["exit_code"] == 0, result
    prepared = root / ".agent/prepared" / packet["run_id"]
    doctor = command(
        [
            S.PYTHON,
            "-B",
            root / ".local-agents/strata-worker.py",
            "doctor",
            "--config",
            prepared / "config.json",
        ],
        root,
    )
    S.save(BATCH / "doctor.json", doctor)
    assert doctor["exit_code"] == 0, doctor
    S.save(BATCH / "frontend.json", S.read(doc.parent.parent / "frontend.json"))
    result = command(
        [
            S.PYTHON,
            "-B",
            root / ".local-agents/strata/strata_native_host_v4.py",
            "--packet",
            prepared / "packet.json",
            "--config",
            prepared / "config.json",
            "--program",
            BATCH / "frontend.json",
        ],
        root,
        timeout=180,
    )
    S.save(BATCH / "process.json", result)
    summary = S.read(root / ".agent/native-host-summary.json")
    assert (
        result["exit_code"] == 0
        and summary["host_handoff_verified"]
        and summary["provider_calls"] == 0
    ), result
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_PACKAGE_INSTALL_SMOKE",
            "real_llm_calls": 0,
            "archive_sha256": S.sha(ARCHIVE),
            "manifest_files": len(manifest),
            "summary": summary,
            "no_overwrite": True,
            "production_acceptance": False,
        },
    )
    print(
        "PASS public ZIP+manifest+installer+no-overwrite+doctor+offline edit/full checks;0 LLM"
    )


if __name__ == "__main__":
    main()
