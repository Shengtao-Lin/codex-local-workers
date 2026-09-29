# S6 candidate release checklist

This worktree is an unreleased candidate, not a tagged release. Historical S5
results do not establish current-version savings.

- [ ] Review and intentionally commit the existing worktree changes; do not
      discard user changes or sweep in `.agent` archives.
- [x] Run the full `.local-agents` test suite with pytest available and confirm
      the HTTP-to-pytest E2E is **not skipped** (117 worker tests, 2026-09-23).
- [x] Run Ruff lint/format on changed Python, `git diff --check`, and the example
      tests. On 2026-09-23, scoped Ruff checks passed for `.local-agents`,
      `scripts`, `tests`, and new evaluation modules; four example tests passed.
      The unchanged historical `benchmarks/s5_benchmark.py` still has two Ruff
      lint findings and is not part of the target installation.
- [x] From a clean disposable repository, preview and apply
      `scripts/install_local_agents.py`; verify that `AGENTS.md` and runtime
      files and standalone worker tests are present but `.agent`, `config.json`,
      and kit-only integration tests are not copied. Merge model IDs, Python path,
      validation profiles, and new config
      keys into the target's `config.json`; never overwrite it.
- [x] Verify packet anchors and required project formatter/linter checks in a
      focused live Coder run, followed by Local Reviewer and Primary review.
      The 2026-09-23 disposable run passed four independent tests and both
      configured Ruff checks; its cumulative diff was inspected.
- [x] Confirm no installer action implies `.agent` logs or
      user configuration are copied as part of the kit.
- [x] Report but preserve three legacy kit-only tests left in an existing
      target's `.local-agents/tests`; verify the installer never deletes them.
- [ ] Run the paired real-task pilot and publish its quality, latency, and
      measured-token coverage, including failures and takeovers.
- [x] Test live LM Studio with the disposable Explorer/Coder/Reviewer smoke.
- [ ] Test disposable external PostgreSQL/MLflow integrations in a target
      project with its own acceptance suite.

The live-smoke evidence is retained in the system temporary directory at
`local-worker-live-smoke-d4ba327dda19`. It is a capability check, not a
paired task result. The original S5 results are not reused as S6 evidence.

Do not mark the candidate as a proven usage-saving release until the paired
measurement gate is complete. A deterministic fake-model E2E proves protocol
and recovery behavior, not live model quality or operating-system isolation.
