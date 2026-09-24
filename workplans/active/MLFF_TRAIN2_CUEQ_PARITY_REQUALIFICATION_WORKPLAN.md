---
kind: abstraction-concretization-change-plan
protocol_version: 6.4.0
status: active-serious-challenge
workplan_id: MLFF-TRAIN2-CUEQ-PARITY-REQUALIFICATION
created_date: 2026-09-24
branch: design/mlff-train2-cueq-parity-requalification
basis_commit: af89c30ca5304c4dd71ff82b779db973ce0006f8
highest_potentially_affected_domain: D2
d1_change_expected: false
human_ratification_required_for_d2_mutation: true
production_default_during_repair: e3nn
---

# MLFF TRAIN2 CuEq FP32 backend-parity requalification — D2 -> D3/D4 workplan

## 0. Disposition and Serious Challenge

**OPEN — SERIOUS CHALLENGE to the accepted TRAIN2 FP32 backend-equivalence criterion.**

A real target-host MACE-MH-1 / `omat_pbe` doctor realization on an NVIDIA RTX 3090 passed dependency, selected-head, CUDA, resource, and execution-capability checks but failed the authorizing pure-CuEq TRAIN2 FP32 noise-normalized parity gate.

The observed failure is not sufficient evidence that CuEq is scientifically or numerically inadmissible. It is evidence that the current equivalence authority may be inadequately parameterized for the regime it claims to govern:

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

The strongest immediate counterexample is the descriptor channel: the current absolute cross-backend ceiling is smaller than the maximum observed same-backend FP32 descriptor variability on both backends in this target-host realization. An absolute backend-equivalence predicate that can reject cross-backend variation at or near the backend's own repeatability scale requires renewed numerical justification.

The current authority remains the baseline until a replacement passes independent D2 falsification and receives required human ratification. D3/D4 MUST continue to fail closed under the existing policy in the meantime. No threshold widening, retry-until-pass behavior, silent e3nn fallback, or MH-1-specific bypass is authorized.

Operationally, the accepted safe production route during this repair is the existing explicit `e3nn` TRAIN2 path. CuEq remains opt-in and non-authorizing when its parity gate fails.

## 1. Outcome and authority

### Protected outcome

Determine and freeze a scientifically defensible FP32 TRAIN2 backend-equivalence method that:

1. distinguishes systematic e3nn/CuEq disagreement from ordinary realization-level FP32 variability;
2. applies coherently across every foundation/model family and head that the authority claims to cover;
3. preserves hard fail-closed behavior for genuine numerical disagreement, non-finite outputs, selection disagreement, or unsupported runtime realization;
4. does not tune acceptance to admit a particular observed run;
5. remains strong enough to protect all downstream scientific decisions that depend on TRAIN2 execution equivalence.

### Highest potentially affected semantic domain

`D2 — numerical algorithm/method`.

This is not initially a D4 doctor bug. The current doctor correctly realizes the accepted gate. D3/D4 modification is downstream work only after the D2 criterion is accepted, unless independent evidence first proves that the observed metrics themselves are incorrectly computed.

### Current normative/evidence owners

Current repository baseline:

`hjin98/mdstats@af89c30ca5304c4dd71ff82b779db973ce0006f8`

Primary affected numerical specification:

`docs/specs/training_data/mlff_cueq_train_noise_normalized_parity_spec.md`

Current executable realization:

`mdstats/training_data/acceleration.py`

Current governing general numerical authority:

`docs/methods/mlff_numerical_algorithmic_method.md`, especially the execution-equivalence rules requiring an accepted relation rather than a backend-observed ad hoc tolerance.

Relevant historical qualification/specification evidence includes:

- `docs/specs/training_data/mlff_cueq_train_default1_hotfix_spec.md`;
- `docs/specs/training_data/mlff_cueq_train_default1_fp32_ceiling_hotfix_spec.md`;
- `docs/specs/training_data/mlff_cueq_phase1_training_qualification_spec.md`;
- `docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV86.md`;
- `release/MLFF_CUEQ_DEFAULT1_HF1_QUALIFICATION_0.20.194a0.json`;
- MPA-0 DIAG3 evidence cited by the current noise-normalized parity spec;
- the new MH-1 target-host doctor realization supplied by the stakeholder on 2026-09-24, which must be captured durably before it is used as acceptance evidence.

### Required human state

Any material replacement of the current D2 equivalence relation requires:

`proposed D2 -> fresh independent D2 falsification -> stakeholder ratification -> D3/D4 handoff`.

The implementation agent cannot self-authorize a looser equivalence criterion.

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
10. **Uncertainty must be represented honestly.** Repeated-pair statistics built from a small number of repeated evaluations are dependent observations; all-pairs cardinality must not be interpreted as an independent-sample count.
11. **Accepted currentness is explicit.** Any changed parity-policy identity must invalidate/remap dependent preflight, handoff, qualification, cache, and provenance records exactly where they bind the old policy digest.
12. **Existing e3nn production path remains admissible.** The repair may not destabilize the current default MH-1 e3nn campaign path.

### 2.2 Cycle-scoped decisions

For this repair cycle:

- use the real MH-1 target-host observation as a falsification input, not as the new tolerance source;
- compare at least the historically relevant MPA-0/default and MH-1/omat_pbe regimes before claiming a generic replacement policy;
- prefer one coherent equivalence construction over stacked legacy absolute floors plus model-family exceptions;
- keep the current warm-up and repeated-evaluation machinery only if its statistical role is independently justified; its current implementation identity is not protected.

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

- `docs/specs/training_data/mlff_cueq_train_noise_normalized_parity_spec.md`;
- `mdstats/training_data/acceleration.py`;
- doctor/preflight code in `mdstats/training_data/_campaign_cli_core.py`;
- FINAL-GPU1 preflight/handoff policy-digest bindings;
- parity/repeatability record schemas and serializers;
- focused CuEq parity tests, especially `tests/test_mlff_cueq_train_noise_normalized_parity.py` and specification tests;
- MH-1 campaign-default tests to ensure e3nn remains the default;
- any release/audit qualification records that are normative inputs rather than frozen historical evidence;
- current architecture/dependency documentation and semantic-evolution notes if D2 authority changes.

### 3.3 Unaffected siblings to preserve

Unless new evidence contradicts them:

- source/DATA6 acceleration parity authority;
- FP64 parity;
- CUEQ-PHASE1 paired-training scientific qualification semantics;
- TRAIN2/EVAL2 model-architecture authentication;
- production scheduler/resource budgeting;
- replay-retention and checkpoint-admissibility method;
- final-production publication and P7 deployment ownership.

### 3.4 Project Engineering Memory / Historical Applicability Set

Effective memory basis at plan opening is the accepted `PROJECT-ENGINEERING-MEMORY.md` on `main@af89c30...`, whose accepted-base metadata is itself partial and historically reconciled through `4eabe2ae...` plus the later final-publication candidate overlay.

Materially applicable current lessons:

- **SP-002**: preserve fail-closed authenticated identity/state boundaries;
- **SP-004**: real-owner and target-host qualification can expose defects missed by mocks/control-plane checks;
- TRAIN2/EVAL2 CuEq architecture history: do not confuse backend-parity failure with model-construction/architecture drift without independently checking exact realization identity.

PEM coverage is partial. Absence of a specific historical parity family is not evidence that no relevant prior episode exists. Perform a bounded history search over CuEq/FP32 parity, selected-head MH-1, MPA-0, DIAG3, CUEQ-DEFAULT1, CUEQ-REPEAT1, and FINAL-GPU1 before freezing a replacement criterion.

## 4. Evidence and falsification

### 4.1 Reverse-semantic verification question

For every proposed criterion `Q`:

> Could `Q` pass a backend pair whose systematic numerical difference is materially larger than ordinary same-backend FP32 variability or capable of changing a governed selection/scientific decision?

And conversely:

> Could `Q` reject two realizations whose observed difference is statistically indistinguishable from the same-backend variability that `Q` already accepts?

Both false-positive and false-negative behavior matter.

### 4.2 Durably capture the new target-host evidence

Before using the 2026-09-24 MH-1 realization as acceptance evidence, record:

- exact mdstats commit/package identity;
- campaign configuration/foundation contract digest;
- exact selected-head derived model digest;
- MACE/e3nn/Torch/CUDA/CuEq package identities;
- GPU identity;
- parity-policy digest;
- full repeatability diagnostic record, not only console summaries;
- deterministic-control state if separately exercised;
- structure/model/descriptor/FPS identities sufficient to establish applicability.

The chat transcript is discovery evidence, not a durable qualification artifact.

### 4.3 Required regime matrix

At minimum evaluate:

1. MPA-0/default FP32 selected-head TRAIN2;
2. MH-1/omat_pbe FP32 selected-head TRAIN2.

Add another materially different supported family/head only if already within the claimed generic policy scope and cheaply available. Do not broaden the project merely to manufacture sample count.

Each regime must use the exact accepted source model/head and the production parity path.

### 4.4 Statistical validity obligations

The current method retains ten post-warm-up evaluations per backend and computes 45 self pairs plus 100 cross pairs. These pairwise statistics share evaluations and are not independent replicates.

Any proposed tail/quantile/ratio criterion MUST therefore justify:

- the experimental unit;
- which observations are independent or conditionally dependent;
- how uncertainty of the self-noise envelope and cross statistic is estimated;
- why the selected quantile/tail functional is stable at the available repeat count;
- how the method behaves when self-noise is zero or nearly zero;
- whether repeat count is sufficient to support the selected quantile;
- whether structure/atom/component multiplicity creates pseudo-replication;
- whether deterministic controls diagnose cause without becoming an unrealistic authorization regime.

Do not justify `P99` reliability by treating 100 correlated cross pairs as 100 independent backend experiments.

### 4.5 Channel-specific falsification

For energy, force, stress, and descriptors:

- measure same-backend repeatability and cross-backend discrepancy under identical inputs;
- test whether a channel is genuinely stable enough for an independent absolute ceiling;
- if an absolute ceiling is retained, derive it from accepted numerical-error semantics or sufficiently broad independent evidence, not merely the largest observed passing value;
- if normalization is used, test pathological low-self-noise cases and systematic offsets;
- preserve a catastrophic absolute guard where needed so a large common-noise envelope cannot normalize away a materially large disagreement.

For deterministic FPS/selection:

- require exact identity unless D2 explicitly proves a weaker relation preserves every dependent decision;
- include near-tie structures capable of exposing descriptor perturbations at selection boundaries.

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
10. repeated-pair pseudo-replication case showing that a naive independent-sample uncertainty estimate is overconfident.

### 4.7 Historical evidence is evidence, not authority

Reconstruct why:

- selected-head MH-1 earlier motivated a `2e-6` TRAIN2 FP32 absolute floor;
- MPA-0 later motivated a `1e-5` force ceiling;
- DIAG3 led to the current force noise-normalized criterion and the return of energy/stress/descriptor to `1e-6`.

Determine whether the later generic policy had adequate cross-family evidence for each stable-channel assumption. Do not simply revert to an older constant.

## 5. Concretization sequence

### Stage A — Evidence intake and authority reconstruction

1. Durably capture the new MH-1 target-host diagnostic.
2. Reconstruct the exact current D2 parity claim and every dependent policy digest/currentness edge.
3. Perform the bounded historical CuEq parity/HAS review.
4. Confirm that the observed failure is not caused by mismatched model/head/descriptor/FPS identities or an implementation bug in metric construction.
5. If D4 metric computation is wrong, route that defect separately and rerun before mutating D2.

**Gate A:** only proceed with D2 replacement design if current metrics are valid and the accepted criterion remains materially challenged.

### Stage B — D2 candidate method

1. Define the experimental units and stochastic/repeatability semantics.
2. Define the equivalence statistics per channel.
3. Define absolute catastrophic guards.
4. Define selection identity requirements.
5. Define repeat/warm-up/sample requirements and insufficiency outcomes.
6. Define generic-vs-regime parameterization explicitly.
7. Define the policy digest/parameter family so evidence cannot silently cross incompatible regimes.
8. Write the proposed D2 method/specification before changing product thresholds.

**Gate B:** candidate method must be definition-closed and must not contain constants selected merely because they pass the new MH-1 observation.

### Stage C — Independent numerical falsification

Exercise the proposed method against:

- current MPA-0 evidence;
- current MH-1 target-host evidence;
- synthetic/adversarial counterexamples from Section 4.6;
- repeatability resampling or additional realizations sufficient to assess estimator stability.

A candidate that merely admits both historical real runs but cannot reject systematic disagreement is not acceptable.

**Gate C:** fresh independent D2 Review and required stakeholder ratification.

### Stage D — D3/D4 handoff

Only after Gate C:

1. revise the single canonical parity owner in `acceleration.py`;
2. remove superseded criterion machinery rather than layering a second special-case path;
3. revise records/schemas only where the accepted method requires it;
4. update doctor/preflight diagnostics to report the new method transparently;
5. update policy-digest bindings/currentness;
6. preserve no-silent-fallback and default-e3nn behavior;
7. add focused positive/negative tests that exercise the real numerical owner rather than duplicating expected logic in fixtures.

### Stage E — Assembled acceptance

Run:

- focused parity-policy/unit tests;
- specification tests;
- doctor/config/default tests;
- affected FINAL-GPU1/preflight tests;
- affected acceleration/foundation/MH-1 tests;
- complete affected regression;
- real target-host requalification for MH-1;
- MPA-0 requalification if the accepted generic policy claims MPA-0 coverage.

Long training trajectories are not required to prove this preflight equivalence relation unless the accepted D2 method explicitly needs downstream training-decision evidence that cannot be established more cheaply. Do not turn this repair into an unnecessary full campaign.

## 6. Reopen, simplification, and human triggers

### Earliest owner to reopen

- wrong metric/identity/comparison implementation -> D4;
- insufficient representation of realization/policy/currentness -> D3;
- invalid equivalence statistic, tolerance, precision/noise model, or stochastic semantics -> D2;
- changed scientific meaning of what backend equivalence must protect -> D1.

### Evidence that invalidates frozen premises

Reopen the candidate if:

- same-backend variability is materially nonstationary across repeats or structures;
- model family/head materially changes the error regime and no generic criterion remains defensible;
- descriptor noise can change FPS selection despite aggregate parity;
- CuEq/e3nn disagreement has persistent signed structure beyond repeatability noise;
- the proposed criterion becomes permissive under inflated self-noise;
- required evidence depends on an unavailable/unsupported runtime.

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

On accepted D2 change:

1. mark the superseded parity specification historical without rewriting its original evidence;
2. update the numerical method's execution-equivalence import/definition if needed so the canonical D2 owner is unambiguous;
3. update architecture/specification documentation;
4. update semantic dependency/currentness views;
5. remap or invalidate evidence bound to the old parity-policy digest;
6. preserve frozen release/audit records as historical evidence;
7. reconcile PEM only if this episode establishes a qualifying new failure family, success application, or materially changes an existing lesson;
8. record why the old cross-family assumption was inadequate so the same threshold-tuning cycle is not repeated.

## 8. Acceptance and handoff

The workplan may close only when all of the following hold:

- the current Serious Challenge has been resolved by an accepted D2 criterion or falsified by evidence showing the original criterion remains adequate;
- the new MH-1 observation exists as durable, applicability-qualified evidence;
- generic-vs-family scope is explicit;
- estimator dependence and uncertainty are accounted for;
- adversarial false-pass/false-fail cases are closed;
- independent D2 Review passes;
- stakeholder ratification is recorded;
- D3/D4 realize exactly the accepted relation with no special-case bypass;
- all dependent policy-digest/currentness bindings are reconciled;
- complete affected regression passes;
- required target-host requalification passes for every regime claimed by the accepted criterion;
- no required check is merely deferred while an unqualified CuEq production claim is made.

Until closure, the safe campaign disposition is:

```toml
[acceleration]
backend = "e3nn"
```

for production MH-1 runs that must proceed without the challenged CuEq equivalence claim.
