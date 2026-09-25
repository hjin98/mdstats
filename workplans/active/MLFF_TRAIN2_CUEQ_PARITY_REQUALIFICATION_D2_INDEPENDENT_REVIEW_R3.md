---
kind: D2-independent-review
protocol_version: 6.4.0
status: NO_PASS
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
reviewed_candidate: f3035317dcea1448c9d6d825c6f2d9f156aaec24
reviewed_candidate_blob: f2596ef7bb0f146e6a6ec3b0af44ffcf8b96764a
lifecycle_head_basis: 2fb4bfcac6dfc7272091fa428d16133f1a6d5b6c
accepted_parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_parent_d2_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
serious_challenge: false
highest_blocking_owner: D2
date: 2026-09-25
---

# Candidate-6 fresh independent Protocol-6.4 D2 Review R3

## 1. Immutable review binding and disposition

The semantic Review target is immutable Candidate 6:

f3035317dcea1448c9d6d825c6f2d9f156aaec24

The Candidate-6 file at lifecycle head 2fb4bfcac6dfc7272091fa428d16133f1a6d5b6c has Git blob:

f2596ef7bb0f146e6a6ec3b0af44ffcf8b96764a

which is exactly the frozen blob required by the Candidate-6 handoff. The mutable lifecycle head was not substituted for Candidate 6.

The accepted parent was reconstructed from the pinned Protocol-6.4 authority, not from newer proposed canonical-path material:

- accepted D1/D2 kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2;
- exact stakeholder-ratified D1/D2 source: a4824d28775164aa942fd29fa97ee0957eb87e6f.

Historical Candidate 4 and Candidate 5 remain immutable failed candidates. Stage-A MH-1 and MPA-0 observations were used only as method-design evidence. No Candidate-6 Stage-C outcome was used in this Review.

**Overall disposition: NO-PASS**

**SERIOUS CHALLENGE to accepted D1/D2 parent authority: NO**

The earliest defective owner is the proposed Candidate-6 D2 acceleration-equivalence overlay. Candidate 6 materially improves Candidate 5, but four genuine false-pass/undefined-decision defects remain in the proposed numerical relation. A fifth statistical-derivation defect is also recorded; it does not independently require a larger sample because the existing all-family zero-exceedance observations support a correct joint-process bound.

Candidate 6 therefore must not proceed to Stage C and must not be promoted to D3/D4. Any semantic repair is Candidate 7 or later.

## 2. Blocking finding B1 — the four score families are not injective over the final portable state or the downstream continuous consequences Candidate 6 claims to protect

Candidate 6 says that the protected consequence includes the final completed state used by projection/EVAL2, but the authorizing score set observes only:

- optimizer-consumed loss values;
- energy/force/stress on one finite witness corpus W for the live model;
- the same finite W for EMA; and
- an RMS reduction of those same physical-component ULP distances.

It never directly protects the complete projected portable model state, gradients, updates, or the complete continuous EVAL2/monitor consumer domain.

### Concrete falsifying case

Consider a two-coordinate learned model state theta=(a,b) and an exact qualification realization in which all TRAIN2 examples, checkpoint-monitor examples, and the predeclared W have zero sensitivity to b, while an accepted held-out EVAL2 configuration x-star has nonzero sensitivity to b.

At the last relevant optimizer update, suppose the e3nn backward produces the correct update Delta b=0 while a defective CuEq backward/update path writes Delta b=epsilon. This can represent a masked-property/inactive-to-active, rare-environment, or erroneous-gradient channel. The forward loss for that update is unchanged because loss is observed before the defective state mutation. There need be no later TRAIN2 update that exposes b.

Then:

1. every loader/head/mask identity remains exact;
2. every recorded loss value can be identical;
3. all W live and EMA physical values can be identical;
4. all four Candidate-6 scores can be zero;
5. checkpoint/admissibility decisions can be identical because the monitor has zero sensitivity to b;
6. the completed CuEq state contains b=epsilon;
7. the projection relation can faithfully map that defective state into e3nn coordinates and pass transient-CuEq versus mapped-e3nn parity, because projection tests preservation of the candidate state rather than equality to the reference-trained state; yet
8. EVAL2 on x-star differs by a material amount.

This is a genuine false pass. Full-horizon execution closes Candidate-5 recurrence/window extrapolation, but it does not make a finite functional witness injective over the trained state. The same construction applies to EMA if a later accepted consumer evaluates an EMA state outside W.

The defect is especially important because the accepted pipeline deliberately separates TRAIN2 from EVAL2 and publication. A correct CuEq-to-e3nn mapper cannot repair a training-state discrepancy; it only preserves it in the portable representation.

### Required Candidate-7 repair

Retain the exact-realization and full-horizon narrowing, but make the protected continuous consequence complete enough for the claim.

At minimum Candidate 7 must do one of the following, source-closed to the accepted role:

1. compare the projected live and EMA model state in the common portable e3nn coordinate at every state boundary whose value can be consumed downstream, with complete forward-affecting state inventory and a valid stochastic numerical relation; or
2. bind and observe the complete actual downstream continuous consumer population for the exact role, including every checkpoint monitor quantity and every EVAL2/held-out quantity whose value can affect accepted assessment/publication, not only its final boolean decision.

If neither is intended, the claim must be narrowed so the CuEq-trained state cannot authorize downstream EVAL2/publication. That narrowing would not satisfy the current pipeline obligation and therefore is not a practical repair.

A finite W may remain as a diagnostic/non-dilution witness, but it cannot be the sole owner of complete portable-state consequence.

## 3. Blocking finding B2 — a sample-maximum self-repeatability envelope can authorize a systematic candidate shift and the reference-stability gate does not control that permissiveness

The reference-side finite-sample theorem itself is correct:

- for J=4 and Gamma=0.90, 4*0.90^42 = 0.0478900607 <= 0.05, so 42 is the minimum cardinality and n_ref=44 is conservative;
- dependence among the four score families does not invalidate the union bound.

The numerical defect is what the maximum-based limit means as backend equivalence. A one-sided tolerance limit controls a lower content property of the reference distribution; it places no useful upper control on the width of the admitted backend envelope and does not test whether the candidate distribution is systematically shifted relative to ordinary reference behavior.

### Concrete falsifying distribution

For one fixed score family, let accepted e3nn self-repeatability be

S_RR = 0 with probability 0.90
S_RR = M with probability 0.10

for some material M, while every governed discrete scientific decision remains unchanged in both cases.

With 44 reference processes,

P(L=M) = 1 - 0.90^44 = 0.9903022627.

Now let a non-equivalent CuEq backend produce

S_RC = M/2

in every fresh candidate process, again without changing the tested discrete decisions.

Whenever the reference sample contains one rare M excursion, every one of the 44 candidate processes passes S_RC <= L. Thus this systematically shifted backend passes with approximately 99 percent probability under this adversary even though the candidate discrepancy occurs in 100 percent of processes while nonzero reference self discrepancy occurs in only 10 percent.

This directly violates the workplan's protected purpose of distinguishing systematic e3nn/CuEq disagreement from ordinary realization-level variability.

The REFERENCE_METHOD_UNSTABLE rule does not close the hole. It fails only when reference variability changes a governed discrete scientific decision, becomes non-finite, violates common input, or breaks restart. A numerically very noisy but decision-stable reference can therefore mint an arbitrarily permissive envelope for continuous quantities.

The same conceptual weakness applies to the projection evaluator envelope: a stochastic evaluator tolerance maximum is not, by itself, evidence that a systematically shifted transient-CuEq/mapped-e3nn evaluator distribution is equivalent to ordinary e3nn self behavior.

### Required Candidate-7 repair

Separate two questions that Candidate 6 currently conflates:

1. **reference adequacy** — whether the e3nn self-repeatability population is itself numerically adequate for the protected continuous consequences; and
2. **candidate equivalence** — whether the CuEq cross-backend score distribution is no worse than ordinary reference self variability rather than merely below one high reference order statistic.

The reference adequacy condition must be derived from accepted numerical/scientific consequence semantics, not from a new arbitrary constant and not from candidate outcomes.

The candidate rule must reject the explicit 0/M reference versus constant M/2 candidate adversary. A defensible repair can use a predeclared distribution-free comparison such as a simultaneous one-sided stochastic-dominance/non-inferiority relation between the candidate and reference process-score distributions, or an equivalent source-closed construction that controls systematic location/quantile shift. The reference sample may define the rule prospectively, but one rare reference observation must not become a universal hard ceiling.

No Candidate-6 Stage-C outcome may be used to choose that repair.

## 4. Blocking finding B3 — the ULP primitive is not uniquely defined across signed zero

Candidate 6 defines U_d(a,b) as the absolute distance between monotone ordered IEEE bit-pattern integers while treating +0 and -0 as equal. That does not uniquely specify the integer rank map.

A conforming implementation can either:

- retain two adjacent signed-zero bit-pattern ranks and special-case only the pair (+0,-0) as distance zero; or
- quotient the two signed-zero encodings into one rank before computing distances.

For the adjacent finite values (-min-subnormal, +min-subnormal), these conventions produce different integer distances. At an integer tolerance boundary that one-count difference changes PASS versus FAIL.

The ambiguity also affects exactly the near-zero/subnormal cases the handoff requires this Review to audit. Because ULP distance is an authorizing score coordinate, an implementation-dependent rank map is a D2 decision ambiguity, not a style issue.

### Required Candidate-7 repair

Define one exact rank function over finite values of each supported IEEE dtype. A simple admissible form is:

- strip the sign bit to obtain the finite nonnegative magnitude-bit integer m;
- assign rank r=+m for nonnegative values and r=-m for negative values;
- map both signed zeros to rank 0; and
- define U_d(a,b)=abs(r(a)-r(b)).

Any equivalent exact formula is acceptable, but Candidate 7 must state it normatively and include adjacency fixtures for:

- negative and positive ordinary numbers;
- -min-subnormal, signed zero, +min-subnormal;
- subnormal/normal boundary;
- exponent boundaries;
- same-value signed zero;
- NaN/infinity fail-closed behavior; and
- exact dtype/no implicit cross-dtype conversion.

## 5. Blocking finding B4 — projection-oracle independence remains vulnerable to shared semantic owners in the pinned MACE 0.3.16 conversion paths

Candidate 6 correctly rejects the existing inverse converter as automatically independent, but its normative independence clause excludes only:

- calling the primary mapper; and
- consuming the same generated mapping table.

That is insufficient against the actual pinned MACE 0.3.16 implementation.

Direct inspection of the pinned conversion sources shows that the e3nn->CuEq and CuEq->e3nn converters share:

- get_kmax_pairs;
- the same symmetric_contraction_proj semantic owner;
- the same state-key correspondence pattern;
- the same symmetric-contraction key enumeration; and
- the same copy/reshape logic.

The CuEq->e3nn path additionally forms a pseudoinverse with numpy.linalg.pinv and applies the floating transform with torch.einsum.

### Concrete falsifying case

Suppose a shared key-pair enumeration owner has an off-by-one defect that omits one last-layer contraction under a particular keep_last_layer_irreps/correlation combination. The production mapper uses that owner. An "independent" oracle reimplements or imports the same pair-enumeration/key-correspondence owner into a different function and never calls the production mapper or consumes its generated table.

Under Candidate-6 wording, that oracle can satisfy the two explicit independence exclusions while reproducing the same omission. If the omitted state is quiescent on the frozen evaluator witness, the physical projection envelope also passes. A later EVAL2 configuration can activate the omitted contribution.

The statement that dropped/quiescent state must fail is therefore not enforceable unless the inventory and correspondence oracle are themselves independent of the mapper's semantic enumeration.

There is also a concrete forward-affecting state category that must not be lost by a state_dict-only interpretation: MACE 0.3.16 InteractionBlock stores avg_num_neighbors as an ordinary module attribute and divides messages by it during forward execution. The native converters explicitly copy interactions[i].avg_num_neighbors in addition to state_dict contents. A complete portable-forward inventory must therefore include forward-affecting non-parameter/non-buffer state or prove it is reconstructed identically from independently authenticated architecture/configuration.

### Required Candidate-7 repair

The structural oracle contract must explicitly prohibit common semantic owners, not merely common execution:

1. independent source and destination inventory derivation;
2. no shared mapper, generated mapping table, key-correspondence owner, pair-enumeration logic, get_kmax_pairs owner, or generated projection-matrix object;
3. explicit accounting for every forward-affecting parameter, buffer, and non-state_dict configuration/attribute;
4. independent semantic derivation of each copy/reshape/permutation/linear-transform correspondence;
5. exact set/cardinality reconciliation before any numeric comparison; and
6. fault-injection oracles for omission, duplicate mapping, wrong permutation, wrong kmax pair, wrong contraction matrix, and quiescent-state loss.

The oracle may share only primitive tensor/value access and the accepted mathematical architecture specification, not the implementation logic under test.

## 6. Statistical derivations and nonblocking corrections

### 6.1 Reference cardinality

For TRAIN2:

4*0.90^41 = 0.0532111786 > 0.05
4*0.90^42 = 0.0478900607 <= 0.05
4*0.90^44 = 0.0387909492.

Therefore Candidate 6 is correct that 42 is sufficient/minimal under its stated union-bound reference construction and 44 is conservative.

Family dependence does not invalidate the union bound.

For projection:

2*0.90^35 = 0.0500631101 > 0.05
2*0.90^36 = 0.0450567991 <= 0.05.

Therefore n_P=36 is correct for the stated projection reference-side tolerance construction.

### 6.2 Candidate zero-exceedance statement

The sentence attributing the joint candidate population claim to "the same Bonferroni/union-bound family-wise allocation" is mathematically wrong as written.

With a per-family Bonferroni confidence allocation alpha_j=0.05/4=0.0125, zero exceedances in 44 processes gives the exact one-sided upper bound

p_j <= 1 - 0.0125^(1/44) = 0.0947928934

for each family simultaneously at family-wise confidence 0.95. A union bound on those four exceedance probabilities yields only

P(all four pass) >= 1 - 4*0.0947928934 = 0.6208284263,

not 0.90.

However, the existing Candidate-6 observation rule already records zero occurrences of the **joint process-level event**

Y_p = 1 if any of the four score families exceeds its fixed reference limit.

For zero Y events in 44 independent candidate processes, the exact one-sided 95 percent upper bound is

p_any <= 1 - 0.05^(1/44) = 0.0658187711.

Thus the raw zero-all-families rule actually supports a stronger-than-90-percent joint process-content claim at 95 percent confidence. No larger n_C is required for that corrected derivation.

This error is not counted as an additional false-pass blocker because the unchanged observation/decision rule contains the sufficient joint data. Candidate 7, already required by B1-B4, must nevertheless replace the incorrect Bonferroni explanation with the process-level joint-event derivation.

The 95 percent reference-tolerance statement and the 95 percent candidate-process statement are separate inferential claims. They must not be silently rephrased as a single joint 95 percent statement about both stages; two separate 95 percent guarantees alone provide only a 90 percent union-bound lower guarantee for their intersection.

## 7. Other required falsification questions

### 7.1 Exact-realization scope

The exact-realization narrowing is legitimate and materially better than Candidate 5. The symbolic key plus the authorizing-record requirements bind initial state, corpus/loader, objective, horizon, runtime/device/kernel, optimizer/EMA/scheduler, construction/execution order, witness identity, restart mode, and projection identity. No material broad generalization was found in the prose.

Arithmetic-relevant ambient state not named individually must be included in rho/currentness when it can change the realized arithmetic. If production can realize multiple materially distinct construction/execution orders, each order is a distinct key or must be explicitly incorporated into the stochastic population; one order cannot authorize another.

### 7.2 Full-horizon replacement of Candidate-5 extrapolation

Executing every accepted TRAIN2 update genuinely closes Candidate-5 B4-B6 for effects that become visible within the observed TRAIN2 horizon. No recurrence theorem or sparse-window extrapolation remains.

B1 above is different: the escape is a final/downstream continuous-state consequence not injectively represented by the four score families.

### 7.3 Optimizer semantics and restart

Candidate 6 validly removes the non-injective finite optimizer-action probes and does not claim raw cross-parameterization optimizer-state equality. A hidden optimizer-state difference that affects a later update inside the bound horizon is exercised by the full trajectory. A difference that never affects any governed consequence before training ends need not be equal.

Same-backend restart is correctly qualification-keyed; mid-run backend switching is explicitly unsupported. No separate optimizer-state blocker remains beyond B1's missing complete output-state consequence.

### 7.4 EMA semantics

Complete-horizon EMA observation on W is coherent for that bounded functional domain. It does not establish global EMA-state equality, and Candidate 6 no longer claims such a theorem.

Any EMA state used by downstream EVAL2/publication outside W inherits B1 and must be protected at the actual consumer/state boundary.

### 7.5 Score-family structure

S_rms is dimensionless and not mathematically malformed. Although bounded by the componentwise maximum for one fixed realization, its independently calibrated population behavior can detect broad moderate shifts that do not trigger a rare maximum threshold, so it is not automatically redundant.

The score family remains incomplete because gradients/updates and complete portable state/downstream continuous consumers are not injectively represented; that is B1.

### 7.6 Construction/execution order

Binding one production order is a legitimate narrowing. Averaging over four order cells is not required if real production has one deterministic relevant order per qualification key. If the actual runtime can vary a material order dynamically under one nominal key, the key/population definition must be widened explicitly or each order qualified separately.

### 7.7 Complete-loader semantics

The accepted Protocol-6.4 P5 owner and current realized P5 specification agree with Candidate 6:

- replay-enabled foundation P5 uses replay/pt_head first and target second before shuffle;
- there is no balancing sampler;
- there is no intentional target duplication;
- current foundation-P5 training uses drop_last=true;
- the path is single-process unless separately qualified; and
- naive target-only foundation fine-tuning also uses shuffled drop_last=true, not the P3 target-size drop_last=false geometry.

Complete-horizon Candidate-6 execution therefore exercises every update and every loader transition actually realized by the bound accepted TRAIN2 path. It does not need to fabricate exposure of examples legitimately dropped by the accepted loader.

### 7.8 Source/DATA6 narrowing

The accepted Protocol-6.4 D2 parent contains no CuEq-specific acceleration relation. Current generated policy is source/DATA6/evaluation e3nn with TRAIN2 cueq. Candidate 6 therefore validly narrows away generic CuEq source/DATA6 authority instead of inheriting historical D4 allclose rules.

Removal of an unaccepted optional acceleration path is not a scientific regression. No serious challenge to the accepted parent arises here.

### 7.9 FP64 scope

FP64 CuEq TRAIN2 is unambiguously unsupported and fail-closed. Source/DATA6 evidence, FP32 TRAIN2 qualification, and projection evidence cannot authorize FP64 TRAIN2. This Candidate-5 defect is closed.

### 7.10 Floating projection bound

The formula gamma_n = n*u/(1-n*u) is a standard forward-error coordinate for an appropriately modeled finite linear reduction. The pinned MACE 0.3.16 symmetric-contraction conversion is indeed linear in the weight tensor once the projection matrix is fixed, and it uses torch.einsum for the contraction.

Candidate 6 correctly says the operation count and reduction structure are part of mapping identity and fails qualification if a valid source-closed bound is unavailable. Therefore the formula is not independently blocking at D2.

Stage C must not assume that a nominal tensor dimension alone establishes n. It must establish the resolved accumulation dtype/order/kernel model, coefficient-matrix identity, handling of coefficient construction/rounding including numpy.linalg.pinv on the inverse path, and any underflow/overflow/subnormal assumptions needed by the claimed bound. If those assumptions cannot be established for the resolved kernel, the structural relation fails closed.

### 7.11 Projection evaluator envelope

The n_P=36 cardinality is correct for the stated J_P=2 reference-side union-bound construction. Structural transfer correctness and evaluator arithmetic are conceptually separated in Candidate 6.

The evaluator envelope nevertheless inherits B2's maximum-envelope permissiveness and cannot rescue an incomplete/common-mode structural oracle.

### 7.12 Exact decisions versus stochastic scores

The rules are logically compatible: any exact governed decision mismatch overrides a stochastic numerical score that is inside its envelope.

The defect is completeness, not logical contradiction: exact booleans cannot substitute for continuous quantities that remain downstream scientific inputs. B1 addresses that omission.

### 7.13 Routine doctor

The routine doctor is correctly reduced to exact qualification authentication plus a cheap real forward/backward reachability/finiteness witness. It cannot re-estimate tolerance, widen the key, retry until pass, revive stale evidence, substitute descriptor/FPS evidence, or authorize backend switching. No blocker remains here.

### 7.14 D2/D3 boundary

Candidate 6 binds several concrete MACE/Torch/CUDA/CuEq/device/kernel identities. In this exact-realization qualification they are numerically material to floating semantics, evidence applicability, and currentness, so their presence is not by itself D3/D4 overreach.

D3 remains responsible for persistence, concurrency, packaging, and execution decomposition after D2 is accepted. No D3/D4 implementation is authorized by this Review.

## 8. Required workplan state after this Review

The workplan remains open.

Before another independent Review:

1. create a new immutable Candidate 7 or later identity; never mutate or reinterpret C6;
2. close B1 by adding a complete common-coordinate model-state/downstream continuous-consequence relation;
3. close B2 by replacing sample-maximum containment as the backend-equivalence definition and adding a reference-adequacy rule that cannot be made permissive by rare decision-stable self noise;
4. close B3 with one exact IEEE rank/ULP definition and boundary fixtures;
5. close B4 with an oracle independence contract that excludes shared inventory, correspondence, pair-enumeration, and projection-matrix semantic owners;
6. correct the candidate-side joint confidence derivation to use the process-level any-family exceedance event, unless Candidate 7 adopts a different predeclared stochastic relation;
7. retain full-horizon execution, exact-realization scoping, same-backend restart semantics, FP64 fail-closed narrowing, source/DATA6 e3nn narrowing, and routine-doctor restrictions unless a new independent defect is demonstrated;
8. do not run Candidate-6 Stage C and do not use any Candidate-6 CuEq outcome to tune Candidate 7; and
9. do not implement D3/D4 until a fresh independent D2 Review passes the new immutable candidate and the stakeholder ratifies that exact candidate.

## 9. Final disposition

**NO-PASS**

**SERIOUS CHALLENGE to accepted D1/D2 parent authority: NO**

Candidate 6 is not strong enough to proceed to Stage-C qualification. The failure remains at D2 and is repairable without changing accepted D1.
