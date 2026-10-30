"""Preserve the original producer bytes when correcting pre-live import style."""

import copy
from pathlib import Path

import reviewer_observation_probe as P


def main():
    original = P.BATCH / "observation-seal.json"
    seal = copy.deepcopy(P.B.read(original))
    old_path = str(P.B.KIT / "benchmarks/harness_observation_seal.py")
    digest = seal["pins"].pop(old_path)
    snapshot = P.BATCH / "producer-v1.py"
    assert P.B.sha(snapshot) == digest
    seal["pins"][str(snapshot)] = digest
    seal["pins"][str(original)] = P.B.sha(original)
    seal["producer_amendment"] = {
        "reason": "Before live, archive the exact producer bytes; root producer import ordering was corrected. Observations, requests and source manifests unchanged.",
        "original_seal": str(original),
        "legacy_producer_snapshot": str(snapshot),
        "corrected_producer_sha256": P.B.sha(Path(old_path)),
        "new_model_calls": 0,
    }
    P.B.save(P.BATCH / "observation-seal-v2.json", seal)


if __name__ == "__main__":
    main()
