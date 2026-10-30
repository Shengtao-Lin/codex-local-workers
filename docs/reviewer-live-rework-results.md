# Controlled Reviewer-confirmed live rework

2026-10-10. Weekly used: 46% last observed, ceiling 50%. Stop reason: the
preregistered two-cell experiment has a checkable stage conclusion. No commit,
push, sibling-repository edits, model changes, prompt additions or new cases.

## Decision

The **controlled confirmed-finding repair chain passes 2/2**. This supports using
the new disposition boundary in supervised work. It does not release autonomous
Reviewer semantics, Coordinator, or the product gate; those remain HOLD.

Both cells come from the unchanged frozen sixteen-case corpus:

| Cell | Actual child repair | Outcome | Command window |
| --- | --- | --- | --- |
| display-default-b-r1 | Preserve present empty string/None; default only for absence | Coder validation, auto Reviewer and independent probe pass | 42.1 s |
| lookup-fallback-b-r1 | Catch only KeyError; propagate other errors unchanged | Coder validation, auto Reviewer and independent probe pass | 63.4 s |

Before confirmation, both inherited packets were mechanically rejected without
a model call. Primary dispositions bind the exact canonical historical Reviewer
report and confirmed finding ID. After confirmation, each actual Qwen Coder call
edited only the authorized source, ran fresh validation and handed off directly
to a fresh Muse Reviewer through local-unit. Both Reviewers read source/tests,
verified the inherited finding and configured checks, and returned
pass_to_primary with zero protocol errors. The first Reviewer independently
executed approved tests/checks; the second relied on the runtime's existing
executed evidence and did not claim additional execution.

Each Coder archive retains two validation attempts, including pre-edit evidence;
only current post-edit validation qualifies for handoff. Each final focused run
executed one test, with zero failures/skips, and passed Ruff format/lint. Primary
inspected the actual diffs and checked four display/nonmutation outcomes and
seven lookup value/error identity/single-call outcomes outside the protected
tests. Each child has an immutable accept record. Tests/config/contracts were
not weakened. The lookup Reviewer honestly noted untested boundary scenarios
without converting optional coverage into a fabricated production defect.

## Limits and retained evidence

The parent Coder archives are **synthetic benchmark archives**, copied into
separate experiment roots. Their historical Reviewer calls and findings are
real; the two new Coder and two new Reviewer calls are also real. Existing parent
Primary decisions are not edited: the copied experiment parents intentionally
omit the old Primary decision and receive a new boundary-bound disposition.
No real-project success credit, repeatability claim or savings claim follows.
The fixed sixteen-case semantic result remains 14/16, not 16/16.

Single-model residency and concurrency-one configurations were preserved; calls
were sequential. A supplemental lms ps diagnostic could not connect to its
daemon and timed out. That is retained as a diagnostic limitation, not a failed
worker call: the inference endpoint completed both chains. No independent live
residency inventory was obtained, so configuration is not presented as measured
GPU-residency proof.

Primary active time and cloud tokens remain unmeasured. Command windows include
the local-unit workflow, not a complete economic comparison. No claimed benefit
over direct Primary implementation.

Artifacts under benchmarks/work/capability-fit:

- reviewer-live-rework-runtime-1: frozen current runtime.
- reviewer-live-rework-1/registration.json: fixed cells and gate.
- reviewer-live-rework-1/registered-driver.py: exact pre-run driver retained;
  its hash matches registration. Afterwards only driver formatting, probe lint
  corrections and a post-run audit action were added; no model run was repeated.
- Each child root retains the copied parent, unconfirmed-entry rejection,
  Primary disposition, actual child archive, automatic review request/report,
  independent probe, command output/timing and immutable Primary acceptance.
- reviewer-live-rework-1/stage-decision.json: machine-checked stage result.
- benchmarks/work/reviewer-live-rework-regression-1.xml: disposition/recording/
  local-unit/policy regression, **35 passed, 24 subtests passed**. Previous full
  runtime regression remains **1014 passed, 137 subtests passed**; production
  runtime was not changed this round.

## Next step

Use the same boundary on one small real implementation unit: normal Coder,
automatic Reviewer, then Primary causal adjudication only if needed. Do not
manufacture a defect to force rework. Measure Primary preparation/adjudication/
review effort separately from local command time, against a comparable direct
Primary baseline, before claiming the local workers reduce coordination cost.
Do not resume prompt stacking or grow the fixed semantic gate to hide failures.
