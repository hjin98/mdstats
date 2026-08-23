# TARGET-SIZE-V5-PERF-PRESERVE1 — Restore preserved parallelization and performance contracts

**Status:** complete
**Current authority:** `docs/arch_manuals/mlff_training_data/50_target_multiview.md`, `docs/arch_manuals/mlff_training_data/60_execution_performance.md`, `workplans/archive/PAR90_FULL_PARALLELIZATION_WORKPLAN.md`, `workplans/archive/DOC-MVSEL2_HARDEN1_V3.md`
**Target branch/base:** uploaded `mdstats-feat-target-size-v5-redesign (5)` source package

## Objective

Close the performance-preservation gaps found during the target-size v5 architecture review without changing scientific selection, repair, qualification, or target-size semantics. Restore the accepted MVSTATE2-to-REPAIR2 continuation optimization inside the canonical REPAIR2 scientific owner; make structural-selection execution consume the campaign-authorized resource snapshot rather than independently reconstructing a default 90% budget; and repair performance regression tests whose monkeypatch seams were invalidated by the `campaign_cli` facade split.

## Invariants

- MVSEL2, REPAIR2, MVQUAL2, and target-size v5 scientific digests, ordering, coverage, hard-obligation, and 3/10/30 halving semantics remain unchanged.
- `target_multi_view_repair_v2` remains the only REPAIR2 scientific owner. No campaign-side candidate scoring, proposal generation, repair mutation loop, or duplicate scientific authority is reintroduced.
- Pure-selector MVSTATE2 state may be restored only while REPAIR2 has not diverged from MVSEL2. After the first accepted repair swap, later selector checkpoints are never restored.
- Restoring a checkpoint at rung `N` must still repair that rung's active shell; a restored selected count of `N` must not be interpreted as completion of the rung.
- Missing, incompatible, corrupt, or unavailable MVSTATE2 checkpoints fall back to exact selected-prefix forward replay.
- Automatic CPU capacity remains `max(1, floor(cpu_fraction * runtime_available_threads))`; explicit worker settings are caps inside that budget.
- Structural selection may reduce width for task count, dynamic membership-provider serialization, or measured autotuning, but may not silently increase the campaign CPU fraction.
- Native/OpenMP, BLAS, structural-worker, tree-worker, and Python-worker nesting protections remain intact.
- GPU behavior is unchanged and is not qualified by this CPU-only closeout.

## Scope

Included:

- `mdstats/training_data/target_multi_view_repair_v2.py`
- `mdstats/training_data/mvsel2_hardening_runtime.py`
- `mdstats/training_data/structural_selection.py`
- `mdstats/training_data/data6_bundle.py`
- `mdstats/training_data/_campaign_cli_core.py`
- focused REPAIR2/MVSTATE2, resource-authority, DATA6, and facade regression tests
- stale performance-test patch points that must target the true `_campaign_cli_core` semantic owner

Excluded unless required by a failing invariant:

- changes to target-size v5 candidate/halving policy;
- new MVSEL2 per-domain width scheduling;
- new MVQUAL cross-domain scheduling;
- MVIDX full-authority restore redesign;
- GPU qualification or accelerator-policy changes.

## Gates

### G0 — Freeze regression evidence and ownership

**Goal:** Establish exact pre-change behavior and the accepted historical contracts.

**Work:**

- Reconfirm the archived MVSTATE2/REPAIR2 continuation contract and PAR90 resource authority.
- Run the focused current tests that cover REPAIR2 ownership, checkpoint behavior, resources, and structural execution.
- Record baseline timing for a representative checkpoint-capable REPAIR2 fixture where stable enough to compare work avoided rather than relying on noisy microseconds alone.

**Acceptance:**

- Scientific baseline digest/trace is reproducible.
- The production bypass of selector checkpoints and the structural resource re-detection path are directly demonstrated.

### G1 — Canonical rung-aware MVSTATE2 reuse in REPAIR2

**Goal:** Restore selector-checkpoint reuse without duplicating repair science or skipping the restored rung's active shell.

**Work:**

- Replace the insufficient single `initial_state + selected_count` continuation interpretation with canonical rung-aware checkpoint consumption.
- Before divergence, allow REPAIR2 to restore an authenticated selector state for the current materializable rung, set the active shell start from the previous repaired rung, and execute repair for the current shell without replaying that rung's selector extension.
- When no rung checkpoint exists, extend the current state by exact selected-prefix replay.
- After the first accepted repair swap, carry repaired mutable state forward and ignore all later pure-selector checkpoints.
- Expose execution-only progress/telemetry showing checkpoint restore count/state mode; keep all such metadata outside scientific digests.
- Route production `mvsel2_hardening_runtime` through authenticated rung states and the canonical REPAIR2 API.

**Acceptance:**

- Cold replay and checkpoint-assisted executions have identical plan digest, repaired order, rung coverage, obligations, and swap trace.
- A restored checkpoint at rung `N` still processes shell `[previous_size, N)`.
- No checkpoint is restored after first repair divergence.
- Corrupt/missing checkpoints fail closed to replay rather than changing science.
- Existing single-owner tests prove no campaign-side repair loop exists.

### G2 — Single campaign resource authority for structural selection

**Goal:** Prevent structural selection from silently reconstructing a default 90% CPU budget when the campaign authorizes another fraction.

**Work:**

- Add an execution-only resource snapshot parameter through DATA6 to the built-in structural provider.
- Use the supplied `SystemResourceSnapshot` for worker admission and stage scope.
- Preserve standalone-provider behavior by detecting resources only when no caller snapshot is supplied.
- Pass `_performance_resources(cfg)` from the production materialization path.

**Acceptance:**

- A campaign resource snapshot with a non-default CPU fraction bounds structural workers to that snapshot.
- Explicit structural worker settings remain caps inside the campaign budget.
- Existing structural autotuning and nested-thread protection tests remain green.

### G3 — Restore truthful performance regression seams

**Goal:** Ensure tests patch the actual orchestration owner after the `campaign_cli` facade split.

**Work:**

- Update affected tests to patch `campaign_cli._core` for globals resolved by functions defined in `_campaign_cli_core`.
- Retain public facade assertions where the facade itself is the behavior under test.
- Do not add runtime indirection solely to preserve obsolete monkeypatch locations.

**Acceptance:**

- Previously false-negative/false-positive performance/restart tests exercise the real production dependency seams.
- No new facade/core duplicate authority is introduced.

### G4 — Integrated validation and closeout

**Goal:** Demonstrate that v5 preserves the accepted CPU-performance architecture after the fixes.

**Work:**

- Run focused REPAIR2/MVSTATE2, PAR90/resources, structural selection, DATA6, target-size v5, halving, and staged-evaluation tests using the supplied dependency bundle/environment.
- Run a broader non-GPU regression slice around MLFF preparation and performance-sensitive orchestration.
- Compare checkpoint-assisted REPAIR2 against cold replay using exact digests/traces and execution telemetry/work counts; report timing only where representative and stable.
- Reconcile durable architecture text only if current accepted behavior is documented incorrectly.
- Archive this workplan after all gates pass.

**Acceptance:**

- Focused and integrated suites pass with no scientific digest drift.
- Checkpoint-assisted REPAIR2 demonstrably avoids selected-prefix replay work before divergence.
- Structural workers never exceed the supplied campaign budget.
- No unresolved material CPU-performance regression attributable to the v5 enforcement remains in scope.

## Completion evidence

- Canonical REPAIR2 now restores authenticated MVSTATE2 state lazily at the current materializable rung, repairs that rung's active shell, and permanently stops pure-selector restoration after the first accepted repair swap.
- Exact regression fixture: cold and checkpoint-assisted REPAIR2 both produced digest `e4bbee2b314952d44467453051c21e3008f2a7dcf2144be76edce54bfa90e57e` with three accepted swaps; checkpoint assistance reduced repair-side selector scoring calls from 19 to 15.
- DATA6 structural selection now consumes the caller-authorized `SystemResourceSnapshot`; a non-default 25% / two-thread campaign budget is covered by regression tests and bounds an explicit eight-worker request to two workers.
- Performance/restart tests now monkeypatch `_campaign_cli_core`, the real global namespace of the re-exported orchestration functions, rather than the facade copy.
- Using an isolated environment populated from the supplied dependency bundle (`ase 3.29.0`, `mace-torch 0.3.16`, `python-hostlist 2.3.0`), the focused performance/v5 integration set completed with 188 passed and one external-model skip.
- Broader repository collection is not a release signal for this patch: the uploaded source package lacks `tests/data/mesh_topology_revision_stage1_cases.json`, and retained historical MLFF specification tests still assert superseded release identities such as `0.20.140a0` against the current `0.20.242a0`. Neither issue is caused by this transition.
- Current architecture/specification text already states the accepted MVSTATE2 selector-to-REPAIR2 reuse and single resource-scope principles, so no durable documentation rewrite is required.

## Closeout

When all gates pass:

1. update current architecture documentation only where its present-tense contract needs correction;
2. keep benchmark/correctness evidence in the existing test/benchmark mechanisms rather than creating redundant authority;
3. mark this workplan complete and move it to `workplans/archive/`;
4. export one git-format patch against the uploaded source-package baseline.
