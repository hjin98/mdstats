---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 5
status: implemented
package_revision: 6
amended_date: 2026-08-29
entry_p4_closure_commit: 145388e5ad11733be1c19539886e34b82cc7d7d2
revision5_implementation_baseline_commit: ca1c402645fc210c38a15e55c81cdf30e6b459ab
revision4_baseline_commit: e19962966116586da8a028c252a53deb80cd6795
revision3_baseline_commit: 178a4e653693b810cb02e5ea8bd6bd376da93ab0
revision2_baseline_commit: 2a3c3776aa03ac7e45dd0de2986a6bb390deb710
revision1_baseline_commit: 5bf53c99ce31d1438c21bae81c0f30c79176bdc4
compatibility_policy: current-generation-cutover-no-derived-migration
reconciliation_reason: Independent review of the assembled revision-5 implementation found one genuine P5-local blocker without invalidating the frozen parent or accepted P1-P4/P5 architecture: PostSelectionMethodIdentity is not yet guaranteed to describe the method actually executed by post-selection DATA7/DATA8/TRAIN2/MACE, and replay-enabled checkpoint admissibility has no real TRUE_DFT replay evaluation path. Revision 6 closes only the method-identity-to-execution equivalence and replay-admissibility execution surfaces while preserving every unaffected prior P5 obligation.
---

# P5 revision 6 — executable-method realization and replay-admissibility closure

## 0. Authority, scope, and preserved contract

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. P5 remains bound to Protocol 5.8.0. This revision does not reopen P1-P4 or alter the target-size scientific model.

The implementation at `ca1c402645fc210c38a15e55c81cdf30e6b459ab` is the immediate revision-5 implementation baseline under correction. Revisions 2-5 remain incorporated as historical provenance, but this revision is the current implementation handoff and is self-contained for still-binding P5 task semantics.

The following remain frozen and must not regress:

- P4 CampaignStore/current-terminal authority is the sole upstream current `N_selected/T_selected` owner;
- `T_selected = pi_train[:N_selected]` exactly, with no CV/replay expansion or reselection;
- P5 current reads/writes reauthenticate P4 currentness and current-facing publication is commit-time stale-generation fenced;
- post-selection CV occurs only after selection, uses configured `K >= 2`, exact selected-only coverage, and the complete canonical P1 split-exclusion/protected-relation projection;
- every required CV fold and every required CV seed/variant must pass; no mean-only, majority, best-seed, partial-fold, K=0/K=1, or `cv_not_performed` production authorization;
- checkpoint/model ordering among admissible candidates is target-only; replay and physical evidence are constraints/diagnostics and receive zero ranking or acceptance-score credit;
- held-out outer CV evidence cannot select that fold's checkpoint;
- M3 is development/model-selection evidence only, never independent validation;
- final production is fresh, uses full exact `T_selected`, fresh optimizer/RNG/run state, and never resumes a target-size or CV model/optimizer/checkpoint trajectory;
- `[training].max_num_epochs` is final-production-only horizon authority, independent of target-size `n3` and CV budget;
- screen/CV/final run/restart/checkpoint namespaces remain collision-proof;
- policy -> plan -> realized evidence dependency direction remains acyclic;
- no CV/final result may mutate or reinterpret P4 target-size authority;
- long GPU/data-heavy production qualification remains deferred to final release; bounded functional regression/integration is mandatory now.

Revision 6 has precedence only for shared-method resolution, executable realization, replay training/exposure, replay admissibility evaluation, and acceptance evidence needed to prove those surfaces.

---

## 1. Blocking defect being corrected

The current revision-5 implementation can compute a `PostSelectionMethodIdentity` that claims one scientific method while the MACE job executes a materially different or incomplete realization.

Observed failure mechanisms include:

1. post-selection method resolution constructs a default `TargetSizeCommonTrainingPolicy()` instead of proving that the policy is the same accepted method/preparation recipe actually consumed by execution;
2. method identity can contain training mode, optimizer, precision/backend, checkpoint admissibility, replay semantics, and other fields that are not all consumed or enforced by the generated MACE/TRAIN2 job;
3. post-selection MACE materialization currently canonicalizes `mace_architecture` from `None`, which means pinned defaults rather than an authenticated exact accepted model/architecture realization;
4. canonical foundation/model/head initialization is not positively bound through the post-selection execution configuration;
5. replay enablement is inferred from one legacy path-presence heuristic instead of the canonical campaign replay authority;
6. the post-selection TRAIN2 runtime is built with replay monitoring disabled, and checkpoint assessment supplies `None` replay candidate/baseline metrics and `None` label mode;
7. therefore a replay-enabled admissibility policy either rejects every checkpoint for missing evidence or is effectively absent from a runtime that claims to implement replay retention;
8. the current assembled P5 fixture does not configure replay, so it cannot detect this defect.

This is implementation nonconformance against the already-frozen P5 method/replay contract. The correction is P5-local unless repository evidence proves that the accepted P3/P4 method authority itself cannot be reused without changing predecessor science.

---

## 2. Frozen corrected design

### 2.1 One canonical resolved post-selection method realization

There must be one canonical pre-execution resolution path for the shared method that both:

```text
(a) produces PostSelectionMethodIdentity
and
(b) supplies the exact executable inputs consumed by DATA7/DATA8/TRAIN2/MACE/EVAL2.
```

Implementation may extend the current `PostSelectionMethodPolicies` or introduce one version-agnostic resolved-method object. Do not create parallel independent resolvers for identity and execution.

The resolved method must carry, directly or through existing owned policy objects, every scientifically material field needed to reproduce the method, including as applicable:

- training mode;
- canonical foundation/model initialization identity and executable source;
- selected head/head-family/multihead realization;
- canonical MACE model architecture/configuration identity;
- objective/property/configuration-weighting recipe;
- fold/final target preparation recipe shared by the method;
- replay source/exposure/training-role semantics;
- TRUE_DFT replay-retention/admissibility policy;
- optimizer family and scientifically material shared optimizer settings;
- LR schedule policy;
- checkpoint interval/admissibility/target-only selection policy;
- precision/dtype;
- acceleration/backend identity only to the extent it is scientifically material and actually enforced;
- ExtXYZ/data-key policy;
- other shared integrity constraints already accepted by P5.

The object may also carry runtime handles/paths needed to execute those identities, but raw path spelling must not substitute for scientific identity. If moving the same immutable foundation/replay file to another path does not change scientific meaning, identity should bind its authenticated content/semantic digest rather than path location.

### 2.2 Identity/execution equivalence invariant

For every field included in `PostSelectionMethodIdentity`, exactly one of the following must be true:

1. the executable DATA7/DATA8/TRAIN2/MACE/EVAL2 path consumes/enforces the corresponding resolved value; or
2. the field is proven non-scientific/resource-only and is removed from the method identity; or
3. the requested value is unsupported and resolution fails closed before expensive work.

It is forbidden for a config mutation to change the method digest while leaving the executable scientific job unchanged merely because execution silently falls back to a default.

Conversely, no material executable method choice may vary without participating in the appropriate shared-method/policy identity.

### 2.3 Reuse the accepted target-size/common MACE construction authority

Do not hand-build a second P5-specific interpretation of foundation/head/architecture/training-mode semantics.

Implementation must trace the current accepted target-size/P3 construction path and reuse or extract its canonical version-agnostic method/MACE configuration builder wherever the semantics are shared. If the reusable logic is currently embedded inside a target-size-specific caller, refactor the minimum common builder/resolver and make both target-size and P5 callers use it without changing accepted P3 behavior.

In particular:

- `canonicalize_mace_candidate_architecture(None)` must not remain the P5 method realization unless `None -> pinned defaults` is positively the exact authenticated method architecture and that same descriptor is bound by the method identity;
- foundation/head/multihead fine-tuning settings must come from the canonical resolved method and be emitted to the actual MACE job through the established MACE argument translation;
- optimizer-family/settings that participate in identity must reach the runtime/MACE owner or be rejected if unsupported;
- dtype/backend values in identity must match the runtime realization that actually executes;
- target preparation must receive the resolved common training/weighting/reference-fit recipe instead of internally constructing unrelated defaults.

Fresh CV/final training means fresh execution from the canonical method initialization. For a foundation-fine-tuning method this means reloading the canonical foundation initialization for each new run, not random scratch and not a screening/CV checkpoint. If the canonical method is truly scratch initialization, use that exact accepted scratch policy instead.

### 2.4 Replay authority resolution

Replay configuration must be resolved through the repository's canonical replay owner, not through `bool([paths].replay_true_labels)` or another single-key heuristic.

Implementation must support the currently accepted replay configuration interface(s), including the canonical single-source replay path when enabled and any still-supported legacy split-file form through the existing normalization layer. Do not create another P5-only replay configuration schema.

Resolve before expensive post-selection work:

```text
canonical replay config/source authority
 -> authenticated replay source identity
 -> deterministic train/monitor split authority
 -> training replay role
 -> TRUE_DFT monitor/evaluation view when replay retention is enabled
```

If the resolved shared method requires replay but the required source/TRUE_DFT retention authority cannot be constructed, fail before fold/final training when the absence is knowable at setup time. Never silently set replay disabled merely because one legacy path key is absent.

### 2.5 Replay training exposure is part of the method

When the resolved method uses replay/multihead replay, each CV/final training run must actually receive the authorized replay training exposure required by that method.

The target role remains:

- CV: fold-local target gradient membership only;
- final: full exact `T_selected` target gradient membership.

Replay training membership is a separate explicit role descended from the canonical replay authority. It must not enter `T_selected`, CV fold construction, target E0/target-only fitted preparation, or target-size authority by accidental union.

Reuse the shared DATA8/MACE multihead/replay materialization machinery already used by the accepted training path. Do not concatenate replay frames into the target dataset merely to make a single-file trainer work if doing so changes head/objective/exposure semantics.

### 2.6 TRUE_DFT replay admissibility execution

When replay admissibility is enabled, every checkpoint considered for a CV representative or final-production representative must have authenticated replay evidence before target-only ordering.

For the exact replay monitor membership bound to the method/plan:

```text
candidate checkpoint -> replay TRUE_DFT predictions -> candidate replay force RMSE
canonical foundation/baseline -> same TRUE_DFT replay monitor -> baseline replay force RMSE
candidate - baseline -> replay degradation
label namespace -> true_dft
```

Feed the real values to the existing `CheckpointAdmissibilityPolicy` / `assess_eval2_checkpoint` owner:

- `replay_candidate_force_rmse_ev_per_angstrom = actual candidate RMSE`;
- `replay_foundation_force_rmse_ev_per_angstrom = actual canonical baseline RMSE`;
- `replay_label_mode = "true_dft"` (or the canonical enum value serialized equivalently).

Passing `None` is valid only when the resolved admissibility policy has replay disabled.

The foundation/baseline model and head used here must be the canonical baseline bound by the resolved shared method; a convenient unrelated model is not acceptable.

Candidate and baseline must be evaluated on the exact same authenticated TRUE_DFT replay monitor membership and label convention.

### 2.7 Reuse existing replay evaluation machinery

Prefer semantic reuse of existing owners such as the current replay source/split/true-label materialization/view machinery and the existing checkpoint model-comparison/evaluation path that already computes candidate-vs-foundation TRUE_DFT replay metrics.

Do not revive legacy MLCV target+replay weighted ranking. If an existing helper mixes obsolete ranking authority with useful replay prediction/reduction, extract/reuse only the lower-level source/view/prediction/metric owner.

A small content-addressed baseline replay metric may be reused across checkpoints/runs when its complete identity matches, at minimum:

```text
canonical baseline model/head identity
+ exact TRUE_DFT replay monitor identity
+ evaluation/metric policy identity
+ dtype/backend identity when scientifically relevant
```

Caching is optional; correctness and ownership are mandatory. A cache may accelerate evidence generation but cannot become replay authority.

### 2.8 Ordering and acceptance remain unchanged

The required order is:

```text
checkpoint candidate
 -> target metrics
 -> replay TRUE_DFT retention + required physical admissibility
 -> discard inadmissible candidates
 -> target-only ordering among admissible candidates
 -> freeze representative
 -> for CV only: held-out outer target evaluation
 -> fold target-only acceptance
```

Replay may reject a checkpoint but may never improve its rank, break a target tie, rescue a target-failed outer fold, choose another target size, or change P4 state.

For final production, M3 remains the target checkpoint/model-selection evidence. Replay is still an admissibility constraint only.

---

## 3. Identity and lineage placement

### 3.1 Shared method identity

`PostSelectionMethodIdentity` must bind stable shared method definitions, including the authenticated canonical model/foundation/head/architecture and replay exposure/admissibility definition as scientifically applicable.

Do not bind realized fold membership, exact replay prediction outputs, checkpoint metrics, fitted E0 values, M3 membership, or accepted CV result into the shared method policy identity.

### 3.2 CV plan/evidence

The CV plan continues to bind:

- current P4 selected binding;
- exact `T_selected` identity;
- shared method digest;
- CV policy digest;
- current canonical P1 relation authority;
- selected-only projected components;
- exact folds and required CV run matrix;
- exact inherited replay/source lineage needed to execute the method when that lineage is not already fully represented by stable method identity.

Fold evidence binds actual replay training/evaluation artifacts and replay metric records it consumes/produces.

### 3.3 Final plan/evidence

The final-production plan continues to bind:

- current P4 selected binding/full exact `T_selected`;
- shared method digest;
- accepted current CV authorization for that method;
- final-production policy digest;
- M3 lineage;
- final seed/run matrix;
- required replay/source lineage and other inherited scientific parents.

Final evidence binds realized replay training/evaluation/checkpoint evidence below that plan.

### 3.4 Invalidation

Preserve the existing DAG:

- corruption/change of a realized replay metric invalidates only affected descendant evidence;
- change of replay source/exposure/admissibility that changes the scientific method changes the shared method identity and invalidates stale CV/final authorization;
- if that same method field is also part of the target-size/P1-P4 scientific identity, existing upstream invalidation remains authoritative and P5 must not preserve P4 currency locally;
- production-only horizon change still leaves accepted CV method evidence valid;
- CV-only fold/acceptance-policy change still leaves P4 and production-only policy identity unchanged.

---

## 4. Required implementation sequence

### P5-R6A — canonical method resolver and execution parity

**Required end state:** one resolved method object/path controls both method identity and actual post-selection execution.

Implementation consequences:

1. Reconcile `post_selection_identity.py` so method resolution does not create scientifically meaningful defaults that execution does not share.
2. Resolve the canonical foundation/model/head/architecture/training-mode/common preparation/replay/optimizer/LR/dtype/backend/admissibility/selection policies through existing accepted owners.
3. Pass the resolved common training/preparation recipe into fold/final preparation; remove hidden default construction from execution-level helpers where it can drift.
4. Replace P5-local default MACE architecture construction with the canonical resolved architecture/configuration used by the accepted training path.
5. Ensure the generated MACE/TRAIN2 configuration consumes every scientifically material method field or rejects unsupported values.
6. Keep CV budget and production horizon role-specific as already accepted.
7. Preserve P4/P5 identity hierarchy and currentness behavior.

Expected primary affected surface:

- `mdstats/training_data/post_selection_identity.py`;
- `mdstats/training_data/post_selection_execution.py`;
- `mdstats/training_data/campaign_post_selection_runtime.py`;
- the canonical target-size/common MACE configuration builder/resolver if extraction is required;
- associated exports/tests.

Do not modify P1-P4 scientific policy merely to avoid reusing its method resolver.

**Stage-local acceptance:**

- real config -> resolved method -> identity and generated executable config share the same foundation/head/architecture/training mode/optimizer/LR/dtype policy;
- mutate one supported material method field and prove both method digest and executable config/runtime plan change consistently;
- for any configured method value not supported by execution, prove pre-training rejection rather than silent default;
- path relocation of byte-identical immutable model input does not change scientific identity when path location is not semantic;
- structural check proves the current post-selection execution path no longer depends on an unbound `canonicalize_mace_candidate_architecture(None)` default;
- structural check proves execution-level fitted preparation no longer silently substitutes a fresh default common-training policy for the resolved method;
- affected P3/common MACE builder regression passes if shared code is refactored.

Dependent replay/final work does not proceed until this stage has semantic and functional closure.

### P5-R6B — replay training and TRUE_DFT admissibility path

**Required end state:** replay-enabled P5 runs train with the authorized replay exposure and evaluate real TRUE_DFT replay retention before candidate ordering.

Implementation consequences:

1. Resolve replay through the canonical replay configuration/source/split owner, including the current single-source interface and any still-supported normalized legacy form.
2. Bind authenticated replay train/monitor identities into the appropriate method/plan/evidence layers.
3. Materialize replay training input through the shared DATA8/MACE training path when the method requires replay.
4. Materialize/resolve the TRUE_DFT replay monitor view through the existing replay true-label owner.
5. Evaluate the canonical foundation/baseline once per matching evidence identity as appropriate and each candidate checkpoint on the same TRUE_DFT monitor.
6. Convert those predictions with the existing metric/reduction owner; do not add a P5-local RMSE definition.
7. Pass real candidate RMSE, baseline RMSE, and TRUE_DFT label mode into checkpoint admissibility.
8. Persist enough replay metric/source/baseline lineage for restart and audit.
9. Keep replay absent/disabled path valid only when the canonical resolved method actually disables replay.
10. Do not enable TRAIN2 adaptive replay stopping; replay retention remains checkpoint admissibility, not a performance-driven training-termination authority.

Expected primary affected surface:

- `campaign_post_selection_runtime.py`;
- `post_selection_execution.py`;
- replay/source/view integration adapters if needed;
- `post_selection_cv_acceptance.py` only if evidence binding requires extension, not to change target-only acceptance semantics;
- `post_selection_production.py`/plan records only for exact replay/source parent binding if not already covered;
- tests/fixtures.

Prefer reuse of `replay.py` source/split/TRUE_DFT view owners and the existing checkpoint evaluation/model-comparison machinery. Modify those shared owners only when an actual reusable API gap exists, and then run their affected regression.

**Stage-local acceptance:**

- replay-enabled real config produces a canonical replay authority; no legacy path-presence heuristic decides scientific enablement;
- captured CV/final training materialization proves authorized replay training exposure is present when required and target membership remains exact;
- candidate within replay degradation budget is admissible;
- candidate above replay degradation budget is inadmissible even if target score is best;
- two admissible candidates where the target-better candidate has worse replay degradation still select the target-better candidate;
- missing/unauthenticated TRUE_DFT replay evidence fails closed and cannot be converted to replay-disabled behavior;
- replay-disabled method runs without replay metrics and remains target-only;
- candidate and foundation replay metrics bind the same exact TRUE_DFT monitor membership;
- final-production M3 checkpoint selection applies the same replay admissibility constraint before target-only ordering;
- no replay metric contributes to outer-fold acceptance or seed/committee ranking credit.

### P5-R6C — assembled authorization/restart reclosure

**Required end state:** the complete P4 -> P5 lifecycle proves that the method CV accepts is exactly the method final production executes, including replay.

Assembled bounded flow:

```text
real config + real CampaignStore
 -> real current P4 SELECTED authority
 -> current selected-training context
 -> canonical resolved shared method
 -> CV policy + exact selected/P1 CV plan
 -> real replay source/split/TRUE_DFT authority when enabled
 -> real fold DATA7/DATA8/TRAIN2/EVAL2 orchestration
 -> replay admissibility + target-only representative selection
 -> held-out target-only fold acceptance
 -> accepted CV authorization for exact shared method
 -> final policy + final plan + M3 lineage
 -> fresh full-T_selected DATA7/DATA8/TRAIN2/EVAL2 orchestration
 -> replay admissibility + target-only M3 checkpoint choice
 -> currentness-fenced publication
 -> fresh-process reload/restart authentication
```

Allowed test doubles: expensive MACE numerical training and inference may be bounded/faked below the real configuration, method-resolution, replay authority, materialization, TRAIN2/EVAL2 decision, CV acceptance, final authorization, persistence/restart, and publication owners.

Forbidden proxy acceptance:

- directly fabricate `Eval2CheckpointRecord` replay fields and claim the runtime replay path is accepted;
- patch the post-selection method resolver or materializer to return the desired executable configuration;
- seed accepted CV records and skip real fold authorization/acceptance;
- bypass canonical replay source/split/TRUE_DFT resolution;
- inspect only method digests without proving the job handed to the trainer consumes the same method;
- replace CampaignStore/currentness when current/restart/publication is under acceptance.

Mandatory assembled assertions:

- P4 selection/revision remains unchanged by CV/final work;
- exact CV universe remains `T_selected` and complete under P1 split exclusion;
- the trainer request/materialized MACE config proves canonical foundation/head/architecture/training-mode realization;
- replay-enabled runs contain the authorized replay training role and authenticated TRUE_DFT replay monitor lineage;
- every accepted representative passed replay/physical admissibility and target-only ordering;
- every required fold/seed passed the configured outer target predicate;
- final production uses full exact `T_selected`, fresh initialization/optimizer/RNG, independent configured production horizon, M3 target monitor, and the same shared method digest accepted by CV;
- screen/CV/final namespaces remain disjoint;
- restart reauthenticates P4 + method/policy/plan + replay/source parents before reuse;
- stale CV under a changed shared method cannot authorize final production;
- stale-generation publication race remains fenced.

---

## 5. Mandatory negative and structural matrix

The revision is not closed without the following direct protections:

1. **identity-only mutation guard:** changing a method field cannot change only the digest while leaving the executable job byte/semantically unchanged.
2. **execution-only mutation guard:** changing a material executable MACE method setting cannot leave the method identity unchanged.
3. **default architecture guard:** no current P5 path silently replaces accepted architecture with unbound pinned defaults.
4. **foundation guard:** no screening/CV checkpoint is used as P5 initialization; canonical foundation/scratch policy is used freshly.
5. **training-mode guard:** identity claiming replay/multihead cannot execute a target-only single-head job.
6. **replay-enable guard:** current replay enablement comes from canonical replay resolution, not one legacy path boolean.
7. **replay-training guard:** replay-required method cannot train without authorized replay exposure.
8. **TRUE_DFT guard:** replay-enabled admissibility cannot call EVAL2 with missing candidate/baseline replay metrics or missing label mode.
9. **same-monitor guard:** candidate and baseline replay metrics cannot come from different replay memberships/label namespaces.
10. **ranking guard:** replay can reject but cannot rank/tie-break/credit acceptance.
11. **outer-fold guard:** outer CV data cannot enter fitting/checkpoint selection.
12. **M3 guard:** M3 can select final checkpoint but is not independent validation.
13. **horizon guard:** production `[training].max_num_epochs` remains independent from target-size `n3` and CV budget.
14. **currentness guard:** g1 work cannot become current after g2 P4 publication.
15. **no-backflow guard:** CV/replay failure cannot trigger target-size reducer/reselection.
16. **legacy-authority guard:** no current P5 execution edge depends on DATA5 label-domain CV or replay-weighted MLCV ranking authority.

---

## 6. Affected regression and qualification disposition

After P5-R6A, run focused method-resolution/materialization tests plus stage-local affected regression for every shared builder/resolver touched.

After P5-R6B, run focused replay/source/split/TRUE_DFT/checkpoint-admissibility tests plus affected DATA8/TRAIN2/EVAL2/replay regression.

After P5-R6C, re-derive the affected surface from the assembled diff and run fresh complete affected regression. At minimum include:

- all P5-A/B/C/D/E/F/G and revision-5 identity tests still applicable;
- P4 current terminal/currentness/publication race tests;
- target-size/P3 common method/MACE builder tests if shared code changed;
- replay source/split/single-source/legacy-normalization/TRUE_DFT view tests actually reused;
- existing TRUE_DFT replay checkpoint-evaluation regression;
- DATA7/DATA8 materialization and replay-role tests;
- TRAIN2 policy/runtime/checkpoint/provider tests;
- EVAL2 target/replay admissibility and target-only ordering tests;
- final-production/M3/freshness/horizon tests;
- persistence/restart/content-addressed evidence tests;
- CLI/orchestrator assembled P4 -> P5 integration.

If the final diff crosses a shared execution/replay surface whose consumers cannot be confidently bounded, run the broader repository regression rather than assuming unaffected behavior.

Do not perform long GPU/data-heavy production qualification as part of this repair. Bounded CPU/available-device functional tests and existing lightweight numerical fakes are sufficient for control-flow/scientific-contract closure. Final real-GPU/production-scale qualification remains deferred under the frozen parent.

---

## 7. Implementation authority

### Frozen

Implementation must preserve all requirements in Sections 0-6. In particular:

- one canonical resolved shared method controls both identity and executable realization;
- canonical foundation/head/architecture/training/replay semantics are reused from existing accepted owners;
- replay-enabled training actually exposes replay data according to the method;
- replay-enabled checkpoint admissibility consumes authenticated TRUE_DFT candidate-vs-foundation metrics;
- replay remains zero-credit for ranking/acceptance;
- all prior P5 currentness/CV/final-production/identity hierarchy rules remain intact.

### Delegated

Implementation may choose:

- exact version-agnostic resolved-method class/module names;
- whether common target-size/P5 MACE configuration logic is extracted into a new shared module or an existing module gains a reusable function;
- exact immutable replay metric record schema when an existing record is not reusable;
- whether baseline replay evaluation is cached or recomputed, provided identity/currentness is correct;
- exact local factoring/error messages;
- bounded numerical fake implementation below the frozen real-owner acceptance boundaries.

### Reopen only on evidence

Reopen only the affected P5 surface if repository evidence demonstrates one of these genuine contradictions:

1. the accepted P3/P4 target-size method cannot expose/reconstruct the canonical foundation/head/architecture/training recipe needed for downstream method equality without changing predecessor science;
2. the supported external MACE interface cannot realize the already-accepted shared method for CV/final production through the common execution engine;
3. TRUE_DFT replay retention cannot be evaluated on the configured canonical replay source without changing the accepted replay scientific contract;
4. making replay training exposure real would require changing the method whose target-size convergence was selected, in which case the existing upstream method identity/invalidation must be honored rather than locally overridden;
5. another frozen P5 requirement is materially contradictory to the implemented predecessor authority.

Legacy topology, inconvenient function boundaries, missing reusable helper APIs, or the need to refactor a shared builder are not redesign triggers by themselves.

---

## 8. Exit gate

P5 revision 6 is accepted only when:

> The exact current P4-selected dataset remains the sole upstream selection authority; one canonical resolved post-selection method produces both the shared method identity and the actual DATA7/DATA8/TRAIN2/MACE/EVAL2 realization; canonical foundation/head/architecture/objective/optimizer/LR/dtype/replay semantics cannot drift between identity and execution; replay-required CV/final runs actually receive the authorized replay exposure; every replay-enabled checkpoint is qualified against authenticated TRUE_DFT candidate-versus-canonical-baseline replay evidence before target-only ordering; all required selected-only CV folds/seeds pass their target-only held-out predicate; and fresh full-`T_selected` final production executes the exact CV-accepted method under independent production policy/M3 lineage without stale currentness, reverse authority, replay ranking credit, or cross-role restart collision.

After stage-local semantic + functional closure for R6A/R6B, fresh assembled R6C regression/integration, and independent review pass, mark P5 implemented/accepted and commit the formal P5 closure checkpoint. P6 remains blocked until that closure.
