# Explicit bounded-unit evidence bridge

`coordinator-bounded.py` is a trusted Primary-side, read-only API. Installation
does not enable it or change existing Coordinator, Coder, Reviewer or acceptance
defaults. It never dispatches a Worker, edits code, records acceptance, or grants
permission to retry a unit. Primary still owns classification and final review.

Callers must explicitly pass `bridge_profile="bounded-v1"`, a trusted feature
plan/capability catalog and the exact sealed per-unit configuration. Keep the
unit's `coordinator_enabled` false: this bridge is outside the isolated Coder
loop, not a way to switch on nested orchestration.

## Optional decomposition-only routing

`coordinator-routing.py` is a separate, explicit Primary-side API. It does not
change `coordinator-brief.py`, existing callers, or configuration defaults.
Use `bind_catalog(brief, catalog)` only with Primary-reviewed qualification
evidence. The binding covers the complete exact brief: contracts, source hashes,
tests, scope and risk. Each catalog entry names the already-qualified family,
exact implementation path/symbol and its evidence; merely naming a function
does not qualify it. Binding validates the complete Primary acceptance recipes
using the existing packet schema before any model call; missing tests or malformed
criteria are Primary preparation errors, not something the model can repair.

`probe(brief, context, client, binding)` asks the model for cohesive units and
dependencies without an `owner` field. The original validator checks the model's
decomposition first. The host then suggests `local-coder` only for an exact
qualified single-function match with no new files or ordering-sensitive contract;
unmatched units remain `primary`. Unresolved proposals remain unresolved. The
raw `decomposition`, materialized `proposal` and `routing` reasons are separate
in the result. A model-authored owner is a protocol error, not silently overridden.

Primary must review both the raw proposal (including uncertainty in its rationale)
and the suggested routing before using the existing `coordinator-brief.approve`
API on the materialized proposal. A qualification string is trusted Primary input,
not independently verified proof or model permission. No proposal or route calls
Coder, records acceptance, or authorizes a retry. Existing bridge checks still
apply at execution and dependency transfer. The model client must use the same
trusted configuration and single-residency lease as other Coordinator calls.

Evidence is limited to the recorded known-contract snapshot composition; this
does not establish decomposition from vague plans or general local coding.
Host owner selection is a policy property, not a model success score.

### Explicit proposal command

The installed `coordinator-limited.py propose` command can call this same API;
no separate launcher or production default change is needed:

```powershell
python -B .local-agents/coordinator-limited.py propose `
  --brief .agent/feature-brief.json --context .agent/feature-context.json `
  --routing-catalog .agent/qualified-routing.json `
  --config .agent/coordinator-proposal-config.json `
  --proposal .agent/unique-proposal.json --authorize-step
```

These are Primary-prepared files, not model-authored authority. The catalog maps
contract IDs to `family`, `path`, `symbol`, and `qualification_evidence` as
described above. The separate proposal configuration must explicitly enable
Coordinator and single-model residency. Do not change production defaults or
the downstream bounded unit's disabled Coordinator setting. Catalog/acceptance
validation precedes model construction and residency; current source hashes are
checked before and after the call. Proposal files are create-only.
If source inputs drift during the call, no current proposal is produced. The
opt-in command retains the completed, untrusted attempt in a create-only
`<proposal-stem>.invalid.json` diagnostic, exits blocked, and refuses to reuse
that identity. The diagnostic has no top-level approvable proposal and never
authorizes dispatch. Existing archives and source bindings are not rewritten.

Omitting `--routing-catalog` retains the existing model-selected-owner proposal
protocol. The option is rejected for `approve`, `dispatch`, and `inspect`:
their existing behavior has not been changed or qualified for the immutable
bounded snapshot workflow. For that workflow, review the raw and normalized
proposal, use the existing `coordinator-brief.approve` API, then the bounded
evidence/dependency bridge described here. This command is proposal convenience,
not an end-to-end autonomous runner. Inspect the saved `status`; a successful
command exit alone is not a valid proposal, approval or acceptance.

- `eligible_packet` validates the existing plan/schema/risk floor, one existing
  function/file, exact contract implementation binding and qualified route.
- `verify_accepted_unit` reuses the complete host handoff verifier, including
  manifest, real JUnit, configured commands, current source/tests and diff.
  It also checks live-request provenance, an exact completed fresh Reviewer
  pass/current observed sources, and the canonical report-bound Primary
  disposition. The pending-review status is preserved, not relabeled as legacy
  success. Replay archives do not establish live qualification.
- `dependency_readiness` verifies prerequisite evidence recursively and returns
  readiness for Primary consideration. `dispatch_allowed` and
  `automatic_acceptance` remain false. It is not a scheduler or dispatch lease.

The same-worktree mode requires every prior validation input to remain current;
the bridge does not automatically forgive downstream edits or roll validation
forward. For separate immutable snapshots, Primary can explicitly supply
`dependency_roots`, a containing `evidence_root`, and `transfer_paths`. A transfer
must copy the exact accepted producer-owned file bytes into a protected,
approved-readable consumer path. Neither root nor transfer permission can come
from a model-authored claim. Consumer validation and final integration remain
mandatory; passing a dependency gate is not feature acceptance.

Qualification is currently narrow: small, prelocated single-function tasks with
complete trusted contracts/tests and supported canonical observations. A
supervised snapshot smoke is not general release, repeated-reliability proof,
same-worktree automatic execution, or demonstrated cloud-cost savings.

Like the rest of this kit, evidence integrity assumes a trusted local host; this
API does not provide operating-system isolation or protect against a host that
rewrites both evidence and its bindings.
