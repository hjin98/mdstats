---
kind: implementation-workplan
workplan_id: MLCV-LIFECYCLE-FIX1
protocol_version: 5.4.0
---

# MLCV-LIFECYCLE-FIX1 — Lifecycle authority reconciliation correction

**Status:** active — design frozen for implementation
**Branch:** `feat/mlff-end-to-end-performance-v1`
**Reviewed source baseline:** `2f3f5371c64188781ea9ee4542f674bf75d0650a`
**Priority:** blocking correctness fix for TARGET-SIZE-V5 training entry; independent of DATA78 closeout and PERF1 performance closeout

## Objective

Correct MLCV lifecycle reconciliation so ordinary training and TARGET-SIZE-V5 may reuse restored MLCV-origin artifacts without synthesizing invalid campaign lifecycle provenance, while preserving strict migration semantics, lifecycle digest/idempotence guarantees, and existing MLCV compatibility behavior.

The fix must remove the authority-ownership defect in shared lifecycle infrastructure. It must not special-case TARGET-SIZE-V5, epoch 3, or the observed exception.

## Diagnosis

The observed target-size run reaches valid pre-training authorities:

- `TARGET-DATA2B` authority verifies;
- `TARGET-SIZE-V5` authority verifies with `Q=[512, 1024, 2048, 4096, 8192]` and `outcome=awaiting_epoch_3`;
- DATA4/DATA6 restore completes;
- failure occurs before the epoch-3 training jobs launch.

The failing path is:

```text
command_select_target_size
  -> _execute_train_current_authority
     -> _reconcile_mlcv_lifecycle_authority
        -> mdstats.build_mlcv_lifecycle_authority
           -> MlcvLifecycleAuthorityRecord.__post_init__
              -> TrainingDataInputError(
                   "MLCV lifecycle source strategy is unsupported."
                 )
```

The earliest violated invariant is ownership of `source_checkpoint_strategy`.

`MlcvLifecycleAuthorityRecord` correctly restricts historical MLCV source provenance to the supported MLCV strategies (`mlcv_nested_cv` and transitional `adaptive_topk`) and requires canonical requested lifecycle behavior. However, ordinary training reconciliation currently derives lifecycle source/requested strategy from the current campaign `evaluation.checkpoint_strategy`. Separately, lifecycle construction can be triggered by restored DATA8 bundle provenance whose `selection_strategy` is MLCV-derived. Those are different authorities:

```text
restored bundle provenance       -> historical origin of an artifact
current evaluation strategy      -> runtime policy of this invocation
campaign lifecycle authority     -> persistent lifecycle/migration state
```

The current reconciliation conflates them. Therefore an MLCV-origin restored bundle can trigger lifecycle construction while an unrelated current evaluation strategy is written as the historical MLCV source, causing the strict record constructor to reject the invalid candidate.

There is a second latent defect in the same fallback: when source is legitimately `adaptive_topk`, defaulting requested strategy to source would attempt `adaptive_topk -> adaptive_topk`, while the canonical lifecycle request must remain `mlcv_nested_cv`.

This is a shared lifecycle-authority defect, not a 3 -> 10 -> 30 halving/ranking defect and not a DATA4/DATA6 restore or cleanup defect.

## Engineering envelope

An acceptable correction must satisfy all of the following:

- TARGET-SIZE-V5 scientific semantics remain unchanged: exact 3/10/30 checkpoint boundaries, candidate sizes, seeds, fixed comparison cohort, ranking logic, and target-size authority digests are out of scope.
- `MlcvLifecycleAuthorityRecord` validation remains strict. Do not broaden valid MLCV source strategies to admit unrelated runtime/evaluation strategies.
- Historical lifecycle provenance is owned by the lifecycle/migration mechanism, never reconstructed from an arbitrary current training invocation.
- Restored artifact provenance does not by itself create campaign-wide lifecycle state.
- Reuse of valid MLCV-origin DATA8/restored artifacts by a non-MLCV current campaign remains legal; it must not synthesize a new MLCV lifecycle authority merely because the artifact originated under MLCV selection.
- If a lifecycle authority already exists, reconciliation preserves its historical source provenance and canonical request rather than rewriting history from current configuration.
- Explicit legacy migration remains the owner of `adaptive_topk -> mlcv_nested_cv` provenance.
- Genuine MLCV operation remains canonical as `mlcv_nested_cv -> mlcv_nested_cv`.
- Reconciliation is deterministic and idempotent: identical effective state yields the same lifecycle content digest and does not create an authority conflict.
- Existing persisted lifecycle records that are valid under the current schema remain readable and authoritative.
- Do not introduce a second persisted lifecycle record, compatibility database, migration layer, scheduler, or target-size-specific lifecycle path.
- Functional regression/integration tests are required; full data-heavy/GPU production qualification remains deferred to final release qualification.

## Product design

### Authority separation

Retain the existing lifecycle record and migration machinery, but separate three decisions that are currently conflated:

1. **Lifecycle admission:** determine whether the current campaign actually has/needs MLCV lifecycle state.
2. **Historical source provenance:** if lifecycle state exists, obtain source strategy only from authoritative lifecycle/migration evidence.
3. **Current runtime policy compatibility:** check the invocation's current evaluation policy independently; it must not become historical lifecycle provenance merely because training is executing now.

A restored bundle whose `selection_strategy` records MLCV origin may contribute artifact provenance/reuse eligibility, but does not independently admit a campaign lifecycle.

### Required lifecycle states

The supported persistent lifecycle semantics remain:

```text
canonical MLCV:
    source_checkpoint_strategy    = mlcv_nested_cv
    requested_checkpoint_strategy = mlcv_nested_cv

legacy explicit migration:
    source_checkpoint_strategy    = adaptive_topk
    requested_checkpoint_strategy = mlcv_nested_cv
```

For an ordinary non-MLCV campaign reusing MLCV-origin restored bundles:

```text
no existing/explicit MLCV lifecycle intent
    -> no new lifecycle authority is synthesized
```

For an existing valid lifecycle authority:

```text
existing lifecycle provenance
    -> remains authoritative and is reconciled idempotently
```

### Implementation shape

Prefer the smallest ownership correction in the existing reconciliation/builder boundary. A small internal lifecycle-intent resolver/helper is acceptable if it materially clarifies the state model, but it must be nonpersistent and must not duplicate authority.

The implementation should conceptually distinguish:

```text
NONE               no lifecycle state should be created
EXISTING            preserve/reconcile existing lifecycle
CANONICAL_MLCV      create canonical mlcv_nested_cv lifecycle when genuinely required
LEGACY_MIGRATION    explicit adaptive_topk -> mlcv_nested_cv migration
```

Exact local API names and whether this is represented by branches, an enum, or a small helper are delegated to implementation.

The builder/record validator must remain a fail-closed final boundary. The caller must stop passing arbitrary `config["evaluation"]["checkpoint_strategy"]` as `source_checkpoint_strategy`.

## Implementation authority

### Frozen

Implementation must preserve these decisions:

- Fix shared MLCV lifecycle reconciliation; do not add a TARGET-SIZE-V5/epoch-specific workaround.
- Current evaluation checkpoint strategy and historical MLCV source provenance are distinct authorities.
- MLCV-origin restored bundle provenance alone does not synthesize campaign lifecycle state.
- Valid non-MLCV campaigns may reuse valid MLCV-origin artifacts without creating an MLCV lifecycle authority.
- Existing valid lifecycle authority owns historical provenance on restart/resume.
- Canonical requested lifecycle strategy is `mlcv_nested_cv` whenever a real MLCV lifecycle is produced.
- `adaptive_topk` is accepted only as historical legacy source for explicit/correctly evidenced migration to `mlcv_nested_cv`.
- Strict lifecycle-record validation must not be weakened.
- Lifecycle identity/digest/conflict handling remains deterministic and fail closed.
- No new persisted authority or compatibility subsystem.
- No change to TARGET-SIZE-V5 scientific ranking/halving semantics.

### Delegated

Implementation may choose:

- whether admission/provenance resolution is an internal helper, enum/state function, or direct structured branches;
- exact function signatures after removing the misleading source/requested fallback;
- whether obsolete optional parameters are deleted or retained temporarily with stricter internal semantics when required for compatible callers;
- exact focused test fixture organization and names;
- whether nonpersistent diagnostic messages are improved to expose lifecycle intent/source/current runtime policy separately.

Prefer deletion/consolidation over adding compatibility wrappers when callers can be migrated safely in the same change.

### Reopen only on evidence

Reopen only the affected design surface if implementation proves one of these assumptions false:

- a governed specification explicitly requires every reused MLCV-origin artifact to impose an MLCV lifecycle on the current campaign;
- a valid persisted lifecycle schema encodes additional historical source strategies not accounted for by current migration contracts;
- another production caller legitimately depends on current evaluation policy being persisted as lifecycle source provenance;
- existing lifecycle digest semantics cannot preserve valid records after correcting ownership without a migration decision.

If any trigger fires, stop dependent implementation, identify the governing contract/evidence, and redesign only the lifecycle admission/provenance surface. Do not relax record validation as a shortcut.

## Initially expected affected behavioral surface

Primary implementation surface:

- `mdstats/training_data/_campaign_cli_core.py`
  - `_execute_train_current_authority()`
  - `_reconcile_mlcv_lifecycle_authority()`
  - other callers that pass source/requested checkpoint strategy into lifecycle reconciliation;
- `mdstats/training_data/mlcv_migration.py`
  - lifecycle builder/record contracts only as needed to make ownership explicit; strict validation remains;
- lifecycle persistence/load/conflict code used by restart/resume;
- explicit MLCV migration command/path;
- target-size training entry because it exercises the shared train-current-authority path;
- ordinary train/evaluate flows that share lifecycle reconciliation;
- DATA8/restored-bundle reuse cases carrying `mlcv_nested_cv` or `adaptive_topk` artifact provenance.

The final affected surface must be re-derived from the assembled diff before closeout; tests/callers discovered transitively are included even if absent from this provisional list.

## Task-specific acceptance

Generic functional-acceptance requirements are inherited from Protocol 5.4.0.

### Focused lifecycle matrix

At minimum, executable tests must cover:

| Case | Required result |
| --- | --- |
| canonical MLCV source/request | accepted |
| legacy `adaptive_topk` source with canonical MLCV request | accepted |
| arbitrary non-MLCV source passed to lifecycle record | rejected |
| noncanonical requested lifecycle strategy | rejected |
| non-MLCV current config + non-MLCV restored bundles | no synthesized lifecycle |
| non-MLCV current config + MLCV-origin restored bundles | artifact reuse allowed; no synthesized lifecycle |
| genuine canonical MLCV campaign | canonical lifecycle produced |
| existing lifecycle + different current runtime/evaluation policy | existing historical provenance preserved |
| reconciliation repeated with unchanged authority | same lifecycle digest / no conflict |

Keep or strengthen negative constructor tests; do not rewrite them merely to make the new caller behavior pass.

### Explicit migration regression

Prove explicit legacy migration preserves:

```text
adaptive_topk -> mlcv_nested_cv
```

with correct source/requested fields and unchanged fail-closed validation of unsupported strategies.

### TARGET-SIZE-V5 integration regression

Add a fast integration path that reaches the real shared training-entry/lifecycle reconciliation boundary with:

```text
sizes  = [512, 1024, 2048, 4096, 8192]
seeds  = [1, 2]
epochs = 3 -> 10 -> 30
restored MLCV-origin bundle provenance present
current target-size campaign not admitted as an MLCV lifecycle solely by that provenance
```

Acceptance requires:

- TARGET-DATA2B verification succeeds;
- TARGET-SIZE-V5 verification succeeds;
- lifecycle reconciliation succeeds/no-ops according to actual lifecycle intent;
- the epoch-3 training jobs are allowed to launch;
- only exact boundary checkpoints may contribute to target-size ranking;
- continuation to the epoch-10 boundary does not rewrite lifecycle provenance or introduce a digest conflict.

The test may stub genuinely heavyweight model training after proving launch/continuation wiring, but it must not stub the lifecycle reconciliation/authority boundary being fixed.

### Affected shared-flow regression

After each material behavior-changing stage, run the relevant affected regression subset. Final assembled regression must cover at least:

- ordinary campaign training entry;
- target-size selection/training entry;
- restart/resume with existing lifecycle authority;
- MLCV canonical path;
- explicit legacy migration path;
- restored DATA8/bundle reuse carrying MLCV provenance;
- lifecycle authority persistence/digest/conflict handling.

Run repository-required broader checks. If the implementation diff reveals an impact that cannot be bounded confidently, broaden to the relevant full training-data/campaign suite.

Production qualification: **deferred**. This correction is functional lifecycle/authority logic and should be closed with focused, affected-surface, and integration tests. RTX 3090/data-heavy production qualification remains part of the final release handoff rather than this bug-fix gate.

## Implementation sequence

### L1 — Install reproduction and ownership-focused focused tests

- Add a minimal executable reproduction for the observed mixed state: MLCV-origin restored bundle + non-MLCV current evaluation policy + no genuine current MLCV lifecycle intent.
- Confirm the pre-fix path fails at lifecycle construction with the unsupported-source error.
- Add/retain strict constructor tests for valid/invalid source/requested combinations.

**Gate:** focused tests establish the defect and validator contract without changing production behavior.

### L2 — Correct lifecycle admission and provenance ownership

- Remove the fallback that treats current `evaluation.checkpoint_strategy` as lifecycle `source_checkpoint_strategy`.
- Stop restored artifact provenance from independently synthesizing campaign lifecycle state.
- Preserve existing lifecycle provenance when present.
- Produce canonical `requested_checkpoint_strategy="mlcv_nested_cv"` only when a real lifecycle is admitted.
- Keep explicit migration as the owner of `adaptive_topk` historical provenance.
- Consolidate/delete misleading reconciliation parameters or helper branches where safe.

**Stage-local affected regression:** focused lifecycle matrix + ordinary training entry + restart/existing-lifecycle cases.

### L3 — Reconcile all shared callers and migration behavior

- Audit every `_reconcile_mlcv_lifecycle_authority()`/builder caller for the same ownership conflation.
- Ensure canonical MLCV operation and explicit legacy migration produce identical valid lifecycle semantics to the accepted contract.
- Verify deterministic digest/idempotence and fail-closed conflicting-authority behavior.

**Stage-local affected regression:** MLCV canonical/migration/restart/persistence tests plus shared train/evaluate caller tests touched by the change.

### L4 — Close TARGET-SIZE-V5 real integration boundary

- Add/extend fast target-size integration coverage through verified target authorities into the actual training-entry/lifecycle boundary.
- Prove epoch-3 launch with restored MLCV-origin provenance.
- Prove continuation toward epoch 10 does not rewrite lifecycle provenance.
- Confirm no change to exact 3/10/30 ranking eligibility semantics.

**Stage-local affected regression:** target-size selection/training integration subset and any directly affected DATA8/reuse tests.

### L5 — Final affected-surface reconciliation and closeout

- Re-derive the affected behavioral surface from the assembled implementation rather than relying only on this initial list.
- Run final affected-surface regression and real integration boundaries.
- Run repository-required checks/broader training-data suite when impact cannot be bounded.
- Update durable lifecycle/configuration documentation only if the corrected ownership contract is absent or contradicted; do not create documentation solely to narrate the bug.
- Record production qualification as deferred, not failed or omitted.

**Closeout condition:** the original target-size mixed-provenance scenario reaches epoch-3 training entry without synthesizing invalid lifecycle state; canonical MLCV and legacy migration remain valid; restart/persistence is idempotent; no lifecycle validator was weakened.

## Risks / redesign triggers

- **Hidden compatibility dependency:** a caller may have relied on the incorrect fallback to create lifecycle state. Treat this as evidence to inspect ownership, not as a reason to preserve the fallback automatically.
- **Persisted invalid records:** if target hosts already contain lifecycle records that could only have been produced by now-invalid semantics, do not silently normalize them. Determine whether they are actually constructible under released code and whether explicit migration/diagnostic handling is required.
- **Artifact-vs-campaign provenance ambiguity:** if a governing spec intentionally couples MLCV-origin DATA8 artifacts to campaign lifecycle state, that contract must be surfaced before changing reuse policy.
- **Digest drift:** if correcting ownership changes the digest of an otherwise valid existing lifecycle, identify whether the prior record was genuinely equivalent. Preserve valid authority; do not overwrite it merely to match the new candidate.

No other architecture, target-size science, DATA7/DATA8 materialization behavior, or PERF1 performance machinery is reopened by this workplan.
