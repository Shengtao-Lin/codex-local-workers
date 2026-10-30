# Controlled Coordinator pilot: prerequisite regression

## Decision

**HOLD.** The fresh Explorer call is protocol-valid but incomplete. Coordinator,
Coder and Reviewer were not dispatched. This is a prerequisite failure, not a
Coordinator model failure and not a new E/C/R chain success.

Evidence is retained under
`benchmarks/work/capability-fit/coordinator-completion-pilot-1/`:
`registration.json`, `manifest.json`, `primary-stage-decision-1.json`, and the
isolated root's immutable Explorer report and Primary adjudication.

## What the new run establishes

The existing qualified async-receipt fixture was reconstructed in a fresh root;
initial source/test hashes match the qualified corpus. The frozen runtime and
role settings were retained; only that root enabled Coordinator. The global
configuration remains unchanged and disabled. No production source was edited.

Explorer read all four files and returned real entry, receipt, collector and
collector-order test references. However, the question also requested the public
round-trip integration test. Both test-file references selected the collector
test at lines 7–19, one as `test` and one as `caller`; neither selected
`test_receipt_roundtrip` at lines 36–47. Reading the full test file did not make
the final answer complete. The report declared no uncertainty. The initial
Primary adjudication's line hint was 35–46; the appended erratum corrects it to
36–47 without replacing the historical adjudication or changing the verdict.

There were zero protocol errors, ten actions, no cache hit and no infrastructure
failure. The final request reported 2,842 input tokens against 32,768 context.
This is not evidence of context exhaustion. The earlier four complete answers
remain valid history; including this fresh run gives this prompt candidate four
strictly complete answers in five calls. It does not establish stable completion.

## Design implication and next bounded experiment

The runtime correctly proves that cited lines were read and unchanged. Required
paths and an assertion citation do not prove that every requested question was
answered, especially when two obligations live in the same file. Its explicit
`semantic_verdict: not_evaluated` must not become dispatch approval by implication.

Do not add another generic reminder or rerun unchanged until green. For known
locations, first use the **existing** required-source-anchor mechanism, testing
that an omitted integration anchor is rejected and that an actual read citation
can repair it. This is an assisted localization arm, not unaided discovery; keep
the current failure in the denominator. For genuinely unknown locations, define
an explicit completion contract and evaluate it on holdouts before claiming a
generic solution. Primary semantic adjudication remains necessary meanwhile.

The registered pilot driver is experimental and does not itself enforce Primary
semantic adjudication before `run`. Do not resume it after this HOLD; a successor
must enforce that check before any Coordinator or worker call. This is separate
from the product's existing structural citation and bounded-dispatch gates.

Weekly used was 37% at the last check, below the 40% ceiling. This phase stopped
on a new, auditable prerequisite regression, not budget exhaustion. No commit,
push, sibling-repository modification or historical-result replacement occurred.
