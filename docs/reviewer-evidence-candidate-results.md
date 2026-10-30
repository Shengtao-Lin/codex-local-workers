# Reviewer evidence candidate — HOLD

2026-10-10. One candidate evaluated against the preregistered
`reviewer-evidence-candidate-plan.md`; no second candidate or failed-cell resample.
Starting and final observed weekly used: 45%; ceiling: 50%. Stop reason is a
completed, auditable stage decision, not budget exhaustion.

## Results

| Fixed distinction | Correct / executed |
| --- | --- |
| Existing blind controls | 7 / 8 |
| Four new distinctions, twice | 7 / 8 |
| All substantive decisions | 14 / 16 |
| Real code defects detected across both screens | 6 / 6 |
| Correct code with no explicit test-coverage obligation | 5 / 6 |
| Explicit missing-test obligation correctly blocks | 2 / 2 |
| Contradictory contract correctly escalates | 1 / 2 |

The last four rows partition the sixteen controls. All archives are explicitly
synthetic Primary-authored controls; none is a real Coder success. The conditional
eight real-unit Reviewer rechecks were not started because the screen failed.
No production implementation, Coder, Explorer or Coordinator model call occurred.

Candidate regression: **1009 passed, 117 subtests passed**. Targeted Reviewer
tests: 85 passed, 25 subtests. Initial sandbox attempt failed on host temporary
directory permissions; its XML is retained separately. The approved host rerun
passed. After restoring the live baseline, its Reviewer tests passed again:
84 passed, 25 subtests. Ruff passes for both new drivers; diff check passes.

Sixteen Reviewer invocations produced valid final reports; four protocol errors
were recovered in two calls. This is not a protocol-error-free qualification.
Reviewer command windows total 538.894 seconds (about 8m59s), excluding fixture
preparation and Primary work; loading time is not separately measured. Primary
active time/cloud tokens remain unmeasured, so no cost-saving claim is made.

## What the single candidate changed

Only the Reviewer system prompt and one associated policy regression test changed
between frozen baseline and candidate. Guidance distinguishes source-backed code
violations, justified blocking coverage gaps, and essential uncertainty. No
special-case `.get` hint, keyword-based report rejection, permission expansion,
model swap, temperature change or extra retry was introduced. The existing report
schema and Primary acceptance authority were retained.

Current Muse remains `meta/muse-glimmer`, context 24576, parallel 1,
temperature 1.0, CLI loading, single-model residency. Live `lms ps --json` during
execution and after completion showed only Muse. Existing Explorer/Coder model
configuration and global Coordinator-disabled setting were unchanged.

## Two remaining failures

`display-default-a-r1`: Reviewer acknowledges that `record.get("name", "unnamed")`
returns present empty/None unchanged and does not mutate the input, but still
blocks with high-severity `test_gap`. The contract defines return semantics; it
does not explicitly require those assertions. Reviewer supplies no unresolved
material risk beyond absence of tests. Primary source review and an independently
executed empty/None/missing/named/nonmutation probe confirm correct behavior.
Round two passes with identical source, tests and configuration. Thus the
candidate changes the label, not reliably the unnecessary rework disposition.

`conflicting-contract-r2`: contract requires `x+1` and `x-1` for negative integers.
Reviewer's suggested fix correctly says escalate because satisfying both is
impossible, but final decision is `rework/contract_violation`, which produces
`next_action_required: bounded_coder_rework`. Round one correctly escalates the
same contract/source/tests. This is a separate inconsistency between understood
evidence and selected disposition; it is not failure to compute the contradiction.

Both incorrect decisions have zero protocol errors. The frozen source and
protected-input hashes are intact. No HTTP/loader failure explains these two
judgments. A hidden lookup control also contains a stray contradictory sentence
about false-valued results in contract_review; its principal exception-propagation
finding is causal and correct. Primary recorded the limitation rather than
turning that sentence into another production repair.

The six true code-defect controls were detected with relevant source evidence and
repairs. This small result supports continued usefulness as a research/review
assistant, not general recall, zero false-positive reliability or a new release.
Historical old-screen result was also 7/8; this is not a randomized paired
experiment and does not establish improvement or statistical equivalence.

## Disposition and next decision

**HOLD the candidate and the existing product gate.** The candidate is preserved
in `reviewer-evidence-candidate-1`; only this round's prompt/test delta was removed
from the default runtime. Every baseline-frozen live file matches its original
hash, preserving all pre-existing dirty changes. No commit/push, sibling-repo
write, history deletion or global Coordinator enablement occurred.

Do not spend the next round on more reminders or rerunning until these cells
happen to pass. The next architectural decision should be an explicit supervised
Reviewer disposition boundary:

- Reviewer supplies typed evidence, not independently conflicting instructions
  for code rework versus contract escalation. Types alone do not prove semantics.
- Trusted routing preserves the distinction between a production defect, an
  explicit blocking coverage requirement, and a contract/context question.
- Primary confirms each blocking finding before creating a Coder rework packet;
  contract conflicts go to Primary revision, not production repair.
- Optional test suggestions cannot silently become new hard requirements;
  high-risk unresolved gaps and explicitly required assertions still block.

This would be a separately authorized mode/schema/routing change, not a claim
that the current fixed gate passed. Existing Primary authority already prevents
automatic feature acceptance; the proposal makes rework disposition less
dependent on an internally inconsistent model report. Retain these sixteen
controls and add no new cases merely to dilute their failures. A future proposal
must preregister a versioned gate and measure Primary adjudication effort against
direct Primary review before claiming product value. No such redesign was
implemented in this round.

## Evidence

All evidence is under `benchmarks/work/capability-fit/reviewer-evidence-1/`:

- `registration.json`: prospective cells, expected dispositions, protected hashes.
- `independent-observations-1.json`: actual source/tests and external boundary probes.
- `primary-adjudications-1.json`: explicit Primary causal judgments for all sixteen.
- Each root's `.agent/primary-control-adjudication.json` and canonical `review.json`.
- `primary-screen-decision.json`: HOLD, 14/16, conditional stage not started.
- `final-audit-1.json`: freeze scope, restored live hashes, old source/test equality,
  sole-resident model facts, protocol counts, durations and unmeasured economics.

Frozen baseline/candidate siblings retain complete runtime and tests. Candidate
execution driver is `benchmarks/reviewer_evidence_candidate.py`; independent
observation/explicit adjudication driver is `benchmarks/reviewer_evidence_audit.py`.
Deterministic XML logs are in `benchmarks/work/reviewer-evidence-*.xml`. No prior
report or acceptance decision was overwritten.
