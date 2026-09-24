---
kind: proposed-D2-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_NOT_ACCEPTED
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
candidate_id: MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-1
date: 2026-09-24
parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
parent_d2_exact_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
stage_a_cross_family_basis: 24734c8113dfaeaba4ae32c2bb0b80f3c0c72e82
human_ratification_required: true
---

# Proposed D2 acceleration-equivalence overlay for MACE e3nn / CuEq execution

## 1. Lifecycle and scope

This document is a **proposed** bounded D2 overlay. It is not accepted current authority and cannot authorize CuEq execution by repository presence alone.

It concretizes the accepted D2 rule that an optimized/native backend is execution-only only under a source-closed numerical-equivalence relation. It changes the challenged TRAIN2 relation while source-closing adjacent currently supported acceleration relations. It does not change D1 scientific meaning, MACE training objectives, replay semantics, checkpoint ranking, CV thresholds or publication policy.

The proposal is deliberately role-separated:

1. source/DATA6 calculator inference;
2. TRAIN2 training-operator equivalence;
3. trained-state CuEq -> portable-e3nn projection/EVAL2.

One role cannot authorize another merely because the same library backend name appears in both.

## 2. Acceleration-equivalence family

### D2.CUEQ.DEF.001 — relation key

An acceleration-equivalence member is keyed by

[
A=(r,d,s,k,o,ho),
]

where:

- (r) is semantic role;
- (din{mathrm{float32},mathrm{float64}}) is learned-model dtype;
- (s) is model-state class;
- (k) is resolved kernel realization;
- (o) is the governed consumer/objective identity; and
- (ho) is the arithmetic-relevant runtime identity.

A record from another key is not current evidence for this member.

### D2.CUEQ.DEF.002 — exact common inputs

Reference e3nn and candidate CuEq observations compare only when all non-backend inputs are identical: model architecture/head topology and state, structure/batch membership and order, labels, objective/E0/weights/masks, dtype, accepted preprocessing, and every other numerical input owned upstream. Backend/kernel realization is the deliberate independent variable.

A mismatch is typed failure, not numerical disagreement.

## 3. Preserved source/DATA6 calculator relations

### D2.CUEQ.DEF.003 — source FP32

For source-foundation inference, DATA6 descriptor execution, pseudolabel execution when authorized, or another role that actually consumes calculator descriptors/selection, the current FP32 relation is source-closed without numerical change:

- energy/atom, force, stress and invariant descriptors compare componentwise by
  (mathrm{rtol}=10^{-5}), (mathrm{atol}=10^{-6});
- the existing deterministic descriptor/FPS fingerprint is exact under its current (	frac12) selection fraction and (10^{-12}) tie tolerance;
- all compared outputs are finite and shape-compatible.

The exact fingerprint is hard because selection is a protected consequence for this role.

### D2.CUEQ.DEF.004 — source FP64

The same source-role relation uses
(mathrm{rtol}=10^{-10}), (mathrm{atol}=10^{-12})
for FP64, with the same exact selection consequence.

These values are preserved current semantics, not inferred from the Stage-A TRAIN2 failure.

## 4. TRAIN2 protected consequence

### D2.CUEQ.DEF.005 — training operator

For TRAIN2, the governed backend-specific operator is not a calculator forward alone. It is the map

[
(	heta, B, O) mapsto igl(L,;gigr),
]

where:

- (	heta) is the exact current trainable model state;
- (B) is the exact current training batch/exposure;
- (O) is the accepted TRAIN2 objective, including head routing, labels, E0, weights, masks, reduction/accumulation and any accepted gradient transformation before optimizer consumption;
- (L) is the scalar objective supplied by the training path; and
- (g) is the canonical optimizer-consumed trainable-parameter gradient vector immediately before optimizer state mutation.

The canonical gradient vector is flattened in exact named-trainable-parameter order. Shape/name mismatch is failure.

Optimizer/EMA code that is backend-independent remains a D4/D3 identity obligation; CuEq equivalence is judged at the backend-dependent gradient boundary rather than by duplicating optimizer semantics inside a second numerical owner.

### D2.CUEQ.DEF.006 — TRAIN2 descriptors are not an authorizing channel

Invariant descriptors and FPS fingerprints are not consumed by the current TRAIN2 optimizer. They therefore do not belong to the TRAIN2 backend-equivalence predicate.

They may remain diagnostics. They remain hard under D2.CUEQ.DEF.003-004 where descriptor geometry/selection is actually consumed.

A future TRAIN2 design that consumes descriptors reopens this definition.

## 5. Finite-sample stochastic qualification functional

### D2.CUEQ.DEF.007 — experimental unit and frozen design

The independent experimental unit is the **fresh process**.

The qualification realization is balanced over the four construction/execution-order cells:

[
H={(R!	o!C,R!	o!C),
(R!	o!C,C!	o!R),
(C!	o!R,R!	o!C),
(C!	o!R,C!	o!R)},
]

where (R) denotes e3nn reference and (C) pure CuEq candidate.

For each cell:

- 5 fresh processes;
- 1 discarded warm-up observation per backend;
- 3 retained observations per backend;
- exact reset to the bound model/training state for every retained training-operator observation;
- no early stopping;
- no rerun selected from observed pass/fail.

The resulting (20) fresh processes and nested repeats form a **finite-sample functional**. No all-pairs count is interpreted as an independent population sample count.

### D2.CUEQ.DEF.008 — governed vector observations

For governed continuous channel (c), let

[
x_{b,h,p,r,c}inmathbb R^{m_c}
]

be the retained observation for backend (bin{R,C}), order cell (h), process (p), and retained repeat (r).

For TRAIN2 the required channels are:

1. energy/atom vector over the bound forward probe;
2. force-component vector;
3. stress-component vector;
4. scalar objective (L), represented as a one-component vector, for each active objective/head branch; and
5. canonical optimizer-consumed gradient vector (g) for each active objective/head branch.

Only channels actually defined by the active objective are required; missing required branches are insufficiency/failure, not implicit zeroes.

For vector (vinmathbb R^m),

[
|v|_{mathrm{RMS}}
=
sqrt{rac1msum_{j=1}^{m}v_j^2}.
]

### D2.CUEQ.DEF.009 — reference and candidate centroids

With balanced total retained count (N=60) per backend,

[
mu_{b,c}
=
rac1N
sum_{h,p,r}x_{b,h,p,r,c}.
]

For cell (h), with (N_h=15),

[
mu_{b,h,c}
=
rac1{N_h}
sum_{p,r}x_{b,h,p,r,c}.
]

### D2.CUEQ.DEF.010 — finite-sample variability

Reference and candidate finite-sample variability are defined with the finite functional's own divisor, not a claim of unbiased population estimation:

[
V_{b,c}
=
rac1N
sum_{h,p,r}
|x_{b,h,p,r,c}-mu_{b,c}|_{mathrm{RMS}}^2.
]

For each candidate order cell,

[
V_{C,h,c}
=
rac1{N_h}
sum_{p,r}
|x_{C,h,p,r,c}-mu_{C,h,c}|_{mathrm{RMS}}^2.
]

The global and cell-conditioned backend centroid displacements are

[
D_c=|mu_{C,c}-mu_{R,c}|_{mathrm{RMS}},
]

[
D_{h,c}=|mu_{C,h,c}-mu_{R,h,c}|_{mathrm{RMS}}.
]

### D2.CUEQ.DEF.011 — reference-anchored stochastic equivalence

For every required channel (c) with (V_{R,c}>0), pass requires all of:

[
D_c^2 le V_{R,c},
]

[
D_{h,c}^2 le V_{R,c}
qquad orall hin H,
]

[
V_{C,c}le 2V_{R,c},
]

[
V_{C,h,c}le 2V_{R,c}
qquad orall hin H.
]

Interpretation:

- systematic global or order-conditioned backend shift may not exceed one RMS scale of ordinary e3nn realization variability;
- CuEq stochastic variance may not exceed twice e3nn variance, so the candidate-specific additional variance budget is no larger than the accepted reference variance;
- the scale is set only by the accepted e3nn reference, never by candidate cross discrepancy or candidate-inflated pooled noise.

The constants (1) and (2) are semantic effect/variance budgets defined before Stage-C evidence. They are not fitted to the Stage-A CuEq outcomes.

### D2.CUEQ.DEF.012 — zero-reference-variance branch

If (V_{R,c}=0), the channel passes only when

[
D_c=0,qquad
D_{h,c}=0;orall h,qquad
V_{C,c}=0,qquad
V_{C,h,c}=0;orall h.
]

No epsilon is learned from the candidate. If exact zero reference variability makes a required nonzero-gradient probe uninformative, the probe is insufficient under D2.CUEQ.DEF.014 instead of being silently accepted.

### D2.CUEQ.DEF.013 — finite/shape hard guards

Every reference/candidate observation must be finite and shape/name compatible. Any non-finite value, missing gradient, parameter-order mismatch, missing required property/head branch, or impossible reset is typed failure.

No stochastic envelope rescues a structural mismatch.

## 6. Gradient direction and probe adequacy

### D2.CUEQ.DEF.014 — gradient direction

For each active TRAIN2 branch/state, let (mu_{R,g}) be the e3nn global gradient centroid.

A qualifying probe requires

[
|mu_{R,g}|_{mathrm{RMS}}>0.
]

For every factorial cell (h),

[
langle mu_{R,h,g},mu_{R,g}angle>0,
]

[
langle mu_{C,h,g},mu_{R,g}angle>0.
]

Thus neither reference nor candidate cell centroid may reverse the accepted reference descent half-space. A zero or directionally ambiguous reference gradient makes that probe insufficient; another predeclared real TRAIN2 branch/batch is required.

This sign condition is independent of the magnitude envelope in D2.CUEQ.DEF.011.

### D2.CUEQ.DEF.015 — objective/branch coverage

The probe set must exercise every branch that can reach the optimizer in the qualified TRAIN2 realization.

For a multi-head/replay realization this includes, where active:

- target-head target-data objective;
- replay/pretraining-head replay objective;
- every property mask/reduction route that can materially alter the accepted gradient.

A source-selected batch or descriptor-only proxy cannot substitute for an active training branch.

Probe membership/order/labels are frozen before candidate evaluation.

## 7. Model-state domain

### D2.CUEQ.DEF.016 — starting state

(S_0) is the exact authenticated pre-TRAIN2 checkpoint/head topology bound by the current campaign.

A passing (S_0) relation establishes entry-state operator equivalence only.

### D2.CUEQ.DEF.017 — non-initial state

A full TRAIN2 operator claim additionally requires at least one authenticated non-initial state (S_1) for every materially distinct claimed architecture/head topology.

(S_1):

- must differ from (S_0);
- must be obtained independently of the CuEq candidate's acceptance outcome;
- may come from a bounded e3nn-only adaptation or still-applicable authenticated trained-state evidence;
- binds the same architecture/head/objective family being claimed.

Starting-state evidence alone cannot be represented as proof over optimizer-reachable trained states.

Contradictory later paired-training evidence reopens this relation even when CUEQ-PHASE1 is not a universal runtime prerequisite.

## 8. Dtype semantics

### D2.CUEQ.DEF.018 — FP32 TRAIN2

FP32 TRAIN2 pure-CuEq authorization uses D2.CUEQ.DEF.005-017.

The Rev86 `1e-6` stable-channel maximum, force p99/p99.9 ratio `1.25`, `1.5` Fmax self factor and `1e-4` absolute Fmax ceiling are superseded for TRAIN2 authorization if this candidate is accepted. They remain historical diagnostic semantics only.

No replacement tail percentile or family-specific tolerance is introduced.

### D2.CUEQ.DEF.019 — FP64 TRAIN2

The existing FP64 forward calculator guard retains
(mathrm{rtol}=10^{-10}), (mathrm{atol}=10^{-12}).

That forward guard is necessary but not sufficient to call CuEq an equivalent **training** backend. Current FP64 CuEq TRAIN2 support must also satisfy the protected gradient/operator consequence of D2.CUEQ.DEF.005-017, or D3/D4 must narrow CuEq TRAIN2 support so FP64 is not represented as qualified.

This is a source-closure strengthening, not a relaxation of the FP64 numerical envelope.

## 9. Trained-state projection / EVAL2

### D2.CUEQ.DEF.020 — portable projection relation

For phase-separated CuEq TRAIN2 with portable checkpoints:

1. authenticate the transient trained CuEq realization and checkpoint/model state before it controls inference;
2. reconstruct the canonical portable e3nn target shell from the accepted configuration;
3. transfer state through the pinned dependency-native CuEq -> e3nn state-transfer owner;
4. require exact preservation of the canonical portable-shell architecture identity across transfer;
5. compare the projected portable e3nn model against the authenticated CuEq realization under the existing dtype-appropriate calculator relation;
6. perform EVAL2 with the actual portable e3nn provider identity.

This source-closes the already qualified representation split; it does not redefine projection tolerance from the present TRAIN2 incident.

## 10. Qualification versus routine doctor admission

### D2.CUEQ.DEF.021 — qualification record

The multi-process functional produces an authorizing qualification record only when all required role/state/dtype channels pass.

Its identity binds at least:

- this D2 method digest;
- CUEQ-DEP1/runtime identity and every arithmetic-relevant MACE/Torch/CUDA/CuEq component/source identity;
- device/runtime precision, determinism, TF32/matmul state where material;
- dtype and resolved CuEq kernel;
- model architecture/head topology;
- (S_0) and (S_1) applicability identities;
- TRAIN2 objective/exposure identity;
- exact probe membership/order;
- construction/evaluation-order design and cardinality.

A changed binding stales the record.

### D2.CUEQ.DEF.022 — routine witness

A routine campaign doctor need not rerun the 20-process qualification experiment on every invocation.

It may:

1. authenticate a current qualification record whose applicability contains the requested realization; and
2. run a cheaper bounded execution witness for current checkpoint/head/objective/runtime reachability and finite forward/backward execution.

The routine witness cannot:

- estimate a new equivalence envelope;
- widen a failed qualification;
- convert an old-policy `passed=true` record into current evidence;
- retry until pass;
- substitute descriptor/FPS parity for gradient/operator parity.

The exact persistence/routing mechanism belongs to D3/D4.

## 11. Evidence role of Stage A

The authenticated MH-1 and MPA-0 Stage-A artifacts are **method-design evidence**, not Stage-C acceptance evidence for this candidate.

They establish:

- model-family-dependent absolute FP32 discrepancy scale;
- similar normalized stochastic decomposition across the two families;
- material process/order covariance;
- failure of the fixed `1e-6` stable-channel interpretation across descriptor and MPA-0 energy;
- redundancy/fragility of the previous tail-percentile reducer.

They do not contain optimizer-consumed gradients and therefore cannot pass D2.CUEQ.DEF.005-017.

Fresh candidate-bound evidence is required after this document is frozen.

## 12. Stage-C falsification obligations

Before acceptance, fresh target-host evidence must attempt to falsify at least:

1. MACE-MH-1 / `omat_pbe`, FP32, (S_0) and (S_1);
2. MACE-MPA-0-medium / `default`, FP32, (S_0) and (S_1);
3. target and replay/head/property branches actually able to reach the optimizer;
4. global systematic shift above the reference-variance boundary;
5. order-cell shift that cancels globally but exceeds the reference boundary in one cell;
6. candidate variance inflation above (2V_R);
7. gradient-direction reversal;
8. zero-reference-variance with nonzero candidate disagreement;
9. descriptor-only drift that leaves TRAIN2 operator channels unchanged — this must **not** fail TRAIN2 solely because descriptor coordinates differ;
10. source/DATA6 descriptor/FPS drift — this **must** fail the source relation where selection is governed;
11. wrong checkpoint/head/objective/runtime/method identity;
12. trained-state projection architecture drift and post-projection calculator mismatch;
13. FP64 operator parity if FP64 CuEq TRAIN2 remains supported.

The number/order of processes and repetitions is frozen before outcomes are inspected. A failed realization is evidence; it is not permission to repeat until pass.

## 13. D2 -> D3 handoff if accepted

D3/D4 shall prefer reduction over additive compatibility machinery:

- replace the current TRAIN2 Rev86 authorizing reducer rather than stacking this relation above it;
- retain old Rev83-86 schemas only for historical deserialization/diagnosis, not authorization;
- remove TRAIN2 descriptor/FPS hard-gating when no TRAIN2 consumer exists instead of adding a geometry exception;
- use one canonical training-operator qualification owner;
- reuse current CampaignStore/currentness machinery and add only the missing method/applicability identity needed to prevent stale authorization;
- keep source/DATA6 calculator parity and trained-state projection relations separate;
- preserve no-silent-fallback behavior;
- preserve the generated source `e3nn` / TRAIN2 `cueq` policy unless its owning policy is separately changed;
- correct EVAL2 measurement identity to the actual portable e3nn forward without retraining an otherwise authenticated root.

## 14. Acceptance state

This candidate is **not accepted**.

Required next steps are:

1. independent numerical review/falsification of this exact candidate;
2. any repair that review requires, producing a new immutable candidate identity when semantics change;
3. fresh Stage-C target-host evidence under the immutable candidate;
4. explicit stakeholder ratification of the exact reviewed/passing candidate;
5. only then D3/D4 concretization.

Until those steps complete, the current executable doctor remains fail-closed and the explicit e3nn TRAIN2 override remains the bounded safe operational route.
