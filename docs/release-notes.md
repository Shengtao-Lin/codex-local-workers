# Release notes

## v2.1: supervised local coordination

This release adds an optional Coordinator to the existing Explorer, Coder and
Reviewer workflow. It proposes execution steps for a Primary-approved feature;
the Primary still owns contracts, permissions, risk and final acceptance.

- Supervised localization connects verified Explorer file/line evidence to a
  bounded Coder packet. Runtime checks reject mismatched or stale handoffs.
- Successful Coder validation automatically starts an independent Reviewer.
  Reviewer can read and search, run only registered validation commands, and
  report defects; it cannot edit or accept a feature.
- Repair feedback identifies failing source locations and stops repetitive
  no-progress actions rather than treating retries as success.
- Model residency is serialized to reduce GPU-memory pressure. Model IDs and
  context settings are configurable; role compatibility must be qualified.
- Coordinator reasoning strength is an optional prompt setting. The example
  uses `low`; it never weakens approval or validation gates.

The qualified Coordinator scope is **Primary-supervised localization**, not
autonomous semantic planning or unattended feature completion. Explorer
citations are evidence of localization, not proof of complete understanding.
The kit assumes a trusted local repository; validation is not OS-sandboxed.

Release verification: 466 tests and 28 subtests passed, including installation,
scope enforcement, handoff and coordination boundaries. Real local paired
execution also passed Coder validation, independent Reviewer and Primary review.
See [model configuration](models.md) and [cost and latency](cost-and-latency.md)
for replacement criteria and measurement limits.

Engineering plans and experiment history are maintained on the
[`codex/v2.1-dev` branch](https://github.com/Shengtao-Lin/codex-local-workers/tree/codex/v2.1-dev).
