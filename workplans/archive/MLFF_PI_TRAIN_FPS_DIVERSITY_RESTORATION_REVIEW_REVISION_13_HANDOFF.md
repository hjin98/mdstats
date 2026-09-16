---
kind: independent-review-handoff
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 13
protocol_version: 6.3.0
status: active
review_date: 2026-09-16
branch: design/mlff-pi-train-fps-diversity-restoration
reviewed_candidate: c6fbe03c92f23a79123031922f338966e9c76c6b
reviewed_implementation: 9c41f44be32dd0e4f3869e6e48be4e85b9effce9
verdict: NO-PASS
highest_blocking_domain: D4
serious_challenge: false
---

# Revision 13 independent re-review handoff

## Verdict

**NO-PASS.** R12 successfully closes the REPAIR2 execution bottleneck and the post-`N_max` restart-cost blocker without changing D2 semantics or adding persistent repair state. The remaining blockers are B13-1 resource-routing/evidence closure and B13-2 canonical HAS representation.

No Serious Challenge is raised to D1, D2 or D3. The existing D4 resource-scope interface is sufficient; the production caller simply does not use it.

## Accepted from R12

Preserve as closed unless contradicted by new evidence:

- `_StateBatch` batched REPAIR2 execution over the existing MVIDX CSR/native row primitive;
- D2 §9 frontier, objective, tolerance, rank-inheritance and strict-improvement semantics;
- bitwise/scalar-oracle bounded equivalence at widths 1/2/4/16;
- removal of the REPAIR2 Python worker queue and one shared selector/repair execution-width decision;
- representative LTA REPAIR2 6,156 s -> 99 s with identical R11-correct build identity and repair trace;
- restart replay 6,610 s -> 100 s, no longer dominant, with no repair-side persistence added;
- every R11 correctness/ownership closure.

## Blocking finding B13-1

Production `_build_current_target_training_order()` resolves `_performance_resources(cfg)` but passes only `workers=resources.cpu_threads_budget` to `prepare_target_training_order()`. It does not pass `resource_scope`. R12's own representative telemetry therefore reports `ram_budget_bytes=None` and `queue_memory_budget_bytes=None`.

The R12 RAM evidence also samples current process RSS only before COVREF and after release. `after_rss - before_rss = -200 MiB` is not a peak measurement. A transient high allocation followed by release would be invisible to this metric. Queue-accounted memory does not cover every resident allocation and cannot substitute for the requested process-RSS peak.

This means Revision 12 section 4 / gate 6 was not satisfied: there is no governing stage RAM budget to compare against, and the actual in-stage process peak was not measured.

Required repair is a direct rewire: build one root `StageResourceScope` from the already-resolved campaign resources and pass it into `prepare_target_training_order`; use the existing scope propagation into COVREF/MVIDX/MVQUAL. No new memory manager or resource policy. Obtain the actual COVREF peak in the qualification harness and rerun current-scale evidence under the finite budget.

## Blocking finding B13-2

The R12 PEM table is substantively useful but not the canonical Protocol 6.3 HAS representation. Protocol 6.3 requires the exact interface:

```yaml
pem_basis:
  accepted_project_state: e72090e21cec5311ce87745b03603f8783cd15a7
  accepted_pem: hjin98/mdstats@e72090e21cec5311ce87745b03603f8783cd15a7:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: ...
```

Allowed dispositions are `APPLICABLE`, `NOT_APPLICABLE`, `REVIEW_REQUIRED`; `applied/rejected/review-required` are not the canonical schema. A byte hash may supplement but does not replace the recoverable accepted PEM publication route.

The accepted `main` basis remains `e72090e21cec5311ce87745b03603f8783cd15a7`, so no basis refresh is currently required.

## Independent HAS for this review

```yaml
pem_basis:
  accepted_project_state: e72090e21cec5311ce87745b03603f8783cd15a7
  accepted_pem: hjin98/mdstats@e72090e21cec5311ce87745b03603f8783cd15a7:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: R12 repaired the hot path by removing the Python queue and reusing the existing owner/substrate rather than adding a competing execution owner.
  - id: SP-002
    disposition: APPLICABLE
    reason: Target-order publication, checkpoint and currentness boundaries remain fail-closed authenticated state boundaries.
  - id: SP-003
    disposition: APPLICABLE
    reason: The restart decision deliberately preserves the existing authenticated durable boundaries instead of adding repair-side persistent state.
  - id: SP-004
    disposition: APPLICABLE
    reason: Current-envelope acceptance depends on the real-owner suite plus representative current LTA execution, not substitutes alone.
  - id: FF-001
    disposition: NOT_APPLICABLE
    reason: R12/R13 do not touch MACE model reconstruction, accelerator realization or checkpoint architecture identity.
  - id: FF-002
    disposition: APPLICABLE
    reason: Pre-adoption target-order checkpoints and post-N_max restart behavior are directly within the continuation-authority failure family surface.
  - id: FF-003
    disposition: APPLICABLE
    reason: Immutable publication and cleanup ownership remain material to the target-order durable boundary.
  - id: FF-004
    disposition: NOT_APPLICABLE
    reason: Its accepted semantic identity is P5 TRAIN/CUDA scheduler and residency control; target-order CPU RAM admission is outside that family and remains governed by current resource authority directly.
  - id: FF-005
    disposition: APPLICABLE
    reason: Downstream selection must continue consuming prepared target-order evidence without reconstructing preparation-owned science.
```

No PEM mutation is warranted by this review.

## Evidence assessment

Implementation-recorded evidence inspected:

- R12 current-scale fresh LTA build: REPAIR2 ~99 s versus R11 ~6,156 s; whole prepare ~32 min; scientific build identity unchanged;
- R12 current-scale interrupted/resumed LTA build: repair replay ~100 s; final build identity unchanged;
- 29 real-owner tests recorded green;
- installed-package native/reference equivalence recorded green;
- documentation/CLI-spec batch 12 passed / 0 failed;
- affected 55-file regression recorded 1,264 passed / 4 failed, with all four node IDs reproduced at the R12 basis and no new failures;
- no CI statuses are attached to `c6fbe03c...`.

These results were inspected as repository evidence; they were not independently re-executed in this review environment.

## Next gate

Implement `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_13.md`, then request another independent review. Close/archive only after the finite campaign RAM budget is actually routed through the existing target-order resource scope, actual in-stage COVREF peak is measured under that scope, scientific identity remains exact, the affected final regression is closed, and the durable HAS uses the canonical Protocol 6.3 interface.
