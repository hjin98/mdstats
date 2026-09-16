---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 13
protocol_version: 6.3.0
status: active
created_date: 2026-09-16
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
parent_plan_revisions: [12]
reviewed_assembled_candidate: c6fbe03c92f23a79123031922f338966e9c76c6b
reviewed_r12_implementation_commit: 9c41f44be32dd0e4f3869e6e48be4e85b9effce9
highest_affected_domain: D4
challenge_state: D4_NO_PASS_RESOURCE_AND_EVIDENCE_CLOSURE_REQUIRED
upstream_authority_state: D1_D2_D3_ACCEPTED_UNCHANGED
---

# MLFF `pi_train` restoration — Revision 13 resource-budget and HAS closure

## 0. Independent re-review verdict

Fresh independent review of assembled candidate `c6fbe03c92f23a79123031922f338966e9c76c6b` against Revision 12 and the accepted D1/D2/D3 authority is **NO-PASS**, but the remaining scope is narrow.

Revision 12 **does close** the material REPAIR2 performance defect and restart-cost question:

- the R12 batched REPAIR2 realization preserves the accepted D2 §9 decision sequence and reuses the existing MVIDX/native-row execution substrate;
- bounded scalar/batched/native equivalence evidence is appropriately targeted;
- representative current-scale REPAIR2 falls from about 6,156 s to 99 s while the complete scientific build identity remains identical to the R11-correct baseline;
- post-`N_max` REPAIR2 replay falls from about 6,610 s to 100 s and is no longer the dominant resumed-prepare cost;
- no new repair persistence/currentness owner was introduced.

The six R11 correctness/ownership closures and the R12 B12-1/B12-2 closures SHALL remain frozen unless new contradictory evidence appears.

Two closure defects remain:

1. B12-3 was declared closed even though the production target-order path carries **no RAM admission scope** and the recorded before/after RSS delta is **not a stage peak**. The R12 evidence therefore cannot falsify a transient over-budget COVREF peak and cannot establish behavior against the campaign RAM budget it cites.
2. B12-4 records useful PEM dispositions, but not in the canonical Protocol 6.3 HAS interface. The durable handoff uses noncanonical `applied/rejected/review-required` labels instead of the exact `pem_basis` + `has` schema and `APPLICABLE/NOT_APPLICABLE/REVIEW_REQUIRED` dispositions required by Protocol 6.3 workflow authority.

Neither defect requires a D1/D2/D3 change. The existing D4 interfaces already contain the required resource-scope route and the HAS repair is representation/evidence only.

## 1. Protected accepted state

Preserve without redesign:

- one exact `P_train`, one complete `pi_train`, exact nested `T_N`;
- sole `TargetCoverageReference`, one canonical obligation authority, one shared FEAS1/NEIGHBOR1 construction, MVIDX as representation;
- MVSEL2/REPAIR2 as the single order owner and independent MVQUAL;
- prepare-owned construction/publication and prepared-generation/CampaignStore completed-currentness ownership;
- R11 immutable create-or-verify publication, same-build single-flight preparation, frozen structural-family completeness, documentation delegation and downstream no-rebuild routing;
- R12 `_StateBatch` exact batched REPAIR2 execution and the one metered selector/repair execution-width decision;
- no new repair cache/checkpoint/currentness owner;
- final production-scale GPU qualification remains deferred to the final complete release package on the stakeholder machine.

## 2. Blocking finding B13-1 — B12-3 RAM closure is not actually established

### 2.1 Production routing omits the campaign RAM budget

`campaign_target_size_runtime._build_current_target_training_order()` resolves the campaign `SystemResourceSnapshot` through `_performance_resources(cfg)` and passes that object to the universal structural provider. But the call to `prepare_target_training_order()` passes only:

```text
workers = resources.cpu_threads_budget
```

and does **not** pass `resource_scope`.

Consequently the target-order preparation owner receives `resource_scope=None`. The R12 representative evidence confirms the concrete consequence:

```text
StageResourceScope.ram_budget_bytes = None
queue_memory_budget_bytes = None
```

for COVREF-PAR1, even though the same campaign resource snapshot reports a finite RAM planning budget.

This is a D4 routing omission, not a reason to invent resource machinery. `prepare_target_training_order()` already accepts `resource_scope`; COVREF, MVIDX, REPAIR2 and MVQUAL already accept/inherit it. The missing edge is from the existing campaign resource owner into that existing interface.

### 2.2 The R12 measurement did not measure stage peak RSS

R12 records current process RSS immediately before COVREF and current process RSS after COVREF releases its execution state, then calls the difference `stage_incremental_rss_bytes`. The observed value is about -200 MiB.

That quantity cannot establish peak stage demand. A stage could transiently allocate tens of GiB and free them before the post-stage sample while producing the same negative end-minus-start value. Queue-accounted task memory (~132 MiB) also does not include every resident object in the process and cannot substitute for a process-RSS peak measurement.

Revision 12 explicitly required `TargetCoverageReference` **peak process RSS and incremental RSS above the stage baseline** plus its governing `StageResourceScope.ram_budget_bytes`. Neither condition was actually satisfied:

- the peak was not observed;
- the governing stage RAM budget was absent.

Therefore R12 gate 6 remains open irrespective of the fact that the representative process stayed inside physical machine capacity.

### 2.3 Required repair — rewire, do not add a resource subsystem

At `campaign_target_size_runtime._build_current_target_training_order()`:

1. keep `_performance_resources(cfg)` as the sole campaign resource snapshot owner;
2. construct one execution-only root target-order `StageResourceScope` using the existing `build_stage_resource_scope()` helper and the already-resolved `resources` object;
3. carry the existing CPU budget and **the existing `resources.ram_budget_bytes`** into that scope;
4. pass that scope to `prepare_target_training_order(..., resource_scope=target_order_scope)`;
5. keep `workers=max(1, resources.cpu_threads_budget)` as the work-width ceiling; do not create another worker policy;
6. let existing COVREF/MVIDX/MVQUAL nested scopes inherit the RAM budget through their current `resource_scope` plumbing; let R12 REPAIR2 continue to use the preflight-selected execution width capped by the same root CPU budget;
7. do not add a second RAM manager, a new admission database, a target-order-specific memory fraction, or a silent increase of the campaign RAM fraction.

The structural-provider call already receives `resources` directly and remains under its existing owner; do not duplicate or nest a second structural-provider resource policy merely because target-order preparation now receives its own existing scope argument.

### 2.4 Focused falsification

Add/extend real-owner or runtime-owner tests that prove:

- `_build_current_target_training_order()` passes a non-`None` `resource_scope` to `prepare_target_training_order()`;
- that scope binds the same `cpu_threads_available`, `cpu_threads_budget` and `ram_budget_bytes` as `_performance_resources(cfg)`;
- COVREF-PAR1 receives a finite inherited RAM budget in a finite-budget fixture;
- MVIDX nested execution inherits the same budget rather than replacing it with `None`;
- serial/parallel COVREF content digests remain identical;
- R12 REPAIR2 width selection and exact repair-plan behavior remain unchanged when the RAM budget is non-constraining;
- a deliberately small finite budget reaches the deterministic queue/admission path through the production routing. The test need only prove routing/admission ownership; do not use actual host exhaustion.

### 2.5 Required representative RAM evidence

On the same representative LTA substrate, capture:

1. process RSS immediately before COVREF;
2. **actual peak process RSS observed while COVREF is executing**;
3. incremental peak `peak_rss - entry_rss`;
4. process RSS after COVREF release;
5. finite `StageResourceScope.ram_budget_bytes` inherited from the campaign resource snapshot;
6. deterministic-queue peak accounted memory, memory budget and backpressure counts;
7. COVREF worker width/block size;
8. whole-prepare peak RSS and wall time for context.

Do not add permanent product machinery solely to obtain item 2 if an external/qualification harness can sample `/proc/<pid>` or equivalent during the stage. Evidence instrumentation is not scientific state and must not enter build identity.

Acceptance requires the finite campaign budget to reach the stage and the measured current-scale execution to remain inside the governing resource envelope. If finite-budget admission changes COVREF/MVIDX execution width, that is execution-only; record it and prove the final build/repair/order/MVQUAL identities remain unchanged. If the accepted current workload cannot fit under the existing campaign resource policy after the missing route is restored, stop and raise a focused D3 resource Challenge rather than bypassing the policy.

## 3. Blocking finding B13-2 — HAS representation is noncanonical Protocol 6.3

Revision 12 correctly identified the accepted project state and the relevant memory lessons, but its table is not the canonical HAS interface. Protocol 6.3 workflow authority requires this exact shape (no aliases):

```yaml
pem_basis:
  accepted_project_state: e72090e21cec5311ce87745b03603f8783cd15a7
  accepted_pem: hjin98/mdstats@e72090e21cec5311ce87745b03603f8783cd15a7:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: <bounded rationale>
```

Use only `APPLICABLE`, `NOT_APPLICABLE`, or `REVIEW_REQUIRED`. Do not substitute `applied`, `rejected`, aliases for the basis keys, or a byte hash alone for the recoverable accepted PEM publication route.

Record at least the materially matched entries already reviewed in R12:

- `SP-001` — `APPLICABLE`: owner-layer reduction/consolidation directly governed the R12 execution repair;
- `SP-002` — `APPLICABLE`: fail-closed authenticated boundaries remain applicable to target-order persistence/checkpoint/currentness;
- `SP-003` — `APPLICABLE`: immutable durable boundaries/restart reuse governed the decision not to add repair-side persistent state;
- `SP-004` — `APPLICABLE`: real-owner/current-regime qualification is material to this closure;
- `FF-002` — `APPLICABLE`: continuation authority and authenticated restart boundaries are directly relevant;
- `FF-003` — `APPLICABLE`: destructive-storage ownership remains relevant to immutable publication/cleanup;
- `FF-005` — `APPLICABLE`: downstream no-reconstruction behavior remains relevant and was rechecked;
- `FF-001` — `NOT_APPLICABLE`: R12/R13 do not touch MACE model reconstruction/realization;
- `FF-004` — resolve against its actual semantic identity envelope. Its accepted family is P5 TRAIN/CUDA scheduler/residency resource control; do not silently generalize it into a generic CPU-RAM family. Unless exact accepted PEM metadata establishes the target-order CPU-RAM surface is inside that family, record `NOT_APPLICABLE` with that bounded reason. Generic current resource authority still governs B13-1 independently of PEM.

No canonical PEM mutation is required merely to repair the HAS representation. Perform the ordinary closeout-learning assessment after the final repair; add/change PEM only if its admission threshold is independently met.

## 4. R12 evidence preserved as still applicable

The following R12 evidence remains applicable unless the R13 resource wiring materially changes its execution regime:

- bitwise/scalar-oracle REPAIR2 batch equivalence;
- D2 §9 clause-by-clause conformance;
- removal of the Python worker queue from REPAIR2;
- bounded mechanism profile showing 1.49 -> 17.2 effective cores and identical repair-plan digest;
- current-scale scientific identity equality to the R11-correct baseline;
- no new repair persistence/currentness owner;
- R11 publication/concurrency/family/documentation/currentness closures;
- affected regression failures already proven baseline-equal and outside the changed R12 surface.

Do not rerun expensive evidence merely for ceremony. R13 changes the resource routing into target-order stages, so final assembled acceptance must rerun the evidence whose execution regime is materially affected by that route.

## 5. Required final evidence

Before requesting another independent review, record:

1. exact R13 implementation commit and changed files;
2. production routing proof that finite campaign RAM budget reaches target-order `resource_scope`;
3. focused finite-budget admission/routing falsification;
4. actual representative COVREF peak RSS, entry RSS, incremental peak, exit RSS, finite stage budget and queue accounting;
5. representative current LTA fresh build after resource wiring, with complete build identity, repair-plan digest/order/MVQUAL identity checked against R12;
6. a post-`N_max` resumed run if the restored resource scope changes any target-order stage width/admission regime used by the R12 restart evidence; otherwise explicitly preserve the R12 restart realization with applicability rationale;
7. final affected regression after all executable edits;
8. canonical Protocol 6.3 `pem_basis` + `has` block using exact field names and dispositions;
9. explicit confirmation that no new selector, repair algorithm, currentness/checkpoint store, cleanup owner, memory manager or compatibility path was added.

No CI status is currently attached to the reviewed R12 assembled candidate; implementation-recorded local execution remains evidence to assess, not CI-attested fact.

## 6. Re-review gate

A fresh independent review may PASS only when:

1. every R11 correctness/ownership closure remains intact;
2. R12 REPAIR2 exactness and current-scale performance closure remain intact;
3. the existing campaign RAM budget is actually routed into target-order preparation through the existing `resource_scope` interface;
4. COVREF's actual in-stage peak RSS and incremental peak are measured, not inferred from end-minus-start RSS;
5. finite-budget representative execution is inside the governing resource envelope or any real violation is corrected through the existing resource owner;
6. final scientific build, repair/order and MVQUAL identities remain exact under the restored resource routing;
7. the HAS is represented in the canonical Protocol 6.3 schema against the unchanged accepted main basis (or refreshed if that basis advances);
8. affected final regression/integration evidence is applicable and no new failures are introduced;
9. no competing scientific, persistence, currentness, cleanup, resource-policy or compatibility owner exists.

Until all nine conditions hold, the restoration remains **ACTIVE / D4 NO-PASS** and must not be closed or archived.
