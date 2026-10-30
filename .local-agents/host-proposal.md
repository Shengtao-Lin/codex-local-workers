# Experimental host proposal protocol

## Explicit bounded-v1 installed entry

For the qualified local compatibility path, explicitly add
`"bounded_compatibility_profile": "flat-v1"` to the trusted configuration.
Coder then sends a required `kind`/`content` object and the host normalizes it
to the existing replacement or blocked proposal. Reviewer uses the existing
low-reasoning, required-report transport from its first source review.
Contracts, editing boundaries, budgets, checks and Primary acceptance stay the same.
Omitting this setting preserves the earlier wire and Reviewer selection.

With the CLI model loader, `"model_load_ack_policy": "api_verified"` permits a
timed-out CLI process to proceed only through the existing native API checks:
exactly one correct model, verified sufficient context and parallel=1. A timeout
is retained in request diagnostics. The default `"strict"` policy still fails
on CLI timeout. This does not extend model-request or validation budgets.

Qualification covers the recorded local-function and complete-package trials,
not arbitrary algorithmic repairs. ASCII-boundary recovery remains unqualified;
automatic semantic Reviewer-to-Coder rework remains off. The caller still supplies
a trusted packet/profile. Register every local project import needed by factual
observations, including package `__init__.py` files, and verify the complete
installed entry offline before a new live project trial. Explorer and Coordinator
qualification is separate.

### Optional compact execution output

Add `--compact-output` to an explicit `local-bounded-unit.py --mode unit` call
to print one concise execution receipt. This is a presentation option, not a
configuration/profile or change to Worker context, checks, budgets or permissions.
The ordinary output remains the default. Full Coder/Reviewer reports and canonical
archives are retained; Reviewer process streams are also preserved under the run
archive as `reviewer-process.stdout.log` and `reviewer-process.stderr.log`.

The receipt lists the actual stop reason, edit/check/no-op counts, failing checks,
Reviewer recommendation and evidence paths. Any excerpt truncation is explicit.
The original Coder-stage marker remains as `coder_next_action_required`; the
unit-level `next_action_required` points to Primary review/disposition after a
completed Reviewer, not another dispatch. Conflicting or missing facts point to
evidence reconciliation. These are navigation labels, not executable commands.
`reviewer_reported_decision` is a raw convenience-file label, not authorization;
the authoritative returned `reviewer_decision` requires successful process exit
and a matching current-run canonical report/completion record. A stale PASS cannot
clear this return gate. Offline inspection is always `NOT_RUN`, never live review.
Primary still verifies current evidence and performs the required risk-routed
review. Neither a receipt nor `pass_to_primary` is final acceptance or permission
to automatically retry. Output reduction is not a measured cloud-cost saving.

`local-bounded-unit.py` is a separate, default-off installation of the bounded
single-function candidate. It does not change `local-unit.py` or enable a global
default. Current qualification is limited; no Coordinator or automatic semantic
Reviewer-to-Coder rework is enabled.

The trusted run configuration must add `bounded_execution_profile: "bounded-v1"`
and the registered host-proposal opt-ins. The profile keeps the fixed 12-request,
3-effective-edit, 1-initial-check plus 3-post-edit-check, 900-second Coder limits.
Formatting and protocol recovery are separately bounded. It requires the exact
trusted strict profile (focused tests, Ruff format/lint, Pyright and an
authenticated `actual-observations` command), a matching protected canonical
capture policy, and the existing single-function write scope. Unsupported
profiles, nonmatching capture targets and additional execution/search/ordering
review obligations fail closed; they are not general task support.

```powershell
python .local-agents/local-bounded-unit.py --mode unit `
  --packet .agent/packet.json --config .agent/bounded-config.json `
  --report .agent/unit-report.json --review-report .agent/reviewer-report.json `
  --summary .agent/unit-summary.json
```

The installed Coder uses `bounded/static_focus_rules.py`; the fresh Reviewer uses
the same contract-first/canonical-capture candidate as the frozen experiment,
including explicit reasoning-effort transport. Final acceptance still belongs
to Primary. Passing configured checks or a Reviewer PASS is never final acceptance.
The installed package contains no sealed historical task provider or benchmark
directory dependency. Historical experiment source is retained as a frozen
comparison, not silently substituted into installed execution.

The `--replay` option is for offline diagnostic responses only. It authenticates
the review input without calling a Reviewer and cannot establish semantic review
or feature acceptance. No real LM Studio call is needed for `--mode preflight`.

## Legacy opt-in profile (unchanged)

This default-disabled R3 candidate is not a general product release. Existing
configurations and `ready_for_review` archives keep their old contract gates.

The trusted configuration must explicitly set `host_proposal_enabled: true`,
`coder_structured_output: false`, `coder_typed_action_arguments: false`, and
`coder_single_function_patch_repair: false`, with the existing exact
`coder_single_function` scope. Coordinator must be disabled. High-risk packets
require `host_proposal_isolated_high_risk_fixture: true`; this is only for the
registered isolated evaluation, not permission to downgrade risk.

The model supplies one strict JSON whole-function replacement or a concrete
blocked reason. The host binds the current source hash and exact function span,
preserves the qualified terminal-newline boundary, applies through SafeEditor,
and runs trusted checks. No shell or arbitrary edits become model actions.

A fresh baseline check counts against the same maximum of three checks. Every
formatter-triggered recheck also counts. Maximums are six model requests, three
effective proposals and two repairs, further reduced by existing packet limits.
Green unedited baselines, unknown model assessments and rejected proposals never
become implementation success. The host never generates `contract_check` claims.

`host-proposal-v1` archives use `validation_passed_pending_review`. A separate
immutable manifest binds the actual checks, JUnit, current revision, configuration
and canonical archive artifacts. `local-unit.py` requires explicit opt-in and
verifies those facts plus the existing scope/diff/current-input gates before one
automatic independent Reviewer dispatch. Reviewer receives the unchanged complete
contract; its semantic rules and model are unchanged. There is no automatic
second Reviewer call with a changed token budget in this mode. A dispatch claim
prevents replay under a fresh review id.

Primary acceptance still requires a passing independent review and current host
facts. Supply the same trusted configuration using `record-review.py --config`.
Task policy sends this new state to Primary until the protocol-aware verifier has
run; it does not call it legacy success. Unknown protocols fail closed. Neither
classification nor cross-file tasks are admitted, and Coordinator is not enabled
by this candidate.

The installer distributes the three new Python modules and this note while
preserving the destination config, so installation alone never enables the mode.
Archives are integrity evidence in a trusted local repository, not cryptographic
attestation against a host capable of rewriting both facts and their manifest.
