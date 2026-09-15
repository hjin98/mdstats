---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 6
protocol_version: 6.3.0
status: active
created_date: 2026-09-15
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
exact_revision_5_basis:
  commit: d06d98c70455714065035bc434bd949d5b71856d
  path: workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_5.md
  blob: 4274096c9a7878c27c934a4aa531b22e49324398
review_reopen: workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_REVISION_5_REVIEW_REOPEN.md
highest_affected_domain: D1
challenge_state: SERIOUS_CHALLENGE
human_ratification: stakeholder-restoration-direction-recorded-exact-d1-d2-reconciliation-still-required
---

# MLFF `pi_train` latest-path restoration — Revision 6

## 0. Authoritative revision-6 artifact

Revision 6 is intentionally a **two-document snapshot-complete composition**:

1. the exact immutable Revision-5 body at `hjin98/mdstats@d06d98c70455714065035bc434bd949d5b71856d:workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_5.md` (blob `4274096c9a7878c27c934a4aa531b22e49324398`); and
2. this Revision-6 closure document.

Both are mandatory. This document has precedence only where it explicitly strengthens or corrects Revision 5. All other Revision-5 requirements remain binding without reinterpretation. Revision 6 does **not** reopen the stakeholder decision, the exact historical recovery snapshot, the restore/prune map, D1/D2 restoration semantics, current one-`P_train` ownership, MVSTATE2/REPAIR2 rules, MVQUAL qualification, prepared-generation/CAS architecture, PEM/HAS, implementation gates, invalidation surface, or non-goals.

The Revision-5 independent review found six remaining acceptance/evidence gaps. Sections 1-6 below close them. The resulting canonical restoration remains:

```text
current P_train
 -> DATA6
 -> selector-relevant DATA7 fitted projection
 -> TargetCoveragePolicy + TargetCoverageReference
 -> FEAS1
 -> MVIDX1
 -> MVSEL2
 -> REPAIR2
 -> independent MVQUAL
 -> current P2 TargetTrainingOrder / pi_train
```

with MVSTATE2 as subordinate authenticated preparation-continuation state and current prepared-generation/CampaignStore owners retaining completed currentness.

---

## 1. Independent TargetCoverageReference oracle

Revision 5 restores `TargetCoveragePolicy`/`TargetCoverageReference` as the scientific reference/witness authority. That owner itself requires independent bounded verification before downstream agreement can count as evidence.

### 1.1 Required reference fixtures

Construct small explicit DATA6/DATA7 inputs for which expected reference families can be computed independently of production `target_coverage.py`. At minimum cover:

- structural family membership and canonical family order;
- witness identity/order;
- witness weights and normalization/mass accounting;
- fitted metric/scaling coordinates used by the coverage owner;
- radius/extent derivation where governed by the restored policy;
- condition support;
- structural event support;
- profile/environment support where the retained current profile policy enables them;
- any retained target-label-tail/foundation-residual family input after Gate R1's leakage/fit-domain reconciliation;
- missing/disabled optional family behavior.

The oracle may be a deliberately simple bounded mathematical/reference implementation or hand-computable fixture. It shall not import the production coverage-reference builder or copy candidate-produced serialized values into the expected result.

### 1.2 Required negative cases

Acceptance must reject at least:

- changed family order under otherwise equal values;
- changed witness order where order is identity-bearing;
- one altered weight;
- one altered radius/extent;
- one missing required support family;
- stale fitted-metric/provider ancestry.

A downstream MVIDX/selector/MVQUAL stack that is self-consistent with a wrong reference object cannot pass this owner.

---

## 2. Independent MVIDX1 exact-neighborhood oracle

MVIDX1 defines the exact scientific sparse relation consumed by FEAS/MVSEL2/REPAIR2/MVQUAL. Therefore selector/qualifier agreement is insufficient proof of MVIDX correctness.

### 2.1 Direct relation oracle

For bounded fixtures, recompute adjacency directly from the accepted mathematical relation without importing the production MVIDX builder or consuming its sparse arrays:

```text
A[m,w,c] = 1 iff ||D_m (x_w^(m) - x_c^(m))||_2 <= r_w^(m)
```

Compare exact candidate-to-witness incidence, canonical ordering, typed cardinalities and bound identities against the production MVIDX artifact.

Required cases include:

1. one witness strictly inside the radius;
2. one strictly outside;
3. exact equality at the radius boundary, proving inclusive `<=` semantics;
4. nonuniform witness radii where the recovered policy permits them;
5. transformed/scaled coordinates with more than one active dimension;
6. empty candidate rows;
7. duplicate/degenerate coordinates;
8. multiple families with different dimensions/scales;
9. file-backed serialize/reload identity equality.

### 2.2 Common-mode counterfactual

Start from one valid fixture, perturb exactly one sparse edge while updating all downstream selector/repair/qualification consumers to use that same wrong index. The independent MVIDX oracle must still fail. This is the required discriminating proof against a self-consistent common-mode sparse-index defect.

### 2.3 Exact sparse-content validation

MVIDX publication/reload acceptance shall verify array dtype, shape/cardinality, byte/content digest, candidate/reference/family ancestry and schema semantic version. A correct pathname or manifest entry with wrong bytes is a hard failure.

---

## 3. Explicit numerical-boundary falsification

The recovered method makes exact finite-precision/tie rules part of D2. Add dedicated fixtures rather than relying on ordinary random/easy cases.

### 3.1 MVSEL2 contender boundaries

For every inclusive best-relative filter, test candidate values:

```text
best
best - epsilon
next representable value above/below the acceptance boundary where practical
best - epsilon - delta
```

Prove `value >= best - epsilon` behavior and stable UID use only after every earlier ranking stage remains tied.

### 3.2 Bottleneck family ties

Construct at least two families whose coverage ratios are tied exactly or within accepted epsilon. Prove that the **first canonical minimum-coverage family** is selected as the bottleneck family and that no extra candidate-ranking stage is introduced.

### 3.3 Phase-B lazy bounds

Exercise outward-rounded conservative upper bounds at/near the certification boundary. The lazy path must either refresh or certify exactly as the full-forward oracle requires. No stale upper bound may exclude a true contender.

### 3.4 Optimized/native reductions

Where native/OpenMP or vector kernels are shipped, use adversarial near-tie CSR rows to compare against the exact reference reduction. Worker count and execution backend cannot change winner/order. A backend mismatch reopens/fails the backend; tolerance may not be widened to bless it.

---

## 4. External selector-artifact retention and storage lifecycle

Revision 5 allows large MVIDX/reference artifacts to remain authenticated file-backed objects. Close their lifecycle under the **existing storage/prepared-generation owners**; do not introduce an MVSEL-specific garbage collector.

Required real-owner tests:

1. an adopted prepared generation keeps every referenced selector object/array protected and reloadable;
2. constructing or adopting generation `g+1` cannot overwrite/delete a selector object still referenced by current/recoverable generation `g`;
3. content-identical objects may be shared by content address across generations and remain protected while any live/protected generation references them;
4. cleanup may reclaim an unreachable failed/stale pre-adoption selector object only after proving no protected generation references it;
5. missing, truncated or wrong-hash external selector bytes cause authenticated prepared-load failure before manual selection, training or CV;
6. a failed/stale expensive build that never wins CAS remains inert and cannot alter the current generation;
7. storage accounting/retention includes selector external artifacts so resource reporting does not hide their real footprint.

These tests must execute the current storage/prepared-generation owner boundary rather than a mock cleanup helper.

---

## 5. Native/backend build and packaging closure

The restoration may recover historically qualified native/OpenMP sparse kernels, but current packaging must determine whether they are actually shipped.

### 5.1 If native/compiled backend is retained

Final D4 acceptance requires:

- current source/build metadata includes the required native source/extension and no deleted historical packaging assumption;
- a clean current package/install build succeeds;
- importing the installed package exposes the intended production backend;
- backend availability and selected fallback are observable enough to diagnose qualification;
- installed native/OpenMP execution is compared against the installed/reference exact implementation on the required equivalence fixtures;
- package/wheel/source distribution contains every required runtime artifact and no stale historical selector entrypoint is accidentally exported.

### 5.2 If native backend is not retained

Record an explicit `DROP/REFERENCE_ONLY` disposition for the historical native path and prove that the retained exact Python/vector implementation satisfies current representative-scale CPU/RAM/runtime requirements. Do not silently fall back and then cite historical native performance as current qualification.

### 5.3 Semantic fallback rule

Backend availability may change performance only. It may not change scientific ordering, coverage, repair or qualification semantics. An unavailable optional backend must select an exact supported fallback or fail with an actionable execution/configuration error; it cannot weaken the method.

---

## 6. Immutable oracle provenance and anti-self-golden rule

Historical-equivalence fixtures are useful only if their expected outputs are independently recoverable.

For every material historical fixture used to claim unchanged semantics, record one of:

```text
immutable expected artifact at recovery-snapshot identity
OR
independent reference procedure + immutable input fixture
OR
hand/analytical expected result for a bounded case
```

A candidate-produced golden file is not an independent oracle merely because it is committed before the test runs. If a new golden must be generated because the historical expected artifact is unavailable, its first generation remains `REVIEW_REQUIRED` until independently justified against the recovered spec/reference implementation.

Group historical reference/kernel outputs that share the same underlying implementation into one provenance cluster for evidence-strength interpretation; do not count them as independent corroboration simply because several tests consume them.

---

## 7. Amend Revision-5 acceptance obligations

Revision 5 Section 18 is strengthened by the following mandatory evidence. These are additive and cannot be waived by a broad green regression suite:

- TargetCoverageReference independent fixtures and negative perturbations from Section 1;
- MVIDX direct-neighborhood oracle and wrong-edge common-mode counterfactual from Section 2;
- exact contender/radius/lazy-bound/near-tie numerical tests from Section 3;
- real prepared/storage retention and corruption lifecycle from Section 4;
- clean installed-package/backend evidence from Section 5;
- immutable oracle provenance from Section 6.

Revision 5 Section 22 pass criteria gain the following requirements:

20. TargetCoverageReference family/weight/radius/support semantics pass an independent bounded oracle;
21. MVIDX exact adjacency passes an independent direct mathematical oracle, including radius-boundary semantics and a wrong-edge common-mode counterfactual;
22. FP64/tolerance/canonical-order/lazy-certification boundary cases pass exact reference comparisons;
23. external selector artifacts survive/reclaim exactly under existing protected-generation/storage ownership and fail closed on corruption;
24. any restored compiled/native backend passes current clean-build/install/package and installed-reference equivalence, or is explicitly omitted with a currently qualified exact fallback;
25. material historical-equivalence expected values have immutable/independent provenance and are not candidate-self-generated goldens.

---

## 8. Implementation-sequence impact

No earlier gate is weakened. Add these closure points:

- **R3:** establish independent TargetCoverageReference fixtures before treating restored reference construction as closed;
- **R4:** establish the direct MVIDX mathematical oracle before dependent selector work can use MVIDX evidence as trusted input;
- **R5:** run explicit tolerance/bottleneck/lazy-bound boundary fixtures against reference and optimized paths;
- **R8:** run real external-artifact retention/corruption/CAS lifecycle tests;
- **R9:** run clean install/package/backend qualification plus oracle-provenance review as part of final assembled acceptance.

A failure in Sections 1-3 reopens D2 or its concretization depending on whether the accepted method or implementation is at fault. A failure in Sections 4-5 is D3/D4 unless it reveals an impossible D2 resource contract.

---

## 9. Final Revision-6 pass condition

Revision 6 is ready for D1/D2 Gate R1 implementation only when the exact Revision-5 body plus this closure document are treated together. Neither document alone is the active plan.

The current product method remains under **SERIOUS CHALLENGE** until the restored method passes R1 acceptance and downstream implementation/qualification. This workplan itself does not self-ratify D1/D2.
