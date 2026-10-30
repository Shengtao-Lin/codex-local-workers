# Reviewer evidence candidate: fixed decision experiment

Baseline: `reviewer-evidence-baseline-1`, frozen before the change. Starting
weekly used is 45%; stop at 50%. Preserve all earlier outcomes and working-tree
changes. No commit/push, model change, permission expansion or Coder rewrite.

One candidate only: clarify Reviewer prompt distinctions between source-backed
code violations, justified blocking test gaps, and essential uncertainty. Keep
the report schema, risk floors, deterministic handoff and Primary authority.
The runtime does not mechanically classify semantics or accept/reject a finding
using keywords. No `.get`-specific example or fixture answer enters the prompt.

Feature/unit/integration risk: high (review authority). Owned contracts:
evidence-consistency, defect-recall, coverage-risk, immutable-history.
Unit rationale: changing judgment guidance affects an acceptance boundary, even
though execution permissions and report validation are unchanged.

Fixed prospective gate, registered before model execution:

1. Existing eight blind controls: two families, clean/defective, twice. All
   eight decisions must be substantively correct; hidden defects require causal
   source-backed findings, not unrelated coverage complaints.
2. Four additional distinctions, twice: correct arithmetic with optional missing
   boundary assertion (pass); correct arithmetic missing explicitly required
   assertion (rework/test_gap); conflicting negative-input requirements
   (escalate); wrong negative-input arithmetic (rework/contract_violation).
3. If both screens pass, fresh Reviewer-only reviews of the eight previously
   accepted real unit archives. No changes to implementation or previous reviews.
4. Deterministic Reviewer tests and broader regression, protected hashes and
   unchanged role/model/configuration checks must pass before adoption.

One incorrect substantive decision is enough to fail this strict candidate gate.
Finish the current screen for a usable denominator if budget allows, but do not
repair the candidate, resample failed cells or change expected outcomes. Later
stages are conditional, not omitted successes. Primary inspects actual evidence;
driver expectations are not semantic adjudication. Synthetic archives have no
Coder credit. Results support only this bounded gate, not general reliability.

A failure means HOLD, retain an unaccepted experimental candidate and propose a
separately authorized advisory-Reviewer mode. It does not permit relabeling the
old product gate as passed. At the usage ceiling preserve partial results and
report incomplete. No savings claim without measured Primary work/cloud tokens.
