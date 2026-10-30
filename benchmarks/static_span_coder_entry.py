"""Installed formal candidate entry, using frozen schema and scheduling layers."""

import coder_output_channel as OUTPUT
import coder_prevalidation_format as PREPARE
import coder_static_span as SPAN
import scheduled_coder_entry as ENTRY


def configure(worker, config):
    enabled = config.get("experimental_static_span_repair")
    if (
        type(enabled) is not bool
        or config.get("experimental_prevalidation_format") is not True
    ):
        raise worker.WorkerError(
            "Explicit span boolean and qualified scheduling required"
        )
    if config.get("experimental_output_channel") != "schema":
        raise worker.WorkerError("Static span requires schema transport")
    original = OUTPUT.make_runtime

    def factory(worker, host, arm):
        base = PREPARE.make_runtime(worker, original(worker, host, arm))
        return SPAN.make_runtime(worker, host, base) if enabled else base

    OUTPUT.make_runtime = factory
    try:
        OUTPUT.install(worker, "schema")
    finally:
        OUTPUT.make_runtime = original


if __name__ == "__main__":
    ENTRY.configure = configure
    raise SystemExit(ENTRY.main())
