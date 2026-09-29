# Benchmarks

The [S5 baseline](S5-RESULTS.md) is a historical diagnostic experiment from
before the current S6 Reviewer and recovery flow. For current-version evidence,
follow the [real-task paired evaluation protocol](REAL-TASK-EVAL.md) and its
read-only `real_task_eval.py` scorecard. Do not mix S5 aggregate results with
new S6 trial records.

For a disposable live LM Studio protocol smoke, run
`python benchmarks/live_smoke.py` with an interpreter that has pytest and Ruff.
It creates a new system-temp workspace, keeps the reports for inspection, and
does not edit the kit. This is a small capability check, not the real-task
paired benchmark. `codex_usage.py` extracts measured token counts from one or
more private `codex exec --json` streams; see the paired protocol for limits.

To persist model-by-role protocol qualification evidence, run
`python benchmarks/role_compat.py`. It reuses the disposable live smoke, reads
the canonical Explorer/Coder/Reviewer action archives, and writes timestamped
local results plus `benchmarks/results/role-compat/latest.json`. A core role
success remains `incomplete` until every required action has actually been
exercised; missing coverage is never promoted to a compatibility pass. A
Reviewer blocked by failed Coder validation is `not_run`; a model-server
rejection is recorded as `infra_failure`, including bounded startup retries.

The frozen runtime capability contract is
`benchmarks/capability-matrix-v1.2.json`. Each allowed and prohibited matrix
cell references an executable test node, and the full local-agent suite checks
both those behaviors and the fixture's referential integrity. This proves
runtime enforcement; it does not replace live model-role qualification.

The stability runner now contains eleven named frozen cases, including the
original six-case baseline. Run `benchmarks/stability_e2e.py`
with pytest, Ruff, and the copied source modules' declared Python dependencies
available in the *same* interpreter; it checks test collection before any
model call and refuses to score an uncollectable fixture. For example:

```powershell
uv run --with pytest --with ruff --with pydantic --with pydantic-settings `
  --with opentelemetry-api --with sqlalchemy --with fastapi --with httpx `
  --with alembic python benchmarks/stability_e2e.py --rounds 1
```

The first two-round, 12-unit v1.2 baseline and its GO/NO-GO decision are in
`V1.2-UNIT-BASELINE.md`. Keep its archived batch as the pre-fix comparison.
The separate post-fix 12-unit comparison and remaining caveats are in
`V1.2-ITERATION-RESULTS.md`; do not pool their denominators.
The static-check-only fixture, later distinct unit expansions, and independent
real-source Reviewer hidden-defect challenges are documented in
`V1.2-EXPANDED-COVERAGE.md`. Do not pool successive batch denominators.
The one-round frozen 11-case expanded batch and its Primary acceptance audit
are in `V1.2-EXPANDED-UNIT-BASELINE.md`.
The later frozen 22-run, two-round expanded audit and strict Explorer semantic
checklist are in `V1.2-TWO-ROUND-AUDIT.md`; its Phase 2 decision is NO-GO.
The later role-aligned gate, unknown-location handoff, mathematically stopped
candidate, and one focused repeat are in `V1.2-ROLE-ALIGNED-CANDIDATE.md`.
Future two-round candidates can use `stability_e2e.py --rounds 2
--stop-when-unreachable`; a stopped batch is a NO-GO result, not a complete
denominator. Assess a complete batch with
`v1_2_readiness.py --gate-version role-aligned-v1`.
`V1.2-EXPLORER-SEMANTIC-AUDIT.json` is the Primary-reviewed per-cell rating;
`python benchmarks/explorer_semantic_audit.py` checks that it covers every
frozen cell and reports semantic success separately from line evidence and
protocol E2E. It is not an automated natural-language judge.
Disposable Bonsai Explorer and Devstral Reviewer qualification, including the
Explorer semantic-versus-citation gap, is in `V1.2-MODEL-CANDIDATES.md`.
`coder_search_compat.py` and `sample_identity_decomposition.py` retain
isolated candidate/decomposition diagnostics; they do not change active
role routing or overwrite the formal baseline.

The current role mapping is OSS20B Explorer, Q4_K_M Qwen Coder, and Muse
Reviewer with bounded native tool calls. Run `role_compat.py` after changing
any role model or transport. Each later 10–15-unit run must be a new batch,
not an aggregate of earlier calibration or candidate trials; keep Explorer as
an independent success denominator. See `STABILITY-V1-RESULTS.md` for
qualification history and remaining first-pass/rework caveats.

For an isolated Explorer model comparison on the frozen cases, run
`python benchmarks/explorer_candidate_eval.py --rounds 2` with the same
dependencies as `stability_e2e.py`. It creates one workspace per model and
case so Explorer's content-addressed cache cannot turn a model comparison into
a cache replay. Its `mechanical_success` means a real model call returned a
successful report with observed file/line evidence; manually verify the claim
against source and tests before counting semantic success. The 2026-09-26
OSS/Bonsai and Devstral candidate outcomes are in `STABILITY-V1-RESULTS.md`.

To test Reviewer bug detection beyond a green test suite, pass the disposable
`workspace` printed by `live_smoke.py` to `reviewer_challenge.py`:

```powershell
python benchmarks/reviewer_challenge.py --source-workspace <smoke-workspace>
```

The challenge synthesizes a canonical review archive in another temp workspace,
executes pytest and Ruff on code with an untested long-input contract violation,
then asks the configured local Reviewer to inspect it. The packet does not reveal
the injected bug. Success requires a concrete finding on the offending source
line; a bare `escalate` or empty findings is not counted. This is a one-case
diagnostic, not a measured miss rate or proof of general review reliability.

## S5 baseline benchmark

Copy `config.example.json` to the ignored `config.local.json` and set its
trusted Python interpreter before running local workers. Generated task
workspaces and detailed local results are intentionally ignored; the aggregate
`results/summary.json` is retained as publishable evidence.
The interpretation and limitations of the current run are recorded in
`S5-RESULTS.md`.

This benchmark compares two workflows from identical task snapshots:

- `A`: Primary/Codex implements and reviews directly.
- `B`: Primary creates a bounded packet, the local Coder implements it, and
  Primary independently reviews the result.
- `P`: a disposable local-Coder pilot used to retest selected failure-prone
  cases after runtime or deployment changes; it is not part of the A/B result.

The corpus contains ten small Python maintenance tasks spanning validation,
boundary handling, cross-function behavior, exception paths, state, and small
refactors. Public tests are visible to the implementer. Hidden acceptance tests
are stored inside the harness and materialized only while Primary evaluates a
finished attempt.

## Commands

```powershell
python benchmarks/s5_benchmark.py prepare --group B
python benchmarks/s5_benchmark.py baseline --group B
python benchmarks/s5_benchmark.py evaluate --group B
python benchmarks/s5_benchmark.py summary
```

Use `--tasks task-01,task-02` for a pilot subset. Preparing an existing task is
refused unless `--replace` is supplied, so an attempt is not silently reset.

Each prepared task contains `.agent/implementation-packet.json`. Run the local
Coder from that task directory while passing `-Config` to the PowerShell wrapper
or `--config` to the Python entrypoint. Point it at a trusted config whose Python
interpreter has pytest installed. Runtime archives and Primary review remain
inside the isolated task.

## Measurement rules

- A task passes only when both public and hidden tests pass.
- Initial snapshots must fail at least one public or hidden assertion.
- Record failures, rework and takeovers; do not report only successful runs.
- Rerunning an evaluation archives the previous canonical result under the
  ignored local `results/<group>/history/` directory.
- Codex token usage is `unavailable` unless an actual per-attempt measurement is
  supplied. Call counts or subscription percentages are not converted to tokens.
- Tool-building time is reported separately from per-task execution time.
- This first ten-task corpus is diagnostic, not evidence of universal savings.

Explorer semantic review must use each cell's `explorer_full_report` (or the
compact report's `diagnostic_report`), not the CLI report alone: the latter
intentionally truncates each finding at 800 characters and now exposes
`findings_truncated` for visibility.
