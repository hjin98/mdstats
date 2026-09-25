---
kind: proposed-D2-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_NOT_ACCEPTED
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
candidate_id: MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-5
date: 2026-09-24
parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
parent_d2_exact_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
stage_a_cross_family_basis: 24734c8113dfaeaba4ae32c2bb0b80f3c0c72e82
supersedes_reviewed_candidate_commit: cd4e0453d0a27ae01f7041c1c9d222fd9d71a0e9
superseded_candidate_review: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R1.md
human_ratification_required: true
---

# Proposed D2 acceleration-equivalence overlay for MACE e3nn / CuEq execution — Candidate 5

## 1. Lifecycle, authority, and scope

This document is a **proposed** bounded D2 overlay. It is not accepted-current authority and cannot authorize CuEq execution by repository presence alone.

Candidate 5 supersedes reviewed Candidate 4 after the fresh independent Review returned NO-PASS. Candidate 4 remains immutable historical evidence at:

`cd4e0453d0a27ae01f7041c1c9d222fd9d71a0e9`.

Candidate 5 repairs only the D2 numerical-method defects identified by that Review. It does not change D1 scientific meaning, MACE training objectives, replay semantics, checkpoint ranking, cross-validation thresholds, production threshold policy, target-size selection, or publication policy.

The acceleration-equivalence family remains separated by protected consequence:

1. source/DATA6 calculator equivalence;
2. TRAIN2 training-state-transition equivalence; and
3. completed-state CuEq-to-portable-e3nn projection/EVAL2 equivalence.

A pass in one role never authorizes another.

Candidate 5 deliberately narrows current TRAIN2 CuEq support:

- **FP32 TRAIN2 is the only TRAIN2 dtype proposed for qualification.**
- **FP64 CuEq TRAIN2 is unsupported by this candidate** and must fail closed unless a future independently reviewed D2 candidate operator-qualifies it.
- source/DATA6 FP32 and FP64 remain separate proposed sibling relations.
- completed-state projection/EVAL2 applies only to a state produced by a TRAIN2 relation that is itself current and qualified.

The Stage-A MH-1 and MPA-0 observations remain method-design evidence only. They are not Candidate-5 acceptance evidence and do not determine Candidate-5 thresholds.

## 2. Common relation family

### D2.CUEQ5.DEF.001 — relation key

An acceleration-equivalence member is keyed by

$$
A=(r,d,s,k,o,\rho,m),
$$

where:

- \(r\) is semantic role;
- \(d\) is learned-model dtype;
- \(s\) is qualified model/training-state class;
- \(k\) is resolved kernel realization;
- \(o\) is governed consumer/objective identity;
- \(\rho\) is arithmetic-relevant runtime identity; and
- \(m\) is the exact Candidate-5 method identity.

Evidence from a different key is stale or non-applicable for this member.

### D2.CUEQ5.DEF.002 — exact common inputs

Reference e3nn and candidate pure-CuEq observations compare only when all non-backend inputs are identical:

- architecture/head topology;
- exact starting model state;
- exact optimizer, exponential-moving-average (EMA), scheduler/counter, and random-number-generator state;
- structure/batch membership and order;
- labels, E0, objective coefficients, masks, and property availability;
- accepted preprocessing;
- dtype;
- loader/exposure identity; and
- every other numerical input owned upstream.

Backend/kernel realization is the deliberate independent variable. Any mismatch outside that variable is typed evidence failure, not numerical disagreement.

### D2.CUEQ5.DEF.002A — TRAIN2 physical numerical budget declaration

For later TRAIN2 definitions, let the accepted property residual scales be

$
\delta_E=0.01\ \mathrm{eV/atom},
\qquad
\delta_F=0.01\ \mathrm{eV/\mathring A},
\qquad
\delta_S=0.01\ \mathrm{eV/\mathring A^3}.
$

Let \(u_d\) be machine epsilon for learned-model dtype \(d\).

Candidate 5 proposes the fixed physical numerical budget

$
\epsilon_{c,d}=\delta_c\sqrt{u_d},
\qquad c\in\{E,F,S\}.
$

This declaration makes \(\epsilon_{c,d}\) source-available before later transfer, transition, stochastic, and outlier predicates use it.

Its numerical rationale and FP32 resolved value are stated in D2.CUEQ5.DEF.013. The declaration is a proposed D2 method coordinate, not an accepted theorem and not Candidate-outcome fitted.

## 3. Proposed source/DATA6 sibling relations

Candidate 5 does **not** describe these relations as already accepted D2 authority. It proposes them for source closure because historical operational behavior alone cannot promote itself into D2.

### D2.CUEQ5.DEF.003 — proposed source/DATA6 FP32 relation

For source-foundation inference, DATA6 descriptor execution, pseudolabel execution when separately authorized, and another role that actually consumes calculator descriptors/selection:

- energy/atom, force, stress, and invariant descriptors compare componentwise with
  \(\mathrm{rtol}=10^{-5}\) and \(\mathrm{atol}=10^{-6}\);
- all compared outputs are finite and shape-compatible; and
- the deterministic descriptor/FPS protected consequence is exact under its accepted selection fraction \(1/2\), tie semantics, and tie tolerance \(10^{-12}\).

The numerical relation is direct-forward output equivalence, not a training-state relation. Descriptor coordinate differences are acceptable only when the exact governed descriptor/FPS selection consequence is preserved.

These constants are proposed from the existing bounded ACCEL1 operational contract and must be independently reviewed as D2 numerical authority. A historical D4 pass is evidence, not authority.

### D2.CUEQ5.DEF.004 — proposed source/DATA6 FP64 relation

The same source/DATA6 relation uses

$$
\mathrm{rtol}=10^{-10},
\qquad
\mathrm{atol}=10^{-12}
$$

for FP64, with exact selection consequence unchanged.

FP64 source/DATA6 evidence does not imply FP64 TRAIN2 support.

### D2.CUEQ5.DEF.005 — sibling evidence requirement

Before either source/DATA6 sibling is accepted as D2 authority, its protected consequence must be freshly or still-applicably demonstrated under exact model/runtime/dtype identity.

If no current source/DATA6 evidence exists for a claimed key, that sibling remains unqualified without affecting an independently qualified TRAIN2 key.

## 4. TRAIN2 protected state

### D2.CUEQ5.DEF.006 — complete TRAIN2 state

For TRAIN2 define complete mutable numerical state

$$
\Xi=(\theta,q_{\rm opt},q_{\rm ema},q_{\rm sched},q_{\rm rng},q_{\rm backend}),
$$

where:

- \(\theta\) is model state;
- \(q_{\rm opt}\) is all optimizer state capable of affecting a later update;
- \(q_{\rm ema}\) is EMA shadow state when enabled;
- \(q_{\rm sched}\) contains scheduler state, step counters, and other update-index state;
- \(q_{\rm rng}\) is accepted Python/NumPy/Torch/device random-number-generator state; and
- \(q_{\rm backend}\) is any mutable backend-specific state capable of influencing later TRAIN2 arithmetic.

For backend \(b\in\{R,C\}\),

$$
\mathcal T_b:(\Xi,\omega)\mapsto\Xi',
$$

where \(\omega\) is one exact accepted optimizer-update exposure/objective input.

Every mutable item capable of affecting a later update must be represented in \(\Xi\), or proved to be an exact deterministic function of represented state plus immutable configuration. Unrepresented mutable backend state makes the relation unqualifiable.

### D2.CUEQ5.DEF.007 — exact discrete state consequences

The following compare by exact identity after every governed update:

- scheduler phase and counters;
- optimizer step counters where their semantics are exact integers;
- RNG states/positions when the accepted method requires identical stochastic exposure;
- property/head masks and active-branch identity;
- accepted batch/example/head order; and
- any exact discrete backend state.

A backend that consumes a different random stream or advances a governed counter differently is non-equivalent evidence even when immediate predictions look close.

## 5. Canonical portable observation and non-invasive state transfer

### D2.CUEQ5.DEF.008 — portable live-model transform

Let

$$
P_b:\theta_b\mapsto\widetilde\theta_b
$$

map a model state into the canonical portable-e3nn model coordinate.

For e3nn, \(P_R\) is identity. For CuEq, \(P_C\) is the dependency-native CuEq-to-e3nn state-transfer owner applied to an immutable snapshot.

Every mapped state must satisfy all of:

1. exact canonical architecture/head identity;
2. an explicit complete inventory of every parameter and buffer affecting the portable forward;
3. one-to-one source-to-destination correspondence for that inventory;
4. deterministic transfer for fixed source state/configuration;
5. exact source-state identity before and after transfer, proving that the measurement is non-mutating;
6. direct transient-CuEq versus mapped-portable-e3nn energy/atom, force, and stress parity under D2.CUEQ5.DEF.013-014; and
7. no descriptor/FPS TRAIN2 acceptance criterion imported through the mapping.

A transfer that drops a quiescent tensor still fails structural completeness even if a finite witness corpus does not expose it.

### D2.CUEQ5.DEF.009 — independent anti-common-mode transfer oracle

At least one nontrivial state for every claimed topology must also be checked by a state-transfer route that is independent of \(P_C\)'s implementation and mapping-table generator.

The same independence requirement applies to the optimizer-state transfer used by D2.CUEQ5.DEF.011-012: at least one nontrivial state must receive an independently implemented inventory/value check of optimizer state keyed by canonical portable parameter identity. A second check that calls the same optimizer-state mapper or consumes the same generated mapping table is correlated evidence, not an independent oracle.

It may use pinned-MACE conversion only if that route does **not** call the same transfer owner or derive its state mapping from the same generated source.

If no independent route exists, the claimed anti-common-mode check is unavailable rather than silently counted twice.

The independent route must compare:

- canonical architecture identity;
- full transferable tensor/buffer inventory; and
- canonical state values under the exact mapping semantics.

### D2.CUEQ5.DEF.010 — EMA observation

When EMA is enabled, define portable EMA state

$$
\widetilde\theta^{\rm ema}_b=P_b(\theta^{\rm ema}_b).
$$

EMA is an authorizing physical-function channel, not merely a finiteness guard.

At every governed state where live-model E/F/stress is observed, the same frozen portable witness is evaluated from the EMA state. An EMA-only discrepancy therefore cannot pass while the live model agrees.

## 6. Optimizer-state observability without raw-coordinate authority

### D2.CUEQ5.DEF.011 — canonical optimizer-action probe

Raw optimizer moments are not made the primary backend-equivalence observable because transient backend parameter storage can differ.

Instead, for every state after the second backend-specific update, Candidate 5 requires an **optimizer-action probe** on an immutable snapshot.

Construct a canonical portable-e3nn training shell whose:

- live model is \(P_b(\theta_b)\);
- optimizer state is transferred by semantic portable-parameter identity;
- scheduler/counters are restored exactly;
- EMA state is restored through the same portable parameter identity; and
- no state is taken from object identity or incidental module ordering.

The optimizer-state transfer must have an explicit complete inventory. A state item that cannot be mapped to a canonical portable parameter identity makes qualification fail closed.

### D2.CUEQ5.DEF.012 — common-gradient action functional

For frozen canonical probe gradient set \(G^*=\{g_1^*,\ldots,g_L^*\}\), define

$$
\mathcal A(q_{\rm opt},q_{\rm sched},\widetilde\theta;g^*)
$$

as one optimizer/scheduler action using the **same assigned canonical gradient** \(g^*\), without running a backend-specific forward/backward pass.

The probe set includes:

1. a zero-gradient probe, exposing weight decay, momentum carry, counters, and scheduler-only effects; and
2. the canonical e3nn gradients from every selected real TRAIN2 exposure-window branch used by the qualification.

For each probe, compare the resulting portable live-model and EMA E/F/stress function under D2.CUEQ5.DEF.013-014.

This functional readout closes latent optimizer-state differences that are finite and not yet visible in the live model.

The action probe is measurement-only. It never mutates the live qualification trajectory.

## 7. Physical numerical scale for TRAIN2

### D2.CUEQ5.DEF.013 — precision-scaled property materiality rationale

TRAIN2 does not reuse the source-calculator `rtol/atol` relation on update centroids.

D2.CUEQ5.DEF.002A declares

$
\epsilon_{c,d}=\delta_c\sqrt{u_d}.
$

The construction uses the accepted property-residual scale only as a dimensional reference and scales it by \(\sqrt{u_d}\), so the proposed numerical budget vanishes under precision refinement and remains far below the robust-loss transition itself.

For FP32, \(u_{32}=2^{-23}\), giving approximately

$
\epsilon_{E,32}=\epsilon_{F,32}=\epsilon_{S,32}
\text{ numerically }3.45\times10^{-6}
$

in their respective physical units.

For FP64 source calculations this formula is informative only; FP64 TRAIN2 is not authorized by Candidate 5.

The relation is a **proposed precision-scaled materiality heuristic**, not a theorem of floating-point error propagation. It is fixed before Candidate-5 Stage-C CuEq outcomes and must be independently challenged for adequacy.

### D2.CUEQ5.DEF.014 — no near-zero relative-tolerance escape

TRAIN2 persistent-bias and outlier guards use \(\epsilon_{c,d}\) as a physical absolute scale.

No relative term based on a near-zero update displacement is used.

This prevents a large baseline prediction from hiding a training update and prevents an arbitrary source-calculator absolute floor from being transferred to training-transition centroids.

## 8. Stateful TRAIN2 witness

### D2.CUEQ5.DEF.015 — two committed updates plus state readouts

From exact starting state \(\Xi^{(0)}\), execute two exact accepted loader-derived optimizer updates:

$$
\Xi_b^{(1)}=\mathcal T_b(\Xi^{(0)},\omega_1),
$$

$$
\Xi_b^{(2)}=\mathcal T_b(\Xi_b^{(1)},\omega_2).
$$

Two committed updates remain the minimum local backend-specific recurrence witness because update 1 creates non-initial optimizer/EMA recurrence state and update 2 consumes it.

Candidate 5 no longer claims that two live-model observations alone prove complete recurrence equivalence.

After update 2, the immutable state snapshot is additionally subjected to:

- exact discrete-state comparison;
- live-model portable physical-function comparison;
- EMA portable physical-function comparison;
- canonical optimizer-action probes; and
- state-transfer completeness/non-mutation checks.

The added state readouts, not a gratuitously longer backend-specific horizon, close the latent-state false pass.

### D2.CUEQ5.DEF.016 — update-induced physical displacement

Let \(E\) be the fixed portable-e3nn evaluator on frozen witness corpus/head.

For starting state \(S\),

$$
y^{(0)}=E(P_R(\theta^{(0)})).
$$

After update \(k\in\{1,2\}\),

$$
y_b^{(k)}=E(P_b(\theta_b^{(k)})),
$$

and

$$
\Delta y_b^{(k)}=y_b^{(k)}-y^{(0)}.
$$

Required live-model channels are energy/atom, force, and stress for:

- the starting state;
- \(\Delta y^{(1)}\);
- \(\Delta y^{(2)}\); and
- every optimizer-action probe result.

The corresponding EMA channels are required whenever EMA exists.

### D2.CUEQ5.DEF.016A — bounded recurrence-horizon adaptation

The local two-update witness is not, by itself, allowed to certify a backend whose small coherent update bias would accumulate materially over many optimizer updates.

For each state anchor, define the slowest active exponential recurrence factor

$
\beta_{\max}
=
\max\{\beta:\beta\text{ is an active optimizer-moment or EMA recurrence factor}\}.
$

When such recurrence exists, define the recurrence-horizon update count

$
H_{\rm rec}
=
\max\left(2,\left\lceil\frac{1}{1-\beta_{\max}}\right\rceil\right).
$

This is the e-folding-scale update count of the slowest accepted first-order recurrence. It is a numerical reason for a longer bounded witness, not a generic "more is safer" multiplier.

If no exponential recurrence is active, \(H_{\rm rec}=2\).

From each state anchor, let \(H\) be the smaller of \(H_{\rm rec}\) and the number of accepted optimizer updates remaining in the anchor's reference trajectory.

For one predeclared native loader continuation per anchor and order cell, each fresh process executes the same accepted exposure for \(H\) backend-specific updates from the exact anchor state.

Physical live-model and EMA channels are observed at

$
K_H=\{1,2,4,8,\ldots,2^j\le H\}\cup\{H\}.
$

The continuation is fixed from the reference loader trace before CuEq outcomes and retains all scheduler/epoch transitions encountered naturally.

This bounded adaptation is qualification-only evidence. It is not inserted into ordinary production training.

### D2.CUEQ5.DEF.016B — coherent-drift growth guard

For ensemble \(e\), order cell \(h\), channel \(c\), checkpoint \(k\in K_H\), fresh process \(p\), and nested repeat \(r\), let retained physical observation be \(x_{b,e,h,p,r,c}(k)\).

Define the process mean

$
\bar x_{b,e,h,p,c}(k)
=
\frac{1}{R}\sum_{r=1}^{R}x_{b,e,h,p,r,c}(k),
\qquad R=3,
$

and the cell centroid

$
\mu_{b,e,h,c}(k)
=
\frac{1}{5}\sum_{p=1}^{5}\bar x_{b,e,h,p,c}(k).
$

Then define

$
d_{e,h,c}(k)
=
\mu_{C,e,h,c}(k)-\mu_{R,e,h,c}(k)
$

as the process-level backend-centroid difference in portable physical function.

Every observed horizon must satisfy

$
\|d_{e,h,c}(k)\|_{\rm RMS}
\le
\epsilon_{c,32}.
$

Define the maximum observed systematic secant growth

$
g_{e,h,c}
=
\max_{k_i<k_j}
\frac{
\|d_{e,h,c}(k_j)-d_{e,h,c}(k_i)\|_{\rm RMS}
}{
k_j-k_i
}.
$

Let \(U_{\rm rem}\) be the number of accepted optimizer updates remaining from the anchor to the end of its reference TRAIN2 horizon.

Pass additionally requires the conservative no-hidden-linear-accumulation bound

$
\|d_{e,h,c}(H)\|_{\rm RMS}
+
\max(0,U_{\rm rem}-H)\,g_{e,h,c}
\le
\epsilon_{c,32}.
$

This guard is deliberately one-sided against coherent accumulation: stochastic scatter may enlarge uncertainty, but it cannot be used to authorize an unresolved systematic growth rate.

Before CuEq results are inspected, the reference-only process ensemble must also have sufficient resolution for this claim. For each long-horizon cell/channel, define the RMS standard error of the reference process centroid. If that reference-only standard error exceeds

$
\epsilon_{c,32}/2,
$

the qualification result is

`INSUFFICIENT_REFERENCE_RESOLUTION`

rather than PASS or FAIL.

The fixed five-process-per-cell design may therefore authorize only when it can resolve the proposed physical numerical budget. A future larger-process design must be separately predeclared before observing its CuEq outcomes; it is not an outcome-selected rerun of the insufficient design.

The same recurrence-horizon and growth tests are repeated independently in both complete ensembles. Pooling cannot rescue an insufficient or failed ensemble.

## 9. State-domain applicability

### D2.CUEQ5.DEF.017 — reference-generated state anchors

Candidate 5 does not infer a theorem over all mathematically reachable states from one non-initial checkpoint.

For each materially distinct claimed topology/objective family, qualification uses authenticated **full** e3nn reference states:

1. \(S_0\): exact pre-TRAIN2 state;
2. \(S_M\): a mid-trajectory state from an e3nn-only reference TRAIN2 trajectory at the predeclared nearest complete update to one-half of the accepted training horizon; and
3. \(S_L\): a late nonterminal e3nn-only state at the predeclared latest update that still permits every required two-update exposure/probe.

Each anchor includes complete

$$
(\theta,q_{\rm opt},q_{\rm ema},q_{\rm sched},q_{\rm rng}).
$$

The anchor trajectory is generated independently of CuEq acceptance results.

If the accepted horizon is too short to yield three distinct anchors, every distinct reachable update state is used instead.

Each non-initial anchor must change at least one governed live-model or EMA portable witness channel relative to \(S_0\) by more than its \(\epsilon_{c,32}\) scale.

A passing qualification is therefore empirical evidence over the declared entry/mid/late state classes. It is not represented as proof of every possible optimizer-reachable state.

Contradictory later paired evidence reopens the relation.

## 10. Real TRAIN2 exposure

### D2.CUEQ5.DEF.018 — accepted loader is the only authorizing exposure owner

Before CuEq numerical outcomes are inspected, construct the qualification trace through the actual accepted TRAIN2 loader from authenticated corpus/configuration identity.

For replay-enabled current P5:

$$
D_{\rm train}=D_r\Vert D_t,
$$

with:

- replay/pretraining head first;
- target head second;
- accepted pre-shuffle combined index layout;
- accepted seed;
- accepted shuffle/sampler behavior;
- exact batch size;
- no target duplication;
- \(\mathrm{drop\_last}=\mathrm{true}\); and
- realized example/head order retained as evidence.

Target-only training uses its accepted target-only loader semantics.

Hand-built, target-first, replay-only, duplicated, balancing-sampler, or otherwise reconstructed lookalike batches are non-authorizing.

### D2.CUEQ5.DEF.019 — predeclared exposure-window set

For every state anchor, select consecutive two-update windows from reference-only metadata before CuEq outcomes.

The window set is the deterministic union of all applicable:

1. first native consecutive two-update window from the anchor;
2. last complete consecutive two-update window before the next epoch boundary;
3. a native window crossing an epoch/shuffle boundary when such a two-update window exists;
4. a window bracketing every scheduler-state discontinuity that can change update arithmetic;
5. metadata-extreme native windows for target fraction;
6. metadata-extreme native windows for total atom count and graph/edge count when those metadata are available from accepted loader inputs; and
7. the smallest additional set needed so every active head/property-mask branch capable of reaching the optimizer appears.

Duplicate windows are collapsed by exact ordered batch identity.

Selection may inspect only authenticated frame/head/property/exposure metadata and accepted loader order. It may not inspect e3nn/CuEq numerical outcomes.

At least one truly native consecutive window is mandatory even if boundary/branch windows add more coverage.

## 11. Fresh-process stochastic design

### D2.CUEQ5.DEF.020 — independent unit and nested repeats

The independent experimental unit is the **fresh process**.

Qualification remains balanced over four cells:

1. e3nn constructed first / e3nn witness executed first;
2. e3nn constructed first / CuEq witness executed first;
3. CuEq constructed first / e3nn witness executed first; and
4. CuEq constructed first / CuEq witness executed first.

For each cell and each complete ensemble:

- five fresh processes;
- one discarded warm-up per backend;
- three retained observations per backend/window/state;
- exact starting-state reset for every retained observation;
- identical accepted exposure supplied to both backends;
- no early stopping; and
- no outcome-selected rerun.

Retained repeats are nested measurements and never counted as independent processes.

### D2.CUEQ5.DEF.021 — two complete independent ensembles

An authorizing qualification requires **two independently launched complete ensembles** of the entire four-cell design.

Every hard predicate must pass separately in ensemble 1 and ensemble 2.

Pooling the two ensembles may be reported diagnostically but may not rescue a failed ensemble.

A failed or insufficient ensemble cannot be replaced by an outcome-selected rerun.

The two-ensemble rule is a classification-stability guard for the new transition observable. It is not inherited from Stage A.

## 12. Process-level reduction

### D2.CUEQ5.DEF.022 — process means

For governed vector channel \(c\), let

$
x_{b,e,h,p,r,c}\in\mathbb R^{m_c}
$

be retained observation for backend \(b\), ensemble \(e\), order cell \(h\), fresh process \(p\), and nested repeat \(r\).

The process mean is the same canonical reduction introduced in D2.CUEQ5.DEF.016B:

$
\bar x_{b,e,h,p,c}
=
\frac{1}{R}\sum_{r=1}^{R}x_{b,e,h,p,r,c},
\qquad R=3.
$

All primary centroid and between-process stochastic statistics use \(\bar x\), not the 60 nested observations as if they were independent.

### D2.CUEQ5.DEF.023 — ensemble and cell centroids

For five processes per cell,

$$
\mu_{b,e,h,c}
=
\frac{1}{5}\sum_{p=1}^{5}\bar x_{b,e,h,p,c}.
$$

With four balanced cells,

$$
\mu_{b,e,c}
=
\frac{1}{4}\sum_h\mu_{b,e,h,c}.
$$

Define persistent backend effect

$$
B_{e,h,c}
=
\|\mu_{C,e,h,c}-\mu_{R,e,h,c}\|_{\rm RMS},
$$

and global

$$
B_{e,c}
=
\|\mu_{C,e,c}-\mu_{R,e,c}\|_{\rm RMS}.
$$

Every ensemble must satisfy

$$
B_{e,h,c}\le\epsilon_{c,32}
\quad\forall h,c
$$

and

$$
B_{e,c}\le\epsilon_{c,32}
\quad\forall c.
$$

Cell-conditioned guards prevent opposite order-conditioned backend shifts from cancelling globally.

### D2.CUEQ5.DEF.023A — reference-only resolution sufficiency

Before candidate values are used for an authorizing decision, each ensemble/cell/channel must demonstrate that the fixed reference process design can resolve the claimed persistent-bias budget.

Let \(SE_{R,e,h,c}\) be the root-mean-square over components of the ordinary standard error of the five reference process means in that cell.

Require

$
SE_{R,e,h,c}\le\epsilon_{c,32}/2.
$

If this is false, the result is `INSUFFICIENT_REFERENCE_RESOLUTION` for that ensemble/cell/channel, not PASS and not a candidate FAIL.

This is a design-resolution condition, not a normality-based confidence claim. It prevents five processes from authorizing a bias scale that the reference experiment itself cannot resolve.

A larger-process qualification may be designed later only as a new predeclared qualification instance before its CuEq outcomes are inspected; it is not an outcome-selected retry.

### D2.CUEQ5.DEF.024 — between-process stochastic non-degradation

Define reference/candidate cell-local between-process variance

$$
V_{b,e,h,c}
=
\frac{1}{5}\sum_{p=1}^{5}
\|\bar x_{b,e,h,p,c}-\mu_{b,e,h,c}\|_{\rm RMS}^2.
$$

Define corresponding global balanced-process variance

$$
V_{b,e,c}
=
\frac{1}{20}\sum_{h,p}
\|\bar x_{b,e,h,p,c}-\mu_{b,e,c}\|_{\rm RMS}^2.
$$

Pass requires separately in each ensemble:

$$
V_{C,e,h,c}
\le
V_{R,e,h,c}+\epsilon_{c,32}^2
\quad\forall h,c,
$$

and

$$
V_{C,e,c}
\le
V_{R,e,c}+\epsilon_{c,32}^2.
$$

A candidate cell may not borrow variance from another reference cell.

When reference variance is zero, the permitted additional candidate variance remains the fixed Candidate-5 physical numerical budget only.

### D2.CUEQ5.DEF.025 — within-process stochastic non-degradation

Nested repeats protect a distinct within-process coordinate.

For each backend/cell/process define

$$
W_{b,e,h,p,c}
=
\frac{1}{R}\sum_r
\|x_{b,e,h,p,r,c}-\bar x_{b,e,h,p,c}\|_{\rm RMS}^2.
$$

The cell mean within-process variance is

$$
W_{b,e,h,c}
=
\frac{1}{5}\sum_p W_{b,e,h,p,c}.
$$

Pass requires

$$
W_{C,e,h,c}
\le
W_{R,e,h,c}+\epsilon_{c,32}^2
\quad\forall e,h,c.
$$

Candidate-specific stochasticity therefore cannot hide behind a process-level average.

## 13. Rare-component hard guard

### D2.CUEQ5.DEF.026 — reference-controlled non-dilution guard

Candidate 5 removes the `0.01` Huber transition scale as a direct backend-discrepancy ceiling.

For each reference process/window/state/channel, define the reference self-repeat component maximum

$$
M_{R,e,h,p,c}
=
\max_{r_1<r_2,j}
|x_{R,e,h,p,r_1,c,j}-x_{R,e,h,p,r_2,c,j}|.
$$

Define candidate/reference paired component maximum

$$
M_{C,e,h,p,c}
=
\max_{r,j}
|x_{C,e,h,p,r,c,j}-x_{R,e,h,p,r,c,j}|.
$$

Pass requires

$$
M_{C,e,h,p,c}
\le
M_{R,e,h,p,c}+\epsilon_{c,32}
$$

for every retained process/window/state/channel.

Thus:

- one rare large component cannot be diluted by an RMS centroid;
- a deterministic-reference case still permits only the fixed precision-scaled physical budget; and
- the hard guard is controlled by reference repeatability plus a D2 materiality scale, not by a training-loss branch transition.

Non-finite values remain unconditional failure.

## 14. Robust-loss branch consequence

### D2.CUEQ5.DEF.027 — robust-objective consequence

Property masks and property availability are exact common inputs.

The implementation's internal label for which algebraic Huber branch evaluates a residual is **not** an independent TRAIN2 hard gate. Huber loss and its residual derivative are continuous at the transition, and an otherwise harmless floating-point straddle must not become a second numerical authority.

The protected consequence is the accepted TRAIN2 state transition already measured by:

- live portable physical-function displacement;
- EMA physical-function displacement;
- optimizer-action probes;
- exact discrete state; and
- recurrence-horizon coherent-drift guards.

The optimizer-consumed scalar loss and per-property loss contributions remain mandatory finite diagnostics and counterexample instrumentation. A near-transition perturbation passes or fails only through its governed transition consequence, not through branch-name identity alone.

The Huber value `0.01` therefore supplies the accepted property residual scale used in D2.CUEQ5.DEF.002A; it is not a direct backend-discrepancy ceiling.

## 15. TRAIN2 descriptors are not an authorizing channel

### D2.CUEQ5.DEF.028 — protected-consumer rule

Invariant descriptors and FPS fingerprints are not consumed by the current TRAIN2 optimizer.

They therefore do not belong to the TRAIN2 backend-equivalence predicate.

They may remain diagnostics.

They remain hard under D2.CUEQ5.DEF.003-004 where source/DATA6 descriptor geometry and selection are actually consumed.

A future TRAIN2 design that consumes descriptors reopens this definition.

## 16. FP32 and FP64 TRAIN2 disposition

### D2.CUEQ5.DEF.029 — FP32 TRAIN2

FP32 pure-CuEq TRAIN2 authorization requires every applicable Candidate-5 definition above.

If Candidate 5 is later accepted and qualified, obsolete Rev86 TRAIN2 authorizing statistics are retired as authority rather than stacked underneath the new relation.

They may remain historical diagnostics.

### D2.CUEQ5.DEF.030 — FP64 TRAIN2 unsupported

Candidate 5 does not authorize FP64 pure-CuEq TRAIN2.

Historical FP64 forward parity cannot establish a training operator.

D3/D4 must fail closed for a requested FP64 CuEq TRAIN2 realization unless a later accepted D2 authority operator-qualifies FP64 under an explicit protected consequence.

No silent fallback or implicit inheritance from source/DATA6 FP64 is permitted.

## 17. Completed-state projection and EVAL2

### D2.CUEQ5.DEF.031 — proposed trained-state projection relation

For a completed state produced by an accepted and current CuEq TRAIN2 relation:

1. authenticate the exact transient CuEq realization and state;
2. reconstruct the canonical portable-e3nn shell from accepted configuration;
3. transfer complete portable-forward state through the qualified dependency-native state-transfer owner;
4. prove source-state non-mutation;
5. require exact canonical architecture/head identity and complete state inventory;
6. require direct transient-CuEq versus mapped-portable-e3nn E/F/stress parity under the Candidate-5 physical numerical scale for the trained dtype;
7. require the independent anti-common-mode transfer oracle of D2.CUEQ5.DEF.009; and
8. execute EVAL2 under provider identity **e3nn**, because portable e3nn is the actual numerical forward.

This is a newly source-closed proposed D2 relation. Historical deployment implementation does not authorize it by itself.

Source/DATA6 descriptor/FPS parity is not imported into this trained-state projection unless a projection consumer explicitly consumes those descriptors.

## 18. Qualification record and currentness

### D2.CUEQ5.DEF.032 — qualification applicability identity

An authorizing qualification record binds at least:

- Candidate-5 method digest;
- exact D2 candidate identity;
- MACE/Torch/CUDA/CuEq source/runtime identities;
- arithmetic-relevant device/precision/determinism/TF32/matmul state;
- FP32 dtype and resolved CuEq kernel;
- model architecture/head topology;
- exact state-anchor identities and state-class declaration;
- TRAIN2 objective identity;
- exact ordered corpus/head layout;
- loader seed/shuffle/sampler/batch/drop-last identity;
- every selected exposure-window identity;
- portable live/EMA witness corpus identity;
- optimizer-action probe gradient identities;
- state-transfer mapping identity and independent anti-common-mode oracle identity;
- construction/execution-order design;
- process/repeat cardinality;
- two complete ensemble identities; and
- source/DATA6 or projection role identity when those siblings are claimed.

A change in a bound material dimension stales the record.

A stale Rev86 `passed=true` record cannot authorize Candidate 5.

## 19. Qualification versus routine doctor

### D2.CUEQ5.DEF.033 — routine execution witness

The routine campaign doctor need not recreate the two complete qualification ensembles.

It may only:

1. authenticate a current qualification whose exact applicability contains the requested realization/state class; and
2. run a cheap bounded real forward/backward reachability and finiteness witness under the current checkpoint/head/objective/runtime.

The routine witness cannot:

- estimate or widen Candidate-5 numerical envelopes;
- repair a failed qualification;
- retry until pass;
- authorize a different model/runtime/dtype/topology/state class;
- turn historical Rev86 evidence into current qualification;
- substitute descriptor/FPS parity for the TRAIN2 state-transition relation; or
- claim equivalence from a smoke execution alone.

Exact persistence/routing belongs to D3/D4.

## 20. Candidate-5 Stage-C falsification obligations

Fresh target-host evidence may begin only after Candidate 5 receives a fresh independent D2 Review PASS and stakeholder ratification of the exact immutable candidate.

For each claimed FP32 topology/family, Stage C must realize the complete Candidate-5 functional.

At minimum it must attempt to falsify:

1. MH-1 / omat_pbe FP32 at \(S_0,S_M,S_L\);
2. MPA-0-medium / default FP32 at \(S_0,S_M,S_L\);
3. both independent complete four-cell ensembles;
4. process-level rather than repeat-level primary reduction;
5. cell-local candidate variance inflation against the matching reference cell;
6. within-process candidate variance inflation;
7. opposite cell biases that cancel globally;
8. a single rare component error otherwise diluted by RMS statistics;
9. update-2-only live-model divergence;
10. EMA-only divergence;
11. optimizer-state divergence that is invisible in the live state but changes a common-gradient action probe;
12. scheduler/counter or RNG-state divergence;
13. a non-mutating state-transfer check;
14. a dropped transferable tensor that is quiescent on the physical witness corpus;
15. an anti-common-mode transfer route that intentionally disagrees with the primary transfer;
16. target-first, hand-built, balancing-sampler, duplication, or altered-drop-last exposure;
17. first/last/epoch-boundary/scheduler-discontinuity/extreme-metadata window selection;
18. recurrence-horizon bounded adaptation and injected coherent linear drift that is locally sub-tolerance but extrapolates beyond the full remaining-horizon budget;
19. reference-only long-horizon resolution too weak for the proposed bias budget — must return INSUFFICIENT_REFERENCE_RESOLUTION, not PASS;
20. descriptor-only drift with preserved TRAIN2 physical consequence — must not fail TRAIN2 solely for that descriptor drift;
21. source/DATA6 descriptor/FPS drift that changes selection — must fail the source relation;
22. near-transition Huber straddle with unchanged governed transition — branch identity alone must not fail; a straddle that changes the governed transition beyond Candidate-5 bounds must fail;
23. zero-reference-variance cases;
24. stale qualification after runtime/source/configuration/method/state-class change;
25. a formally different but numerically trivial state anchor; and
26. attempted FP64 CuEq TRAIN2 admission — must fail closed.

The process/repeat/order design is frozen before Candidate-5 outcomes are inspected.

No failure may be converted into a pass by widening \(\epsilon_{c,32}\), deleting a state/window/channel, pooling two ensembles to rescue one, or rerunning until a desired classification appears.

## 21. Counterexample disposition

Candidate 5 is specifically constructed to reject:

- coherent small backend bias that is locally sub-tolerance but would accumulate beyond the fixed physical numerical budget over the remaining accepted horizon, through the recurrence-horizon growth guard;
- equal global means with order-cell bias;
- cell-local variance inflation hidden by another reference cell;
- within-process variance inflation hidden by process averaging;
- one rare large component hidden by RMS aggregation;
- update-2-only divergence;
- EMA-only divergence;
- optimizer-state divergence not yet visible in the live model;
- scheduler/RNG-state drift;
- target-first or synthetic-batch substitution;
- dropped/misrouted state during projection;
- transfer that mutates the source model;
- stale qualification/currentness reuse;
- source/DATA6 descriptor drift that changes FPS selection; and
- nominally different but numerically trivial state anchors.

Candidate 5 intentionally **does not** claim bitwise equality of whole stochastic training trajectories across backends.

Its claim is bounded numerical interchangeability inside the accepted stochastic TRAIN2 method over the explicitly qualified model/runtime/state/exposure domain.

## 22. D2-to-D3 handoff if Candidate 5 is later accepted

No D3/D4 implementation is authorized merely by this proposal.

After fresh independent Review PASS, stakeholder ratification, and fresh Stage-C qualification, D3/D4 shall prefer reduction over additive machinery:

- replace the Rev86 TRAIN2 authorizing reducer rather than stacking Candidate 5 above it;
- retain legacy records only for historical diagnosis/deserialization;
- keep source/DATA6, TRAIN2, and projection/EVAL2 as separate semantic owners;
- remove TRAIN2 descriptor/FPS hard-gating when no TRAIN2 consumer exists;
- use the real loader/exposure owner rather than a reconstructed qualification loader;
- preserve full-state identity/currentness;
- make measurement transfer snapshot-based and non-mutating;
- reuse the qualified state-transfer owner rather than inventing parallel projection machinery;
- represent FP64 CuEq TRAIN2 as unsupported;
- preserve no-silent-fallback behavior; and
- identify EVAL2 as portable-e3nn execution after qualified projection.

## 23. Evidence/currentness consequence of Candidate 5

Candidate 5 changes the acceptance relation materially relative to Candidate 4.

Therefore:

- Candidate-4 Stage-C evidence, if ever produced, cannot qualify Candidate 5;
- Stage-A MH-1/MPA-0 evidence remains method-design evidence only;
- Candidate-4 NO-PASS remains applicable historical falsification evidence;
- source/DATA6 historical operational passes may support review but do not by themselves accept D2.CUEQ5.DEF.003-005;
- fresh Candidate-5 Stage-C evidence must bind the exact immutable Candidate-5 commit and blob; and
- any semantic edit to this document after freezing creates a new candidate identity.

## 24. Required acceptance sequence

Candidate 5 remains **PROPOSED_NOT_ACCEPTED**.

The valid sequence is:

1. freeze Candidate 5 by immutable Git commit/blob identity;
2. perform a genuinely fresh independent Protocol-6.4 D2 Review against the accepted parent and Candidate-4 NO-PASS findings;
3. repair to a new identity if that Review finds any semantic blocker;
4. obtain stakeholder ratification of the exact passing candidate;
5. run fresh Stage-C target-host evidence under that exact method;
6. adjudicate Stage-C evidence without tuning the method to the outcomes; and
7. only then hand accepted D2 semantics to D3/D4.

A Review PASS means the numerical method is coherent enough to test. It does not itself qualify CuEq.
