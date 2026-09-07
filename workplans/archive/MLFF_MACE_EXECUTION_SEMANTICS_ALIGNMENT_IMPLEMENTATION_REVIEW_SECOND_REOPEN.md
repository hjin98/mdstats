---
kind: implementation-workplan-review-reopen
workplan_id: MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT-IMPLEMENTATION-REVIEW-SECOND-REOPEN
parent_workplan_path: workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_IMPLEMENTATION_REVIEW_FINAL_DESIGN_CLOSURE.md
governing_workplan_path: workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_REOPEN_WORKPLAN.md
protocol_version: 5.15.0
status: implementation-repair-required
created_date: 2026-09-06
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_implementation_commit: dba91048e4358af4df3566c5f70b482c49567c08
reviewed_parent_commit: 1ddf592cd4d86a902a5f154b939772c00755c199
design_verdict: pass-frozen-design-unchanged
implementation_review_verdict: no-pass
precedence: This review reopens implementation only. The governing repair workplan, first implementation-review reopen, and final design closure remain authoritative except where this file supplies the concrete additional repair obligations surfaced by the second independent implementation review. No scientific formula, P3/P4/P5 ownership decision, replay method, or final-production architecture is changed.
---

# MLFF MACE execution-semantics alignment — second independent implementation review reopen

## 0. Verdict

**NO-PASS / bounded implementation repair required.**  
**Frozen scientific method and high-level architecture: PASS / unchanged.**

The reviewed implementation commit `dba91048e4358af4df3566c5f70b482c49567c08`
substantially closes the three blocker families from the previous review:

- P5 current method resolution now cuts over globally to the corrected recipe generation;
- historical v1 MACE compatibility/source-probe records have an explicit readable-history representation and cannot satisfy the current source/dry-run execution compatibility path;
- target-size acceptance now includes a real non-divisible TRAIN2 run, and replay-enabled P5 acceptance now executes production materialization, the qualified wrapper, pinned MACE training, native loss, and durable TRAIN2 evidence.

Those are real improvements and must be preserved. They do **not**, however, close the workplan. Two implementation blockers were introduced/left exposed in the expanded checkpoint-evaluation surface, and final acceptance remains incomplete.

The repair should be a **reduction/alteration pass**. Do not add another model builder, checkpoint store, compatibility registry, execution wrapper, or scientific identity.

---

## 1. Global invariant analysis

### 1.1 Core problem of concern

The governing problem remains:

> the method mdstats authenticates must be the method pinned MACE 0.3.16 actually executes, and downstream checkpoint evaluation/currentness must consume the exact resulting model state without silently changing scientific identity.

This includes not only loss/LR/replay/batch realization at training launch, but the later P5 representative-selection path that reconstructs a model shell and loads a TRAIN2 checkpoint for EVAL2.

### 1.2 Frozen architecture remains valid

Keep the accepted authority graph unchanged:

```text
canonical frame/source authority
  -> neutral statistical substrate
  -> P_train / M3 + canonical order
  -> common preparation
  -> P3 target-size screen / TRAIN2 / EVAL2
  -> P4 selected N / T_selected
  -> P5 selected-only CV
  -> fresh final production
```

Keep:

- one qualified MACE wrapper in `critical_precision_cli.py`;
- native MACE loss/trainer ownership;
- one shared TRAIN2 runtime/currentness lineage;
- P3 canonical `target_head` architecture;
- P5 replay `target_head`/`pt_head` execution;
- ordinary P5 single-head MACE `Default` execution when replay is disabled;
- exact checkpoint bytes as the state authority for evaluated checkpoints;
- only one current continuation companion for restart/exact continuation;
- selected-only CV and fresh final production;
- deferred production-scale/GPU qualification.

No current finding requires changing target-size normalization, objective weighting, replay policy, CV selection, or final-production semantics.

---

## 2. Blocker S1 — ordinary P5 checkpoint reconstruction uses the P3 `target_head` namespace instead of MACE `Default`

### 2.1 Diagnosis

The corrected P5 executable projection now intentionally emits
`multiheads_finetuning=False` for scratch and naive-fine-tuning jobs. The
post-selection execution owner also records the pinned ordinary single-head
namespace as `Default` in its launch authority.

Pinned MACE 0.3.16 confirms the behavior: when no explicit `heads` map is supplied,
`run_train` calls `prepare_default_head(args)`, then executes that ordinary head as
`Default`.

The new shared reconstruction logic in
`build_mace_model_from_configuration()` does not reproduce that rule. Its current
head selection is effectively:

```text
explicit heads mapping -> use mapped heads
else if multiheads_finetuning is true -> Default
else -> architecture["heads"]
```

But the canonical architecture object is deliberately P3-specific and validates
`architecture["heads"] == ["target_head"]`.

Therefore a corrected scratch/naive P5 materialization has:

```text
post-selection schema
multiheads_finetuning = false
no explicit heads map
```

and the reconstruction falls through to `target_head`, while the real TRAIN2
model was built with `Default`. `authenticate_train2_checkpoint_provider()` then
compares the reconstructed architecture digest with the real TRAIN2 architecture
digest before state can be accepted. This makes ordinary P5 scratch/naive
checkpoint evaluation structurally inconsistent with the model that was actually
trained.

There is a second semantic detail in the same owner: for ordinary naive
fine-tuning, the current reconstruction helper falls back to foundation atomic
energies whenever a foundation model exists. Pinned MACE's ordinary default head,
however, consumes the explicit global `E0s` supplied by the P5 configuration; the
foundation E0 path is the replay `pt_head` case. Raw checkpoint state may later
overwrite calibration buffers, but reconstruction must still model the real
construction path rather than rely on checkpoint overwrite to hide a wrong shell.

### 2.2 Required repair — alter the shared reconstruction owner, do not add another builder

Repair `build_mace_model_from_configuration()` in place.

Required head resolution:

1. when the config contains the explicit replay `heads` mapping, preserve the
   exact MACE ordering rule (`pt_head` first) and reconstruct those mapped heads;
2. when the config is a **post-selection** config with
   `multiheads_finetuning=False` and no explicit heads mapping, reconstruct the
   pinned ordinary MACE single head `Default`;
3. when the config is a **target-size P3** config, preserve the existing canonical
   `target_head` reconstruction;
4. do not globally rename P3 to `Default` and do not change the P3 canonical
   architecture schema merely to accommodate P5.

Use the existing config schema/role information to distinguish P3 from P5. If a
shared constant is useful, place the source-owned MACE `Default` name in an
existing MACE/post-selection compatibility owner rather than introducing a new
head registry or a second architecture object.

Required E0 resolution:

- explicit per-head E0s remain authoritative when supplied;
- the replay `pt_head` may use the authenticated foundation E0s as pinned MACE
  does;
- ordinary single-head P5 uses the configuration's explicit fitted `E0s`, even
  when a foundation model is present;
- P3 without a foundation continues to use its explicit fitted E0s.

### 2.3 Acceptance

Add bounded real-MACE integration for **both** non-replay P5 modes:

- one scratch P5 run;
- one naive-fine-tuning P5 run with a tiny foundation model.

For each, execute the real `MacePostSelectionTrainer`/qualified wrapper far enough
to produce a real TRAIN2 checkpoint and then execute the real checkpoint-provider
/EVAL2 authentication path. Prove:

- the real TRAIN2 model reports the expected `Default` head;
- `build_mace_model_from_configuration()` reconstructs the same head namespace;
- reconstructed and TRAIN2 architecture digests match;
- the raw checkpoint state loads and authenticates;
- bounded EVAL2 inference succeeds;
- P3 `target_head` real TRAIN2/EVAL2 tests remain unchanged and green;
- multihead replay `target_head`/`pt_head` reconstruction remains green.

A parser-only `Default` assertion is a useful focused check but is not sufficient
for this blocker because the defect is downstream reconstruction/authentication.

---

## 3. Blocker S2 — per-epoch full TRAIN2 companions duplicate large durable state unnecessarily

### 3.1 Diagnosis

To evaluate earlier P5 checkpoints, the implementation added per-epoch files:

```text
train2_runtime_epoch-{epoch}.json
train2_runtime_epoch-{epoch}.pt
```

Every epoch already has the raw MACE checkpoint because P5 uses
`save_all_checkpoints=True`. The new `.pt` companion additionally serializes the
full live parameter list, optimizer state, EMA state, RNG state, architecture
identity, and runtime-plan lineage for every epoch, while the existing
`train2_runtime.pt` continues to hold the latest exact-continuation state.

This is not a small evidence record. With EMA enabled, each per-epoch companion
can contain additional full-model live and EMA parameter copies on top of the raw
checkpoint. Across all saved epochs, CV folds, seeds, and final runs this creates
O(number-of-checkpoints) extra full-model storage and write I/O.

The new earlier-checkpoint evaluation code demonstrates that this duplication is
not required for the scientific claim: after loading an earlier raw checkpoint,
it intentionally **does not** overwrite that model from the companion's live
parameters; for an earlier EMA checkpoint it returns using the raw checkpoint
model state before consuming companion EMA shadow state. The full historical
continuation state therefore exists mainly to satisfy the new helper shape, not a
Tier-1 restart or evaluation invariant.

This directly hits the final design closure's active-simplicity guard against
`duplicate runtime-evidence stores` and is especially harmful because the raw
checkpoint family is already intentionally complete.

### 3.2 Required repair — keep small immutable boundary metadata, remove historical full companions

Reduce the realization:

1. retain the existing single latest `train2_runtime.pt` companion as the exact
   continuation/restart authority;
2. retain a small immutable per-epoch JSON boundary summary **only if** it is
   needed to bind `(run authority, epoch, raw checkpoint SHA, execution evidence,
   architecture identity)` for checkpoint evaluation;
3. stop writing `train2_runtime_epoch-{epoch}.pt` full companions;
4. remove the historical-companion path/template/export helpers and the checkpoint
   inventory exclusions that exist only because those `.pt` files collide with
   checkpoint discovery;
5. for an earlier checkpoint, authenticate:
   - the per-epoch boundary summary against the current run authority;
   - the raw checkpoint bytes against the boundary summary's SHA;
   - the model shell against the corrected configuration/architecture;
   - the raw checkpoint state as the actual historical evaluation state;
6. keep the current rule that an earlier EMA-enabled MACE checkpoint is evaluated
   as MACE's checkpoint representation, while an unsupported request for an
   unavailable historical live state fails closed;
7. latest-checkpoint evaluation/restart may continue to use the one current
   continuation companion where live/EMA/RNG/optimizer state is genuinely needed.

Do not replace the per-epoch companions with another checkpoint database or a
second state archive. The raw MACE checkpoint plus one small authenticated
boundary record is the minimum complete historical evaluation authority.

If the per-epoch boundary JSON is retained, publish/create-or-verify it as an
immutable epoch record rather than treating it like the mutable latest summary.

### 3.3 Acceptance

Prove on a bounded multi-epoch run:

- multiple raw MACE checkpoints exist;
- exactly one latest continuation companion exists;
- no per-epoch full TRAIN2 `.pt` companion family exists;
- an earlier checkpoint is discovered without special-case runtime-file filtering;
- its boundary summary binds the correct raw SHA and run/method/runtime evidence;
- earlier checkpoint provider authentication and evaluation succeed;
- tampered earlier checkpoint bytes or boundary metadata fail closed;
- latest exact continuation/restart remains byte/state exact;
- target-size restart/continuation regression remains green.

This repair must **reduce**, not increase, durable checkpoint-state machinery.

---

## 4. Blocker S3 — acceptance requirements remain incomplete on the reviewed candidate

This blocker is evidence/acceptance nonconformance, not a request for more product
machinery.

### 4.1 Stored historical P5 authorization is still tested only synthetically

Final clarification C1 explicitly required that a synthetic digest fixture not be
the only evidence that stored pre-repair P5 authorization is rejected.

The current R6-D test creates the historical method, CV plan, and acceptance with
`dataclasses.replace(...)` from current objects. The branch's static fixture
directory contains only `mace_compatibility_v1.json`; there is no serialized
pre-repair P5 method/CV/acceptance fixture.

Required repair:

- add one small static fixture mechanically captured/derived from the exact
  pre-repair serializer for `PostSelectionMethodIdentity` plus the minimum CV
  plan/acceptance chain needed for authorization;
- deserialize it through the current readers;
- prove the real final-production authorization owner rejects it against the
  current v3 method before trainer launch;
- keep the current synthetic test as an inexpensive companion if useful.

No production migration layer is required.

### 4.2 The assembled replay test does not prove its discriminating LR/EMA and ratio conditions are live

The assembled P5 test deliberately writes:

```text
learning_rate = 0.0123
ema = true
ema_decay = 0.87
60 replay configurations
```

but its assertions do not verify that the materialized/executable config and
resolved runtime evidence actually contain `0.0123`, `True`, and `0.87`, nor does
it assert that the realized target/replay ratio is below MACE's native `0.1`
threshold.

That leaves an acceptance-liveness gap: the test can exercise real MACE while
failing to prove that the non-default override and hidden-duplication branches
were genuinely discriminating on that assembled path.

Tighten the existing test only:

- assert the production materialization/executable config carries
  `lr=0.0123`, `ema=True`, `ema_decay=0.87`;
- assert TRAIN2 `mace_execution_evidence` records the same resolved LR/EMA values;
- assert `target_train_count / replay_train_count < 0.1` for that exact run;
- retain the existing threshold-zero and duplication-factor-one assertions;
- retain the same production-exported weighted batch/native-loss oracle.

Do not add a new acceptance framework.

### 4.3 Final executable evidence is unavailable for `dba91048...`

For the exact reviewed implementation SHA, the repository exposes no GitHub
Actions run and no commit-status checks. The implementation commit also does not
contain the R8-D evidence metadata required by the final design closure, and no
local test output was supplied to this review.

Therefore the required stage-local/final affected regression and real-MACE
integration cannot be credited as executed acceptance evidence.

After S1/S2/S3 edits, prior evidence would be stale for the affected surfaces
anyway. On the final executable candidate, run and record:

- S1 focused + P5 scratch/naive stage-local affected regression;
- S2 focused + TRAIN2/checkpoint/restart stage-local affected regression;
- historical DATA8/P5 currentness regression;
- real non-divisible P3 integration;
- real replay-enabled P5 integration with the liveness assertions above;
- complete affected-surface regression for MACE compatibility/wrapper,
  target-size TRAIN2/EVAL2/restart, P5 CV/checkpoint selection/final
  authorization, DATA8 compatibility, and objective/export weighting;
- the broader MLFF suite if the final affected surface cannot be bounded;
- repository/project-required checks.

Required real-MACE tests must execute with `mace-torch==0.3.16`; a skip is not a
pass. Record exact candidate SHA, commands, pass/fail/skip counts, and dependency
identity in the existing evidence convention.

---

## 5. Accepted implementation state to preserve

Do not undo the already-correct parts merely to repair the blockers above:

- current P5 method recipe cutover to the corrected generation;
- explicit non-replay `multiheads_finetuning=False`;
- replay `force_mh_ft_lr=True` and `real_pt_data_ratio_threshold=0.0`;
- source-qualified prevention of the forced `UniversalLoss` transition;
- native MACE `WeightedEnergyForcesStressLoss`;
- P3 complete-batch target-size realization and non-divisible real integration;
- historical/current MACE compatibility/source-probe schema separation;
- current source probe fail-closed behavior;
- production-exported P5 weighting/native-loss oracle;
- one qualified wrapper and one TRAIN2 runtime authority;
- exact latest continuation/restart state;
- P3/P4/P5 scientific ownership and fresh final production.

The repair should remove more state/code than it adds. In particular, S2 should
net-delete the per-epoch `.pt` companion machinery.

---

## 6. Repair sequence and closure

### A — repair P5 reconstruction first

Implement S1 in the existing shared reconstruction owner. Run focused and
stage-local affected regression for P3 reconstruction plus P5 scratch, naive, and
replay modes before proceeding.

### B — reduce historical TRAIN2 persistence

Implement S2 by deleting per-epoch full companions and adapting earlier-checkpoint
authentication to raw checkpoint + immutable boundary summary. Run focused and
stage-local checkpoint/restart/EVAL2 regression.

### C — close acceptance liveness/history evidence

Implement only the test/evidence corrections in S3. Do not add production
machinery to make tests easier.

### D — final assembled acceptance and independent review

On one final executable SHA:

1. reconcile against the governing workplan, first reopen, final design closure,
   and this second reopen;
2. re-derive the final affected surface;
3. execute complete affected regression and the required real-MACE integrations;
4. verify no required test skipped;
5. perform an active-simplicity review of MACE reconstruction, TRAIN2 persistence,
   wrapper/source qualification, and compatibility serialization;
6. perform a fresh independent Software Design closure review.

**PASS only when no genuine scientific, architectural, runtime, currentness,
compatibility, persistence/resource, or acceptance blocker remains.**

If another issue is found, update this same implementation lineage. Do not create
a new scientific workplan or another wrapper/checkpoint system to patch around it.

---

## 7. Final review disposition

**Software Design:** PASS — the frozen scientific method and high-level architecture remain valid.  
**Implementation:** **NO-PASS** — S1, S2, and S3 must close before archival.
