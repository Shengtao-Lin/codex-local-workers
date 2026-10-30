"""Seal offline factual observations; never produce a semantic acceptance decision."""

import xml.etree.ElementTree as ET
from pathlib import Path

import reviewer_observation_probe as P


def main():
    B = P.B
    tree = ET.parse(P.BATCH / "offline-controls-v2.xml")
    assert len(tree.findall(".//testcase")) == 22
    assert not any(tree.findall(".//" + key) for key in ("failure", "error", "skipped"))
    sources, pins = [], {}
    for name in sorted(P.FIXTURES):
        row = P.fixture(name)
        cell = P.BATCH / name
        observation = B.read(cell / "observation.json")
        assert (
            observation["execution_completed"]
            and observation["semantic_verdict"] is None
        )
        assert observation["source"]["sha256"] == row["files"][P.TARGET]
        sources.append(
            {
                "source_manifest": {
                    p: sha for p, sha in row["files"].items() if p.startswith("src/")
                },
                "observation": str(cell / "observation.json"),
                "request": str(cell / "request.json"),
            }
        )
        for path in (
            cell / "observation.json",
            cell / "request.json",
            cell / "execution.json",
        ):
            pins[str(path)] = B.sha(path)
    for path in (
        Path(__file__),
        Path(P.__file__),
        B.KIT / "tests/test_reviewer_observation_probe.py",
        P.BATCH / "registration.json",
        P.BATCH / "offline-controls.xml",
        P.BATCH / "offline-controls-v2.xml",
        P.H.BATCH / "decision.json",
    ):
        pins[str(path)] = B.sha(path)
    B.save(
        P.BATCH / "observation-seal.json",
        {
            "sources": sources,
            "pins": pins,
            "projection": ["call_id", "name", "arguments", "result", "status"],
            "runtime_scope": "Same evaluation session and fixed project Python environment; no dependency installation or machine-setting changes. Data are cached observations, not newly executed tests or a proof for all inputs.",
        },
    )
    B.save(
        P.BATCH / "decision.json",
        {
            "offline_observation_proof": "PASS",
            "negative_controls": 22,
            "source_versions": 2,
            "observations": 12,
            "model_calls": 0,
            "r4_passed": False,
            "reviewer_live_started": False,
            "model_proposed_execution_enabled": False,
            "fixed_primary_fact_delivery_next": True,
            "production_installed": False,
            "first_test_failure": "Old basetemp was inside the permitted design batch, so the supposed outside-archive negative did not escape; test corrected to a real outside path. First XML retained.",
        },
    )
    print({"offline_observation_proof": "PASS", "controls": 22, "model_calls": 0})


if __name__ == "__main__":
    main()
