# Local agents

The local workers call LM Studio's OpenAI-compatible chat endpoint directly.
`explorer-runtime.py` exposes read-only repository actions;
`worker-runtime.py` exposes bounded implementation and validation actions; and
`reviewer-runtime.py` performs an independent read-only review of completed
Coder runs.

For explicitly configured bounded execution, use `local-bounded-unit.py` and
the `flat-v1` compatibility profile described in [host-proposal.md](host-proposal.md).
This profile sends flat `kind`/`content` Coder proposals and selects direct
Reviewer reports while reusing the same editor, checks and acceptance gates.
It remains opt-in; installing the kit does not select it or qualify new task
families. CLI model loading can separately use `model_load_ack_policy: "api_verified"`
to verify native readiness after a CLI timeout. The default loading policy is unchanged.

`local-bounded-review.py --inspect-only --request <request.json> --config
<config.json> --report <new-inspection.json>` authenticates the canonical run and
assembles the actual Reviewer evidence without loading/calling a model or claiming
its one-shot dispatch. It writes only the requested inspection report, not a
Reviewer archive or acceptance. Use a new report path for every inspection.
Real review still rechecks current evidence and claims its original single dispatch;
inspection cannot reopen an already dispatched run or replace independent review.

The bounded unit entry checks capture policy shape, declared scope/protection,
target-function binding and pinned interpreter before acquiring a model lease.
An incompatibility returns `blocked` / `bounded_capture_preflight`, with zero
model calls, so Primary can correct preparation without retrying the Worker.
This is not a complete dependency-import check or a passing validation result;
offline replay and the final canonical evidence gate remain necessary.

### Preparing one already-approved bounded unit

In a fresh isolated workspace, `local-bounded-prepare.py` assembles the capture
material that previously required manual copies and hashes. It does not author a
contract, choose tests/dependencies, widen scope, enable a profile, or call a model.
Supply a complete schema-2 packet, an explicitly selected bounded-v1 project
configuration, and a capture specification with exactly these fields:

```json
{
  "schema_version": 1,
  "target": {"path": "src/product/code.py", "module": "product.code", "symbol": "merge_labels"},
  "source_paths": ["src/product/code.py", "src/product/__init__.py", "tests/test_contract.py", "pyproject.toml"],
  "family": "json-call-model-dump-v1",
  "cases": [{"args": [{"a": "old"}, {"a": "new"}], "kwargs": {}}]
}
```

This example supplies factual inputs, not expected answers. Use the actual
approved function, complete explicit local dependency list and focused tests.
The packet must already make `acceptance/capture-policy.json`,
`acceptance/capture_validation_facts.py`, and
`acceptance/reviewer_capture_envelope.py` readable and protected readonly.
Existing project-specific Ruff format/lint, Pyright and actual-observations
commands must already be configured. Preparation never removes or substitutes
checks, and retains the registered bounded execution budget.

```powershell
python -B .local-agents/local-bounded-prepare.py --packet .agent/packet.json --config .agent/config.json --capture-spec .agent/capture-spec.json
# Explicit create-only application after inspecting the preview:
python -B .local-agents/local-bounded-prepare.py --packet .agent/packet.json --config .agent/config.json --capture-spec .agent/capture-spec.json --apply
```

The default preview does not write files or execute commands. Apply creates the
three capture files and `.agent/prepared/<run_id>/{packet,config,preparation}.json`;
the packet is copied byte-for-byte and only the task-specific capture-policy hash
changes in the copied configuration. Original inputs and production defaults
remain unchanged. Existing destinations, unsafe paths, missing protection and
stale inputs are rejected. All paths supplied to this entry are workspace-relative.
An interrupted write may leave partial files; the completion receipt is written
last, and a retry never overwrites them. Inspect and use a fresh snapshot instead.

Use the reported `next_inputs` for `local-bounded-unit.py --mode preflight` and
offline replay before live dispatch. Preparation is not passing validation or
qualification: package-initializer checks are not complete import discovery,
and actual checks, fresh Reviewer and Primary acceptance still apply. The
current fixed capture paths support one unit per fresh isolated workspace;
inheritance and multi-unit in-place preparation are deliberately not supported.

For source-only Explorer questions, Primary may explicitly set
`explorer_require_test_evidence: false` in the trusted per-call configuration.
This prevents a phrase such as "no test changes" from creating a mandatory test
report obligation. Use `true` when test evidence is required; omission retains
the legacy task-word inference. The obligation is included in the evidence-cache
identity. Any claimed citation still requires an actual allowed source read.
For qualified location work prefer the existing `explorer_mode: "locate"` with
approved paths/symbol anchors: the host returns source excerpts, not a trusted
model-authored causal verdict. Neither flag grants additional file permissions.

## Layout and compatibility

The project-local `.local-agents` directory is the default installation and
contains the Python entrypoints, runtime, configuration, and wrappers:

- `local-code.py`
- `local-explore.py`
- `local-code.ps1`
- `local-explore.ps1`
- `local-review.py`
- `local-review.ps1`
- `local-unit.py`
- `local-unit.ps1`
- `explorer-runtime.py`
- `reviewer-runtime.py`
- `worker-runtime.py`
- `safe-edit.py`
- `run-state.py`
- `record-review.py`
- `evidence-cache.py`
- `task-policy.py`
- `protocol.md`
- `config.example.json` (tracked template)
- `config.json` (local, ignored configuration)

An optional copy under `%USERPROFILE%\.codex\local-workers` may be retained as a
compatibility entry, but project operation must not depend on that global path.

## Setup and requirements

For another repository, use `python scripts/install_local_agents.py --target
<repo>` from the kit root to preview, then add `--apply` after reviewing the
file list. It excludes `.agent`, local `config.json`, and caches; worker runtime
tests remain included and can run in the target without `benchmarks/` or `scripts/`.
It refuses differing existing files rather than overwriting them; merge an
existing target `AGENTS.md` manually. Run the installer from the source kit;
the target does not need a copy of `scripts/install_local_agents.py`.

Create the local configuration before the first invocation:

```powershell
Copy-Item .local-agents\config.example.json .local-agents\config.json
```

- Windows PowerShell
- LM Studio listening at the URL in `config.json`
- the configured Coder and Reviewer models loaded or available in LM Studio
- target repository virtual environment at `.\.venv\Scripts\python.exe`
- pytest installed in that environment

The runtime itself uses only the Python standard library.

With `single_model_residency: true`, normal Explorer, Coder, and Reviewer CLI
invocations use one LM Studio role model at a time. At a role handoff the kit
unloads only the other model IDs configured for those three roles, then loads
the active model at its configured context length. A cross-process lease holds
the role model for the whole invocation, so concurrent kit calls fail with a
visible lock reason instead of unloading one another's model. A different
loaded LM Studio model blocks the handoff; the kit never unloads it implicitly.
The active model stays loaded after the invocation until the next role switch.
The lease file is in the system temp directory; after an abnormal termination,
inspect its PID and actual process state before removing a stale lease. This
policy coordinates this kit's CLIs, not unrelated LM Studio clients.

## Local verification before copying to another repository

Run all runtime tests with a Python environment that has pytest installed:

```powershell
python -B -m pytest -q .local-agents/tests
```

This collects both unittest-style and pytest fixture-based controls. Running only
unittest discovery omits the pytest-style Coordinator and bounded-entry controls.

`test_e2e_pipeline.py` starts a scripted loopback LM Studio-compatible HTTP
server and exercises the real Explorer, Coder, inherited rework, pytest
validation, run archives, and Reviewer CLIs. Its focused fixture covers normal,
error, and boundary inputs. It skips if the invoking Python has no pytest;
check the test summary for skips. This deterministic E2E checks the protocol and
orchestration, not the quality of a live model or an external PostgreSQL/MLflow
deployment. Real-service smoke tests remain separate and should use disposable
resources.

## Invocation

Run a focused read-only exploration from the target repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-explore.ps1" `
  -Task "Trace how configuration reaches request handling." `
  -Report ".agent\last-local-explorer-report.json"
```

Create a Coder packet based on `example-packet.json`, then run the normal
Coder → validated automatic Reviewer path:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-unit.ps1" `
  -Packet ".agent\implementation-packet.json"
```

The dispatcher verifies canonical validation, path attribution, and unchanged
validation inputs before starting Reviewer. For LM Studio Muse, the current
configuration uses `reviewer_native_tools: true`: the model emits one bounded
OpenAI tool call, which the runtime normalizes into the same allowlisted action
protocol. A Reviewer request error or model-request timeout still permits one
fresh-review-id retry after rechecking the handoff; both attempts remain in the
unit result. It does not accept on behalf of Primary. Use direct
Coder invocation for diagnostics:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-code.ps1" `
  -Packet ".agent\implementation-packet.json" `
  -Config ".local-agents\config.json" `
  -Report ".agent\last-local-coder-report.json"
```

`-Config` is optional and defaults to the configuration next to the runtime.
It is useful for isolated benchmark copies or repositories whose trusted Python
interpreter is configured outside their own root.

The Coder exits zero only with `ready_for_review`, after runtime-observed syntax
checks and focused pytest succeed after the final edit. `blocked` exits with code
3, `policy_violation` with 4, and `interrupted` with 130. After direct Coder
invocation, Primary must send the run through Reviewer and apply the risk route.
One packet may cover a cohesive multi-file behavior. Put critical acceptance
tests in `scope.readonly`; list Coder-writable tests in `supplemental_tests` and
`focused_tests`. `implementation_guidance` may suggest an approach without
making it mandatory. Coder can iterate edits and tests within the bounded call.
For a conflicting contract, suspected outdated test, or missing scope, Coder
sends `REQUEST_CONTRACT_REVISION` with observed evidence and returns `blocked`
for a Primary decision; this is neither success nor a quality failure.

Create a unique review request from `example-review-request.json`, then run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".local-agents\local-review.ps1" `
  -Request ".agent\review-request.json" `
  -Config ".local-agents\config.json" `
  -Report ".agent\last-local-review-report.json"
```

Reviewer is strictly read-only and returns `pass_to_primary`, `rework`, or
`escalate`. Small units route to Primary evidence acceptance, medium units to a
lightweight Primary review, and high units to a full Primary review. High-risk
feature integration still receives a final cumulative Primary review.

Coder requests use LM Studio JSON Schema structured output by default. The
schema guarantees one syntactically valid `{action, arguments}` object; the
runtime still validates action-specific fields, paths, hashes, state, and
authorization. `coder_structured_output` is an explicit backend-compatibility
fallback. Sampling and output limits come from `config.json`, so GUI inference
defaults do not silently change worker behavior.

Some managed Windows command sandboxes prevent child Python processes from
writing even within the workspace. The runtime reports this as an environment
block and never elevates itself. Primary may choose the host's approved execution
path after considering the repository and command.

## Protocol and security boundary

Explorer can request only `LIST_FILES`, `SEARCH`, `READ_FILE`, `TRACE`, and finish actions.
Coder can request only `READ_FILE`, `SEARCH`, `SAFE_CREATE`, `SAFE_REPLACE`,
`SAFE_REPLACE_LINE`, `VALIDATE`, and finish actions. Neither worker can construct commands. Coder
writes are restricted to the packet's exact create/modify allowlists. Existing
files require an exact unique replacement and a current SHA-256 read token.
Managed Coder runs also hold one repository write lock, reject symlink/junction
path components, create files exclusively, and atomically replace existing
files after rechecking their hash. A validation timeout triggers process-tree
termination; uncertain termination prevents further writes.
Failed replacements return a bounded excerpt near the closest current line and
do not consume a repair cycle unless an edit actually succeeds.
Reviewer can request only `READ_FILE`, `SEARCH`, registered
`RUN_APPROVED_TEST`/`RUN_APPROVED_STATIC_CHECK`, and `REPORT`; it has no write
action. Native tool transport does not expand this allowlist. It receives a
fresh context and treats Coder prose as untrusted.

Packets distinguish feature, unit, and integration risk. Primary decomposes a
feature into cohesive implementation units and assigns owned contract ids.
Contracts may set a `risk_floor`, preventing a critical invariant from being
made cheap merely by splitting the work. `scope.readonly` explicitly identifies
tests and context that Coder can inspect and execute but never modify.

Each Coder `run_id` owns an immutable archive under
`.agent/tasks/<task_id>/runs/<run_id>/`. It contains the final packet, pre-run
baseline, compact tool events, actual relevant changes, validation evidence,
exact authorized-file preimages, forward/reverse diffs, post-state, and handoff.
Reusing a run id is blocked instead of overwriting the
old record. Task state keeps runtime facts separate from Primary-owned accepted
decisions and open-issue conclusions.

After reviewing actual changes and broader validation, Primary records its
decision once:

```powershell
python .local-agents/record-review.py `
  --task-id "task-1" --run-id "task-1-unit-1-a1" `
  --decision accept --summary "Reviewed diff and regression evidence."
```

Review decisions are `accept`, `rework`, `replan`, or `takeover`. `review.json`
is exclusive-create and cannot silently replace an earlier review.

Coder output is compact by default so Primary need not ingest full hashes and
command logs on a normal success. The immutable run archive remains complete;
pass `--full-report` only when detailed diagnostics are needed.

Explorer caches successful results for an exact repeated task in
`.agent/repo-map.json`. Reuse occurs only while the visible repository
fingerprint is unchanged; otherwise Explorer calls the local model again and
refreshes the entry.

Use the smallest path that preserves quality:

- tiny, obvious, already-located edit: Primary implements directly;
- known files and settled behavior: one bounded Coder packet;
- unclear location or call flow: focused Explorer, then Coder if appropriate;
- architecture, security, concurrency, or ambiguous behavior: Primary settles
  invariants first and delegates only a bounded implementation if useful.

Python syntax checks do not emit bytecode. Focused pytest produces JUnit counts;
zero-test and all-skipped runs cannot become `ready_for_review`. Relevant source,
test, and observed evidence facts are bound to the validation result and checked
again when the worker tries to finish.
Packets can express `required_order`, `forbidden_orderings`, and per-scenario
`observables`. When present, `VALIDATE` requires a structured contract check.
Validation failures return a compact traceback/assertion digest rather than
forcing another broad file read. The base turn limit remains bounded, while a
small separately capped reserve guarantees room to react after the first
validation.
Before syntax/tests, a deterministic diff-quality gate rejects newly introduced
trailing whitespace, conflict markers, and missing final newlines with exact
file/line diagnostics. Trusted validation profiles may add fixed argument-array
commands such as Ruff; only actually executed checks appear in runtime evidence.
Focused rework can use `parent_run_id` plus `preserve_contract: true`; the
runtime inherits the parent's scope, risk, contract, tests, and limits and only
accepts new identity/revision and review feedback fields.

These action restrictions are not an operating-system sandbox. Pytest executes
trusted repository code, imports, `conftest.py`, and plugins with the actual
Python process permissions and may create side effects outside `safe-edit.py`.
V1 is for trusted local repositories.

Task-level fallback and invocation-level limits are separate. A task may use
multiple Explorer and Coder calls for as many distinct implementation steps as
needed. Each Explorer call has its own turn/read/search budget; each Coder call
has its own turn/protocol/repair budget. These per-call limits stop a single
worker loop but do not impose a total task-call ceiling.

Task fallback is progress based. By default, Primary falls back after the same
failure signature repeats three times without progress, the same unit has three
no-progress outcomes, or a worker fails the same quality gate three times.
Material progress resets the applicable streak. Unsafe or out-of-scope behavior
causes immediate takeover. `task-policy.py` provides a deterministic evaluator
for the state recorded in `.agent/current-task.json`.

Run the zero-dependency boundary tests with:

```powershell
python -m unittest discover -s .local-agents\tests -v
```
# Explicit Explorer capability modes (experimental localization)

`explorer_mode` defaults to `investigate`, preserving the existing research
report protocol. Opt-in `locate` returns selected source/test ranges, not an
execution prediction. The runtime materializes exact quotes and hashes from
unchanged, actually displayed source. Reports explicitly mark semantic
diagnosis `not_evaluated`; do not use them as proof that tests pass or that a
proposed repair is correct. Primary/Coder/Reviewer retain their responsibilities.
The locator accepts at most six references and 80 total displayed lines, with
one bounded final-report correction. Missing evidence fails closed. The two
modes have separate exact-task cache keys. Qualification results must name the
mode; success in `locate` does not qualify `investigate` for autonomous routing.

## Read-only supervised Coordinator inspections

From the target repository root, the restricted Coordinator supports
`--compact-handoff` and `--next-step`, with `--plan <feature-plan.json>` and
`--run-refs <accepted-run-refs.json>` (or repeated `--run-ref UNIT TASK RUN`).
An empty JSON object supplies no accepted-unit evidence. `--next-step` also
reads `--state`, defaulting to `.agent/coordinator/<feature_id>/state.json`.
Absent state initializes read-only pending memory; it does not create a file.

Only matching immutable Primary/Coder/Reviewer archives establish accepted
units. Unknown units remain unverified. An unresolved running, rework or
escalated unit requires Primary inspection before further dispatch; no restart
or retry is triggered. `CONTINUE` is a proposal for a Primary-authorized
localization dispatch, not automatic execution. `FEATURE_READY` additionally
requires current passing integration evidence and means only eligibility for
Primary final review. Both interfaces are read-only and never accept a feature.

Coordinator model probes use `coordinator-runtime.py --mode decision|proposal`
with a Primary plan and bounded context. `--report` creates immutable evidence
inside workspace `.agent`; it never overwrites old outcomes. Decision probes
can additionally use `--check-transition --run-refs <Primary-selected refs>`
and optional `--state`. They reread state after inference and reject a changed
sequence. Syntax validity is distinct from `transition_valid`; neither launches
a worker. Unaccepted dependencies and unresolved execution block CONTINUE;
REWORK_LOCAL requires the separate explicit Primary recovery route;
FEATURE_READY needs matching accepted archives and current passing integration.

## Explicitly authorized model-Coordinator step

`coordinator-supervised.py` is the opt-in product entry point for one
Primary-supervised localization unit. From the target repository root, supply
`--plan`, `--context` (including the Primary-granted unit/run/attempt/revision),
`--request`, `--explorer-report`, `--run-refs`, `--config`,
`--authorize-step`, and `--expected-sequence <current sequence>`.
Missing authorization or stale state fails before model inference.

The entry independently gates a model decision, materializes a fresh-context
proposal against the Primary contract, verifies current Explorer evidence,
releases the Coordinator model lease, and dispatches the trusted Coder→Reviewer
route. Dispatch repeats the authorized sequence check. Every run reserves a
create-only proposal archive; an existing run id is never overwritten or retried.
ESCALATE_PRIMARY and FEATURE_READY do not dispatch or accept anything. Primary
still reviews and records acceptance separately. This entry does not
automatically recover failed units or accept features.

Opt-in `--manage-exploration` lets Coordinator select RUN_EXPLORER,
REUSE_EVIDENCE or ESCALATE_PRIMARY in a separate fresh context, with at most one
protocol correction. RUN_EXPLORER launches the trusted read-only CLI using the
unchanged Primary-approved single question and locate-mode configuration;
the Coordinator lease is released first. `--explorer-report` may be omitted for
this mode. REUSE_EVIDENCE only avoids another call: all current-file and quote
checks remain mandatory before Coder dispatch. Missing evidence cannot be
skipped, and failed Explorer calls are preserved without automatic retry.

Exploration now precedes proposal generation. The proposal's fresh context
receives the selected report's bounded source references; the original Primary
context is unchanged. Existing evidence is first checked against the Primary
unit's scope ceilings, and that runtime fact is supplied to the exploration
selector. Dispatch still rechecks evidence against the actual narrower packet.

An already-applied terminal-failure recovery grant can be supplied with
`--recovery-authorization <fixed Primary review path>`. The entry checks the
failed canonical archive hashes, post-recovery state sequence, approved new run id
and increased attempt/revision before model inference. Only the granted unit may
receive a REWORK_LOCAL proposal; all normal packet/evidence checks and the
trusted route's no-scope-expansion rules still apply. The entry neither creates
the Primary grant nor infers permission from the model's reason_code. Unknown,
interrupted or incomplete execution requires inspection, not a replay.

`--proposal-id <unique identifier>` reserves a separate immutable Coordinator
attempt without changing the Primary-granted Coder run identity. Use it only
after Primary inspection/authorization and a changed approach or evidence target,
not as an automatic retry. Any existing canonical Coder run directory, including
an incomplete one, blocks inference: another proposal id never permits execution
replay. The old proposal archive is retained and cannot be overwritten.

Successful Coordinator transport calls retain a deep-copied `model_requests`
metadata list in decision/proposal and exploration-choice archives, including
protocol-correction turns. These are client-observed request facts, not model
claims, prompts, or authority. A transport exception may leave only a partial
archive; missing usage is unknown, not zero.

Compact handoffs include canonical validation counts/configured-check results
and the matching fresh Reviewer's current findings/check acknowledgements.
Missing fields remain `null` or `not_recorded`; historical finding resolution
is explicitly `not_inferred` and requires archive inspection when relevant.
Neither the compact facts nor FEATURE_READY replace risk-routed Primary review.

Native LM Studio model keys and loaded-instance ids can differ. Readiness reuses
the resident instance of the matching model key while retaining the configured
context floor; it does not reload merely because an instance has an alias id.
The role lease still enforces exactly one resident managed model instance.

## Limited, capability-routed Coordinator entry

`coordinator-limited.py` is an opt-in, explicitly supervised entry. It does not
replace `coordinator-supervised.py` or change the default `coordinator_enabled`.
It is qualified only for the named small transformations and sequential async
collection/receipt contracts tested with this kit. Classification remains
Primary-owned; unknown task families require a Primary decision, not a local retry.
No general semantic reliability or cloud-cost saving is established.

Primary supplies a schema-1 brief with `acceptance_catalog`, complete
`capability_catalog`, and hashes of writable and protected inputs. Each capability
entry has `owner`, `route` (`direct_local` or `primary_owned`), exact `modify`
paths, and qualification `evidence`. The model cannot add qualification. Primary
must review both the actual task's fit and the proposed ownership/dependencies.
New file creation is not qualified in this entry. Do not label an unsupported
task as qualified merely to make its dispatch pass.

Use a project-specific configuration with `single_model_residency: true`, the
existing local models, and required project lint/format checks. The tested modes
are `explorer_answer_protocol: true`, `reviewer_evidence_ids: true`,
`reviewer_assessment_protocol: true`, and `coder_typed_action_arguments: true`.
Set `coordinator_enabled: true` only in this explicitly selected test config.
Installation does not copy or overwrite `config.json`.

From the target repository, with all Primary JSON inputs under `.agent`:

```powershell
$python = '.\.venv\Scripts\python.exe'
$entry = '.local-agents\coordinator-limited.py'
& $python -B $entry propose --brief .agent/brief.json --context .agent/context.json --proposal .agent/proposal.json --config .agent/config.json --authorize-step
# Inspect the untrusted proposal and review ownership, atomic contracts and tests.
& $python -B $entry approve --brief .agent/brief.json --proposal .agent/proposal.json --approval .agent/approval.json --config .agent/config.json --authorize-step --note 'Primary reviewed qualification, contracts and dependencies'
# Primary materializes one bounded packet using coordinator-contract.py.
& $python -B $entry dispatch --brief .agent/brief.json --proposal .agent/proposal.json --approval .agent/approval.json --config .agent/config.json --refs .agent/accepted-refs.json --packet .agent/unit-packet.json --authorize-step
```

An initial `accepted-refs.json` is `{}`. Dispatch runs the installed `local-unit.py`
and its automatic fresh Reviewer, never acceptance. Primary inspects the real
diff and current validation, records the immutable `record-review.py` decision,
and supplies the selected canonical `{task_id, run_id}` reference for that unit.
Only then can a separately authorized dependent step start. Primary-owned units
use the fixed Primary review path and hashed passing test/lint/format receipts,
not synthetic local-worker credit. After all units, run independent integration
checks and perform final risk-routed review. `inspect` verifies selected records
and current source hashes but does not claim integration or feature acceptance.

Approvals bind brief, proposal, plan, configuration and installed runtime bytes.
Contract/config/runtime drift, unaccepted dependencies, stale evidence, and
duplicate dispatch fail closed. A started, failed or interrupted step is not
replayed automatically: retain its archive and ask Primary to adjudicate a new
reviewed identity. These checks assume trusted Primary files and a trusted local
repository; they are not a security boundary against the host user.
