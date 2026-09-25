---
kind: independent-review-handoff
protocol_version: 6.4.0
status: AWAITING_FRESH_INDEPENDENT_D2_REVIEW
workplan_id: MLFF-TRAIN2-CUEQ-PARITY-REQUALIFICATION
branch: design/mlff-train2-cueq-parity-requalification
accepted_D2_baseline: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_D2_source_target: a4824d28775164aa942fd29fa97ee0957eb87e6f
immutable_D2_candidate: 6e73fbb7af9b8d46f61cf81113259584ffed8527
D2_candidate_blob: 4bfd2451cc1835e82e303cc9a597b69b8f8deda9
superseded_candidate4: cd4e0453d0a27ae01f7041c1c9d222fd9d71a0e9
candidate4_review: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R1.md
candidate5_repair_record: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_5_REPAIR.md
highest_review_owner: D2
stage_C_state: BLOCKED_PENDING_FRESH_D2_REVIEW_AND_RATIFICATION
D3_D4_state: BLOCKED_PENDING_D2_ACCEPTANCE
---

# Fresh independent D2 Review handoff — Candidate 5 TRAIN2 CuEq acceleration equivalence

## 1. Immutable binding

Perform a genuinely fresh Protocol-6.4 numerical-method Review of immutable Candidate 5:

`6e73fbb7af9b8d46f61cf81113259584ffed8527`

Canonical Candidate-5 blob:

`4bfd2451cc1835e82e303cc9a597b69b8f8deda9`

Candidate file:

`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_5.md`

Review against accepted-current D2 kernel:

`a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`

and exact accepted D2 source target:

`a4824d28775164aa942fd29fa97ee0957eb87e6f`.

Do **not** substitute the mutable branch head for Candidate 5. Later descendants are lifecycle coordination only.

Candidate 4 is historical and already received NO-PASS. Do not re-review Candidate 4 as if it were current.

The earlier Candidate-5 author target `be57964c15ed24e30372de407534efd8173d6bc5` contained two renderer-sensitive single-dollar display delimiters around an otherwise unchanged inequality. It is historical representation only. The immutable target above is the representation-corrected, semantically unchanged Candidate-5 target.

## 2. Independence

This must be a genuinely fresh independent D2 Review.

Do not inherit:

- the Candidate-5 author repair conclusions;
- the proposed `delta*sqrt(u)` numerical scale;
- the recurrence-horizon construction;
- the state-anchor sufficiency claim;
- the two-ensemble/cardinality choice;
- the optimizer-action-probe adequacy claim;
- source/DATA6 sibling thresholds;
- projection/EVAL2 adequacy; or
- the author claim that B1-B7 are closed.

Treat those as propositions to falsify.

If accepted parent D1/D2 is itself numerically inadequate, contradictory, or incapable of protecting the scientific meaning, raise SERIOUS CHALLENGE to the earliest proper owner.

## 3. Candidate-5 scope

Candidate 5 preserves three separate semantic roles:

1. source/DATA6 calculator equivalence;
2. TRAIN2 state-transition equivalence; and
3. completed-state projection/EVAL2 equivalence.

Candidate 5 proposes CuEq TRAIN2 support for **FP32 only**.

FP64 CuEq TRAIN2 is explicitly unsupported and must fail closed.

## 4. Mandatory Challenge areas

### 4.1 Protected TRAIN2 consequence and full state

Challenge whether Candidate 5 now observes enough of the complete transition state:

- live model;
- optimizer state;
- EMA;
- scheduler/counters;
- RNG;
- hidden backend mutable state.

Determine whether the canonical common-gradient optimizer-action probe is a valid parameterization-safe observable of latent optimizer state.

Attempt a false pass where optimizer state differs but the chosen zero/reference-gradient probe set fails to expose the future consequence.

Challenge whether exact discrete-state equality is too strong, too weak, or correctly scoped.

### 4.2 EMA and optimizer-state transfer common mode

Challenge both model-state and optimizer-state transfer.

Verify that:

- transfer is snapshot-only and non-mutating;
- every relevant tensor/buffer/state item has a complete semantic inventory;
- independent anti-common-mode checks do not call the same mapping owner or consume the same generated mapping table;
- a quiescent dropped tensor still fails structurally;
- the optimizer-action probe cannot become self-consistent through a defective optimizer-state mapper.

### 4.3 Precision-scaled physical numerical budget

Candidate 5 proposes

`epsilon_(c,d)=delta_c*sqrt(u_d)`.

This is a new D2 heuristic, not inherited authority.

Challenge:

- whether the accepted robust-loss residual scale is the correct dimensional reference;
- whether `sqrt(u)` has a defensible role for backend-training equivalence;
- whether the scale is too strict to distinguish reference stochasticity or too loose for the protected consequence;
- whether energy/atom, force, and stress retain coherent physical interpretation;
- whether any part of the rule was implicitly tuned to Stage-A observations;
- whether near-zero update displacement is now handled correctly.

Do not preserve the formula merely because it is prospective.

### 4.4 Coherent accumulation and recurrence horizon

Candidate 5 adds:

- recurrence-horizon bounded adaptation using the slowest active e-folding timescale;
- full remaining-horizon treatment for non-decaying carried recurrence not closed by action probes;
- dyadic physical observations;
- maximum secant-growth extrapolation through the remaining accepted horizon.

Challenge explicit adversaries:

- constant tiny per-update backend bias;
- bias that appears only after recurrence state is populated;
- nonlinear late divergence;
- EMA-only growth;
- optimizer extremum/max state;
- scheduler discontinuity;
- apparently noisy centroids that make the extrapolation unstable.

Determine whether the growth rule is a legitimate conservative bound or an unjustified linear extrapolation.

If it is not valid, require a source-closed alternative rather than silently deleting the coherent-bias obligation.

### 4.5 State-domain applicability

Candidate 5 uses full-state entry/mid/late e3nn reference anchors and explicitly avoids claiming a theorem over every reachable state.

Determine whether that empirical state-class domain is sufficient to authorize full FP32 TRAIN2 execution.

Challenge whether candidate CuEq trajectories can leave the qualified state classes even when local e3nn-anchor probes pass.

If additional state coverage or an online/current-state condition is numerically required, state the minimum justified requirement.

### 4.6 Stochastic semantics and cardinality

The independent unit is fresh process.

Candidate 5 separates:

- between-process variability;
- within-process nested-repeat variability;
- global centroid;
- order-cell centroid;
- corresponding cell-local reference variance.

It requires two complete independent four-cell ensembles, five processes/cell, three nested retained repeats, no pooling rescue, and no outcome-selected rerun.

It additionally requires reference and candidate process-centroid resolution <= `epsilon/2`; otherwise the result is typed `INSUFFICIENT_*_RESOLUTION`.

Challenge:

- whether five processes/cell can ever support the proposed claim without hidden inferential assumptions;
- whether the resolution sensor is adequate and dimensionally/statistically meaningful;
- whether two independent complete ensembles are enough for classification stability;
- whether within-process and between-process decompositions are complete;
- whether candidate cell variance can still borrow an unrelated scale.

### 4.7 Rare-component non-dilution guard

Candidate 5 replaces the Huber `0.01` catastrophic ceiling with:

candidate/reference paired component maximum <= reference self-repeat component maximum + epsilon.

Challenge:

- same-repeat pairing dependence;
- finite-sample maximum instability;
- zero-reference-variance behavior;
- whether one rare large component can still hide;
- whether reference self-repeatability can become an unjustified candidate tolerance.

### 4.8 Robust-loss consequence

Candidate 5 no longer hard-gates algebraic Huber branch identity.

Challenge whether that is correct given continuity at the transition and the fact that the actual protected consequence is the optimizer/state transition.

Construct near-transition cases where branch identity changes but the state transition is benign, and cases where a tiny residual perturbation causes a material later update.

### 4.9 Real TRAIN2 exposure

Verify the qualification uses the actual accepted loader owner.

Challenge the deterministic union of:

- first window;
- last complete pre-boundary window;
- epoch/shuffle-boundary window;
- scheduler-discontinuity window;
- target-fraction extrema;
- atom/edge-count extrema; and
- all active head/property-mask branches.

Determine whether this is sufficient and whether any metadata rule can still systematically avoid numerically difficult native exposure.

Hand-built or reordered batches cannot substitute.

### 4.10 Source/DATA6 siblings

Candidate 5 now correctly labels FP32 and FP64 source/DATA6 relations as **proposed new D2 siblings** rather than already accepted D2 authority.

Independently determine whether:

- FP32 `rtol=1e-5, atol=1e-6`;
- FP64 `rtol=1e-10, atol=1e-12`; and
- exact descriptor/FPS protected selection consequence

are numerically adequate and sufficiently evidenced for their source/DATA6 roles.

Historical D4 behavior is evidence only.

### 4.11 Projection/EVAL2

Challenge the proposed completed-state relation independently of TRAIN2.

Verify:

- exact transient state authentication;
- snapshot-only non-mutating transfer;
- complete portable-forward state inventory;
- direct transient-CuEq vs mapped-e3nn physical parity;
- independent anti-common-mode mapping oracle;
- no accidental descriptor/FPS TRAIN2 gate; and
- EVAL2 provider identity **e3nn** as the actual portable numerical forward.

### 4.12 FP32/FP64 disposition

Explicitly judge:

- source/DATA6 FP32;
- source/DATA6 FP64;
- TRAIN2 FP32;
- TRAIN2 FP64 unsupported/fail-closed; and
- projection/EVAL2.

Do not infer FP64 TRAIN2 support from any forward-only sibling.

### 4.13 Qualification versus routine doctor

Candidate 5 retains the architecture-neutral split:

- expensive qualification establishes bounded applicability;
- routine doctor authenticates that record and performs a cheap real reachability/finiteness witness.

Verify the routine witness cannot recreate/widen equivalence, retry until pass, authorize another state/runtime/model/dtype, or revive stale Rev86 evidence.

## 5. Required counterexample closure

At minimum reason through:

- coherent sub-tolerance per-update bias;
- nonlinear late divergence;
- equal means with inflated candidate variance;
- quiet-cell variance inflation hidden by another cell;
- within-process inflation hidden by process means;
- opposite cell biases cancelling globally;
- rare one-component error;
- update-2-only divergence;
- EMA-only divergence;
- optimizer-state divergence invisible to live predictions;
- optimizer-action probe blind spot;
- scheduler/RNG divergence;
- target-first or synthetic batch;
- omitted boundary/scheduler exposure;
- dropped model state;
- dropped optimizer state;
- transfer mutation;
- common-mode primary/independent mapper;
- descriptor-only TRAIN2 drift;
- source/DATA6 FPS-changing descriptor drift;
- zero reference variance;
- insufficient reference resolution;
- insufficient candidate resolution;
- stale qualification;
- trivial mid/late state anchors;
- CuEq trajectory leaving the e3nn anchor domain; and
- attempted FP64 TRAIN2 admission.

## 6. Evidence boundary

Stage-A MH-1 and MPA-0 evidence is method-design evidence only.

Candidate-4 evidence cannot qualify Candidate 5.

Do not run Candidate-5 Stage-C acceptance first and then tune the method to its outcomes.

A fresh D2 Review PASS means only that Candidate 5 is coherent enough for prospective Stage-C qualification.

Stakeholder ratification of the exact passing candidate remains required before Stage C.

No D3/D4 product implementation is authorized by Review alone.

## 7. Required disposition

Return:

- PASS or NO-PASS for immutable Candidate 5;
- SERIOUS CHALLENGE state and earliest affected authority owner, if any;
- genuine blocking findings only;
- precise repair instructions for every blocker;
- explicit disposition of source/DATA6 FP32 and FP64;
- explicit disposition of TRAIN2 FP32;
- explicit confirmation or rejection of FP64 TRAIN2 fail-closed narrowing;
- explicit disposition of projection/EVAL2;
- explicit judgment on `delta*sqrt(u)`;
- explicit judgment on recurrence-horizon/growth semantics;
- explicit judgment on state-anchor applicability;
- explicit judgment on EMA and optimizer-state observability;
- explicit judgment on process/cardinality/replication/resolution design;
- explicit judgment on rare-component guard;
- evidence/currentness impacts; and
- D2 -> D3 handoff implications if PASS.

Do not mutate `6e73fbb7af9b8d46f61cf81113259584ffed8527` and continue calling it the same reviewed candidate.

Any semantic repair creates a new candidate identity.

Even after Review PASS, do not implement D3/D4 and do not treat CuEq as qualified. Fresh Stage-C evidence remains mandatory after stakeholder ratification.
