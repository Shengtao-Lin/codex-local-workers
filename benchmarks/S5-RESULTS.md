# S5 baseline results

Measured on 2026-09-22 with the ten-task Python corpus described in
`README.md`. This is a diagnostic baseline, not evidence that the same result
generalizes to large repositories or other languages.

## Result

| Workflow | Final qualified pass | First quality gate | Rework | Local runtime |
| --- | ---: | ---: | ---: | ---: |
| A: Codex Primary direct | 10/10 | 9/10 hidden on the first evaluation | 1 Primary correction | not measured |
| B: original local Coder run | 10/10 | 2/10 accepted on first review | 12 rework reviews across 22 Coder calls | 220.588 s |
| P: structured-output pilot | 2/2 | 1/2 accepted on first review | 1 rework review across 3 Coder calls | 22.938 s |

The A workflow missed one boundary on task-06: an infinite retry cap was
accepted. A focused correction produced 10/10. Worker-specific review and call
metrics do not apply to A and are represented as `null` in `summary.json`.

The original B run preserved final quality without a Primary takeover, but its
20% first-review acceptance rate and 2.2 Coder calls per qualified task are too
weak to claim an efficiency win. Most failures were semantic boundary misses,
not evidence that a fixed total-call ceiling was needed.

The P pilot used LM Studio JSON Schema structured output and deterministic
sampling settings. Task-07 passed on its first call. Task-08 had no protocol
error but missed empty-input and blank-header behavior; after those scenarios
were made explicit in a revision-2 packet, the next bounded call passed public
and hidden tests. This supports improving packet specificity before adding a
reviewer model.

## Measurement limits

- Per-attempt Codex token usage was unavailable, so no percentage usage saving
  is claimed.
- A implementation elapsed time was not captured by the original harness.
- The corpus is small and its tasks have narrow, prewritten requirements.
- The original result writer replaced a task's canonical evaluation on rerun.
  The harness now archives the prior canonical result under the ignored local
  `results/<group>/history/` directory before writing a new attempt. The first
  failed A/task-06 output predates that fix and is summarized here rather than
  present as an immutable result file.

## S5 decision

The bounded runtime and Primary quality gate are viable, but the current data
does not yet prove Codex usage savings. Keep the local reviewer disabled. The
next useful experiment is a real small Python maintenance task with concrete
acceptance scenarios and actual usage/timing capture; use replacement-model or
reviewer experiments only if repeated, categorized failures justify them.
