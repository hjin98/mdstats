# Implementation workplans

`workplans/` contains temporary engineering coordination artifacts for proposed changes to mdstats. It is not current product authority and is intentionally excluded from source and wheel distributions.

Authority model:

```text
architecture -> accepted current structure
specification -> accepted current behavior
workplan -> proposed transition and developer implementation gates
history -> completed chronology
audits / qualification evidence -> correctness evidence
benchmarks -> performance evidence
guides / runbooks -> stable operational usage
```

A workplan may reference current architecture and specifications, but it must not override them before the corresponding implementation is accepted. Runtime/product gates that are part of current software behavior remain in architecture/specifications; developer gates that organize implementation belong here.

Use `TEMPLATE.md` for new workplans. Active plans live in `active/`. Implementation-to-qualification handoff contracts associated with an active plan also live in `active/` so that the workplan, candidate-bound handoff, and lifecycle coordination remain colocated; qualification reports and execution evidence remain in their dedicated evidence locations. After a transition is accepted, move durable current-state consequences into architecture/specifications, move chronology/evidence to their permanent homes, then archive the plan and its retained coordination lineage in `archive/` when useful.
