---
kind: implementation-repair-workplan
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-REALIZED-MACE-ARCHITECTURE-REPAIR
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
related_packages:
  - CODE-MLFF-TARGET-SIZE-V7-P3
  - CODE-MLFF-TARGET-SIZE-V7-P4
protocol_version: 5.14.0
status: implementation-ready
created_date: 2026-09-04
reviewed_baseline_commit: fa549de76692d56d2e6a6a76720da4c660f5ce9b
reviewed_baseline_tree: 68d07f85fd30a5585a057849c76149508f5c9ac8
trigger: real Boundary-1 TRAIN2 succeeds, but direct authenticated EVAL2 rejects the reconstructed candidate model because the actual MACE execution architecture differs from the canonical candidate configuration
scope: P3 study-wide MACE model-construction normalization, single-head realization, TRAIN2/EVAL2 architecture equivalence, generation invalidation, and affected P4/P5 regression only; no P1/P2 target-size scientific redesign
---

# P3 TRAIN2/EVAL2 realized MACE architecture identity repair

## 0. Disposition

**Design/workplan verdict: PASS / implementation-ready.**

The failure is not evidence that the authenticated EVAL2 architecture check is too strict. The check has correctly exposed that the real pinned-MACE TRAIN2 path is constructing a different model than the candidate configuration later reconstructs for EVAL2.

This is an implementation nonconformance inside the already accepted P3 architecture. In particular, P3 already freezes one common deterministic preparation for the whole target-size study and requires every fitted normalization/preprocessing quantity consumed by candidate training to be fitted once at common-preparation scope rather than refitted as N changes. The real run proves that MACE currently recomputes one model-affecting normalization (`avg_num_neighbors`) independently from each candidate training loader. That makes N change more than data cardinality and therefore violates the existing P3 contract.

The repair must correct the real TRAIN2 model-construction inputs and make the candidate configuration an exact reconstruction authority. It must **not** weaken architecture authentication, infer architecture from checkpoint state, accept post-hoc drift, or add a compatibility fallback.

This is also a second failure at the same canonical-configuration -> MACE-realization boundary immediately after the executable-config serialization repair. Under Protocol 5.14 active-simplicity rules, another field-by-field EVAL2 exception is not acceptable. The implementation must close the complete model-construction family: every model-affecting value that MACE can default, derive, normalize, rename, or overwrite before `configure_model(...)` must have one deliberate P3 authority and identical TRAIN2/EVAL2 realization.

Long GPU/production qualification remains deferred. The repair requires bounded real-MACE functional integration and affected regression.

---

## 1. Trigger and observed production evidence

A real `select-target-size` run on the current implementation now crosses the previously broken configargparse boundary, materializes the N=128/seed=1 candidate, starts MACE 0.3.16, completes durable epoch 0, and saves the TRAIN2 checkpoint/model.

The decisive runtime facts are:

```text
Using heads: ['Default']
...
Computing average number of neighbors
Average number of neighbors: 26.85965347290039
...
Epoch 0 ...
mdstats TRAIN2B paused after durable epoch 0
```

Immediately afterward, direct target-size EVAL2 fails before numerical inference:

```text
TrainingDataInputError:
Candidate MACE configuration reconstructs a different execution architecture
from the authenticated TRAIN2 model.
```

That error is raised by `authenticate_train2_checkpoint_provider(...)` after:

1. loading and authenticating the actual TRAIN2 state-dict checkpoint and continuation companion;
2. taking the candidate materialization/configuration as the architecture authority;
3. reconstructing a real MACE model from that configuration;
4. computing the canonical weight-independent execution-architecture digest of the reconstructed model; and
5. comparing it with the architecture digest persisted from the **actual real model trained by MACE** at the durable boundary.

The VASP interrupted-XML/velocity warnings and PyTorch/TorchScript deprecation warnings in the same run are non-causal and outside this repair.

---

## 2. Root-cause reconstruction

### 2.1 The architecture mismatch is real, not a stale digest

TRAIN2's runtime owner computes `model_architecture_digest` directly from the live real MACE model at durable checkpoint persistence and places that digest in both the runtime companion and runtime summary. EVAL2 independently reconstructs from the candidate configuration and computes the same canonical descriptor on the reconstructed model.

The two digests therefore disagree because the two models are structurally different. Do not change the digest comparison to make the error disappear.

### 2.2 Guaranteed drift #1 — P3 canonical head versus MACE fallback head

The current canonical target-size MACE architecture requires:

```text
heads = ['target_head']
```

and `build_mace_model_from_configuration(...)` reconstructs the model with that exact head list.

The real P3 executable config, however, intentionally does not emit the internal architecture `heads` list as MACE's `--heads` argument. With no explicit MACE dataset-head mapping, pinned MACE 0.3.16 calls `prepare_default_head(...)`, whose single head is named:

```text
Default
```

The production log confirms that real TRAIN2 therefore builds `model.heads == ['Default']`.

The previous serialization repair was correct to reject **blind** projection of internal `mace_architecture['heads']`: a model-head list is not the same type as MACE's `--heads` dataset-head dictionary. But P3 already materializes an explicit one-head target dataset mapping under its canonical candidate config. The missing step is a deliberate P3 dataset-head projection, not restoration of blind architecture flattening.

### 2.3 Guaranteed drift #2 — MACE recomputes model normalization per N

The current canonical architecture obtains `avg_num_neighbors` from MACE parser/default canonicalization before data loading; absent an explicit common fit, the canonical value is the parser-side default.

Pinned MACE 0.3.16 later executes:

```text
args.avg_num_neighbors = get_avg_num_neighbors(head_configs, args, train_loader, device)
```

and the parser default is:

```text
compute_avg_num_neighbors = True
```

Therefore real TRAIN2 discards the canonical/default normalization and recomputes it from the current candidate training loader. The real N=128 run reports:

```text
avg_num_neighbors = 26.85965347290039
```

`avg_num_neighbors` is not merely logging. It is consumed when constructing MACE interactions and is explicitly part of mdstats' canonical execution-architecture descriptor (`interaction_avg_num_neighbors`). It affects forward normalization and model behavior.

This is a **scientific execution nonconformance**, not only an authentication inconvenience. Candidate-local recomputation makes a model-construction parameter a function of `T_N`, so changing N changes both training data cardinality and model normalization. P3 explicitly forbids candidate-specific normalization/refitting and requires all fitted quantities consumed by training to be frozen once in the common preparation.

### 2.4 Existing tests miss the real owner boundary

The current P3A4 real-MACE authentication tests construct their model with `build_mace_model_from_configuration(...)`, compute the expected architecture digest from that same reconstructed model, and then save a MACE-shaped checkpoint from it.

Those tests are valuable for checkpoint/state/EMA authentication, but they do not execute pinned MACE's real pre-`configure_model(...)` training path. They therefore cannot detect:

- `prepare_default_head(...)` renaming the head to `Default`;
- `get_avg_num_neighbors(...)` replacing the configured normalization from the actual training loader;
- any sibling model-affecting parser/data-loader mutation performed by `run_train(...)` before model construction.

This is a proxy-acceptance gap. Final acceptance must cross the real MACE training/model-construction owner.

---

## 3. Authority classification

### 3.1 Tier 1 / product and scientific invariants

Preserve all accepted P1/P2/P3 scientific behavior:

- `N` remains the sole target-size data-cardinality variable;
- exact P2 `T_N` membership, M1/M2/M3 membership, candidate qualification, seed set/order, reducer/ranking, practical-equivalence, and terminal selected-size semantics do not change;
- one common deterministic fitted preparation is used across every N and optimizer seed;
- candidate preparation remains exact projection/selection only;
- no candidate-specific E0, normalization, configuration-weight, preprocessing, or model-construction refit is permitted;
- one continuous TRAIN2 trajectory is preserved across configured fidelity boundaries;
- exact authenticated boundary state remains the only admissible EVAL2 state;
- direct exact-M EVAL2 remains the ranking evidence owner;
- P4 CampaignStore/generation/currentness ownership remains intact;
- long GPU/production qualification remains distinct and deferred.

### 3.2 Frozen high-level architecture for this repair

Freeze the following implementation-cycle architecture because it is necessary to preserve the accepted scientific experiment:

1. **One study-wide P3 MACE construction authority.** Seed-neutral/N-neutral model-construction inputs are resolved once and bound into P3 common/execution identity before candidate materialization.
2. **One common MACE neighbor normalization.** `avg_num_neighbors` is derived once from the accepted common training membership (normally P2 `P_train`) under the exact pinned MACE neighbor/cutoff semantics and reused unchanged by every candidate.
3. **No MACE candidate-local normalization.** Real TRAIN2 must run with MACE neighbor recomputation disabled and must consume the bound common value.
4. **One explicit P3 target dataset/model head realization.** The P3 target head must be deliberately supplied to MACE from the canonical P3 target dataset mapping so real TRAIN2 and EVAL2 construct the same single-head model. The incidental MACE fallback namespace `Default` is not a second P3 architecture authority.
5. **Candidate configuration remains the reconstruction authority.** Raw TRAIN2 checkpoint/companion objects provide authenticated state, not architecture.
6. **The canonical execution-architecture digest remains fail-closed.** TRAIN2 persists the actual model digest; EVAL2 independently reconstructs and must match it before loading/evaluating state.
7. **Existing generation/currentness machinery owns invalidation.** A change to common MACE normalization/model-construction identity starts/requires a fresh current target-size generation; old screen evidence is never reinterpreted under the repaired identity.

### 3.3 Delegated solution space

The implementer may choose the smallest coherent internal representation that realizes the frozen architecture above. In particular, it may:

- extend `TargetSizeCommonTrainingPolicy` / `TargetSizeCommonPreparation` directly;
- add one small immutable common-MACE-normalization subrecord if that reduces validation duplication;
- bind a realized architecture/template digest through the existing execution context;
- refactor existing candidate architecture canonicalization so one seed-neutral template is resolved once rather than repeatedly;
- reuse a pinned-MACE helper to compute common neighbor normalization instead of reimplementing the formula.

Do **not** create a parallel architecture registry, compatibility state machine, retry layer, second model-config authority, or P3-only MACE fork.

---

## 4. Required end state

The assembled P3 flow must reduce to one model-construction contract:

```text
P2 P_train + frozen P3 MACE architecture template
        |
        | one common fit under pinned MACE graph/neighbor semantics
        v
P3 common preparation
  - common E0s
  - common frame/property weights
  - common avg_num_neighbors
  - seed-neutral/N-neutral MACE construction identity
        |
        +------------------------------+
        |                              |
        v                              v
candidate T_N projection          EVAL2 reconstruction
(no refit)                        (same construction identity)
        |                              ^
        v                              |
canonical candidate config             |
        |                              |
        | explicit target-head mapping |
        | avg_num_neighbors = common   |
        | compute_avg_num_neighbors=F  |
        v                              |
pinned MACE 0.3.16 run_train           |
        |                              |
        v                              |
actual TRAIN2 model -------------------+
        |
        v
actual architecture digest == reconstructed architecture digest
```

For every screened N and seed, the following must be true before any checkpoint state is loaded into EVAL2:

```text
mace_model_execution_architecture_digest(actual TRAIN2 model)
==
mace_model_execution_architecture_digest(model reconstructed from canonical candidate config)
```

The equality must arise because both sides are genuinely the same architecture, not because the descriptor was weakened.

---

## 5. Implementation obligations

### 5.1 Census every model-affecting MACE mutation before editing

Before changing code, inspect the exact pinned `mace-torch==0.3.16` path from parser/check-args through dataset/head preparation and the final `configure_model(...)` call.

Build a field-level table for every P3 model-construction input that can be:

- parser-defaulted;
- normalized by `check_args`;
- derived from target/harness data;
- derived from a head configuration;
- derived from a foundation model (should be absent for P3 scratch screening);
- rewritten immediately before `configure_model(...)`;
- or otherwise capable of changing `mace_model_execution_architecture_digest(...)`.

At minimum the census must include:

- model family/class;
- head list / dataset-head names;
- atomic-number table/order;
- r_max/cutoff;
- radial basis/cutoff basis and distance transform;
- interaction classes/count;
- hidden/edge irreps and channel/max-L derivation;
- product/correlation/readout settings;
- radial MLP;
- `avg_num_neighbors` and `compute_avg_num_neighbors`;
- dtype/precision;
- scaling/mean/std where they can alter constructed modules;
- embedding/readout/cutoff flags;
- any additional field discovered in the exact pinned path.

Classify each as:

1. fixed seed-neutral P3 architecture;
2. common fitted P3 value;
3. authorized candidate-varying value that does **not** change model architecture;
4. external MACE syntax only;
5. forbidden candidate-local model-construction derivation.

**Gate requirement:** do not patch only the two already observed fields if the exact source census finds another TRAIN2/EVAL2 construction divergence.

### 5.2 Resolve one seed-neutral P3 MACE architecture template

The current production path calls candidate architecture defaults during individual materialization. Replace that effective repeated/default authority with one seed-neutral/N-neutral template resolved at the study/common authority boundary.

The template must bind every fixed model-construction field needed by P3 and the pinned MACE compatibility identity. It must not contain optimizer seed, N, active boundary, candidate file path, or outcomes.

The same resolved template must feed:

- common MACE normalization fitting;
- every P3 candidate materialization;
- real TRAIN2 executable projection;
- EVAL2 model reconstruction;
- restart/currentness validation.

Do not let TRAIN2 use a fresh parser default while EVAL2 uses a persisted template, or vice versa.

### 5.3 Fit `avg_num_neighbors` once at common-preparation scope

Extend the existing P3 common-preparation authority so the actual MACE neighbor normalization consumed by model construction is a durable, validated, seed-neutral/N-neutral common value.

Required semantics:

- fit membership = exact accepted P2 `P_train`, not `T_N`, M1/M2/M3, CV, harness-only membership, or a candidate subset;
- cutoff/neighbor semantics = the same pinned MACE 0.3.16 semantics and r_max used by candidate training;
- computation is deterministic for fixed common membership + architecture/compatibility identity;
- the result is finite and strictly positive;
- its identity is bound into `TargetSizeCommonPreparation.content_digest` directly or transitively;
- the execution context therefore changes when this common model normalization changes;
- candidate projection merely copies/references the common value and never recomputes it.

Prefer reuse of MACE's own supported neighbor construction/average-neighbor machinery, or a shared existing mdstats owner already proven equivalent. Do not introduce an independent approximate formula merely to avoid the dependency boundary.

The implementation may persist only the scalar plus enough parent identity to prove its meaning; do not persist candidate graph caches or a new normalization database.

### 5.4 Make real TRAIN2 consume the common normalization exactly

The P3 executable MACE config must deliberately set both sides of the pinned parser contract:

```text
avg_num_neighbors = <common fitted value>
compute_avg_num_neighbors = false
```

or the exact equivalent accepted by MACE 0.3.16.

The common value must be the one already bound into P3 common/config identity. `mace_run_configuration(...)` may translate syntax, but it may not calculate a new value.

A real TRAIN2 run must not log/execute `Computing average number of neighbors` for P3 screening. If the pinned MACE code still recomputes despite the executable setting, treat that as an unresolved implementation failure rather than accepting the recomputed number after the fact.

### 5.5 Deliberately project the P3 single target head

P3 already materializes the exact target training/validation dataset mapping under its canonical target-head namespace. Translate that mapping deliberately into MACE's `--heads` dataset-head dictionary for P3 scratch screening.

Required P3 result:

```text
actual MACE model heads == ['target_head']
reconstructed EVAL2 model heads == ['target_head']
```

Use the existing structured-literal serializer introduced by the prior MACE config repair so nested `atomic_numbers`/`E0s` obey pinned parser syntax. Do not reintroduce blind `mace_architecture['heads']` projection.

The source of the MACE dataset-head mapping must be the canonical P3 target dataset/config owner, not a second hand-written duplicate in `campaign_target_size_runtime.py`.

Do not set `multiheads_finetuning=True`; P3 remains one-head scratch screening with no replay/foundation state. An explicit one-head `heads` dictionary is a namespace/configuration declaration, not P5 multihead replay.

### 5.6 Preserve P5 head semantics and shared serializer correctness

P5's canonical post-selection heads remain `target_head` / `pt_head`, and P5 multihead replay continues to emit exactly those two dataset heads through its existing real MACE `heads` mapping.

If shared architecture canonicalization or executable serialization is changed, re-run P5 scratch, naive-fine-tuning, and multihead parser/integration regression. Do not globally rename P5 or foundation heads to `Default` as a shortcut for the P3 mismatch.

### 5.7 Candidate configuration must describe the model TRAIN2 actually constructs

After the repair, the canonical P3 candidate configuration must contain or transitively bind the exact model-construction values used by TRAIN2, including:

- the seed-neutral architecture template;
- the common `avg_num_neighbors` value;
- the one-head target realization;
- atomic-number table/order;
- dtype/precision;
- all other model-affecting fields from the Gate-5.1 census.

`build_mace_model_from_configuration(...)` must reconstruct the same model without reading checkpoint state, TRAIN2 companion model objects, TRAIN2 logs, or post-hoc realized values.

The raw checkpoint remains a state-dict source only.

### 5.8 Keep the architecture descriptor strong

Do not remove or relax any currently justified fields from `_mace_model_execution_architecture_descriptor(...)` merely to make the digest match.

In particular, preserve binding of:

- model class;
- head structure;
- interaction `avg_num_neighbors`;
- parameter structure/dtype;
- model-owned non-calibration buffer values;
- module census and other current graph-affecting architecture fields.

If the Gate-5.1 census discovers a model-affecting value that is **not** currently visible to the descriptor, strengthen the canonical descriptor only when necessary to protect genuine execution equivalence, and then run all hot-swap/runtime-architecture affected regression. Do not add redundant identity fields that are already transitively represented by model structure/buffers.

### 5.9 Invalidate the old P3 screen truthfully

This repair changes a genuine model-construction/scientific execution identity: candidate-local neighbor normalization is replaced by a common fitted value, and the real P3 head realization becomes explicit.

Therefore old candidate materializations/TRAIN2 checkpoints produced under the old identity must not be silently resumed or reinterpreted.

Use the existing current-generation authority:

- new common-preparation/model-construction identity changes the bound P3 digest;
- `select-target-size` against an old canonical generation must fail closed and direct the user through the existing `prepare`/fresh-generation path;
- the new generation receives a fresh execution root/screen evidence;
- old generation data may remain immutable historical evidence but is not admissible under the repaired context.

Do not special-case the observed epoch-0 N=128 checkpoint for reuse. Do not ask the user to manually delete checkpoints as part of correctness.

Bump only the affected internal schema/version(s) necessary to make this incompatibility explicit. Do not bump the global development protocol or manufacture a repository-wide compatibility layer.

---

## 6. Expected affected surface

Minimum production surface to inspect and likely modify:

- `mdstats/training_data/target_size_execution/common.py`
  - `TargetSizeCommonTrainingPolicy`
  - `TargetSizeCommonPreparation`
  - `build_target_size_common_preparation(...)`
  - new/extended common MACE normalization ownership
- `mdstats/training_data/target_size_execution/context.py`
  - binding of the seed-neutral/common MACE construction identity if not already transitive through common preparation
- `mdstats/training_data/target_size_execution/candidate.py`
  - canonical P3 MACE configuration
  - candidate materialization/validation
  - use of one common architecture template rather than candidate-local/default realization
- `mdstats/training_data/campaign_target_size_runtime.py`
  - `mace_run_configuration(...)`
  - real P3 target-head projection
  - executable `compute_avg_num_neighbors=False`
  - current-authority construction plumbing
- `mdstats/training_data/model_features.py`
  - candidate architecture canonicalization/model reconstruction only where needed
  - **do not** weaken `mace_model_execution_architecture_digest(...)`
- `mdstats/training_data/mace_compatibility.py`
  - only if the existing literal/config projection helper needs a minimal generic extension for `compute_avg_num_neighbors` or explicit P3 heads
- `mdstats/training_data/target_size_execution/evaluation.py`
  - expected to remain mostly unchanged; architecture mismatch check remains authoritative
- current P4 generation/cutover owners only if schema invalidation plumbing requires them; no new currentness owner.

Minimum test surface to re-derive and extend:

- `tests/test_mlff_target_size_execution_p3a.py`
- candidate/materialization/runtime P3B/P3C tests
- `tests/test_mlff_target_size_p3a4_final_review.py`
- `tests/test_mlff_target_size_p4d_runtime_cutover.py`
- assembled P4 target-size integration tests
- MACE config parser/projection tests added by the previous serialization repair
- P5 post-selection parser/execution tests if shared architecture/serialization helpers change
- hot-swap/runtime architecture tests if the canonical architecture descriptor changes.

The implementer must re-derive callers/references from the final diff; this list is a floor, not a filename whitelist.

---

## 7. Implementation gates

## Gate A — complete realized-construction census

Before behavior edits:

1. inspect exact pinned MACE 0.3.16 `build_default_arg_parser`, `check_args`, `run_train`, head preparation, dataset loading, `get_avg_num_neighbors`, and `configure_model` call path;
2. enumerate every model-affecting field at the point `configure_model` is called;
3. map each field back to the current P3 canonical/common/candidate authority;
4. identify every field whose real TRAIN2 value can differ from `build_mace_model_from_configuration(...)`;
5. inspect all production P3/P5 uses of the shared candidate architecture canonicalizer and executable-config helper before changing their semantics;
6. use Serena/reference tooling when available for symbol ownership/callers and a focused Semgrep/AST query when available for structural config projection/build sites; ordinary GitHub/source search is an acceptable fallback when those engines are unavailable in the active host.

**Gate A exit:** a complete table explains the two observed mismatches and closes all sibling model-construction divergences before implementation starts.

## Gate B — common normalization and exact P3 model configuration

Implement the minimum coherent repair:

1. resolve one seed-neutral P3 MACE architecture template;
2. fit common `avg_num_neighbors` exactly once over P2 `P_train` under that template's cutoff/neighbor semantics;
3. bind the result into common/execution identity;
4. make candidate materialization consume the common realized architecture without candidate refit;
5. emit `compute_avg_num_neighbors=False` plus the common value to MACE;
6. deliberately emit the canonical P3 one-head target dataset mapping so MACE constructs `target_head` rather than fallback `Default`;
7. ensure EVAL2 reconstruction uses those same bound values;
8. make old-generation materialization/checkpoint reuse fail closed through existing currentness rules.

**Gate B exit:** static/config-level comparison shows one model-construction contract feeds both real TRAIN2 and EVAL2 reconstruction, with no candidate-local model normalization path left.

## Gate C — real pinned-MACE owner-boundary reproducer

Add a bounded CPU integration test that crosses the exact production construction boundary which the current P3A4 fixtures miss.

The mandatory positive reproducer must:

1. create a tiny but real canonical P3 common preparation and two candidate memberships with different N where practical;
2. produce the real canonical P3 candidate materialization/config through production owners;
3. invoke the real `MaceTargetSizeBoundaryTrainer`/qualified `mdstats-mace-train` path or an equivalently exact bounded subprocess path that executes pinned MACE `run_train(...)` through dataset/head loading and `configure_model(...)`;
4. run only enough training to produce one durable TRAIN2 boundary checkpoint/companion/summary;
5. prove the real training model reports head `target_head`, not `Default`;
6. prove real training does not recompute average neighbors from the candidate loader;
7. prove the actual model's interaction `avg_num_neighbors` equals the common-preparation value;
8. call production `authenticate_train2_checkpoint_provider(...)` / `run_target_size_direct_boundary_inference(...)` with **no architecture or provider override**;
9. prove reconstructed architecture digest equals the persisted actual TRAIN2 architecture digest before state application;
10. perform a tiny real CPU forward/evaluation far enough to show the production provider is deployable.

For two candidate N values, it is acceptable to stop before meaningful optimization so long as the real MACE model-construction path runs; assert both models consume the same common `avg_num_neighbors`. The goal is functional/model-construction equivalence, not performance qualification.

This test must reproduce the current defect on the pre-repair implementation: either `Default` vs `target_head`, candidate-local average-neighbor drift, or the exact final architecture-digest rejection.

### Gate C negative evidence

Add focused failures proving:

- changing the canonical/common avg-neighbor value changes/rejects architecture identity as appropriate;
- re-enabling candidate-local `compute_avg_num_neighbors` is not accepted as P3 executable configuration;
- a TRAIN2 model with `Default` head cannot be authenticated against a canonical `target_head` P3 config;
- architecture mismatch remains rejected before checkpoint state can control inference;
- checkpoint/companion state cannot become an alternate architecture source;
- old-generation P3 state produced under the superseded common/model-construction identity is not resumed as current.

## Gate D — affected regression and assembled CLI acceptance

After the last executable edit:

1. re-derive the final affected surface from callers/references and exact diff;
2. run focused common-preparation/model-construction tests;
3. run complete affected P3 candidate/materialization/TRAIN2/EVAL2 regression;
4. run existing real-MACE state/EMA authentication regression;
5. run P4 generation/currentness/restart/cutover regression affected by the new common identity;
6. run P5 scratch/naive/multihead regression if any shared architecture/config serializer changed;
7. run hot-swap/runtime architecture regression if the architecture descriptor changed;
8. run repository import/collection/static/conflict checks required by the project;
9. run a bounded assembled `select-target-size` path through Boundary 1 far enough to prove one real candidate completes TRAIN2 architecture authentication and enters direct EVAL2 rather than failing with the reported architecture mismatch;
10. do not require the complete 16-cell production screen, long GPU qualification, final-production training, or P7 physical qualification for this repair.

**Gate D exit:** the assembled current product crosses the same real boundary that failed in the user's run, and all plausibly affected software regression is green.

---

## 8. Acceptance invariants / anti-shortcuts

Implementation is **No-Pass** if any of the following remains true:

- `authenticate_train2_checkpoint_provider(...)` is weakened or bypassed to tolerate an architecture mismatch;
- EVAL2 obtains model architecture from raw checkpoint state, TRAIN2 companion model objects, saved compiled model files, or logs instead of the canonical candidate configuration;
- `avg_num_neighbors` is still computed separately for each `T_N`;
- the executable P3 config leaves `compute_avg_num_neighbors=True` or lets MACE silently replace the bound common value;
- real P3 TRAIN2 still builds head `Default` while canonical reconstruction uses `target_head`;
- `target_head` is blindly copied from `mace_architecture['heads']` rather than produced from the canonical dataset-head mapping;
- P5's `target_head`/`pt_head` semantics are globally renamed or conflated with P3/MACE fallback defaults;
- a second common-normalization authority is introduced beside `TargetSizeCommonPreparation`/execution identity;
- old generation candidate checkpoints are accepted under the new model-construction identity without a legitimate current-generation transition;
- the only positive test builds a MACE model directly through `build_mace_model_from_configuration(...)` and then authenticates a checkpoint from that same model; that remains proxy evidence and does not exercise the failed owner boundary;
- full production/GPU qualification is substituted for missing focused regression/integration, or vice versa.

---

## 9. Non-goals

This repair does **not** change:

- P1 canonical frame/neutral substrate science;
- P2 candidate sizes, qualification, paired optimizer seeds, fidelity boundaries, evaluation sizes, reducer/ranking, practical-equivalence, or selected-size policy;
- common E0 fitting mathematics except insofar as common-preparation identity now also binds the missing MACE normalization;
- candidate frame weights/objective weights;
- TRAIN2 continuous-rung schedule/LR semantics;
- EVAL2 metric/reduction mathematics;
- P4 CampaignStore ownership architecture;
- P5 CV/final-production scientific method;
- P7 qualification architecture;
- MACE/PyTorch versions;
- TorchScript deprecation-warning policy;
- VASP interrupted-XML/velocity-warning behavior;
- GPU scheduling/resource policy;
- storage/I/O architecture except normal generation invalidation of superseded P3 evidence.

---

## 10. Handoff checklist

Implementation may start when the implementer can answer **yes** to all of the following from current source:

- [ ] The exact pinned MACE pre-`configure_model` mutation census is complete.
- [ ] The common `avg_num_neighbors` owner and membership are unambiguous.
- [ ] The P3 single-head dataset/model namespace is unambiguous.
- [ ] Candidate materialization and EVAL2 reconstruction consume the same seed-neutral MACE construction identity.
- [ ] Old-generation evidence invalidation is handled by existing currentness/generation machinery.
- [ ] The real owner-boundary test exercises MACE `run_train`, not only mdstats' reconstruction helper.
- [ ] P5 head semantics are preserved if shared code is touched.
- [ ] No architecture-authentication fallback or second authority is introduced.

**Final Design verdict: PASS / implementation-ready.**
