---
kind: proposed-D2-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_NOT_ACCEPTED
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
candidate_id: MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-4
date: 2026-09-24
parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
parent_d2_exact_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
stage_a_cross_family_basis: 24734c8113dfaeaba4ae32c2bb0b80f3c0c72e82
supersedes_proposed_candidate: MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-3
human_ratification_required: true
---

# Proposed D2 acceleration-equivalence overlay for MACE e3nn / CuEq execution

## 1. Lifecycle and scope

This document is a **proposed** bounded D2 overlay. It is not accepted current authority and cannot authorize CuEq execution by repository presence alone.

Candidate 4 supersedes unreviewed Candidates 1, 2 and 3.

Author-side Challenge history:

- Candidate 1 incorrectly used ordinary e3nn realization RMS as the margin for persistent backend bias and compared raw gradient coordinates as the main training consequence.
- Candidate 2 separated persistent bias from noise and moved to a two-update state-transition witness, but a second author Challenge found three remaining defects: no explicit rare-outlier materiality guard; an unnecessarily permissive factor-two stochastic-variance rule; and a potentially circular measurement dependency that could re-import source/DATA6 descriptor/FPS acceptance through the projection relation.

Candidate 3 repaired those defects. A final author-readiness audit against accepted P5 exposure semantics and real-owner evidence then found that it still under-specified how two-update batches are obtained and how the transient->portable measurement transform is independently falsified. Candidate 4 repairs those remaining scope/oracle gaps before independent Review.

The overlay concretizes the accepted D2 rule that a native backend is execution-only only under a source-closed numerical-equivalence relation. It changes the challenged TRAIN2 relation while source-closing adjacent supported acceleration relations. It does not change D1 scientific meaning, MACE training objectives, replay semantics, checkpoint ranking, CV thresholds or publication policy.

The relation family is split by protected consequence:

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
(	heta',q'),
]

where:

- (bin{R,C}) is e3nn reference or pure CuEq candidate;
- (	heta) is exact model state;
- (q) is accepted optimizer/EMA/scheduler/RNG state;
- (omega) is the exact frozen exposure/objective input for one optimizer update.

The backend-specific forward/backward graph is part of (mathcal T_b). Optimizer/EMA semantics are held identical rather than redefined here.

Every mutable transient CuEq state item capable of influencing a later TRAIN2 update must either be represented by ((	heta',q')) or be an exact deterministic function of represented state plus immutable configuration. A hidden mutable CuEq-only state outside this closure makes the transition witness incomplete and fails qualification.

### D2.CUEQ.DEF.006 — minimum stateful transition witness

A qualification observation resets exact ((	heta,q)), executes two frozen optimizer updates,

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

Two updates are the minimum witness because update 1 populates stateful optimizer/EMA recurrence and update 2 consumes non-initial recurrence state.

Every observation must retain finite loss, optimizer-consumed gradients, model parameters, optimizer state and EMA state. Non-finite state is hard failure.

### D2.CUEQ.DEF.007 — common state-transfer measurement transform

Transient e3nn/CuEq parameterizations need not have identical storage coordinates. TRAIN2 transition evidence therefore uses one canonical state-transfer transform

$$
P_b:\theta_b\mapsto\tilde\theta_b,
$$

where $\tilde\theta_b$ is the canonical portable e3nn model coordinate.

For e3nn, $P_R$ is identity. For CuEq, $P_C$ is the existing dependency-native transfer into an already reconstructed canonical portable shell.

For use as a **measurement transform**, every mapped CuEq state used by the qualification functional must satisfy:

1. exact canonical portable-shell architecture identity before/after transfer;
2. complete transfer of every mutable model state that can affect the portable function;
3. deterministic mapping for fixed transient state/configuration;
4. direct transient-CuEq versus mapped-portable-e3nn energy/atom, force and stress agreement on a frozen mapping-witness corpus under the dtype mixed envelope of D2.CUEQ.DEF.013;
5. no source/DATA6 descriptor/FPS acceptance criterion imported merely by using the transform.

In addition, at least one nontrivial state per claimed dtype/topology is checked by a separate dependency-native differential route against pinned MACE conversion semantics/state values. This is supporting anti-common-mode evidence; the direct transient-versus-mapped physical check above remains required for every measured state.

The broader trained-state deployment/projection relation remains separately governed by D2.CUEQ.DEF.023.

This separation prevents circularity: TRAIN2 does not pass or fail because a source-selection descriptor moved, while a defective state-transfer mapping cannot make the training-transition oracle silently self-consistent.
### D2.CUEQ.DEF.008 — functional observation of the transition

Let (E) be the fixed portable-e3nn evaluator on a frozen witness corpus/head.

For a bound starting state (S), compute one common baseline

[
y^{(0)}=E(	heta^{(0)}).
]

After update (kin{1,2}),

[
y_b^{(k)}=E(P_b(	heta_b^{(k)})),
]

and define update-induced displacement

[
Delta y_b^{(k)}
=
y_b^{(k)}-y^{(0)}.
]

The governed transition channels are energy/atom, force and stress displacement vectors at both (k=1) and (k=2).

Using displacement rather than absolute post-step prediction prevents a large common baseline from masking a materially different training update.

The portable shell and evaluator are reset/reconstructed according to the frozen measurement protocol for every retained observation so measurement-state reuse cannot create a backend-specific hidden input.

### D2.CUEQ.DEF.009 — TRAIN2 descriptors are not an authorizing channel

Invariant descriptors and FPS fingerprints are not consumed by the current TRAIN2 optimizer. They therefore do not belong to the TRAIN2 backend-equivalence predicate.

They may remain diagnostics. They remain hard under D2.CUEQ.DEF.003-004 where descriptor geometry/selection is actually consumed.

A future TRAIN2 design that consumes descriptors reopens this definition.

## 5. Frozen finite-sample qualification design

### D2.CUEQ.DEF.010 — experimental unit, exposure trace and order cells

The independent experimental unit is the **fresh process**.

Before any CuEq numerical outcome is inspected, build the qualification exposure trace through the real accepted TRAIN2 loader owner from exact authenticated corpus/configuration identity.

For replay-enabled current P5 the trace preserves the accepted numerical exposure semantics:

$$
D_{\mathrm{train}}=D_r\Vert D_t,
$$

with `pt_head`/replay first and target second before shuffle, the accepted seed and shuffle/sampler semantics, exact batch size, no implicit target duplication, and `drop_last=true`. Target-only training uses its accepted target-only loader semantics.

Qualification windows are **not hand-built batches**. From the reference-only trace, select the smallest deterministic set of consecutive two-update windows that covers every active head/property-mask branch capable of reaching the optimizer. The selection rule may inspect only frame/head/property metadata and the accepted exposure order. It may not inspect e3nn/CuEq numerical results. At least one native consecutive window is mandatory even if supplemental windows are needed for branch coverage.

Qualification is balanced over four cells defined by:

1. which training realization is constructed first; and
2. which complete backend witness is executed first.

For each cell:

- 5 fresh processes;
- 1 discarded warm-up per backend;
- 3 retained observations per backend/window/state;
- exact model/optimizer/EMA/RNG reset for every retained transition observation;
- the same harvested two-update window supplied to e3nn and CuEq;
- no early stopping;
- no outcome-selected reruns.

Projection/evaluation occurs as part of each backend witness under the common frozen measurement transform; the baseline portable evaluation for a retained observation is common to both backends.

Thus 20 fresh processes are independent units and repeated observations are nested measurements. Additional branch/state windows multiply nested observations, not the process count.

The relation is a deterministic finite-sample qualification functional. It does not interpret all-pairs or retained-observation cardinality as an inferential independent-sample count.
### D2.CUEQ.DEF.011 — canonical reduction arithmetic

All qualification reductions are performed in canonical IEEE-754 binary64 control arithmetic.

The iteration order is fixed lexicographically by:

[
(	ext{cell identity},	ext{process replicate},	ext{retained repeat},	ext{component index}).
]

Centroid and sum-of-squares accumulation order is therefore part of the method identity. D3 may use a mathematically equivalent more accurate summation only after exact decision-equivalence is established for the accepted boundaries.

### D2.CUEQ.DEF.012 — vector notation

For governed vector channel (c), let

[
x_{b,h,p,r,c}inmathbb R^{m_c}
]

be the retained observation for backend (b), order cell (h), fresh process (p), repeat (r).

This notation covers:

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

### D2.CUEQ.DEF.013 — dtype mixed envelope

Let ((r_d,a_d)) be:

- FP32: (r_d=10^{-5}), (a_d=10^{-6});
- FP64: (r_d=10^{-10}), (a_d=10^{-12}).

For reference vector (z), define

[
	au_{d,j}(z)=a_d+r_d|z_j|.
]

A candidate vector (w) is persistently equivalent to (z) iff

[
|w_j-z_j|
le
	au_{d,j}(z)
qquadorall j.
]

The numerical constants are inherited from the existing dtype calculator precision scale. Their application to TRAIN2 transition centroids is a **new proposed D2 use** and must be independently falsified; it is not represented as having been previously accepted for training-state transitions.

### D2.CUEQ.DEF.014 — global and cell centroid guards

Every governed channel must satisfy

[
mu_{C,c}approx_dmu_{R,c},
]

and for every order cell (h),

[
mu_{C,h,c}approx_dmu_{R,h,c},
]

using D2.CUEQ.DEF.013 componentwise.

Opposite order-conditioned backend biases therefore cannot cancel into a passing global mean.

A systematic centroid shift never receives a larger margin merely because realization noise is large.

## 7. Stochastic non-degradation

### D2.CUEQ.DEF.015 — fixed dtype tolerance scale

For channel (c), form the tolerance vector around the e3nn global centroid,

[
t_{c,j}=a_d+r_d|mu_{R,c,j}|,
]

and its RMS-square scale

[
T_c^2
=
rac1{m_c}sum_j t_{c,j}^2.
]

(T_c) is fixed by accepted dtype numerical scale and e3nn reference magnitude. Candidate observations do not set it.

### D2.CUEQ.DEF.016 — additional stochastic variance budget

Pass requires

[
V_{C,c}
le
V_{R,c}+T_c^2
]

and

[
V_{C,h,c}
le
V_{R,c}+T_c^2
qquadorall h.
]

Thus candidate stochastic variability may exceed accepted e3nn variability by at most one fixed dtype-tolerance-sized variance budget.

This handles deterministic-reference cases without inventing an epsilon and is strictly candidate-independent.

No tail percentile, all-pairs pseudo-count, pooled candidate denominator, variance ratio, or family threshold table is authoritative.

## 8. Catastrophic/materiality guard

### D2.CUEQ.DEF.017 — accepted property-scale guard

The accepted TRAIN2 robust-loss property transition scales are:

- energy: (delta_E=0.01;mathrm{eV/atom});
- force: (delta_F=0.01;mathrm{eV/AA});
- stress: (delta_S=0.01;mathrm{eV/AA^3}).

For every retained **paired same-process/same-repeat** e3nn/CuEq observation, the maximum absolute backend discrepancy in each physical channel, including update-induced displacement channels, must remain strictly below its corresponding (delta).

This is a gross catastrophic/materiality guard only. It is not the ordinary numerical equivalence envelope and may not be lowered/raised from the candidate observations.

The purpose is to reject rare discrepancies large enough to reach the accepted property-loss regime scale even if centroid/variance aggregation would dilute them.

Non-finite values remain hard failure independently.

## 9. Objective, branch and state coverage

### D2.CUEQ.DEF.018 — real TRAIN2 objective and exposure coverage

Every two-step transition witness uses the real accepted TRAIN2 objective and exact inputs: checkpoint/head set, labels, E0, objective weights, masks, optimizer, EMA, scheduler, dtype and the loader-derived window of D2.CUEQ.DEF.010.

For replay-enabled multi-head P5, replay/target membership, `pt_head`-first then target-second pre-shuffle indexing, accepted seeded shuffle, `drop_last`, and realized two-batch example/head order are part of witness identity. A target-first reorder, balancing sampler, duplicated target sample, hand-assembled branch batch, or other exposure substitution is non-equivalent evidence.

Every active objective/head/property-mask branch capable of reaching the optimizer must appear in at least one predeclared loader-derived window. The coverage scan is performed on reference-independent metadata before CuEq outcomes are available.

The frozen portable witness corpus must include all geometries used by the selected two-update windows plus additional predeclared structures sufficient to expose the claimed head/property behavior. Witness membership/order cannot be selected from CuEq outcomes.

A source-selected descriptor proxy, calculator-only check or synthetic batch that bypasses the real loader cannot substitute.
### D2.CUEQ.DEF.019 — starting state

(S_0) is the exact authenticated pre-TRAIN2 model state for the claimed architecture/head topology.

A passing (S_0) witness establishes entry-state transition equivalence only.

### D2.CUEQ.DEF.020 — non-initial state

A full TRAIN2 operator claim additionally requires at least one authenticated non-initial state (S_1) for each materially distinct claimed architecture/head topology.

(S_1):

- differs from (S_0) in authenticated model state;
- is obtained independently of the candidate acceptance outcome;
- may come from bounded e3nn-only adaptation or still-applicable authenticated trained-state evidence;
- uses the same architecture/head/objective family being claimed; and
- must change at least one governed portable-e3nn witness output relative to (S_0) by more than the D2.CUEQ.DEF.013 dtype envelope, so a numerically trivial state cannot satisfy non-initial coverage.

Starting-state evidence alone cannot be represented as proof over optimizer-reachable trained states.

Contradictory later paired-training evidence reopens the relation even though historical CUEQ-PHASE1 is not a universal doctor prerequisite.

## 10. Dtype semantics

### D2.CUEQ.DEF.021 — FP32 TRAIN2

FP32 pure-CuEq TRAIN2 authorization uses D2.CUEQ.DEF.005-020.

If this candidate is accepted, the Rev86 TRAIN2 authorizing statistics are retired:

- fixed (10^{-6}) stable-channel maximum;
- force p99/p99.9 ratio (1.25);
- Fmax self factor (1.5);
- fixed (10^{-4}) Fmax ceiling.

They remain historical diagnostics only.

No family-specific replacement threshold is introduced.

### D2.CUEQ.DEF.022 — FP64 TRAIN2

FP64 retains the existing forward calculator envelope
(mathrm{rtol}=10^{-10}), (mathrm{atol}=10^{-12}).

That forward guard is not sufficient by itself to establish an equivalent training-state transition. FP64 CuEq TRAIN2 must satisfy D2.CUEQ.DEF.005-020 or D3/D4 must explicitly narrow support.

This strengthens source closure without relaxing FP64 numerical tolerance.

## 11. Trained-state deployment projection / EVAL2

### D2.CUEQ.DEF.023 — deployment projection relation

For a completed CuEq-trained checkpoint:

1. authenticate the transient CuEq realization and state before it controls inference;
2. reconstruct the canonical portable e3nn shell from accepted configuration;
3. transfer state through the pinned dependency-native CuEq -> e3nn transfer owner;
4. require exact canonical portable-shell architecture identity;
5. require the existing dtype-appropriate post-transfer calculator parity relation that currently governs deployment projection;
6. execute EVAL2 under provider identity `e3nn`, because that is the actual numerical forward.

The numerical values of this existing deployment relation are not changed by the current TRAIN2 incident.

D2.CUEQ.DEF.007 uses only the independently qualified state-transfer mapping as a measurement transform; it does not make source/DATA6 descriptor/FPS parity a TRAIN2 protected consequence.

## 12. Qualification versus routine doctor admission

### D2.CUEQ.DEF.024 — qualification record

The multi-process functional authorizes only when all required role/state/dtype channels pass.

Its identity binds at least:

- D2 method digest;
- CUEQ-DEP1/runtime identity and arithmetic-relevant MACE/Torch/CUDA/CuEq component/source identities;
- device precision/determinism/TF32/matmul state where material;
- dtype and resolved CuEq kernel;
- model architecture/head topology;
- (S_0) and (S_1) applicability;
- TRAIN2 objective/exposure identity;
- frozen training sequences and portable witness corpus;
- construction/execution-order design and cardinality;
- state-transfer measurement-transform qualification.

A changed binding stales the record.

### D2.CUEQ.DEF.025 — routine witness

Routine campaign doctor need not rerun the 20-process qualification experiment on every invocation.

It may:

1. authenticate a current qualification whose applicability contains the requested realization; and
2. run a cheaper bounded execution witness for current checkpoint/head/objective/runtime reachability and finite forward/backward execution.

The routine witness cannot estimate a new envelope, widen a failed qualification, retry until pass, or substitute descriptor/FPS parity for the training transition relation.

Exact persistence/routing belongs to D3/D4.

## 13. Evidence role of Stage A

Authenticated MH-1 and MPA-0 Stage-A artifacts are **method-design evidence**, not acceptance evidence for Candidate 3.

They establish model-family-dependent absolute FP32 discrepancy, similar normalized stochastic decomposition, material process/order covariance, failure of the fixed (10^{-6}) stable-channel interpretation, and fragility of tail/max reduction.

They do not contain two-update training-state transitions. Fresh candidate-bound evidence is required after Candidate 3 is frozen.

## 14. Stage-C falsification obligations

Before acceptance, fresh target-host evidence must attempt to falsify at least:

1. MACE-MH-1 / `omat_pbe`, FP32, (S_0) and (S_1);
2. MACE-MPA-0-medium / `default`, FP32, (S_0) and (S_1);
3. every active target/replay/head/property branch capable of reaching the optimizer;
4. persistent global centroid bias outside D2.CUEQ.DEF.013;
5. opposite order-cell biases that cancel globally;
6. candidate stochastic variance above (V_R+T^2);
7. a single rare paired discrepancy above the accepted property-scale guard while aggregate centroids/variance otherwise pass;
8. a defect that appears only on update 2 after recurrence state is populated;
9. descriptor-only drift with otherwise equivalent transition — this must not fail TRAIN2 solely because descriptor coordinates differ;
10. source/DATA6 descriptor/FPS drift — this must fail the source relation where selection is governed;
11. wrong checkpoint/head/objective/runtime/method identity;
12. incomplete/hidden transient state not represented by the state-transfer measurement mapping;
13. deployment projection architecture/state corruption and post-projection numerical mismatch;
14. deterministic-reference cases with zero (V_R);
15. FP64 transition evidence if FP64 CuEq TRAIN2 remains supported.

The number/order of fresh processes and repeats is frozen before outcomes are inspected. Failure is evidence, not permission to rerun until pass.

## 15. D2 -> D3 handoff if accepted

D3/D4 shall prefer reduction over additive machinery:

- replace the current Rev86 TRAIN2 authorizing reducer rather than stacking Candidate 3 above it;
- retain old Rev83-86 record schemas only for historical deserialization/diagnosis;
- remove TRAIN2 descriptor/FPS hard-gating when no TRAIN2 consumer exists;
- use one canonical TRAIN2 transition-qualification owner;
- reuse CampaignStore/currentness machinery and add only missing method/applicability identity;
- reuse the existing dependency-native transient->portable state-transfer owner; do not add a second projection implementation;
- keep source/DATA6 calculator parity and deployment projection relations separate;
- preserve no-silent-fallback behavior;
- preserve the generated source `e3nn` / TRAIN2 `cueq` policy unless its owning policy is separately changed;
- correct EVAL2 measurement identity to the actual portable e3nn forward without retraining an otherwise authenticated root.

## 16. Acceptance state

Candidate 4 is **not accepted**.

Required next steps:

1. fresh independent numerical Review of this exact Candidate 4;
2. semantic repair under a new candidate identity if Review finds a blocker;
3. fresh Stage-C target-host evidence under the immutable reviewed candidate;
4. explicit stakeholder ratification of the exact reviewed/passing target;
5. only then D3/D4 concretization.

Until then, current executable doctor remains fail-closed and the explicit e3nn TRAIN2 override remains the bounded safe operational route.
