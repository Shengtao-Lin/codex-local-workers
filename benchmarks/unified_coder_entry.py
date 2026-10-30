"""Truthfully configured receiver for the mechanically unified candidate."""

import coder_output_channel as OUTPUT
import coder_prevalidation_format as PREPARE
import coder_static_span as SPAN
import coder_unified_preparation as UNIFIED
import scheduled_coder_entry as ENTRY


def configure(worker, config):
    enabled = config.get("experimental_unified_preparation")
    if (
        type(enabled) is not bool
        or config.get("experimental_static_span_repair") is not True
    ):
        raise worker.WorkerError(
            "Explicit unified boolean and static-span mode required"
        )
    if (
        config.get("experimental_prevalidation_format") is not True
        or config.get("experimental_output_channel") != "schema"
    ):
        raise worker.WorkerError("Qualified schema and preparation required")
    original = OUTPUT.make_runtime

    def factory(worker, host, arm):
        base = PREPARE.make_runtime(worker, original(worker, host, arm))
        return (
            UNIFIED.make_runtime(worker, host, base)
            if enabled
            else SPAN.make_runtime(worker, host, base)
        )

    OUTPUT.make_runtime = factory
    try:
        OUTPUT.install(worker, "schema")
    finally:
        OUTPUT.make_runtime = original


if __name__ == "__main__":
    ENTRY.configure = configure
    raise SystemExit(ENTRY.main())
