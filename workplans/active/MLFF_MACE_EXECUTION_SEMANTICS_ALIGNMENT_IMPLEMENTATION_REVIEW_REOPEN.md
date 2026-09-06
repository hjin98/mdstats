---
kind: implementation-workplan-review-reopen
workplan_id: MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT-IMPLEMENTATION-REVIEW-REOPEN
parent_workplan_id: MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT-REOPEN
protocol_version: 5.15.0
status: implementation-repair-required
created_date: 2026-09-06
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_plan_commit: 4635b89fd9edd1a475a4c1873263f13faefc5fd6
reviewed_implementation_commit: 5d152dded08fc344a456d1716569b1f8bb71e6ad
reviewed_branch_head: a323a18c366444e711120b7747a66ee52e9f3932
design_verdict: pass-frozen-design-unchanged
implementation_review_verdict: no-pass
precedence: This review reopens implementation of the parent workplan. The parent workplan remains the governing design; this file adds only the bounded repair and acceptance obligations discovered by independent closure review. All non-conflicting Tier-1 invariants, forbidden patterns, gates, and acceptance requirements in the parent remain binding.
---

# MLFF MACE execution-semantics alignment — independent implementation review reopen

## 0. Verdict

**NO-PASS / bounded implementation repair required.**  
**Frozen scientific design and high-level architecture: PASS / unchanged.**

Independent Software Design review of implementation commit
`5d152dded08fc344a456d1716569b1f8bb71e6ad` found that the central runtime repair is directionally and architecturally correct: it keeps native MACE `WeightedEnergyForcesStressLoss`, explicitly controls replay balancing and multihead LR/EMA behavior, realizes complete target-size batches for the frozen `ceil(N/B)` normalization, and records resolved runtime semantics through the existing qualified MACE wrapper/TRAIN2 boundary.

The implementation also obeys the parent simplicity constraint in the important architectural sense: it does **not** introduce a second trainer, loss engine, replay system, compatibility registry, checkpoint authority, or process wrapper. The new runtime adaptation is concentrated in the already-accepted source-qualified `critical_precision_cli.py` seam.

Three genuine blockers remain:

1. **P5 non-replay method identity does not cut over when execution semantics changed.** Scratch and naive-fine-tuning runs now explicitly force `multiheads_finetuning=False`, but their current `PostSelectionMethodIdentity` is still byte-identical to the pre-repair method when all user configuration is unchanged. Pre-repair CV evidence can therefore authorize corrected final production despite having been executed under a materially different MACE method.
2. **The MACE compatibility/schema cutover breaks the repository's existing historical DATA8 readability contract.** `MaceCompatibilityPolicy` and `MaceSourceProbe` were versioned to v2 with v2-only readers, while `Data8PreparationBundle.from_dict()` still explicitly accepts historical DATA8 bundle/parser versions and directly delegates their nested v1 compatibility records to those v2-only readers. Historical/current pre-repair DATA8 artifacts therefore fail before their original digests can be authenticated.
3. **The parent workplan's proxy-proof and final executable acceptance has not been closed on the reviewed candidate.** The new real-`run_train.run()` tests stop immediately before `tools.train` and construct acceptance-critical ExtXYZ weights manually; the existing exporter test reaches the real exporter and MACE loss but stops before the repaired `run_train` mutation boundary. The two halves do not constitute the required assembled production-owner proof. Repository CI evidence for `5d152dde...` contains only the documentation-PDF workflow, not the required affected regression/real-MACE integration.

These are implementation/currentness/evidence defects. They do not justify revising the scientific objective, target-size mathematics, P1->P5 authority graph, replay method, or final-production architecture.

---

## 1. Global invariant analysis

### 1.1 Core problem of concern

The parent workplan's core problem remains:

> the scientific method authenticated by mdstats must be the scientific method that pinned MACE 0.3.16 actually executes.

The implementation closes the original direct runtime contradictions:

- replay-enabled execution is source-qualified so MACE's internal forced `UniversalLoss` assignment cannot replace the accepted `loss="stress"` method;
- MACE's native `get_loss_fn()` remains the loss owner; mdstats did not add another loss implementation;
- replay jobs explicitly resolve `force_mh_ft_lr=True` and `real_pt_data_ratio_threshold=0.0`;
- target-size execution records complete target membership and `drop_last=False`, so real target-size update geometry can equal the frozen `ceil(N/B)` definition;
- resolved loss class, optimizer settings, replay exposure, membership digests, and target-size batch geometry are checked at the real dependency boundary and carried into TRAIN2 runtime evidence.

This is the correct solution direction and must be preserved.

### 1.2 Frozen architecture remains valid

Do not redesign the accepted authority graph:

```text
canonical frame authority
  -> neutral statistical substrate
  -> one P_train / M3 split
  -> one pi_train / pi_eval
  -> one common deterministic preparation
  -> paired (N, optimizer-seed) target-size screen
  -> exact n1 -> n2 -> n3 continuation
  -> target-only EVAL2 reduction
  -> one N_selected / T_selected
  -> post-selection CV on exactly T_selected
  -> fresh final production on exactly T_selected
```

The reviewed implementation does not expose a reason to change:

- exact nested `T_N` membership;
- paired-seed reduction/ranking;
- target-only force-component RMSE;
- common preparation and fitted-weight ownership;
- normalized target-size LR/EMA equations;
- P3 restart/checkpoint authority;
- P4 terminal/adoption authority;
- selected-only P5 cross-validation;
- fresh final production;
- dependency-native weighted energy/forces/stress objective;
- deferred production-scale/GPU qualification.

The blockers below are failures to make currentness, compatibility, and evidence match that architecture.

---

## 2. Blocker R1 — global P5 method cutover is incomplete for scratch and naive fine-tuning

### 2.1 Diagnosis

Before this implementation, `post_selection_mace_run_configuration()` emitted `multiheads_finetuning=True` only for explicit replay jobs and emitted **no value** for non-replay jobs. Pinned MACE 0.3.16 therefore supplied its parser default `multiheads_finetuning=True` for ordinary scratch/naive configurations.

The implementation correctly changes current P5 projection to emit an explicit boolean for every job, with `False` for non-replay execution. This is a material method correction: it determines whether MACE enters its multihead-fine-tuning argument-mutation path.

However, the existing P5 scientific identity does not globally cut over:

- `resolve_post_selection_method_identity()` already used
  `method_recipe_version="mdstats.post-selection-method.2026-09.v2"` before this repair and still uses the same value;
- the no-replay `resolve_post_selection_replay_policy_digest()` payload is unchanged and does not bind `MACE_EXECUTION_SEMANTICS_VERSION` or explicit `multiheads_finetuning=False`;
- only replay-enabled replay-policy payloads gained the new execution-semantics/control fields.

Final-production authorization is explicitly method-digest based: accepted CV must bind the same `PostSelectionMethodIdentity.content_digest` that current final production resolves. Therefore an old scratch/naive CV authorization can remain method-compatible with corrected execution even though MACE's resolved method changed.

That violates the frozen invariant:

> historical accepted evidence is never silently reinterpreted under corrected execution semantics.

### 2.2 Required repair

Use the existing P5 method-identity owner. **Do not add a new runtime-method class, compatibility registry, or second authorization digest.**

Preferred minimal repair:

1. cut over the existing `PostSelectionMethodIdentity.method_recipe_version` once for this corrected MACE execution semantics (for example from current `...v2` to the next version) **for all three supported P5 training modes**;
2. preserve the already-added replay-policy execution-semantics fields; do not move them into another owner merely to perform the global cutover;
3. keep the current explicit executable `multiheads_finetuning=False` for scratch/naive and the explicit replay controls for multihead replay;
4. do not rewrite or migrate stored CV/final evidence to the new method digest;
5. let the existing `require_cv_acceptance_for_method()` / final-production plan validation reject old evidence before trainer launch.

A global recipe-version cutover is preferred over putting a fake execution-semantics field into the disabled replay-policy payload, because this change affects the P5 training method itself, not replay only.

### 2.3 Acceptance

Add focused currentness tests through the existing P5 owners:

- unchanged scratch config: synthetic/pre-repair `...v2` CV acceptance cannot authorize the corrected current method;
- unchanged naive-fine-tuning config: same rejection before `MacePostSelectionTrainer` launch;
- replay-enabled old evidence remains rejected as it is now;
- current corrected CV acceptance authorizes current final production through the same existing owner;
- changing only execution-semantics recipe identity changes P5 method/CV/final currentness, while P4 selected `N/T_selected` remains unchanged;
- no new method/currentness hierarchy is introduced.

---

## 3. Blocker R2 — nested compatibility schema cutover breaks historical DATA8 readability

### 3.1 Diagnosis

At the parent-plan base:

```text
MACE_COMPATIBILITY_POLICY_SCHEMA = mdstats.mace-compatibility-policy.v1
MACE_SOURCE_PROBE_SCHEMA          = mdstats.mace-source-probe.v1
```

The implementation changes both to v2 and makes both `from_dict()` readers accept only their current v2 schema.

At the same time, the existing DATA8 reader still explicitly accepts:

```text
mdstats.data8-preparation-bundle.v1
...v2
...v3
...v4
...v5
```

and the historical parser-version set, then unconditionally calls:

```text
MaceCompatibilityPolicy.from_dict(payload["compatibility_policy"])
MaceSourceProbe.from_dict(payload["compatibility_probe"])
```

A DATA8 artifact written immediately before this repair therefore contains accepted v1 nested compatibility records but is now rejected by the v2-only nested readers before its historical digest can be authenticated. This contradicts the repository's established DATA8 compatibility surface, which intentionally keeps historical DATA8 schemas readable while keeping them non-current.

This repair must not solve current semantic drift by making historical evidence unreadable.

### 3.2 Required repair

Repair the existing compatibility readers/serialization owners in place. **Do not add a new legacy-bundle class, migration database, compatibility registry, or shadow DATA8 hierarchy.**

Required end state:

1. current construction continues to emit the corrected current compatibility/source-probe representation and current execution-semantic evidence;
2. exact accepted pre-repair v1 `MaceCompatibilityPolicy` and `MaceSourceProbe` payloads remain readable as historical records with their **original serialized payload/digests authenticated**, not silently upgraded to corrected semantics;
3. a historical v1 nested compatibility/probe representation can never satisfy the current corrected execution-compatibility/currentness gate merely because it is readable;
4. DATA8 v1-v5 historical outer payload digest verification remains correct, including pre-repair v5 payloads whose nested records are v1;
5. tampered legacy policy/probe/bundle payloads fail closed;
6. current v2 compatibility/probe records continue to source-qualify all four repaired MACE behavior families required by the parent workplan.

Implementation should first seek a **reduction**: retain the existing versioned reader pattern and add only the minimum legacy branch/state needed to preserve the already-supported serialization surface. If `execution_semantics_version` does not need to be a field of `MaceCompatibilityPolicy` because the existing method/runtime identities already strongly bind it, simplifying that ownership is preferable to adding another compatibility layer. Any such simplification must preserve the current source-probe/runtime fail-closed guarantees.

### 3.3 Acceptance

Use actual serialized fixtures generated from the pre-repair v1 classes/payload shapes, not hand-waved dictionaries only:

- pre-repair v1 compatibility policy round-trips/authenticates its original digest as historical;
- pre-repair v1 source probe round-trips/authenticates its original digest as historical;
- a pre-repair DATA8 v5 bundle containing those nested v1 records loads through the existing DATA8 reader and preserves the original outer digest;
- at least one older supported DATA8 outer schema remains readable if it is still in the declared reader set;
- current execution rejects the historical compatibility/probe as non-current before MACE launch;
- current v2 DATA8/current construction remains unchanged;
- tampering with any nested legacy digest/field is rejected.

If the implementation instead intends to retire legacy DATA8 readability, stop: that is an architecture/compatibility-policy change outside this workplan and requires explicit design authority rather than an incidental implementation side effect.

---

## 4. Blocker R3 — proxy-proof real-MACE acceptance and final regression are not yet closed

### 4.1 What the current tests prove

The new `tests/test_mlff_mace_execution_semantics.py` is valuable and should be retained/reduced rather than replaced. It crosses the real MACE parser and `run_train.run()` mutation region, resolves real loaders and native `WeightedEnergyForcesStressLoss`, and demonstrates:

- target-size `drop_last=False` for divisible/non-divisible synthetic target counts;
- explicit P5 single-head `multiheads_finetuning=False`;
- replay `loss="stress"`, non-default LR/EMA preservation, `force_mh_ft_lr=True`, threshold zero, and no implicit target duplication;
- correct resolved native loss coefficients.

The pre-existing `tests/test_mlff_target_size_mace_objective_realization.py` separately proves that the production P3 materialization/export path writes configuration weights/property masks correctly and that native MACE weighted-MSE reduction consumes them correctly.

### 4.2 Remaining proxy gap

The acceptance-critical real-`run_train` fixtures in the new test create ASE frames directly and inject:

```text
config_weight
config_energy_weight
config_forces_weight
config_stress_weight
```

from test literals. They do not consume a production mdstats materialization for the same run that crosses the repaired `run_train` boundary.

Conversely, the production-export objective test calls the real parser/`get_loss_fn` directly and therefore does not cross the repaired MACE post-parse mutation/source-patch boundary.

Thus there is still no single proxy-proof acceptance chain proving:

```text
mdstats scientific policy
 -> real mdstats materialization/export
 -> real parser-facing config
 -> qualified wrapper
 -> real MACE run_train mutations
 -> native loss + real loader
 -> at least one real TRAIN2 update/boundary
```

The parent G2/G5 explicitly required this assembled boundary and explicitly rejected parser equality, source grep, mocks, or required tests that skip as closure evidence.

### 4.3 Required repair of tests/evidence — no new test machinery

Alter/reuse the existing fixtures and production owners; do not create another trainer or acceptance harness.

#### Target-size

Reuse `tests/test_mlff_target_size_p3_realized_mace_architecture.py` and its real `MaceTargetSizeBoundaryTrainer`/qualified-wrapper helper, or equivalently reuse the existing production fixture. Add a deliberately non-divisible **real training** case, for example a current admissible target size with `B=3` so `N % B != 0`.

Require the completed TRAIN2 summary/runtime evidence to prove on the same real run:

- complete exact target membership UID digest;
- `target_drop_last=False`;
- `target_updates_per_epoch=ceil(N/B)`;
- completed optimizer-update count consistent with that geometry;
- resolved native weighted-stress loss;
- no restart/currentness regression.

Do not satisfy this gate with `_StopAfterResolution` alone.

#### Replay-enabled P5

Reuse the existing P5 materialization/`MacePostSelectionTrainer` owners and tiny foundation/replay fixtures. The target ExtXYZ entering MACE must be the actual production P5/mdstats export output; do not write acceptance-critical target weights directly into synthetic ASE objects after export.

Use deliberately distinguishable values:

- non-default E/F/S objective coefficients;
- at least one non-unit realized configuration weight;
- at least one missing-property zero mask if the production P5 fixture supports the same canonical label contract;
- target/replay ratio below MACE's native `0.1` threshold;
- non-default LR/EMA values.

Run far enough through the **real qualified wrapper and native MACE trainer** to produce a real TRAIN2 summary/boundary with runtime evidence. Prove on that same assembled path:

- native `WeightedEnergyForcesStressLoss` executes;
- global coefficients and exported configuration/local weights remain separate;
- `force_mh_ft_lr=True` preserves configured LR/EMA;
- threshold zero prevents target duplication;
- runtime evidence is bound to the run/method and persisted in TRAIN2;
- corrected CV/final currentness consumes the corrected method identity.

The existing low-level `_StopAfterResolution` tests may remain as fast focused tests, but they are not the final integration gate.

### 4.4 Final executable evidence

After R1/R2 and the proxy-proof test correction, run the parent G5 affected-surface regression on the exact final executable candidate. At minimum include all files/modules changed by this repair and the parent implementation, especially:

- MACE compatibility/source probe;
- critical-precision wrapper/restart patch;
- target-size candidate/context/runtime/TRAIN2/restart/EVAL2 affected tests;
- P5 method identity/CV acceptance/final authorization/execution;
- DATA8 legacy-schema compatibility;
- objective/configuration-weight/export realization;
- executable config serialization and currentness guards.

Then run the broader MLFF suite if the transitive surface cannot be bounded confidently.

Required real-MACE tests must **execute**, not skip. Record exact candidate SHA, commands, pass/fail/skip counts, and the real-MACE version in the existing workplan/evidence convention. Production-scale/GPU qualification remains deferred.

As of reviewed commit `5d152dde...`, the repository exposes one GitHub Actions run for that SHA and it is only `Build documentation PDFs`; no affected-regression or real-MACE acceptance run is attached. This is not proof that local tests failed, but it is insufficient evidence for the parent G5/G7 closure gate.

---

## 5. Accepted implementation state to preserve

Do not reopen or replace the following implementation decisions unless the repair itself proves a concrete defect:

- one existing qualified wrapper seam in `critical_precision_cli.py`;
- exact MACE 0.3.16 source/version qualification and fail-closed marker checks;
- source-qualified prevention of the forced `UniversalLoss` transition while retaining native `get_loss_fn()`;
- explicit replay `force_mh_ft_lr=True` and `real_pt_data_ratio_threshold=0.0`;
- explicit non-replay `multiheads_finetuning=False`;
- P3 target-size `drop_last=False`, complete target membership, no padding duplication, and distributed fail-closed behavior;
- `MACE_EXECUTION_SEMANTICS_VERSION` in target-size loader geometry/currentness;
- resolved execution evidence carried by TRAIN2 and compared across target-size continuation;
- exact raw-MACE restart-epoch handoff correction;
- existing P3/P4/P5 scientific ownership and final-production freshness.

The repair should be materially smaller than the already-landed execution-semantics implementation. If it starts adding another wrapper, compatibility hierarchy, trainer, loss, or currentness layer, stop and simplify.

---

## 6. Repair sequence

### R8-A — close P5 method identity first

Implement R1 and its focused currentness tests. Exit only when old scratch, naive, and replay CV evidence all fail to authorize the corrected method through the existing final-production owner.

### R8-B — restore historical DATA8 readability without making it current

Implement R2 in the existing compatibility/deserialization owners. Exit only when exact pre-repair nested v1 records and supported historical DATA8 bundles are readable/digest-authenticated but cannot authorize current corrected execution.

### R8-C — close assembled real-MACE acceptance

Modify/reuse the existing tests as R3 requires. Run the real production owners with bounded CPU work; do not add another harness whose semantics are easier than production.

### R8-D — final regression and independent closure review

On one final executable SHA:

1. run stage-local focused tests for R8-A/B/C;
2. run complete affected-surface regression;
3. run the required real-MACE target-size and replay-enabled P5 integrations without skips;
4. perform a fresh independent Software Design product-alignment review against the parent workplan, this reopen, current architecture/specifications, and pinned MACE 0.3.16 source;
5. perform active-simplicity review of `critical_precision_cli.py` and `mace_compatibility.py`; remove redundant repair-only logic if a smaller equivalent owner is now evident;
6. PASS only if no genuine Tier-1/Frozen scientific, currentness, compatibility, numerical, runtime, or acceptance blocker remains.

If the result passes, archive the parent workplan and this review together according to the existing workplan lifecycle. If a blocker remains, update this same implementation lineage rather than inventing another parallel design.

---

## 7. Final review disposition

**Software Design:** PASS — no frozen scientific or high-level architecture change is required.  
**Implementation:** **NO-PASS** — R1, R2, and R3 must close before this workplan can be archived.
