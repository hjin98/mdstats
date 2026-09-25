---
kind: D2-independent-review
protocol_version: 6.4.0
status: NO_PASS
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
reviewed_candidate: c6e18ccfce62d47e96dde80600558522c62c28ef
reviewed_candidate_blob: 60598fa33048df16f9cc41e6adf761dd952aa28f
lifecycle_head_basis: 62ec417a4e9d0899fb1fce286955e07d1fb11bd1
accepted_parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_parent_d2_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
serious_challenge: false
highest_blocking_owner: D2
stage_C_state: BLOCKED
D3_D4_state: BLOCKED
date: 2026-09-25
---

# Candidate-8 fresh independent Protocol-6.4 D2 Review R5

## 1. Immutable binding and disposition

This Review targets immutable Candidate 8 exactly at:

`c6e18ccfce62d47e96dde80600558522c62c28ef`

with Candidate-8 Git blob:

`60598fa33048df16f9cc41e6adf761dd952aa28f`.

The lifecycle descendant

`62ec417a4e9d0899fb1fce286955e07d1fb11bd1`

is a direct child of Candidate 8 and changes only the Candidate-8 repair record, the independent-review handoff, and the active workplan. It was not substituted for Candidate 8 as the semantic Review target.

The pre-freeze author drafts

- `07c273a4e5ec382ed84204af73bd97fe08f5cd34`;
- `d3f4cbbadbf86553361be756c31e372478a338de`

are historical authoring states only.

The accepted parent was reconstructed from:

- accepted D1/D2 kernel `a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`;
- exact accepted D1/D2 source `a4824d28775164aa942fd29fa97ee0957eb87e6f`.

Newer proposed canonical-path files were not treated as accepted parents.

Historical Candidate-4 Review R1, Candidate-5 Review R2, Candidate-6 Review R3, Candidate-7 Review R4, the Candidate-8 repair record, Stage-A MH-1/MPA-0/order-process diagnostics, the active workplan, and applicable PEM entries `FF-001`, `FF-002`, `SP-002`, `SP-003`, and `SP-004` were used only as falsification/evidence context.

No Candidate-8 Stage-C result exists at the reviewed lifecycle state and none was used.

**Overall disposition: NO-PASS**

**SERIOUS CHALLENGE to accepted D1/D2 parent authority: NO**

Candidate 8 repairs four of the five Candidate-7 R4 defect families and materially improves the fifth, but the exact stochastic null used to authorize the two systematic-shift population statements is internally inconsistent with the launch-order randomization that Candidate 8 introduced. The earliest defective owner remains the proposed Candidate-8 D2 overlay.

Candidate 8 must remain immutable historical candidate state. It must not proceed to Stage C and must not be handed to D3/D4. Any semantic repair is Candidate 9 or later.

## 2. Blocking finding B1 — the fixed-stratum conditional-exchangeability theorem is false under the order nuisance that Candidate 8 explicitly admits

Candidate 8 makes two statements that cannot both serve as written.

First, D2.CUEQ8.DEF.015 correctly recognizes that launch-order strata can have different conditional score distributions and therefore independently randomizes one of the six `R1/R2/C` launch permutations for every triplet. It then states that the triplets form an i.i.d. marginal six-stratum mixture.

Second, D2.CUEQ8.DEF.016 and D2.CUEQ8.DEF.021 assert that, under the exact backend-equivalence null, `R2` and `C` are exchangeable **conditional on the sampled launch-order nuisance stratum**, and derive

[
P(S^{RC}_{p,j}>S^{RR}_{p,j})
=
P(S^{RR}_{p,j}>S^{RC}_{p,j})
le rac12.
]

That conditional claim is not generally true once the stratum fixes which child occupies each launch position.

### 2.1 Exact same-backend counterexample

Construct the strongest null: `C` is not merely scientifically equivalent to e3nn; it is another realization of the same backend and same scientific operator.

Let launch position alone create deterministic nuisance values

[
h_1=0,qquad h_2=1,qquad h_3=2,
]

with no backend-label effect at all. Let the protected scalar score between two children be the absolute difference of their nuisance values. This is an admissible order-only counterexample because Candidate 8 expressly allows order strata to have different conditional score distributions.

Condition on the fixed stratum

[
(R1,R2,C).
]

Then

[
S^{RR}=|h_1-h_2|=1,qquad
S^{RC}=|h_1-h_3|=2,
]

so the strict-worse indicator is deterministically one.

Within this fixed stratum, swapping `R2` and `C` is not a symmetry operation; it produces the different stratum `(R1,C,R2)`. Thus `R2` and `C` are not exchangeable conditional on the full sampled permutation even though the candidate backend is literally identical to the reference backend.

The same defect occurs for stochastic position effects whenever the conditional response laws of launch positions differ.

This is a genuine false-fail/null-definition defect, not a prose preference: the Candidate-8 null can reject an exact same-backend realization solely because it conditioned on the randomization variable that was introduced to average the nuisance away.

### 2.2 What the six-permutation draw actually proves

The uniform randomization can support a valid **marginal** symmetry argument, but that is a different theorem.

Pair every permutation with the permutation obtained by exchanging the labels `R2` and `C` while holding the pre-assignment nuisance state fixed. Under a backend-equivalence null whose response law is invariant to that label exchange, the two paired assignments have equal design probability. Therefore the unconditional joint law of

[
(S^{RR},S^{RC})
]

is exchangeable after averaging over the assignment randomization, and strict worse has probability at most one half, including discrete/tied cases.

For the deterministic position counterexample above, the six strata give strict-worse indicators

[
1,0,0,0,0,1,
]

so the marginal strict-worse probability is `2/6=1/3`. The randomized design repairs the nuisance only **after** averaging over the assignment law; it does not create conditional exchangeability inside each realized permutation.

Candidate 8 therefore contains the ingredients for a repair, but immutable Candidate 8 does not state the correct inferential object.

### 2.3 The exact key conditions away the same randomization unless the conditioning level is repaired

Candidate 8 places

[
R=(eta_{m NI},q_{m cat},n,q_{m design})
]

inside the exact authorizing key `A`, and the authorizing record binds the exact design RNG and realized permutations.

That is appropriate for evidence identity/currentness, but the statistical population must distinguish:

1. the pre-assignment scientific/runtime key and **randomization law**; from
2. the post-assignment evidence record containing the realized permutation sequence.

If `q_design` is interpreted as a fixed seed/realized assignment sequence and the Binomial proposition is conditioned on the full exact key including that sequence, then the nuisance strata are fixed rather than independently redrawn. With stratum-specific worse probabilities, the `B_p` are generally Poisson-binomial/non-identically-distributed rather than Binomial((n,p)).

A reproducible record may bind the realized assignments after the fact. It may not simultaneously condition them away and claim that their prospective randomization makes the already-conditioned trials i.i.d.

### 2.4 Cross-triplet host state remains a proof obligation

Fresh OS processes are necessary but not sufficient to prove independent triplets on one target host. CUDA context creation, driver/compiler caches, allocator and device residency, clocks/thermal state, autotuning, filesystem/page cache, and child teardown can persist across process boundaries.

Candidate 8 usefully says qualification fails closed if process isolation or the i.i.d. mixture cannot be established. That prevents a direct false pass. Candidate 9 must nevertheless say what the stochastic proposition conditions on:

- either establish/reset/block persistent host state so the pre-assignment triplet law is common and independent;
- or include that state in a prospective nuisance/block model and use inference valid for that model.

Outcome-dependent redraw, warm-up selection, retry-until-pass, failed-child deletion, or adaptive reassignment remains forbidden.

### 2.5 Why B1 is blocking

The two systematic-shift acceptance statements are authorizing population claims. Their Clopper-Pearson upper bounds require the declared Bernoulli model, and the `1/2` baseline requires an actual exchangeability theorem.

Candidate 8 currently proves the wrong exchangeability statement and is ambiguous about whether the exact qualification key conditions on the randomization that is supposed to create the i.i.d. marginal mixture.

Repair changes the exact null, conditioning set, qualification-key semantics, and statistical proof. That is D2 semantic content. It cannot be corrected by a D3/D4 implementation convention or a review note attached to immutable Candidate 8.

## 3. Required Candidate-9-or-later repair for B1

Candidate 9 or later must preserve the successful independent-per-triplet randomization idea but state one mathematically coherent design.

At minimum it must:

1. define a pre-assignment triplet state (Lambda_p) containing every nuisance coordinate on which inference conditions before child labels are assigned;
2. draw the `R1/R2/C` assignment independently from the exact uniform six-permutation law after (Lambda_p) is fixed;
3. state the backend-equivalence null as label-exchange invariance of the relevant `R2/C` potential-response/consumer-score law, not exchangeability conditional on the full realized permutation;
4. prove that the resulting **marginal** strict-worse indicator has one common Bernoulli probability (p_jle1/2), or replace Binomial Clopper-Pearson with an exact/conservative procedure valid for the actual stratified/dependent design;
5. separate randomization-policy identity from the realized assignment sequence so currentness can bind both without conditioning away the design randomness used by the population statement;
6. state how persistent target-host state is either reset/isolated, blocked and modeled, or causes qualification to fail closed;
7. define startup failure, OOM, timeout, crash, nonfinite child, and infrastructure failure prospectively so none can become outcome-selected discard/redraw; and
8. retain the no-adaptive-retry rule.

No Candidate-8 outcome may be used to choose this repair.

## 4. Parameterized risk authority — otherwise acceptable as a reviewed family

The parameterized-family construction is not independently blocking.

### 4.1 Family versus instance

(eta_{m NI}), (q_{m cat}), and (n) are explicit method-instance coordinates with no generated defaults. Mathematics does not determine the stakeholder's tolerated population risk. Exposing those choices is preferable to Candidate 7's false derivation from an unrelated (Gamma=0.90) content statement.

A D2 family can be reviewed before an exact instance is ratified provided:

- the parameter meanings and admissible domain are fixed;
- no outcome chooses them;
- the exact instance is frozen before Stage C; and
- currentness binds the exact values.

Candidate 8 meets those requirements apart from B1's randomization-coordinate ambiguity. Exact numerical risk values therefore need not themselves be embedded in immutable Candidate 8 merely to make family Review possible.

### 4.2 Domain boundary cases

The declared domain is

[
0leeta_{m NI}le q_{m cat}<0.10.
]

The boundary behavior is coherent but should be interpreted precisely:

- (eta_{m NI}=0) asks the data to support (p_jle1/2) at the declared confidence; this is extremely conservative at a true boundary (p_j=1/2) and can have very low power, but it does not create a false pass.
- (eta_{m NI}=q_{m cat}) merely couples two distinct probability budgets conservatively; the coupling is not a mathematical identity and should not be described as one.
- (q_{m cat}ightarrow0.10^-) is the loosest admissible known-adversary exclusion.
- (q_{m cat}ightarrow0^+) requires rapidly increasing prospective (n).
- (q_{m cat}=0) has no finite feasible (n) because (1-alpha^{1/n}>0) for every finite positive (n). The separate (Qle q_{m cat}) feasibility condition therefore makes that boundary an empty finite-sample subfamily; it is not an executable zero-risk claim.

With (alpha=0.0125), the minimum integer (n) satisfying

[
1-alpha^{1/n}le q_{m cat}
]

is

[
nge
leftlceil
rac{logalpha}{log(1-q_{m cat})}
ightceil.
]

Examples are `n=42` near (q_{m cat}=0.10), `86` at (0.05), `437` at (0.01), and `4380` at (0.001).

### 4.3 Meaning of the 0.10 ceiling

The strict (q_{m cat}<0.10) ceiling is defensible only as a known-counterexample exclusion: a population with a source-defined material failure probability exactly (0.10) lies outside every admissible target risk budget. It is not a derivation that (0.099) is scientifically desirable.

Finite confidence does not make false acceptance impossible. For example, a true (p=0.10) reference process can still produce zero events with small probability. The one-sided confidence construction controls that error; it does not convert a finite sample into proof of zero risk.

### 4.4 (eta_{m NI}le q_{m cat})

These probabilities describe different events, so there is no theorem requiring their equality or ordering. The constraint is nevertheless conservative: it restricts the systematic-score margin and cannot by itself authorize a materiality failure. Since every source-defined material violation is separately governed by the joint (q_{m cat}) event, this restriction is not a false-pass route.

## 5. Exact consumer closure and final-state authority — PASS subject to exact instance enumeration

Candidate 8 legitimately chooses Review R3's complete-actual-consumer closure route rather than attempting cross-basis raw-state numerical equality.

The current role is bounded as

[
TRAIN2
ightarrow checkpoint/monitor
ightarrow retention/admissibility
ightarrow completed-state projection
ightarrow EVAL2/publication
]

with exact `E` part of the qualification identity.

The Candidate-6 final-step hidden-coordinate counterexample is closed for the exact qualified role: after the final optimizer/EMA mutation, the completed portable state is evaluated on exact `E`. A hidden coordinate that changes a current `E` consumer therefore becomes visible even when no later TRAIN2 batch activates it.

A coordinate dormant for every member of current `E` but active for a plausible future deployment use does not become silently authorized. Candidate 8 explicitly places that future consumer outside the qualification claim. Generic open-ended reuse would require a broader accepted relation or separate qualification.

This narrowing is compatible with the present D2 task. It does not delete structural portable-state accounting: the complete forward-affecting inventory remains mandatory, including non-`state_dict` ordinary attributes and `avg_num_neighbors`.

Held-out `E` labels/metrics are observation-only and cannot feed target membership, training, checkpoint selection, early stopping, or another upstream scientific decision.

No raw optimizer/EMA coordinate is granted materiality authority. A latent state difference that changes a governed consequence inside the complete horizon or final `E` is exposed; one that never changes the bounded consequence is outside the claim.

## 6. Source availability and (mathcal R_e) — source-closed and fail-closed

The accepted parent D2 kernel was checked directly rather than inferring tolerances from current D4 behavior.

Relevant accepted owners include:

- D2.DEF.057 for shared checkpoint/replay-retention constraints;
- D2.DEF.058 for role-effective target monitor force-RMSE admissibility and exact inclusive (	au_{CV}/	au_{prod}) boundary semantics;
- D2.DEF.059 for CV outer evaluation and (	heta_{CV});
- D2.IMP.CV / D2.IMP.MONITOR for accepted representative/checkpoint ranking and practical-equivalence ordering;
- exact tie, lexicographic, and local guard semantics imported by those owners; and
- D2.DEF.060A for exact identity/equality and exact canonical binary64 comparison when a governed output has no accepted nonzero tolerance.

Thus Candidate 8 need not invent a materiality scale from ULP, Huber delta, a D4 tolerance, sample maximum, or observed Candidate behavior.

The Candidate-8 rule that an actually governed continuous consumer with no source-available matching relation makes the role unqualifiable is correct fail-closed behavior.

Threshold-touching, inclusive/exclusive, exact-tie, practical-equivalence, lexicographic, and multi-coordinate cases remain source-owned. Candidate 8's local margin relations are conservative sufficient conditions; they do not widen any accepted threshold.

Reported but unconsumed metrics are correctly excluded from authorizing channels.

The exact instance still must enumerate the actual current `E` and source identity of every (mathcal R_e) before Stage C. A missing consumer/source at that stage is failure, not permission to invent a tolerance.

## 7. IEEE ULP primitive and score pair — PASS

For each exact IEEE binary dtype, Candidate 8 maps finite values to

[
r_d(x)=
egin{cases}
0,&x=pm0,\
+m_d(x),&x>0,\
-m_d(x),&x<0.
end{cases}
]

This gives one rank to signed zero and monotone adjacent ranks over negative finite values, the negative normal/subnormal boundary, negative minimum subnormal, zero, positive minimum subnormal, positive normal/subnormal boundary, exponent transitions, and largest positive finite.

NaN and infinity fail closed. Cross-dtype ULP comparison is undefined unless an already accepted conversion relation first puts the coordinates in one exact dtype, so binary64 control quantities cannot silently be coerced to binary32.

[
S_{max}=max_i z_i
]

catches a rare large numerical displacement, while

[
S_Sigma=sum_i z_i
]

is exact unnormalized integer ULP mass. Adding unchanged coordinates contributes zero. Tensor split/merge and serialization block layout therefore cannot dilute or tune the score.

Mixing ULP counts from multiple exact dtypes inside the stochastic observation score is not itself a materiality assertion. Different physical scales/conditioning are independently protected by (mathcal R_e).

Equal-(S_{max}), equal-(S_Sigma) displacement vectors with different geometry do exist. Candidate 8 does not claim otherwise. If one geometry is materially different, the source-owned per-consumer relation or exact discrete decision must fail. Thus the compression is acceptable only as the secondary systematic-shift statistic, which Candidate 8 states explicitly.

Exact-integer accumulation of sufficient range is order-independent and cannot overflow by definition.

## 8. Finite-sample probability statements — algebraically correct once B1 is repaired

For four simultaneous one-sided population statements and target simultaneous confidence

[
kappa=0.95,
]

Candidate 8 assigns

[
alpha=(1-kappa)/4=0.0125.
]

Bonferroni requires no independence among the four statements.

For an actual Binomial((n,p_j)) strict-worse count (X_j), an exact one-sided Clopper-Pearson upper bound (U_j) with per-statement error (alpha) is valid, and the acceptance rule

[
U_jle rac12+eta_{m NI}
]

is coherent.

For zero observed joint materiality failures, the exact one-sided bound is

[
Q=1-alpha^{1/n},
]

and requiring (Qle q_{m cat}) is correct.

The same prospectively fixed (n) can support both systematic-shift and joint-tail statements; sharing observations does not invalidate Bonferroni. Reference and candidate joint events may also share (n); they are separate dependent statements with their own simultaneous error allocation.

Increasing (n) after outcomes, accepting only completed favorable triplets, or stopping a failed run and replacing it is forbidden. Stopping immediately after a definitive failure is operationally harmless only because no passing dataset may then be declared from that stopped sequence.

Zero events establishes an upper confidence bound on event probability, not zero event probability.

All of these statements remain contingent on repairing B1 so the `B_p` model is actually Binomial or replacing Clopper-Pearson with a procedure valid for the final design.

## 9. Candidate-6/R3 adversary and rare tails — repaired

Reproduce the R3 adversary:

- reference self score (0) with probability (0.90);
- reference self score (M) with probability (0.10);
- candidate score always (M/2).

If (M) violates any source-owned (mathcal R_e), the reference joint materiality population has failure probability (0.10). Since every admissible target has (q_{m cat}<0.10), that population lies outside the target reference-risk class. Finite sampling retains the declared confidence error; it does not alter the population proposition.

If (M) remains inside every accepted (mathcal R_e), there is no materiality failure. Whether the constant (M/2) candidate is accepted then legitimately depends on the repaired systematic-shift proposition and ratified (eta_{m NI}). No sample maximum may widen (mathcal R_e).

For a candidate with a very rare but arbitrarily severe source-defined material violation, severity is binary at the event layer: any observed violation is one joint event and fails the observed sample. Unobserved occurrence probability is bounded only by the exact finite-confidence (q_{m cat}) proposition. Severity is therefore not averaged away.

A rare large reference excursion cannot mint candidate tolerance. If it is outside (mathcal R_e), it is a reference materiality event; if inside, it remains inside the fixed source relation and does not widen that relation.

Any consumer whose accepted owner requires deterministic/exact equality remains exact through (mathcal R_e) and exact-decision preservation; a nonzero (q_{m cat}) cannot redefine an exact source relation.

## 10. Projection structural oracle and pinned MACE 0.3.16 — PASS as fail-closed method scope

Pinned MACE 0.3.16 was reconstructed directly from its conversion sources.

The production e3nn -> CuEq converter:

- derives `kmax` membership with `get_kmax_pairs`;
- for `use_reduced_cg=true`, obtains `symmetric_contraction_proj` and multiplies contraction coefficients by that projection;
- otherwise concatenates the full-basis contraction weights directly;
- copies matching state keys/reshapes;
- copies `interactions[i].avg_num_neighbors` outside `state_dict`.

The production CuEq -> e3nn converter:

- performs the reverse split;
- for `use_reduced_cg=true`, explicitly uses `np.linalg.pinv(proj)`;
- also copies `avg_num_neighbors` outside `state_dict`.

This confirms both the common-owner danger found by R3/R4 and the necessity of Candidate 8's non-`state_dict` inventory.

Candidate 8 correctly forbids an independent oracle from reusing the production converter, inverse converter, `get_kmax_pairs`, `symmetric_contraction_proj`, production mapping tables, production key enumeration/correspondence, or production projection/pseudoinverse matrices as semantic owners.

Exact inventory/cardinality reconciliation must therefore catch omission, duplicate mapping, wrong semantic identity, wrong permutation, wrong k-range, wrong contraction membership, extra fallback, and quiescent forward-capable-state loss before evaluator comparison.

### 10.1 Reduced-CG inverse non-uniqueness

The pinned source also confirms a critical scope fact: `symmetric_contraction_proj` is a reduced reparameterization, and its own documentation includes a rectangular projection example. The production reverse path uses a Moore-Penrose pseudoinverse to choose one full-basis representative.

Functional equality alone does not generally make an inverse coefficient vector unique when the destination full basis has gauge/null directions.

Candidate 8 does **not** silently authorize that ambiguity. It requires the independent semantic map to prove existence/uniqueness on the active authenticated subspace and says a non-unique or rank-deficient required inverse fails closed. It also explicitly refuses to let production `numpy.linalg.pinv` own the semantics.

Therefore a reduced-CG key remains unsupported unless an independent accepted representation convention defines the active subspace/canonical inverse. This is restrictive but not a false-pass defect.

For a full-basis key, the contraction transfer may reduce to exact structural concatenation/split rather than a nontrivial floating (A^ast). The exact Stage-C model configuration must authenticate which case applies; this Review does not infer it from a filename or current implementation default.

## 11. Exact semantic transform and coefficient qualification — R4 scalar false pass closed

Where a nontrivial transform is admissible, Candidate 8 requires an independently derived exact semantic (A^ast), a certified higher-precision enclosure, proof of existence/uniqueness, and exact bitwise equality

[
widehat A=operatorname{RN}_d(A^ast)
]

before output accumulation error is considered.

The R4 scalar adversary

[
A^ast=1,qquad widehat A=100,qquad x=1
]

therefore fails immediately. Wrong-sign, wrong-permutation, wrong-k-range, and subtly wrong coefficient matrices likewise fail the coefficient gate before evaluator agreement.

The rule may be stronger than a production converter that computes a mathematically equivalent coefficient by another rounding path. That creates a possible false fail, not a false pass. Candidate 8 deliberately chooses fail-closed behavior. If the current production converter cannot meet correctly rounded equality, Stage C fails; the Review may not widen the coefficient rule to rescue it.

For reduced-CG reverse mapping, Section 10.1 applies: no unique independently owned inverse means the key fails before coefficient comparison.

## 12. Floating transfer bound — acceptable only under the realized kernel proof

Candidate 8 uses

[
gamma_n=rac{nu}{1-nu}.
]

That is a standard floating-point accumulation form only after the actual sequence of rounded operations is established and (nu<1). Candidate 8 binds the actual reduction structure, accumulation dtype, fused-kernel order, coefficient dtype, operation count, rounding mode, coefficient provenance, and kernel identity, and fails closed if the assumptions cannot be certified.

The coefficient term

[
|operatorname{RN}_d(A^ast)-A^ast|,|x|
]

is now source-derived rounding error rather than the observed production coefficient discrepancy, closing R4 B5's self-authorization route.

If (x) is already an authenticated learned-dtype state tensor, its finite floating value can be treated as the exact real input to the transform analysis. Any additional dtype conversion before the contraction needs its own rounding term.

Ill conditioning, cancellation, overflow, unsupported underflow/subnormal or flush-to-zero behavior, non-default rounding, and an unproved fused reduction fail closed rather than widening the bound.

Stage C must derive the bound for the realized kernel rather than substituting nominal tensor length for the actual rounding model.

## 13. Projection evaluator relation — structurally subordinate and source-closed

The projection evaluator is a distinct stochastic relation over one exact completed state and exact role-effective EVAL2 consumer population.

Its common anchor is the canonical portable reference state. Only source-owned role-effective EVAL2 consumers are authorizing.

It has its own prospectively fixed (n_{m eval}) and design randomization. Its (eta_{m NI}) and (q_{m cat}) cannot be looser than the TRAIN2 instance.

The same B1 randomization/null repair must apply to the evaluator relation. That does not create a separate blocker; the evaluator imports the defective Candidate-8 stochastic theorem.

Structural inventory, correspondence, coefficient, or transform failure remains terminal. Evaluator agreement cannot rescue it.

Post-projection EVAL2 provider identity remains unequivocally e3nn.

## 14. Qualification key and currentness — PASS except for B1 conditioning semantics

The exact key correctly binds the ordered backend/kernel pair ((K_R,K_C)), runtime arithmetic coordinates (ho), model/corpus/head/objective/horizon/seed identity, exact consumer population `E`, risk coordinates, and method identity.

The authorizing record additionally binds every (mathcal R_e) source, structural inventory, mapper/oracle identities, semantic transform/correct rounding proof, ULP-rank version, triplet evidence, decision traces, restart mode, and projection/evaluator evidence.

Any changed model, corpus, scientific seed, risk coordinate, consumer population, source relation, runtime, mapper, transform owner, backend/kernel pair, or materially arithmetic coordinate stales the record.

Candidate-4 through Candidate-7 evidence cannot authorize Candidate 8.

The one required repair is to distinguish prospective randomization-law identity from the realized assignment sequence at the inferential conditioning level, as specified in B1.

## 15. Accepted TRAIN2 semantics and scope preservation — PASS

Candidate 8 preserves the accepted P5 loader:

- replay/`pt_head` first and target second before shuffle;
- native shuffle/sampler;
- no balancing sampler;
- no intentional target duplication;
- `drop_last=true`;
- target-only foundation adaptation when that exact role applies.

It executes the complete accepted optimizer horizon.

Same-backend restart may be qualified only under an exact keyed restart boundary. Cross-backend TRAIN2 restart remains unsupported.

Source/DATA6 CuEq remains outside Candidate-8 authority.

FP64 CuEq TRAIN2 remains unsupported and fail-closed. Forward-only evidence cannot authorize FP64 TRAIN2.

Routine doctor remains only an authenticated currentness/reachability/finiteness witness. It cannot calibrate, widen, or create authority.

Candidate 8 remains D2. Persistence, scheduler concurrency, packaging, and implementation decomposition remain D3/D4 concerns.

## 16. Historical regression check — R1-R4 closures preserved

No regression was found in the following earlier closures:

- no reused forward-inference tolerance as TRAIN2 bias budget;
- no finite two-update/window extrapolation;
- no recurrence/secant extrapolation;
- no metadata-only exposure sampling;
- no raw gradient-coordinate equivalence;
- no invalid cross-basis optimizer equality;
- EMA consequence coverage;
- exact final-state consequence for exact `E`;
- source/DATA6 narrowing;
- FP64 fail-closed behavior;
- exact signed-zero ULP semantics;
- complete ordinary-state inventory;
- independent projection semantic ownership requirement;
- exact scientific-decision preservation;
- e3nn EVAL2 provider identity;
- no adaptive retry; and
- no Candidate-outcome calibration.

The consumer-closure narrowing does not reopen the Candidate-6 complete-state defect inside the exact qualified role because final completed-state `E` evaluation is mandatory. It deliberately declines authority for future consumers outside `E`.

## 17. Evidence/lifecycle integrity — PASS

The immutable semantic target is exactly:

`c6e18ccfce62d47e96dde80600558522c62c28ef`

with candidate-file blob:

`60598fa33048df16f9cc41e6adf761dd952aa28f`.

The lifecycle descendant

`62ec417a4e9d0899fb1fce286955e07d1fb11bd1`

is one direct child and changes only lifecycle/workplan/repair/handoff state.

No Candidate-8 Stage-C result exists in the reviewed repository state.

No Candidate-7 or Candidate-8 outcome was found as an owner for (eta_{m NI}), (q_{m cat}), (n), `E`, any (mathcal R_e), score definitions, launch randomization, projection transform semantics, or projection bounds.

Stage-A evidence and PEM were used only as evidence/challenge context, not D2 authority.

## 18. Review matrix against the handoff challenge set

| Handoff area | Disposition | Review conclusion |
|---|---|---|
| A. Parameterized risk authority (1-7) | PASS with feasibility note | Family-level Review is legitimate; exact instance must be ratified prospectively; (q_{m cat}=0) has no finite feasible (n); no preferred value invented. |
| B. Exact consumer closure/final state (8-15) | PASS | Complete actual-consumer route closes the final-state defect for exact `E`; future consumers remain outside authority; inventory remains complete. |
| C. Source availability/(mathcal R_e) (16-23) | PASS/fail-closed | Accepted threshold/ranking/exact-equality owners exist for current roles; missing owner makes role unqualifiable. |
| D. ULP primitive/trace (24-31) | PASS | IEEE rank, signed zero, nonfinite rejection, dtype separation, exact sum all coherent. |
| E. (S_{max}+S_Sigma) (32-39) | PASS | No zero dilution/storage partition dependence; geometry loss is subordinate to (mathcal R_e). |
| F. Triplet/exchangeability (40-47) | **NO-PASS — B1** | Fresh triplet is right unit and shared anchor can be valid, but fixed-stratum conditional exchangeability is false when order position matters. |
| G. Six-permutation nuisance mixture (48-57) | **NO-PASS — B1** | Uniform independent randomization can justify a marginal mixture, not the stated conditional theorem; conditioning/currentness and persistent host state must be repaired. |
| H. Finite-sample statements (58-70) | Formula PASS / model blocked | Bonferroni and CP algebra are correct only after B1 supplies a valid Binomial or replacement model. |
| I. Candidate-6/R3 adversary (71-75) | PASS | Material (M) is a joint reference event; nonmaterial (M) is handled by systematic-shift relation; no maximum widens (mathcal R_e). |
| J. Rare candidate tails (76-81) | PASS | Severity via source relation, occurrence via (q_{m cat}); exact/deterministic consumers remain exact. |
| K. Projection oracle independence (82-87) | PASS | Shared converter semantic owners prohibited; complete inventory including `avg_num_neighbors` required. |
| L. Exact (A^ast) (88-95) | PASS/fail-closed | Unique semantic map required; reduced-CG inverse/pinv ambiguity is explicitly unsupported unless independently source-closed. |
| M. Coefficient qualification (96-100) | PASS | R4 scalar self-authorization closed by exact correctly-rounded coefficient equality; strictness may false-fail but cannot rescue production. |
| N. Floating bound (101-111) | PASS subject to realized proof | Actual operation/reduction/dtype/FMA/subnormal semantics must be certified; otherwise fail closed. |
| O. Projection evaluator (112-118) | inherits B1 | Structurally subordinate and e3nn-owned, but its stochastic theorem requires the same Candidate-9 repair. |
| P. Key/currentness (119-124) | PASS except B1 conditioning split | Exact semantic/currentness coordinates are bound; randomization-law versus realized-assignment conditioning must be distinguished. |
| Q. TRAIN2 semantics/scope (125-133) | PASS | Loader, horizon, restart, source/DATA6, FP64, doctor, D2 boundary preserved. |
| R. Historical regressions (134-136) | PASS | No R1-R4 closure regressed; exact-`E` narrowing is explicit. |
| S. Evidence/lifecycle (137-140) | PASS | Candidate/blob/descendant/no-Stage-C/no-outcome-tuning checks pass. |

## 19. Workplan/lifecycle action required

The active workplan must remain open and be revised to record this R5 NO-PASS.

Required state:

1. preserve immutable Candidate 8 and its repair/history records unchanged;
2. preserve all Candidate-8 repairs that this Review passed;
3. repair only the stochastic null/randomization/conditioning defect unless a fresh independent issue is found;
4. freeze the semantic repair as Candidate 9 or later;
5. perform a fresh independent D2 Review of that immutable candidate;
6. do not run Candidate-8 Stage C;
7. do not use Candidate-8 outcomes to choose the replacement randomization law, risk coordinates, process count, source relations, or score definitions;
8. keep D3/D4 blocked; and
9. after a future independent PASS, require stakeholder ratification of the exact reviewed instance before Stage C.

## 20. Final disposition

**NO-PASS**

**SERIOUS CHALLENGE to accepted D1/D2 parent authority: NO**

Candidate 8 is not adequate for stakeholder instance ratification or Stage-C testing because its authorizing systematic-shift theorem conditions on the realized launch-order stratum while simultaneously relying on randomization across those strata to remove order nuisance. The randomized design can likely be repaired prospectively by moving the exchangeability claim to the correct pre-assignment/marginal level and defining the exact inferential conditioning/currentness split, but that is a D2 semantic change and therefore requires Candidate 9 or later.
