# Revision-5 independent workplan review — NO PASS / reopen

Date: 2026-09-15
Workplan: `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_5.md`
Disposition: **NO PASS AS FINAL WORKPLAN; reopen for bounded evidence-architecture repairs**

## 1. Review method

This review reconstructs the current P1/P2/prepared-generation owners and the exact historical recovery snapshot independently of the Revision-5 rationale. It treats the historical selector mechanism as evidence/concretization, the historical current specifications at `hjin98/mdstats@3937881ef00222e80845aa81f5471d89a4a7736c` as the recovery-period normative owners, and current D1/D2 as the owners that must accept the restored meaning.

Revision 5 successfully closes the prior semantic/ownership gaps: exact pre-deletion recovery identity, selector-relevant DATA7 projection, explicit TargetCoverageReference ownership, correct MVSEL2 ranking, family-threshold reconciliation, post-repair state reconstruction, P2 qualification projection, stale-generation rejection, CAS currentness, resource ownership, and PEM/HAS.

The remaining blockers are narrower but real because they permit a self-consistent wrong sparse relation or an operationally unusable restored package to pass the stated acceptance suite.

## 2. B1 — MVIDX1 lacks an independent relation oracle

**Owner:** D2 evidence design / D4 acceptance.

MVSEL2, REPAIR2 and MVQUAL all consume the authenticated MVIDX1 sparse relation. Revision 5 requires selector/reference equality and independent MVQUAL recomputation, but those checks can all agree if MVIDX itself encoded the wrong adjacency.

The scientific relation is the exact radius test

```text
A[m,w,c] = 1 iff ||D_m (x_w^(m) - x_c^(m))||_2 <= r_w^(m)
```

so acceptance needs a bounded independent direct-neighborhood oracle that does **not** consume production MVIDX arrays or the production sparse builder. It must cover at least:

- exact inside/outside witnesses;
- equality at the radius boundary (`<=` semantics);
- canonical candidate/witness/family ordering;
- nonuniform witness radii/weights where supported;
- transformed/scaled coordinates;
- empty rows and duplicate/degenerate coordinates;
- file-backed serialization/reload equality.

A known-broken counterfactual that perturbs one sparse edge must be rejected even if selector and qualifier consume the same perturbed index.

## 3. B2 — TargetCoverageReference construction needs an oracle distinct from MVIDX consumers

**Owner:** D1/D2 evidence design.

Revision 5 correctly restores `TargetCoveragePolicy`/`TargetCoverageReference`, but its tests begin largely downstream. The reference/witness authority owns family membership, weights, radii/extents and support facts. A wrong reference authority can therefore make FEAS1, MVIDX1, selector and MVQUAL coherently wrong.

Add bounded fixtures that independently reconstruct expected reference families/weights/radii/support from simple DATA6/DATA7 inputs and compare the published coverage-reference identity/content. Include a negative fixture where family order or one weight/radius is altered while downstream sparse rows remain otherwise self-consistent.

## 4. B3 — exact numeric boundary/equivalence tests are incomplete

**Owner:** D2.

The recovered method makes FP64 reduction order, canonical family ordering, `1e-14` inclusive contender filters, and exact radius inclusion part of numerical identity. Revision 5 states these rules but does not require explicit boundary fixtures.

Add exact tests for:

- contender values at `best - epsilon`, just inside, and just outside;
- canonical first-bottleneck-family selection when ratios tie within epsilon;
- outward-rounded Phase-B upper bounds at the acceptance boundary;
- reference vs optimized/native reductions on adversarial near-tie rows;
- stable UID only after every prior exact stage remains tied.

Tolerance may not be widened because an optimized backend disagrees.

## 5. B4 — external selector-artifact retention/GC is specified but not falsified

**Owner:** D3 storage/persistence acceptance.

Revision 5 correctly allows product-scale MVIDX arrays to remain external/file-backed and says they must be protected while referenced, but the acceptance suite lacks a real lifecycle test.

Add failure/lifecycle evidence proving:

- an adopted prepared generation keeps every referenced selector object/array reachable and unreclaimed;
- constructing or adopting a later generation cannot overwrite/delete objects still referenced by an older current/recoverable generation;
- cleanup/retention can reclaim only objects no protected generation references;
- a missing/truncated/wrong-hash external array causes authenticated load failure before downstream selection/training;
- failed/stale pre-adoption builds remain inert and may be reclaimed without affecting the current generation.

Reuse the existing storage owner; do not create an MVSEL-specific cleanup engine.

## 6. B5 — restored native/compiled backend packaging is not in assembled acceptance

**Owner:** D4 packaging/runtime.

Revision 5 permits restoring the historically qualified native/OpenMP kernels when the current build/runtime supports them. If restored, acceptance must exercise the actual current package/install boundary, not merely an in-tree import.

Require:

- current build/package metadata includes the restored native sources/extensions where selected;
- clean install/build imports the production backend;
- backend availability/fallback reporting is explicit;
- reference equality is run against the installed backend;
- absence of a compiled backend cannot silently change selector semantics; an exact supported fallback may change performance only.

If the final implementation deliberately chooses the exact Python/vector fallback and does not ship native code, record that disposition and qualify current-scale CPU/RAM/runtime accordingly.

## 7. B6 — historical fixture provenance must be immutable and independent of candidate output

**Owner:** evidence lifecycle.

Revision 5 says fixtures must be provenance-bound and not regenerated from the candidate. Tighten this into an acceptance artifact requirement: each historical-equivalence fixture names its immutable recovery-snapshot source/expected-output identity or an independently generated reference procedure. Candidate-produced golden files cannot become the expected oracle in the same cycle without independent adjudication.

## 8. Challenge pass

No new Serious Challenge to the restoration direction was found. The remaining defects are evidence/acceptance inadequacies in the workplan, not evidence that MVSEL2 should not be restored.

The current target-order method itself remains under the already-recorded Serious Challenge until the restored D1/D2 method is accepted and implemented.

## 9. Required repair

Supersede Revision 5 with one bounded closure revision that preserves all Revision-5 semantic decisions and adds B1-B6 as mandatory acceptance obligations. Then re-review the composed plan independently.

## 10. Disposition

**NO PASS AS FINAL WORKPLAN.**

Revision 5 is semantically strong but still permits common-mode MVIDX/reference defects and an unqualified packaging/artifact-lifecycle realization to escape. These gaps must close before implementation handoff is treated as complete.
