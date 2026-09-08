# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

The current MLFF implementation authority is:

- `workplans/active/MLFF_TARGET_SIZE_INTEGRATION_CLOSURE_REPAIR_WORKPLAN.md`

Independent Software Design review of candidate `2199bbd4bffc3a950a6b63b010c48e32c829c5b3` is **NO-PASS** and the same plan remains open. The executable implementation is `07bdd51f6857eb052aa05e7e23a1ec89a53e0e6c`; the reviewed child only regenerates affected PDFs.

The accepted scientific architecture remains intact. Static review accepts the narrow manual prepared/P2 dependency and the current-side P5A6 `frozen_entries` rewire. Remaining blocking closure work is:

1. remove the selection-view dependency on an older non-authoritative `target-size-state.json`; selection-only refresh must project committed state rather than copy stale diagnostic fields;
2. close R2 through a real completed auto-diagnostic -> poisoned-P3/exposure -> manual-selection integration, not a fabricated diagnostic state proxy;
3. strengthen the existing scalar-state AST guard so the escaped defect family is detected under a simple local state alias while legitimate per-size `.frozen` use remains allowed;
4. reconcile remaining scalar contradictions in current normative docs, especially the cross-cutting stage-plan spec, dependency graph summaries, root README, and current GPU/workstation runbook;
5. execute and record final affected regression/integration plus `python qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py` on the final candidate. The only branch CI evidence available at review time was documentation-PDF generation.

Repair policy remains dependency reduction and current-owner rewiring, not additive wrappers, caches, duplicate state, compatibility machinery, or a new view authority.

Previous completed workplans remain archived as historical evidence and are not current implementation authority.

Full long-running real-data/GPU/CuEq/LAMMPS production qualification remains separate and deferred to the established final-release/user-machine qualification stage.
