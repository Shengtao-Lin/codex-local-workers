# Strata supervised subagent

A local task worker for investigation, implementation and supplemental tests.
Primary assigns goals and constraints; Strata chooses its steps and repairs within
the task budget. Primary reads the actual work and independently accepts,
requests an eligible follow-up, completes a useful draft, or replans.

Version **0.3.0-supervised.2** is a release candidate pending publication and the
remote-install replay. Its runtime is the unchanged tested task.34 build.
The additional Primary guide, skills and feedback helper are optional.
Use trusted repositories and an isolated project copy for the initial trial.

## Install and configure

For Primary-assisted installation and current environment calibration, start with
[SETUP.md](SETUP.md). It covers pinned Release acquisition, fresh-project setup,
service-off waiting, non-overwrite behavior, current encoder calibration and the
separate task smoke. The manual path below remains available.

Keep this bundle in a stable location. Use an existing Python environment with
your project's checks, an existing Strata harness, and iq3_s as the only resident
model. Installation downloads nothing and leaves existing project files intact.
The target must exist and have no `.local-agents` installation.

```powershell
$kit = 'F:/tools/strata-subagent'
$projectCopy = 'F:/work/project-trial'
$python = 'F:/work/project/.venv/Scripts/python.exe'
& $python "$kit/install.py" --target $projectCopy
```

Give Primary [AGENTS.strata.md](AGENTS.strata.md), or merge its rules into the
project's own AGENTS.md. Keep existing project rules. Choose the relevant
[profile](PROFILES.md), adapt its connection paths and checks to your project,
and prepare a fresh task contract. The examples contain this machine's verified
Strata paths/tokenizer hashes; they are examples, not portable machine defaults.

Before the first coding call, inherit the project's test, formatter, lint and
typecheck requirements. Checks use Ruff `--no-fix` and format `--check`; the host
handles permitted formatting separately. Pin actual check inputs and verify
imports come from the project copy. See [contract format](CONTRACT.md).

## Run and review

```powershell
$taskId = 'change-001'
$request = "$projectCopy/.agent/requests/$taskId"
$entry = "$projectCopy/.local-agents/strata-task.py"
& $python "$projectCopy/.local-agents/strata-worker.py" doctor --config "$request/config.json"
& $python $entry prepare --project $projectCopy --contract "$request/contract.json" --config "$request/config.json"
& $python $entry prepare --project $projectCopy --contract "$request/contract.json" --config "$request/config.json" --apply
& $python $entry run --project $projectCopy --task-id $taskId --attempt-id first
& $python $entry status --project $projectCopy --task-id $taskId
```

Wait for the same process if it takes several minutes. Never restart a live task
just because an outer command yielded. `ready_for_primary` means review is
pending. Coding uses fresh independent-context review; investigation goes
directly to Primary. A valid report, matching quote or green check is not final
semantic acceptance. Read the complete report, not just its mechanical preview.

Canonical results are in `.agent/tasks/<taskId>/workflow/runs/<attempt>/result.json`;
actual diffs, checks and complete outputs are under the same task's `runs` tree.
Record an accepted coding unit with installed `record-review.py`; preserve the
original disposition when Primary instead completes a draft.

```powershell
& $python "$projectCopy/.local-agents/record-review.py" --repo $projectCopy --task-id $taskId --run-id first --decision accept --summary 'Independent validation facts and limits'
```

## Continue or complete a draft

Select continuation before the first call. One eligible same-contract follow-up
shares the original scope, history and credits; it does not grant a new budget.
The optional `tools/prepare-strata-return.py` generates version-bound feedback.
It never dispatches the worker or decides whether a finding is correct.

For readonly `task-v1`, supply an evidence question JSON with only
`contract_ids` (existing IDs) and `text`. For coding, use confirmed finding
objects with `id`, `contract_id`, `text`, `path`, `line`; the existing host also
requires the appropriate Reviewer disposition when findings originate there.

```powershell
& $python "$kit/tools/prepare-strata-return.py" --project $projectCopy --task-id $taskId --evidence-request question.json --output feedback.new.json --assistance unassisted
& $python $entry resume --project $projectCopy --task-id $taskId --attempt-id followup --feedback feedback.new.json
```

Classify new semantic explanations, specific fixes or algorithm help as assisted.
Preserve original failures. A small clear gap may be cheaper for Primary to finish:
wait for a settled task, retain the original work, complete a separate copy, then
validate and review the final version. The earlier Reviewer covers only its old
snapshot. No guarantee is made that a failed first stage is eligible for resume.

Use `cancel` with the task ID when needed, then inspect the resulting actual state.
For create-only implementation diff/check export use installed
`strata-worker.py export --project ... --task-id ... --output ...`.
This export does not bundle complete investigation/Reviewer transcripts; read
those from the canonical paths above. Export transfers a draft, not acceptance
or permission to overwrite a project.

## Boundaries and costs

Optional capabilities are explicitly task-approved; see PROFILES.md. There is no
arbitrary shell, model-authored script execution, deep recursion or Coordinator.
The host's checks execute trusted project code with host permissions: this is
not OS isolation for hostile repositories. Skills never grant permissions.

Some recorded investigations contain incorrect extra claims despite valid
citations. Primary must check material inferences, including mutable aliases,
dependency guarantees and concurrency claims. Local retries are allowed within
the original budget; repeated unchanged review sampling until PASS is not.

Separate independent worker completion, reusable drafts, Primary assistance and
final acceptance. Local request/time data is recorded; cloud tokens and Primary
active time may be unknown. This candidate does not promise a percentage saving.
