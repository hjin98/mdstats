---
kind: proposed-D2-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_NOT_ACCEPTED
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
candidate_id: MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-2
date: 2026-09-24
parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
parent_d2_exact_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
stage_a_cross_family_basis: 24734c8113dfaeaba4ae32c2bb0b80f3c0c72e82
supersedes_proposed_candidate: MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-1
human_ratification_required: true
---

# Proposed D2 acceleration-equivalence overlay for MACE e3nn / CuEq execution

## 1. Lifecycle and scope

This document is a **proposed** bounded D2 overlay. It is not accepted current authority and cannot authorize CuEq execution by repository presence alone.

Candidate 2 supersedes the unreviewed Candidate 1. Author-side Challenge found that Candidate 1 allowed a persistent backend centroid displacement as large as one ordinary e3nn realization RMS. That is not adequate for a training operator because a persistent bias can accumulate while zero-mean execution noise need not. Candidate 2 separates fixed dtype-scale persistent-bias control from reference-anchored stochastic-spread control.

This overlay concretizes the accepted D2 rule that a native backend is execution-only only under a source-closed numerical-equivalence relation. It changes the challenged TRAIN2 relation while source-closing adjacent currently supported acceleration relations. It does not change D1 scientific meaning, MACE training objectives, replay semantics, checkpoint ranking, CV thresholds or publication policy.

The relation family is deliberately split by protected consequence:

1. source/DATA6 calculator inference;
2. TRAIN2 training-state transition;
3. trained-state CuEq -> portable-e3nn projection/EVAL2.

One role cannot authorize another merely because the same backend name appears in both.

## 2. Acceleration-equivalence family

### D2.CUEQ.DEF.001 — relation key

An acceleration-equivalence member is keyed by

[
A=(r,d,s,k,o,ho),
]

where (r) is semantic role, (d) learned-model dtype, (s) model-state class, (k) resolved kernel realization, (o) governed consumer/objective identity, and (ho) arithmetic-relevant runtime identity.

A record from another key is not current evidence.

### D2.CUEQ.DEF.002 — exact common inputs

Reference e3nn and candidate CuEq observations compare only when all non-backend inputs are identical: model architecture/head topology and state, structure/batch membership and order, labels, objective/E0/weights/masks, optimizer/EMA/RNG state, dtype, accepted preprocessing, and every other numerical input owned upstream.

Backend/kernel realization is the deliberate independent variable. A mismatch is typed failure, not numerical disagreement.

## 3. Preserved source/DATA6 calculator relations

### D2.CUEQ.DEF.003 — source FP32

For source-foundation inference, DATA6 descriptor execution, pseudolabel execution when authorized, or another role that actually consumes calculator descriptors/selection, the current FP32 relation is source-closed without numerical change:

- energy/atom, force, stress and invariant descriptors compare componentwise by
  (mathrm{rtol}=10^{-5}), (mathrm{atol}=10^{-6});
- the existing deterministic descriptor/FPS fingerprint is exact under its current one-half selection fraction and (10^{-12}) tie tolerance;
- all compared outputs are finite and shape-compatible.

The fingerprint is hard because selection is a protected consequence for this role.

### D2.CUEQ.DEF.004 — source FP64

The same source-role relation uses
(mathrm{rtol}=10^{-10}), (mathrm{atol}=10^{-12})
for FP64, with exact selection consequence unchanged.

These constants are preserved current numerical semantics, not inferred from Stage-A TRAIN2 observations.

## 4. TRAIN2 protected consequence

### D2.CUEQ.DEF.005 — backend-specific training map

For TRAIN2 the governed backend-specific computation is the accepted training-state transition

[
mathcal T_b:
(	heta,q,omega)
mapsto
(	heta',q',omega'),
]

where:

- (bin{R,C}) is e3nn reference or pure CuEq candidate;
- (	heta) is exact model state;
- (q) is accepted optimizer/EMA/scheduler/RNG state;
- (omega) is the exact frozen exposure/objective input for one optimizer update; and
- the output is the post-update training state.

The backend-specific forward/backward graph is part of (mathcal T_b). Optimizer semantics are not redefined here; they are held identical so any difference in the transition is attributable to the backend-dependent model computation.

### D2.CUEQ.DEF.006 — minimum stateful transition witness

A TRAIN2 qualification observation resets exact ((	heta,q)), executes two frozen optimizer updates

[
(	heta_b^{(1)},q_b^{(1)})
=
mathcal T_b(	heta^{(0)},q^{(0)},omega_1),
]

[
(	heta_b^{(2)},q_b^{(2)})
=
mathcal T_b(	heta_b^{(1)},q_b^{(1)},omega_2).
]

Two updates are the minimum witness because the first populates stateful optimizer/EMA recurrence and the second consumes non-initial recurrence state.

Every run must retain finite loss, optimizer-consumed gradients, model parameters, optimizer state and EMA state. Any non-finite state is hard failure.

### D2.CUEQ.DEF.007 — common functional observation of the transition

Training realizations may use different transient parameterizations, so transition equivalence is observed through one common portable function.

Let (P_b) be the already-governed projection from the authenticated transient training realization to the canonical portable e3nn shell; for e3nn this is identity.

Let (E) be the fixed portable-e3nn evaluator on a frozen witness corpus/head.

For (kin{1,2}),

[
y_{b}^{(k)}
=
E(P_b(	heta_b^{(k)})),
qquad
y^{(0)}
=
E(	heta^{(0)}),
]

and define the update-induced functional displacement

[
Delta y_b^{(k)}
=
y_b^{(k)}-y^{(0)}.
]

The governed transition channels are the energy/atom, force and stress displacement vectors at both (k=1) and (k=2).

Using displacement rather than absolute post-step prediction prevents a large common baseline from masking a materially different update.

Projection is a measurement dependency here and must independently satisfy D2.CUEQ.DEF.021 before it can be used to close TRAIN2 evidence.

### D2.CUEQ.DEF.008 — TRAIN2 descriptors are not an authorizing channel

Invariant descriptors and FPS fingerprints are not consumed by the current TRAIN2 optimizer. They therefore do not belong to the TRAIN2 backend-equivalence predicate.

They may remain diagnostics. They remain hard under D2.CUEQ.DEF.003-004 where descriptor geometry/selection is actually consumed.

A future TRAIN2 design that consumes descriptors reopens this definition.

## 5. Frozen finite-sample qualification design

### D2.CUEQ.DEF.009 — experimental unit

The independent experimental unit is the **fresh process**.

Qualification is balanced over four backend construction/execution-order cells. For each cell:

- 5 fresh processes;
- 1 discarded warm-up per backend;
- 3 retained observations per backend;
- exact model/optimizer/EMA/RNG reset for each retained transition observation;
- no early stopping;
- no outcome-selected reruns.

Thus 20 fresh processes are independent units and repeated observations are nested measurements.

The relation is a deterministic finite-sample qualification functional. It does not interpret all-pairs or retained-observation cardinality as an inferential independent-sample count.

### D2.CUEQ.DEF.010 — vector notation

For governed vector channel (c), let

[
x_{b,h,p,r,c}inmathbb R^{m_c}
]

be the retained observation for backend (b), order cell (h), fresh process (p), repeat (r).

This notation is used for:

- direct starting-state physical E/F/stress forward channels where required by the qualification record; and
- (Delta y^{(1)}) and (Delta y^{(2)}) E/F/stress transition-displacement channels for every active TRAIN2 objective/head branch and bound state.

For vector (v),

[
|v|_{mathrm{RMS}}
=
sqrt{rac1msum_j v_j^2}.
]

With balanced total retained count (N=60),

[
mu_{b,c}
=
rac1Nsum_{h,p,r}x_{b,h,p,r,c},
]

and with (N_h=15),

[
mu_{b,h,c}
=
rac1{N_h}sum_{p,r}x_{b,h,p,r,c}.
]

Finite-sample variability is

[
V_{b,c}
=
rac1N
sum_{h,p,r}
|x_{b,h,p,r,c}-mu_{b,c}|_{mathrm{RMS}}^2,
]

and candidate cell-local variability is

[
V_{C,h,c}
=
rac1{N_h}
sum_{p,r}
|x_{C,h,p,r,c}-mu_{C,h,c}|_{mathrm{RMS}}^2.
]

## 6. Persistent-bias relation

### D2.CUEQ.DEF.011 — dtype mixed envelope

Let ((r_d,a_d)) be:

- FP32: (r_d=10^{-5}), (a_d=10^{-6});
- FP64: (r_d=10^{-10}), (a_d=10^{-12}).

For reference vector (z), define component tolerance

[
	au_{d,j}(z)
=
a_d+r_d|z_j|.
]

A candidate vector (w) is persistently equivalent to (z) iff

[
|w_j-z_j|
le
	au_{d,j}(z)
qquadorall j.
]

This is the existing dtype mixed numerical envelope, applied to backend **centroids** rather than noisy single realizations.

### D2.CUEQ.DEF.012 — global and order-cell centroid guards

For every governed channel (c), pass requires

[
mu_{C,c}
approx_d
mu_{R,c},
]

and for every order cell (h),

[
mu_{C,h,c}
approx_d
mu_{R,h,c},
]

using D2.CUEQ.DEF.011 componentwise.

Therefore opposite order-conditioned backend biases cannot cancel into a passing global mean.

A systematic centroid shift never receives a larger margin merely because single-realization noise is large.

## 7. Stochastic non-degradation

### D2.CUEQ.DEF.013 — tolerance RMS floor

For channel (c), form the fixed tolerance vector around the e3nn global centroid,

[
t_{c,j}
=
a_d+r_d|mu_{R,c,j}|,
]

and its RMS-square scale

[
T_c^2
=
rac1{m_c}sum_j t_{c,j}^2.
]

Define the candidate-independent reference stochastic budget

[
B_c
=
max(V_{R,c},T_c^2).
]

The candidate cross result does not enter (B_c).

### D2.CUEQ.DEF.014 — variance budget

Pass requires

[
V_{C,c}le 2B_c
]

and

[
V_{C,h,c}le 2B_c
qquadorall h.
]

The factor two is a predeclared variance budget: candidate stochastic spread may consume at most one additional reference-sized variance budget beyond the larger of observed accepted-reference variability and its fixed dtype tolerance floor.

This prevents a noisy candidate from inflating its own acceptance denominator while allowing a deterministic reference regime to retain the fixed dtype numerical floor.

No tail percentile, all-pairs count, candidate-normalized ratio, or model-family threshold table is authoritative.

## 8. Objective, branch and state coverage

### D2.CUEQ.DEF.015 — real TRAIN2 objective coverage

The two-step transition witness must use the real accepted TRAIN2 objective and exact inputs: checkpoint/head set, labels, E0, objective weights, masks, replay/target branch, optimizer, EMA, scheduler, dtype and batch/exposure semantics.

Every active objective/head/property branch capable of reaching the optimizer requires a predeclared two-step witness sequence. A source-selected structure proxy, descriptor-only check, or inference calculator cannot substitute.

### D2.CUEQ.DEF.016 — starting state

(S_0) is the exact authenticated pre-TRAIN2 model state for the claimed architecture/head topology.

A passing (S_0) witness establishes entry-state transition equivalence only.

### D2.CUEQ.DEF.017 — non-initial state

A full TRAIN2 operator claim additionally requires at least one authenticated non-initial state (S_1) for each materially distinct claimed architecture/head topology.

(S_1):

- differs from (S_0);
- is obtained independently of the candidate acceptance outcome;
- may come from bounded e3nn-only adaptation or still-applicable authenticated trained-state evidence;
- uses the same architecture/head/objective family being claimed.

Starting-state evidence alone cannot be represented as proof over optimizer-reachable trained states.

Contradictory later paired-training evidence reopens the relation even though historical CUEQ-PHASE1 is not a universal doctor prerequisite.

## 9. Dtype semantics

### D2.CUEQ.DEF.018 — FP32 TRAIN2

FP32 pure-CuEq TRAIN2 authorization uses D2.CUEQ.DEF.005-017.

If this candidate is accepted, the Rev86 TRAIN2 authorizing statistics are retired:

- fixed (10^{-6}) stable-channel maximum;
- force p99/p99.9 ratio (1.25);
- Fmax self factor (1.5);
- fixed (10^{-4}) Fmax ceiling.

They remain historical diagnostics only.

No family-specific replacement threshold is introduced.

### D2.CUEQ.DEF.019 — FP64 TRAIN2

FP64 retains the existing calculator forward envelope
(mathrm{rtol}=10^{-10}), (mathrm{atol}=10^{-12}).

That forward guard is not sufficient by itself to establish an equivalent training state transition. FP64 CuEq TRAIN2 must satisfy D2.CUEQ.DEF.005-017 or D3/D4 must explicitly narrow support rather than representing the historical forward-only record as training equivalence.

This strengthens source closure without relaxing FP64 numerical tolerance.

## 10. Projection / EVAL2 relation

### D2.CUEQ.DEF.020 — authenticated transient state

A CuEq-trained checkpoint is first authenticated in the exact transient realization that produced it. Checkpoint/model state cannot control inference before this identity/state authentication succeeds.

### D2.CUEQ.DEF.021 — portable projection

Projection then:

1. reconstructs the canonical portable e3nn shell from accepted configuration;
2. transfers authenticated state through the pinned dependency-native CuEq -> e3nn transfer owner;
3. requires exact preservation of the canonical portable-shell architecture identity;
4. compares projected portable e3nn against the authenticated CuEq realization under the existing dtype-appropriate calculator relation; and
5. executes EVAL2 with provider identity `e3nn`, because that is the actual numerical forward after projection.

The projection relation is independently checked before its common evaluator may serve as the TRAIN2 transition oracle.

## 11. Qualification versus routine doctor admission

### D2.CUEQ.DEF.022 — qualification record

The multi-process functional produces an authorizing qualification record only when all required role/state/dtype channels pass.

Its identity binds at least:

- D2 method digest;
- CUEQ-DEP1/runtime identity and arithmetic-relevant MACE/Torch/CUDA/CuEq component/source identities;
- device precision/determinism/TF32/matmul state where material;
- dtype and resolved CuEq kernel;
- model architecture/head topology;
- (S_0) and (S_1) applicability;
- TRAIN2 objective/exposure identity;
- frozen transition witness corpus and batch sequences;
- construction/execution-order design and cardinality;
- independently qualified projection relation.

A changed binding stales the record.

### D2.CUEQ.DEF.023 — routine witness

Routine campaign doctor need not rerun the 20-process qualification experiment on every invocation.

It may:

1. authenticate a current qualification whose applicability contains the requested realization; and
2. run a cheaper bounded execution witness for current checkpoint/head/objective/runtime reachability and finite forward/backward execution.

The routine witness cannot estimate a new envelope, widen a failed qualification, retry until pass, or substitute descriptor/FPS parity for the training transition relation.

Exact persistence/routing belongs to D3/D4.

## 12. Evidence role of Stage A

Authenticated MH-1 and MPA-0 Stage-A artifacts are **method-design evidence**, not acceptance evidence for Candidate 2.

They establish model-family-dependent absolute FP32 discrepancy, similar normalized stochastic decomposition, material process/order covariance, failure of the fixed (10^{-6}) stable-channel interpretation, and fragility of tail/max reduction.

They do not contain two-step training-state transitions. Fresh candidate-bound evidence is required after Candidate 2 is frozen.

## 13. Stage-C falsification obligations

Before acceptance, fresh target-host evidence must attempt to falsify at least:

1. MACE-MH-1 / `omat_pbe`, FP32, (S_0) and (S_1);
2. MACE-MPA-0-medium / `default`, FP32, (S_0) and (S_1);
3. every active target/replay/head/property branch capable of reaching the optimizer;
4. persistent global centroid bias outside D2.CUEQ.DEF.011;
5. opposite order-cell biases that cancel globally;
6. candidate stochastic variance above D2.CUEQ.DEF.014;
7. a defect that appears only on the second optimizer update after recurrence state is populated;
8. descriptor-only drift with otherwise equivalent transition — this must not fail TRAIN2 solely because descriptor coordinates differ;
9. source/DATA6 descriptor/FPS drift — this must fail the source relation where selection is governed;
10. wrong checkpoint/head/objective/runtime/method identity;
11. projection architecture/state corruption and post-projection numerical mismatch;
12. deterministic-reference cases where (V_R=0) but the fixed tolerance floor remains nonzero;
13. FP64 transition evidence if FP64 CuEq TRAIN2 remains supported.

The number/order of fresh processes and repeats is frozen before outcomes are inspected. Failure is evidence, not permission to rerun until pass.

## 14. D2 -> D3 handoff if accepted

D3/D4 shall prefer reduction over additive machinery:

- replace the current Rev86 TRAIN2 authorizing reducer rather than stacking Candidate 2 above it;
- retain old Rev83-86 record schemas only for historical deserialization/diagnosis;
- remove TRAIN2 descriptor/FPS hard-gating when no TRAIN2 consumer exists;
- use one canonical TRAIN2 transition-qualification owner;
- reuse CampaignStore/currentness machinery and add only missing method/applicability identity;
- keep source/DATA6 calculator parity and trained-state projection relations separate;
- preserve no-silent-fallback behavior;
- preserve the generated source `e3nn` / TRAIN2 `cueq` policy unless its owning policy is separately changed;
- correct EVAL2 measurement identity to the actual portable e3nn forward without retraining an otherwise authenticated root.

## 15. Acceptance state

Candidate 2 is **not accepted**.

Required next steps:

1. fresh independent numerical Review of this exact candidate;
2. semantic repair under a new candidate identity if Review finds a blocker;
3. fresh Stage-C target-host evidence under the immutable reviewed candidate;
4. explicit stakeholder ratification of the exact reviewed/passing target;
5. only then D3/D4 concretization.

Until then, current executable doctor remains fail-closed and the explicit e3nn TRAIN2 override remains the bounded safe operational route.
