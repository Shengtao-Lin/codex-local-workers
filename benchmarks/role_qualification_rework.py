"""Primary-authored boundary clarification; explicitly guided, never restores score."""

import json

from capability_fit import WORK, write


def prepare():
    root = WORK / "roleq-six-1/runs/v1/roleq1/filename-suffix-round-1"
    packet = json.loads(
        (root / ".agent/qual-unit-reference.json").read_text(encoding="utf-8")
    )
    packet.update(
        parent_run_id=packet["run_id"],
        run_id=packet["run_id"].replace("-a1", "-a3"),
        attempt=2,
        packet_revision=2,
        plan_revision=2,
    )
    packet["review_feedback"] = [
        {
            "finding_id": "dot-prefix-overgeneralization",
            "contract_id": "qual-unit",
            "text": "Primary checked current source and protected failure: the early empty return classifies every dot-prefixed name as no suffix. Only a dot-prefixed name with no OTHER dot is suffixless. A leading dot is not itself grounds for rejection when a later dot separates a nonempty suffix. Preserve all normal and other boundary assertions. This is a guided clarification, not unseen qualification.",
        }
    ]
    packet["acceptance_scenarios"] = [
        {
            "id": "normal",
            "text": "suffix('report.TAR.GZ') == 'gz'; suffix('a.b-c') == 'b-c'",
            "observables": {"normal": True},
        },
        {
            "id": "boundary",
            "text": "suffix('.profile') == ''; suffix('.config.JSON') == 'json'; suffix('README') == ''; suffix('file.') == ''",
            "observables": {"distinguishes_leading_dot_from_last_separator": True},
        },
    ]
    allowed = {
        "schema_version",
        "task_id",
        "unit_id",
        "run_id",
        "attempt",
        "plan_revision",
        "packet_revision",
        "parent_run_id",
        "review_feedback",
    }
    packet = {key: value for key, value in packet.items() if key in allowed}
    packet["preserve_contract"] = True
    target = root / ".agent/guided-a3.json"
    write(target, packet)
    write(
        root / ".agent/guided-a3-provenance.json",
        {
            "classification": "guided recovery, excluded from initial autonomous score",
            "runtime_changed": False,
            "protected_tests_changed": False,
            "scope_changed": False,
        },
    )
    print(target)


if __name__ == "__main__":
    prepare()
