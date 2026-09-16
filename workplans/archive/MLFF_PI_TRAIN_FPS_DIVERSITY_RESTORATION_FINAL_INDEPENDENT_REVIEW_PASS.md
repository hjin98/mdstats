---
kind: independent-assembled-candidate-review
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
protocol_version: 6.3.0
status: PASS
review_date: 2026-09-16
branch: design/mlff-pi-train-fps-diversity-restoration
reviewed_candidate: caab58e87db281f90181da1e43a5ba73c231cb85
r14_implementation_commit: bc733983df328b9e5c285878443b2017e55e5469
accepted_project_basis: e72090e21cec5311ce87745b03603f8783cd15a7
highest_affected_domain: D4
serious_challenge: false
---

# MLFF `pi_train` restoration — final independent assembled-candidate review

## Verdict

**PASS.** No genuinely blocking issue remains in the governed restoration scope.
The accepted scoped D1/D2/D3 authority remains coherent and unchanged. Revision
14 closes the final D4 resource-scope defect without changing scientific or
numerical semantics and without adding a competing resource, persistence,
currentness, cleanup, selector, repair, or compatibility owner.

## Revision-14 gate disposition

1. **Prior closures preserved — PASS.** The six R11 correctness/ownership
   repairs, R12 exact REPAIR2 performance/restart closure, and R13 root resource
   routing/COVREF peak-memory/canonical-HAS closure remain intact.
2. **Root resource authority reaches FEAS1/NEIGHBOR1 — PASS.** The existing root
   target-order `StageResourceScope` now supplies the existing
   `build_target_coverage_geometry(..., resource_scope=...)` interface with the
   same CPU and finite RAM budget.
3. **Native-thread scope ownership — PASS.** FEAS1 no longer switches
   `DeterministicWorkQueue.manage_resource_scope` according to scope provenance;
   the queue applies its declared stage limits through the existing default.
4. **Real-owner finite-budget admission — PASS.** Focused real-owner evidence
   exercises inherited finite RAM, queue accounting/backpressure, exact scope
   fields, small-budget fail-closed admission, and serial/parallel exactness.
5. **Representative resource envelope — PASS.** On the same LTA substrate used
   by R11-R13, FEAS1/NEIGHBOR1 ran at 28 admitted CPU lanes under a finite
   41,804,365,824-byte stage budget. External `/proc` sampling measured an
   in-stage process peak of approximately 32.91 GiB, below the governing budget;
   the whole prepare completed successfully.
6. **Scientific identity exactness — PASS.** The final build remains
   `b8d75b6a1857`; exact `P_train`, FEAS terminal result, Phase-A/B boundary,
   49-swap REPAIR2 trace, complete order and MVQUAL-qualified configured sizes
   remain unchanged.
7. **Affected regression — PASS.** The recorded final 52-file affected batch is
   1,275 passed / 4 failed; the same four failures reproduce at the pre-R14
   basis, so the new-failure delta is zero. The failures are preserved rather
   than hidden with skips/xfails.
8. **Ownership/topology — PASS.** No second resource manager, RAM policy,
   selector, repair algorithm, persistent repair cache, checkpoint/currentness
   store, cleanup owner, sparse authority, or compatibility path was introduced.
9. **Protocol-6.3 project-memory closure — PASS.** The canonical session-local
   `pem_basis` + `has` basis remains applicable against accepted project state
   `e72090e21cec5311ce87745b03603f8783cd15a7`; no PEM mutation is warranted.

## Resource-accounting observation

FEAS1 queue-accounted memory is materially smaller than total process RSS during
the representative run. This is **not a blocking admission defect** in the
accepted architecture: inspection of the actual NEIGHBOR1 construction shows
that the dominant result is intentionally file-backed/OOC via staged and packed
memmaps, while queue task/persistent/finalization anonymous working memory is
bounded and admitted. The accepted D3 execution architecture explicitly permits
large NEIGHBOR1/MVIDX payloads to be file-backed/OOC while anonymous working and
finalization memory remain bounded. The directly measured total process peak is
also inside the finite inherited stage budget. This remains a useful
observability/ledger-coverage maintenance topic, not a reason to manufacture a
new resource owner in this restoration.

## Evidence applicability and limitations

The review independently inspected the assembled code, authority, workplan,
resource-flow implementation, OOC representation, representative evidence, HAS,
and affected-regression attribution. The recorded local test and representative
LTA executions were produced by the implementation/qualification environment;
they were **not independently re-executed by this reviewer environment**. No CI
statuses are attached to the reviewed candidate. Those facts limit the provenance
of the execution observations but do not make them stale or inapplicable to this
candidate; code inspection and basis-attribution checks found no contradictory
evidence.

The repository is not claimed globally green: baseline-equal/environmental test
failures remain outside this bounded restoration result.

## Closeout

The restoration workplan is accepted complete and may be archived. Current
scientific/numerical/software authority remains in the canonical D1/D2/D3
method/architecture documents and the accepted D4 implementation, not in this
review record or archived workplan lineage.

Final production-scale GPU qualification for the overall MLFF release remains
deferred to the final complete release package on the stakeholder machine, as
previously governed; the restored target-order path itself does not require GPU
execution.
