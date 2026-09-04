---
kind: implementation-workplan
workplan_id: CODE-MLFF-P4-CAMPAIGN-DEMO-BLOCKER-REPAIR
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P4
protocol_version: 5.14.0
status: active
baseline_observed: deaeff0a97a89858694e4f0a31a21a1ad2c8efbb
created_date: 2026-09-04
---

# P4 Campaign Demonstration Blocker Repair Workplan

## Objective / problem invariants / non-goals

The immediate stakeholder objective is operational: restore the already-accepted current MLFF campaign path quickly enough to obtain a successful real campaign demonstration, without reopening the target-size architecture or adding compatibility machinery merely to suppress exceptions.

Two production-reachable blockers are demonstrated on the current P4 cutover path:

1. **Manifest approval control-flow regression.** The public parser contract says `prepare --approve-manifest` approves the exact reviewed manifest and returns, while `--continue-after-approval` explicitly opts into continuing the preparation pipeline in the same invocation. The current `execute_current_prepare()` passes `approve_manifest` into `_prepare_catalog()` but does not honor `continue_after_approval`; after approval it continues into P1/P2 authority construction instead of returning.
2. **Neutral regime-resolution type-contract mismatch.** `mdstats.training_data.neutral_substrate.partition` reuses legacy `training_data.partition._regime_label()`. That helper was written for legacy `TrainingDataSource` and falls back to `source.production_status`. Current neutral `SourceRecord` deliberately has no such field. A real source without an explicit `regime` assertion therefore raises `AttributeError` while `build_neutral_unit_catalog()` is constructing the current neutral statistical substrate.

### Tier-1 product/problem invariants

- `prepare` must honor its public operator contract. Approval-only invocation records approval and returns; continuing after approval requires the explicit continue flag or a subsequent plain `prepare` invocation.
- Current P1 neutral scientific construction must not crash on a valid `SourceRecord` merely because the source carries no optional explicit regime annotation.
- Missing scientific categorical information must be represented explicitly rather than fabricated from obsolete machinery. A missing current neutral regime resolves to the existing explicit unresolved category, not to invented legacy state.
- Existing target-size scientific semantics, exact P1/P2/P3 ownership, destructive-generation cutover, P4 CampaignStore authority, and post-selection semantics remain unchanged.
- The repair must preserve real manifest digest approval, source/frame authority validation, and all existing VASP recovery behavior.

### Non-goals

This repair does **not**:

- redesign P1 source authority, P2 statistics, P3 execution, P4 persistence/cutover, P5+ post-selection logic, or storage architecture;
- add `production_status`, `production_assessment_status`, or other legacy DATA2 qualification fields to neutral `SourceRecord` merely to satisfy the old helper;
- migrate or version-bump `SourceRecord` or neutral persistence schemas absent independent evidence that a current P1 scientific fact is genuinely missing;
- change legacy DATA5 `_regime_label()` semantics for legacy `TrainingDataSource` callers;
- suppress, downgrade, or otherwise change `VelocityReconstructionWarning` or `InterruptedXmlWarning`; those warnings are not the cause of the demonstrated crash;
- broaden into cleanup, refactoring, or test-suite modernization unrelated to the two blockers;
- treat a successful production run as a substitute for focused/regression/integration acceptance.

## Frozen high-level architecture and engineering envelope

The existing accepted P1/P4 architecture remains Frozen for this repair:

```text
manifest + lower-level source/frame inputs
  -> current compatibility-neutral SourceAuthority / SourceRecord
  -> CanonicalFrameAuthority
  -> NeutralFeatureEvidence
  -> NeutralStatisticalBase
  -> P2 experiment definition/common preparation
  -> P4 CampaignStore current-generation binding
```

Public current target-size orchestration remains:

```text
prepare
  -> current P1/P2 authorities + one common preparation
  -> selects nothing

select-target-size
  -> sole paired-seed screening owner
```

The repair must preserve these ownership boundaries:

- manifest approval remains an operator gate on the exact manifest digest;
- current `prepare` remains the real production owner for current P1/P2 substrate construction;
- neutral source records remain compatibility-neutral current-generation records rather than adapters for legacy `TrainingDataSource`;
- neutral partition construction owns current condition/regime categorization and must consume current-authority inputs only;
- legacy partition behavior remains isolated from the current neutral path.

No new persistence authority, compatibility adapter, fallback registry, wrapper state machine, or duplicate source record is justified.

## Implementation obligations and delegated solution space

### A. Restore approval-only `prepare` control flow

**Concern / rationale.** The public CLI currently advertises an approval-only action but production P4 orchestration ignores the return boundary. This can unexpectedly launch expensive preparation work and violates the operator workflow documented as two separate invocations.

**Required end state.**

For a manifest requiring approval:

```text
prepare --approve-manifest
  -> authenticate/review current manifest path
  -> record approved_manifest_digest for the exact manifest
  -> leave no running prepare operation behind
  -> do not construct/bind current P1/P2 target-size authorities
  -> return success with an actionable instruction to run plain prepare
```

For:

```text
prepare --approve-manifest --continue-after-approval
```

approval is recorded and the same invocation continues through normal current preparation.

A subsequent plain `prepare` after approval must continue normally and remain idempotent under unchanged inputs.

**Operational-state constraint.** An approval-only success must not leave the `prepare` stage marked `RUNNING` or falsely mark the scientific substrate `COMPLETE`. Use the existing campaign-stage model; `WAITING` with an actionable reason is the preferred current-state representation if the current owner has already entered the running stage before approval completes. Equivalent simpler sequencing that avoids entering `RUNNING` before the approval-only return is also valid.

**Delegated solution space.** The exact branch placement is delegated. Prefer altering the current `execute_current_prepare()` control flow over adding a second approval helper or wrapper. Reuse `_prepare_catalog()` and the existing manifest metadata authority rather than reimplementing approval.

**Anti-shortcut.** Do not make the parser/help text match the buggy behavior by redefining `--approve-manifest` to continue. The operator contract and user guide already distinguish approval-only from `--continue-after-approval`.

**Acceptance evidence.**

- focused test: approval-only records the exact digest and returns 0;
- focused test: approval-only does not invoke/build current target-size authorities or advance the current target-size generation;
- focused test: approval-only leaves `prepare` non-running and non-complete;
- focused test: `--approve-manifest --continue-after-approval` reaches normal preparation;
- focused test: plain `prepare` after approval reaches normal preparation;
- affected CLI manifest-approval regression remains green.

### B. Remove the neutral path's dependency on legacy `production_status`

**Concern / rationale.** The crash is a current/legacy object-contract mismatch, not missing defensive attribute handling. Retaining the legacy helper through duck typing would preserve the wrong dependency and can silently collapse current sources into a different regime category.

**Required end state.** Current neutral partition regime resolution must use only facts present in the current neutral contract. For the existing neutral regime inputs, preserve this deterministic precedence:

```text
nonempty per-frame regime_by_frame_uid override
  -> nonempty source assertions["regime"]
  -> "unresolved"
```

A valid current `SourceRecord` with no explicit regime annotation must therefore construct a neutral condition using the explicit unresolved category rather than raising or reading legacy production-assessment state.

This repair intentionally does **not** reinterpret old `TrainingDataSource.production_status` as a current neutral scientific fact. If implementation discovers concrete current P1 evidence that source-level production assessment is independently required to preserve accepted scientific behavior, stop this obligation and reopen only the P1 source/regime authority surface; do not smuggle the field back through `getattr`, adapter objects, or assertions.

**Delegated solution space.** Prefer removing the neutral module's import/use of legacy `_regime_label` and resolving neutral regime at the neutral partition owner. The exact private helper/inlining is delegated. Do not modify the legacy helper unless a separate legacy regression proves a genuine defect there.

**Anti-shortcuts.** The following are not acceptable closures:

- `getattr(source, "production_status", None)` in the neutral path;
- adding a dummy/default `production_status` property to neutral `SourceRecord`;
- adding a compatibility subclass/wrapper so the old helper accepts both record families;
- changing all tests/fixtures to inject `assertions=(("regime", "production"),)` and thereby continue masking the missing-regime path;
- fabricating `"production"`, `"accepted"`, or another value when no current-authority regime fact exists.

**Acceptance evidence.**

- direct bug reproducer: a real/current `SourceRecord` with no `regime` assertion and no per-frame override reaches `build_neutral_unit_catalog()`/`build_neutral_statistical_base()` without exception and carries `regime == "unresolved"` where applicable;
- precedence test: a nonempty source assertion remains honored;
- precedence test: a nonempty per-frame override wins over the source assertion;
- existing neutral statistical/partition behavior remains unchanged for already-annotated fixtures;
- structural inspection confirms the current neutral partition path no longer calls a helper whose correctness requires legacy `production_status`.

### C. Close the fixture blind spot at the real P4 boundary

**Concern / rationale.** Existing P1/P4 integration fixtures commonly seed `assertions=(("regime", "production"),)`, so the legacy helper returns before touching the invalid fallback. P4 integration therefore remained green while the real no-annotation path was broken.

**Required end state.** At least one assembled P4 current-`prepare` regression must exercise the real current production owner with a source lacking a `regime` assertion. The test must reach `execute_current_prepare()`/real current authority construction rather than only calling a new local resolver.

The fixture may be parameterized or minimally specialized; do not duplicate the whole campaign harness merely to vary one manifest assertion.

**Acceptance boundary.** The claim under acceptance is the real current P4 `prepare` orchestration reaching the real P1 neutral owners. Expensive MACE training/inference remains outside this prepare-only boundary and need not run. Do not patch `build_current_target_size_authorities()`, `build_neutral_statistical_base()`, or the regime resolver itself to return desired values.

### D. Preserve warnings and interrupted-XML recovery behavior

The demonstrated VASP warnings are observational inputs, not this crash's owner. The repaired candidate must continue to accept the existing interrupted-XML recovery behavior according to current source-quality rules. Do not suppress these warnings to make the demonstration output look cleaner.

If the real campaign later fails because recovered data violate a separate existing scientific gate, report that gate as a new concrete blocker; do not weaken the gate under this workplan merely to obtain a demonstration.

## Implementation authority

### Frozen

- exact-manifest approval remains mandatory where current policy requires it;
- `--approve-manifest` is approval-and-return by default;
- `--continue-after-approval` is the explicit same-invocation continuation opt-in;
- current P1 source authority remains the compatibility-neutral `SourceRecord` contract already accepted by P1;
- current neutral partition construction must not require legacy `TrainingDataSource` fields;
- absence of an explicit current regime fact is represented as `"unresolved"`, never fabricated;
- P1/P2/P3/P4 scientific and persistence architecture remains unchanged;
- real-boundary acceptance must exercise current P4 `prepare` and real neutral authority construction.

### Delegated

- exact placement of the approval return branch and stage transition;
- exact local neutral regime resolver shape/name;
- whether the current no-regime regression extends an existing fixture or adds one minimal fixture;
- test parametrization and exact error/progress wording;
- local import/comment cleanup caused by removing the invalid neutral-to-legacy dependency.

### Reopen only on evidence

Reopen only the smallest affected design surface if implementation demonstrates one of the following:

- current P1 scientific semantics genuinely require source-level production-assessment state that is absent from `SourceRecord` and cannot be derived from existing current authorities;
- the existing campaign-stage model cannot represent a successful approval-only return without leaving consequential stale state;
- a supported current caller intentionally relies on `--approve-manifest` continuing without `--continue-after-approval`, contradicting the parser/user-guide contract;
- removing the neutral dependency on legacy `_regime_label` exposes another current scientific caller whose required categorical semantics differ materially from override -> assertion -> unresolved.

Do not reopen target-size selection, storage, post-selection, VASP recovery, or unrelated source semantics without direct evidence.

## Affected surface and task-specific acceptance

Initially expected executable surfaces:

- `mdstats/training_data/campaign_target_size_runtime.py` — current `prepare` control flow;
- `mdstats/training_data/neutral_substrate/partition.py` — current neutral regime resolution;
- `tests/test_mlff_campaign_cli.py` — manifest approval behavior where applicable;
- `tests/test_mlff_neutral_scientific_substrate.py` — no-regime/precedence reproducer;
- `tests/test_mlff_target_size_p4d_runtime_cutover.py` — real current `prepare` boundary;
- `tests/test_mlff_target_size_p4g_assembled_integration.py` only if fixture reuse or assembled lifecycle coverage is changed/needed;
- parser/help/user-guide/spec surfaces only if implementation reveals drift. The current documented approval behavior is already the target, not a documentation change request.

Final implementation must re-derive this surface after edits. Do not run the entire repository suite merely by habit if the final diff remains bounded; do run broader regression if the implementation unexpectedly touches shared legacy partition/source semantics.

### Minimum high-signal functional closure

Run, at minimum, the cheapest tests that establish the full affected behavior:

```text
1. focused approval-only / continue-after-approval tests
2. focused neutral no-regime + precedence tests
3. complete neutral-scientific-substrate affected regression
4. P4-D current prepare/cutover affected regression, including one no-regime source
5. P4-G assembled current lifecycle regression if the shared fixture or downstream assembled path was changed
```

Existing unaffected expensive P3/P5/P6 numerical qualification evidence is reusable. Full GPU/production qualification is not required for code acceptance.

### Real campaign demonstration

After software closure on the same candidate, run the actual campaign path as an operational demonstration:

```text
prepare --approve-manifest       # only if approval is currently required; must return
prepare                          # must complete current P1/P2 substrate
select-target-size               # proceed through the real current screening owner
cross-validate                   # when selection succeeds and current policy requires it
train-production                 # when CV acceptance permits it
```

Use the user's real campaign configuration and source dataset; do not alter scientific thresholds, candidate sizes, quality gates, or recovered-XML handling merely to force completion.

A new failure discovered by this real run may be repaired under this same emergency workplan only when all of the following hold:

- it is a direct implementation-local blocker on this already-accepted current campaign path;
- the owning cause is clear and bounded;
- the repair preserves all Frozen architecture and scientific semantics above;
- it receives a focused reproducer plus affected regression before the run resumes.

If a new failure requires a schema/authority redesign, scientific-policy change, target-size algorithm change, or acceptance weakening, stop and return to Software Design rather than stacking an emergency workaround.

## Implementation sequence and genuine redesign / simplification triggers

### Stage 1 — approval control-flow repair

1. Reproduce the approval-only continuation bug at the public/current prepare boundary.
2. Alter the existing current prepare control flow so approval-only records the exact digest and exits with truthful non-running stage state.
3. Prove approval-only, approval+continue, and subsequent plain prepare behavior with focused tests.
4. Run the affected manifest/prepare regression subset before Stage 2.

### Stage 2 — neutral regime owner repair

1. Reproduce the `SourceRecord.production_status` failure using a current source with no `regime` assertion.
2. Remove/narrow the neutral path's dependency on the legacy helper rather than adapting the new record to the old contract.
3. Prove override -> assertion -> unresolved semantics and existing annotated behavior.
4. Run the neutral-substrate affected regression before Stage 3.

Stages 1 and 2 are independent enough to fault-localize separately, but may be committed together if that is materially faster and both stage-local test sets are executed before assembled acceptance.

### Stage 3 — assembled P4 prepare reclosure

1. Ensure at least one real P4 `prepare` fixture omits the masking `regime` assertion.
2. Execute current `prepare` through real P1/P2 owners and current CampaignStore.
3. Confirm no target size is selected and no retired authority is reintroduced.
4. Run the bounded assembled P4 affected regression on the final executable candidate.

### Stage 4 — real campaign demonstration

Run the actual campaign from the appropriate current state. Treat the first new failure, if any, as evidence: repair it only under the bounded emergency rule above, otherwise stop for Design.

### Active simplicity trigger

If implementation starts adding compatibility properties to `SourceRecord`, generic dual-record adapters, approval wrapper functions/state, or special-case fallbacks around the same P4 path, stop. The correct direction is to remove the invalid legacy dependency or alter the existing current owner, not to preserve accidental machinery.

### Genuine Design-reopen trigger

Reopen Design only if evidence shows the accepted current P1/P4 authority boundary itself lacks a required scientific/operator capability. Ordinary missing branch logic, stale helper reuse, fixture masking, or another bounded implementation bug remains implementation repair.

## Design handoff verdict

**PASS — ready for immediate implementation.**

The two known blockers have clear owning causes, the repair does not require a high-level architecture change, the fastest justified solution is alteration/removal of the faulty current control/dependency edges, and the acceptance boundary is small enough to close before resuming the real campaign demonstration.
