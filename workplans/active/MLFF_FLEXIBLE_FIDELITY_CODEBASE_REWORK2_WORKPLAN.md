---
kind: implementation-workplan
workplan_id: CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1-REWORK2
protocol_version: 5.5.0
---

# MLFF Flexible-Fidelity Rework 2 Closure Workplan

## 1. Authority, objective, and starting point

This is the governing closure overlay for `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1` and Rework 1 after independent Software Design review of branch `feat/mlff-end-to-end-performance-v1` at implementation commit `af280aadce2c976fa794508c545b8b1869a2ca1d`.

The parent workplan and Rework 1 remain authoritative for every frozen decision and obligation not explicitly strengthened here. This overlay does **not** reopen the accepted flexible-fidelity architecture:

```text
0 < n1 < n2 < n3 <= n

default fidelity = (1,3,10)
default full TRAIN2 horizon n = 30
```

Objective: close the remaining semantic-identity defect and acceptance gap without replaying already-correct flexible-fidelity work. After this overlay passes, semantically unchanged preparation/preflight/materialization must survive fidelity or full-horizon changes, while fidelity/TRAIN2 state invalidates at the exact dependency frontier; current runtime language must be semantic rather than fixed-epoch; and the assembled implementation must pass the mandatory bounded integration/regression envelope on one final candidate.

## 2. Independent-review findings and routing

### R2-1 - BLOCKER: full TRAIN2 horizon leaks into preparation identity

Classification: implementation nonconformance against Rework 1 O10-R1/RW1.

Observed implementation: `_preparation_config_digest()` starts from nearly the whole normalized campaign configuration and removes selected target-size fidelity fields. `[training].max_num_epochs` remains in that payload. Completed prepare reuse compares this digest exactly.

Failure mode: changing only `n` from 30 to 40 can change the preparation fingerprint and force an upstream rerun even though `n` is a TRAIN2 schedule authority and cannot change already prepared DATA6/DATA7/DATA8 bytes.

Required end state: preparation/preflight/materialization compatibility depends only on configuration and authorities that can change those upstream outputs or their required topology. Fidelity geometry `(n1,n2,n3)`, full TRAIN2 horizon `n`, LR/checkpoint schedule controls, downstream evaluation/progress/presentation, and documentation-only settings must not invalidate semantically independent preparation.

### R2-2 - HIGH: required independent invalidation-frontier test is missing

Classification: acceptance/test nonconformance.

Rework 1 explicitly requires independent perturbation of `n1`, `n2`, `n3`, and `n`. Existing focused coverage proves fidelity-tuple exclusion and one preparation-affecting change, but does not prove that `n` leaves preparation reusable. This omission allowed R2-1 to escape.

Required end state: executable tests establish the exact frontier for each fidelity boundary and for `n`, including post-preflight migration/restart behavior and cross-horizon checkpoint rejection.

### R2-3 - MEDIUM: current runtime still exposes fixed-fidelity wording

Classification: bounded implementation/documentation drift.

Current `size_fidelity.py` still contains current-runtime docstrings/errors such as “30-epoch”, “3-epoch rule”, “10-epoch screen”, and “10-epoch survivors” where the active policy is configurable.

Required end state: current runtime/operator-facing semantics use `coarse`, `short`, `final-screen`, `reference/full horizon`, or the actual configured epoch. Literal `3/10/30` remains only where it is genuinely historical compatibility/test evidence.

### R2-4 - HIGH: final assembled gate evidence remains unproven

Classification: acceptance nonconformance, not a request for production qualification.

The final head has no current CI/status evidence for the required Rework 1 assembled A/B/C + D1/D2/D3 envelope. Source-level review found the previous SIZE-FIDELITY R2/R3 scientific defects materially corrected, but source inspection cannot substitute for required execution.

Required end state: the mandatory assembled cases, final affected-surface regression, integration boundaries, and repository-required checks execute on the same final candidate. Full GPU/production qualification remains deferred.

## 3. Frozen closure design

### 3.1 Positive preparation-semantic identity

The preparation identity must be expressed as an explicit **positive semantic projection** of preparation-owned configuration/authorities, or an equivalent dependency-builder with the same fail-closed semantics. Do not continue the fragile pattern “hash almost the whole campaign configuration and subtract known downstream fields.”

The projection includes every field/authority that can change, at minimum, source admission, frame/catalog semantics, DATA4-DATA6 preprocessing/model-feature generation, REPAIR2/MVQUAL admission, DATA7 fitting/selection/coverage, DATA8 bytes, required preparation variant topology, foundation/model-dependent preprocessing, and input identities.

The projection excludes fields that cannot change prepared outputs, including at minimum:

- `target_data.size_convergence.fidelity_epochs`;
- target-size ranking/equivalence controls whose only effect is later target-size reduction;
- `[training].max_num_epochs` / full horizon `n`;
- TRAIN2 LR schedule, checkpoint admissibility/selection, and stopping controls when they affect training only;
- downstream evaluation/verification/progress/presentation/documentation-only controls.

Do **not** remove a whole configuration section merely because one field is downstream-only. Training method/seed/topology or other fields that genuinely determine which preparation variants/materializations are required must remain authenticated where they are semantically preparation-relevant.

A whole-config SHA may remain as provenance only. It may not by itself invalidate a completed upstream stage when the positive preparation identity proves compatibility.

### 3.2 Exact invalidation frontier

Frozen behavior:

```text
change n1/n2/n3 only
  -> preserve compatible prepare + screening preflight + DATA7/DATA8 materializations
  -> invalidate/reset fidelity-dependent target-size plan/state/evidence and cross-dependent SIZE-FIDELITY/PERF-P2R state
  -> first authorized screen follows the new n1

change n only
  -> preserve compatible prepare + screening preflight + DATA7/DATA8 materializations
  -> invalidate TRAIN2 schedule/training/checkpoint identity and every cross-dependent artifact whose meaning includes n
  -> reject reuse of incompatible pre-existing TRAIN2 checkpoints/evidence
  -> establish the new full-n schedule before new training work

change preparation-owned input/policy
  -> invalidate prepare/preflight/materialization and all dependent downstream state

change presentation/documentation-only field
  -> no scientific/preparation invalidation
```

Target-size candidate/materialization identity must remain independent of later screen geometry/horizon wherever those values cannot alter the bytes. Historical fixed target-size evidence must never be relabeled as flexible evidence.

### 3.3 Migration/restart behavior

Historical v1/schema-less post-preflight campaigns remain governed by Rework 1 D1/D2/D3 semantics. Historical receipts/artifacts must be validated under their historical authority before reuse/re-authentication. If compatibility cannot be proven, fail closed at the narrowest justified rerun boundary.

For the nondefault D2 upgrade `(2,5,12)/40`, changing from historical/default `n=30` to `n=40` must not cause preparation or screening preflight to rerun when all preparation-owned inputs are unchanged. It must, however, establish a new full-40 TRAIN2 schedule identity and reject cross-horizon checkpoint reuse.

### 3.4 Preserve corrected SIZE-FIDELITY science

The prior independent-review blockers are considered design-closed and must not regress:

- short-screen ordering uses the production coarse-screen practical-equivalence semantics;
- final-screen decision at `n3` is a hard qualification input against the full-horizon reference at `n`;
- `n3 == n` may deduplicate physical evaluation while retaining both semantic roles;
- full-reference authority remains `n`, not `n3`.

Do not redesign or weaken these criteria while repairing identity or wording.

### 3.5 Current semantic language

Current executable source, current normative docs, config comments, CLI/status/error strings, and nonhistorical tests must not imply fixed 3/10/30 behavior. Prefer semantic stage names; interpolate the configured epoch when a numeric value improves diagnostics.

Allowed fixed-number occurrences include explicit historical schema/migration compatibility, historical fixtures/oracles, and archived documentation. Such occurrences must be structurally distinguishable from current product authority.

## 4. Implementation obligations

### O14 - Repair preparation identity ownership

**Protected concern:** prevent downstream-only TRAIN2/fidelity configuration from causing expensive, scientifically unnecessary upstream recomputation while retaining fail-closed reuse.

**Required end state:** completed prepare/preflight/materialization reuse is governed by a stable positive preparation-semantic identity. `n` and fidelity-only changes do not alter it; preparation-affecting changes do.

**Required implementation consequences:**

- replace/refactor `_preparation_config_digest()` or its caller architecture so the digest is built from preparation-owned dependencies rather than a whole-config negative filter;
- keep whole-config SHA only as provenance;
- preserve historical v2/schema-less receipt validation before v3/current re-authentication;
- preserve DATA8/candidate materialization independence from fidelity/horizon where bytes/topology are unchanged;
- do not broaden reuse across source/model/selection/coverage/materialization-affecting changes;
- do not create a second parallel preparation-identity authority.

**Expected affected surface:** `_campaign_cli_core.py` preparation fingerprinting/receipt/restart/status; DATA7/DATA8 reuse identity; target-size candidate authority bridge; config normalization; persistence/migration tests.

**Acceptance evidence:**

1. identical preparation inputs with `n:30 -> 40` yield the same preparation semantic digest and reuse completed prepare/preflight/materializations;
2. independent `n1`, `n2`, `n3` changes also preserve preparation identity;
3. a preparation-affecting control such as coverage/admission/selection input changes preparation identity and invalidates upstream state;
4. a presentation-only change does not change preparation/scientific identity;
5. historical receipt corruption/ambiguous compatibility still fails closed.

### O15 - Close exact fidelity/TRAIN2 invalidation frontier

**Protected concern:** upstream reuse must not become unsafe downstream reuse.

**Required end state:** tuple changes reset only fidelity-dependent state; horizon changes reset TRAIN2 schedule/checkpoint/cross-dependent state; incompatible checkpoints cannot continue under a different horizon.

**Required implementation consequences:** existing stage completion/status/advance/restart consumers must derive compatibility from the correct scoped identities rather than global config SHA. Old fixed target-size evidence cannot satisfy a new flexible tuple.

**Acceptance evidence:** dedicated tests perturb `n1`, `n2`, `n3`, and `n` independently and assert exact preserved/invalidated records/stages; cross-horizon continuation is rejected; first post-migration authorization matches the configured coarse screen.

### O16 - Scrub current fixed-fidelity semantic leakage

**Protected concern:** configurable runtime must not mislead operators or future maintainers into treating 3/10/30 as current authority.

**Required end state:** current semantic source/error/docs use stage names or configured values. Historical literals remain only in explicit compatibility/history contexts.

**Acceptance evidence:** structural search over current executable/current normative surfaces classifies every remaining `3`, `10`, `30`, `epoch3`, `epoch10`, `epoch30`, `3/10/30`, and fixed-role phrase occurrence on this fidelity surface as either legitimate historical compatibility or a failure to scrub. Add focused assertions for operator-visible nondefault errors where useful.

### O17 - Final assembled acceptance

**Protected concern:** helper-level green tests and source review cannot prove the real migration/orchestration/persistence path.

**Required end state:** all mandatory bounded integration cases execute on the final assembled candidate, followed by fresh final affected-surface regression and repository-required checks.

**Mandatory cases:**

- **A** fresh `(1,3,10)/30` through configuration -> policy -> screen authorization/evidence -> reductions -> selected size -> production horizon -> status/restart;
- **B** fresh `(2,5,12)/40`, including exact full-40 schedule authentication, eliminated-candidate no-work, progress/status denominators, continuation, and production to 40;
- **C** `(1,3,30)/30`, proving one physical final/reference endpoint may serve two semantic roles without collapsing their validation;
- **D1** historical completed preflight -> default v2 `(1,3,10)/30` upgrade with upstream reuse and downstream fidelity reset;
- **D2** historical completed preflight -> `(2,5,12)/40` upgrade with upstream reuse, new full-40 schedule identity, and no cross-horizon checkpoint reuse;
- **D3** preparation-affecting historical/config change -> fail closed or rerun from the correct upstream boundary.

Use bounded/synthetic data and mocks only where they preserve the real configuration/persistence/orchestration consumers. Do not substitute a helper-level reimplementation for the product path.

## 5. Implementation authority

### Frozen

- accepted `(n1,n2,n3)/n` flexible architecture and defaults;
- stage-scoped semantic dependency/invalidation from Rework 1, strengthened here by positive preparation identity;
- historical validation before migration/re-authentication;
- exact continuation and cross-horizon checkpoint incompatibility;
- corrected SIZE-FIDELITY final-screen/full-reference and equivalence semantics;
- target-size candidate ladder, MVQUAL authority, funnel cardinalities, paired seed behavior, target-only ranking, and unrelated target-size-v5 science;
- GPU/full production qualification remains deferred to the existing final qualification boundary.

### Delegated

- exact helper/function/type names for the positive projection;
- whether the projection is assembled directly from normalized config or from existing resolved preparation policies, provided there is one semantic authority and stable deterministic serialization;
- exact current schema bump if serialized receipt/fingerprint shape materially changes;
- test fixture organization and bounded harness mechanics.

### Reopen only on evidence

Reopen only the affected design surface if repository evidence proves that a field currently classified as downstream-only can actually change prepared DATA7/DATA8 bytes/topology, or that a preparation-owned field cannot be reconstructed/validated safely from existing historical receipts. Do not reopen the flexible-fidelity scientific architecture merely because a migration path is inconvenient.

## 6. Initially expected affected behavioral surface

Primary:

- `mdstats/training_data/_campaign_cli_core.py`;
- preparation restart receipt schema/validation/re-authentication;
- DATA7/DATA8 candidate/materialization reuse identity consumers;
- target-size study/candidate authority consumers if needed to preserve the dependency frontier;
- `mdstats/training_data/size_fidelity.py` current semantic strings/docstrings/errors.

Tests/integration likely include:

- `tests/test_mlff_flexible_fidelity.py`;
- `tests/test_mlff_campaign_performance.py`;
- `tests/test_mlff_campaign_cli.py` and semantic orchestration/status tests;
- target-size topology/persistence/continuation tests;
- SIZE-FIDELITY tests;
- real-boundary assembled integration tests added or extended for A/B/C/D1/D2/D3.

Current documentation/config comments are affected only where fixed-fidelity wording remains. Historical/archive documents are not rewrite targets.

Implementation must re-derive the final affected surface from the assembled diff/callers/consumers before final regression.

## 7. Task-specific acceptance

In addition to Protocol 5.5.0 functional acceptance:

- prove absence of whole-config/negative-filter over-invalidation on preparation compatibility;
- prove `n` does not enter preparation identity while remaining authenticated by TRAIN2 schedule/training identity;
- prove tuple/horizon changes do not change compatible DATA8 materialization authority solely because downstream screen geometry changed;
- prove historical fixed target-size evidence cannot masquerade as new flexible evidence;
- prove current runtime source no longer presents fixed 3/10/30 as current semantics;
- run A/B/C/D1/D2/D3 and final affected regression on one final commit;
- run repository-required checks and broaden to the full available suite if the final affected surface cannot be bounded confidently.

Production qualification: **deferred**. Do not run long data-heavy GPU qualification during this repair. Bounded functional/integration checks and ordinary accelerator smoke tests remain allowed where required by repository tests.

## 8. Implementation sequence and gates

### R2W0 - Characterize the remaining blocker

Add/confirm the failing `n:30 -> 40` preparation-identity reproducer and audit the exact current preparation dependencies. Classify fields by preparation-owned versus downstream-only semantics before changing the fingerprint.

Closure: failing reproducer or structural proof exists; no unknown identity consumer on prepare/preflight/DATA8 reuse remains.

### R2W1 - Positive preparation identity and invalidation frontier

Implement O14/O15. Preserve existing historical validation and corrected flexible-fidelity science.

Stage-local semantic closure: one preparation identity authority; no downstream-only `n`/fidelity leakage; no unsafe reuse widening.

Stage-local functional closure: focused fingerprint/receipt/migration tests plus affected prepare/preflight/materialization/status/continuation regression. D1 and D2 upstream-reuse portions must pass before dependent closeout work proceeds.

### R2W2 - Semantic-language cleanup

Implement O16 after executable identity behavior is stable. Scrub current runtime/current docs/config comments only; preserve explicit historical compatibility evidence.

Closure: structural search/classification and focused nondefault diagnostic tests pass. Documentation-only edits do not force unnecessary rerun of unchanged executable regression evidence, but any executable string/control-path edits receive the relevant focused checks.

### R2W3 - Final assembled acceptance

Execute O17 A/B/C/D1/D2/D3 on the assembled candidate. Then reconcile all parent/Rework1/Rework2 obligations, re-derive the final affected behavioral surface, run fresh complete affected-surface regression, integration, and repository-required checks on the same candidate.

No workplan may be called complete while any required case/check is unexecuted or newly failing on the affected surface.

### R2W4 - Closeout

Only after R2W3 passes: update any final current documentation generated descendants if needed, verify tracked generated artifacts affected by this repair, archive/supersede the flexible-fidelity workplans according to repository policy, and prepare the implementation handoff. Do not perform full production GPU qualification here.

## 9. Design handoff closure

The review findings map losslessly to O14-O17 and R2W0-R2W4:

- `n` preparation-identity leakage -> positive preparation ownership + exact frontier tests;
- missing `n` perturbation evidence -> mandatory focused and D2 assembled acceptance;
- stale fixed-fidelity current language -> semantic scrub + structural absence/classification;
- unproven assembled gates -> mandatory final A/B/C/D1/D2/D3 + fresh final regression/integration.

All previously accepted flexible-fidelity scientific/state decisions remain frozen. No material review finding or known cross-module consequence is intentionally omitted.

## 10. Risks / redesign triggers

- A training/config field that appears downstream-only may actually control preparation variant topology. Evidence of that dependency requires adding it to preparation identity, not abandoning stage-scoped identity.
- Historical receipts may lack enough evidence to prove compatibility for a particular campaign generation. Such a case must fail closed at the narrowest safe rerun boundary; it does not justify blanket recomputation for all campaigns.
- If final assembled tests expose a new scientific/state-machine defect unrelated to identity, route it as a new bounded finding; do not weaken SIZE-FIDELITY or continuation invariants to make the suite pass.
