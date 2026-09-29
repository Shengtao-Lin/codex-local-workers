# S6 real-task paired evaluation

The S5 ten-task benchmark is historical. This scorecard is for actual
maintenance work, not a claim that the current Local Worker already saves
Codex usage. The tool reads local JSON files and prints a summary; it does not
run a model, edit a repository, or modify benchmark results.

## Corpus and paired procedure

Collect a minimum pilot of about 20 task/trial pairs across small, medium,
and high integration risk. Include multi-file behavior, cross-unit contracts,
error handling, and at least one concurrency or lifecycle task. A task must
have a fixed Git start commit and a fixed acceptance suite revision. The
acceptance suite should include tests the implementer cannot reshape while
working. Do not select tasks only because a previous Local Worker run succeeded.

For each task and trial, use two isolated checkouts of the same start commit:

1. `primary`: Codex Primary implements and reviews directly.
2. `local`: Primary plans, delegates to the local workers where appropriate,
   reviews by risk, and completes the same acceptance suite.

Use the same Primary model and the same acceptance suite for both arms. Record
failures, retries, takeovers, and any failed quality gate, including runs that
end without a solution. Keep preparation/tool-building time separate from each
task's elapsed time. Randomize or alternate arm order to reduce order effects.
The scorecard checks that records agree with a manifest; it does **not** prove
that a claimed commit exists or that the acceptance hash matches real tests.
Primary must verify those before collecting results.

## Input format

Create an ignored local manifest (for example under `benchmarks/work/`) with
`schema_version: 1` and a non-empty `tasks` array. Each task has `task_id`,
`risk` (`small`, `medium`, `high`), `category`, full 40-hex `start_commit`, and
64-hex `acceptance_sha256`. Do not reuse a task ID after changing its task or
acceptance suite.

Create a JSON Lines file with one object per arm/trial. Required fields:

| Field | Meaning |
| --- | --- |
| `task_id`, `trial_id`, `arm` | Same task and positive trial number; arm is `primary` or `local`. |
| `start_commit`, `acceptance_sha256` | Exact manifest values for both arms. |
| `primary_model` | Identical for a paired trial. |
| `qualified_pass`, `first_gate_pass` | Actual independent acceptance outcomes, booleans. |
| `wall_seconds` | Measured task execution time, nonnegative. |
| `primary_tokens`, `token_source` | Optional together; use only attributable measured tokens. |
| `coder_calls`, `explorer_calls`, `reviewer_calls`, `takeovers` | Optional nonnegative local-flow counts. |
| `failure_categories` | Optional list of concrete failure labels, including unsuccessful runs. |

Example record shape (hashes below are placeholders, not an evaluation result):

```json
{"task_id":"real-01","trial_id":1,"arm":"local","start_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","acceptance_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","primary_model":"gpt-6-sol","qualified_pass":true,"first_gate_pass":false,"wall_seconds":420,"primary_tokens":null,"token_source":null,"coder_calls":2,"explorer_calls":1,"reviewer_calls":1,"takeovers":0,"failure_categories":["first-coder-rework"]}
```

Run the read-only scorecard:

```powershell
python benchmarks/real_task_eval.py `
  --manifest benchmarks/work/manifest.json `
  --records benchmarks/work/records.jsonl
```

It reports only complete matched pairs. Unpaired trials remain visible but
do not affect paired metrics. Token reduction is computed only from pairs with
measured tokens on **both** arms; call counts and subscription-window percentage
changes are never converted into tokens. `measured_all` means every *paired*
trial has usage measurements; check `unpaired_trials` before treating that as
full corpus coverage. A `measured_subset` is not evidence that the entire corpus
saves tokens. Review quality regressions and risk mix
before interpreting speed or usage.

## Codex CLI token collection (when using CLI arms)

An isolated `codex exec --json` run can emit a `turn.completed.usage` object.
This was verified locally on 2026-09-23; it is not a claim that desktop-app
threads expose equivalent task-level telemetry. Keep raw JSONL under the ignored
`benchmarks/work/` directory because it may contain prompts, source, and tool
results. Use one fresh CLI run per task arm and record the exact model.

```powershell
codex exec --json --ephemeral -m gpt-6-sol -C <isolated-checkout> `
  "<bounded task>" | Tee-Object benchmarks/work/real-01-primary.jsonl
python benchmarks/codex_usage.py benchmarks/work/real-01-primary.jsonl
```

Copy the extractor's `primary_tokens` and `token_source` into that arm's JSONL
scorecard record. For a task spanning several Codex CLI invocations, pass all
of that arm's JSONL paths to the extractor; it sums distinct streams. Each
stream must contain exactly one successful completed turn. The extractor rejects
absent or malformed usage, hashes the source streams, and counts cached input
only once. Use the same method for both arms. Token reduction is a token
comparison, **not** a conversion to subscription five-hour allowance or exact
credit cost: cache mix, model, reasoning, and other usage affect those. The
official [Codex usage dashboard and `/status`](https://learn.chatgpt.com/docs/pricing)
show account limits, not a reliable per-task allowance charge.

## Decision gate

Do not change the default model routing or advertise savings after a single
good run. First verify the full paired corpus, report token-measurement coverage,
and inspect each high-risk quality regression. If per-task token telemetry is
unavailable, report the quality/latency result and mark usage savings unknown.
Live LM Studio and disposable PostgreSQL/MLflow smoke tests are separate from
the deterministic local-runtime E2E suite.
