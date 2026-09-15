---
kind: R1-gate-status
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
workplan_revision: 8
gate: R1
protocol_version: 6.3.0
status: PROPOSED_D1_D2_REPAIRED_AWAITING_INDEPENDENT_REREVIEW
accepted_current_authority_changed: false
implementation_authorized: false
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
recovery_snapshot: 3937881ef00222e80845aa81f5471d89a4a7736c
active_handoff: MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_INDEPENDENT_REREVIEW_HANDOFF_2.md
---

# R1 status — D1/D2 reconstruction repaired; independent re-review pending

## Disposition

The latest independent R1 D1/D2 review returned **NO-PASS** for one remaining obligation-reconciliation defect while leaving the governing Revision-8 workplan itself PASS. That defect has now been repaired in proposed R1 evidence; it has **not** been self-approved.

The effective repaired R1 evidence set is:

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_METHOD_AMENDMENT.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D2_METHOD_AMENDMENT.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_D2_RECONSTRUCTION_EVIDENCE.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_EXACT_RECONSTRUCTION_LEDGER.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_D2_REPAIR_ADDENDUM.md` — controlling repair text wherever earlier proposed R1 text conflicts;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_INDEPENDENT_REREVIEW_HANDOFF_2.md` — active independent re-review handoff.

Prior handoffs remain historical review evidence only.

## Latest repaired blocker — support locus versus requirement strength

The prior repair incorrectly treated a larger explicit current P2 minimum on the same automatic restored support locus as a contradiction. That would have rejected valid current policy, for example:

```text
automatic condition=A minimum 1
explicit condition_id=A minimum 2
```

The proposed authority now separates:

```text
L(o) = scientific support-locus identity
A(o) = exact current-P_train candidate incidence
k(o) = required minimum
```

`k(o)` is not part of support-locus identity. Same-locus records are admissible only when their exact incidence agrees, and their one canonical requirement is:

```text
k_canonical(L) = max k(o).
```

Thus a stronger current explicit requirement subsumes the weaker automatic baseline rather than failing preparation or receiving duplicate hard-gain votes. Different scientific loci remain distinct even when incidence overlaps or is identical. True same-locus incidence/applicability contradictions and source-ID semantic collisions still fail closed.

Mandatory falsification now includes alias invariance, weaker/stronger same-locus composition, automatic-minimum-one plus explicit-minimum-k equivalence, source-ID rename/collision, same-locus incidence conflict, and different-locus identical-incidence cases.

## Previously repaired blockers retained

### 1. Lossless reconstruction ledger

The immutable recovery ledger remains bound directly to `3937881ef00222e80845aa81f5471d89a4a7736c`, with DATA6/DATA7 input mapping, TargetCoverage/FEAS1/NEIGHBOR1/MVIDX1/MVSEL2/REPAIR2/MVQUAL field dispositions, discrepancy adjudications and family-threshold census. Its older obligation-minimum wording is subordinate to the controlling repair addendum.

### 2. DATA7 / TargetCoverageReference ownership

For the target-order subchain, `TargetCoverageReference` remains the sole fitted selector numerical owner. DATA7 retains logical lineage/input semantics without introducing a second fitted selector metric/scaler/PCA/reference owner.

### 3. Certified-lazy MVSEL2 numerical contract

D2 retains exact all-candidate Phase-B rebase, outward conservative bounds, stale-score refresh and monotonicity guard, exact contender certification using `B_max < R_best - 1e-14`, full-forward per-rank oracle/fallback, and mandatory lazy-state invalidation/reconstruction after accepted REPAIR2 swaps.

### 4. Named-family threshold adjudication

The recovered instantiated baseline remains one scalar `coverage_threshold = 0.95`; no active named-family threshold policy map was found. The historical override sentence remains dormant/uninstantiated capability requiring a future accepted D1/D2 change before use.

## Repaired proposed chain

```text
exact current P_train
 -> authenticated selector input lineage
 -> sole fitted TargetCoverageReference on exact P_train
 -> FEAS1
 -> exact NEIGHBOR1 / canonicalized MVIDX1 obligations
 -> exact MVSEL2 + certified-lazy equivalent execution
 -> configured-shell REPAIR2
 -> post-repair exact state reconstruction
 -> independent current-ladder MVQUAL
 -> same-MVSEL2 continuation to complete TargetTrainingOrder
```

Historical label-domain/fold target-size fan-out and fixed-eight/fixed-16384 target-size topology remain retired. Current `pi_eval/M1/M2/M3`, P3 target-size training/evaluation/reducer, post-selection CV, replay and production remain unchanged.

## Authority state

**No accepted D1/D2 authority has changed.**

The accepted-current method papers at `e72090e21cec5311ce87745b03603f8783cd15a7` remain authoritative. The repaired R1 documents are proposals only.

R2 and production implementation remain blocked until:

1. a new independent D1/D2 re-review of the repaired candidate passes;
2. any new blocker or Serious Challenge is resolved;
3. the stakeholder ratifies the exact repaired proposed method; and
4. accepted-current method papers are explicitly promoted/reconciled with provenance.

Final production GPU qualification remains deferred to the final-release qualification package.

## Current gate

```text
PROPOSED_D1_D2_REPAIRED_AWAITING_INDEPENDENT_REREVIEW
```

This status is not a PASS claim. It records only that the known authoring blockers have been repaired sufficiently to request independent re-review.
