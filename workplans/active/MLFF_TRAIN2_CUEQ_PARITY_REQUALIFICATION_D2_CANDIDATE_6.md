---
kind: proposed-D2-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_NOT_ACCEPTED
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
candidate_id: MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-6
date: 2026-09-25
parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
parent_d2_exact_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
stage_a_cross_family_basis: 24734c8113dfaeaba4ae32c2bb0b80f3c0c72e82
supersedes_candidate: 6e73fbb7af9b8d46f61cf81113259584ffed8527
superseded_candidate_review: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R2.md
human_ratification_required: true
---

# Proposed D2 full-trajectory acceleration-equivalence overlay for MACE e3nn / CuEq TRAIN2 — Candidate 6

## 1. Lifecycle, authority, and deliberate narrowing

Candidate 6 is a **proposed** D2 overlay. Repository presence does not make it accepted authority.

It supersedes immutable Candidate 5 after fresh independent Review R2 returned NO-PASS.

Candidate 6 changes the problem shape rather than stacking more guards onto Candidate 5:

1. it removes the `delta*sqrt(u)` numerical scale;
2. it removes recurrence-horizon extrapolation;
3. it removes sparse entry/mid/late state-class authorization;
4. it removes finite common-gradient optimizer probes as complete-state authority;
5. it removes fixed five-process/two-ensemble stochastic cardinality;
6. it removes the three-repeat reference-max rare-component allowance;
7. it removes sampled TRAIN2 exposure windows from authorizing coverage;
8. it narrows qualification to the **exact complete accepted TRAIN2 realization and horizon**; and
9. it does **not** propose generic CuEq source/DATA6 execution in this candidate.

The accepted D1 scientific method, robust objective, replay semantics, checkpoint policy, target-size method, production threshold policy, and publication policy remain unchanged.

Candidate 6 proposes:

- FP32 CuEq TRAIN2 only;
- full-horizon stochastic numerical equivalence against the accepted e3nn reference method;
- no mid-run e3nn/CuEq backend switching;
- completed-state CuEq-to-portable-e3nn projection only after a passing TRAIN2 qualification;
- EVAL2 under actual provider identity **e3nn** after qualified projection.

FP64 CuEq TRAIN2 remains unsupported and fails closed.

Generated/current source/DATA6 execution remains e3nn. Historical optional CuEq source/DATA6 realizations are not promoted by Candidate 6.

## 2. Protected claim

### D2.CUEQ6.DEF.001 — exact realization key

An authorizing TRAIN2 relation is keyed by

$$
A=(d,\theta_0,q_0,D,O,H,K,\rho,m),
$$

where:

- \(d\) is learned-model dtype;
- \(\theta_0,q_0\) identify the exact authenticated initial model and mutable training state;
- \(D\) is the exact authenticated target/replay corpus and ordered loader configuration;
- \(O\) is the exact accepted objective/head/property-mask identity;
- \(H\) is the exact accepted optimizer-update horizon and checkpoint/monitor schedule;
- \(K\) is the resolved backend/kernel realization;
- \(\rho\) is arithmetic-relevant runtime/hardware/determinism identity; and
- \(m\) is the immutable Candidate-6 method identity.

A qualification is applicable only to the exact bound key. Candidate 6 does not infer equivalence to another corpus, seed, horizon, objective, initial state, topology, runtime, device class, or backend order.

### D2.CUEQ6.DEF.002 — whole-trajectory claim

For one exact accepted TRAIN2 realization, Candidate 6 asks whether pure CuEq execution is numerically interchangeable with the accepted e3nn reference **over the complete realized training horizon**.

The protected consequence is the complete observed training trajectory needed by the accepted method:

- exact loader/example/head/property-mask exposure;
- finite optimizer-consumed total/per-property/per-example loss contributions;
- portable live-model physical function through the horizon;
- portable EMA physical function through the horizon when EMA is active;
- exact governed scheduler/counter/checkpoint-monitor events;
- exact scientific checkpoint/admissibility decisions;
- successful same-backend continuation for any execution mode claimed by the qualification key; and
- the final completed state used by projection/EVAL2.

Candidate 6 does **not** claim raw cross-parameterization optimizer-state equality.

It does **not** authorize changing backend at an intermediate checkpoint.

Latent optimizer state is protected by executing and observing every future update in the exact authorizing horizon. A latent difference that never changes any governed consequence before the bound horizon ends is outside the Candidate-6 claim.

## 3. Common inputs and exact discrete semantics

### D2.CUEQ6.DEF.003 — exact common inputs

Reference e3nn and candidate CuEq trajectories begin from identical upstream-owned numerical inputs:

- architecture and head topology;
- authenticated initial model;
- objective coefficients and robust-loss parameters;
- E0 and labels;
- property masks/availability;
- optimizer configuration and schedule;
- EMA configuration;
- exact corpus membership;
- replay/target mode and lineage;
- loader seed, shuffle, sampler, batch size, and `drop_last`;
- accepted preprocessing; and
- the exact update/checkpoint horizon.

Backend realization is the deliberate independent variable.

### D2.CUEQ6.DEF.004 — governed exact discrete state

The following are exact where the accepted parent method makes them common semantics:

- batch/example/head order;
- property masks and active head identity;
- scheduler phase and accepted update counters;
- checkpoint-monitor evaluation schedule;
- checkpoint identity/index selected by the accepted rule;
- target/replay membership and duplication factor;
- accepted RNG state/position when that RNG governs common exposure;
- restart boundary identity for a qualification that claims restart/resume; and
- every final scientific accept/reject/admissibility decision in the qualified role.

A backend-private cache/counter/RNG is not compared merely because it exists. It must be bound in runtime identity and is an equivalence coordinate only if it can alter a governed consequence.

Any exact-discrete mismatch is immediate non-equivalence.

## 4. Real TRAIN2 trajectory

### D2.CUEQ6.DEF.005 — accepted loader is the sole exposure owner

For replay-enabled current P5, the actual accepted loader constructs

$$
D_{\rm train}=D_r\Vert D_t,
$$

with replay/pretraining head first and target head second before seeded shuffle, no target/replay balancing sampler, no intentional target duplication, the accepted batch size, and `drop_last=true`.

Target-only foundation adaptation uses its accepted target-only shuffled loader semantics.

No hand-built batch, selected window, reordered lookalike, target-first substitute, replay-only substitute, balancing sampler, or duplicated replacement can authorize Candidate 6.

### D2.CUEQ6.DEF.006 — complete horizon, not sampled windows

Every optimizer update in the exact accepted TRAIN2 horizon is executed by both the reference and candidate realization.

There is no recurrence extrapolation and no authorizing sparse state-anchor interpolation.

If the accepted realization contains \(U\) optimizer updates, qualification executes all \(U\).

All scheduler/epoch/shuffle transitions encountered by the accepted loader are encountered naturally.

This rule replaces Candidate 5's window-selection and recurrence-horizon machinery.

## 5. Portable functional observation

### D2.CUEQ6.DEF.007 — canonical portable live state

Let

$$
P_R(\theta_R)=\theta_R
$$

for the e3nn reference coordinate.

For a CuEq live-model snapshot, \(P_C\) is the qualified dependency-native CuEq-to-e3nn projection applied only to an immutable snapshot.

No projection operation may mutate the measured live trajectory.

### D2.CUEQ6.DEF.008 — complete projection inventory

Every projection used for qualification requires:

1. exact canonical architecture/head identity;
2. explicit inventory of every parameter and buffer affecting portable forward execution;
3. one-to-one semantic source/destination correspondence;
4. exact copy/reshape/permutation semantics where no floating contraction is required;
5. declared linear-transform semantics where a floating contraction is required;
6. exact source-state identity before and after projection; and
7. an independent structural oracle that neither calls the primary mapper nor consumes the same generated mapping table.

A dropped quiescent state item is failure even if the physical witness does not expose it.

### D2.CUEQ6.DEF.009 — independent floating transfer oracle

For a floating linear transfer

$$
y=Ax,
$$

the independent structural oracle evaluates the semantic transform independently of the production mapper.

Exact copies, pure reshapes, and pure permutations compare exactly.

For a length-\(n\) floating inner product in learned-model dtype with unit roundoff \(u\), define

$$
\gamma_n=\frac{nu}{1-nu},
\qquad nu<1.
$$

When a transfer value is produced by a declared linear reduction, the production mapper must satisfy the standard componentwise forward-error envelope against an independently evaluated higher-precision semantic transform:

$$
|\widehat y-y^*|
\le
\gamma_n\,(|A||x|)+\frac12\,\operatorname{ulp}_d(y^*),
$$

componentwise, with operation count and reduction structure bound to the mapping identity.

If the mapping cannot be represented by exact structural operations or a source-closed numerical transform with a valid bound, the structural oracle is unavailable and qualification cannot PASS.

The inverse pinned-MACE converter is not automatically independent merely because its call direction is reversed.

## 6. Floating-distance primitive

### D2.CUEQ6.DEF.010 — symmetric ULP distance

For finite scalars \(a,b\) in the same declared IEEE learned-model dtype \(d\), define

$$
U_d(a,b)
$$

as the absolute distance between their monotone ordered IEEE bit-pattern integers, treating \(+0\) and \(-0\) as equal.

NaN or infinite values are unconditional failure.

ULP distance is used only as a dimensionless observation coordinate. Candidate 6 does not claim that a universal fixed number of ULPs is intrinsically acceptable.

Acceptability is calibrated from the accepted e3nn method's own fresh-process numerical repeatability before Candidate CuEq outcomes are used.

## 7. Full-horizon score families

### D2.CUEQ6.DEF.011 — fixed authorizing score set

For one complete process realization define four score families.

#### F1 — optimizer-consumed loss trace

At every update, retain the finite total loss and the optimizer-consumed per-property/per-example loss contributions in the native learned-model arithmetic coordinate.

For a paired realization, \(S_{\rm loss}\) is the maximum ULP distance over the complete loss trace.

#### F2 — portable live-model trace

On the predeclared backend-blind portable witness corpus \(W\), evaluate live-model energy/atom, force, and stress after every optimizer update.

For a paired realization, \(S_{\rm live}\) is the maximum ULP distance over every retained physical component and update.

#### F3 — portable EMA trace

When EMA is enabled, evaluate the same \(W\) from the EMA state after every optimizer update.

\(S_{\rm ema}\) is the maximum ULP distance over the complete EMA physical trace.

When EMA is disabled by the accepted method, both realizations must agree exactly on that absence and \(S_{\rm ema}=0\).

#### F4 — broad physical displacement

Let the paired portable live and EMA physical-component ULP distances at update \(k\) form vector \(z(k)\).

Define

$$
S_{\rm rms}
=
\max_k
\sqrt{\frac{1}{|z(k)|}\sum_j z_j(k)^2}.
$$

This prevents a broad low-amplitude shift from being represented only by the componentwise maximum.

The score family count is therefore

$$
J=4.
$$

No descriptor/FPS coordinate appears in TRAIN2 because current TRAIN2 does not consume it.

## 8. Reference-only stochastic calibration

### D2.CUEQ6.DEF.012 — independent unit

The independent experimental unit is a fresh operating-system process that constructs and executes the complete bound TRAIN2 realization.

Nested evaluations inside one process are measurements, not independent replicates.

### D2.CUEQ6.DEF.013 — reference self pair

A reference-calibration process launches two independently constructed e3nn realizations, \(R_1,R_2\), with the exact common inputs and exact bound production execution order.

It executes both through the complete accepted horizon and computes

$$
S^{RR}_{p,j},
\qquad j\in\{\mathrm{loss,live,ema,rms}\}.
$$

Construction/execution order is part of the qualification key. Candidate 6 does not average over hypothetical orders and then authorize another order.

A different order is a different key.

### D2.CUEQ6.DEF.014 — finite-sample coverage coordinates

Candidate 6 fixes the reference tolerance-content target and simultaneous confidence target as

$$
\Gamma=0.90,
\qquad
\Kappa=0.95.
$$

For \(J=4\) fixed score families, choose the smallest integer \(n_{\rm ref}\) such that

$$
J\,\Gamma^{n_{\rm ref}}
\le
1-\Kappa.
$$

For \(J=4\), \(\Gamma=0.90\), and \(\Kappa=0.95\),

$$
n_{\rm ref}=42
$$

is sufficient; Candidate 6 uses the predeclared round number

$$
n_{\rm ref}=44.
$$

No Candidate CuEq outcome may change this count.

### D2.CUEQ6.DEF.015 — distribution-free reference tolerance limits

For score family \(j\), define

$$
L_j
=
\max_{1\le p\le n_{\rm ref}}
S^{RR}_{p,j}.
$$

For one score family, the sample maximum is a one-sided nonparametric tolerance limit. Without assuming a parametric process distribution,

$$
\Pr\!\left[F_j(L_j)\ge\Gamma\right]
\ge
1-\Gamma^{n_{\rm ref}},
$$

where \(F_j\) is the reference-process score distribution.

By the union bound, the four limits simultaneously cover at least \(\Gamma=0.90\) of each reference score population with confidence at least \(\Kappa=0.95\).

The claim is exactly this finite-sample tolerance statement. It is not a normality claim, not a standard-error heuristic, and not an estimate of infinite-tail support.

### D2.CUEQ6.DEF.016 — reference-method stability gate

Before CuEq confirmation, the reference-only phase must also show:

- no non-finite trajectory;
- no exact common-input violation;
- exact agreement of every governed discrete scientific decision between \(R_1\) and \(R_2\) in every reference process; and
- no reference-only restart inconsistency for any restart execution mode included in the qualification key.

If accepted e3nn self variability changes a governed scientific decision under the exact key, the result is

`REFERENCE_METHOD_UNSTABLE`

rather than a widened backend tolerance.

## 9. Candidate confirmation

### D2.CUEQ6.DEF.017 — cross-backend processes

A candidate-confirmation process independently constructs one e3nn reference trajectory \(R\) and one pure-CuEq trajectory \(C\) under the exact bound key and computes

$$
S^{RC}_{p,j}.
$$

The candidate sample count is

$$
n_C=44.
$$

The candidate processes are independent of the reference-calibration processes.

### D2.CUEQ6.DEF.018 — zero-exceedance rule and population statement

Every candidate process must satisfy

$$
S^{RC}_{p,j}\le L_j
$$

for all four score families.

Any exceedance is a failed qualification. There is no outcome-selected rerun.

With zero exceedances in \(n_C=44\) independent processes, for one family the one-sided exact binomial upper bound on the exceedance probability is below \(0.10\) at confidence exceeding \(0.95\).

Using the same Bonferroni/union-bound family-wise allocation as the reference calibration, Candidate 6 therefore authorizes only the following stochastic population claim:

> with simultaneous confidence at least \(0.95\), at least \(0.90\) of fresh candidate processes for the exact qualification key have each governed numerical score inside the independently calibrated e3nn self-repeatability tolerance limit.

Candidate 6 does not claim bitwise trajectory identity and does not claim zero probability of a larger stochastic excursion.

### D2.CUEQ6.DEF.019 — zero-reference-variation semantics

If \(L_j=0\) for a score family, every candidate score in that family must be exactly zero.

Reference exactness cannot mint a positive candidate tolerance.

## 10. Scientific-decision preservation

### D2.CUEQ6.DEF.020 — exact decisions

In every candidate-confirmation process, reference and candidate must agree exactly on every governed discrete scientific consequence reached by the qualified role, including when applicable:

- checkpoint evaluation schedule;
- selected checkpoint index/identity;
- checkpoint admissibility;
- target/replay retention/admissibility classification;
- production checkpoint-quality classification; and
- any other accepted boolean/discrete decision downstream of the bound TRAIN2 trace.

A stochastic numerical score inside the reference envelope cannot rescue a different scientific decision.

### D2.CUEQ6.DEF.021 — no branch-name authority

Huber branch labels are not an independent hard gate.

Masks and property availability remain exact common inputs.

Near-transition arithmetic is accepted or rejected through the complete loss/trajectory score and exact downstream decision consequences.

## 11. State and restart scope

### D2.CUEQ6.DEF.022 — complete state for authenticity, not cross-basis equality

The runtime still authenticates complete mutable state

$$
\Xi=(\theta,q_{\rm opt},q_{\rm ema},q_{\rm sched},q_{\rm rng},q_{\rm backend})
$$

for restart/currentness.

Candidate 6 does not require a raw componentwise e3nn/CuEq optimizer-moment equivalence because CuEq and e3nn may use different parameter coordinates and elementwise optimizers are not generally basis invariant.

Instead, the exact full horizon consumes the actual optimizer state and the authorizing observable is its governed trajectory consequence.

### D2.CUEQ6.DEF.023 — no mid-run backend switching

A CuEq-qualified run must resume CuEq from authenticated CuEq state.

An e3nn run must resume e3nn from authenticated e3nn state.

Candidate 6 does not authorize:

- e3nn -> CuEq restart conversion;
- CuEq -> e3nn restart conversion during TRAIN2; or
- any backend switch before the completed state enters the separate projection relation.

A future cross-backend restart capability requires new D2 authority.

### D2.CUEQ6.DEF.024 — restart mode is qualification identity

If a product execution mode permits same-backend restart/resume, the qualification key must include that mode and a predeclared restart boundary.

The reference and candidate process designs must realize the same restart semantics.

If only uninterrupted execution is qualified, a restarted run is outside applicability and fails closed.

## 12. Rare-component and broad-shift semantics

### D2.CUEQ6.DEF.025 — no separate three-repeat catastrophic allowance

Candidate 6 has no rule of the form

$$
M_C\le M_R+\epsilon.
$$

Rare components are protected by the maximum-ULP live/EMA/loss score families across the full horizon.

Broad low-amplitude shifts are protected by \(S_{\rm rms}\).

Their tolerance limits come only from the independent reference self population defined above.

The finite-sample content/confidence statement is explicit and fixed before Candidate CuEq execution.

## 13. Source/DATA6 disposition

### D2.CUEQ6.DEF.026 — source/DATA6 CuEq not proposed here

Candidate 6 does not promote historical source/DATA6 FP32 or FP64 CuEq `allclose` rules into D2 authority.

Under Candidate 6:

- generated/current source-side execution remains e3nn;
- DATA6 descriptor/selection execution remains e3nn unless another accepted D2 relation separately authorizes CuEq;
- historical optional source/DATA6 CuEq realization records are evidence/history only;
- descriptor/FPS exact selection consequences remain owned by their existing source/DATA6 method, not by TRAIN2; and
- pseudolabel generation, E0/source inference, or any other numerical consumer may not infer CuEq authorization from TRAIN2.

This narrowing is deliberate. It closes Candidate-5 B9 by removing an unjustified generic sibling rather than inventing a new threshold.

A future CuEq source/DATA6 proposal must define each protected consumer separately. Exact descriptor/FPS decision preservation may be sufficient for a selection-only relation; pseudolabel or physical-output materialization requires its own consequence-specific numerical relation.

## 14. FP32/FP64 TRAIN2 disposition

### D2.CUEQ6.DEF.027 — FP32

FP32 pure-CuEq TRAIN2 is the only TRAIN2 acceleration member proposed by Candidate 6.

It requires every applicable definition above for the exact qualification key.

### D2.CUEQ6.DEF.028 — FP64 unsupported

FP64 pure-CuEq TRAIN2 is unsupported.

Source-side or forward-only FP64 evidence cannot authorize a training operator.

A requested FP64 CuEq TRAIN2 realization must fail closed until a later accepted D2 candidate qualifies it.

## 15. Completed-state projection

### D2.CUEQ6.DEF.029 — projection is a separate relation

Only a completed state produced by a current Candidate-6-qualified CuEq TRAIN2 realization may enter the projection relation.

Projection requires:

1. exact completed transient CuEq realization/state authentication;
2. immutable snapshot input;
3. exact canonical architecture/head identity;
4. complete portable-forward state inventory;
5. primary dependency-native CuEq-to-e3nn projection;
6. independent structural mapping oracle under D2.CUEQ6.DEF.008-009;
7. source-state non-mutation;
8. direct transient-CuEq versus mapped-e3nn physical-function equivalence under the projection-specific reference-self envelope below; and
9. EVAL2 provider identity e3nn after projection.

### D2.CUEQ6.DEF.030 — projection reference-self envelope

Projection does not reuse a TRAIN2 physical tolerance.

For the exact completed state and frozen projection witness corpus, launch fresh evaluator processes using the same portable e3nn state twice to obtain reference self scores

$$
Q^{RR}_{p,\max},
\qquad
Q^{RR}_{p,\rm rms}.
$$

The projection score family count is \(J_P=2\).

Use the same

$$
\Gamma=0.90,
\qquad
\Kappa=0.95
$$

nonparametric tolerance construction with a predeclared process count satisfying

$$
J_P\Gamma^{n_P}\le1-\Kappa.
$$

Candidate 6 uses

$$
n_P=36.
$$

The transient-CuEq versus mapped-e3nn evaluator confirmation uses 36 fresh independent processes and requires zero exceedances of both reference-self projection limits.

This envelope governs only evaluator arithmetic. It does not replace the independent structural mapping oracle.

### D2.CUEQ6.DEF.031 — EVAL2 identity

After projection passes, EVAL2 executes the canonical portable **e3nn** provider.

Stored measurement identity must therefore name e3nn as the numerical forward.

CuEq is provenance of the completed TRAIN2 state, not the EVAL2 provider.

## 16. Qualification record and currentness

### D2.CUEQ6.DEF.032 — authorizing identity

An authorizing TRAIN2 qualification record binds at least:

- immutable Candidate-6 commit/blob/digest;
- exact initial model/checkpoint and selected head;
- exact complete training-state identity;
- exact corpus/replay/label lineage;
- exact loader seed/order/sampler/batch/drop-last identity;
- exact objective and optimizer/EMA/scheduler configuration;
- exact update/checkpoint horizon;
- exact production construction/execution order;
- learned-model dtype;
- MACE/Torch/CUDA/CuEq source/runtime identities;
- device identity and arithmetic-relevant determinism/TF32/matmul state;
- resolved CuEq kernel;
- portable witness corpus identity;
- reference calibration process identities;
- candidate confirmation process identities;
- score-family definitions and ULP primitive identity;
- reference limits \(L_j\);
- restart execution mode/boundary when claimed;
- projection mapping/oracle identities when projection is claimed; and
- exact scientific decision trace.

A material change in any bound coordinate stales the record.

No historical Rev86/Candidate-4/Candidate-5 record can authorize Candidate 6.

## 17. Routine doctor

### D2.CUEQ6.DEF.033 — cheap runtime witness

Routine doctor does not recreate the full qualification.

It may only:

1. authenticate an exact current qualification record whose key contains the requested realization; and
2. execute a cheap real forward/backward finite/reachability witness under the requested current state.

It cannot:

- estimate new tolerance limits;
- alter \(\Gamma\), \(\Kappa\), or sample count;
- authorize another corpus/seed/horizon/runtime/device/order;
- retry until pass;
- revive stale Rev86 evidence;
- substitute descriptor/FPS parity for TRAIN2; or
- authorize a mid-run backend switch.

## 18. Candidate-6 Stage-C obligations

Fresh Stage-C evidence may begin only after Candidate 6 receives fresh independent D2 Review PASS and stakeholder ratification of the exact immutable candidate.

Stage C must realize, at minimum:

1. MH-1 / omat_pbe FP32 exact qualification key;
2. MPA-0-medium / default FP32 exact qualification key;
3. complete accepted TRAIN2 horizon for every reference and candidate process;
4. the fixed 44-process reference-only calibration before Candidate CuEq confirmation;
5. the fixed 44-process candidate confirmation;
6. exact `J=4`, \(\Gamma=0.90\), \(\Kappa=0.95\) decision semantics;
7. exact reference-method discrete-decision stability;
8. loss/live/EMA/RMS score collection over the full horizon;
9. zero-reference-variation exactness;
10. injected late-only divergence that Candidate 5's recurrence extrapolation could miss;
11. injected latent optimizer-state difference that changes a later real update;
12. a metadata-ordinary but numerically difficult batch, which must be exercised because the complete loader is executed;
13. a rare single physical component perturbation;
14. a broad low-amplitude physical shift;
15. same-backend restart/resume if that execution mode is claimed;
16. attempted mid-run backend switching, which must fail closed;
17. stale qualification after any bound-key change;
18. attempted FP64 CuEq TRAIN2, which must fail closed;
19. attempted source/DATA6 CuEq authorization from the TRAIN2 record, which must fail closed;
20. projection mapping mutation, which must fail;
21. dropped/quiescent projection state, which must fail structurally;
22. a correlated inverse-converter "oracle", which must be rejected as non-independent;
23. a deliberately wrong independent mapping expression, which must fail;
24. projection evaluator zero-exceedance qualification under its separate reference-self envelope; and
25. EVAL2 measurement identity e3nn after successful projection.

No Candidate-6 threshold, process count, witness, or score family may be changed after Candidate CuEq outcomes are inspected.

## 19. Counterexample closure

Candidate 6 is designed to close the Candidate-5 false passes as follows.

| Counterexample | Candidate-6 treatment |
|---|---|
| unsupported `delta*sqrt(u)` scale | removed |
| coherent small bias accumulating late | complete horizon observed; no extrapolation |
| nonlinear late divergence | complete horizon observed |
| optimizer state invisible to finite probes | no finite-probe complete-state claim; every later real update is executed |
| EMA difference outside finite early witness | EMA physical function observed through complete horizon |
| candidate leaves e3nn anchor class | no anchor-class extrapolation; exact trajectory key only |
| metadata-ordinary difficult batch omitted | impossible; complete loader trajectory executed |
| underpowered five-process estimate | replaced by explicit distribution-free content/confidence design |
| rare reference repeat widens `M_R+epsilon` | rule removed; reference population tolerance has declared finite-sample semantics |
| zero reference variation | candidate must be exact |
| descriptor-only TRAIN2 drift | not an authorizing TRAIN2 channel |
| source/DATA6 pseudolabel tolerance inherited from forward allclose | source/DATA6 CuEq not authorized by Candidate 6 |
| mid-run backend conversion | explicitly unsupported |
| stale qualification | exact key currentness |
| FP64 TRAIN2 inference from forward evidence | fail closed |

## 20. Author-side Challenge

Candidate 6 has been challenged against the Review-R2 blockers before freezing.

The main deliberate tradeoff is scope and qualification cost.

Candidate 6 gives up generic model-state-class authorization in exchange for a much stronger statement about one exact realized TRAIN2 experiment. It also gives up current optional source/DATA6 CuEq promotion rather than manufacturing new source thresholds.

The 90%-content / 95%-simultaneous-confidence stochastic claim is explicit and finite-sample. It is not represented as proof of complete distribution equality.

A future broader state/corpus/runtime generalization must be separately proposed and independently reviewed.

## 21. D2-to-D3 handoff if later accepted

No D3/D4 implementation is authorized by this proposal.

After independent Review PASS, stakeholder ratification, and fresh Stage-C qualification, D3/D4 must preserve:

- exact qualification-key applicability and fail-closed currentness;
- full accepted-loader trajectory qualification rather than sampled windows;
- reference calibration before Candidate CuEq confirmation;
- fixed score/statistical semantics;
- no mid-run backend switching;
- source/DATA6 e3nn narrowing;
- FP64 TRAIN2 unsupported state;
- snapshot-only projection;
- genuinely independent structural transfer oracle;
- separate projection evaluator envelope; and
- EVAL2 provider identity e3nn.

Rev86/Candidate-4/Candidate-5 authorizing machinery must be replaced rather than stacked beneath Candidate 6.

## 22. Evidence boundary and acceptance sequence

Stage-A MH-1/MPA-0 evidence remains method-design evidence only.

Candidate-5 Review R2 remains historical falsification evidence.

No Candidate-6 CuEq acceptance outcome has been used to choose Candidate-6 semantics.

The valid sequence is:

1. freeze Candidate 6 by immutable commit/blob;
2. perform a genuinely fresh independent D2 Review;
3. if blocked, repair to another new identity;
4. obtain stakeholder ratification of the exact passing candidate;
5. run fresh Candidate-6 Stage-C target-host evidence;
6. adjudicate without method tuning;
7. only then hand accepted D2 semantics to D3/D4.

A Review PASS means only that Candidate 6 is coherent enough to test. It does not itself qualify CuEq.
