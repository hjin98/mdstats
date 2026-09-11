---
kind: implementation-workplan
workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME
protocol_version: 6.2
status: active-ready-for-implementation
plan_review_state: baseline-design-review-complete
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
baseline_commit: 2f56df276d022760588aa5fd3ec7bbe5479ad6ea
reviewed_plan_commit: d6808f966b799dfc618a470960f7693de7c4454b
highest_affected_domain: D3 configuration, stage, persistence/currentness, and accelerator-lifetime architecture -> D4 implementation
upstream_policy_constraint: new single-source replay defaults to source TRUE_DFT labels; foundation pseudo-label replay remains explicit opt-in
serious_challenge: none
related_active_workplan: workplans/active/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_REPAIR_WORKPLAN.md
related_review_reopen: workplans/active/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_FIFTH_REVIEW_REOPEN.md
precedence: This workplan changes only new/single-source replay default resolution and generated configuration, restores accepted replay preparation/currentness ownership, repairs pseudo-label CUDA lifetime, and closes directly dependent documentation/evidence surfaces. It does not supersede the existing TRAIN2 zero-safe-admission/live-memory-safety repair, target-size prepared-generation identity, target-size screen/recommendation/provisional selection, or any non-conflicting CV, production, optimizer, precision, backend, checkpoint, publication, storage, or restart authority.
---

# MLFF replay TRUE_DFT default, pseudo-label preparation, and CUDA lifetime repair

## 0. Baseline design-review disposition

### 0.1 Disposition

The original plan at `d6808f966b799dfc618a470960f7693de7c4454b` was **NO-PASS as an implementation handoff** because several ownership, currentness, compatibility, invalidation, and evidence boundaries were under-specified. This in-place revision closes those design gaps against baseline `2f56df276d022760588aa5fd3ec7bbe5479ad6ea`.

After the corrections below, the **workplan is PASS / frozen for implementation**. No Serious Challenge is active. The defect is primarily a D4 regression against coherent accepted D3 plus one stakeholder-authorized change to the default configuration selection among already-supported replay-label modes.

### 0.2 Material gaps found and closed

1. **The plan overclassified the default change as a D1/D2 redesign.** The baseline already supports both `TRUE_DFT` and `FOUNDATION_PSEUDOLABEL` as distinct scientific method identities, and current architecture describes pseudo-label replay as optional. The user decision changes which existing mode new single-source configurations select by default; it does not change the scientific/numerical semantics inside either mode. This revision therefore places the implementation work at D3 configuration/stage/resource architecture -> D4, under an explicit stakeholder policy constraint. Any required change inside either label mode still routes upstream.
2. **Replay preparation risked being coupled into the target-size immutable prepared generation.** That would be architectural regression. Current P3 target-size screening is one-head/target-only and binds `REPLAY_EXPOSURE_NONE_DIGEST`; replay-label choice is not part of the current target-size screen. This revision explicitly forbids adding replay artifacts, replay label mode, replay prediction policy, or replay currentness to `CurrentTargetSizeAuthorities` or the target-size prepared-generation identity merely to fix P5 replay routing.
3. **The accepted replay stage ownership had not been identified strongly enough.** REPLAY-UNIFY1D already froze: `doctor` validates; `prepare` performs/persists explicit pseudo-label prediction/qualification/materialization; downstream TRAIN2/DATA8 consume those authorities. The current lazy P5 rebuild is a regression from that design. This plan restores the existing owner by rewiring/removal rather than creating a new replay stage or readiness subsystem.
4. **Downstream currentness was under-specified.** A historical `prepare` stage flag alone cannot authorize current replay after configuration/source changes. This revision requires a read/authentication path that validates stored replay authority against the current effective replay policy and authenticated source/policy identities before P5 use, without running foundation inference.
5. **The original “missing prepared state must fail” rule was too broad.** Accepted replay architecture intentionally treats generated ExtXYZ views and similar transports as reconstructable representation caches. Deleting a transport must remain recoverable from authenticated parents without foundation reinference. This revision distinguishes missing scientific/prediction authority from missing disposable representation.
6. **Minimal invalidation and identical-byte relocation were not protected explicitly.** The existing `ReplayInvalidationPlan` already separates source indexing, prediction, qualification, split, and materialization. This revision requires reuse of that semantic matrix and preserves path-free scientific identity/identical-byte relocation rather than invalidating everything under one new prepare digest.
7. **Compatibility for omitted legacy split-file mode was ambiguous.** The new TRUE_DFT default applies to the current single-source interface. Historical split-file behavior must not be silently reinterpreted. New generated single-source configurations should explicitly emit `label_mode = "true_dft"` for reproducibility even though omission resolves to the same value.
8. **The no-cold-build rule was scoped too narrowly to `cross-validate`.** The same P5 replay resolver participates in CV run setup, final production, restart/re-evaluation, and related consumers. No post-selection consumer may become a hidden foundation-prediction owner.
9. **The real-CUDA evidence could have passed through process exit.** A separate `prepare` CLI process releases CUDA on process termination even if the provider was never explicitly retired. This revision requires an in-process real-provider lifetime observation while the Python process remains alive after the production replay-preparation owner returns, plus separate assembled CLI stage-routing evidence.
10. **Removing the process-local replay builder from P5 could accidentally reintroduce O(folds/runs) source scans.** This revision requires one authenticated replay resolution per command/shared method scope where practical, with lightweight reuse by folds/sizes/runs; currentness must not mean reparsing the 12k source for every child.
11. **The active-workplan index is stale.** `workplans/active/README.md` says no MLFF workplan is active even though the P5 repair/reopens and this replay repair are active. The index must be corrected as part of this review commit; it is repository state, not new product machinery.

## 1. Background and governing problem

### 1.1 Terminology

**TRUE_DFT replay** means the replay training head consumes authenticated source density-functional-theory (DFT) energy/force labels, with optional stress according to the existing label-domain contract.

**Foundation pseudo-label replay** means replay training labels are generated from the bound foundation MACE model on the replay geometries. Source truth remains a separate namespace and the replay admissibility monitor remains TRUE_DFT under the current P5 method contract.

A **single-source replay campaign** uses `[paths].replay_set` as its sole new-style external replay corpus. Source inspection, true-label cache, foundation prediction cache, qualification, deterministic split, and MACE-readable train/monitor ExtXYZ files are distinct descendant layers with distinct invalidation rules.

A **scientific replay authority** here means a source/label/prediction/qualification/split identity that can change downstream method or evidence meaning. A **transport representation** means a reconstructable file/view/index/receipt whose deletion may be repaired from authenticated parents without changing that meaning.

**CUDA residency** means accelerator memory retained by live provider/model/graph/framework state or the framework allocator while the Python process remains alive. Function return or zero GPU utilization does not establish resource retirement.

### 1.2 Core problem of concern

The observed post-selection command reaches TRAIN2 admission with approximately 19.9 GiB already resident at 0% GPU utilization. Baseline control-flow reconstruction shows that `_resolve_post_selection_replay_resolution()` can call the construction-oriented `_single_source_replay_context()` before the scheduler's first telemetry sample. For explicit/current pseudo-label replay, a cold/mismatched prediction cache then performs replay-wide foundation inference. `build_replay_foundation_prediction_cache()` can internally construct a CUDA `MaceCalculatorProvider`, while the per-batch prediction adapter reconstructs `StaticMaceInferenceExecutor` repeatedly and does not bind its device correctly. The internally acquired provider is not explicitly retired before the cache builder returns.

The existing TRAIN2 scheduler then correctly sees the actual contaminated aggregate baseline and refuses to admit a nominal 6 GiB training job under the 90% 24-GiB envelope. The scheduler is not the cause and must not be weakened.

### 1.3 High-level architecture that governs the repair

The accepted architecture already supplies the simpler answer:

```text
external replay_set
  -> source authentication / source-index representation
  -> source TRUE_DFT label cache
  -> mode-specific qualification authority
       TRUE_DFT: source truth
       pseudo: foundation prediction cache -> pseudo qualification
  -> one deterministic split
  -> mode-specific training view + TRUE_DFT monitor view
  -> post-selection method/replay lineage
  -> CV / final production consumers
```

Stage ownership is:

```text
doctor
  -> validate configuration/source/runtime prerequisites
  -> no full replay-wide foundation prediction

prepare
  -> prepare/reuse target-size substrate under its existing independent owner
  -> prepare/reuse replay authority/materializations when replay is configured
  -> retire any prepare-owned accelerator provider before returning

select-target-size
  -> target-size work only; replay label choice does not enter the current P3 screen

cross-validate / train-production / P5 recovery consumers
  -> authenticate and consume prepared replay authority
  -> may reconstruct disposable transport from authenticated parents
  -> may not run replay-wide foundation prediction or re-decide replay science
```

The public `prepare` operation may sequence target-size and replay preparation in one invocation, but they remain **semantically separate authorities**. Do not create one combined generation identity merely because one command drives both.

## 2. Outcome and authority

### 2.1 Protected product outcome

For the current single-source interface:

```text
[paths].replay_set absent
    -> no single-source replay

[paths].replay_set present
    + [replay].label_mode omitted
        -> TRUE_DFT replay                         [new default]

    + label_mode = "true_dft"
        -> TRUE_DFT replay                         [explicit equivalent]

    + label_mode = "foundation_pseudolabel"
        -> foundation pseudo-label replay          [explicit opt-in]
```

New `campaign init` output and the canonical example should nevertheless **emit `label_mode = "true_dft"` explicitly** so the scientifically meaningful effective mode is visible in the persisted user configuration. Omission remains a supported convenience/default, not the preferred generated representation.

If a default/explicit TRUE_DFT source lacks required truth for a requested role, fail closed at the source/true-label owner. Never infer that pseudo-label replay was intended.

### 2.2 Existing-mode scientific semantics remain unchanged

This cycle does not alter the meaning of TRUE_DFT or pseudo-label training, the deterministic split algorithm, the target/replay heads, the TRUE_DFT replay monitor role, pseudo qualification, or the training/evaluation method inside either mode. It selects TRUE_DFT as the new single-source default and repairs the software architecture that prepares/consumes those already-defined modes.

Changing effective replay label mode remains a method change for post-selection. CV/final-production evidence from pseudo mode cannot authorize TRUE_DFT mode and vice versa.

### 2.3 Target-size independence

Current target-size screening is target-only. Its common training policy carries `REPLAY_EXPOSURE_NONE_DIGEST`, and the target-size MACE adapter rejects multihead replay. Therefore:

- changing single-source replay label mode does **not** by itself invalidate the target-size immutable prepared generation;
- it does **not** invalidate current target-size screen evidence/recommendations whose method has no replay exposure;
- it does **not** invalidate an operator's provisional selected `N` or its exact target membership merely because downstream replay training policy changed;
- once `cross-validate` freezes a downstream design, P5 method/currentness rules determine whether existing CV/final evidence remains usable under the effective replay mode.

Do not make replay default/currentness a P1-P3 generation input just to gain an existing generation mechanism.

### 2.4 Historical compatibility

The new default applies to the current single-source interface. Preserve supported historical behavior:

- explicit historical single-source `label_mode` keeps its value;
- explicitly supported old `replay.mode = external_true_label` maps to TRUE_DFT;
- explicitly supported old `replay.mode = external_pseudolabel` maps to pseudo;
- legacy split-file replay remains under its historical compatibility resolver, including its historical omitted-mode behavior unless a separately accepted compatibility change says otherwise;
- mixed `replay_set` and legacy replay paths remain rejected;
- conflicting simultaneously declared selectors that imply different label authorities fail before expensive work;
- persisted/frozen evidence is never rewritten under the new default.

## 3. Cycle-scoped D3 decisions and delegated D4 space

### 3.1 Frozen for this cycle

1. **One canonical single-source configuration resolver.** It normalizes omitted/new/legacy selectors to one effective `ReplayLabelMode` before downstream method/replay resolution.
2. **TRUE_DFT is the new single-source default; generated configs state it explicitly.** Pseudo mode requires an explicit opt-in.
3. **No scientific fallback.** Missing TRUE_DFT labels never trigger foundation prediction.
4. **Restore existing replay stage ownership.** `doctor` validates; `prepare` may build; post-selection commands read/authenticate. This is restoration of REPLAY-UNIFY1D, not creation of a second replay subsystem.
5. **Keep replay preparation separate from target-size prepared-generation identity.** Public `prepare` can sequence both owners, but replay records do not become `CurrentTargetSizeAuthorities` components solely for this repair.
6. **Public prepare completion covers configured prerequisites.** When single-source replay is enabled, the `prepare` operation is not complete until the replay preparation owner has either authenticated/reused or constructed/persisted the required replay authority. A replay failure may leave an already-published valid target-size generation intact; retry reuses valid work rather than rolling it back or rebuilding it for ceremony.
7. **Downstream P5 resolution is read/authenticate-only at the scientific/prediction layer.** CV, final production, restart/re-evaluation, and any other current P5 consumer may not trigger foundation replay inference, pseudo requalification because policy changed, or a new scientific split.
8. **Disposable transport remains reconstructable.** A missing/stale generated ExtXYZ view, source index, or equivalent representation may be rebuilt from authenticated current parents if the accepted replay owner already allows it and the operation performs no foundation inference or scientific re-resolution. Representation loss is not automatically a command-to-run-prepare error.
9. **Minimal invalidation is retained.** Source, prediction, qualification, split, and materialization remain independently fingerprinted. Use the semantics of the existing `ReplayInvalidationPlan`; do not replace them with one coarse “replay prepared version” that reruns more work.
10. **Location is not scientific identity.** Identical-byte replay relocation remains reusable through the established source receipt/index rules. Downstream scientific identity stays path-free where current owners already define it that way.
11. **Accelerator acquisition has one explicit operation lifetime.** Any internally acquired pseudo-label MACE provider is retired in exception-safe cleanup before the owning preparation operation returns to its caller. Caller-supplied providers remain caller-owned unless an existing interface explicitly transfers ownership.
12. **OOM/resource-learning state spans the cold prediction operation.** The chosen inference concretization must bind the real device and must not forget a learned safe batch merely because the outer replay stream advanced to the next batch.
13. **No scheduler compensation.** TRAIN2 sees whatever aggregate occupancy remains; zero-safe admission/live-memory protections stay unchanged.
14. **Bound repeated validation work.** Within one post-selection command/shared replay context, expensive source authentication/materialized-view validation is performed once at the appropriate replay owner and reused by sizes/folds/runs where the same authority applies. Currentness may recheck cheap digests/receipts as needed, but removing the lazy builder must not turn a 12k replay parse into per-fold work.
15. **Cache/rebuild disposition is observable at `prepare`.** Explicit pseudo mode distinguishes authenticated cache reuse, cold prediction build, and rebuild due to unusable/stale prediction state without creating a second cache authority.

### 3.2 Delegated D4 concretization

Helpers, private APIs, in-memory context objects, exact log text, counters, and class/object factoring remain replaceable. In particular, D3 does **not** require a newly named replay-prepared record, a specific wrapper, or a specific number of Python objects.

Preferred minimum-complexity concretization reuses and, where necessary, separates the existing owners:

- `single_source_replay_config_from_campaign()` for configuration normalization;
- existing source receipt/index, true-label cache, prediction cache, qualification, split, and view records;
- the existing campaign `prepare` control flow, altered to invoke replay preparation before declaring the configured operation complete;
- the existing replay persistence records rather than a second readiness database;
- `PostSelectionReplayResolution` as a transport adapter populated from authenticated replay records, not from the construction path;
- existing `MaceCalculatorProvider.close()` / accelerator-residency cleanup;
- existing `StaticMaceInferenceExecutor` or an equivalent reduced use of it that preserves device correctness and operation-scoped OOM learning.

A single operation-scoped `StaticMaceInferenceExecutor` over the cold cache build is the currently preferred D4 simplification because it already provides bounded prediction/OOM machinery, but the invariant is **one coherent resource-learning lifetime**, not the class name itself.

### 3.3 Required simplification

Prefer rewiring/removal over compensation:

- split the current construction-oriented single-source replay path into preparation versus downstream authenticated consumption, or otherwise make those two modes unambiguous;
- remove production P5 call paths from the foundation-prediction builder;
- remove per-outer-batch recreation of device/OOM state;
- close the internally acquired provider at the existing owner;
- reuse existing replay records/invalidation logic rather than inventing a combined prepare-generation authority;
- do not add scheduler-entry cache flushes, fallback builders, replay-ready flags, provider registries, or retry databases around the defect.

## 4. Material implementation obligations

### R1 - canonical single-source default and compatibility normalization

Change the canonical single-source resolver so omission resolves to TRUE_DFT while supported explicit/legacy selectors retain their meanings.

Required behavior:

- `replay_set` absent -> no single-source replay;
- `replay_set` + omitted selector -> TRUE_DFT;
- explicit `label_mode=true_dft` -> TRUE_DFT;
- explicit `label_mode=foundation_pseudolabel` -> pseudo;
- supported explicit historical `mode` values normalize centrally;
- conflicting new/legacy selectors fail before source/model work;
- legacy split-file omitted-mode behavior is unchanged by this single-source default change;
- downstream method/policy code consumes the normalized result rather than maintaining its own single-source default.

`campaign init` and `campaign.toml.example` must emit `label_mode = "true_dft"`; pseudo is documented as an explicit alternative, not the generated default.

**Evidence:** real resolver tests for omitted/explicit/conflict/legacy/path cases; generated-init/example checks; canonical post-selection replay-policy digest checks showing default and explicit TRUE_DFT are method-equivalent while explicit pseudo differs.

### R2 - TRUE_DFT path has zero pseudo-label foundation inference

For a valid single-source TRUE_DFT replay corpus, replay preparation authenticates the source, builds/reuses source index/true-label cache/split/required true-label views, and records TRUE_DFT method lineage without requiring pseudo prediction state.

No replay foundation provider/prediction cache/qualification is constructed solely for TRUE_DFT training. Missing required truth fails closed with no pseudo fallback.

**Real-owner evidence:** run the production single-source resolver/preparation path from a real campaign configuration with omitted `label_mode`; place a liveness spy/failpoint only below the foundation prediction constructor and prove it does not fire. Prove the same hook *does* fire on an explicit pseudo cold path so the negative evidence cannot pass because the pseudo route was globally disconnected.

### R3 - restore prepare-owned replay preparation without polluting the target-size generation

Alter the current public prepare control flow so it sequences its existing target-size work and the existing replay preparation owner when replay is configured.

Requirements:

- replay configuration conflicts/defaults are resolved before launching expensive pseudo work;
- target-size substrate publication/currentness remains exactly under the target-size prepared-generation owner;
- replay authorities/materializations remain under replay records/receipts/invalidation owners, not target-size generation components;
- TRUE_DFT replay preparation uses no foundation inference;
- explicit pseudo preparation may build/reuse the prediction cache, qualify, split, and materialize its pseudo training view plus required TRUE_DFT monitor view;
- required replay records are persisted before public `prepare` is marked COMPLETE;
- if replay preparation fails after target-size generation has successfully published, do not destructively roll back the valid target-size generation; mark the operation failure truthfully and let retry reuse it;
- retry/idempotence uses authenticated existing target-size and replay state and does not redo foundation prediction on a valid cache;
- do not resurrect a retired generic restart receipt or add a second combined generation solely to synchronize the two preparations.

**Evidence:** `doctor -> prepare` command-owner tests for no replay, TRUE_DFT, pseudo cache hit, pseudo cold build, pseudo failure after target-size publication, and retry. Prove a replay-only policy edit does not change the target-size prepared-generation identity or discard valid screen/provisional-selection evidence.

### R4 - make every post-selection replay consumer scientific-read-only

The current P5 replay resolution must obtain replay training/monitor artifacts and lineage from authenticated prepared replay records/current parents, not by invoking the construction path.

This applies to all production P5 consumers sharing the resolver: cross-validation setup, final production, restart/continuation, representative re-evaluation/recovery, and future callers of the same current owner.

At use time, authenticate enough current semantics to reject stale science before TRAIN2/EVAL2:

- effective single-source replay label mode;
- split ratio/seed and current split authority;
- source SHA/content/true-label identity as governed by current replay owners;
- explicit pseudo prediction policy/cache and qualification identities when pseudo mode applies;
- required train/TRUE_DFT monitor artifact lineage;
- current method replay-policy identity.

Do not use `ReplaySingleSourceConfig.content_digest` as a coarse scientific equality test if doing so would make a locator change scientific; its current record contains a path. Preserve the established path-free method/replay identities and identical-byte relocation behavior.

If current configuration/source/prediction/qualification semantics require scientific reconstruction or foundation inference, fail before TRAIN2 with guidance to run `prepare`. Do not lazily repair it inside P5.

If only a disposable materialized view/index/receipt is absent or stale while its authoritative parents remain current, representation-only reconstruction is allowed under the existing replay owner. It must not call the foundation model, requalify under a changed policy, resplit under a changed scientific parent, or change method identity.

Resolve/authenticate shared replay authority once per command/shared method scope where practical, then reuse that immutable resolution across selected sizes/folds/runs. Do not replace hidden GPU work with repeated whole-corpus CPU/I/O scans.

**Evidence:** production P5 resolver/integration tests for CV, final production, restart/re-evaluation; structural/call-graph negative assertion that no P5 production route can call the cold foundation prediction builder; source/view mutation cases; an execution counter proving the 12k-source parser/prediction builder is not invoked once per fold/run.

### R5 - repair the internally owned pseudo-label provider lifetime

On a cold pseudo prediction-cache build:

- distinguish internally constructed provider from caller-supplied provider;
- internally constructed provider is retired through the existing lifecycle primitive on success and every failure path after acquisition;
- caller-supplied provider remains caller-owned unless ownership transfer is already explicit;
- no valid cache manifest is published before all required cache files/identities are durable and valid;
- cleanup covers provider-validation failure, source iteration, prediction/OOM, shard/audit write, publication/rename, and other post-acquisition exceptions;
- returned cache state contains no live provider/executor/model reference.

Do not add a second provider registry or scheduler cleanup hook.

**Evidence:** ownership-sensitive fake provider plus bounded failure injection at several post-acquisition points; caller-owned non-close test; structural review of all exits from the acquisition boundary.

### R6 - retain device-correct bounded OOM learning for the whole cold build

Current per-outer-batch executor creation resets learned safe batch state and defaults the executor device to CPU despite a CUDA-backed provider.

Required end state:

- prediction execution is bound to the effective replay prediction device;
- synchronization/OOM/cache handling follows the actual CUDA device when applicable;
- a learned safe prediction batch persists across the whole cold cache-build operation;
- later outer batches do not retry a size already shown unsafe solely because a helper object was recreated;
- ordering, source membership, prediction identities, audit values, and shard logical semantics are unchanged.

Preferred implementation: construct/reuse one existing static executor for the operation and close it at the same owner boundary. Equivalent simpler factoring is allowed.

**Evidence:** deterministic OOM/backoff provider showing the first oversized batch learns a safe size and later outer batches start from that learned bound; device-binding assertion; output/order equivalence with a non-OOM reference.

### R7 - preserve the existing minimal replay invalidation matrix

The repair must use/preserve the semantics of `ReplayInvalidationPlan` rather than treating replay as one coarse prepared blob.

At minimum preserve:

- identical source bytes relocated -> no scientific invalidation/reparse solely because path changed;
- source byte change -> source revalidation/reindex as currently governed;
- source true-label change in TRUE_DFT mode -> only truth-dependent qualification/split/materializations and downstream method lineage invalidate as governed;
- source true-label change in pseudo mode does not rerun foundation prediction when geometry/prediction policy are unchanged, though TRUE_DFT monitor/label-dependent descendants update as governed;
- pseudo foundation checkpoint/head/inference-policy change -> prediction cache invalidates and downstream pseudo qualification/split/view/method lineage follows;
- pseudo qualification-threshold change -> requalify cached prediction/audit evidence without foundation reinference;
- split ratio/seed change -> resplit/rematerialize required roles without foundation reinference;
- deletion of materialized views -> reconstruct from authenticated parent caches without reinference;
- prediction cache corruption/missing state -> cold rebuild only under `prepare`, never P5.

If a baseline invalidation rule is discovered to be scientifically wrong, route that finding to its owner; do not silently “simplify” by invalidating everything.

**Evidence:** reuse/extend invalidation tests plus assembled prepare/P5 cases for threshold edit, split edit, identical relocation, view deletion, prediction-cache deletion/corruption, and source-label mutation.

### R8 - expose expensive replay cache disposition at the owning boundary

At `prepare`, explicit pseudo mode must visibly distinguish:

- authenticated prediction-cache hit;
- cold prediction build because no current cache exists;
- rebuild because stored prediction state is invalid/incompatible/corrupt.

The output must identify effective replay mode and owning stage sufficiently to explain a long/high-VRAM operation. It must not create a new durable cache-status database. Current invalidation/replay records remain authority; diagnostics report them.

P5 output should describe consumption/authentication of prepared replay state, not suggest it is generating pseudo labels.

### R9 - close the real CUDA lifetime and assembled stage boundary on target hardware

Fake-provider evidence cannot close the physical lifetime claim.

#### R9-A: in-process real-provider lifetime proof

Use the production replay prediction/preparation owner with real MACE/CUDA in a Python process that remains alive after the owner returns. Force a cold pseudo prediction path using only reconstructable replay cache state.

Capture as available:

- NVML aggregate/process occupancy;
- `torch.cuda.memory_allocated()`;
- `torch.cuda.memory_reserved()`;
- `torch.cuda.max_memory_allocated()`;
- `torch.cuda.max_memory_reserved()`;
- provider/executor acquisition/retirement boundary evidence.

Required signature:

```text
clean baseline
  -> provider/model residency
  -> bounded replay inference high-water
  -> final prediction complete
  -> explicit owner cleanup returns
  -> process remains alive
  -> allocated/reserved/NVML occupancy falls to ordinary context-scale residency
```

A shell-level `prepare` process that exits immediately after inference is **not sufficient** to prove explicit provider retirement, because process exit would release CUDA even if the owner leaked it.

#### R9-B: assembled command/stage proof

On the same final candidate:

**Case TRUE_DFT default**
- use a representative valid-labeled `replay_set` with omitted `label_mode`;
- run normal `prepare`;
- prove zero foundation pseudo-label inference during replay preparation;
- begin `cross-validate` and establish no replay-foundation model-scale pre-TRAIN2 residue/prediction pass.

**Case explicit pseudo cold cache**
- remove only reconstructable pseudo prediction/materialization state needed to force the cold path;
- run `prepare` and observe the one legitimate replay foundation prediction workload;
- after prepare, run `cross-validate` and prove no replay-wide foundation prediction occurs there;
- verify the scheduler now sees only real current occupancy, and no owned orphan GPU process/provider remains after terminal cleanup/interruption.

The pseudo prediction peak itself need not be tiny. The governed claim is bounded resource use, correct stage ownership, and retirement before downstream training. If correct pseudo preparation intrinsically cannot fit the supported prepare-time device/resource envelope, route that separately rather than weakening this lifetime contract.

Production target-host evidence is required for PASS because VRAM lifetime is itself the claim.

## 5. Configuration, identity, persistence, and currentness invariants

### 5.1 Configuration identity

Effective replay mode is scientifically meaningful and must participate in post-selection method identity. Generated configuration makes the effective default explicit; runtime omission resolves identically.

Do not let a compatibility alias create a second downstream representation. Normalize first, validate conflict, then persist/derive identities from the canonical mode.

### 5.2 Path and source identity

Configured `replay_set` path is a locator. The replay source authority binds authenticated source bytes/content/geometry/label identities. Preserve the current ability to rebind an identical source at a different path without changing scientific replay identity or repeating foundation inference.

### 5.3 Prepared replay persistence

Reuse existing campaign replay records/receipts to make preparation restartable. The required semantic state differs by mode:

```text
TRUE_DFT:
  normalized single-source config semantics
  + authenticated replay source / true-label cache
  + deterministic split
  + required true-label role/view lineage

FOUNDATION_PSEUDOLABEL:
  above source/true-label basis
  + foundation prediction policy/cache
  + pseudo qualification
  + split bound to qualification
  + pseudo training-view lineage
  + independent TRUE_DFT monitor-view lineage
```

A process-local `_UNIFIED_REPLAY_CONTEXT_CACHE` may remain an optimization inside a bounded construction/consumption scope, but it is not currentness authority and must not be the only reason later commands can reuse replay state.

### 5.4 Public prepare state

`StageState.COMPLETE` for `prepare` means all preparation prerequisites required by the configured campaign have completed/authenticated for that invocation. It must not mean “target-size generation succeeded, replay preparation silently deferred to P5.”

However, failure of the replay sub-operation does not revoke an independently valid immutable target-size generation. Durable child owners keep their truthful state; public operation status reports incomplete/failed orchestration and retry resumes/reuses current pieces.

## 6. Evidence applicability and dependency impact

### 6.1 Evidence that remains applicable

Unless executable edits reach them materially:

- target-size P1/P2/common prepared-generation evidence remains applicable because replay exposure is NONE there;
- target-size screen/reducer evidence remains applicable to its target-only method and target-side ranking rules;
- manual provisional `N` selection remains a valid target-data choice;
- TRAIN2 zero-safe admission/live-memory controller unit evidence remains applicable to genuine aggregate occupancy;
- explicit historical pseudo-mode evidence remains truthful evidence of pseudo mode, not evidence of the new TRUE_DFT default;
- replay source/split/cache tests whose propositions are mode-independent remain reusable after impact review.

### 6.2 Evidence requiring review/rerun

- generated/default configuration tests that expected pseudo by default;
- any test whose scientific proposition depended on omitted single-source mode resolving to pseudo;
- replay prepare/restart/currentness integration that assumed `_single_source_replay_context()` could construct on demand from P5;
- assembled P5/CV target-host evidence whose pre-TRAIN2 path included replay resolution;
- real CUDA replay pseudo-label qualification that did not prove provider retirement while process remained alive;
- documentation/generated derivatives stating pseudo labels are the default or that replay prediction can occur in P5.

### 6.3 Dependency graph

```text
single-source default policy
  -> canonical replay config normalization
  -> post-selection replay-policy identity
  -> mode-specific replay prepared authority
  -> replay train/TRUE_DFT monitor lineage
  -> P5 method identity / CV plan / final-production descendants

replay source content + split policy
  -> source/label cache + split
  -> disposable views
  -> P5 replay lineage

explicit pseudo mode
  -> foundation prediction policy
  -> prediction cache
  -> pseudo qualification
  -> split + pseudo train view
  -> P5 replay lineage

provider acquisition
  -> operation-scoped inference/OOM learning
  -> prediction cache publication
  -> explicit provider retirement
  -> clean downstream accelerator baseline
  -> unchanged TRAIN2 admission controller

current target-size prepared generation
  X-> replay label mode    [no dependency in current target-only P3 screen]
```

The final implementation review must preserve the negative dependency in the last line.

## 7. Affected implementation surface

Initial required inspection includes:

- `mdstats/training_data/replay.py` - canonical single-source config/source/true-label identities;
- `mdstats/training_data/replay_invalidation.py` - minimal invalidation policy;
- `mdstats/training_data/replay_pseudolabel.py` - pseudo prediction cache/provider/executor lifetime;
- `mdstats/training_data/model_features.py` - existing provider/executor lifecycle primitives, only if required to express correct existing ownership;
- `mdstats/training_data/_campaign_cli_core.py` - current construction/persistence helper, doctor messaging, config generation, process-local context cache;
- `mdstats/training_data/campaign_target_size_runtime.py` - public `prepare` orchestration only; target-size scientific generation must remain replay-independent;
- `mdstats/training_data/campaign_post_selection_runtime.py` - replace construction-capable replay resolution with authenticated consumption across CV/final/recovery paths;
- `mdstats/training_data/post_selection_identity.py` and related method/lineage owners - verify canonical mode and path-free identity/currentness;
- campaign store/replay record APIs only as needed to reuse existing persisted replay records; do not add a parallel readiness owner without proof it is unavoidable;
- storage/retention owners insofar as replay view/cache reconstruction and protected external `replay_set` are affected;
- `campaign.toml.example`, `campaign init` output, README, relevant Architecture Manual chapter sources/specifications, replay architecture history/dependency documentation;
- replay-unification, post-selection, multi-size, restart/currentness, storage/invalidation, P5, and resource-lifetime tests whose propositions are affected.

Re-derive the final surface from actual edits before closure. File count is not authority scope.

## 8. Acceptance matrix

| Scenario | Required outcome |
|---|---|
| no `replay_set` | no new replay work or state |
| single-source, omitted `label_mode` | TRUE_DFT effective mode |
| generated new campaign | explicit `label_mode = "true_dft"` |
| explicit `true_dft` | method-equivalent to omitted default |
| explicit `foundation_pseudolabel` | pseudo mode; foundation prediction permitted only during prepare cold build |
| supported legacy explicit true/pseudo selector | historical meaning retained |
| legacy split-file omitted mode | historical compatibility behavior retained |
| conflicting selectors | reject before expensive work |
| TRUE_DFT missing required source labels | fail closed; zero pseudo fallback |
| replay-only mode edit after target-size prepare/screen | target-size generation/screen remains current; P5 method descendants re-resolve/invalidate as required |
| pseudo prediction cache hit | prepare reuses; zero model inference |
| pseudo qualification-threshold edit | requalify cached audit/prediction state; zero model inference |
| split ratio/seed edit | resplit/rematerialize; zero model inference |
| identical-byte source relocation | preserve scientific identity/reuse; no foundation reinference solely for path |
| deleted train/monitor ExtXYZ view with current parents | representation-only rematerialization allowed; no foundation inference |
| missing/corrupt pseudo prediction cache | rebuild only in prepare |
| P5 sees mode/source/policy change requiring scientific rebuild | fail currentness before TRAIN2; direct user to prepare |
| CV/final/recovery after valid prepare | authenticate/reuse; no replay-wide foundation inference |
| internally created provider success | explicitly retired before owner returns |
| internally created provider failure | explicitly retired; no valid partial publication |
| caller-supplied provider | remains caller-owned |
| first pseudo batch OOM learns smaller batch | later outer batches retain safe bound |
| high genuine external VRAM occupancy | unchanged TRAIN2 zero-safe admission blocks correctly |
| replay preparation fails after target-size generation publish | target-size generation remains valid; public prepare fails/retries replay without rollback |

## 9. Required validation

### 9.1 Stage-local evidence

**Stage A - configuration and scientific-route selection**
- R1 resolver/generated-config/legacy/conflict tests;
- R2 TRUE_DFT no-pseudo-provider real-owner test;
- method-policy identity checks.

**Stage B - prepare/currentness rewiring**
- R3 command-owner prepare cases;
- R4 read-only P5 cases across CV/final/recovery;
- structural negative call-path checks;
- target-size non-impact/idempotence tests;
- representation-only rematerialization tests.

**Stage C - pseudo resource lifetime and invalidation**
- R5 lifecycle/failure injection;
- R6 device/OOM-learning persistence;
- R7 invalidation/relocation matrix;
- R8 cache disposition observability.

Each coherent executable stage runs focused plus affected stage-local regression before dependent work continues.

### 9.2 Final assembled evidence

Before review readiness:

- re-derive the complete affected surface from the final candidate;
- run all replay-unification and affected post-selection/currentness/restart/storage tests;
- run affected target-size tests proving replay changes did not enter target-size identity or screen behavior;
- run affected TRAIN2 scheduler tests proving no weakening/compensation;
- run repository-required lint/type/build/package checks applicable to the changed surface;
- regenerate required documentation/package derivatives through repository owners; unavailable required tooling remains blocking rather than silently skipped;
- run R9-A real in-process CUDA lifetime proof;
- run R9-B assembled TRUE_DFT and pseudo command/stage proofs;
- reassess/rerun only the materially affected existing P5 target-host evidence on the final candidate.

### 9.3 Forbidden proxy proofs

The following cannot close their respective claims:

- helper-only resolver tests for production command routing;
- preconstructed `ReplaySingleSourceConfig` for omitted-value default resolution;
- a fake provider for real CUDA allocator/provider retirement;
- process exit as proof that the provider was explicitly closed;
- a seeded in-memory replay context for restart/persistence/currentness;
- a materialized-view file merely existing as proof its current scientific parents authenticate;
- a target-size generation digest changing after replay-mode edit as “proof of safety”; that would itself violate the required independence.

## 10. Documentation, authority, and history impact

### 10.1 D3 Architecture Manual

Reconcile current chapter sources to state the already-accepted replay ownership explicitly where needed:

- public `prepare` coordinates replay preparation as well as target-size preparation when replay is configured, while the two authorities remain separate;
- `doctor` does not perform replay-wide foundation prediction;
- post-selection commands consume authenticated replay authority and do not cold-build pseudo science;
- disposable replay transports may be reconstructed from current parents without foundation inference;
- prepare-owned accelerator providers terminate at their final preparation consumer;
- single-source default is TRUE_DFT and pseudo is explicit opt-in at the configuration boundary.

Because the stage/lifetime portion restores REPLAY-UNIFY1D/Part VI architecture rather than inventing a new topology, do not mint a new architectural subsystem. Whether an Architecture Manual revision number/history note is needed follows the repository's current authority-publication convention, not the number of implementation edits.

### 10.2 D1/D2

No method-internal D1/D2 change is authorized. Current TRUE_DFT and pseudo semantics remain as defined. If implementation reveals that TRUE_DFT replay cannot satisfy the accepted multi-head label-domain/E0/objective contract without numerical/scientific alteration, stop and route the earliest affected D1/D2 owner.

### 10.3 Configuration/specification

The current single-source omitted-value behavior and generated config change. Document one canonical semantic definition and keep init/example/API/config behavior synchronized. Do not silently change legacy split-file compatibility defaults.

### 10.4 Semantic evolution

Record a concise evolution entry because two lessons are likely to prevent recurrence:

- new single-source campaigns select source truth by default while keeping pseudo replay explicit and supported;
- a later target-size orchestration refactor regressed the already-frozen replay prepare/P5 ownership, allowing expensive pseudo inference and provider residency to leak into the pre-TRAIN2 phase; the repair restores owner boundaries rather than compensating in the scheduler.

History explains why; current configuration/architecture owners remain normative.

### 10.5 Active workplan index

Update `workplans/active/README.md` to stop claiming there are no active MLFF plans. It should identify the current P5 CUDA work and this replay repair as active coordination artifacts and retain the warning that workplans themselves are non-normative.

## 11. Relationship to the existing P5 CUDA repair

The existing P5 TRAIN2 plan remains independently binding. This replay work changes the command path that presents the scheduler with its starting occupancy but does not change scheduler semantics.

After this repair:

- P5 unit/controller evidence for zero-safe admission, live aggregate memory safety, missing telemetry, cancellation/reaping, and fail-before-EVAL2 remains admissible if its executable owners were not changed;
- prior target-host evidence proving a clean single TRAIN2 job fits the 24-GiB device remains relevant to method/device compatibility;
- assembled P5 evidence that traversed the old pre-CV replay resolution is review-required and must be rerun/reassessed on the final candidate;
- a genuine high external/process baseline must still block training rather than being reclassified as a replay bug.

Do not merge the two workplans into one scheduler/replay mechanism merely because the observed failure crosses their boundary.

## 12. Reopen / Challenge triggers

### D4-local blockers

Keep within this workplan: additional lazy P5 construction call sites, omitted provider exits, stale tests, missing view/currentness validation, configuration alias drift, excessive repeated source scans, or documentation/generated-artifact mismatch under the frozen design.

### D3 reopen

Reopen D3 only if evidence shows, for example, that:

- prepare-owned replay authority cannot be restored without a genuinely new durable state/interface;
- replay and target-size preparation must share one scientific generation for an upstream reason currently absent;
- a downstream P5 consumer materially requires live foundation-provider ownership beyond prepare;
- the current replay invalidation decomposition is structurally incapable of preserving currentness while supporting storage/restart.

### D1/D2 route

Route upstream if source TRUE_DFT default exposes a real method-formulation/numerical incompatibility, if true/pseudo modes need different statistical roles not represented by current identities, or if pseudo prediction numerical settings must change for correctness rather than resource realization.

### Mandatory simplification trigger

Stop additive implementation if the proposed fix begins accumulating a second replay-ready record, combined target/replay generation, P5 fallback builder, scheduler cleanup hook, provider registry, or per-command reconciliation wrapper. Re-derive the flow around the existing resolver, replay records/invalidation owner, prepare control path, and provider lifecycle first.

### Serious Challenge

Raise `SERIOUS CHALLENGE` only if current accepted authorities become materially contradictory or unrealizable. No such contradiction is established by this review: historical REPLAY-UNIFY1D, current method identity, current target-size replay-none design, and current provider-lifetime doctrine can be satisfied simultaneously.

## 13. Final PASS criteria and handoff

The implementation is review-ready only when all are true:

1. new single-source omission resolves to TRUE_DFT and generated configs state TRUE_DFT explicitly;
2. explicit pseudo mode and all supported historical explicit/legacy meanings remain compatible;
3. default/explicit TRUE_DFT performs no replay foundation prediction and never falls back to pseudo;
4. public `prepare` restores the existing replay preparation owner while keeping replay state outside the target-size prepared-generation identity;
5. replay-only changes do not retire current target-size substrate/screen/provisional N solely because replay is not part of the current screen;
6. all P5 consumers obtain replay science through authenticated read/currentness paths and cannot cold-build foundation predictions;
7. missing disposable views remain reconstructable from authenticated parents without reinference;
8. mode/source/prediction/qualification/split changes obey the existing minimal invalidation matrix and identical-byte relocation remains non-scientific;
9. internally acquired pseudo providers are explicitly retired on every terminal path before the owner returns;
10. device-correct OOM-learning state persists across the entire cold prediction operation;
11. repeated P5 folds/sizes/runs do not repeatedly parse/reconstruct the same replay authority;
12. pseudo cache hit/cold/rebuild is observable at prepare without a second cache authority;
13. post-selection replay/method lineage binds the effective mode and current semantic parents without making locator path scientific;
14. TRAIN2 zero-safe/live-memory behavior remains unchanged and continues to reject genuine unsafe occupancy;
15. current docs/examples/specifications and required generated derivatives agree with the corrected default and restored stage/lifetime architecture;
16. active-workplan repository state is truthful;
17. R9-A proves explicit real CUDA owner retirement while the process remains alive;
18. R9-B proves assembled TRUE_DFT and explicit-pseudo stage routing and clean pre-TRAIN2 ownership;
19. final affected regression and materially dependent P5 evidence are reconciled on the final candidate;
20. every required unavailable/unexecuted check or unresolved impact remains explicitly blocking rather than inferred green.

Independent Software Design Review must reconstruct the actual final configuration, prepare, persistence/currentness, invalidation, post-selection, and CUDA-lifetime behavior from the assembled candidate. Literal compliance is insufficient if implementation still permits hidden foundation inference downstream, duplicates replay/target-size authority, weakens minimal invalidation/storage reconstruction, changes legacy scientific meaning, or relies on process exit/scheduler cache flushing to conceal an unretired provider.
