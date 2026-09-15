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
---

# R1 status — D1/D2 reconstruction repaired; independent re-review pending

## Disposition

The first independent R1 D1/D2 review returned **NO-PASS** for the proposed candidate while leaving the governing Revision-8 workplan itself PASS. The review identified five authoring/reconstruction blockers. Those blockers have now been repaired in proposed R1 evidence; they have **not** been self-approved.

The repaired R1 evidence set is:

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_METHOD_AMENDMENT.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D2_METHOD_AMENDMENT.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_D2_RECONSTRUCTION_EVIDENCE.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_D2_REPAIR_ADDENDUM.md` — controlling repair text where older proposed R1 text conflicts;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_EXACT_RECONSTRUCTION_LEDGER.md` — immutable field/input `RESTORE/REBIND/DROP` ledger;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_INDEPENDENT_REREVIEW_HANDOFF.md`.

The earlier `R1_INDEPENDENT_REVIEW_HANDOFF.md` remains historical evidence for the first review and is not the active re-review handoff.

## Repaired blockers

### 1. Canonical hard-obligation semantic deduplication

Automatic restored obligations and current explicit hard-support obligations are now normalized into one semantic identity space, retired-topology-only obligations are removed, exact semantic aliases are deduplicated **before canonical ID assignment and hard-gain scoring**, and same-locus semantic conflicts fail closed.

An alias-invariance metamorphic qualification is mandatory: adding an exact semantic alias may not change the canonical obligation set, MVSEL2 order, REPAIR2 trace, or MVQUAL result.

### 2. Lossless reconstruction ledger

The repair adds an immutable recovery ledger bound directly to `3937881ef00222e80845aa81f5471d89a4a7736c`, including:

- exact historical paths and blob identities;
- DATA6/DATA7 selector-input mapping;
- TargetCoverage, FEAS1, NEIGHBOR1/MVIDX1, MVSEL2, REPAIR2 and MVQUAL field dispositions;
- discrepancy adjudications;
- family-threshold census;
- explicit `RESTORE`, `REBIND`, or `DROP` ownership for selector-relevant fields.

### 3. DATA7 / TargetCoverageReference ownership contradiction

For the target-order subchain, `TargetCoverageReference` is now the sole fitted selector numerical owner. DATA7 retains logical lineage/input semantics but does not introduce a second fitted selector metric/scaler/PCA/reference owner. This follows the mature executable path at the coherent recovery snapshot and avoids reconstructing duplicate authority.

### 4. Certified-lazy MVSEL2 numerical contract

D2 now specifies the numerical lazy-certification invariant rather than merely demanding output equivalence:

- exact all-candidate Phase-B rebase;
- outward-rounded conservative bounds;
- stale-score refresh and monotonicity guard;
- exact contender certification using `B_max < R_best - 1e-14`;
- full-forward per-rank oracle/fallback;
- mandatory lazy-state invalidation/reconstruction after accepted REPAIR2 swaps.

Execution queues, native/OpenMP layout, batching, mmap and cache placement remain D3/D4 choices only within that exact D2 contract.

### 5. Named-family threshold override adjudication

The recovery census finds one instantiated scalar `coverage_threshold = 0.95` across TargetCoverage, MVSEL2/MVQUAL inputs and qualification evidence, with no active material/profile family-threshold policy map at the coherent recovery snapshot. The historical named-family override clause is therefore classified as a dormant/uninstantiated extension point, not an active recovered override. Every restored required family maps to threshold 0.95 unless a future accepted D1/D2 revision explicitly defines otherwise.

## Repaired proposed chain

```text
exact current P_train
 -> authenticated selector input lineage
 -> sole fitted TargetCoverageReference on exact P_train
 -> FEAS1
 -> exact NEIGHBOR1 / semantically deduplicated MVIDX1 obligations
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

This status is not a PASS claim. It records only that the identified first-review authoring blockers have been repaired sufficiently to request independent re-review.