---
name: trace-behavior
description: Trace source-level behavior through callers, guards, helpers and tests to answer a focused code question. Use for read-only behavioral investigation, not implementation or a formal acceptance review.
metadata:
  version: "0.1.0"
---

# Trace behavior

Answer the assigned behavior question using the mounted tools and approved
sources. This skill supplies a method; the task contract and host still control
scope, budget and the report format. Choose the useful investigation steps
yourself rather than producing a full repository inventory.

- Start from the relevant entry point and the input or condition in question.
  Follow guards, helper calls and the return or side effect far enough to
  establish the outcome. A matching symbol alone does not establish reachability.
- When behavior crosses a wrapper, alias or delegation boundary, identify what
  values and options cross it. Carry a rule across only when its conditions
  still hold. Distinguish an explicit statement from a source-backed deduction.
- Use callers and tests to resolve the particular ambiguity. A test declaration
  shows intended behavior; it is not an execution receipt. Distinguish a proven
  defect from a missing test or an unavailable dependency.
- If observed evidence disagrees, state the exact conflicting branches or
  assumptions. Search approved dependencies before declaring an information
  gap; narrow absence claims to what was actually inspected.

Deliver the answer, the short causal path that supports it, and any remaining
condition that changes the answer. Cite the decisive observed locations using
the current report interface. Stop once the question is resolved; additional
claims introduce additional verification work. Do not claim executed tests,
unobserved callers, or formal review acceptance.
