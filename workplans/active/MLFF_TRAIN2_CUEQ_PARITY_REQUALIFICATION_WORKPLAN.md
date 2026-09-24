---
kind: abstraction-concretization-change-plan
protocol_version: 6.4.0
status: active-serious-challenge
workplan_id: MLFF-TRAIN2-CUEQ-PARITY-REQUALIFICATION
created_date: 2026-09-24
revision: 6
reviewed_date: 2026-09-24
workplan_review_status: PASS_AS_WORKPLAN_AFTER_R5_REPAIR
workplan_review_basis: c14c153c2c44bd52e6c2532a201819dd3f2ba673
accepted_d1_d2_baseline: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_d1_d2_source_target: a4824d28775164aa942fd29fa97ee0957eb87e6f
branch: design/mlff-train2-cueq-parity-requalification
basis_commit: af89c30ca5304c4dd71ff82b779db973ce0006f8
highest_potentially_affected_domain: D2
d1_change_expected: false
human_ratification_required_for_d2_mutation: true
production_default_during_repair: e3nn
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

This review also confirmed an authority-provenance defect that must be resolved before changing any tolerance. The accepted Protocol-6.4 D2 kernel is `a759e81...`, importing exact source `a4824d2...`; it states that backend-observed discrepancy or an unlisted tolerance cannot create a new numerical-equivalence relation. Direct inspection of the exact accepted source finds no CuEq-specific relation and no FP32 parity rule. The Rev86 CuEq parity document is now classified by the current D4 specification index as historical/backend-qualification material rather than a current semantic owner. Therefore the current CuEq acceleration-equivalence family is **not source-closed as accepted D2 authority under the current Protocol-6.4 kernel**. The immediate adequacy challenge is specific to TRAIN2 FP32, but the same formalization omission also covers the existing source/DATA6 FP32 relation and FP64 CuEq relation. This cycle must formally source-close the current role/dtype family. Numerical changes outside TRAIN2 FP32 are not authorized unless those existing relations are independently falsified.

The current runtime behavior remains the fail-closed baseline until a replacement relation is accepted. D3/D4 MUST continue to fail closed under the existing policy in the meantime. No threshold widening, retry-until-pass behavior, silent e3nn fallback, or MH-1-specific bypass is authorized.

Operationally, the accepted safe production route during this repair is the existing explicit `e3nn` TRAIN2 path. CuEq remains opt-in and non-authorizing when its parity gate fails.

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

This is not initially a D4 doctor bug. The current doctor correctly realizes the accepted gate. D3/D4 modification is downstream work only after the D2 criterion is accepted, unless independent evidence first proves that the observed metrics themselves are incorrectly computed.

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
7. **FP32 scope is explicit.** This work does not relax FP64 authority.
8. **No family-specific exception without D2 justification.** Do not add an `if MH-1` tolerance branch merely because this realization failed.
9. **No auto-calibration from the candidate being judged.** A candidate run may supply repeatability evidence under a predeclared method, but its observed cross discrepancy cannot directly set its own acceptance bound.
9A. **Adjacent parity relations are formalization-frozen.** Source/DATA6 FP32 and FP64 CuEq relations must be brought under explicit D2 source closure because the accepted kernel omitted the entire acceleration-parity surface, but their numerical tolerances/semantics are not changed by this TRAIN2 incident absent separate falsification evidence.
10. **Uncertainty must be represented honestly.** Repeated-pair statistics built from a small number of repeated evaluations are dependent observations; all-pairs cardinality must not be interpreted as an independent-sample count.
11. **Accepted currentness is explicit.** Any changed parity-policy identity must invalidate/remap dependent preflight, handoff, qualification, cache, and provenance records exactly where they bind the old policy digest.
12. **Existing e3nn production path remains admissible.** The repair may not destabilize the current default MH-1 e3nn campaign path.
13. **Authority isolation is hard.** Unrelated proposed D1/D2/D3 renewal artifacts on the repository head are evidence/candidate state only and cannot become parents by path precedence.
13A. **The missing D2 relation is a confirmed closure obligation.** The accepted D2 source does not define CuEq/FP32 parity. D4's Rev86 rule may remain the conservative executable guard during repair, but it cannot be cited as accepted numerical authority until this cycle supplies the source-closed D2 relation through the normal acceptance process.
14. **Parity preflight and CUEQ-PHASE1 have distinct scopes.** Instantaneous E/F/stress/descriptor/FPS evidence is the current per-selected-head/runtime admission screen for explicit CuEq TRAIN2. CUEQ-PHASE1 remains valuable paired-training/FINAL-GPU1 evidence, but Revision 60 explicitly changed campaign policy without retroactively changing the immutable CUEQ-PHASE1 records. Do not falsely make historical phase-1 completion a blanket prerequisite for every current explicit CuEq campaign, and do not claim doctor parity makes the historical phase-1 record pass.
15. **Every parity channel needs a protected consequence.** No internal quantity remains a hard gate merely because it was historically measured; D2 must state which scientific/numerical downstream invariant it protects.
16. **Channel dimensions/scales are explicit.** Energy/atom, force, stress, and latent descriptors have different units/scales. A shared numerical absolute ceiling across unlike channels is inadmissible without an explicit normalization/error derivation.
17. **Qualification currentness is authenticated.** A stored CuEq realization cannot remain current solely because backend/device/dtype/checkpoint match; it must bind the currently accepted parity-policy/method identity and applicable runtime evidence.
18. **Historical records are immutable but non-self-authorizing.** An old record carrying `passed=true` remains historical evidence after a policy/method change and cannot authorize current CuEq use without the accepted remap/requalification rule.
19. **No adaptive retry.** The number/order of independent target-host realizations used for an acceptance decision must be frozen before their outcomes are inspected; pass/fail instability is evidence against a stable authorizing rule, not permission to rerun until pass.

### 2.2 Cycle-scoped decisions

For this repair cycle:

- treat the Rev86 `1e-6/1.25` relation as the **current executable fail-closed rule**, while separately resolving whether it is valid accepted D2 authority;

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

> When may two FP32 TRAIN2 execution backends be treated as numerically equivalent for the scientific decisions that consume their outputs, despite backend- and run-level floating-point reduction variability?

The replacement must discriminate:

`same numerical method under finite-precision execution variability`

from:

`materially different numerical realization capable of changing governed decisions`.

### 3.2 Material dependent surface

At minimum inspect and close:

- accepted D1/D2 kernels and exact imported source target at `a759e81.../a4824d2...`, plus any accepted successor resolved before promotion;
- current role/dtype acceleration parity family: source/DATA6 FP32, selected-head TRAIN2 FP32, source/DATA6 FP64, and TRAIN2 FP64, with only TRAIN2 FP32 numerically challenged by this incident;
- the unrelated proposed D1/D2 renewal currently occupying canonical paths on `main@af89c30...`, for composition/conflict only;
- `docs/specs/training_data/README.md` authority classification;
- historical `docs/specs/training_data/mlff_cueq_train_noise_normalized_parity_spec.md`, Rev83-86 notes, CUEQ-DEFAULT1/HF1/HF2 evidence, and DIAG3 records;
- `mdstats/training_data/acceleration.py`;
- doctor/currentness code in `mdstats/training_data/_campaign_cli_core.py`;
- optimizer/training identity owners that bind `acceleration_realization_digest`, including `mdstats/training_data/protocol.py`, post-selection runtime identities, and target-size execution identities where still current;
- `mdstats/training_data/cueq_phase1.py`, its tool/spec/evidence, and PERF-CERT1 prerequisites;
- `mdstats/training_data/final_gpu1.py` and `tools/run_mlff_final_gpu_qualification.py`;
- FINAL-GPU1 preflight/handoff policy-digest bindings and release-pinned workstation runbooks;
- parity/repeatability/policy/realization record schemas and serializers;
- CampaignStore stage/currentness admission so a pre-change doctor pass cannot survive an authority-policy change;
- focused CuEq parity tests, especially `tests/test_mlff_cueq_train_noise_normalized_parity.py`, DIAG3 tests, default1 tests, FINAL-GPU1 tests, and specification tests;
- MH-1 campaign-default tests to ensure e3nn remains the default;
- frozen release/audit records only as historical evidence; never rewrite them to look current;
- current D3 architecture/dependency documentation and semantic-evolution notes if D2 authority changes.

### 3.3 Unaffected siblings to preserve

Unless new evidence contradicts them:

- CUEQ-PHASE1 paired-training scientific qualification semantics;
- TRAIN2/EVAL2 model-architecture authentication;
- production scheduler/resource budgeting;
- replay-retention and checkpoint-admissibility method;
- final-production publication and P7 deployment ownership.

The **numerical values** of source/DATA6 FP32 and FP64 CuEq parity are presumed unchanged unless separately falsified, but they are not listed as unaffected authorities because the same accepted-D2 source-closure omission applies to them. Include them in the D2 acceleration-equivalence family formalization without using the TRAIN2 failure as a reason to relax them.

“Unaffected” means semantically unaffected, not automatically reusable evidence. A shared runtime/source/policy digest may still make an evidence record stale-dependent; perform the explicit impact projection rather than either invalidating everything or reusing everything.

### 3.4 Project Engineering Memory / Historical Applicability Set

Effective memory basis at plan opening is the accepted `PROJECT-ENGINEERING-MEMORY.md` on `main@af89c30...`, whose accepted-base metadata is itself partial and historically reconciled through `4eabe2ae...` plus the later final-publication candidate overlay.

Materially applicable current lessons:

- **SP-002**: preserve fail-closed authenticated identity/state boundaries;
- **SP-004**: real-owner and target-host qualification can expose defects missed by mocks/control-plane checks;
- TRAIN2/EVAL2 CuEq architecture history: do not confuse backend-parity failure with model-construction/architecture drift without independently checking exact realization identity.

PEM coverage is partial. Absence of a specific historical parity family is not evidence that no relevant prior episode exists. Perform a bounded history search over CuEq/FP32 parity, selected-head MH-1, MPA-0, DIAG3, CUEQ-DEFAULT1, CUEQ-REPEAT1, CUEQ-PHASE1, PERF-CERT1, and FINAL-GPU1 before freezing a replacement criterion.

### 3.5 Qualification hierarchy and claim boundary

The workplan SHALL preserve the distinction among:

1. **runtime/capability identity** — CUEQ-DEP1 and MACE/Torch/CUDA/source compatibility;
2. **current campaign admission** — the selected-head doctor parity/repeatability rule under review here, which current product prose uses to authorize an explicit CuEq TRAIN2 realization fail-closed;
3. **historical/paired training qualification evidence** — CUEQ-PHASE1 short and representative full e3nn-vs-CuEq trajectories with hard-decision preservation;
4. **release/end-to-end certification** — PERF-CERT1/FINAL-GPU1 where applicable.

The authority evolution matters. CUEQ-PHASE1 originally deferred positive accelerator training authorization. Revision 60 (`CUEQ-DEFAULT1`) was an explicit stakeholder/project policy change that made phase-separated CuEq TRAIN2 the generated policy at that time while explicitly preserving the old CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 records and their `generated_default_change_authorized=false` semantics. Later MH-1 CONFIG1 work returned the generated campaign default to e3nn, but current README/runtime behavior still supports **explicit opt-in CuEq** subject to doctor qualification.

Therefore:

- do not require a positive historical CUEQ-PHASE1 record as an invented prerequisite for every current explicit CuEq campaign;
- do not interpret a repaired doctor parity pass as retroactively making CUEQ-PHASE1/FINAL-GPU1 pass;
- when this work affects a release qualification that explicitly includes those gates, reconcile them under their own contracts;
- keep current generated-default policy separate from explicit opt-in authorization.

The D2 candidate must explicitly state the proposition proved by the instantaneous parity gate: bounded numerical admission of the exact selected-head/runtime CuEq realization under current campaign policy. CUEQ-PHASE1 remains useful stronger evidence about multi-epoch trajectory behavior and a falsification source, but it is not silently promoted into the current campaign admission owner.

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
15. stale stored `TrainingAccelerationRealizationRecord` created under an old policy that would otherwise be accepted by backend/device/dtype/checkpoint checks alone;
16. authority-evolution case showing that Rev60 explicit CuEq policy, current e3nn generated default, doctor admission, and historical CUEQ-PHASE1/FINAL-GPU1 state remain distinct rather than being collapsed into one boolean.

### 4.7 Historical evidence is evidence, not authority

Reconstruct why:

- selected-head MH-1 earlier motivated a `2e-6` TRAIN2 FP32 absolute floor;
- MPA-0 later motivated a `1e-5` force ceiling;
- DIAG3 led to the current force noise-normalized criterion and the return of energy/stress/descriptor to `1e-6`.

Determine whether the later generic policy had adequate cross-family evidence for each stable-channel assumption. Do not simply revert to an older constant.

### 4.8 D3/D4 currentness defects to resolve if confirmed

Current inspection confirms that `_stored_training_acceleration_realization(..., require_qualified=True)` authenticates requested backend, device/dtype, checkpoint bytes, and the record's own historical `qualified` flag, but does not authenticate that the record was qualified under the **currently accepted parity-policy/method digest**. Meanwhile optimizer/training identities bind the acceleration-realization digest.

This is a D3/D4 stale-authority defect independent of which new numeric criterion wins. Stage A/D must trace the complete currentness graph for impact and repair the existing owner directly:

- reuse the existing stored parity-policy/parity/realization records;
- make consequential reuse prove the current accepted parity method/policy identity and applicable runtime identity;
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
4. Reconstruct every dependent policy digest/currentness edge through doctor, stored realization, optimizer/training identity, CUEQ-PHASE1, PERF-CERT1 and FINAL-GPU1.
5. Perform the bounded historical CuEq parity/HAS review and classify evidence by provenance: raw realization, derived summary, synthetic fixture, or prose-only claim.
6. Search for the original MPA-0 DIAG3 workstation artifact. If unavailable, do not promote the hardcoded summary fixture into raw evidence.
7. Confirm that the MH-1 observation binds the exact EXTRACT1 selected-head checkpoint and current runtime/source-compatibility evidence.
8. Audit metric semantics: energy/atom, stress convention, descriptor construction, FPS policy, absolute-vs-rtol stable-channel ambiguity, NumPy percentile method, finiteness, and pair counts.
9. Falsify fixed backend-order, warm-up, process-state, corpus-size, and small-tail-resolution effects with bounded diagnostics.
10. Treat the stored-realization currentness defect in Section 4.8 as confirmed at the direct loader boundary and trace whether any upstream stage fence happens to compensate for it; repair the direct consequential-use owner regardless of incidental call ordering.
11. Reconstruct the authority evolution from CUEQ-PHASE1 through Rev60 CUEQ-DEFAULT1 to current CONFIG1/e3nn-generated-default behavior. Record precisely which claims belong to doctor admission, paired-training evidence, generated defaults, and FINAL-GPU1.
12. Confirm that current user-facing/runtime documentation consistently describes explicit opt-in CuEq as doctor-qualified without falsely rewriting immutable CUEQ-PHASE1/FINAL-GPU1 records.
13. If a pure D4 metric defect explains part of the observed failure, repair that owner separately and rerun measurement evidence, but still close the independently confirmed missing-D2 relation and stale-realization currentness gaps.

**Gate A:** proceed to D2 replacement/formalization only when evidence provenance is sufficient, D4 measurement defects are partitioned, the parent authority is unambiguous, and either (a) the accepted relation remains materially challenged or (b) an explicit missing D2 relation must be formally supplied.

### Stage B — Bounded D2 candidate method

1. Define one D2 acceleration-equivalence family with explicit role/dtype applicability. Preserve existing source/DATA6 FP32 and FP64 numerical relations unless separately challenged; isolate the TRAIN2 FP32 method as the changed/challenged member.
2. State the exact proposition of the current doctor TRAIN2 parity admission gate and its relationship to historical CUEQ-PHASE1, Rev60 explicit policy authorization, current generated-default policy, and FINAL-GPU1.
3. Define every governed observable/channel, unit/normalization, and downstream protected consequence.
4. Define the experimental units and whether the TRAIN2 FP32 method is a finite-sample functional or a population estimator.
5. Define the equivalence statistics per justified TRAIN2 FP32 channel, including exact quantile/order-statistic semantics.
6. Define absolute catastrophic guards and protections against inflated/near-zero self-noise.
7. Define exact selection identity/robustness requirements.
8. Define warm-up, repeat, evaluation-order, process-replication, probe-corpus, and insufficiency semantics before seeing acceptance outcomes.
9. Define generic-vs-regime applicability explicitly. Any parameterization must follow a semantically meaningful scale/architecture/runtime coordinate, not a model-family exception table chosen from failures.
10. Define the policy/method digest and realization applicability binding so evidence cannot cross incompatible methods/runtimes.
11. Define old-record currentness/remap semantics and whether record/schema versions must advance.
12. Produce a bounded D2 overlay against the exact accepted parent; do not edit an unrelated unaccepted canonical-path renewal.
13. Write the proposed D2 authority before changing D4 product thresholds.

**Gate B:** candidate method must be source/definition closed, dimensionally/semantically coherent, statistically identifiable at its evidence cardinality, and free of constants selected merely because they pass the new MH-1 observation.

### Stage C — Independent numerical falsification

Exercise the frozen candidate method against:

- authenticated current MPA-0 target-host evidence (fresh if raw historical GPU evidence is unavailable);
- authenticated current MH-1 target-host evidence;
- an evidence corpus adequate for the claimed validity domain;
- synthetic/adversarial counterexamples from Section 4.6;
- predeclared independent process/order realizations sufficient for the chosen estimator semantics;
- applicable deterministic-control diagnostics without substituting them for ordinary production-path evidence.

Freeze the number of repetitions before inspection. A candidate that merely admits both real regimes but cannot reject systematic disagreement is not acceptable; a candidate whose pass/fail flips under the predeclared realizations without a defined probabilistic decision rule is also not acceptable.

**Gate C:** immutable composed D2 candidate, fresh independent D2 Review, and explicit stakeholder ratification of that exact reviewed target.

### Stage D — D3/D4 handoff

Only after Gate C:

1. re-resolve current accepted D3 and avoid editing an unrelated proposed architecture candidate as though accepted;
2. map the accepted D2 relation onto one canonical D4 parity/reducer owner in `acceleration.py`;
3. remove superseded criterion machinery rather than layering a second special-case path;
4. repair stored-realization/stage currentness using existing CampaignStore policy/parity/realization records so an old-policy `qualified=true` cannot authorize current execution;
5. revise record/policy schemas only where method meaning/fields require it; retain historical deserialization without historical authorization;
6. update doctor diagnostics to expose the method, evidence cardinality/applicability and failure reason transparently;
7. update optimizer/training identity only according to the accepted D3 projection; do not force retraining merely because a representation changed, and do not reuse a genuinely changed execution realization;
8. regenerate/rebind FINAL-GPU1 preflight/handoff artifacts rather than mutating a release-pinned handoff whose integrity contract forbids source edits;
9. update policy-digest/currentness dependencies and stale-stage behavior;
10. preserve no-silent-fallback and default-e3nn behavior;
11. preserve the claim boundaries of CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 without inventing them as universal prerequisites for explicit current CuEq admission;
12. add focused positive/negative tests that exercise the real numerical owner and independent oracles rather than duplicating expected logic in fixtures.

### Stage E — Assembled acceptance

Run and retain exact candidate identities for:

- independent estimator/reducer oracle tests and adversarial tests;
- focused parity-policy/unit/schema/backward-readability tests;
- stored-realization/stale-stage/currentness tests;
- specification/authority-layer tests;
- doctor/config/default tests;
- affected optimizer/training-identity and restart/reuse tests;
- affected CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 preflight/handoff tests;
- affected acceleration/foundation/MH-1/MPA-0 tests;
- complete affected CPU regression;
- real target-host MH-1 parity requalification under the exact accepted method/runtime;
- real target-host MPA-0 requalification whenever the accepted relation claims MPA-0/generic coverage.

CPU skips cannot stand in for mandatory target-host evidence. GPU evidence may be deferred only for a claim explicitly left unqualified; a CuEq production authorization may not be closed PASS with its required runtime check skipped.

Long paired training trajectories are **not required merely to prove the current instantaneous parity admission relation**. Current explicit CuEq campaign policy was decoupled from the immutable historical CUEQ-PHASE1 record by Rev60, so this workplan must not invent a new phase-1 prerequisite. If the user's target-host run is also intended to produce CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 evidence, execute those existing gates under their own contracts after parity admission rather than redefining them inside this workplan.

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

1. preserve Rev83-86/CUEQ-DEFAULT1 artifacts exactly as historical evidence; do not rewrite history to imply current authority;
2. promote the parity relation through the accepted D2 owner/overlay with explicit source closure and parent identity;
3. reconcile any accepted successor D1/D2/D3 state before promotion rather than merging candidate files by path;
4. update current D3/D4 architecture/specification documentation and `docs/specs/training_data/README.md` so there is exactly one current numerical owner;
5. update semantic dependency/currentness views;
6. remap or invalidate evidence bound to the old parity-policy/method digest, but preserve still-applicable raw observations;
7. require stale stored CuEq realizations to requalify under current policy before consequential use;
8. project realization-digest changes onto TRAIN2 roots. Preserve e3nn roots. For CuEq roots, distinguish an actual changed execution realization from a non-consumed admission-policy representation before deciding reuse/retraining;
9. regenerate any FINAL-GPU1 preflight/handoff/release-side artifact whose integrity contract binds the old policy; never edit a sealed handoff in place;
10. preserve frozen release/audit/SHA records as historical evidence;
11. reconcile CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 state separately where those release/evidence claims are in scope—parity acceptance alone does not rewrite their immutable status, and their pending status does not by itself revoke Rev60/current explicit-opt-in campaign policy;
12. reconcile PEM only if this episode establishes a qualifying new failure family, success application, notice, or materially changes an existing lesson;
13. record the evidence-quality and transportability failure that caused the old MPA-0-derived rule to be challenged so the same threshold-tuning cycle is not repeated.

## 8. Acceptance and handoff

The workplan may close only when all of the following hold:

- the accepted D1/D2 parent and any overlapping successor authority are explicitly resolved;
- the confirmed acceleration-parity source-closure gap is closed by an accepted role/dtype D2 family covering every current CuEq parity relation that remains supported; only TRAIN2 FP32 may change numerically without separate falsification of the siblings;
- the current Serious Challenge has been resolved by an accepted D2 criterion/formalization or falsified by evidence showing the original relation remains adequate;
- the original MH-1 observation exists as durable, applicability-qualified evidence or its unavailability is explicitly recorded and a reproduction is distinguished from it;
- MPA-0 evidence used for any generic claim is raw/authenticated or freshly re-realized; prose/test fixtures alone do not carry raw-evidence force;
- generic-vs-regime/runtime/hardware/model scope is explicit;
- the parity gate's exact current-admission proposition and its claim-boundary relationship to CUEQ-PHASE1, Rev60, current generated defaults, and FINAL-GPU1 are explicit;
- channel units/scales/protected consequences and descriptor semantics are explicit;
- estimator dependence, quantile definition/resolution, order/warm-up/process effects and uncertainty/finite-sample semantics are closed;
- probe-domain adequacy is established for the claim being made;
- adversarial false-pass/false-fail/currentness cases are closed;
- the immutable composed D2 candidate passes fresh independent Review;
- stakeholder ratification of that exact reviewed target is recorded;
- D3/D4 realize exactly the accepted relation with no special-case bypass or duplicate registry;
- stale stored realizations/stage state fail closed under a changed policy and historical records remain readable but non-authorizing;
- all dependent policy-digest/currentness/FINAL-GPU1 bindings are reconciled;
- complete affected CPU regression passes;
- required target-host requalification passes for every regime claimed by the accepted relation;
- no required check is merely deferred while an unqualified CuEq production claim is made;
- workplan closure does not rewrite CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 status; current explicit CuEq campaign admission follows the accepted current campaign-policy lineage, while generated defaults remain separately owned;
- user-facing/runtime documentation must describe those distinct claims consistently and must not either (a) pretend a doctor pass retroactively passes historical release gates or (b) invent a historical release gate as a universal prerequisite that the later accepted project policy explicitly decoupled.

Until closure, the safe campaign disposition is:

```toml
[acceleration]
backend = "e3nn"
```

for production MH-1 runs that must proceed without the challenged CuEq equivalence claim.


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

Revision 60 (`CUEQ-DEFAULT1`, mdstats 0.20.193a0) explicitly records a stakeholder/project policy change: phase-separated TRAIN2 CuEq became the generated campaign policy at that time, while the immutable CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 records retained their original meanings and were **not** retroactively changed. Revision 61 then used selected-head doctor parity as the fail-closed training realization gate. Later CONFIG1 moved the generated MH-1 default back to e3nn, but explicit CuEq remained an opt-in path.

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
