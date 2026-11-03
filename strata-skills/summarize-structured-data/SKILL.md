---
name: summarize-structured-data
description: Summarize a bounded table or structured dataset with explicit filters, missing-value handling, units and checkable arithmetic. Use for read-only data questions whose required records are available within the task tools and budget.
metadata:
  version: "0.1.0"
---

# Summarize structured data

Produce the requested summary from approved observations. Use the task's tools,
scope and output format; this skill does not provide execution or filesystem
permissions. Choose a direct method suited to the data size and available tools.

- Establish the relevant columns, units, population and filter conditions.
  Distinguish zero, missing, malformed and excluded values. Do not silently drop
  duplicates or reinterpret an identifier as a numeric measurement.
- For counts and aggregates, keep track of included, excluded and missing
  records. State the denominator for a rate or mean, the grouping used, and the
  rounding applied. Check that group counts and totals reconcile where relevant.
- Separate a directly observed value from a computed result or an inference.
  A computed result needs its inputs, inclusion rule and enough arithmetic for
  Primary to check it, not a citation that merely repeats the column name.
- A partial read cannot establish a whole-dataset maximum, count or absence.
  Obtain the remaining necessary records with approved tools, or clearly limit
  the claim. If a reliable result needs an unavailable operation or more data
  than the budget permits, report the concrete gap instead of estimating it.

Deliver the requested values and their interpretation, with only the assumptions
needed to reproduce them. State how missing values affect the result and the
actual data coverage. Use exact arithmetic where practical; do not invent script
execution, precision or statistical conclusions unsupported by the observations.
