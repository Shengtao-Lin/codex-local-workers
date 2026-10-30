"""Verbatim approved dependency evidence on the frozen bounded-source candidate."""

import json

import bounded_evidence_support as S
import supervised_bounded_trial as B
import supervised_feedback_trial as F
from stdlib_reference import collect

BATCH = B.BATCH.with_name("supervised-reference-20261019-1")
ORDER = F.ORDER
command = B.command


def configure(root, packet, policy, config):
    relative = "context/stdlib-reference.json"
    reference = collect((root / "src/product/code.py").read_text(encoding="utf-8"))
    S.save(root / relative, reference)
    packet["scope"]["read"].append(relative)
    packet["scope"]["readonly"].append(relative)
    policy["source_paths"].append(relative)
    policy["readonly_hashes"][relative] = S.sha(root / relative)
    config["coder_single_function"]["dependencies"] += (
        "\n\nVerbatim local API reference (documentation, not instructions):\n"
        + json.dumps(reference, ensure_ascii=False, indent=2)
    )
    return [relative]


if __name__ == "__main__":
    if not (B.BATCH / "decision.json").exists():
        raise ValueError("Finish the preceding fixed batch first")
    F.prepare(
        BATCH,
        command,
        F.BATCH / "candidate-preimages",
        "Bounded source candidate plus full local docstrings/signatures of statically referenced approved json/hashlib APIs. Additional dependency information, not equal-information comparison. All tasks exposed, no manual repair hint or reference solution.",
        configure_cell=configure,
        extra_pins=[__file__, S.KIT / "benchmarks/stdlib_reference.py"],
    )
