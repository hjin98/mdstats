---
kind: abstraction-concretization-change-plan
protocol_version: 6.4.0
status: active-serious-challenge
workplan_id: MLFF-TRAIN2-CUEQ-PARITY-REQUALIFICATION
created_date: 2026-09-24
revision: 26
reviewed_date: 2026-09-25
workplan_review_status: CANDIDATE_9_INDEPENDENT_NO_PASS_CANDIDATE_10_REQUIRED
workplan_review_basis: d288d0f931b36e0304a91312915b9785e07dbe3c
accepted_d1_d2_baseline: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_d1_d2_source_target: a4824d28775164aa942fd29fa97ee0957eb87e6f
branch: design/mlff-train2-cueq-parity-requalification
basis_commit: af89c30ca5304c4dd71ff82b779db973ce0006f8
highest_potentially_affected_domain: D2
d1_change_expected: false
human_ratification_required_for_d2_mutation: true
current_generated_source_backend: e3nn
current_generated_train2_backend: cueq
repair_safe_source_backend: e3nn
repair_safe_train2_backend: e3nn
---

# MLFF TRAIN2 CuEq FP32 backend-parity requalification — D2 -> D3/D4 workplan

## 0. Disposition and Serious Challenge

**OPEN — SERIOUS CHALLENGE to the current executable TRAIN2 FP32 backend-equivalence rule, including its missing accepted-D2 source closure and its numerical adequacy.**

A real target-host MACE-MH-1 / `omat_pbe` doctor realization on an NVIDIA RTX 3090 passed dependency, selected-head, CUDA, resource, and execution-capability checks but failed the authorizing pure-CuEq TRAIN2 FP32 noise-normalized parity gate.

The observed failure is not sufficient evidence that CuEq is scientifically or numerically inadmissible. It is evidence that the current executable equivalence rule may be inadequately parameterized for the regime it claims to govern:

- energy cross maximum: `7.629e-7 <= 1e-6`;
- stress cross maximum: `7.213e-8 <= 1e-6`;
- descriptor cross maximum: `2.241e-6 > 1e-6`;
- e3nn self descriptor maximum: `1.907e-6`;
- CuEq self descriptor maximum: `1.812e-6`;
- force RMSE p99 ratio: `1.153 <= 1.25`;
- force p99 p99-ratio: `1.266 > 1.25`;
- force p99.9 p99-ratio: `1.270 > 1.25`;
- force cross maximum: `2.623e-6 <= 2.861e-6` active catastrophic-tail limit;
- no compared force component exceeded `1e-5`;
- cross deterministic selection identity: `100/100`;
- e3nn self selection identity: `45/45`;
- CuEq self selection identity: `45/45`.

The strongest immediate **adequacy counterexample candidate** is the descriptor channel: the current absolute cross-backend ceiling is smaller than the maximum observed same-backend FP32 descriptor variability on both backends in this target-host realization. That fact alone is not a mathematical contradiction—an independently justified cross-backend bound could in principle be tighter than same-backend extrema—but, combined with the policy's MPA-0-only calibration history, preserved hard selection outcomes, and absence of a current cross-family D2 derivation, it is sufficient to challenge transportability and numerical justification.

This review also confirmed an authority-provenance defect that must be resolved before changing any tolerance. The accepted Protocol-6.4 D2 kernel is `a759e81...`, importing exact source `a4824d2...`; it states that backend-observed discrepancy or an unlisted tolerance cannot create a new numerical-equivalence relation. Direct inspection of the exact accepted source finds no CuEq-specific relation and no FP32 parity rule. The Rev86 CuEq parity document is now classified by the current D4 specification index as historical/backend-qualification material rather than a current semantic owner. Therefore the current CuEq acceleration-equivalence family is **not source-closed as accepted D2 authority under the current Protocol-6.4 kernel**. The immediate adequacy challenge is specific to the TRAIN2 FP32 doctor relation, but the same formalization omission also covers the current source-side inference relation, FP64 CuEq relations, and the trained-state CuEq -> portable-e3nn projection/evaluation relation used after checkpoint authentication. This cycle must source-close the complete supported acceleration-equivalence family by role, dtype, and model-state applicability. Numerical changes outside the challenged TRAIN2 FP32 member are not authorized unless those siblings are independently falsified.

Stage-A closure on the same target host now adds fresh MPA-0 evidence under the frozen 20-process counterbalanced design. The cross-family result strengthens the challenge rather than suggesting a larger threshold: absolute FP32 discrepancy changes by roughly a factor of 5-6 between MH-1 and MPA-0 while the normalized stochastic decomposition remains similar, and MPA-0 ordinary self-repeatability also crosses the Rev86 fixed `1e-6` energy floor.

Stage-B protected-consequence analysis then exposed a second, more fundamental adequacy defect. Every current TRAIN2 admission path in `acceleration.py` judges **calculator forward observables**. FP32 Rev86 adds repeated E/F/stress/descriptor/FPS statistics; FP64 uses the one-shot calculator relation. Neither path exercises the optimizer-consumed parameter gradient produced by the backend-specific training forward/backward graph. A forward-only calculator record therefore cannot, by itself, establish that `run_train` under e3nn and pure CuEq realize the same training operator. This is an operator-domain gap, not evidence that CuEq gradients are wrong.

Consequently the changed D2 member is no longer described as “choose a better FP32 forward threshold.” The repair must source-close the TRAIN2 **training-operator** relation. FP32 remains the observed/falsified numerical regime. FP64 forward tolerances are not relaxed, but FP64 CuEq TRAIN2 may not be promoted as a source-closed training-equivalence member solely from its existing forward-only witness; Gate C must either qualify the same operator consequence for FP64 or explicitly narrow current CuEq TRAIN2 support to the qualified dtype.

The current runtime behavior remains the fail-closed baseline until a replacement relation is accepted. D3/D4 MUST continue to fail closed under the existing policy in the meantime. No threshold widening, retry-until-pass behavior, silent e3nn fallback, or MH-1-specific bypass is authorized.

Operationally, the accepted safe route for a run that must avoid the challenged relation is the existing explicit `e3nn` TRAIN2 override. The generated TRAIN2 backend remains `cueq`, but it is fail-closed: when its doctor parity gate fails, the campaign cannot proceed under that CuEq realization and no silent e3nn fallback is permitted.

## 1. Outcome and authority

### Protected outcome

Determine and freeze a scientifically defensible FP32 TRAIN2 backend-equivalence method, while formally source-closing the adjacent current CuEq acceleration-equivalence family, such that:

1. distinguishes systematic e3nn/CuEq disagreement from ordinary realization-level FP32 variability;
2. applies coherently across every foundation/model family and head that the authority claims to cover;
3. preserves hard fail-closed behavior for genuine numerical disagreement, non-finite outputs, selection disagreement, or unsupported runtime realization;
4. does not tune acceptance to admit a particular observed run;
5. remains strong enough to protect all downstream scientific decisions that depend on TRAIN2 execution equivalence.

### Highest potentially affected semantic domain

`D2 — numerical algorithm/method`.

This is not initially a D4 doctor metric bug. The current doctor correctly realizes the **current executable D4 gate**, but that gate is not source-closed as accepted D2 authority. D3/D4 numerical-threshold modification is downstream work only after the D2 relation is accepted, unless independent evidence first proves that the observed metrics themselves are incorrectly computed.

### Current normative/evidence owners

Repository work starts from:

`hjin98/mdstats@af89c30ca5304c4dd71ff82b779db973ce0006f8`

but **repository head is not synonymous with accepted authority**.

The exact accepted Protocol-6.4 parent authority at workplan opening is:

- D1 accepted kernel: `hjin98/mdstats@a759e81aa1b4c70c8fb513c569ddce57e99cbdb2:docs/methods/mlff_scientific_method.md`;
- D2 accepted kernel: `hjin98/mdstats@a759e81aa1b4c70c8fb513c569ddce57e99cbdb2:docs/methods/mlff_numerical_algorithmic_method.md`;
- exact stakeholder-ratified D1/D2 source target imported by those kernels: `a4824d28775164aa942fd29fa97ee0957eb87e6f`.

The accepted D2 equivalence registry at `a759e81...` is a governing parent: backend execution is noninterfering only under an accepted relation, and backend-observed discrepancy, performance, generic closeness, or an unlisted tolerance cannot mint one.

The files currently present on `main@af89c30...` under `docs/methods/mlff_{scientific,numerical_algorithmic}_method.md` carry **proposed renewal** lifecycle state from another workplan. They MUST NOT be treated as accepted parents or edited in place by this cycle merely because they occupy canonical paths.

The current post-formalization D4 specification index `docs/specs/training_data/README.md` explicitly states that backend qualification reports, hotfix notes, and parity diagnostics are not current semantic owners. Therefore:

- `docs/specs/training_data/mlff_cueq_train_noise_normalized_parity_spec.md` is historical/qualification evidence and a representation of Rev86 behavior; the accepted D2 source at `a4824d2...` contains no CuEq/FP32 parity relation, so Rev86 cannot be treated as current D2 authority by path or runtime use;
- `mdstats/training_data/acceleration.py` and `mdstats/training_data/_campaign_cli_core.py` are executable D4 realizations, not owners permitted to invent numerical equivalence;
- any replacement relation must first exist as a bounded D2 candidate/overlay against the exact accepted parent.

### Authority-composition rule

This cycle SHALL NOT overwrite an unrelated unratified D1/D2 proposal. The D2 parity candidate must be represented as a bounded overlay/change set whose exact parent is recorded.

Immediately before independent D2 Review and again before promotion:

1. resolve the workflow-selected accepted D1 and D2 project state, not merely branch `main`;
2. compare it with the plan's pinned `a759e81...` basis;
3. if another D1/D2 renewal has become accepted, rebase/recompose this parity overlay semantically onto that exact accepted target;
4. review all overlapping definitions, equivalence-registry clauses, failure semantics, parameter ledgers, and dependent handoffs;
5. obtain fresh independent Review for the composed immutable candidate when overlap is material.

Two unratified proposals may never become authority by textual merge or newest-file precedence. D1 remains unchanged unless the parity investigation proves that the scientific meaning/validity regime of execution equivalence itself must change.

### Executable and historical evidence owners

Relevant historical qualification/specification evidence includes:

- `docs/specs/training_data/mlff_cueq_train_default1_hotfix_spec.md`;
- `docs/specs/training_data/mlff_cueq_train_default1_fp32_ceiling_hotfix_spec.md`;
- `docs/specs/training_data/mlff_cueq_phase1_training_qualification_spec.md`;
- `docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV86.md`;
- `release/MLFF_CUEQ_DEFAULT1_HF1_QUALIFICATION_0.20.194a0.json`;
- MPA-0 DIAG3 evidence cited by the current noise-normalized parity spec;
- the new MH-1 target-host doctor realization supplied by the stakeholder on 2026-09-24, which must be captured durably before it is used as acceptance evidence.

### Required human state

Any material replacement or first formal promotion of the TRAIN2 FP32 equivalence relation requires:

`accepted parent -> proposed bounded D2 overlay -> fresh independent D2 falsification -> stakeholder ratification of the exact reviewed candidate -> D3/D4 handoff`.

If Stage A instead demonstrates a pure D4 defect under an already accepted relation, route that defect separately and do not manufacture a D2 change.

The implementation agent cannot self-authorize a looser equivalence criterion, and a passing target-host run cannot ratify its own acceptance rule.

## 2. Governing contract

### 2.1 Invariants

The repair MUST preserve all of the following:

1. **Backend equivalence is numerical authority, not performance policy.** CuEq speedup cannot rescue a failed equivalence criterion.
2. **No scientific-threshold leakage.** TRAIN2 backend parity tolerances cannot become training convergence, replay-retention, CV, EVAL2, deployment, or physical-validation tolerances.
3. **Fail closed.** Non-finite outputs, unsupported realization, invalid selected-head identity, or a failed accepted parity predicate remain hard failures.
4. **No silent fallback.** Explicitly requested CuEq may not silently execute TRAIN2 under e3nn.
5. **Selection identity remains hard.** Deterministic selection fingerprints must agree wherever selection is a governed parity observable.
6. **Reference/candidate identity remains exact.** e3nn and pure-CuEq probes must bind the same selected-head model state, structures, dtype, descriptor definition, FPS procedure, and all other numerically material inputs except the deliberate backend realization.
7. **FP32 is the observed numerical challenge; TRAIN2 operator scope is dtype-complete.** This cycle must not relax the existing FP64 calculator tolerances. However, protected-consequence review has shown that forward-only evidence cannot establish a training operator for either dtype. FP64 CuEq TRAIN2 therefore requires operator source closure/qualification before it can remain a supported training-equivalence member; otherwise support must be narrowed explicitly rather than silently inheriting the old forward-only gate.
8. **No family-specific exception without D2 justification.** Do not add an `if MH-1` tolerance branch merely because this realization failed.
9. **No auto-calibration from the candidate being judged.** A candidate run may supply repeatability evidence under a predeclared method, but its observed cross discrepancy cannot directly set its own acceptance bound.
9A. **Adjacent parity relations are formalization-frozen.** Source-side FP32/FP64 CuEq relations and the trained-state CuEq -> portable-e3nn projection/EVAL2 relation must be brought under explicit D2 source closure because the accepted kernel omitted the acceleration-equivalence surface, but their numerical tolerances/semantics are not changed by this TRAIN2 doctor incident absent separate falsification evidence.
10. **Uncertainty must be represented honestly.** Repeated-pair statistics built from a small number of repeated evaluations are dependent observations; all-pairs cardinality must not be interpreted as an independent-sample count.
11. **Accepted currentness is explicit.** Any changed parity-policy identity must invalidate/remap dependent preflight, handoff, qualification, cache, and provenance records exactly where they bind the old policy digest.
12. **Existing explicit e3nn TRAIN2 path remains admissible.** The current generated campaign split is source/DATA6/evaluation `e3nn` and TRAIN2 `cueq`. This repair must not silently rewrite that accepted generated policy merely to avoid a challenged CuEq gate. A production run that must proceed without the challenged CuEq relation may explicitly set `training_backend = "e3nn"`; that operational override is not a generated-default change.
13. **Authority isolation is hard.** Unrelated proposed D1/D2/D3 renewal artifacts on the repository head are evidence/candidate state only and cannot become parents by path precedence.
13A. **The missing D2 relation is a confirmed closure obligation.** The accepted D2 source does not define CuEq/FP32 parity. D4's Rev86 rule may remain the conservative executable guard during repair, but it cannot be cited as accepted numerical authority until this cycle supplies the source-closed D2 relation through the normal acceptance process.
14. **Current doctor admission and CUEQ-PHASE1 have distinct scopes, and current doctor evidence is not yet an adequate training-operator proof.** Rev60/Rev61 made the selected-head doctor surface the current fail-closed realization admission path for generated TRAIN2 `cueq`, while CUEQ-PHASE1 remains valuable paired-training/FINAL-GPU1 evidence. Stage-B protected-consequence analysis now establishes that the doctor's forward E/F/stress/descriptor/FPS witness is insufficient to prove the backend-specific backward/gradient operator. Repair that admission proposition directly; do not falsely make historical phase-1 completion a blanket prerequisite for every current realization, and do not claim a repaired doctor relation retroactively makes the historical phase-1 record pass.
15. **Every parity channel needs a protected consequence.** No internal quantity remains a hard gate merely because it was historically measured; D2 must state which scientific/numerical downstream invariant it protects. In particular, invariant descriptors/FPS are not TRAIN2 training inputs and therefore cannot remain a TRAIN2 hard gate merely by inheritance from source/DATA6 calculator qualification. The backend-specific loss/gradient computation is a protected TRAIN2 consequence and must be covered through the governed training-state transition; finite loss/gradient execution remains mandatory, while raw parameter-gradient coordinate equality is not itself the equivalence relation.
16. **Channel dimensions/scales are explicit.** Energy/atom, force, stress, and latent descriptors have different units/scales. A shared numerical absolute ceiling across unlike channels is inadmissible without an explicit normalization/error derivation.
17. **Qualification currentness is authenticated.** Neither a source-side nor TRAIN2 stored CuEq realization can remain current solely because backend/device/dtype/checkpoint match; consequential reuse must bind the currently accepted parity-policy/method identity and applicable runtime/model evidence.
18. **Historical records are immutable but non-self-authorizing.** An old record carrying `passed=true` remains historical evidence after a policy/method change and cannot authorize current CuEq use without the accepted remap/requalification rule.
19. **No adaptive retry.** The number/order of independent target-host realizations used for an acceptance decision must be frozen before their outcomes are inspected; pass/fail instability is evidence against a stable authorizing rule, not permission to rerun until pass.

### 2.2 Cycle-scoped decisions

For this repair cycle:

- treat the Rev86 `1e-6/1.25` relation as the **current executable fail-closed D4 rule** while this cycle supplies the already-confirmed missing accepted-D2 source closure;

- use the real MH-1 target-host observation as a falsification input, not as the new tolerance source;
- compare at least the historically relevant MPA-0/default and MH-1/omat_pbe regimes before claiming a generic replacement policy;
- prefer one coherent equivalence construction over stacked legacy absolute floors plus model-family exceptions;
- keep the current warm-up and repeated-evaluation machinery only if its statistical role is independently justified; its current implementation identity is not protected;
- use existing CampaignStore doctor/parity/repeatability records as the first evidence source; do not add a second capture registry;
- treat CUEQ-PHASE1 and FINAL-GPU1 as adjacent historical/release-qualification evidence owners whose claims must remain distinct from the current doctor admission rule; do not collapse them in either direction.

### 2.3 Delegated space

D2 may choose, subject to evidence, among forms such as:

- absolute error envelopes justified independently from precision/error semantics;
- self-noise-normalized cross-backend statistics;
- paired or hierarchical repeatability models;
- robust distributional comparisons;
- a hybrid criterion separating stable and variable channels.

No particular estimator, quantile, repeat count, ratio, or constant is pre-authorized by this workplan.

D3/D4 remain free to simplify or replace the present diagnostic machinery if the accepted D2 method can be realized more directly.

### 2.4 Non-goals

This cycle does not:

- change MACE training objectives, epochs, optimizer semantics, replay exposure, CV thresholds, EVAL2 ranking, or publication policy;
- authorize CuEq inference for source/DATA6 merely because TRAIN2 CuEq is reconsidered;
- re-open GPU scheduler/resource policy unless new evidence independently implicates it;
- revise MACE source-compatibility qualification;
- alter FP64 parity;
- redesign final model publication/P7 deployment;
- add a generic plugin or wrapper system around parity checks.

## 3. Adequacy and affected surface

### 3.1 Upstream meaning to preserve

The D2 question is:

> When may e3nn and pure-CuEq TRAIN2 execution be treated as the same numerical **training operator** for the scientific method, despite backend- and run-level floating-point variability?

For FP32 this includes the challenged physical-output arithmetic **and** the optimizer-consumed backward gradient. For any other dtype retained as supported CuEq TRAIN2, the same protected training-operator consequence must be source-closed even when its existing forward calculator tolerance remains numerically unchanged.

The replacement must discriminate:

`same numerical method under finite-precision execution variability`

from:

`materially different numerical realization capable of changing governed decisions`.

### 3.2 Material dependent surface

At minimum inspect and close:

- accepted D1/D2 kernels and exact imported source target at `a759e81.../a4824d2...`, plus any accepted successor resolved before promotion;
- current acceleration-equivalence family by semantic role and dtype: source-foundation inference/DATA6/pseudolabel execution where the source backend is consumed; selected-head TRAIN2 starting-realization admission; and trained-state transient-CuEq -> portable-e3nn projection/EVAL2 equivalence, with only the TRAIN2 FP32 doctor criterion numerically challenged by this incident;
- the unrelated proposed D1/D2 renewal currently occupying canonical paths on `main@af89c30...`, for composition/conflict only;
- `docs/specs/training_data/README.md` authority classification;
- historical `docs/specs/training_data/mlff_cueq_train_noise_normalized_parity_spec.md`, Rev83-86 notes, CUEQ-DEFAULT1/HF1/HF2 evidence, and DIAG3 records;
- `mdstats/training_data/acceleration.py`;
- doctor/currentness code in `mdstats/training_data/_campaign_cli_core.py`;
- optimizer/training identity owners that bind `acceleration_realization_digest`, including `mdstats/training_data/protocol.py`, post-selection runtime identities, and target-size execution identities where still current;
- `mdstats/training_data/target_size_execution/evaluation.py::authenticate_train2_checkpoint_provider`, which authenticates transient CuEq state and projects it through the dependency-native owner into the portable e3nn EVAL2 provider;
- `mdstats/training_data/campaign_post_selection_runtime.py::_checkpoint_provider_realization`, because current CuEq-trained EVAL2 forwards use the projected portable e3nn provider while this measurement-identity helper currently records the TRAIN2 backend;
- `tests/test_mlff_p5_train2_eval2_cueq_realization_parity.py` and the accepted TRAIN2->EVAL2 recurrence-repair evidence, which provide bounded trained-state/projection evidence but are not themselves D2 authority;
- `mdstats/training_data/cueq_phase1.py`, its tool/spec/evidence, and PERF-CERT1 prerequisites;
- `mdstats/training_data/final_gpu1.py` and `tools/run_mlff_final_gpu_qualification.py`;
- FINAL-GPU1 preflight/handoff policy-digest bindings and release-pinned workstation runbooks;
- parity/repeatability/policy/realization record schemas and serializers;
- CampaignStore stage/currentness admission so a pre-change doctor pass cannot survive an authority-policy change;
- focused CuEq parity tests, especially `tests/test_mlff_cueq_train_noise_normalized_parity.py`, DIAG3 tests, default1 tests, FINAL-GPU1 tests, and specification tests;
- MH-1 campaign-default tests to ensure the current generated phase split remains source/DATA6/evaluation `e3nn` and TRAIN2 `cueq`;
- frozen release/audit records only as historical evidence; never rewrite them to look current;
- current D3 architecture/dependency documentation and semantic-evolution notes if D2 authority changes.

### 3.3 Unaffected siblings to preserve

Unless new evidence contradicts them:

- CUEQ-PHASE1 paired-training scientific qualification semantics;
- TRAIN2/EVAL2 model-architecture authentication;
- production scheduler/resource budgeting;
- replay-retention and checkpoint-admissibility method;
- final-production publication and P7 deployment ownership.

The **numerical values** of the existing source-side FP32/FP64 and trained-state projection parity checks are presumed unchanged unless separately falsified, but they are not listed as unaffected authorities because the same accepted-D2 source-closure omission applies to them. Include their exact propositions/applicability in the D2 acceleration-equivalence family formalization without using the TRAIN2 doctor failure as a reason to relax them.

“Unaffected” means semantically unaffected, not automatically reusable evidence. A shared runtime/source/policy digest may still make an evidence record stale-dependent; perform the explicit impact projection rather than either invalidating everything or reusing everything.

### 3.4 Project Engineering Memory / Historical Applicability Set

Effective memory basis at plan opening is the accepted `PROJECT-ENGINEERING-MEMORY.md` on `main@af89c30...`, whose accepted-base metadata is itself partial and historically reconciled through `4eabe2ae...` plus the later final-publication candidate overlay.

Materially applicable current lessons:

- **SP-002**: preserve fail-closed authenticated identity/state boundaries;
- **SP-004**: real-owner and target-host qualification can expose defects missed by mocks/control-plane checks;
- TRAIN2/EVAL2 CuEq architecture history: do not confuse backend-parity failure with model-construction/architecture drift without independently checking exact realization identity;
- accepted recurrence-repair history at the TRAIN2 -> EVAL2 boundary: authenticate checkpoint state in the true transient CuEq realization, then use dependency-native state transfer into the canonical portable e3nn shell before EVAL2; preserve this representation split and its fail-closed architecture guards.

PEM coverage is partial. Absence of a specific historical parity family is not evidence that no relevant prior episode exists. Perform a bounded history search over CuEq/FP32 parity, selected-head MH-1, MPA-0, DIAG3, CUEQ-DEFAULT1, CUEQ-REPEAT1, CUEQ-PHASE1, PERF-CERT1, and FINAL-GPU1 before freezing a replacement criterion.

### 3.5 Qualification hierarchy and claim boundary

The workplan SHALL preserve the distinction among:

1. **runtime/capability identity** — CUEQ-DEP1 and MACE/Torch/CUDA/source compatibility;
2. **current campaign admission** — the selected-head doctor surface currently authorizes a specific CuEq TRAIN2 realization fail-closed, including the generated TRAIN2 `cueq` path, but its existing forward-only parity/repeatability witness is under adequacy challenge because it does not exercise the backend-specific training gradient;
3. **historical/paired training qualification evidence** — CUEQ-PHASE1 short and representative full e3nn-vs-CuEq trajectories with hard-decision preservation;
4. **release/end-to-end certification** — PERF-CERT1/FINAL-GPU1 where applicable.

The authority evolution matters. CONFIG1 established the canonical MH-1/`omat_pbe` foundation and source-side `e3nn` policy. CUEQ-PHASE1 then supplied a separate paired-training qualification contract. Revision 60 (`CUEQ-DEFAULT1`) was the later explicit stakeholder/project policy change that phase-separated the campaign and made TRAIN2 `cueq` the generated training backend while preserving source/DATA6/evaluation `e3nn` and leaving the old CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 records immutable. Current generator/tests still protect that split.

Therefore:

- do not require a positive historical CUEQ-PHASE1 record as an invented prerequisite for every current CuEq TRAIN2 realization;
- do not interpret a repaired doctor parity pass as retroactively making CUEQ-PHASE1/FINAL-GPU1 pass;
- when this work affects a release qualification that explicitly includes those gates, reconcile them under their own contracts;
- keep generated TRAIN2 policy, doctor realization admission, and explicit e3nn override as separate claims.

The D2 candidate must explicitly state the proposition proved by the instantaneous parity gate: bounded numerical admission of the exact selected-head/runtime CuEq realization under current campaign policy. CUEQ-PHASE1 remains useful stronger evidence about multi-epoch trajectory behavior and a falsification source, but it is not silently promoted into the current campaign admission owner.

### 3.6 Model-state and EVAL2 representation boundary

The accepted TRAIN2 -> EVAL2 recurrence repair establishes a two-representation checkpoint path:

```text
authenticated TRAIN2 checkpoint state
  -> reconstruct/authenticate transient training realization (CuEq when configured)
  -> load exact live/EMA state
  -> dependency-native CuEq -> e3nn state transfer
  -> canonical portable e3nn provider
  -> EVAL2 numerical forward
```

The current doctor parity witness is the selected-head **starting checkpoint**. That witness does not, by itself, prove a numerical statement for every optimizer-reachable trained parameter state. Stage B must therefore make one of these source-closed claims explicit and falsifiable:

- the accepted backend relation is an operator/implementation relation whose validity domain is uniform over a defined family of compatible model states/architectures, with evidence adequate to support that generalization; or
- the relation is witness/state scoped, in which case downstream state domains requiring separate equivalence must name and qualify their own bounded relation.

The existing CUDA recurrence test supplies useful evidence by perturbing trained CuEq parameters, projecting them through pinned MACE's native conversion, and checking portable-vs-CuEq predictions. It is evidence to challenge/reuse, not D2 authority and not proof that the Rev86 FP32 doctor statistic transports to all trained states.

A separate D3/D4 defect is confirmed on this boundary. `authenticate_post_selection_provider()` returns the projected **portable e3nn provider** for CuEq-trained checkpoints, but `_checkpoint_provider_realization()` currently records `context.method_policies.acceleration_backend` (normally `cueq`) in `EvaluationMeasurementIdentity`. Measurement identity must describe the numerically material forward realization, not the transient training representation from which state was authenticated.

Repair this through the existing provider-realization/measurement-identity owner. Do not weaken transient-CuEq checkpoint authentication. Correcting the forward-backend identity from mislabeled `cueq` to actual `e3nn` must stale/recompute affected EVAL2 measurements/assessments through existing content-addressed identity; it must **not** force retraining of otherwise authenticated TRAIN2 roots merely because an assessment-side representation label was wrong.

## 4. Evidence and falsification

### 4.1 Reverse-semantic verification question

For every proposed criterion `Q`:

> Could `Q` pass a backend pair whose systematic numerical difference is materially larger than ordinary same-backend FP32 variability or capable of changing a governed selection/scientific decision?

And conversely:

> Could `Q` reject two realizations whose observed difference is statistically indistinguishable from the same-backend variability that `Q` already accepts?

Both false-positive and false-negative behavior matter.

### 4.2 Durably capture the new target-host evidence

The failed doctor already writes the relevant CampaignStore records before marking the stage failed. **Reuse and authenticate those existing owners first**. Do not invent a sidecar qualification database or rerun merely to manufacture a cleaner result.

Before using the 2026-09-24 MH-1 realization as acceptance evidence, export/snapshot content-addressed copies of the existing:

- `doctor` payload;
- `training_acceleration_parity_policy`;
- `training_acceleration_noise_normalized_parity_policy`;
- `training_acceleration_repeatability_diagnostic`;
- `training_acceleration_noise_normalized_parity` / current parity alias;
- `training_acceleration_realization`;
- selected-head qualification and runtime/source-compatibility records needed to interpret them.

Record: 

- exact mdstats commit/package identity;
- campaign configuration/foundation contract digest;
- exact selected-head derived model digest;
- MACE/e3nn/Torch/CUDA/CuEq package identities;
- exact MACE source/dependency compatibility state, including the reported `mace/calculators/mace.py` byte difference and the semantic probes that admitted it;
- CUEQ-DEP1/runtime-freeze digest when available, including determinism/TF32/matmul/runtime coordinates already owned there rather than duplicating a second runtime probe;
- GPU architecture/device identity;
- parity-policy and stable-channel policy digests;
- full repeatability diagnostic record, not only console summaries;
- deterministic-control state if separately exercised;
- structure/model/descriptor/FPS identities sufficient to establish applicability.

The chat transcript is discovery evidence, not a durable qualification artifact. If the original CampaignStore/workspace cannot be authenticated, record that evidence-loss condition and only then perform a predeclared reproduction under the closest reconstructible runtime; do not silently call the reproduction the original observation.

### 4.3 Required regime and applicability matrix

At minimum evaluate:

1. MPA-0/default FP32 TRAIN2;
2. MH-1/omat_pbe FP32 using the exact EXTRACT1-qualified selected-head checkpoint.

For each row bind model-family/head, exact checkpoint SHA, architecture signature, selected-head extraction identity where applicable, represented elements, probe-corpus identity, GPU architecture, Torch/CUDA/MACE/e3nn/CuEq versions, runtime-freeze/source-compatibility identity, dtype, and parity-method identity.

The in-repository `MLFF_CUEQ_REPEAT1_DIAG3_CPU_QUALIFICATION.json` explicitly states that GPU qualification was not executed. The currently located MPA-0 workstation numbers used to freeze Rev86 survive as summarized prose/test fixtures, not yet as a raw durable GPU record. Stage A MUST search for the original raw artifact. If it cannot be found/authenticated, classify the summary as secondary historical evidence and obtain fresh MPA-0 target-host evidence before using MPA-0 to establish a generic current rule.

Add another materially different supported family/head only if already within the claimed generic policy scope and engineering value justifies it. Do not broaden the project merely to manufacture sample count.

A generic threshold may be claimed portable across model/runtime/hardware axes only when the D2 error semantics justify that portability. Otherwise keep the **acceptance relation** fixed where possible and scope realization evidence to the runtime/applicability coordinates it actually covers; do not create hardware- or family-specific magic constants merely to admit failures.

### 4.4 Statistical validity and reproducibility obligations

The current method retains ten post-warm-up evaluations per backend and computes 45 self pairs plus 100 cross pairs. These pairwise statistics share evaluations and are not independent replicates. The current production probe also evaluates backends in fixed `e3nn -> CuEq` order on every repeat.

Before choosing an estimator, D2 must decide which semantics it intends:

- **finite-sample functional:** the all-pairs object is a deterministic functional of the ten retained outputs; pair dependence is then part of the definition, not “100 independent samples,” and adequacy is tested by repeat-count/process/order sensitivity and independent predeclared realizations; or
- **population/inferential estimator:** uncertainty must be computed with the true experimental hierarchy (evaluation run/process/backend/structure), using an appropriate U/V-statistic, clustered resampling, permutation, or other justified method. Pairwise or force-component pseudo-replication is forbidden.

Any proposed tail/quantile/ratio criterion MUST justify:

- the experimental unit and dependence graph;
- which observations are independent, paired, exchangeable, or conditionally dependent;
- how uncertainty or finite-sample instability of the self-noise envelope and cross statistic is handled;
- repeat count and the predeclared number of independent process-level realizations;
- warm-up adequacy and sensitivity to more than one discarded evaluation;
- fixed-order effects by a counterbalanced/reversed-order or fresh-process diagnostic;
- why the selected tail functional is resolvable at the actual force-component count;
- exact quantile/order-statistic definition, including interpolation method rather than an implicit NumPy default;
- how the method behaves when self-noise is zero, nearly zero, or pathologically inflated;
- whether structure/atom/component multiplicity creates pseudo-replication;
- whether deterministic controls diagnose mechanism without becoming an unrealistic authorization regime;
- joint behavior of multiple hard metrics so threshold proliferation does not create an unexplained classification rule.

In the reported MH-1 run each pair contained only 45 force components. A nominal p99.9 of 45 values is effectively an interpolation at the extreme order statistic, not evidence of independently resolved 0.1% tail behavior. The candidate must either justify that exact finite-sample functional, increase the governed probe support, or replace it with a statistic whose resolution matches the evidence.

Do not justify `P99` reliability by treating 100 correlated cross pairs as 100 independent backend experiments.

### 4.5 Channel-specific semantics and falsification

First define the measured objects and units exactly:

- energy is the calculator total energy divided by atom count, in the calculator's energy/atom unit;
- force components use the MACE/ASE force unit;
- stress uses the ASE Voigt stress convention/unit;
- descriptors are structure-level means of `MACECalculator.get_descriptors(..., invariants_only=True)`, a latent representation whose coordinate scale is architecture-dependent unless independently normalized.

For energy, force, stress, and descriptors:

- state the protected downstream consequence of retaining that channel as a hard gate;
- measure same-backend repeatability and cross-backend discrepancy under identical inputs;
- test whether a channel is genuinely stable enough for an independent absolute ceiling;
- if an absolute ceiling is retained, derive it from accepted numerical-error semantics or sufficiently broad independent evidence, not merely the largest observed passing value;
- if normalization is used, test pathological low-self-noise cases and systematic offsets;
- preserve a catastrophic absolute guard where needed so a large common-noise envelope cannot normalize away a materially large disagreement;
- do not reuse one unscaled absolute scalar across unlike physical/latent channels unless D2 proves that relation meaningful.

The current Rev86 reducer uses `stable_channel_abs_ceiling` as a pure maximum-absolute gate for energy/stress/descriptors, whereas nearby comments/history also describe the conventional `rtol=1e-5, atol=1e-6` policy as the “stable-channel authority.” Stage A must resolve this representation/semantics ambiguity before deciding whether the MH-1 failure falsifies the intended relation or exposes a D4 mismatch.

For descriptors specifically, determine whether numerical descriptor values themselves are governed outputs or whether their protected role is to preserve a downstream selection/neighbor relation. If exact selection identity is the actual invariant, justify any additional absolute descriptor gate by a robustness/margin requirement rather than treating an arbitrary latent coordinate scale as physical error.

For deterministic FPS/selection:

- require exact identity unless D2 explicitly proves a weaker relation preserves every dependent decision;
- bind the exact FPS fraction/tie policy used by production qualification;
- include near-tie structures capable of exposing descriptor perturbations at selection boundaries.

### 4.5A Probe-domain adequacy

The routine doctor corpus is not a representative random sample: it takes one readable periodic campaign structure and constructs at most two deterministic variants (one sinusoidal displacement and one fixed strain). The target-host report exercised 3 structures and 15 atoms total. The parity FPS smoke uses structure-mean invariant descriptors and `selection_fraction=0.5`; with three structures that selects only two structure identifiers. Therefore `100/100` cross selection identity is useful as a local smoke result but is weak evidence for generic selection robustness.

D2/D3 must decide separately:

- the cheap per-campaign doctor smoke corpus needed to catch gross runtime/selected-head mismatches; and
- the evidence corpus needed to justify a generic backend-equivalence claim.

Do not inflate routine doctor cost unnecessarily, but do not use a three-variant local smoke as the sole basis for cross-family numerical authority. Reuse an existing deterministic, leakage-safe development/stress-corpus owner where possible (including prior CuEq qualification corpus machinery) rather than inventing a second selector. Evidence corpus coverage should challenge species, neighbor count/density, strain/stress, force magnitude, descriptor scale, and near-selection-tie regimes material to the claimed validity domain.

### 4.5B Training-kernel relevance

The current doctor probe exercises calculator E/F/stress/descriptors at the selected-head starting checkpoint. Pure-CuEq TRAIN2 also changes forward/backward reduction during optimization. Therefore explicitly test the logical implication being claimed:

`instantaneous selected-head parity -> admissible runtime sanity screen`

is not automatically

`instantaneous selected-head parity -> multi-epoch training scientific equivalence`.

CUEQ-PHASE1 exists to test the latter through short and representative full paired trajectories. Preserve that separation unless a higher-domain authority is intentionally reopened.

### 4.6 Strong counterexamples

At minimum construct or reuse tests that must fail:

1. descriptor systematic offset larger than same-backend noise but below any naive widened absolute ceiling;
2. force tail with acceptable RMSE but materially shifted high-percentile components;
3. identical distribution scale but persistent signed/backend bias;
4. inflated self-noise that would make a pure ratio gate permissive;
5. zero/nearly-zero self-noise with nonzero cross discrepancy;
6. selection/FPS disagreement despite small aggregate numerical errors;
7. one family passing while another falsifies a supposedly generic constant;
8. non-finite output;
9. candidate identity mismatch;
10. repeated-pair pseudo-replication case showing that a naive independent-sample uncertainty estimate is overconfident;
11. backend evaluation-order effect that changes classification;
12. warm-up-count sensitivity that changes classification;
13. quantile-interpolation/cardinality edge case, especially p99.9 with small force-component count;
14. latent descriptor rescaling that leaves protected selection unchanged, to test whether an absolute descriptor gate is actually invariant to representation;
15. stale stored `TrainingAccelerationRealizationRecord` or source-side `AccelerationRealizationRecord` created under an old parity method that would otherwise be accepted by their current shallow loader checks;
16. trained-state counterexample where the starting checkpoint passes but a compatible reachable/perturbed state shows systematic backend/projection disagreement, falsifying an unjustified model-state-uniform claim;
17. CuEq-trained EVAL2 checkpoint whose actual projected forward is portable e3nn but whose measurement identity is labeled CuEq, proving that execution provenance and measurement reuse fail closed after correction;
18. authority-evolution case showing that CONFIG1 source-side `e3nn`, Rev60 generated TRAIN2 `cueq`, doctor admission, explicit e3nn TRAIN2 override, and historical CUEQ-PHASE1/FINAL-GPU1 state remain distinct rather than being collapsed into one boolean.

### 4.7 Historical evidence is evidence, not authority

Reconstruct why:

- selected-head MH-1 earlier motivated a `2e-6` TRAIN2 FP32 absolute floor;
- MPA-0 later motivated a `1e-5` force ceiling;
- DIAG3 led to the current force noise-normalized criterion and the return of energy/stress/descriptor to `1e-6`.

Determine whether the later generic policy had adequate cross-family evidence for each stable-channel assumption. Do not simply revert to an older constant.

### 4.8 D3/D4 currentness defects to resolve if confirmed

Current inspection confirms two stale-authority surfaces:

1. `_stored_training_acceleration_realization(..., require_qualified=True)` authenticates requested backend, device/dtype, checkpoint bytes, and the record's own historical `qualified` flag, but not the **currently accepted parity-policy/method identity**.
2. `_stored_acceleration_realization(..., require_qualified=True)` likewise accepts the source-side realization from backend/device/dtype plus historical `qualified` state; it does not prove that the parity record(s) behind that realization belong to the current source-side D2 method/policy.

Optimizer/training identities bind the training acceleration-realization digest, while source/pseudolabel consumers bind their own inference/currentness ancestry.

These are D3/D4 stale-authority defects independent of which numeric TRAIN2 FP32 criterion wins. Stage A/D must trace the complete currentness graph for impact and repair the existing owners directly:

- reuse the existing stored parity-policy/parity/realization records;
- make consequential reuse of both source-side and TRAIN2 CuEq realizations prove the current accepted parity method/policy identity and applicable runtime/model identity;
- cause an old doctor pass to become stale/fail closed after a parity-authority change;
- do not create a second realization registry or migration database;
- preserve historical records byte-for-byte.

Also project the impact of a new realization digest onto existing TRAIN2 identities. Do not blindly retrain or blindly reuse: determine whether the changed coordinate is training-bearing execution semantics, admission evidence only, or an over-bound representation. If current D3 identity overbinds a non-consumed admission-policy digest, route a D3 simplification; if the accepted execution realization materially changes, old CuEq training roots remain stale-dependent until requalified. e3nn roots are unaffected.

### 4.9 Evidence-oracle independence

Existing unit tests that repeat frozen MPA-0 scalar tuples prove reducer serialization and branch behavior; they are not independent numerical validation of the criterion. The repaired method requires:

- a small independent oracle for the exact estimator/reducer semantics;
- adversarial cases whose expected classification is derived from D2, not copied from production helper output;
- real-owner integration evidence through doctor/currentness;
- target-host evidence for every claimed runtime/family scope.

Do not count several tests sharing the same generated expected values as independent corroboration.

## 5. Concretization sequence

### Stage A — Evidence intake, authority reconstruction, and defect partition

1. Authenticate/export the existing failed-doctor CampaignStore evidence before rerunning anything.
2. Resolve the exact accepted D1/D2 parent (`a759e81.../a4824d2...` at plan opening) and separately identify unrelated proposed renewals on repository head.
3. Record the confirmed source-closure result: the accepted D2 source contains no CuEq parity relation at any dtype/role, while the current D4 index classifies parity diagnostics/hotfix material as non-semantic history. Inventory the current source/DATA6 and TRAIN2 FP32/FP64 relations. Treat their D4/historical specifications as executable guards/evidence, not accepted D2 authority, until the role/dtype family is source-closed.
4. Reconstruct every dependent policy digest/currentness edge through doctor, source-side and TRAIN2 stored realizations, optimizer/training identity, checkpoint projection/EVAL2 measurement identity, CUEQ-PHASE1, PERF-CERT1 and FINAL-GPU1.
5. Perform the bounded historical CuEq parity/HAS review and classify evidence by provenance: raw realization, derived summary, synthetic fixture, or prose-only claim.
6. Search for the original MPA-0 DIAG3 workstation artifact. If unavailable, do not promote the hardcoded summary fixture into raw evidence.
7. Confirm that the MH-1 observation binds the exact EXTRACT1 selected-head checkpoint and current runtime/source-compatibility evidence.
8. Audit metric semantics: energy/atom, stress convention, descriptor construction, FPS policy, absolute-vs-rtol stable-channel ambiguity, NumPy percentile method, finiteness, and pair counts.
9. Falsify fixed backend-order, warm-up, process-state, corpus-size, and small-tail-resolution effects with bounded diagnostics.
10. Treat both stored-realization currentness defects in Section 4.8 as confirmed at their direct loader boundaries and trace whether any upstream stage fence happens to compensate for them; repair the direct consequential-use owners regardless of incidental call ordering.
11. Reconstruct the accepted TRAIN2 -> EVAL2 recurrence repair and prove the actual current representation sequence: transient CuEq authentication/state load -> native projection -> portable e3nn forward. Confirm the current `_checkpoint_provider_realization` backend-label mismatch and its exact affected measurement/currentness surface.
12. Classify the existing trained-state/projection parity tests by evidence scope, and determine what D2 model-state applicability argument/evidence is required before treating a starting-checkpoint doctor witness as a family-wide backend relation.
13. Reconstruct the authority evolution in actual chronological/semantic order: CONFIG1 foundation/source-side `e3nn` -> CUEQ-PHASE1 paired-training evidence contract -> Rev60 phase-separated generated TRAIN2 `cueq` policy -> Rev61+ doctor parity hardening -> current generated split. Record precisely which claims belong to source policy, TRAIN2 generated policy, doctor admission, paired-training evidence, explicit e3nn override, and FINAL-GPU1.
14. Confirm that current user-facing/runtime documentation consistently describes generated TRAIN2 `cueq` as doctor-qualified/fail-closed, preserves source-side `e3nn`, and does not falsely rewrite immutable CUEQ-PHASE1/FINAL-GPU1 records.
15. If a pure D4 metric defect explains part of the observed failure, repair that owner separately and rerun measurement evidence, but still close the independently confirmed missing-D2 relation, stored-realization currentness, and EVAL2 measurement-provenance gaps.

**Gate A:** proceed to the D2 candidate only when evidence provenance is sufficient, D4 measurement defects are partitioned, the parent authority is unambiguous, and the confirmed missing CuEq acceleration-equivalence family can be specified without importing an unresolved lower-level contradiction.

### Stage B — Bounded D2 candidate method

1. Define one D2 acceleration-equivalence family with explicit role/dtype/model-state applicability. Preserve source/DATA6 calculator relations and trained-state projection relations unless separately challenged; isolate TRAIN2 as a **training-operator** member rather than another calculator-inference alias.
2. State the exact proposition of current doctor admission and its relationship to the starting checkpoint, the backend-specific forward/backward graph, optimizer-consumed gradients, reachable trained states, native CuEq -> portable-e3nn projection/EVAL2, CUEQ-PHASE1, Rev60 generated TRAIN2 policy, the explicit e3nn override, and FINAL-GPU1.
3. Define every governed observable, unit/normalization and protected consequence. Descriptor/FPS parity remains hard only where source/DATA6 selection actually consumes it; it is not a TRAIN2 gate unless a current TRAIN2 consumer is identified.
4. Define the TRAIN2 experimental unit as the **fresh process**. Repeats within one process are nested measurements. The replacement is a predeclared finite-sample qualification functional, not a claim that all-pairs differences are independent population samples.
5. For each continuous TRAIN2 observable vector, define the e3nn reference centroid, e3nn finite-sample variability, CuEq centroid bias, CuEq variability, and order-cell conditional bias directly. Do not retain redundant p99/p99.9/max tail gates unless an independent protected consequence requires them.
6. Separate **persistent bias** from stochastic non-determinism. A systematic backend centroid shift cannot borrow a one-realization noise RMS as its acceptance margin because systematic training error can accumulate while zero-mean execution noise need not. Global and order-cell centroids must instead use the existing dtype calculator precision constants componentwise: FP32 `rtol=1e-5, atol=1e-6`; FP64 `rtol=1e-10, atol=1e-12`. Their use on TRAIN2 transition centroids is a new proposed D2 relation and must be independently falsified; the constants themselves are fixed independently of the Stage-A CuEq outcomes.
7. Use e3nn-only repeatability only for the stochastic-spread coordinate. For each governed vector derive a tolerance RMS scale from the dtype mixed envelope around the e3nn centroid and require CuEq total/global and cell-local variance to be no larger than `V_e3nn + T_dtype^2`. This directly budgets at most one fixed dtype-tolerance-sized additional variance beyond the accepted reference, without a fitted ratio or factor-two allowance.
8. Test the **training-state transition**, not merely raw calculator outputs or an implementation-specific gradient coordinate. For each bound model state, harvest qualification windows from the real accepted TRAIN2 loader/exposure trace before any CuEq outcome is inspected. The trace must preserve exact replay-first/target-second pre-shuffle layout where replay is active, accepted seed/shuffle/sampler semantics, batch size and `drop_last`. Each retained backend observation resets exact model/optimizer/EMA/RNG state, executes the same two consecutive harvested optimizer-update batches, maps resulting states through the canonical transient->portable state-transfer transform, and compares update-induced e3nn prediction changes on a frozen witness corpus. The measurement transform must not re-import source/DATA6 descriptor/FPS acceptance into TRAIN2.
9. Require gradients, losses, parameters, optimizer state and EMA state to remain finite during the two-step witness. Select the smallest deterministic set of consecutive two-update windows from the reference-only exposure trace that covers every active head/property-mask branch capable of reaching the optimizer; selection may inspect only corpus/head/property metadata and accepted exposure order, never CuEq values. At least one native consecutive window is mandatory even when a branch-specific supplemental window is needed. A descriptor-only or calculator-only proxy cannot substitute.
10. Descriptor/FPS parity remains hard only where source/DATA6 selection consumes it. It is removed from TRAIN2 authorization unless a current TRAIN2 consumer is identified.
11. Cover model-state applicability explicitly. `S0` is the exact starting checkpoint. A full TRAIN2-operator claim also requires at least one authenticated non-initial `S1` state of each materially distinct claimed architecture/head topology, obtained independently of candidate acceptance (for example, a reference-e3nn bounded adaptation state or still-applicable authenticated trained-state evidence). `S0` evidence alone may establish entry execution but cannot be represented as proof over reachable trained states.
12. Use the already frozen counterbalanced qualification design unless independent review falsifies it: 4 construction/evaluation-order cells, 5 fresh processes/cell, 1 discarded warm-up and 3 retained observations/process, with exact state reset for every retained training-operator observation. This cardinality was frozen before the Stage-A outcomes and is not selected from a passing candidate.
13. Keep non-finite values, shape/head/objective/runtime mismatch, projection/authentication mismatch and unsupported applicability as hard fail-closed outcomes. The transient->portable measurement map must be independently checked for every measured CuEq state: exact canonical portable-shell architecture plus direct transient-CuEq versus mapped-portable-e3nn E/F/stress agreement under the dtype mixed numerical envelope on a frozen mapping witness. A bounded dependency-native projection/state-value differential remains an additional oracle, not the sole warrant. Add a candidate-independent catastrophic guard at the accepted TRAIN2 robust-loss property scale: no retained paired backend discrepancy in energy/atom, force, or stress (including transition-displacement channels) may reach the corresponding `0.01` property Huber transition scale. This is a gross materiality guard, not the equivalence tolerance.
14. Separate qualification from routine admission. The multi-process experiment establishes a current runtime/model/operator qualification record. Routine doctor may perform a cheaper bound execution witness and authenticate that record, but the cheap witness cannot recreate, widen or substitute for the D2 qualification relation.
15. Bind qualification currentness to all arithmetic-relevant CUEQ-DEP1/runtime coordinates, MACE/Torch/CUDA/CuEq versions/source identity, device/runtime precision flags, dtype, architecture/head topology, objective identity, probe-state class and D2 method digest.
16. Source-close unchanged siblings explicitly:
    - source/DATA6 FP32: componentwise `rtol=1e-5, atol=1e-6` for energy/force/stress/descriptors plus exact FPS fingerprint under the existing selection policy;
    - source/DATA6 FP64: componentwise `rtol=1e-10, atol=1e-12` plus exact FPS fingerprint;
    - TRAIN2 FP64 forward calculator guard retains those existing FP64 numerical values, but a forward-only record is no longer sufficient to claim a training operator;
    - trained-state CuEq -> portable-e3nn projection retains exact canonical portable-shell architecture authentication and the existing post-projection calculator relation.
17. Define policy/method digest, record currentness, historical-readability/remap semantics and the exact relation between the new operator qualification and existing CampaignStore realization records.
18. Produce a bounded D2 overlay against the accepted `a759e81.../a4824d2...` parent. Do not edit the unrelated proposed canonical-path renewal merely because it occupies `docs/methods/` on branch head.
19. Write and freeze the proposed D2 authority before changing D4 product thresholds or doctor admission logic.

**Gate B:** candidate method must be source/definition closed, dimensionally/semantically coherent, operator-complete for every TRAIN2 dtype it claims to support, statistically identifiable at its evidence cardinality, and free of constants selected merely because they admit the Stage-A MH-1/MPA-0 observations.

### Stage C — Independent numerical falsification

Exercise the frozen candidate method against:

- fresh candidate-bound MPA-0 target-host evidence;
- fresh candidate-bound MH-1 target-host evidence;
- exact starting state `S0` and at least one independently obtained non-initial `S1` state for every materially distinct claimed architecture/head topology;
- actual TRAIN2 target/replay/head/property branches that can reach the optimizer;
- mandatory starting-state physical E/F/stress channels plus two-step update-induced portable-e3nn prediction deltas under the frozen finite-sample functional, with finite loss/gradient/optimizer/EMA execution during the witness;
- an evidence corpus adequate for the claimed validity domain;
- synthetic/adversarial counterexamples from Section 4.6, including candidate variance inflation, cell-specific persistent-bias cancellation, optimizer-state-step-2 drift, replay/target exposure reorder or hand-built-batch substitution, descriptor-only drift, wrong head/objective/state/runtime, projection corruption, and deterministic-reference/tolerance-floor cases;
- predeclared independent process/order realizations sufficient for the chosen finite-sample semantics;
- applicable deterministic-control diagnostics without substituting them for ordinary production-path evidence;
- FP64 training-operator evidence if CuEq FP64 TRAIN2 remains in supported scope; otherwise an explicit support narrowing with no claim that the historical forward-only FP64 record proves training equivalence.

Freeze the number of repetitions before inspection. A candidate that merely admits both real regimes but cannot reject systematic disagreement or candidate-only variance inflation is not acceptable. A candidate whose global average passes only because opposite order-cell biases cancel is not acceptable. Because the proposed relation is a finite-sample qualification functional rather than a p-value estimator, its exact process/repeat/cardinality and boundary semantics are part of D2 identity; rerun-until-pass is forbidden.

**Gate C:** immutable composed D2 candidate, fresh independent D2 Review, and explicit stakeholder ratification of that exact reviewed target.

### Stage D — D3/D4 handoff

Only after Gate C:

1. re-resolve current accepted D3 and avoid editing an unrelated proposed architecture candidate as though accepted;
2. map the accepted D2 relation onto one canonical D4 parity/reducer owner in `acceleration.py`;
3. remove superseded criterion machinery rather than layering a second special-case path;
4. repair source-side and TRAIN2 stored-realization/stage currentness using existing CampaignStore policy/parity/realization records so an old-policy `qualified=true` cannot authorize current execution;
5. revise record/policy schemas only where method meaning/fields require it; retain historical deserialization without historical authorization;
6. update doctor diagnostics to expose the method, evidence cardinality/applicability and failure reason transparently;
7. update optimizer/training identity only according to the accepted D3 projection; do not force retraining merely because a representation changed, and do not reuse a genuinely changed execution realization;
8. correct P5 EVAL2 provider-realization identity at the existing measurement owner: after CuEq checkpoint authentication and native projection, the numerical forward backend is portable `e3nn`. Preserve transient CuEq authentication as upstream state provenance; do not relabel the forward as CuEq.
9. let the corrected EVAL2 measurement identity naturally stale/recompute old mislabeled measurements and downstream assessments through the existing evidence store. Do not retrain authenticated TRAIN2 roots solely for this assessment-side identity correction.
10. regenerate/rebind FINAL-GPU1 preflight/handoff artifacts rather than mutating a release-pinned handoff whose integrity contract forbids source edits;
11. update policy-digest/currentness dependencies and stale-stage behavior;
12. preserve no-silent-fallback and the current generated phase split: source/DATA6/pseudolabel side `e3nn` by default, TRAIN2 `cueq`; P5 checkpoint EVAL2 uses the authenticated portable e3nn projection of that TRAIN2 state. A temporary explicit `training_backend="e3nn"` repair-time override must not be confused with changing the generated default;
13. preserve the claim boundaries of CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 without inventing them as universal prerequisites for current CuEq TRAIN2 doctor admission;
14. add focused positive/negative tests that exercise the real numerical owner and independent oracles rather than duplicating expected logic in fixtures.

### Stage E — Assembled acceptance

Run and retain exact candidate identities for:

- independent estimator/reducer oracle tests and adversarial tests;
- focused parity-policy/unit/schema/backward-readability tests;
- source-side and TRAIN2 stored-realization/stale-stage/currentness tests;
- trained-state/model-state-domain parity tests, reusing the existing real CuEq recurrence owner rather than inventing a second projection harness;
- P5 EVAL2 measurement-identity tests proving CuEq checkpoint authentication -> portable e3nn forward is labeled e3nn, old mislabeled measurements are not reused, and authenticated TRAIN2 roots are not retrained merely because assessment identity changed;
- specification/authority-layer tests;
- doctor/config/default tests;
- affected optimizer/training-identity and restart/reuse tests;
- affected CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 preflight/handoff tests;
- affected acceleration/foundation/MH-1/MPA-0 tests;
- complete affected CPU regression;
- real target-host MH-1 parity requalification under the exact accepted method/runtime;
- real target-host MPA-0 requalification whenever the accepted relation claims MPA-0/generic coverage.

CPU skips cannot stand in for mandatory target-host evidence. GPU evidence may be deferred only for a claim explicitly left unqualified; a CuEq production authorization may not be closed PASS with its required runtime check skipped.

Long paired training trajectories are **not required merely to prove the current instantaneous parity admission relation**. Rev60 decoupled generated CuEq TRAIN2 campaign policy from the immutable historical CUEQ-PHASE1 record, so this workplan must not invent a new phase-1 prerequisite. If the user's target-host run is also intended to produce CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 evidence, execute those existing gates under their own contracts after parity admission rather than redefining them inside this workplan.

## 6. Reopen, simplification, and human triggers

### Earliest owner to reopen

- wrong metric/identity/comparison implementation -> D4;
- insufficient representation of realization/policy/currentness -> D3;
- invalid equivalence statistic, tolerance, precision/noise model, or stochastic semantics -> D2;
- changed scientific meaning of what backend equivalence must protect -> D1.

### Evidence that invalidates frozen premises

Reopen the candidate if:

- accepted D1/D2 parent authority advances and materially overlaps this overlay before promotion;
- the Rev86 D2 acceptance/import route cannot be established and the proposed replacement fails formal source closure;
- same-backend variability is materially nonstationary across repeats, process realizations, evaluation order, runtimes, or structures;
- model family/head materially changes the error regime and no generic criterion remains defensible;
- descriptor noise can change FPS selection despite aggregate parity;
- CuEq/e3nn disagreement has persistent signed structure beyond repeatability noise;
- the proposed criterion becomes permissive under inflated self-noise;
- required evidence depends on an unavailable/unsupported runtime;
- the cheap doctor corpus and qualification evidence corpus cannot be related to the claimed validity domain;
- instantaneous parity passes while paired-training or other applicable higher-level evidence shows systematic backend disagreement; such contradiction challenges adequacy even when the higher-level artifact is not a universal runtime prerequisite.

### Simplification trigger

If the implementation starts accumulating:

- family-specific threshold maps;
- legacy fallback criteria;
- repeated special-case branches for individual channels;
- parallel parity record types carrying the same semantic claim;

stop and reconsider the D2 formulation/owner. Prefer one explicit parameterized family or one stronger general relation over exception accumulation.

### Human decisions

Stakeholder ratification is required for the accepted D2 replacement. The agent may propose and falsify but may not self-ratify a materially different backend-equivalence envelope.

## 7. Impact and history

On accepted D2 formalization/change:

1. preserve Rev83-86/CUEQ-DEFAULT1 and the accepted TRAIN2->EVAL2 recurrence-repair artifacts exactly as historical evidence; do not rewrite history to imply current D2 authority;
2. promote the parity relation through the accepted D2 owner/overlay with explicit source closure and parent identity;
3. reconcile any accepted successor D1/D2/D3 state before promotion rather than merging candidate files by path;
4. update current D3/D4 architecture/specification documentation and `docs/specs/training_data/README.md` so there is exactly one current numerical owner;
5. update semantic dependency/currentness views;
6. remap or invalidate evidence bound to the old parity-policy/method digest, but preserve still-applicable raw observations;
7. require stale stored CuEq realizations to requalify under current policy before consequential use;
8. project realization-digest changes onto TRAIN2 roots. Preserve e3nn roots. For CuEq roots, distinguish an actual changed execution realization from a non-consumed admission-policy representation before deciding reuse/retraining;
8A. separately project the corrected EVAL2 provider-realization identity: preserved authenticated checkpoint/training roots may be reused, but old measurements/assessments whose identity falsely claimed a CuEq forward must be treated as stale and recomputed under the portable e3nn forward identity;
9. regenerate any FINAL-GPU1 preflight/handoff/release-side artifact whose integrity contract binds the old policy; never edit a sealed handoff in place;
10. preserve frozen release/audit/SHA records as historical evidence;
11. reconcile CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 state separately where those release/evidence claims are in scope—parity acceptance alone does not rewrite their immutable status, and their pending status does not by itself revoke the later Rev60 generated TRAIN2 `cueq` campaign policy;
12. reconcile PEM only if this episode establishes a qualifying new failure family, success application, notice, or materially changes an existing lesson;
13. record the evidence-quality and transportability failure that caused the old MPA-0-derived rule to be challenged so the same threshold-tuning cycle is not repeated.

## 8. Acceptance and handoff

The workplan may close only when all of the following hold:

- the accepted D1/D2 parent and any overlapping successor authority are explicitly resolved;
- the confirmed acceleration-parity source-closure gap is closed by an accepted role/dtype/model-state D2 family covering every current CuEq acceleration-equivalence relation that remains supported; only the challenged TRAIN2 FP32 doctor member may change numerically without separate falsification of its siblings;
- the current Serious Challenge has been resolved by an accepted D2 criterion/formalization or falsified by evidence showing the original relation remains adequate;
- the original MH-1 observation exists as durable, applicability-qualified evidence or its unavailability is explicitly recorded and a reproduction is distinguished from it;
- MPA-0 evidence used for any generic claim is raw/authenticated or freshly re-realized; prose/test fixtures alone do not carry raw-evidence force;
- generic-vs-regime/runtime/hardware/model **and model-state** scope is explicit; starting-checkpoint-only evidence is never represented as proof over reachable trained states, and every supported TRAIN2 dtype has a source-closed backend-specific training-operator consequence;
- the parity gate's exact current-admission proposition and its claim-boundary relationship to CUEQ-PHASE1, Rev60, current generated defaults, and FINAL-GPU1 are explicit;
- channel units/scales/protected consequences and descriptor semantics are explicit; TRAIN2 operator qualification covers the consequence of optimizer-consumed loss/gradient computation through the authenticated state transition, requires finite loss/gradient execution, and does not retain descriptor/FPS as a hard TRAIN2 gate without a real TRAIN2 consumer;
- estimator dependence, quantile definition/resolution, order/warm-up/process effects and uncertainty/finite-sample semantics are closed;
- probe-domain adequacy is established for the claim being made;
- adversarial false-pass/false-fail/currentness cases are closed;
- the immutable composed D2 candidate passes fresh independent Review;
- stakeholder ratification of that exact reviewed target is recorded;
- D3/D4 realize exactly the accepted relation with no special-case bypass or duplicate registry;
- stale source-side and TRAIN2 stored realizations/stage state fail closed under a changed policy and historical records remain readable but non-authorizing;
- the TRAIN2 -> EVAL2 representation boundary is explicit and source-closed: transient CuEq state is authenticated before native projection, while the EVAL2 measurement identity names the actual portable e3nn numerical forward;
- affected old CuEq-trained EVAL2 measurements carrying the wrong backend realization become stale/recomputed through existing measurement identity without unnecessary TRAIN2 retraining;
- all dependent policy-digest/currentness/FINAL-GPU1 bindings are reconciled;
- complete affected CPU regression passes;
- required target-host requalification passes for every regime claimed by the accepted relation;
- no required check is merely deferred while an unqualified CuEq production claim is made;
- workplan closure does not rewrite CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 status; current CuEq TRAIN2 admission follows the accepted current campaign-policy lineage, whose generated split is source `e3nn` / TRAIN2 `cueq`; generated-default ownership remains separate from the parity relation itself;
- user-facing/runtime documentation must describe those distinct claims consistently and must not either (a) pretend a doctor pass retroactively passes historical release gates or (b) invent a historical release gate as a universal prerequisite that the later accepted project policy explicitly decoupled.

Until closure, a production MH-1 run that must proceed **without exercising the challenged CuEq TRAIN2 relation** must override both sides explicitly:

```toml
[acceleration]
backend = "e3nn"
training_backend = "e3nn"
only_cueq = false
require_available = true
```

Setting only `backend = "e3nn"` is insufficient for a phase-separated campaign because the current generated `training_backend` remains `cueq`. This is a bounded operational override for the affected run, not authority to change the generated campaign default.


## 9. Historical R1 exhaustive workplan-review closure — superseded by R2/R3/R4/R5

This Revision-2 workplan incorporates the formal review performed against `main@af89c30...`, the accepted Protocol-6.4 D1/D2 baseline `a759e81...` / source `a4824d2...`, current D4 authority-index rules, current acceleration/doctor implementation, historical CUEQ-DEFAULT1/DIAG3/PARITY1 records, CUEQ-PHASE1, Project Engineering Memory, and FINAL-GPU1 binding machinery.

The review repaired these plan-level blockers:

1. accepted-vs-proposed D1/D2 authority collision and composition;
2. Rev86 parity-spec owner misclassification / possible missing D2 promotion route;
3. conflation of instantaneous parity with paired-training authorization;
4. failure to reuse already-persisted failed-doctor evidence;
5. secondary-summary-only status of located MPA-0 workstation evidence;
6. all-pairs pseudo-replication and finite-sample-vs-inferential ambiguity;
7. fixed backend evaluation-order and warm-up/process-state confounding;
8. underspecified quantile interpolation and p99.9 resolution at small component count;
9. under-scoped one-geometry doctor corpus for a generic equivalence claim;
10. unit/scale and latent-descriptor semantics, including the single stable-channel absolute ceiling;
11. ambiguity between absolute TRAIN2 stable-channel reduction and nearby rtol/atol descriptions;
12. missing protected-consequence test for each retained parity channel;
13. stale stored realization reuse across parity-policy changes;
14. missing projection from realization changes into optimizer/TRAIN2 identity;
15. incomplete FINAL-GPU1 release-pinned currentness impact;
16. weak distinction between synthetic reducer tests and independent numerical oracles;
17. missing no-retry/classification-stability requirement;
18. incomplete runtime/source-compatibility applicability, including semantically qualified MACE source-byte drift.

**R1 disposition: PASS AS WORKPLAN.** No remaining plan-level blocker was found after the repairs above. This is not a PASS of the challenged CuEq D2 method, not CUEQ-PHASE1 authorization, and not permission to implement new thresholds. Stage A remains the next executable gate.


## 10. Historical R2 post-repair review closure — superseded by R3/R4/R5

Revision 2 was re-reviewed rather than accepted on assertion. That re-review promoted three additional facts from investigation items to confirmed obligations:

1. the exact accepted D2 source `a4824d2...` contains no CuEq-specific or FP32 parity relation, so the Rev86 rule is not source-closed under the accepted Protocol-6.4 D2 equivalence registry;
2. `_stored_training_acceleration_realization` directly permits reuse of a historical `qualified=true` realization without checking the current parity-method/policy identity;
3. no later positive CUEQ-PHASE1 record was found, and the ordinary campaign runtime does not consume the phase-1 qualification record directly, so qualification-evidence execution and production authorization must be represented separately.

The review also sharpened the selection-evidence limitation: with the reported three-structure doctor corpus and `selection_fraction=0.5`, the exact FPS equality check selects only two structure IDs from structure-mean latent descriptors.

**R2 disposition: PASS AS WORKPLAN after Revision-3 repair.** R1 is retained as historical review evidence but is superseded by this R2 closure. No remaining plan-level blocker is known. Stage A remains the next gate; no new parity threshold or CuEq production authorization is accepted by this disposition.


## 11. Historical R3 authority-evolution correction — superseded by R4/R5

The Revision-3 plan was subjected to a final historical-authority adversarial check. That check found that R2 had over-constrained current CuEq execution by treating the still-deferred CUEQ-PHASE1 record as a blanket production prerequisite.

Revision 60 (`CUEQ-DEFAULT1`, mdstats 0.20.193a0) explicitly records a stakeholder/project policy change: phase-separated TRAIN2 CuEq became the generated campaign policy at that time, while the immutable CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 records retained their original meanings and were **not** retroactively changed. Revision 61 then used selected-head doctor parity as the fail-closed training realization gate. R3 incorrectly interpreted later CONFIG1 source-backend language as moving the complete generated TRAIN2 default back to e3nn. Current source and regression tests show the generated phase split remained source `e3nn` / TRAIN2 `cueq`; Revision 7 corrects that mistaken R3 interpretation.

Revision 4 therefore:

- retains CUEQ-PHASE1 as valuable stronger paired-training evidence and a release-gate input where applicable;
- removes the false rule that every explicit current CuEq campaign requires a positive phase-1 record;
- preserves doctor parity as the current explicit-realization admission surface that needs proper D2 formalization;
- keeps generated-default policy, explicit opt-in admission, paired-training evidence, and FINAL-GPU1 release qualification as distinct semantic claims.

**R3 disposition: PASS AS WORKPLAN after Revision-4 repair.** R2 is superseded on this authority-evolution point. No remaining plan-level blocker is known after the final historical check.


## 12. Historical R4 full acceleration-parity source-closure correction — superseded by R5

The final source-closure audit generalized the D2 omission correctly: the accepted source contains no CuEq-specific relation at all, not merely no TRAIN2 FP32 rule. Therefore source/DATA6 FP32 and FP64 CuEq parity are also D4/historical relations lacking explicit accepted-D2 source closure.

Revision 5 closes this without turning the MH-1 TRAIN2 failure into permission to alter unrelated tolerances:

- D2 must define/source-close the current acceleration-equivalence family by role and dtype;
- source/DATA6 FP32 and FP64 relations retain their current numerical semantics unless separately falsified;
- the substantive numerical redesign/falsification remains bounded to TRAIN2 FP32;
- downstream D3/D4 can then bind each realization to an explicit accepted D2 member rather than an unlisted D4 constant.

**R4 disposition: PASS AS WORKPLAN after Revision-5 repair.** No known parity-authority surface is left outside the plan, and no unaffected numerical sibling is silently relaxed.


## 13. R5 terminology/source-closure consistency check

The terminal consistency pass found one residual wording error: the opening still called Rev86 an “accepted” D2 criterion after R2/R4 had established that the accepted Protocol-6.4 D2 source contains no CuEq parity relation. Revision 6 now consistently distinguishes:

- the **current executable fail-closed rule** carried by D4/historical Rev86 machinery;
- the **accepted D2 authority**, which currently lacks source closure for the CuEq acceleration-equivalence family;
- the proposed future D2 relation, which requires independent Review and stakeholder ratification.

Earlier R1-R4 closure sections are retained only as historical review chronology and are explicitly labeled superseded.

**R5 disposition: PASS AS WORKPLAN after Revision-6 repair.** No remaining semantic contradiction or plan-level blocker was found in the terminal consistency pass.


## 14. R6 generated phase-split / safe-override correction

A further independent pass checked the workplan's policy statements against the actual user-facing generator and current regression tests rather than relying on CONFIG1 prose alone.

That pass found a material plan defect:

- `_config_template(...)` defaults `acceleration_backend="e3nn"` and `training_acceleration_backend="cueq"`;
- the `init` parser defaults `--backend e3nn` and `--training-backend cueq`;
- `tests/test_mlff_cueq_train_default1.py::test_init_defaults_training_to_cueq_but_source_to_e3nn` and the generated-policy test explicitly protect that phase split;
- CONFIG1 tests asserting `cfg["acceleration"]["backend"] == "e3nn"` constrain the **source** backend and do not prove that TRAIN2 defaults to e3nn.

Therefore the earlier R3/R5 shorthand “current generated MH-1 default remains e3nn” was materially ambiguous/incorrect for this TRAIN2 workplan. More importantly, the previous repair-time TOML example set only `backend="e3nn"`; in a phase-separated generated configuration that leaves `training_backend="cueq"` and therefore does **not** avoid the challenged TRAIN2 relation.

Revision 7 closes the defect by:

1. recording the current generated split explicitly as source `e3nn` / TRAIN2 `cueq`;
2. preserving that accepted generated policy as outside this numerical-relation repair unless separately reopened;
3. defining the bounded repair-time safe override as both `backend="e3nn"` and `training_backend="e3nn"`;
4. correcting residual “accepted gate” wording to “current executable D4 gate,” because accepted D2 source closure is precisely what this cycle must supply;
5. removing the dead Gate-A branch that spoke of a possibly already-accepted CuEq relation after source inspection had already confirmed the relation is missing.

**R6 disposition: PASS AS WORKPLAN after Revision-7 repair.** No remaining plan-level blocker is known after reconciling the workplan with the actual generated phase-separated configuration and current tests.


## 15. R7 live-policy wording closure

After Revision 7 corrected the safe TOML and top-level generated split, a line-by-line contradiction sweep found three remaining **operative** statements that still encoded the same obsolete interpretation:

- the opening called CuEq TRAIN2 “opt-in,” although current generated campaigns default TRAIN2 to `cueq`;
- Section 3.5 still claimed later CONFIG1 returned the complete generated campaign default to e3nn, reversing the actual authority chronology;
- the Stage-A counterexample and authority-reconstruction steps still referred to a “current e3nn generated default.”

Revision 8 repairs all three. The live authority narrative is now consistent:

```text
CONFIG1: canonical MH-1/omat_pbe + source-side e3nn
CUEQ-PHASE1: paired-training qualification evidence contract
Rev60 CUEQ-DEFAULT1: generated TRAIN2 cueq, source side stays e3nn
Rev61+: selected-head doctor parity hardens the CuEq TRAIN2 realization gate
current generator/tests: source e3nn / TRAIN2 cueq
repair-time containment when needed: explicit TRAIN2 e3nn override
```

**R7 disposition: PASS AS WORKPLAN after Revision-8 repair.** The operative workplan now contains no known generated-backend-policy contradiction.


## 16. R8 live claim-boundary cleanup

The post-R7 scan intentionally excluded superseded review history and inspected only operative Sections 0-8. It found five residual phrases that still treated CuEq TRAIN2 as an “explicit opt-in” path or described “e3nn” as the undifferentiated campaign default.

Revision 9 replaces those with the exact current split and claim boundaries:

- generated source/DATA6/evaluation = `e3nn`;
- generated TRAIN2 = `cueq`;
- doctor parity = fail-closed realization admission for CuEq TRAIN2;
- explicit `training_backend="e3nn"` = repair-time/reference override;
- CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 = separate immutable evidence/release claims.

It also strengthens affected regression requirements so “campaign default” tests must assert the full two-backend split, not merely the source-side CONFIG1 field.

**R8 disposition: PASS AS WORKPLAN after Revision-9 repair.** No live Section 0-8 backend-policy ambiguity is known.


## 17. Candidate-4 independent NO-PASS and Candidate-5 repair

Fresh independent Protocol-6.4 D2 Review of immutable Candidate 4

`cd4e0453d0a27ae01f7041c1c9d222fd9d71a0e9`

returned **NO-PASS** with no SERIOUS CHALLENGE to the accepted parent.

The blocking owner remained D2. The Review identified seven material defects:

1. complete optimizer/EMA state was under-observed;
2. source-calculator tolerances were transferred to TRAIN2 centroids without a training-operator warrant;
3. nested repeats were used inside the primary variance estimator despite fresh process being the declared independent unit, and cell-local candidate variance borrowed global reference variance;
4. the `0.01` Huber transition scale was used as an unrelated catastrophic backend ceiling;
5. minimum metadata-covering loader windows could systematically omit difficult exposure regimes;
6. state-transfer measurement retained mutation/common-mode holes; and
7. source/DATA6 and projection/EVAL2 historical D4 relations were described as if already source-closed D2 siblings.

Candidate 5 repairs those blockers and is frozen at immutable semantic target:

`6e73fbb7af9b8d46f61cf81113259584ffed8527`

with canonical blob:

`4bfd2451cc1835e82e303cc9a597b69b8f8deda9`.

The Candidate-5 repair record is:

`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_5_REPAIR.md`.

Material Candidate-5 changes include:

- complete TRAIN2 state semantics and exact discrete-state consequences;
- EMA physical-function observation;
- canonical optimizer-action probes plus independent optimizer-state transfer checks;
- a new prospective TRAIN2 physical numerical budget `epsilon_(c,d)=delta_c*sqrt(u_d)`, explicitly proposed rather than inherited;
- recurrence-horizon bounded adaptation and coherent-drift growth extrapolation over the remaining accepted horizon;
- entry/mid/late full-state anchors;
- process-level primary stochastic reduction, distinct within-process variance, matching-cell reference variance, two independent complete ensembles, and typed insufficient-resolution outcomes;
- removal of `0.01` as a direct backend discrepancy ceiling;
- reference-controlled per-component non-dilution guard;
- expanded real-loader boundary/extreme/branch exposure;
- snapshot-only non-mutating model-state transfer with independent anti-common-mode oracle;
- source/DATA6 and projection/EVAL2 reclassified as explicit proposed D2 siblings requiring their own evidence; and
- explicit narrowing of CuEq TRAIN2 support to FP32. FP64 CuEq TRAIN2 is unsupported pending a future accepted operator relation.

This repair does **not** authorize Candidate 5, CuEq TRAIN2, Stage C, or D3/D4 implementation.

The next gate is a genuinely fresh independent D2 Review pinned to `6e73fbb7af9b8d46f61cf81113259584ffed8527`. Any semantic repair discovered by that Review creates a new candidate identity. Candidate-5 Stage-C evidence may begin only after Review PASS and stakeholder ratification of the exact passing candidate.


## 18. Candidate-5 representation-only correction

After the author-side Candidate-5 repair was frozen, a renderer check found two remaining single-dollar display-math delimiters around the candidate-resolution inequality. The underlying equation, threshold, scope, state semantics, stochastic relation, and every acceptance decision were unchanged.

The representation-only correction produced final immutable Candidate-5 Review target:

`6e73fbb7af9b8d46f61cf81113259584ffed8527`

with canonical blob:

`4bfd2451cc1835e82e303cc9a597b69b8f8deda9`.

The pre-correction Candidate-5 commit `be57964c15ed24e30372de407534efd8173d6bc5` / blob `db0f59e0f9fb81462a18aa6e607ee9deded19c89` is historical only and must not be used as the fresh Review target.

No Stage-C evidence was run between the two representations.


## 19. Candidate-5 independent NO-PASS and Candidate-6 full-trajectory repair

Fresh independent Protocol-6.4 D2 Review R2 of immutable Candidate 5

`6e73fbb7af9b8d46f61cf81113259584ffed8527`

returned **NO-PASS** with no SERIOUS CHALLENGE to accepted D1/D2 parent authority.

Review R2 found nine blocking defects: unsupported `delta*sqrt(u)` error semantics; non-injective optimizer action probes; under-observed EMA state; unsupported recurrence/secant extrapolation; undefined anchor state classes; metadata windows that can omit numerically hard ordinary batches; under-specified finite-sample stochastic authorization; a three-repeat rare-component allowance that can mint candidate tolerance; and under-warranted generic source/DATA6 siblings.

Candidate 6 is the semantic repair. It is frozen at immutable commit:

`f3035317dcea1448c9d6d825c6f2d9f156aaec24`

with Candidate-6 blob:

`f2596ef7bb0f146e6a6ec3b0af44ffcf8b96764a`.

Candidate 6 intentionally narrows rather than broadens authority:

- one exact initial-state/corpus/loader/objective/horizon/runtime/order realization is the qualification unit;
- every accepted TRAIN2 update is executed, eliminating sampled-window and recurrence extrapolation;
- optimizer/EMA latent state is protected only through complete realized-horizon consequences; no arbitrary future-state theorem or mid-run backend conversion is claimed;
- acceptance uses an explicit nonparametric reference-self population tolerance construction rather than Huber-derived or machine-epsilon-derived physical thresholds;
- rare components and broad shifts are part of fixed full-horizon score families;
- generic source/DATA6 CuEq authority is removed from this candidate;
- FP32 remains the sole proposed CuEq TRAIN2 dtype; FP64 remains unsupported;
- completed-state projection retains a distinct structural mapping oracle and evaluator-parity relation; and
- post-projection EVAL2 executes e3nn.

Candidate 6 remains **proposed, not accepted**.

No Candidate-6 Stage-C evidence may run before a fresh independent Review passes and the exact passing immutable candidate receives stakeholder ratification.

No D2-to-D3/D4 handoff exists yet.


## 20. Candidate-6 independent NO-PASS and Candidate-7 repair obligations

Fresh independent Protocol-6.4 D2 Review R3 of immutable Candidate 6

`f3035317dcea1448c9d6d825c6f2d9f156aaec24`

with frozen Candidate-6 blob

`f2596ef7bb0f146e6a6ec3b0af44ffcf8b96764a`

returned **NO-PASS** with **no SERIOUS CHALLENGE to accepted D1/D2 parent authority**.

The independent Review record is:

`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R3.md`

at lifecycle commit:

`ffa521096376bcee66c3ebe867022613c476243d`.

Candidate 6 remains immutable historical candidate state and MUST NOT be edited, reinterpreted, or continued under the same candidate identity. No Candidate-6 Stage-C qualification may run, and no Candidate-6 CuEq outcome may be used to formulate or tune its replacement.

Review R3 found four blocking D2 defects:

1. **Incomplete authorizing consequence / final-state false-pass route.** The loss/live/EMA/RMS score set is not injective over the completed portable training state or the downstream continuous EVAL2/monitor consequences Candidate 6 claims to protect. A final-step state defect can remain invisible on the finite witness corpus and exact discrete decisions, survive a correct CuEq-to-e3nn projection, and alter a held-out EVAL2 configuration.

2. **Reference-maximum envelope is not a backend-equivalence relation.** A rare but decision-stable e3nn self excursion can set a large sample-maximum tolerance and allow a systematically shifted candidate distribution to pass. The replacement must separate reference numerical adequacy from candidate equivalence and must reject the explicit reference (0/M) mixture versus candidate constant (M/2) adversary without tuning from Candidate outcomes.

3. **ULP ordering is not uniquely defined around signed zero.** Candidate 6 does not normatively define one exact finite-value IEEE rank map after collapsing signed zero. Candidate 7 must define the exact rank/distance function and boundary fixtures for signed zero, subnormals, normal/subnormal transition, exponent boundaries, dtype identity, NaN, and infinity.

4. **Projection-oracle independence is under-specified against the actual pinned MACE converters.** Excluding only the primary mapper and its generated mapping table still allows the oracle to share key-correspondence, pair-enumeration, `get_kmax_pairs`, or projection-matrix semantic owners. Candidate 7 must independently derive source/destination inventories and semantic correspondences, include forward-affecting non-`state_dict` state such as `avg_num_neighbors` where applicable, reconcile exact inventory cardinality, and reject common-mode omission/permutation/contraction defects.

The Review also found one finite-sample derivation correction that MUST be repaired in Candidate 7:

- the reference-side cardinalities remain valid: (n_{ref}=44) is conservative for (J=4), (Gamma=0.90), (Kappa=0.95), and (n_P=36) is sufficient for (J_P=2);
- the Candidate-6 prose does **not** obtain its joint candidate-process claim by applying the same per-family Bonferroni argument;
- because every Candidate-6 confirmation process already requires all four families to pass simultaneously, zero occurrences of the joint event “any family exceeds” in 44 independent candidate processes gives the correct exact one-sided 95% process-level bound and does not itself require a larger (n_C);
- reference-calibration confidence and candidate-confirmation confidence remain separate inferential statements and MUST NOT be silently combined into a single 95% joint guarantee.

### Candidate-7 mandatory repair contract

The next semantic candidate MUST be Candidate 7 or later and MUST, before a new immutable freeze:

1. preserve the exact-realization narrowing, complete accepted TRAIN2 horizon, same-backend restart semantics, FP64 CuEq TRAIN2 fail-closed behavior, source/DATA6 e3nn narrowing, and routine-doctor non-authorizing role unless separately falsified;
2. protect the completed live/EMA state or the complete actual downstream continuous consumer domain in a common portable coordinate strongly enough that a final-step hidden-state difference cannot authorize EVAL2/publication;
3. replace sample-maximum containment as the substantive definition of backend equivalence with a predeclared reference-adequacy plus candidate-comparison construction that rejects systematic candidate shifts while retaining explicit finite-sample semantics;
4. define an exact unambiguous IEEE ULP rank/distance primitive;
5. strengthen the projection structural oracle so it shares no semantic inventory/correspondence/pair-enumeration/projection owner with the production mapper and accounts for all forward-affecting state;
6. correct the candidate-side finite-sample statement using the joint process-level exceedance event or another independently derived replacement relation;
7. carry forward exact scientific-decision equality as a hard condition that cannot be rescued by stochastic numerical acceptance;
8. remain prospective: no Candidate-6 Stage-C outcome may select thresholds, witnesses, process counts, score families, or repair form; and
9. undergo a new genuinely fresh independent D2 Review after immutable freeze and then exact stakeholder ratification before any Stage-C evidence is run.

No D3/D4 implementation handoff exists while these D2 blockers remain.


## 21. Candidate-7 repair and immutable Review freeze

Candidate-6 independent Review R3 returned NO-PASS at:

ffa521096376bcee66c3ebe867022613c476243d

with no SERIOUS CHALLENGE to accepted parent D1/D2.

The D2 repair is Candidate 7. Its immutable semantic Review target is:

499b1269590db7c8636b32e6c2dd5cebb05ac602

with Candidate-7 blob:

d5e1c72d6cb4c35027e0f43f502f0da48819af3d.

The earlier author draft 85b41f6954d87175a44bfc2c16e369a5385e8d33 is historical authoring state only. Before freeze, the author-side Challenge pass corrected the realization key to bind the ordered backend-kernel pair (K_R,K_C), replaced globally dilutable RMS with fixed semantic-block RMS, and clarified that TRAIN2 E-consumer comparison uses the same portable e3nn provider on both reference and projected-candidate states.

Candidate 7 repairs the live R3 blockers as follows:

1. **complete-state consequence:** complete forward-affecting live and EMA state is projected to the common e3nn coordinate after every required mutation, including the final optimizer update; exact role-effective downstream consumer population E is part of the key and protected trace;
2. **systematic-shift semantics:** 101 prospective independent R1/R2/C triplets replace sample-maximum containment as the substantive relation; for both S_max and block-balanced S_rms the exact one-sided Clopper-Pearson upper bound on strict-worse probability must be <=0.60 at simultaneous confidence >=0.95;
3. **separate tail guard:** the reference sample maximum remains only a catastrophic-tail guard and cannot rescue a failed systematic-shift relation;
4. **reference adequacy:** accepted threshold and ordering geometry supplies the reference-stability margin; unstable e3nn self behavior fails rather than widening candidate authority;
5. **exact ULP:** signed zero is quotiented to one exact IEEE rank with explicit subnormal/normal semantics;
6. **projection independence:** the oracle cannot share inventory, correspondence, k-range, key-enumeration, projection-matrix, get_kmax_pairs, or symmetric_contraction_proj semantic owners with production;
7. **complete projection inventory:** forward-affecting non-state_dict state, including avg_num_neighbors where applicable, is mandatory;
8. **floating projection bound:** coefficient-representation error is explicit in addition to learned-dtype accumulation error;
9. **scope preserved:** complete real loader/horizon, same-backend restart only, source/DATA6 e3nn narrowing, FP64 CuEq TRAIN2 fail-closed, e3nn EVAL2 provider, and non-authorizing routine doctor remain intact.

Project Engineering Memory was consulted as evidence context. Candidate 7 preserves the materially applicable lessons without treating them as normative authority: authenticated identity/state boundaries (SP-002), immutable restart/reuse boundaries (SP-003), real-owner/target-host qualification (SP-004), architecture-reconstruction drift including avg_num_neighbors/CuEq realization (FF-001), and restart-boundary ownership (FF-002).

The fresh independent handoff is:

workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_HANDOFF_C7.md

No Candidate-7 Stage-C evidence may run before a fresh independent Review PASS and stakeholder ratification of the exact immutable candidate above.

No D2-to-D3/D4 handoff exists yet.

Any semantic repair discovered by that Review creates Candidate 8 or later.


## 22. Candidate-7 independent NO-PASS and Candidate-8-or-later repair obligations

Fresh independent Protocol-6.4 D2 Review R4 of immutable Candidate 7

\`499b1269590db7c8636b32e6c2dd5cebb05ac602\`

with frozen Candidate-7 blob

\`d5e1c72d6cb4c35027e0f43f502f0da48819af3d\`

returned **NO-PASS** with **no SERIOUS CHALLENGE to accepted D1/D2 parent authority**.

The independent Review record is:

\`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R4.md\`

at lifecycle commit:

\`309e5221f9869e6767ae642f1dd0c435ba397ef9\`.

Candidate 7 remains immutable historical candidate state and MUST NOT be edited, reinterpreted, or continued under the same candidate identity. No Candidate-7 Stage-C qualification may run, and no Candidate-7 CuEq outcome may be used to formulate or tune its replacement.

Review R4 confirms that Candidate 7 closes important Candidate-6 defects:

- final-step portable-state observability is complete in the proposed scope;
- complete forward-affecting inventory includes ordinary state such as \`avg_num_neighbors\`;
- latent optimizer handling is narrowed correctly to realized-horizon consequences rather than invalid cross-basis state equality;
- the IEEE binary32 ULP rank is unambiguous across signed zero/subnormals/normals;
- explicit production/oracle semantic-owner sharing exposed by R3 is prohibited;
- generic source/DATA6 CuEq remains outside authority;
- FP64 CuEq TRAIN2 remains fail-closed;
- same-backend restart remains distinct from forbidden cross-backend restart; and
- EVAL2 remains e3nn after completed-state projection.

However, Review R4 found five blocking D2 defects in the replacement relation:

1. **Unjustified stochastic noninferiority margin.** The derivation \(\Gamma=0.90\Rightarrow\eta=0.10\Rightarrow p_{\max}=0.60\) repurposes Candidate-6's reference-content target as a sign-test noninferiority slack without a source-closed theorem or accepted scientific/numerical warrant. The \(1/2\) exchangeability baseline is meaningful; the added \(0.10\) is not derived.

2. **Inference/model mismatch across launch-order strata.** The six fixed launch permutations are prospectively counterbalanced, but Stage-A evidence shows order/process effects are material. If the Bernoulli worse probabilities vary by schedule stratum, the sum is Poisson-binomial rather than Binomial(101,p), so ordinary Clopper-Pearson is not exact. Candidate 8 must either qualify one material order per exact key, explicitly randomize a nuisance population, or use a confidence construction valid for the actual stratified design.

3. **Continuous reference adequacy and candidate catastrophic-tail population risk are not closed.** Threshold/order margins protect discrete decision stability but permit arbitrarily large decision-stable continuous self noise. The sample maximum is only an observed-sample tail guard and gives no candidate-tail population guarantee; rare severe candidate failures can be missed with high probability.

4. **Semantic-block RMS remains representation/dimension sensitive.** One serialized tensor per block prevents cross-tensor dilution but not dilution inside one very large state item. The partition must be derived from accepted representation/forward semantics or replaced by another non-dilutable consequence relation; outcome-selected block splitting is forbidden.

5. **Floating projection coefficient error self-authorizes.** The current bound includes the full observed term \(|\widehat A-A^\ast||x|\) on the allowed side. A grossly wrong production matrix can therefore pass if it is evaluated accurately. Candidate 8 must bind an exact independent semantic owner for \(A^\ast\), derive a prospective coefficient-construction error bound, require \(\widehat A\) to satisfy that bound, and propagate only the justified bound rather than the full observed coefficient error.

The exact Clopper-Pearson arithmetic itself was independently verified for a genuine Binomial(101,p) model:

- \(X=50\): one-sided \(\alpha_j=0.025\) upper bound \(0.5963569324904932<0.60\);
- \(X=51\): upper bound \(0.6059600394771283>0.60\).

Bonferroni across the two score families is valid if each underlying per-family confidence statement is valid. The arithmetic does not repair the design/model mismatch above.

The Review-R3 adversary \(\Pr(S_{RR}=0)=0.90\), \(\Pr(S_{RR}=M)=0.10\), \(S_{RC}=M/2\) is rejected by Candidate 7's sign rule under the intended binomial model; this successful adversary closure does not validate the unsupported \(0.60\) margin generally.

### Candidate-8-or-later mandatory repair contract

The next semantic candidate MUST be Candidate 8 or later and MUST, before a new immutable freeze:

1. preserve Candidate 7 unchanged as historical evidence;
2. preserve exact-realization scope, complete accepted TRAIN2 horizon, complete live/EMA portable-state observation, exact E currentness/leakage restrictions, exact scientific-decision equality, same-backend restart, source/DATA6 e3nn narrowing, FP64 TRAIN2 fail-closed behavior, e3nn EVAL2 identity, and routine-doctor non-authorizing role unless separately falsified;
3. derive the candidate stochastic noninferiority/equivalence proposition from accepted D2 consequence semantics and remove any unsupported relabeling of \(\Gamma\);
4. make launch-order/randomization/stratification part of an explicit population model and use an exact/valid confidence procedure for that model;
5. define continuous reference adequacy and catastrophic candidate-tail severity/probability semantics prospectively, or replace sampling authority with a structural bound that rules out the relevant tail mechanism;
6. define semantic blocks from accepted representation mathematics/forward ownership, or replace \(S_{\rm rms}\) with a source-closed non-dilutable broad-displacement relation;
7. bind an exact independent semantic source for every nontrivial projection transform \(A^\ast\), derive a prospective coefficient-construction error budget including conditioning/pseudoinverse/rounding semantics, require production coefficients to satisfy it, and ensure wrong matrices cannot pass by self-allowance;
8. restate completed-state projection evaluator qualification under the repaired stochastic/tail relation;
9. preserve structural-oracle failure as dominant: evaluator agreement may never rescue inventory/correspondence/transform failure;
10. keep the repair prospective: no Candidate-7 Stage-C outcome may select margins, blocks, process counts, tail policy, transform bounds, randomization law, or repair form;
11. freeze a new immutable Candidate 8 or later and perform a genuinely fresh independent D2 Review; and
12. require exact stakeholder ratification of that passing immutable candidate before any Stage-C qualification, with D3/D4 remaining blocked until then.

No D2-to-D3/D4 handoff exists while these blockers remain.


## 23. Candidate-8 author repair after independent Review R4

Independent Review R4 at \`309e5221f9869e6767ae642f1dd0c435ba397ef9\` returned NO-PASS for immutable Candidate 7 with no SERIOUS CHALLENGE to accepted parent D1/D2.

Candidate 8 is the proposed semantic repair:

\`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_8.md\`.

Its repair record is:

\`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_8_REPAIR.md\`.

The repair contract is:

1. remove the unsupported \`Gamma -> eta -> p_max\` derivation;
2. expose \(\eta_{\rm NI}\) and \(q_{\rm cat}\) as explicit stakeholder-ratified method coordinates with no defaults and bind exact \(n\) prospectively;
3. require \(0\le\eta_{\rm NI}\le q_{\rm cat}<0.10\), with the strict \(0.10\) ceiling serving only to exclude the known 10%-material-instability R3 adversary from the admissible family;
4. replace the fixed six-launch cycle with independent uniform qualification-only permutation draws so exact binomial inference has a declared i.i.d. nuisance-mixture population;
5. define source-owned materiality/equivalence relation \(\mathcal R_e\) for every governed continuous consumer and fail closed when none exists;
6. replace reference/sample-maximum tail semantics with explicit zero-event reference/candidate population-risk bounds no larger than ratified \(q_{\rm cat}\);
7. choose the complete-actual-consumer R3 closure path and stop treating raw parameter ULP magnitude as scientific materiality;
8. replace block RMS with exact non-dilutable ULP mass \(S_{\Sigma}\);
9. retain \(S_{\max}\) for rare coordinates;
10. define semantic projection matrix \(A^\ast\) independently from accepted representation equations;
11. require production coefficients to equal the correctly rounded semantic coefficients exactly before output error is evaluated;
12. propagate only learned-dtype accumulation plus certified coefficient-rounding error;
13. keep structural oracle failure dominant over evaluator agreement;
14. preserve accepted loader/restart/source-DATA6/FP64/doctor/e3nn-EVAL2 closures; and
15. freeze Candidate 8 before fresh independent Review.

No Candidate-8 Stage-C evidence exists. Stage C and D3/D4 remain blocked.


## 24. Candidate-8 immutable Review freeze

Candidate 8 is frozen for fresh independent D2 Review at:

\`c6e18ccfce62d47e96dde80600558522c62c28ef\`

with Candidate-8 blob:

\`60598fa33048df16f9cc41e6adf761dd952aa28f\`.

The pre-freeze author drafts

- \`07c273a4e5ec382ed84204af73bd97fe08f5cd34\`; and
- \`d3f4cbbadbf86553361be756c31e372478a338de\`

are historical authoring state only and are not Review targets.

Candidate 8 is a parameterized D2 method family. The semantic family is frozen; no Stage-C instance exists yet. Exact stakeholder ratification after independent PASS must bind \(\eta_{\rm NI}\), \(q_{\rm cat}\), \(n\), exact \(E\), and every accepted materiality source \(\mathcal R_e\) before Stage C.

The fresh independent handoff is:

\`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_HANDOFF_C8.md\`.

No Candidate-8 Stage-C evidence may run before fresh independent Review PASS plus exact stakeholder instance ratification.

No D2-to-D3/D4 handoff exists.


## 25. Candidate-8 independent NO-PASS and Candidate-9 repair obligations

Fresh independent Protocol-6.4 D2 Review R5 of immutable Candidate 8

\`c6e18ccfce62d47e96dde80600558522c62c28ef\`

with frozen Candidate-8 blob

\`60598fa33048df16f9cc41e6adf761dd952aa28f\`

returned **NO-PASS** with **no SERIOUS CHALLENGE to accepted parent D1/D2 authority**.

The independent Review record is:

\`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R5.md\`

at lifecycle commit:

\`a4c170674b2beb1df57ee56a32777cc2e58a1060\`.

Candidate 8 remains immutable historical candidate state and MUST NOT be edited, reinterpreted, or continued under the same candidate identity. No Candidate-8 Stage-C qualification may run, and no Candidate-8 CuEq outcome may be used to formulate or tune its replacement.

Review R5 confirms that Candidate 8 closes or fail-closes the prior R4 defect families for:

- explicit stakeholder-owned risk coordinates with no generated default;
- complete actual-consumer closure and final completed-state consequence;
- source-owned continuous materiality relations and joint population-risk events;
- exact signed-zero/dtype-aware ULP semantics;
- non-dilutable \(S_{\max}\) plus exact unnormalized \(S_{\Sigma}\);
- complete forward-affecting structural inventory;
- independent projection semantic ownership;
- exact correctly rounded production coefficient qualification;
- reduced-CG/non-unique inverse fail-closed behavior;
- exact scientific-decision preservation;
- source/DATA6 narrowing;
- FP64 TRAIN2 fail-closed scope; and
- non-authorizing routine doctor.

However, R5 found one blocking D2 defect in the replacement stochastic relation.

### Candidate-9 mandatory repair contract

1. Preserve Candidate 8 unchanged as historical evidence and preserve all R5-passed repairs unless separately falsified.
2. Repair the triplet null at the **pre-assignment/marginal randomization level**. Do not assert that \(R2\) and \(C\) are exchangeable conditional on a realized launch-order permutation when that permutation fixes different launch positions.
3. Introduce an explicit pre-assignment triplet nuisance state \(\Lambda_p\), then draw the \(R1/R2/C\) assignment independently from the exact uniform six-permutation law after \(\Lambda_p\) is fixed.
4. State the backend-equivalence null as \(R2/C\) label-exchange invariance of the relevant potential-response/consumer-score law under that prospective randomization. Prove the resulting marginal strict-worse probability is at most \(1/2\), including discrete/tied cases, or replace Binomial Clopper-Pearson with an exact/conservative procedure valid for the actual final design.
5. Separate **randomization-policy identity** from the **realized assignment sequence**. Currentness/evidence may bind both, but the inferential population may not condition away the design randomness whose averaging justifies the Bernoulli model.
6. Resolve persistent target-host state explicitly. CUDA/driver/compiler cache, allocator/residency, clocks/thermal state, autotuning, filesystem/page cache, and teardown state must either be reset/isolated sufficiently to establish common independent triplet law, represented prospectively as nuisance/block state with valid inference, or cause qualification to fail closed.
7. Define child startup failure, OOM, timeout, crash, nonfinite execution, warm-up behavior, and infrastructure failure prospectively so no outcome-dependent discard/redraw or retry-until-pass path exists.
8. Apply the same repaired randomization/null theorem to the completed-state projection evaluator relation.
9. Keep the existing \(\eta_{\rm NI}\), \(q_{\rm cat}\), \(n\), exact \(E\), and \(\{\mathcal R_e\}\) coordinates prospective and outcome-independent. Do not select any of them from Candidate-8 outcomes.
10. Freeze the repair as Candidate 9 or later and perform a genuinely fresh independent D2 Review before stakeholder instance ratification.
11. Do not run Candidate-8 Stage C.
12. Keep D3/D4 blocked until a future immutable D2 candidate passes independent Review, receives exact stakeholder instance ratification, and then passes fresh Stage-C qualification.

The exact counterexample that Candidate 9 must close is an **identical-backend, order-only null**: let launch positions carry deterministic nuisance values \(h=(0,1,2)\) and pair score be absolute difference. In fixed stratum \((R1,R2,C)\), \(S^{RR}=1\) and \(S^{RC}=2\), so conditional exchangeability fails even though \(C\) is literally the same backend. Under a uniform random assignment over all six permutations, the strict-worse indicators are \((1,0,0,0,0,1)\), showing that the relevant symmetry exists only after averaging over the assignment law.

No D2-to-D3/D4 handoff exists while this blocker remains.



Fresh independent Protocol-6.4 D2 Review R5 of immutable Candidate 8

`c6e18ccfce62d47e96dde80600558522c62c28ef`

with frozen Candidate-8 blob

`60598fa33048df16f9cc41e6adf761dd952aa28f`

returned **NO-PASS** with **no SERIOUS CHALLENGE to accepted parent D1/D2 authority**.

The independent Review record is:

`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R5.md`

at lifecycle commit:

`a4c170674b2beb1df57ee56a32777cc2e58a1060`.

Candidate 8 remains immutable historical candidate state and MUST NOT be edited, reinterpreted, or continued under the same candidate identity. No Candidate-8 Stage-C qualification may run, and no Candidate-8 CuEq outcome may be used to formulate or tune its replacement.

Review R5 confirms that Candidate 8 closes or fail-closes the prior R4 defect families for:

- explicit stakeholder-owned risk coordinates with no generated default;
- complete actual-consumer closure and final completed-state consequence;
- source-owned continuous materiality relations and joint population-risk events;
- exact signed-zero/dtype-aware ULP semantics;
- non-dilutable `S_max` plus exact unnormalized `S_Sigma`;
- complete forward-affecting structural inventory;
- independent projection semantic ownership;
- exact correctly rounded production coefficient qualification;
- reduced-CG/non-unique inverse fail-closed behavior;
- exact scientific-decision preservation;
- source/DATA6 narrowing;
- FP64 TRAIN2 fail-closed scope; and
- non-authorizing routine doctor.

However, R5 found one blocking D2 defect in the replacement stochastic relation.

### Candidate-9 mandatory repair contract

1. Preserve Candidate 8 unchanged as historical evidence and preserve all R5-passed repairs unless separately falsified.
2. Repair the triplet null at the **pre-assignment/marginal randomization level**. Do not assert that `R2` and `C` are exchangeable conditional on a realized launch-order permutation when that permutation fixes different launch positions.
3. Introduce an explicit pre-assignment triplet nuisance state (Lambda_p), then draw the `R1/R2/C` assignment independently from the exact uniform six-permutation law after (Lambda_p) is fixed.
4. State the backend-equivalence null as `R2/C` label-exchange invariance of the relevant potential-response/consumer-score law under that prospective randomization. Prove the resulting marginal strict-worse probability is at most (	frac12), including discrete/tied cases, or replace Binomial Clopper-Pearson with an exact/conservative procedure valid for the actual final design.
5. Separate **randomization-policy identity** from the **realized assignment sequence**. Currentness/evidence may bind both, but the inferential population may not condition away the design randomness whose averaging justifies the Bernoulli model.
6. Resolve persistent target-host state explicitly. CUDA/driver/compiler cache, allocator/residency, clocks/thermal state, autotuning, filesystem/page cache, and teardown state must either be reset/isolated sufficiently to establish common independent triplet law, represented prospectively as nuisance/block state with valid inference, or cause qualification to fail closed.
7. Define child startup failure, OOM, timeout, crash, nonfinite execution, warm-up behavior, and infrastructure failure prospectively so no outcome-dependent discard/redraw or retry-until-pass path exists.
8. Apply the same repaired randomization/null theorem to the completed-state projection evaluator relation.
9. Keep the existing (eta_{m NI}), (q_{m cat}), (n), exact `E`, and ({R_e}) coordinates prospective and outcome-independent. Do not select any of them from Candidate-8 outcomes.
10. Freeze the repair as Candidate 9 or later and perform a genuinely fresh independent D2 Review before stakeholder instance ratification.
11. Do not run Candidate-8 Stage C.
12. Keep D3/D4 blocked until a future immutable D2 candidate passes independent Review, receives exact stakeholder instance ratification, and then passes fresh Stage-C qualification.

The exact counterexample that Candidate 9 must close is an **identical-backend, order-only null**: let launch positions carry deterministic nuisance values (h=(0,1,2)) and pair score be absolute difference. In fixed stratum ((R1,R2,C)), (S^{RR}=1) and (S^{RC}=2), so conditional exchangeability fails even though `C` is literally the same backend. Under a uniform random assignment over all six permutations, the strict-worse indicators are ((1,0,0,0,0,1)), showing that the relevant symmetry exists only after averaging over the assignment law.

No D2-to-D3/D4 handoff exists while this blocker remains.

## 26. Candidate-9 author repair after independent Review R5

Candidate 9 is the proposed semantic repair:

\`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_9.md\`.

Its repair record is:

\`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_9_REPAIR.md\`.

The repair contract is:

1. preserve every Candidate-8 surface passed by Review R5;
2. replace fixed-stratum conditional exchangeability with a pre-assignment label-exchange theorem marginalized over uniform random assignment;
3. define exact pre-assignment nuisance state \(\Lambda_p\);
4. bind one renewal/start-state contract \(\mathcal W\) that establishes a common independent fresh-start law across triplets or fail closed;
5. bind prospective design-policy identity \(\mathcal Q\) rather than realized randomization seed/permutations into the method key;
6. retain realized entropy/seed/permutations as auditable evidence-realization identity;
7. prohibit adaptive warm-up, discarded unfavorable triplets, redraw/reassignment, and same-key retry-until-pass;
8. define child/infrastructure failure prospectively and keep failed/incomplete evidence visible;
9. retain exact Binomial/Clopper-Pearson inference only under the repaired common independent renewal law;
10. apply the same theorem to projection evaluator qualification;
11. add the R5 identical-backend/order-only \(h=(0,1,2)\) fixture as a mandatory Stage-C falsification; and
12. freeze Candidate 9 before fresh independent Review.

No Candidate-9 Stage-C evidence exists. Stage C and D3/D4 remain blocked.

### Candidate-9 prefreeze author-side correction

Before immutable freeze, the assembled Candidate-9 challenge pass removed a stale duplicated Candidate-8 closing tail and made two already-required implications explicit:

- post-assignment stochastic state that can correlate triplets must be independently regenerated under the renewal contract or represented in the renewal state; otherwise the Candidate-9 i.i.d. model fails closed;
- \(\eta_{\rm NI}\) is a qualification-comparison probability under the randomized design and cannot stand in for \(q_{\rm cat}\).

These are included in the semantic Candidate-9 target before freeze. No Stage-C evidence exists.

The final prefreeze challenge additionally requires owner-based renewal evidence: statistical stationarity/autocorrelation diagnostics are falsification aids only and cannot by themselves establish the common independent triplet law.

## 27. Candidate-9 immutable Review freeze

Candidate 9 is frozen for fresh independent D2 Review at:

\`d288d0f931b36e0304a91312915b9785e07dbe3c\`

with Candidate-9 blob:

\`7fbe754c60fab953453586619c8ecb21d8a2b9cc\`.

The prefreeze author states

- \`2a5317558cf3d32455617e5f07efa97c31ef0afe\`; and
- \`4fc493d53b225a36682937e0c8d6659619adc5db\`

are historical authoring state only and are not Review targets.

Candidate 9 preserves Candidate 8's R5-passed consumer/materiality/ULP/projection/scope repairs and replaces only the blocked stochastic conditioning semantics. Its authorizing randomization theorem is now pre-assignment and marginal over the uniform \(R1/R2/C\) assignment; its exact Binomial/Clopper-Pearson claims are available only under the prospectively bound owner-based renewal/common-law contract.

Candidate 9 is a parameterized D2 method family. The semantic family is frozen; no Stage-C instance exists yet. Exact stakeholder ratification after independent PASS must bind \(\eta_{\rm NI}\), \(q_{\rm cat}\), \(n\), exact \(E\), every accepted materiality source \(\mathcal R_e\), and exact design/renewal policy \(\mathcal Q\).

The fresh independent handoff is:

\`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_HANDOFF_C9.md\`.

No Candidate-9 Stage-C evidence may run before fresh independent Review PASS plus exact stakeholder instance ratification.

No D2-to-D3/D4 handoff exists.

## 28. Candidate-9 independent NO-PASS and Candidate-10 production-population repair obligation

Fresh independent Protocol-6.4 D2 Review R6 of immutable Candidate 9

\`d288d0f931b36e0304a91312915b9785e07dbe3c\`

with frozen Candidate-9 blob

\`7fbe754c60fab953453586619c8ecb21d8a2b9cc\`

returned **NO-PASS** with **no SERIOUS CHALLENGE to accepted parent D1/D2 authority**.

The independent Review record is:

\`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R6.md\`.

Review R6 confirms that Candidate 9 correctly closes Review R5's fixed-stratum conditional-exchangeability defect. The pre-assignment label-swap theorem, uniform assignment marginalization, separation of prospective \(\mathcal Q\) from realized assignments, owner-based \(\mathcal W\) common-law requirement, and exact Binomial/Clopper-Pearson inference are coherent for the randomized qualification population.

One new blocking D2 defect remains: **production-population transport**.

Candidate 9 defines candidate materiality risk over a qualification-only uniform mixture of the three launch slots after one triplet renewal boundary. A passing record is then allowed to authorize an ordinary single CuEq production launch merely because its pre-assignment production-start predicates belong to the \(\mathcal W\) envelope. That does not prove that the actual production child-start law equals the randomized candidate slot-mixture law.

The exact R6 counterexample uses an admissible \(q_{\rm cat}=0.08\). If candidate materiality probabilities by qualification slot are \(0.20,0,0\), uniform assignment gives qualification risk \(0.066\overline6<0.08\), while an ordinary single cold/fresh production launch corresponding to slot 1 has risk \(0.20>0.08\). The qualification population proposition can be true and can pass exact finite-sample confidence, yet the authorized production proposition is false.

### Candidate-10 mandatory repair contract

1. Preserve Candidate 9 unchanged as immutable historical candidate state and preserve all C9 surfaces R6 found adequate unless independently falsified.
2. Define the exact production CuEq child-start probability law \(P_{\rm prod}\) at the boundary immediately before TRAIN2 arithmetic begins.
3. Define the exact candidate-start law induced by qualification renewal, launch slots and assignment.
4. Prove prospectively that the \(q_{\rm cat}\) materiality-event law used for qualification is identical to, or conservatively dominates, the actual production-start event law.
5. Do not treat membership in the pre-assignment renewal envelope as sufficient transport when earlier qualification children can change cache/residency/thermal/other ambient state before a later candidate child starts.
6. Prefer reduction at the renewal owner: make every qualification child begin from an independently renewed/authenticated production-equivalent state before label-dependent arithmetic, if that can be established on the target host.
7. If slot-specific state cannot be eliminated, either bind production to the same prospective slot-mixture law or define a separately reviewed per-stratum/worst-case materiality inference with valid simultaneous confidence and prospectively fixed sample allocation.
8. Never average a high-risk production-relevant stratum with lower-risk qualification-only strata to meet \(q_{\rm cat}\).
9. The R5 marginal assignment theorem may remain the systematic-comparison owner for \(\eta_{\rm NI}\), but it cannot itself transport catastrophic-tail risk to production.
10. Apply the same actual-start population-transport rule to the projection evaluator wherever evaluator \(q_{\rm cat}\) authorizes a fixed real evaluator/projection regime.
11. Add a mandatory Stage-C adversary with slot risks \(0.20,0,0\), mixture risk below a bound such as \(q_{\rm cat}=0.08\), and production using the high-risk slot; authorization must fail.
12. Do not run Candidate-9 Stage C and do not use Candidate-9 outcomes to choose Candidate-10 transport semantics, risk values, sample allocation, renewal policy or estimator.
13. Freeze any semantic repair as Candidate 10 or later and perform a fresh independent D2 Review.
14. Keep D3/D4 blocked until a future immutable D2 candidate passes independent Review, receives exact stakeholder instance ratification, and subsequently passes fresh Stage-C qualification.

No Candidate-9 Stage-C evidence is authorized.

