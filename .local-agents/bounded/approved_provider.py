"""No historical sealed-file provider in installed execution."""

PROTOCOL = "lossless-typed-observation-input-v1"


def facts_unavailable(runtime, error):
    raise error("Explicit canonical capture policy required")


def restore_unavailable(runtime, profiles, error):
    raise error("Explicit canonical capture policy required")


facts = facts_unavailable
restore = restore_unavailable
