---
kind: independent-review-handoff
protocol_version: 6.4.0
status: AWAITING_FRESH_INDEPENDENT_D2_REVIEW
workplan_id: MLFF-TRAIN2-CUEQ-PARITY-REQUALIFICATION
branch: design/mlff-train2-cueq-parity-requalification
accepted_D2_baseline: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_D2_source_target: a4824d28775164aa942fd29fa97ee0957eb87e6f
immutable_D2_candidate: cd4e0453d0a27ae01f7041c1c9d222fd9d71a0e9
D2_candidate_blob: 1ad1ee0374ce1644f72e9ab89121ea47110f35bd
stage_A_cross_family_basis: 24734c8113dfaeaba4ae32c2bb0b80f3c0c72e82
representation_corrupt_historical_target: 5d63350dd13929c27fa6c2204238f2f2e8f93cbd
highest_review_owner: D2
stage_C_state: BLOCKED_PENDING_FRESH_D2_REVIEW
D3_D4_state: BLOCKED_PENDING_D2_ACCEPTANCE
---

# Fresh independent D2 Review handoff — TRAIN2 CuEq acceleration equivalence

## 1. Immutable binding

Perform a genuinely fresh Protocol-6.4 numerical-method Review of immutable semantic candidate:

cd4e0453d0a27ae01f7041c1c9d222fd9d71a0e9

Canonical Candidate-4 blob:

1ad1ee0374ce1644f72e9ab89121ea47110f35bd

Review it against accepted-current D2 kernel:

a759e81aa1b4c70c8fb513c569ddce57e99cbdb2

and exact accepted D2 source target:

a4824d28775164aa942fd29fa97ee0957eb87e6f.

The current branch head after this handoff is only lifecycle coordination. Do **not** substitute a later mutable branch head for cd4e0453d0a27ae01f7041c1c9d222fd9d71a0e9 as the semantic Review target.

The earlier Candidate-4 commit 5d63350dd13929c27fa6c2204238f2f2e8f93cbd contained renderer-breaking escape corruption. It is historical only and must not be reviewed. The immutable target above is its representation-corrected, semantically unchanged successor.

## 2. Independence

Do not inherit the author-side PASS/readiness conclusions, thresholds, rationale, or workplan disposition.

Treat the following as evidence or claims to challenge, not authority:

- the Stage-A MH-1 and MPA-0 analyses;
- the B1-B10 author Challenge record;
- the assertion that descriptors/FPS should leave TRAIN2 admission;
- the proposed two-update transition horizon;
- the proposed centroid and variance budgets;
- the claim that the state-transfer mapping is a suitable common observation coordinate.

Reconstruct the accepted parent semantics and the proposed child relation independently.

If accepted D2 itself is inadequate, contradictory, or unable to protect the upstream scientific meaning, raise SERIOUS CHALLENGE rather than forcing Candidate 4 to conform to a defective parent.

## 3. Candidate surface under Review

Candidate 4 proposes one acceleration-equivalence family separated by semantic role:

1. source/DATA6 calculator inference;
2. TRAIN2 training-state transition; and
3. completed-state CuEq-to-portable-e3nn projection/EVAL2.

For TRAIN2 it proposes:

- fresh process as the independent experimental unit;
- four construction/execution-order cells;
- five fresh processes per cell, one discarded warm-up, and three retained observations;
- real loader-derived consecutive two-update windows, preserving accepted replay-first/target-second exposure semantics;
- mandatory starting-state physical energy/force/stress channels;
- update-induced portable-e3nn energy/force/stress displacements after update 1 and update 2;
- global and order-cell centroid bias under inherited dtype calculator precision constants, explicitly as a new proposed TRAIN2 use;
- candidate stochastic variance bounded by reference variance plus one fixed dtype-tolerance RMS-square budget;
- a coarse paired property-scale catastrophic guard;
- starting state S0 plus at least one nontrivial independent S1 state per claimed topology;
- transient-to-portable state-transfer mapping checked directly against the transient CuEq physical function;
- no descriptor/FPS hard gate for TRAIN2 when TRAIN2 does not consume descriptors;
- unchanged source/DATA6 calculator semantics;
- unchanged deployment-projection numerical values; and
- expensive qualification separated from routine doctor witnessing/currentness.

## 4. Mandatory Challenge Pass

Challenge at least the following.

### 4.1 Protected consequence and scope

1. Is the backend-specific TRAIN2 **state transition** the correct D2 protected consequence, or does accepted D1/D2 require a stronger or weaker relation?
2. Does comparing physical function changes after updates faithfully cover backend-specific forward/backward numerical consequences without overconstraining incidental parameter representation?
3. Is Candidate 4 accidentally trying to prove complete trajectory equivalence from a local operator check when downstream scientific acceptance permits stochastic trajectory differences?

### 4.2 Two-update horizon, optimizer state, and EMA

4. Is two updates genuinely sufficient to expose every stateful recurrence that can make e3nn and CuEq diverge?
5. Must EMA shadow state be observed as its own physical-function channel when EMA can control checkpoint/evaluation behavior, rather than only required to remain finite?
6. Can optimizer state differ materially after update 2 while live physical outputs still pass, creating latent later divergence?
7. Is the S0-plus-S1 construction adequate for the claimed reachable-state domain? In particular, what optimizer/EMA state must accompany S1?
8. Must state snapshots be captured non-invasively and measured only after the two-update sequence so state-transfer/evaluation cannot perturb update 2?

If these questions require a bounded paired adaptation or another trajectory-level oracle, say so explicitly rather than merely increasing the local update count without justification.

### 4.3 Stochastic semantics and finite-sample stability

9. Is fresh process the correct independent unit?
10. Is the four-cell construction/execution-order factorization sufficient, and are additional order/state factors omitted?
11. Is V_C <= V_R + T^2 a defensible candidate-independent stochastic non-degradation budget?
12. Are global plus cell-conditioned first/second-moment guards and the gross paired guard sufficient to reject materially different distributions?
13. Does the 5-process-per-cell / 3-retained design have adequate numerical meaning for the **new transition observable**, given that this cardinality originated in the Stage-A forward diagnostic?
14. Does qualification require multiple independently executed complete 20-process ensembles, or another explicit repeatability rule, to prevent pass/fail classification instability? A rerun-until-pass rule is forbidden.

### 4.4 Persistent-bias tolerance

15. Candidate 4 reuses FP32 1e-5/1e-6 and FP64 1e-10/1e-12 calculator precision constants on **training-transition centroids**. Is that transfer dimensionally and numerically justified?
16. Does applying relative tolerance to near-zero update-induced displacement have the intended conditioning, or does absolute tolerance dominate in a way that can admit a material update error?
17. Are energy/atom, force, and stress normalized consistently enough that the separate componentwise envelopes preserve their distinct physical meanings?

### 4.5 Real TRAIN2 exposure

18. Does the loader-derived window rule execute the real semantic owner rather than reconstructing a lookalike batch harness?
19. Does the deterministic coverage scan preserve accepted replay-first/target-second pre-shuffle order, seed, shuffle/sampler, batch size, no-duplication, and drop-last semantics?
20. Can selecting the smallest metadata-covering windows bias the qualification away from difficult numerical regimes even without inspecting CuEq outcomes?
21. Should additional predeclared exposure regimes or boundary batches be mandatory?

### 4.6 State-transfer measurement oracle and common-mode risk

22. Can the transient-to-portable mapping hide a training-state difference because it shares implementation machinery with deployment projection?
23. Is direct transient-CuEq versus mapped-e3nn physical parity on every measured state a sufficiently independent oracle?
24. Does the additional pinned-MACE conversion/state-value differential actually reduce common-mode risk, or merely repeat the same transfer implementation?
25. Is the mapping demonstrably non-mutating with respect to the live training state?
26. Does removing descriptor/FPS from TRAIN2 while retaining it for source/DATA6 preserve every actual protected consumer consequence?

### 4.7 Catastrophic guard

27. Is the 0.01 property robust-loss transition scale a justified *catastrophic backend-discrepancy* guard, or is Candidate 4 importing a training-residual scale into an unrelated numerical role?
28. Is that guard necessary once variance and centroid rules are present? If retained, does it reject the right rare failures without becoming an alternate ordinary tolerance?

### 4.8 Model-state, family, dtype, and runtime applicability

29. Is one nontrivial S1 per topology enough to support the claimed state domain?
30. Does the evidence need separate treatment for MPA-0/default versus MH-1/omat_pbe beyond exact applicability binding?
31. Is FP64 TRAIN2 honestly handled: either operator-qualified under the same consequence or explicitly unsupported?
32. Are MACE/Torch/CUDA/CuEq source/runtime, precision flags, device class, objective/exposure, model topology, state class, and method digest sufficient currentness dimensions?

### 4.9 Adjacent relation source closure

33. Are source/DATA6 FP32 and FP64 calculator relations genuinely accepted/source-closed siblings, or is Candidate 4 inadvertently promoting historical D4 behavior into D2 authority?
34. Is the trained-state projection/EVAL2 relation source-closed without changing its numerical meaning?
35. Does EVAL2 correctly identify the actual portable e3nn numerical forward after CuEq checkpoint authentication/projection?

### 4.10 Routine doctor versus qualification

36. Can a cheaper routine doctor witness safely authenticate a prior qualification without silently broadening its applicability?
37. Are stale qualifications guaranteed to fail closed when runtime, model state/topology, objective/exposure, dtype, or method identity changes?
38. Does the proposed split eliminate obsolete Rev86 authority rather than stack another registry/reducer on top?

## 5. Counterexamples the Review should reason through

At minimum attempt to construct a semantically wrong candidate that would still pass if the proposed oracle is weak:

- constant small backend bias repeated coherently across updates;
- equal means but inflated candidate variance;
- opposite cell biases that cancel globally;
- rare large single-component error;
- update-2-only error after optimizer recurrence is populated;
- EMA-only drift;
- optimizer-state drift not yet visible in live parameters;
- target-first or hand-built batch substituted for accepted replay-first exposure;
- state-transfer mapping that drops or misroutes one learned tensor;
- mapping that mutates the live CuEq training state;
- descriptor-only coordinate drift with preserved TRAIN2 physical transition;
- source/DATA6 descriptor drift that changes FPS selection;
- zero-reference-variance regime;
- near-zero update displacement dominated by absolute tolerance;
- stale qualification reused after a material runtime/source change; and
- S1 that is formally different but does not represent a materially different reachable state.

## 6. Evidence boundaries

Stage-A target-host evidence is method-design evidence only. It does **not** contain Candidate-4 two-update training transitions and cannot by itself pass Candidate 4.

Do not run Stage-C acceptance evidence first and then tune Candidate 4 to those outcomes.

A PASS review means the **method is coherent enough to test**, not that CuEq is qualified. Fresh Stage-C target-host evidence remains mandatory after Review.

No D3/D4 product implementation or threshold change is authorized before D2 acceptance.

## 7. Required Review output

Return:

- PASS or NO-PASS for immutable Candidate 4;
- SERIOUS CHALLENGE state and earliest semantic owner if any;
- blocking findings only when they can change correctness/acceptance;
- precise repair instructions for every blocker;
- explicit disposition of FP32, FP64, source/DATA6, TRAIN2, and projection/EVAL2 scope;
- explicit assessment of whether two-update/S0-S1 evidence is sufficient or must be strengthened;
- explicit assessment of qualification replication/stability semantics; and
- dependency/evidence impact if the candidate changes.

Do not mutate cd4e0453d0a27ae01f7041c1c9d222fd9d71a0e9 and continue calling it the same reviewed candidate. Any semantic repair must produce a new candidate identity/immutable target.

Even after Review PASS, stakeholder ratification and fresh Stage-C evidence are still required before D2 acceptance and D3/D4 implementation.
