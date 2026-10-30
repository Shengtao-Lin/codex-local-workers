---
name: source-backed-handoff
description: Complete Primary-delegated investigation or implementation tasks with bounded autonomous recovery and a concise, source-backed handoff. Use when reporting work to a supervising Primary, not for unrelated conversation.
metadata:
  version: "0.1.0"
---

# Source-backed handoff

Work toward the assigned outcome, not a predetermined sequence of tool calls.
Use the current task contract, mounted tools and host state as the authority for
scope, output schema, resource limits and completion. This skill supplies working
methods; it grants no permissions and does not replace the current tool schemas.

## Investigate and act autonomously

- Choose useful reads, searches, edits and checks within the approved task. Do
  not ask Primary to approve every ordinary step. Use enough evidence to resolve
  the question; an exhaustive inventory is not a better answer.
- Follow relevant guards, helpers and callers before attributing an outcome to
  a particular branch. A matching line is a starting point, not proof that the
  execution reaches it. Distinguish construction-time validation from later use.
- Missing information is not evidence of a defect. If the needed source is in
  scope, inspect it. Otherwise state the precise missing evidence and its effect
  on the answer, or use the mounted blocked/request mechanism. Do not invent a
  tool, permission or dependency definition.
- For implementation, make a cohesive in-scope change, obtain the required
  current checks through the available mechanism, and repair ordinary failures
  while credits remain. If the host drives checks automatically, use that result
  rather than inventing an explicit validation or completion action.

## Recover without losing the task

Use the latest host state: original goal and constraints, current source version,
effective changes, latest check results and remaining resources. A continuation
does not reset permissions, budget or previously observed failures.

After failure, identify what changed in the evidence. Repair the concrete current
failure or obtain a genuinely missing fact; do not repeat an unchanged proposal,
unchanged review or already-answered search in hopes of a different result. Keep
resolved failures separate from remaining failures and new regressions. Fewer
failures alone do not establish correctness.

Leave room to deliver. When the remaining allowance is needed for the final
report, stop optional exploration and report the supported answer and limits.
For a rejected report, use the host's exact field errors to correct the complete
submission within any allowed recovery opportunity. Do not claim success because
only its formatting was corrected. Stop on the host's safety or resource limits.

## Build a compact, checkable handoff

Use the current mounted report tool or requested deliverable format. Do not add
an alternative schema or copy example fields absent from the current interface.

Include what Primary needs to judge the result:

- **Outcome:** the answer or actual changes, with the important behavior and
  remaining limits. An investigation can be answered while finding problems;
  that is different from implementation acceptance.
- **Evidence:** relevant observed source locations, actual diff and current
  host check receipts. A test assertion read from source is a test declaration,
  not an executed pass. Bind claims to the version actually observed or checked.
- **Findings:** concrete consequences supported by evidence. Distinguish a
  demonstrated defect from a test gap, conditional concern or information gap;
  do not mark an ordinary unknown as a severe code defect.
- **Unknowns:** what could not be established, why, and whether it prevents a
  complete answer. Keep absence claims limited to the searched/read scope.

Use a small set of strong citations, not a transcript of every read. Each finding
must point to evidence supporting that finding, not merely another valid quote
from the same file. If the interface uses an evidence array and numeric indices,
check the mapping after reordering or removing entries. Use exact quotes only
when requested; use host-bound quotes when the interface supplies them.

Treat displayed size/item limits as upper bounds, not targets. Remove repeated
explanations and unused evidence before compressing essential qualifications.
Do not silently drop unresolved findings or claim checks that were not run.
Primary independently accepts the work; a legal report or local pass is not that
acceptance.

## Two distinctions that change the answer

**Reachability:** a source line calls `send()`, but an earlier disabled-mode guard
returns first. Say that the enabled path sends; do not claim every invocation
sends merely because the call exists. Inspect the relevant guard and cite the
evidence that supports the conditional statement.

**Evidence strength:** an observed test asserts that a missing item raises
`LookupError`. Report that this test declares the expected exception. Do not
claim it passed, proves all error handling, or establishes an unobserved parent
class. Put unavailable runtime or dependency evidence in unknowns.
