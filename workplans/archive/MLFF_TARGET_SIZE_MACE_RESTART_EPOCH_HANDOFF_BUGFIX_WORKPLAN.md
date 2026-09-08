---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-MACE-RESTART-EPOCH-HANDOFF-BUGFIX
protocol_version: 5.15.0
status: implementation-ready
---

# MLFF Target-Size MACE Restart-Epoch Handoff Bug-Fix Workplan

## Status

**PASS / implementation-ready.**

This is a bounded correctness repair for the real target-size TRAIN2 continuation launcher. It does **not** reopen target-size scientific policy, configurable fidelity, P3 restart ownership, TRAIN2 exact-continuation semantics, checkpoint format, EVAL2, precision policy, or the qualified MACE 0.3.16 restart correction.

Diagnosed against `fix/mlff-prepared-common-atomic-reference-order` at parent commit `69aa1c5b85997d6f6e89cf30bef6540f4c30eb55`.

## 1. Objective, problem invariants, and non-goals

### 1.1 Observed production failure

`select-target-size` completes and commits its first configured fidelity boundary, then fails when the first surviving candidate is resumed for the next boundary. The real failure is:

```text
KeyError: 'MDSTATS_MACE_RESTART_EPOCH'
```

inside the qualified MACE training-loop patch, followed by:

```text
TargetSizeRuntimeError: Candidate TRAIN2 rung failed for
n=2048 seed=1 boundary=3: exit status 1
```

The provided run establishes the important ordering:

1. boundary 1 runs normally and publishes durable epoch-0 MACE checkpoints;
2. boundary 1 commits successfully;
3. boundary 3 resolves a continuation workspace and MACE loads the predecessor checkpoint from `from_boundary_1/...epoch-0.pt`;
4. the qualified restart loop is entered;
5. restart verification attempts to read `MDSTATS_MACE_RESTART_EPOCH` and fails because the target-size launcher never supplied it.

This is therefore a launcher-to-wrapper continuation-contract defect. It is not evidence of corrupt checkpoint bytes, failed boundary authentication, an invalid P3 continuation workspace, MACE/PyTorch warning behavior, or a changed scientific trajectory.

### 1.2 Product / computational invariants

The repair must preserve all of the following:

1. A surviving target-size candidate continues from the exact authenticated predecessor boundary rather than restarting training from scratch.
2. No optimizer epoch/update is replayed or skipped across a fidelity boundary.
3. The predecessor checkpoint selected by MACE must be independently checked against the epoch identity expected by mdstats before resumed training advances.
4. The target-size execution owner continues to express `start_epoch` as the **completed-epoch boundary** supplied by authenticated P3 resume state.
5. TRAIN2 remains the authority for the relation between completed epochs, optimizer updates, runtime companion state, and the raw MACE checkpoint epoch.
6. The qualified `mdstats-mace-train` wrapper remains the real production entry point and retains its fail-closed MACE 0.3.16 restart correction.
7. Fresh first-boundary execution has no restart authority and must not inherit stale restart-epoch state from the parent shell or an injected launcher environment.
8. Configured target-size fidelity boundaries, halving/ranking behavior, candidate membership, seeds, optimizer policy, learning-rate trajectory, checkpoint authentication, EVAL2, and selection semantics remain unchanged.

### 1.3 Non-goals

Do not use this repair to:

- suppress or alter the reported TorchScript deprecation/UserWarning groups;
- change MACE or PyTorch versions;
- redesign TRAIN2 persistence or P3 continuation workspaces;
- alter target-size fidelity epochs, selection/ranking, or statistical policy;
- change EMA/LIVE evaluation policy;
- weaken checkpoint, companion, or restart validation;
- introduce a second checkpoint-selection authority;
- add a user-facing restart-epoch configuration option;
- scan checkpoint filenames in the target-size launcher to rediscover an epoch already supplied by authenticated resume state;
- run long production/GPU qualification as a substitute for regression and integration testing.

## 2. Confirmed root cause

### 2.1 Production launcher violates the qualified-wrapper restart contract

The owning launch path is:

```text
execute_current_select_target_size(...)
  -> _execute_candidate_cell(...)
  -> resolve_target_size_candidate_for_resume(...)
  -> TargetSizeRungRequest(start_epoch=...)
  -> MaceTargetSizeBoundaryTrainer.__call__(...)
  -> mdstats-mace-train --restart_latest
```

In `mdstats/training_data/campaign_target_size_runtime.py`, `MaceTargetSizeBoundaryTrainer.__call__()` constructs the subprocess environment, exports the TRAIN2 runtime plan and `PYTHONHASHSEED`, and appends `--restart_latest` whenever `request.start_epoch > 0`.

It does **not** export `MDSTATS_MACE_RESTART_EPOCH`.

The omission exists on both the current fix branch and `main`; it is not caused by the prepared-common atomic-reference repair itself.

### 2.2 The qualified MACE restart patch intentionally requires the missing value

`mdstats/training_data/critical_precision_cli.py::_install_mace_restart_epoch_patch()` detects `--restart_latest` and rewrites the pinned MACE 0.3.16 training loop so that it:

```text
1. captures the raw checkpoint epoch MACE loaded as checkpoint_start_epoch;
2. reads MDSTATS_MACE_RESTART_EPOCH;
3. rejects a mismatch between the loaded checkpoint epoch and the expected one;
4. starts resumed training at checkpoint_start_epoch + 1.
```

The direct environment lookup is deliberately fail-closed. Removing it, replacing it with a permissive default, or catching the `KeyError` would defeat the restart-integrity guard and is not an acceptable repair.

### 2.3 Completed-epoch and raw-checkpoint epochs differ by one

The target-size resume owner returns:

```text
start_epoch = previous_boundary
```

where `previous_boundary` is the number of **completed training epochs** represented by the authenticated predecessor boundary.

TRAIN2 uses zero-based raw MACE checkpoint epochs. Its continuation restore logic explicitly derives:

```text
raw_checkpoint_epoch = current_epoch - 1
```

and requires the runtime summary to report:

```text
summary.completed_epochs == current_epoch
summary.raw_checkpoint_epoch == current_epoch - 1
```

Therefore the authoritative handoff mapping is:

```text
request.start_epoch == completed predecessor epochs
expected raw MACE restart epoch == request.start_epoch - 1
```

For the reported boundary-1 -> boundary-3 transition:

```text
request.start_epoch = 1
loaded raw checkpoint = epoch 0
MDSTATS_MACE_RESTART_EPOCH must be "0"
resumed first training epoch = 1
boundary-3 final raw checkpoint = epoch 2
completed_epochs = 3
```

Setting the environment value to `request.start_epoch` would be an off-by-one bug and must be rejected by acceptance.

### 2.4 Why existing tests missed the defect

The existing real-MACE owner-boundary test in `tests/test_mlff_target_size_p3_realized_mace_architecture.py` drives the production `MaceTargetSizeBoundaryTrainer` and qualified wrapper, but its helper always supplies:

```text
start_epoch=0
```

It therefore proves fresh first-rung model construction and checkpoint production but never enters `--restart_latest` and never exercises the launcher-to-wrapper restart-epoch handoff.

Other P3/P4 continuation tests use bounded TRAIN2 fixtures or substitute the expensive trainer seam, so they establish restart lineage and continuation semantics without proving this specific real subprocess environment contract. The missing test is thus a real-owner continuation integration gap, not merely a missing unit assertion.

## 3. Frozen high-level architecture and engineering envelope

The following high-level decisions are Frozen for this repair:

1. **P3 resume ownership remains unchanged.** `resolve_target_size_candidate_for_resume()` authenticates the durable predecessor lineage and produces the continuation workspace plus completed-epoch start boundary.
2. **One production trainer remains.** `MaceTargetSizeBoundaryTrainer` launches the qualified `mdstats-mace-train` wrapper; do not create a parallel target-size-specific MACE restart wrapper.
3. **The qualified wrapper remains the MACE 0.3.16 restart verifier/corrector.** It must continue checking the actual checkpoint epoch loaded by MACE and advancing to the following epoch.
4. **TRAIN2 remains the exact-continuation authority.** Its completed-epoch/update geometry, raw checkpoint identity, runtime companion, optimizer/live/EMA/RNG state, and restoration checks remain unchanged.
5. **Checkpoint selection is not re-derived in the launcher.** The launcher receives an already authenticated continuation workspace and expected completed boundary; it only translates that owner state into the wrapper's execution contract.
6. **Scientific target-size behavior is unchanged.** The repair is execution plumbing required to realize the already accepted trajectory.

The implementation must remain Python-native and local. A one-line environment contract plus focused validation/testing is preferable to a new state object, registry, adapter hierarchy, compatibility layer, or checkpoint scanner.

## 4. Implementation obligations and delegated solution space

### 4.1 Repair the production launcher handoff

**Owner:**

```text
mdstats/training_data/campaign_target_size_runtime.py
MaceTargetSizeBoundaryTrainer.__call__()
```

For every invocation, construct restart environment state *after* parent/injected environments have been merged so that caller-owned authenticated state cannot be overridden by stale ambient state.

Required behavior:

#### Fresh rung: `request.start_epoch == 0`

- do not append `--restart_latest`;
- remove `MDSTATS_MACE_RESTART_EPOCH` from the child environment if it was inherited from `os.environ` or `self.environment`;
- preserve the existing first-boundary rule that there is no predecessor continuation authority.

#### Continuation rung: `request.start_epoch > 0`

- append `--restart_latest` as today;
- set:

```text
MDSTATS_MACE_RESTART_EPOCH = str(request.start_epoch - 1)
```

before launching the qualified wrapper;
- the value must come from the authenticated completed-epoch start boundary already carried by `TargetSizeRungRequest`, not from a filename scan, directory maximum, log parsing, or a second persisted field.

A local literal for the established environment key is acceptable if there is no existing canonical constant. Do not add a new configuration layer merely to avoid a literal. If an existing single canonical constant is already present and appropriate, reuse it.

### 4.2 Preserve fail-closed wrapper validation

Do not modify `critical_precision_cli._install_mace_restart_epoch_patch()` merely to make this failure disappear.

Specifically forbidden:

- `os.environ.get(..., default)` for a restarting run;
- defaulting to MACE's loaded epoch;
- catching/ignoring missing restart-epoch state;
- deleting the expected-vs-loaded epoch comparison;
- changing the wrapper to infer the expectation from whichever checkpoint MACE happened to load.

The launcher supplies intent; the wrapper checks actual execution against that intent. Those are distinct responsibilities and both are required.

### 4.3 Preserve exact epoch semantics

Do not rename or reinterpret `TargetSizeRungRequest.start_epoch` as a raw MACE epoch. It is already used as the completed-epoch continuation boundary by P3 and TRAIN2.

Do not change TRAIN2's canonical relation:

```text
completed_epochs = raw_checkpoint_epoch + 1
```

The launcher adapter is the correct place to translate from completed boundary to raw MACE restart epoch.

### 4.4 Bounded sibling audit

Perform a bounded structural search of active production source for qualified MACE training launches that enable `--restart_latest`.

For each real production caller, determine whether it already pairs restart mode with an expected restart epoch and whether fresh mode clears stale state where the child environment can inherit it.

Current diagnosis finds the target-size trainer as the live unpaired source site. Historical release patch text is not active runtime source and is not itself a repair target.

If no sibling source defect exists, stop. Do not broaden this into a restart architecture refactor or permanent scanning framework.

## 5. Task-specific acceptance and regression

### 5.1 Focused launcher contract tests

Add focused tests for the child process contract of `MaceTargetSizeBoundaryTrainer`.

At minimum prove:

1. fresh `start_epoch=0` launches without `--restart_latest` and without `MDSTATS_MACE_RESTART_EPOCH`, even when a stale value exists in the inherited/injected environment;
2. continuation `start_epoch=1` launches with `--restart_latest` and exports `MDSTATS_MACE_RESTART_EPOCH="0"`;
3. a later continuation boundary, e.g. `start_epoch=3`, exports `"2"`;
4. authenticated launcher state overrides an ambient/injected conflicting value rather than passing that conflict to MACE.

A subprocess spy/fake below `MaceTargetSizeBoundaryTrainer` is acceptable for these *launcher-shape* assertions, but it cannot by itself close the real restart integration claim below.

### 5.2 Mandatory real-owner continuation integration regression

Extend or add bounded real-MACE coverage that crosses the same production boundary as the failure.

Required semantic path:

```text
real canonical P3 candidate materialization
  -> production MaceTargetSizeBoundaryTrainer
  -> qualified mdstats-mace-train
  -> first durable TRAIN2 boundary
  -> authenticated predecessor/snapshot-resume preparation
  -> production continuation request with start_epoch > 0
  -> production MaceTargetSizeBoundaryTrainer
  -> qualified mdstats-mace-train --restart_latest
  -> actual MACE checkpoint load
  -> restart-epoch verification
  -> continued optimizer execution
  -> next durable TRAIN2 boundary summary
```

Use the smallest deterministic candidate/data/model fixture that already satisfies the real MACE/P3 contracts. CPU execution is acceptable because this bug is launcher/restart semantics, not accelerator behavior. Existing slow real-MACE infrastructure in `test_mlff_target_size_p3_realized_mace_architecture.py` should be reused where practical rather than creating a second harness.

For an `n1=1`, next-boundary `=3` fixture, require all of the following observable outcomes:

- the first rung ends with `completed_epochs == 1` and raw checkpoint epoch `0`;
- the continuation launcher receives `start_epoch == 1`;
- the qualified child receives expected raw restart epoch `0`;
- MACE loads the epoch-0 predecessor checkpoint without a missing-env failure;
- the wrapper resumes at epoch 1 rather than replaying epoch 0;
- the next rung ends with `completed_epochs == 3`, `raw_checkpoint_epoch == 2`, and the expected completed update count;
- TRAIN2 continuation companion authentication succeeds;
- no fresh-start reinitialization substitutes for continuation.

The real integration test must execute both the production trainer and qualified wrapper. A test that directly invokes TRAIN2 restore helpers, directly patches the MACE training loop, or substitutes the entire `MaceTargetSizeBoundaryTrainer` cannot close this claim.

### 5.3 Restart-guard liveness / wrong-value evidence

Preserve or add a bounded check proving the restart guard remains live: when the expected raw restart epoch intentionally disagrees with the checkpoint epoch MACE loads, the qualified wrapper must fail with the established mismatch error rather than silently continuing.

This may reuse an existing qualified-wrapper restart test if it genuinely executes that comparison on the current candidate. Do not duplicate expensive integration solely for wording.

The purpose is to prevent a superficially green repair that merely removes or bypasses the verifier.

### 5.4 Affected-surface regression

After the implementation, rerun the complete affected surface, including at minimum the relevant tests from:

- `tests/test_mlff_target_size_p3_realized_mace_architecture.py`;
- target-size P3-C exact continuation / boundary ancestry coverage;
- P3-E/P3-F candidate resume/replay coverage affected by continuation semantics;
- `tests/test_mlff_target_size_p4d_runtime_cutover.py`;
- current-branch partial-boundary resume regressions;
- `tests/test_mlff_train2b_runtime.py`;
- critical-precision / qualified MACE restart-loop tests;
- any focused launcher tests added by this repair.

If source inspection shows the change can affect additional target-size callers or restart consumers, add them to the final affected-surface regression rather than treating this initial list as a ceiling.

A required test that does not execute is not a pass. Newly introduced failures on this surface block closure.

### 5.5 Production qualification boundary

**Full production/GPU qualification is deferred and not required for this bug-fix closure.**

This repair requires bounded real MACE continuation because the defect exists at that real execution boundary. It does not require a long multi-candidate GPU target-size campaign, production-scale timing, VRAM qualification, or resource characterization. Those remain part of the project's final release qualification policy.

## 6. Implementation authority

### 6.1 Frozen

- exact continuation from the authenticated predecessor boundary;
- no replay or skip of optimizer epochs/updates;
- P3 ownership of authenticated resume state and completed-epoch `start_epoch`;
- TRAIN2 ownership of completed-epoch/raw-checkpoint/update state;
- qualified `mdstats-mace-train` as the production MACE launch path;
- fail-closed verification of the actual checkpoint epoch MACE loads;
- existing target-size scientific/fidelity/ranking semantics.

### 6.2 Delegated

- exact local code arrangement used to set/clear the environment value;
- whether a pre-existing appropriate constant is reused or the established literal remains local;
- exact test helper structure and fixture factoring;
- whether focused launcher assertions spy on `subprocess.run` or use a tiny executable probe;
- small test-only refactors needed to let the existing real-MACE fixture execute a second rung.

Equivalent simpler realizations are valid if they preserve the Frozen authority and real-owner acceptance boundary.

### 6.3 Reopen only on evidence

Reopen Software Design only if implementation/testing demonstrates one of these assumptions is false:

1. `TargetSizeRungRequest.start_epoch` is not reliably the authenticated completed-epoch predecessor boundary;
2. pinned MACE 0.3.16 does not expose the loaded raw checkpoint epoch through the `start_epoch` value the qualified patch currently verifies;
3. TRAIN2's accepted mapping `raw_checkpoint_epoch = completed_epochs - 1` is not the actual production contract;
4. a materially different Frozen owner must select or authenticate the restart checkpoint.

Current source and run evidence support all four assumptions, so no redesign is presently justified.

## 7. Implementation sequence

### Stage A — launcher contract repair

Implement the smallest owning-layer set/clear behavior in `MaceTargetSizeBoundaryTrainer.__call__()` and add focused launcher-shape tests.

Stage closure requires focused tests plus the relevant low-cost affected regression. Do not proceed by weakening the wrapper guard if tests expose a mistake.

### Stage B — real continuation acceptance

Extend the bounded real-MACE owner-boundary regression to cross first-boundary -> next-boundary continuation through the production trainer and qualified wrapper.

If this exposes a different genuine continuation defect, diagnose it at its owning layer. Do not pile compatibility state onto the environment handoff merely to make the test pass.

### Stage C — affected-surface closure

Re-derive the final affected surface, run the required target-size/TRAIN2/restart regressions and integration tests, perform the bounded sibling audit, and inspect the final diff for duplicate restart authority or weakened validation.

## 8. Simplicity and redesign triggers

This is the first clean local defect in this launcher contract. A direct owning-layer repair is appropriate.

Before adding any new durable restart abstraction, stop and simplify if implementation starts to introduce:

- a second restart-epoch state object in addition to existing P3/TRAIN2 state;
- checkpoint filename scanning in the launcher;
- duplicate expected-epoch validation outside the qualified wrapper;
- a compatibility fallback that guesses when the environment is missing;
- separate fresh/resume wrapper entry points solely for this defect;
- additional persisted restart metadata that can disagree with TRAIN2.

Such additions solve a Tier-2 problem created by the launcher while increasing state/authority count and are not justified by the current evidence.

## 9. Acceptance criteria

Implementation may close only when all of the following are true:

- [ ] A fresh target-size rung launches without `--restart_latest` and with no inherited `MDSTATS_MACE_RESTART_EPOCH`.
- [ ] A continuation rung launches with `--restart_latest` and an authoritative expected raw restart epoch.
- [ ] The mapping is exactly `MDSTATS_MACE_RESTART_EPOCH = start_epoch - 1`.
- [ ] Boundary 1 -> boundary 3 therefore exports `0`, loads the raw epoch-0 checkpoint, resumes at epoch 1, and reaches completed epoch 3 without replay/skip.
- [ ] Ambient or injected stale restart-epoch values cannot override authenticated request state.
- [ ] The qualified MACE restart mismatch guard remains fail-closed and demonstrably live.
- [ ] No checkpoint filename/log scan or second restart authority is introduced.
- [ ] No scientific target-size, fidelity, optimizer, ranking, EVAL2, or precision policy changes are introduced.
- [ ] A bounded real-MACE continuation test crosses the production `MaceTargetSizeBoundaryTrainer -> mdstats-mace-train -> MACE restart` boundary and passes.
- [ ] Existing exact-continuation companion/checkpoint authentication remains intact.
- [ ] The bounded sibling audit finds no uncorrected active production `--restart_latest` invocation with the same missing handoff.
- [ ] Final affected-surface regression and integration tests pass on the assembled candidate.
- [ ] No full production/GPU qualification is required for this local functional closure.

## 10. Closure rule

**PASS** only if the reported failure is removed by restoring the missing launcher-to-wrapper restart contract while preserving exact predecessor authentication, zero replay/skip continuation, and the existing fail-closed MACE restart verifier.

**NO-PASS / reopen** if the implementation instead weakens the wrapper guard, guesses restart state, changes `start_epoch` semantics, introduces a parallel checkpoint authority, alters target-size scientific policy, or lacks real production continuation evidence.