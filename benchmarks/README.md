# S5 baseline benchmark

Copy `config.example.json` to the ignored `config.local.json` and set its
trusted Python interpreter before running local workers. Generated task
workspaces and detailed local results are intentionally ignored; the aggregate
`results/summary.json` is retained as publishable evidence.

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
- Codex token usage is `unavailable` unless an actual per-attempt measurement is
  supplied. Call counts or subscription percentages are not converted to tokens.
- Tool-building time is reported separately from per-task execution time.
- This first ten-task corpus is diagnostic, not evidence of universal savings.
