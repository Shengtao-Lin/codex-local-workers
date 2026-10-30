"""Select a versioned wire profile without changing execution authority."""

from types import SimpleNamespace


def selected(config):
    value = config.get("bounded_compatibility_profile")
    if value not in (None, "flat-v1"):
        raise ValueError("bounded_compatibility_profile must be absent or flat-v1")
    return value == "flat-v1"


def proposal_rules(config, base):
    if not selected(config):
        return base
    from . import tagged_wire

    def render(facts):
        first, separator, rest = base.render(facts).partition("\n")
        first = first.replace(
            "Return an updated replacement or a concrete blocked_reason.",
            "Use the output object specified in the system message.",
        )
        return first + separator + rest

    selected_rules = SimpleNamespace(
        IMPORT_CEILING=base.IMPORT_CEILING,
        PROMPT=tagged_wire.PROMPT,
        SCHEMA=tagged_wire.SCHEMA,
        decode=tagged_wire.decode,
        guard=base.guard,
        materialize=base.materialize,
        shape=base.shape,
        render=render,
    )
    # The profile changes wire representation, not the base evidence provider.
    # Keep its existing source/hash/scope checks rather than reconstructing facts.
    if hasattr(base, "diagnostics"):
        selected_rules.diagnostics = base.diagnostics
    return selected_rules


def reviewer_runtime(config, module, base):
    if not selected(config):
        return base
    from .reviewer_direct_report import install

    return install(module, base, enabled=True)
