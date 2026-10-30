# Reviewer disposition boundary

This change preserves model judgments but separates them from rework authority.
Reviewer `rework` means `primary_adjudicate_review_findings`, never permission to
start Coder. local-unit normalizes legacy reports to the same safe boundary.
No model prompt, model configuration, retry allowance or existing safety gate changes.

task-policy uses the same Primary-adjudication route. For an inherited Coder
packet whose parent has a blocking Reviewer report, worker-runtime requires an
immutable Primary `rework` decision with a report-bound disposition and feedback
citing confirmed finding IDs. Contract revision, no disposition, altered report
or unconfirmed finding references are rejected before model execution. Ordinary
repairs of Coder validation failures without a Reviewer blocker remain compatible.
Fresh packet authoring is still trusted Primary authority, not an OS security
boundary; models cannot author new packets or invoke Git/shell/delegation.

Before Reviewer-based rework, Primary supplies `record-review.py --disposition`
with schema_version 1, authority `primary`, exact canonical Reviewer handoff
SHA-256 and identity (including review_id), resolution (`cleared`,
`contract_revision`, `unresolved`), nonempty evidence array, and one findings
entry per reported finding. Each entry contains finding_id, disposition and
source/test-backed evidence. Types: confirmed_defect, required_test_gap,
nonblocking, contract_revision, unresolved. These are Primary classifications;
the runtime does not infer semantics from keywords or model severity/category.

Any contract/evidence question routes to replan; confirmed blockers route to
Primary preparation of a bounded rework packet; otherwise risk-routed Primary
review is next. Every disposition is retained inside immutable canonical
review.json. Missing, duplicate, unknown, stale or cross-run findings fail closed.
Host files are trusted Primary inputs, not authenticated identities; local models
cannot write them. Primary evidence is an assertion to audit, not machine proof.

Existing acceptance gates remain: a disposition does not waive deterministic
validation, required independent Reviewer pass or risk-routed Primary review.
Consequently dismissing a false positive does not automatically accept the run;
Primary may need contract revision/takeover under existing policy. No automatic
Coder dispatch or feature acceptance is introduced.

Experiment: high feature/unit/integration risk; contracts are rework-authority,
evidence-provenance, immutable-history, unchanged-acceptance. Freeze current live
baseline before implementation. Reuse the exact sixteen registered cases and
their actual reports from reviewer-evidence-1, without changing prompts, tests
or resampling judgments. Replay verifies routing, not improved model semantics.
Gate: all sixteen reports require Primary adjudication before rework; all six
real defects remain blocking; both explicit test gaps block; contradictory
contracts route to Primary; unsupported coverage finding never authorizes Coder.
Negative tests cover stale hashes, missing/duplicate/foreign findings, unresolved
evidence and legacy local-unit routing. Broader regression must pass. Preserve
all old results. Weekly used starts at 46%, stops at 50% or a clear stage decision.
No claim of zero model false positives, formal Coordinator release or savings.
