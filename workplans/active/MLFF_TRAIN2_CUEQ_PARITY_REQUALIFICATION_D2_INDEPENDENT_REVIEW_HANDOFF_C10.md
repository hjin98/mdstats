---
kind: independent-review-handoff
protocol_version: 6.4.0
status: READY_FOR_FRESH_INDEPENDENT_REVIEW
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
candidate: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_10.md
immutable_candidate_commit: db2ed47e8c999cb61507803610c72c0fa7ffaaf7
immutable_candidate_blob: 7843a41172d25c231d4c589aebc0214ddec42bd1
accepted_parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_parent_d2_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
candidate9_review: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R6.md
stage_C_state: BLOCKED
D3_D4_state: BLOCKED
date: 2026-09-25
---

# Fresh independent D2 Review handoff — Candidate 10

Use the \`numerical-algorithm-design\` skill and perform a genuinely fresh independent Protocol-6.4 D2 Review.

## Immutable semantic target

Review Candidate 10 exactly at:

\`db2ed47e8c999cb61507803610c72c0fa7ffaaf7\`

Candidate file:

\`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_10.md\`

Expected Candidate-10 blob:

\`7843a41172d25c231d4c589aebc0214ddec42bd1\`

Do not substitute a later lifecycle branch head for the semantic Review target. Later descendants may be read only for lifecycle/evidence/workplan/handoff state.

Candidate 9 remains immutable historical state at:

\`d288d0f931b36e0304a91312915b9785e07dbe3c\`.

No Candidate-9 or Candidate-10 Stage-C result exists.

## Accepted parent

Reconstruct accepted parent independently from:

- accepted D1/D2 kernel: \`a759e81aa1b4c70c8fb513c569ddce57e99cbdb2\`;
- exact accepted D1/D2 source: \`a4824d28775164aa942fd29fa97ee0957eb87e6f\`.

Do not treat newer proposed canonical-path files as accepted parents.

## Required historical falsification context

Read at least:

- Candidate-4 Review R1;
- Candidate-5 Review R2;
- Candidate-6 Review R3;
- Candidate-7 Review R4;
- Candidate-8 Review R5;
- Candidate-9 Review R6;
- Candidate-10 repair record;
- Stage-A MH-1, order/process, and MPA-0 analyses;
- active workplan;
- materially applicable PEM FF-001, FF-002, SP-002, SP-003, SP-004; and
- pinned MACE 0.3.16 conversion sources where projection semantics are challenged.

Treat Stage-A evidence and PEM as evidence/design context only, never D2 authority.

## Candidate-10 repair thesis to falsify

Candidate 10 preserves all Candidate-9 surfaces that R6 passed and repairs only production/evaluator population transport.

The exact repair is:

1. \(\mathcal Q\) binds
   \[
   \mathcal W=(\mathcal W_{\rm pre},\mathcal W_R,\mathcal W_C);
   \]
2. \(\mathcal W_{\rm pre}\) produces the pre-assignment triplet state \(\Lambda_p\);
3. labels are assigned independently and uniformly over the six \(R1/R2/C\) permutations after \(\Lambda_p\) is fixed;
4. immediately before each child executes, the assigned backend-specific \(\mathcal W_R\) or \(\mathcal W_C\) independently renews/authenticates the complete child execution law;
5. for every admissible \(\lambda\) and assignment \(a\), the **joint** three-child law is
   \[
   P_R^{\rm prod}\otimes P_R^{\rm prod}\otimes P_C^{\rm prod},
   \]
   not merely three correct marginals;
6. prior sibling execution, launch slot, hidden shared entropy, cache/residency/thermal/global state, or qualification-only post-start interference may not alter that product law;
7. ordinary production CuEq must execute the same \(\mathcal W_C\) and belong to exactly \(P_C^{\rm prod}\);
8. \(q_{\rm cat}\) is inferred on exact production-equivalent pair populations, not the randomized assignment mixture;
9. the R5 assignment-marginal theorem remains separately responsible for \(\eta_{\rm NI}\);
10. evaluator qualification uses the same production/evaluation-equivalent child-law transport rule; and
11. failure to establish the law structurally fails closed; no post-hoc mixture correction, alternate estimator, or tolerance widening exists.

## Required falsification questions

### A. Lifecycle and parent reconstruction

1. Verify immutable Candidate-10 commit and blob exactly.
2. Verify lifecycle descendants do not mutate Candidate 10.
3. Verify no Candidate-10 Stage-C evidence exists.
4. Verify Candidate 9 remains immutable and no C9 outcome chose the C10 repair.
5. Reconstruct accepted parent D1/D2 and determine whether any finding rises upstream.

### B. Production-equivalent child law

6. Formalize \(P_R^{\rm prod}\) and \(P_C^{\rm prod}\): what exact arithmetic-relevant state/randomness/execution interval do they cover?
7. Verify they cover whole governed child execution, not only an initial snapshot.
8. Verify the exact conditional joint law is
   \[
   P_R^{\rm prod}\otimes P_R^{\rm prod}\otimes P_C^{\rm prod}
   \]
   for every \(\Lambda=\lambda\) and assignment \(a\).
9. Construct a hidden-common-entropy adversary where each child marginal is correct but \(R1,C\) remain coupled; Candidate 10 must reject it.
10. Construct prior-sibling cache/residency/thermal/autotuning/page-cache/global-state attacks.
11. Challenge worker/thread/daemon state, Torch/MACE/CuEq globals, persistent RNGs, CUDA graphs, compiler/kernel caches, allocator pools, power/clock state, and process-supervisor state.
12. Verify sibling overlap/concurrency is forbidden unless it is exactly the production concurrency law and transport is proved.
13. Verify backend-specific prewarm cannot create a qualification-only law.
14. Verify statistical stationarity/autocorrelation tests are falsification aids only and cannot establish transport or independence.

### C. R6 slot-mixture adversary

15. Reproduce the exact R6 construction with candidate slot risks \(0.20,0,0\), \(q_{\rm cat}=0.08\), uniform mixture \(0.066\overline6\), and production using the high-risk first-slot regime.
16. Verify Candidate 10 rejects the construction **before** aggregate materiality inference because slot-specific candidate laws violate D2.CUEQ10.DEF.015.
17. Attempt variants where only post-start state differs by slot despite identical start snapshots.
18. Attempt variants where production skips or changes \(\mathcal W_C\); the passing record must be inapplicable.
19. Verify no broader "fresh-start envelope" can substitute for exact \(P_C^{\rm prod}\).

### D. R5 theorem preservation

20. Re-formalize the six launch assignments and \(\tau\) swapping \(R2/C\).
21. Verify the null remains pre-assignment label-exchange invariance, never exchangeability conditional on realized assignment.
22. Reproduce \(h=(0,1,2)\) and strict-worse indicators \((1,0,0,0,0,1)\).
23. Verify shared \(R1\) does not require false independence.
24. Verify the new per-child product-law requirement does not accidentally condition away or invalidate the prospective assignment theorem.
25. Verify \(\eta_{\rm NI}\) remains a qualification-comparison proposition and does not become the owner of production tail risk.

### E. Materiality population and confidence

26. Verify
   \[
   q_R^\ast=\Pr_{R_1,R_2\sim P_R^{\rm prod}}[C^R=1]
   \]
   and
   \[
   q_C^\ast=\Pr_{R_1\sim P_R^{\rm prod},C\sim P_C^{\rm prod}}[C^C=1]
   \]
   are exactly the populations sampled by valid triplets.
27. Verify triplets are i.i.d. Bernoulli units only under the full joint-law/common-law applicability contract.
28. Re-derive one-sided Clopper-Pearson and four-way Bonferroni \(\alpha=0.0125\).
29. Re-derive zero-event
   \[
   Q=1-\alpha^{1/n}
   \]
   and the minimum-\(n\) formula.
30. Verify \(q_{\rm cat}=0\) remains non-executable for finite \(n\).
31. Verify \(0\le\eta_{\rm NI}\le q_{\rm cat}<0.10\) remains only a conservative admissibility restriction, not a theorem linking event families.
32. Verify no confidence statement claims zero tail probability.
33. Attempt favorable seed/permutation selection, failed-triplet deletion, redraw, retry-until-pass, and selective pooling.

### F. Failure/currentness semantics

34. Challenge startup failure, OOM, timeout, crash, nonfinite child, unsupported runtime, partial output and infrastructure abort.
35. Verify failure cannot become zero, discarded evidence, or same-key retry.
36. Verify changing \(\mathcal W_{\rm pre},\mathcal W_R,\mathcal W_C,P_R^{\rm prod},P_C^{\rm prod}\) stales the key.
37. Verify realized assignment sequence remains evidence identity, not semantic key identity.

### G. Projection evaluator transport

38. Verify evaluator child execution laws equal the exact real evaluator laws in every slot.
39. Reproduce an evaluator slot-mixture adversary analogous to R6.
40. Verify evaluator \(q_{\rm cat}\) is not inferred from a qualification-only mixture.
41. Verify evaluator agreement still cannot rescue structural inventory/correspondence/coefficient failure.

### H. Preserved Candidate-9 surfaces

42. Reverify exact \(E\) consumer closure and final completed-state evaluation.
43. Reverify held-out leakage prohibition.
44. Reverify every current \(\mathcal R_e\) against accepted parent source and fail closed if missing.
45. Reverify signed-zero/dtype-aware IEEE rank.
46. Reverify \(S_{\max}\) and exact unnormalized \(S_\Sigma\).
47. Reverify exact scientific-decision equality.
48. Reverify complete live/EMA and non-\`state_dict\` forward-affecting inventory including \`avg_num_neighbors\`.
49. Reverify projection-oracle semantic-owner independence.
50. Reconstruct pinned MACE 0.3.16 reduced-CG conversion and non-unique inverse fail-closed behavior.
51. Reverify independent \(A^\ast\), exact correctly-rounded production coefficient equality, and \(A^\ast=1,\widehat A=100\) adversary.
52. Reverify realized floating accumulation/rounding/subnormal/overflow assumptions fail closed when unproved.
53. Reverify same-backend restart only and no cross-backend restart.
54. Reverify source/DATA6 CuEq outside authority.
55. Reverify FP64 CuEq TRAIN2 unsupported/fail closed.
56. Reverify EVAL2 provider identity e3nn.
57. Reverify routine doctor currentness/reachability only.

### I. Historical regression and authority scope

58. Check every R1-R6 blocker for accidental regression.
59. Verify no historical D4 tolerance, Stage-A observation, current implementation behavior, or PEM record became D2 authority.
60. Verify Candidate 10 remains a bounded D2 overlay and does not take D3/D4 ownership.
61. Verify no semantic repair is hidden only in a lifecycle descendant after immutable C10.

## Disposition

Return exactly one substantive disposition:

- **PASS AS D2 CANDIDATE FAMILY FOR STAKEHOLDER INSTANCE RATIFICATION AND STAGE-C TESTING**, or
- **NO-PASS** with precise blocking defects and repair requirements.

Also state explicitly whether any finding rises to a **SERIOUS CHALLENGE** against accepted parent D1/D2 authority.

A PASS does not accept CuEq and does not authorize D3/D4. It means immutable Candidate 10 is adequate for stakeholder binding of one exact reviewed method instance before Stage C.

If blocking defects remain:

- update/reopen the existing workplan;
- preserve Candidate 10 as immutable historical state;
- any semantic repair becomes Candidate 11 or later;
- do not run Candidate-10 Stage C; and
- do not use Candidate-10 outcomes to tune its replacement.