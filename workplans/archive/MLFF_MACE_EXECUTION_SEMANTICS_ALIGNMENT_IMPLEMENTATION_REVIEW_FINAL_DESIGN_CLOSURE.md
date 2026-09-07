---
kind: implementation-workplan-final-design-closure
workplan_id: MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT-IMPLEMENTATION-REVIEW-FINAL-DESIGN-CLOSURE
parent_workplan_id: MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT-IMPLEMENTATION-REVIEW-REOPEN
parent_workplan_path: workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_IMPLEMENTATION_REVIEW_REOPEN.md
governing_workplan_path: workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_REOPEN_WORKPLAN.md
protocol_version: 5.15.0
status: implementation-ready
created_date: 2026-09-06
final_review_base: ca68f62adae30842b2ff87105b1fc4e7de977315
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
design_verdict: pass-frozen-design-unchanged
final_plan_review_verdict: pass-implementation-ready
implementation_verdict: no-pass-until-r1-r3-and-final-acceptance-close
precedence: This file is the final Software Design reconciliation of the implementation-review reopen. It does not create a new scientific method or architecture. The governing parent workplan and implementation-review reopen remain binding except where this closure narrows, clarifies, or corrects their implementation/acceptance wording. The three files together are the current implementation handoff.
---

# MLFF MACE execution-semantics alignment — final design closure

## 0. Final plan verdict

**Software Design: PASS / implementation-ready.**  
**Frozen scientific method and high-level architecture: unchanged.**  
**Implementation: still NO-PASS until R1, R2, R3, stage-local regression, final affected regression, and independent closure all pass on one final executable candidate.**

A final Software Design challenge of
`MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_IMPLEMENTATION_REVIEW_REOPEN.md`
found no remaining deficiency in the scientific target or Frozen architecture.
The repair remains correctly bounded to the existing MACE compatibility,
projection, qualified-wrapper, TRAIN2/currentness, and versioned serialization
owners.

The review did find four plan-level ambiguities that are now closed here:

1. the historical DATA8 obligation must be bounded to the **already-declared supported compatibility surface**, not generalized into indefinite legacy support;
2. historical nested MACE compatibility/probe records must remain readable **without being up-converted into current semantics**, and current execution must have an explicit admission distinction between readable-history and current-executable evidence;
3. proxy-proof acceptance must execute every real semantic owner, but it need not be forced into one monolithic test function when a smaller set of tests proves the assembled chain more directly;
4. each executable repair stage requires **stage-local affected regression**, not focused tests alone.

No additional wrapper, trainer, compatibility hierarchy, method registry, loss
engine, or scientific identity is justified.

---

## 1. Authority classes remain unchanged

### 1.1 Tier-1 product/scientific invariants

The implementation must still realize, not merely request:

- pinned MACE 0.3.16 native `WeightedEnergyForcesStressLoss` for the accepted
  weighted energy/forces/stress objective;
- explicit global E/F/S coefficients, configuration weights, and local
  property-availability masks as separate weighting layers;
- no hidden replay target duplication;
- authenticated LR/EMA behavior after MACE's own mutation region;
- exact target-size complete-membership loader geometry matching
  `ceil(N / B)` without target padding/duplication;
- exact target-size checkpoint continuation and target-only EVAL2 semantics;
- selected-only P5 CV and fresh final production;
- historical scientific evidence remaining historical rather than being
  relabeled as corrected execution.

### 1.2 Frozen high-level architecture

Keep the accepted ownership graph:

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

Keep one mdstats-qualified MACE execution seam in `critical_precision_cli.py`.
MACE remains the native loss/training owner. Existing P3/P4/P5 currentness and
publication owners remain the only scientific authorization chain.

### 1.3 Delegated solution space

Implementation may simplify, consolidate, or alter lower-level repair helpers,
source-match logic, serialization helpers, fixtures, or test decomposition when
all Tier-1/Frozen semantics and acceptance boundaries below remain intact.
Do not preserve implementation-created machinery merely because the first repair
introduced it.

---

## 2. Final clarification C1 — P5 method cutover is global, readable history stays history

R1 from the implementation-review reopen remains binding with these final
clarifications.

### Required end state

1. Use the existing `PostSelectionMethodIdentity` owner for the cutover.
2. Advance the current method recipe identity once for the corrected MACE
   execution semantics for **all three supported P5 modes**:
   `scratch`, `naive_fine_tuning`, and `multihead_replay`.
3. Current resolution must never emit the retired pre-repair recipe identity.
4. Historical `PostSelectionMethodIdentity`, CV plan/acceptance, and final-plan
   payloads remain readable under their existing schemas; readability does not
   make their method digest current.
5. Existing CV/final authorization must reject an old method digest before
   `MacePostSelectionTrainer` launch.
6. P4 selected `N`, `T_selected`, and their lineage do not change merely because
   P5 execution semantics cut over.
7. Do not create a second execution-semantics digest solely for P5 currentness.
   The method-recipe cutover plus already-required replay/runtime identities are
   sufficient for this repair.

### Acceptance

At minimum prove:

- unchanged scratch and naive configurations resolve a new current P5 method
  digest and reject pre-repair CV authorization;
- replay old evidence remains rejected;
- current corrected CV authorizes current corrected final production through
  the existing owner;
- historical method/CV records can still be deserialized as history;
- no trainer launch occurs before currentness rejection;
- P4 selection identity remains unchanged by a P5-only method-recipe cutover.

An exact serialized historical fixture is preferred for at least one
currentness-chain test. A focused synthetic digest fixture may supplement it but
must not be the only evidence that stored old authorization is rejected.

---

## 3. Final clarification C2 — historical DATA8 support is bounded and must not up-convert semantics

R2 is a real compatibility regression because the current DATA8 reader still
explicitly advertises historical outer bundle/parser schemas and the current
DATA8 specification permits historical representations through supported
compatibility readers. This closure **does not broaden that support**.

### 3.1 Compatibility scope

Support only the exact historical DATA8 outer schemas/parser versions already
accepted by the current `Data8PreparationBundle.from_dict()` contract on this
branch. Do not add older schemas, migration windows, registries, or indefinite
backward-compatibility policy as part of this repair.

If a historical schema/parser version is deliberately removed from that
existing supported set, that is a separate compatibility-policy/design decision
and is not authorized by this workplan.

### 3.2 Historical nested records

For pre-repair v1 `MaceCompatibilityPolicy` and `MaceSourceProbe` records:

- authenticate the exact historical serialized shape and its original digest;
- preserve the historical policy/probe digest relationship exactly;
- do **not** default-fill newly introduced v2 execution-semantics fields and then
  serialize the record as though it had always been v2;
- do **not** infer the new forced-loss/LR/duplication/drop-last qualification
  claims from the older probe's `fixed_file_adapter_supported=True` state;
- current constructors/builders must emit only the current corrected
  compatibility/probe representation.

A minimal schema-aware branch inside the existing compatibility/serialization
owner is acceptable. A new legacy DATA8 class hierarchy, compatibility registry,
migration database, or shadow bundle model is not.

### 3.3 Readability versus execution admission

The existing current execution boundary must distinguish:

```text
readable authenticated historical record
    !=
current corrected executable compatibility evidence
```

`fixed_file_adapter_supported=True` from a historical probe is **not** by itself
a current-execution authorization.

Before current DATA8/P3/P5 MACE launch, the existing compatibility/currentness
owner must require the current compatibility/source-probe schema or current
execution-semantics identity. A legacy nested v1 record must fail that admission
cleanly while remaining readable for history/inspection.

Do not add a second launch gate when an existing compatibility/currentness owner
can carry this distinction.

### 3.4 Digest-preservation acceptance

Use a static fixture whose bytes/fields are mechanically derived from the exact
pre-repair source/serialization contract (for example from the reviewed
pre-repair commit), rather than a hand-invented approximation. The test suite
must not require Git/network access at runtime.

Prove:

- v1 compatibility-policy original digest is preserved;
- v1 source-probe original digest is preserved;
- the v1 probe still references the original v1 policy digest;
- a pre-repair DATA8 v5 bundle with nested v1 records preserves/authenticates its
  original outer digest;
- at least one older outer DATA8 schema from the **already-declared supported
  set** remains readable;
- nested or outer tampering fails closed;
- current builders emit current records only;
- historical readable records cannot authorize a current MACE launch.

If preservation of the old outer digest would require rebuilding the old record
into a current representation and hashing that current representation, the
repair is wrong. Historical digest validation must be against the historical
serialized contract.

---

## 4. Final clarification C3 — proxy-proof acceptance is owner-complete, not test-function-complete

The parent G2/G5 requirement remains: acceptance must prove the real scientific
request reaches and survives the real MACE execution boundary. The
implementation-review reopen correctly rejected the existing split evidence
because the real-`run_train` half manually manufactured acceptance-critical
weights instead of consuming production mdstats materialization.

The final requirement is **not** that every assertion live in one test function.
It is that the acceptance evidence, considered together on one final candidate,
executes the real semantic owners and has no proxy hole.

### 4.1 Required assembled owner chain

The accepted evidence set must establish:

```text
resolved mdstats scientific policy
 -> real mdstats P3/P5 materialization/export
 -> real parser-facing configuration
 -> existing qualified mdstats MACE wrapper
 -> real pinned MACE run_train mutation/resolution region
 -> native MACE loss + real loader
 -> at least one real optimizer update / durable TRAIN2 boundary where required
 -> existing runtime/currentness consumer
```

Every arrow that constitutes the claim must use production code. Tests may be
split when doing so is simpler and higher-signal, provided the same
production-generated artifact/configuration is what reaches the real dependency
boundary and no test substitutes the semantic owner it is intended to prove.

### 4.2 Allowed bounded doubles

Allowed below/outside the owner under acceptance:

- tiny deterministic source datasets;
- tiny foundation/replay model fixtures;
- CPU execution and one/few epochs/updates;
- bounded inference/evaluation dependencies not under the specific claim;
- temporary filesystem roots and deterministic seeds.

Forbidden for the final gate:

- fake `MaceTargetSizeBoundaryTrainer` or `MacePostSelectionTrainer`;
- monkeypatching `mace.cli.run_train.run()` or `tools.train` to manufacture the
  final integration result;
- manually injecting/changing `config_weight` or local property weights after
  production mdstats export;
- directly creating a successful TRAIN2 summary/checkpoint instead of letting
  the real runtime produce it;
- parser/source-text equality as a substitute for real resolved behavior.

Low-level monkeypatched/source-probe tests remain useful focused checks; they are
not the final integration evidence.

### 4.3 Target-size acceptance

Use real `MaceTargetSizeBoundaryTrainer`/qualified-wrapper execution with an
admissible `N % B != 0` case. On the resulting real TRAIN2 evidence prove:

- exact exported target UID-set digest;
- no target duplication/padding;
- `target_drop_last=False`;
- `target_updates_per_epoch=ceil(N/B)`;
- real completed optimizer-update count matches the frozen geometry;
- resolved native weighted-stress loss evidence exists and matches the launch
  authority;
- continuation/currentness behavior remains valid.

The runtime-evidence field must be live: absence of `mace_execution_evidence`,
a stale authority digest, or an unexercised patch path is a failed acceptance,
not a pass.

### 4.4 Replay-enabled P5 acceptance

Use actual P5 materialization and real `MacePostSelectionTrainer` through the
qualified wrapper and real pinned MACE trainer. Production-exported target data
must supply the training weights/masks.

Use distinguishable values for:

- global E/F/S objective coefficients;
- at least one non-unit configuration weight;
- target/replay ratio below MACE's native `0.1` balancing threshold;
- non-default LR and EMA values.

A missing-property zero mask should be included when the production P5 fixture
naturally supports that canonical label condition; it is not a new product
requirement for this bug family.

The assembled evidence must prove:

- native `WeightedEnergyForcesStressLoss` is the resolved loss;
- configured global coefficients survive into the native loss;
- production-exported configuration/local weights remain distinct from global
  coefficients;
- `force_mh_ft_lr=True` preserves the requested LR/EMA values;
- threshold zero prevents implicit target duplication;
- runtime evidence is persisted in the real TRAIN2 summary and bound to the
  current method/config authority;
- corrected method identity is what the existing CV/final currentness chain
  consumes.

The independently calculated native-loss oracle may be a focused companion test
that feeds the **same production-exported batch** into MACE's real loss function.
It does not replace the real wrapper/trainer integration, and the integration
does not replace the oracle. This decomposition is preferable to intercepting
`tools.train` in the only acceptance test.

---

## 5. Final clarification C4 — dual closure at every executable repair stage

The previous R8 sequence mentioned focused stage checks but did not state the
full Protocol 5.15 stage-local affected-regression obligation explicitly.
Replace that sequencing rule with the following.

### R8-A — P5 method/currentness cutover

Before R8-B:

1. implement C1/R1;
2. complete semantic/conformance review for the P5 identity/currentness surface;
3. run focused currentness tests;
4. run the **stage-local affected regression** for P5 method resolution, CV
   planning/acceptance, final authorization, and trainer-launch guards;
5. proceed only when both semantic and functional closure pass.

### R8-B — historical DATA8 readability/current admission

Before R8-C:

1. implement C2/R2 in existing compatibility/serialization owners;
2. complete semantic/conformance review of legacy-read/current-execute
   separation;
3. run focused legacy digest/tamper/currentness tests;
4. run the **stage-local affected regression** for DATA8 serialization,
   compatibility/source-probe consumers, loader-dry-run/protocol identities,
   and any current builder/reader paths touched;
5. proceed only when both semantic and functional closure pass.

### R8-C — real-MACE proxy-proof acceptance

Before final closure:

1. implement/reconcile C3/R3 test and fixture changes without adding product
   machinery;
2. run focused low-level source/projection/runtime checks;
3. run the real target-size and replay-enabled P5 integrations with no required
   skips;
4. run the **stage-local affected regression** for wrapper/TRAIN2/P3/P5 behavior
   changed by any executable test-support or production repair edits;
5. proceed only when both semantic and functional closure pass.

### R8-D — final assembled acceptance

After all material executable edits:

1. reconcile the final implementation against the governing workplan, reopen,
   and this closure;
2. re-derive the complete affected surface from the assembled candidate;
3. run complete affected-surface regression on that exact candidate;
4. run repository/project-required checks;
5. rerun the required real-MACE integrations if any later executable change can
   plausibly invalidate them;
6. run the broader MLFF suite when the affected surface cannot be bounded with
   confidence;
7. record exact candidate SHA, commands, pass/fail/skip counts, and
   `mace-torch==0.3.16` identity in the existing evidence convention;
8. perform the independent Software Design closure review.

Required real-MACE acceptance tests that skip are incomplete acceptance.
Production-scale/GPU qualification remains deferred and must not be substituted
for functional regression/integration.

---

## 6. Simplicity and convergence guard

The implementation reviewed before this closure already added a substantial
source-qualified runtime repair. R1/R2/R3 are therefore a convergence point:
do not respond with another additive layer.

Before declaring implementation complete, inspect `critical_precision_cli.py`,
`mace_compatibility.py`, P3/P5 projection/currentness, and compatibility
serialization together and ask whether any repair-only state/helper can now be
removed or consolidated while preserving the accepted semantics.

A repair is suspect if it introduces any of the following:

- another wrapper or trainer;
- a second currentness or compatibility registry;
- parallel legacy/current DATA8 bundle hierarchies;
- a second scientific method record;
- a replacement loss implementation;
- duplicate runtime-evidence stores;
- generic source rewriting beyond the exact pinned behavior under qualification;
- a migration mechanism where historical read-only compatibility is sufficient.

Prefer a small schema-aware compatibility branch, one global P5 recipe cutover,
and reuse of the existing production-owner tests.

If the only way to close a blocker genuinely requires changing a Frozen
architecture decision, stop and reopen only that design surface. No current
evidence requires such a redesign.

---

## 7. Snapshot-complete implementation handoff

Implementation authority for this repair is the supplied current set:

1. `workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_REOPEN_WORKPLAN.md`
   — governing original repair design;
2. `workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_IMPLEMENTATION_REVIEW_REOPEN.md`
   — independently diagnosed residual blockers R1-R3;
3. this final design closure
   `workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_IMPLEMENTATION_REVIEW_FINAL_DESIGN_CLOSURE.md`
   — final clarification/narrowing of compatibility, acceptance, and stage gates;
4. current MLFF architecture/specification authority referenced by the governing
   workplan, especially the DATA8 MACE-artifact contract.

No prior chat, hidden review history, or superseded implementation note is
required to recover the still-binding task semantics.

Where wording conflicts:

```text
Tier-1/current architecture & specifications
  -> governing original repair workplan
  -> implementation-review reopen
  -> this final closure's explicit clarifications
  -> delegated implementation choice
```

This closure does not alter any scientific formula, candidate/reducer behavior,
P3/P4/P5 ownership, replay method, or final-production method. It only closes
implementation/currentness/compatibility/acceptance ambiguities.

---

## 8. Final Design disposition

**PASS — the plan is ready for implementation.**

There are no remaining known plan-level scientific, architectural, numerical,
compatibility-scope, currentness, testing-boundary, or stage-gating gaps.

Implementation remains **NO-PASS** until the concrete R1/R2/R3 repairs and all
R8-A through R8-D functional evidence close on one assembled candidate.

After implementation, the next review should be an implementation closure review,
not another redesign pass, unless new evidence invalidates a Frozen decision.
