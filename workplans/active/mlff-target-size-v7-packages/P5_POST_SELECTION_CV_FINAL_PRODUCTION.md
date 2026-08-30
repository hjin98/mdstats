---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 5
status: active
package_revision: 3
amended_date: 2026-08-29
entry_p4_closure_commit: 145388e5ad11733be1c19539886e34b82cc7d7d2
revision2_baseline_commit: 2a3c3776aa03ac7e45dd0de2986a6bb390deb710
revision1_baseline_commit: 5bf53c99ce31d1438c21bae81c0f30c79176bdc4
compatibility_policy: current-generation-cutover-no-derived-migration
reconciliation_reason: Independent final design review of revision 2 found seven P5-local handoff gaps without invalidating the frozen parent or accepted P1-P4 architecture: publication-time currentness could race a concurrent new P4 generation; legacy MLCV could still grant replay metrics ranking credit; CV acceptance and final production lacked one explicit protocol identity; final target checkpoint/seed evidence roles were not positively owned after DATA5 retirement; CV membership admitted a subset loophole; legacy zero-fold cv_not_performed behavior was not explicitly retired; and screen/CV/final roles were not required to have collision-proof run namespaces. Revision 3 is a narrow final-hardening overlay that closes these gaps while preserving revision-2 science and the parent verdict.
---

# P5 revision 3 — final hardening of post-selection CV and fresh final production

## 0. Authority, overlay precedence, and preserved baseline

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. This package remains bound to Protocol 5.8.0. Nothing in revision 3 upgrades the protocol binding or reopens accepted P1-P4 science.

Revision 2 at commit `2a3c3776aa03ac7e45dd0de2986a6bb390deb710` is the complete baseline contract and is incorporated here by reference. All revision-2 requirements remain mandatory except where this revision makes them more specific. This overlay has precedence only for the P5-local surfaces named below.

Revision 3 does **not** reopen:

- `T_selected = pi_train[:N_selected]` or any P2 target-size statistical authority;
- P3 target-size screening, paired optimizer seeds, TRAIN2/EVAL2 execution evidence, reducer/head/restart semantics, or exact M-ladder ownership;
- P4 CampaignStore current-generation ownership, canonical current terminal loader/exposure chain, terminal-result API sealing, storage ownership, or canonical execution root;
- target-size ranking, N/M/fidelity ladders, target-size practical-equivalence policy, or selected N;
- the requirement that `[training].max_num_epochs` is the downstream production horizon and is independent of target-size screening `n3`;
- the requirement that long GPU/data-heavy production qualification is deferred to final release while bounded functional regression/integration remains mandatory.

The revision-2 one-way dependency remains frozen:

```text
current authenticated P4 SELECTED authority
  -> exact T_selected downstream binding
  -> post-selection CV of one frozen downstream training protocol
  -> fresh final-production run(s) on full T_selected
  -> downstream calibration / locked / deployment evidence
```

No P5 result may flow backward into target-size selection.

---

## 1. Final-review defects closed by revision 3

### 1.1 Publication-time currentness race

Revision 2 correctly requires reauthentication of P4 currentness before P5 start/resume/report/write. That alone does not close this interleaving:

```text
P5 validates selected generation g1
  -> concurrent real prepare commits g2 as P4 current
  -> stale g1 P5 writer publishes after g2
```

A g1 descendant may remain valid immutable **historical evidence**, but it must never become or overwrite a result advertised as current after g2 becomes current.

### 1.2 Legacy replay-weighted ranking is incompatible with current TRAIN2 semantics

Current TRAIN2 separates:

```text
replay degradation -> hard admissibility constraint
TARGET evidence     -> checkpoint/model ordering
```

Legacy MLCV selection/aggregation records still contain target/replay weights and combined scores. Those combined scores are not current P5 ranking authority. Reusing MLCV code does not preserve obsolete scientific policy.

### 1.3 CV and final production need one exact downstream protocol identity

CV validates a frozen method/protocol. Final production must execute exactly that validated method/protocol, modulo run-specific membership/seed identity. A CV pass under one LR/checkpoint/budget/precision/replay policy cannot authorize final production under another.

### 1.4 Retiring DATA5 MLCV authority left final target evidence under-specified

P5 must positively state which target evidence may control CV checkpoints, final-production checkpoints, final seed ranking, and any retained committee. Otherwise implementation could accidentally reuse locked/calibration evidence or legacy DATA5 role records.

### 1.5 CV subset loophole

"Every used frame belongs to T_selected" prevents expansion but does not prove that CV covers the intended selected population. A convenient strict subset could otherwise pass the revision-2 checks.

### 1.6 Legacy zero-fold bypass

Legacy `cv_not_performed` / zero-fold behavior is not part of the frozen parent lifecycle. Current P5 requires actual post-selection methodological CV before final production.

### 1.7 Cross-role run identity

Screen, CV-fold, and final-production jobs may share the same N and even the same numeric seed. They still require distinct run/restart/checkpoint namespaces so one role can never resume or overwrite another.

---

## 2. Frozen revision-3 product design

### 2.1 Current P5 publication is derived from current P4 authority

Keep the revision-2 canonical selected-training adapter:

```text
real cfg + paths + CampaignStore
  -> P4 expose/load current terminal
  -> require SELECTED
  -> CurrentSelectedTrainingContext
```

P5 descendants are immutable/content-addressed where practical and bind the exact P4 generation/revision plus `N_selected/T_selected` lineage.

**Preferred currentness realization:** there is no independently mutable P5 "current authority" at all. A current P5 read/report resolves P4 currentness first, derives the expected P5 binding, and exposes only matching immutable descendants.

If repository fit requires a mutable convenience pointer/index, it is **derived and non-authoritative**. Publication that changes such a current-facing pointer/index must be guarded by the existing CampaignStore transaction/CAS/lock boundary or an equivalent single owning transaction that rechecks the expected P4 generation/revision at commit time. A check performed only before the write is insufficient.

Frozen rules:

- immutable g1 P5 evidence may remain on disk after g2 exists;
- g1 evidence must be unreachable as *current* through public P5 APIs after g2 commits;
- no mutable P5 current file/cache/registry becomes a second upstream authority;
- no P5 publication may mutate P4 target-size state to obtain atomicity;
- same-binding concurrent publication is idempotent/conflict-safe;
- stale-binding publication loses the race deterministically and leaves current-facing state unchanged.

### 2.2 One canonical post-selection training-protocol identity

Introduce or adapt one version-agnostic immutable identity, conceptually:

```text
PostSelectionTrainingProtocolIdentity
```

It owns the downstream method whose CV result can authorize final production. It is distinct from the P4 target-size currentness identity and does not create a second selected-N authority.

It must bind every material method field that CV and final production must share, including as applicable:

- foundation/model/head initialization identity;
- training mode and architecture-relevant training protocol;
- objective/property/configuration weighting;
- replay source/exposure/TRUE_DFT admissibility semantics;
- optimizer family and non-seed optimizer settings;
- learning-rate schedule;
- production training budget resolved from `[training].max_num_epochs`;
- precision/dtype/backend/acceleration policy where scientifically material;
- batch/exposure semantics;
- checkpoint admissibility policy;
- checkpoint **target-only** selection policy;
- target evidence-role policy;
- any physical gates or monitor policy that can affect checkpoint/model acceptance.

Run-specific values such as CV fold index, exact fold membership, and the actual optimizer seed are child run-plan identities, not reasons to fork the protocol identity itself. A configured seed **policy/set** may participate when it changes the downstream experiment definition.

The resolved `[training].max_num_epochs` is part of this P5 downstream protocol identity even though it remains excluded from target-size screening identity. Therefore changing only production `max_num_epochs`:

- leaves accepted P4 target-size selection current;
- invalidates/requires new affected P5 CV/final descendants because CV must validate the actual downstream training protocol to be produced.

A method field that is also upstream target-size scientific identity continues to follow the existing P1-P4 invalidation DAG; P5 must not weaken upstream invalidation merely because it also appears here.

### 2.3 Exact post-selection CV universe and completeness

Define the current CV universe as exactly the selected target dataset plus the P1 neutral correlation relation projected **into** that dataset:

```text
CV_universe = exact T_selected
selected_group(g) = P1 neutral correlation/duplicate group(g) intersect T_selected
```

Unselected siblings never enter the CV universe.

The post-selection CV plan must content-bind:

- exact ordered `T_selected` membership/digest;
- exact selected-only group/correlation projection;
- configured fold count `K` with `K >= 2`;
- partition seed/policy;
- exact per-fold gradient-training, checkpoint-monitor, outer-evaluation, and justified purge memberships;
- deterministic accounting sufficient to prove no selected CV-eligible group silently disappears.

For ordinary K-fold CV:

- every CV-eligible selected correlation unit/group is held out as outer evaluation exactly once across the K folds;
- within each fold, gradient-training, checkpoint-monitor, outer-evaluation, and purge roles are disjoint under the selected-only correlation authority;
- any fold-local purge/defer state must be explicit and policy-derived, not silent omission;
- no group may be dropped merely to make a requested K feasible.

If the configured K is infeasible under the frozen selected-only correlation constraints, current P5 fails before expensive training with deterministic diagnostics. It must not silently reduce to zero/one fold, synthesize correlated evaluation evidence, or enlarge T_selected. A future explicit nonzero fold-reduction policy would be a P5 design revision; implementation may not invent it.

Current P5 therefore rejects `K < 2` and does not produce `cv_not_performed` as a production-authorizing outcome. Historical zero-fold records may remain readable only as unreachable historical compatibility evidence; they are never current authority.

### 2.4 Explicit downstream evidence-role map

Current P5 uses the following scientific role ownership.

#### CV folds

- **Fold target gradients:** exact fold-local subset of `T_selected`.
- **Fold checkpoint monitor:** selected-only fold-local monitor derived from the same current post-selection CV plan; it may control checkpoint admissibility/selection for that fold but is not outer-CV evidence.
- **Fold outer evaluation:** selected-only held-out fold; it evaluates the frozen protocol after checkpoint choice and cannot control that fold's checkpoint, target size, or final production seed ranking.
- **Replay TRUE_DFT:** admissibility/safety evidence only according to current TRAIN2 policy; never ranking credit.

#### Final production

- **Target gradients:** full exact `T_selected`.
- **Target checkpoint/model-selection evidence:** the frozen P2 `M3` reserve may be reused as development/model-selection evidence, because it is already selected-data-independent and explicitly permitted downstream by the parent. It is **not** independent validation because it participated in target-size development.
- **Replay TRUE_DFT:** hard admissibility/safety constraint only; never target-model ranking credit or tie-break.
- **CV held-out fold metrics:** gate whether the frozen protocol is methodologically accepted; they do not rank final-production checkpoints or seeds.
- **Calibration / locked interpolation / challenge evidence:** strictly downstream; cannot select checkpoints, seeds, production horizon, or committee membership.

If implementation evidence shows frozen M3 cannot serve the required final target model-selection role without violating an accepted predecessor contract, stop and reopen this specific P5 evidence-role decision. Do not substitute locked/calibration/CV-held-out evidence silently.

### 2.5 Target-only ordering after admissibility

Current checkpoint/seed ordering must follow the current TRAIN2 separation:

```text
candidate
  -> target/replay/physical admissibility gates
  -> among admissible candidates, target-only ordering
```

Consequences:

- no replay score weight in current P5 checkpoint ranking;
- no replay margin/metric in current P5 seed ranking or tie-break;
- no combined target+replay score may determine current representative/best-seed identity;
- replay degradation and absolute replay diagnostics may still be persisted for audit/diagnostics;
- CV cross-fold replay summaries may remain diagnostic/safety summaries but cannot become target-model ordering credit.

Legacy `MlcvRunSelectionPolicy`, `MlcvCrossValidationPolicy`, aggregate/final records, or helpers may be reused only after removing/bypassing their replay-ranking authority on the current path. Historical schemas may remain for historical reads/tests but cannot be current P5 scientific authority.

### 2.6 Fresh final production and role-separated run namespaces

Preserve revision-2 fresh-production requirements and add an explicit run-role identity boundary.

At minimum, execution/restart identity must distinguish:

```text
TARGET_SIZE_SCREEN
POST_SELECTION_CV(fold, seed)
FINAL_PRODUCTION(seed/run)
```

Equivalent existing repository role discriminators may be reused; do not add a redundant enum if one already closes the namespace.

For the same `N_selected` and the same numeric seed, roles must not collide in:

- run digest/ID;
- checkpoint directory/logical checkpoint owner;
- runtime summary/progress state;
- model export/publication identity;
- optimizer/RNG restart ownership;
- attempt/recovery state.

Role identity belongs in execution/run/checkpoint namespace. It must **not** unnecessarily contaminate policy-independent selected target membership or reusable DATA7/DATA8 scientific preparation identity.

"Selected size only" constrains target-data cardinality, not final-production multiplicity. All configured fresh final-production seeds/jobs remain allowed. Each starts from canonical initialization with fresh optimizer/RNG state and uses the exact shared post-selection protocol identity.

---

## 3. Revision-3 implementation obligations and stages

All stage-local executable work inherits Protocol 5.8 semantic/conformance closure plus focused and affected-regression functional closure before dependent stages proceed.

### P5-A3 — publication-time currentness and immutable downstream binding

**Required end state:** stale g1 work can remain historical but can never become current after a concurrent g2 P4 transition.

Required implementation consequences:

1. Preserve the revision-2 real `cfg + paths + CampaignStore` selected-training adapter and P4 canonical loader.
2. Bind every persistent CV/final descendant to exact P4 generation/revision + selected-membership lineage.
3. Prefer currentness-by-resolution over a mutable P5 current-state authority.
4. If a current-facing pointer/index exists, recheck expected P4 revision in the same transaction/critical publication boundary that makes the pointer current.
5. Same logical immutable descendant publication is create-once/idempotent; conflicting bytes/digests fail closed.
6. Do not hold a broad CampaignStore lock across expensive training. Perform expensive work under immutable attempt identity, then use a short commit-time currentness fence.

**Proxy-proof acceptance boundary:** real P4 CampaignStore transition and real P5 current-publication owner must execute. Expensive MACE work may be faked below them.

Mandatory race:

```text
real selected g1
 -> P5 validates/begins g1 descendant
 -> barrier before current-facing commit
 -> real prepare commits g2
 -> release g1 publication
 -> g1 cannot become current / overwrite current-facing state
```

Also prove same-g1 concurrent identical publication is idempotent and conflicting publication fails closed.

### P5-B3 — canonical downstream protocol identity and config binding

**Required end state:** CV acceptance authorizes final production only for the exact downstream protocol it validated.

Required implementation consequences:

1. Reuse existing protocol/policy dataclasses where semantically correct; add only the minimum aggregate identity needed to bind them together.
2. Resolve configuration through the existing canonical config path.
3. Bind `[training].max_num_epochs` into P5 downstream protocol identity and TRAIN2 budget, while keeping it independent of target-size `n3`/P4 identity.
4. CV fold run plans and final run plans carry the same downstream protocol digest.
5. Final-production entry rejects stale/mismatched CV evidence before numerical work.
6. Presentation/resource-only settings that do not change scientific/execution meaning must not cause unnecessary scientific invalidation.

Acceptance includes:

- CV under protocol A -> final protocol A accepted;
- mutate only LR schedule/checkpoint policy/precision or another method-defining field -> old CV cannot authorize final production;
- mutate only `[training].max_num_epochs` -> P4 selected generation remains current, but old P5 CV/final protocol binding becomes stale;
- `[training].max_num_epochs != n3` fixture proves actual CV/final TRAIN2 budget follows production horizon while P4 remains unchanged.

### P5-C3 — complete selected-only CV plan and zero-fold retirement

**Required end state:** current CV is a complete, leakage-safe methodological test of exact `T_selected`, never an expanded or convenient subset.

Required implementation consequences:

1. Build CV roles only from exact selected frame IDs plus selected-only projections of neutral P1 correlation/duplicate groups.
2. Persist/check a canonical CV-universe digest and exact per-fold role membership.
3. Require configured/resolved `K >= 2` on the current path.
4. Require every CV-eligible selected group to appear as outer evaluation exactly once across the K folds.
5. Require explicit fold-local accounting for training/monitor/evaluation/purge; reject silent omissions.
6. Reject infeasible K before DATA7/DATA8/TRAIN2 work.
7. Remove current orchestration reachability of `cv_not_performed` / zero-fold production authorization.
8. Preserve deterministic membership for same selected binding + policy + seed.

Acceptance includes:

- selected member + unselected correlated sibling never expands the universe;
- deliberately omit one eligible selected group -> plan validation rejects;
- duplicate outer holdout across folds -> rejects;
- same-input plan is byte/digest deterministic;
- K=0 and K=1 reject before training;
- infeasible K rejects rather than silently shrinking or synthesizing evidence;
- no legacy DATA5/label-domain/CV plan is required.

### P5-D3 — current MLCV selection/aggregation policy cutover

**Required end state:** replay protects admissibility but target evidence alone orders admissible checkpoints/seeds.

Required implementation consequences:

1. Route fold/final checkpoint admissibility through the current TRAIN2 admissibility authority, including authenticated TRUE_DFT replay requirements.
2. Route checkpoint ranking through current target-only `CheckpointSelectionPolicy` or one semantically identical shared owner.
3. Remove/bypass current use of legacy target/replay weighted `full_score` for representative selection, final seed ranking, or tie-break.
4. Outer-CV aggregation may summarize target and replay diagnostics separately; protocol acceptance cannot smuggle replay ranking credit back through a combined score.
5. CV outcome gates downstream protocol acceptance only; it cannot rank N or select a final production seed.
6. Final target checkpoint/seed evaluation uses the explicit role map above; calibration/locked evidence is unreachable from these decision owners.

Mandatory reversal test:

```text
candidate A: better target metric, worse but admissible replay
candidate B: worse target metric, better replay
legacy weighted score would prefer B
current P5 must prefer A
```

Add corresponding seed-ranking/tie-break coverage if final seed selection has a separate owner.

### P5-E3 — fresh final production and collision-proof execution identity

**Required end state:** final production is new training under the CV-accepted protocol, not continuation or namespace reuse.

Required implementation consequences:

1. Final target gradients are full exact ordered `T_selected`.
2. Final target checkpoint/model-selection evidence is frozen M3 development/model-selection evidence unless the evidence-role stop condition fires.
3. Every final run starts from canonical foundation/init with fresh optimizer/RNG state.
4. No target-size or CV checkpoint/optimizer/RNG lineage is an admissible parent.
5. Final run receives the same post-selection protocol digest accepted by CV.
6. Screen/CV/final run identities are collision-proof even when N and numeric seed are equal.
7. Preserve configured multiplicity of fresh final-production seeds/jobs.
8. Existing final committee machinery may retain all qualified fresh final seeds only if its current role/evidence semantics conform to this overlay; it may not retain fold/screen models as production committee members.

Acceptance includes a same-N/same-seed fixture across screen, CV, and final production proving distinct run IDs, checkpoint roots, restart ownership and model-publication identities.

### P5-F3 — public/orchestrator cutover and structural absence

All current P5 CLI/orchestration paths must flow through:

```text
P4 current selected adapter
 -> currentness-safe P5 binding/publication
 -> complete selected-only CV plan
 -> one post-selection protocol identity
 -> current TRAIN2/EVAL2 selection/admissibility semantics
 -> fresh final production
```

Structural/absence acceptance must prove:

- one P4 current terminal/currentness owner remains;
- one thin P5 selected-training adapter remains;
- no P5 mutable current-state authority competes with CampaignStore;
- no target-size result JSON is read as N/T authority;
- no legacy DATA5/label-domain CV authority edge is reachable from current P5;
- no `cv_not_performed` / zero-fold path can authorize current production;
- no current P5 representative/final-seed decision consumes replay-weighted combined score;
- no calibration/locked evidence reaches checkpoint/seed selection;
- no current path changes P4 N/reducer/head/current revision;
- no target-size `n3` -> production budget dependency or reverse dependency exists;
- no V7/version-prefixed production symbols are introduced merely by this workplan.

P6 remains the owner for destructive deletion of unreachable legacy topology unless immediate removal is strictly necessary to prevent current reachability.

### P5-G3 — fresh assembled closure

P5-G3 is blocked until P5-A3 through P5-F3 achieve both semantic/conformance and functional closure.

Mandatory assembled lifecycle through real owners:

```text
real cfg + real CampaignStore
 -> current P4 SELECTED authority
 -> exact current T_selected binding
 -> complete selected-only K-fold CV plan (K >= 2)
 -> bounded CV DATA7/DATA8/TRAIN2/EVAL2
 -> target-only representative ordering after replay admissibility
 -> CV accepts exact PostSelectionTrainingProtocolIdentity
 -> configured [training].max_num_epochs final budget
 -> fresh final-production DATA8/TRAIN2 on full T_selected
 -> final checkpoint/seed selection using authorized target evidence + replay gate
 -> persist/reload descendants
 -> fresh P4 currentness resolution
 -> expose matching current P5 result
```

Mandatory final assertions:

- same exact P4 `N_selected/T_selected` before and after all P5 work;
- P4 current revision/head/reducer unchanged by CV/final production;
- CV universe equals exact `T_selected`, with complete deterministic fold accounting;
- every eligible selected CV group is held out exactly once;
- CV held-out evidence never controls its own checkpoint or final seed ranking;
- replay influences admissibility only, never ranking credit;
- final production uses the exact CV-accepted downstream protocol identity;
- final gradients use full exact T_selected;
- final target model-selection role is authorized M3 development/model-selection evidence and is not relabeled independent;
- calibration/locked evidence remains downstream;
- final optimizer/init/RNG ancestry is fresh;
- actual production/CV budget follows `[training].max_num_epochs`, independently of `n3`;
- screen/CV/final run namespaces remain disjoint even for equal N/seed;
- current result exposure succeeds only after fresh P4 currentness resolution.

Mandatory negative matrix additionally includes:

1. P4 `FAILED_SCIENTIFIC` cannot enter P5;
2. retained legitimate g1 P5 evidence after real g2 prepare cannot become current;
3. deterministic barrier-controlled g1-publication-vs-g2-prepare race loses stale publication;
4. wrong/reordered/expanded or incomplete selected membership rejects;
5. selected + unselected correlated sibling cannot expand CV population;
6. omitted eligible selected CV group rejects;
7. duplicate/missing outer-fold coverage rejects;
8. K=0/K=1 and legacy `cv_not_performed` production authorization reject;
9. screening checkpoint/optimizer offered to CV rejects/unreachable;
10. screening/CV continuation offered to final production rejects/unreachable;
11. replay-weighted ranking-reversal fixture still selects target-better admissible candidate;
12. CV failure cannot invoke target-size reducer/reselection;
13. CV protocol A cannot authorize final protocol B;
14. changing `[training].max_num_epochs` invalidates old P5 protocol/CV binding but leaves P4 selected authority unchanged;
15. locked/calibration evidence cannot influence checkpoint/seed selection;
16. same-N/same-seed cross-role jobs cannot collide or resume each other;
17. stale/missing derived target-size result JSON cannot supersede CampaignStore authority.

---

## 4. Affected surface and regression obligations

Initial affected surface includes, only where implementation actually touches or consumes them:

- P5 selected-training/current-publication adapter and downstream binding records;
- CampaignStore transaction/CAS/currentness interfaces used for commit-time fencing;
- post-selection CV plan/role records and neutral selected-correlation projection;
- `mlcv_roles.py`, `mlcv_select.py`, `mlcv_aggregate.py`, `mlcv_final.py`, monitors/verification or replacement current-path records;
- TRAIN2 budget/LR/admissibility/selection policy integration;
- EVAL2 target/replay role/evaluation integration;
- DATA7/DATA8 materialization and MACE run-plan identity;
- final production/committee publication paths actually reused;
- config resolution for CV K/seed/policy and `[training].max_num_epochs`;
- restart/storage/concurrency/publication owners;
- CLI/orchestrator/public export surfaces;
- current architecture/spec/user documentation affected by the P5 current path.

After every material behavior-changing stage, run focused checks plus the full affected regression subset for that stage before dependent work proceeds.

Before P5 closure:

1. reconcile every revision-2 + revision-3 material obligation against the assembled candidate;
2. re-derive affected behavior from the final diff rather than relying on this initial list;
3. run fresh complete affected-surface regression on that candidate;
4. run assembled P4 -> P5 real-owner integration, including the deterministic publication race;
5. run broader repository tests if the final affected surface cannot be bounded confidently;
6. update durable architecture/spec/user docs if public/current contracts changed.

Required P4/P3 regression is impact-based: current-terminal/currentness tests are mandatory because P5 wraps that seam; P3A9/reducer/head tests are required when implementation touches or changes their resolver/currentness consumption, not merely because a new session began.

Long GPU/full-data production qualification remains deferred to final release. Bounded real-owner functional testing may replace expensive training/prediction below the semantic owners under acceptance; it may not mock the currentness fence, CV-plan owner, protocol-identity owner, checkpoint/admissibility decision owner, or final-production orchestrator and then claim those owners are accepted.

---

## 5. Implementation authority

### Frozen

Implementation must preserve:

- the complete revision-2 baseline except where revision 3 is more specific;
- Protocol 5.8.0 binding;
- parent V7 one-way science and accepted P1-P4 ownership;
- exact selected-data semantics `T_selected = pi_train[:N_selected]`;
- CampaignStore/P4 as the only current target-size authority;
- publication-time stale-generation exclusion, not only pre-write checking;
- one exact P5 downstream training-protocol identity shared by CV and final production;
- complete selected-only CV universe and K >= 2 current methodological validation;
- explicit downstream evidence-role map;
- target-only ordering after replay/physical admissibility;
- fresh final production on full T_selected;
- `[training].max_num_epochs` as P5 production/CV budget authority independent of target-size n3;
- collision-proof screen/CV/final execution/restart namespaces;
- no locked/calibration leakage into model-control decisions;
- no current legacy DATA5 CV authority or zero-fold production bypass;
- stage-local and fresh final affected regression/integration;
- deferred long GPU/production qualification.

### Delegated

Implementation may choose:

- exact version-agnostic names/modules for the P5 selected context, binding, protocol identity and CV-plan records;
- whether current P5 exposure is implemented with no mutable pointer at all (preferred) or a derived pointer transactionally fenced against P4 currentness;
- exact reuse/refactoring boundary among legacy MLCV modules versus new current-generation records;
- deterministic selected-group CV assignment algorithm, provided the frozen universe/completeness/leakage rules hold;
- exact final-production role discriminator if existing run/job-kind identity already provides collision-proof separation;
- exact target metric tuple/tie-break already owned by current `CheckpointSelectionPolicy`/accepted downstream target policy;
- compact persistence layout for immutable P5 descendants, provided ownership/restart/currentness constraints hold;
- bounded numerical fakes below accepted semantic-owner boundaries.

### Reopen only on evidence

Stop dependent implementation and reopen only the affected P5 surface if evidence shows:

1. P4/CampaignStore cannot provide a short commit-time stale-generation fence without modifying accepted upstream semantics;
2. neutral selected-only correlation evidence cannot construct K >= 2 leakage-safe CV for supported default workloads;
3. the frozen M3 reserve cannot serve final target checkpoint/model-selection evidence without violating an accepted predecessor contract;
4. current TRAIN2 target-only selection cannot express required downstream checkpoint/seed ordering without a genuinely different scientific policy;
5. CV and final production cannot share one protocol identity because a scientifically necessary field must differ between them;
6. shared DATA7/DATA8/TRAIN2 execution cannot provide role-separated restart identity without changing accepted common execution semantics;
7. a required training-method change invalidates the upstream target-size experiment whose result P5 consumes;
8. the frozen parent and implemented predecessor authority are materially contradictory rather than locally adaptable.

Do not weaken the stated invariant silently when one of these triggers fires.

---

## 6. Exit gate

P5 revision 3 is implementation-ready only under this complete revision-2 + revision-3 contract.

P5 is accepted after implementation only when:

> The current P4-selected dataset is freshly authenticated and cannot lose publication currentness to a concurrent new generation; exact `T_selected` is completely and leakage-safely covered by mandatory post-selection CV; CV validates one explicit downstream training-protocol identity; replay evidence constrains admissibility but never receives model-ranking credit; final production uses full exact `T_selected`, fresh optimizer/model/RNG lineage, authorized M3 development/model-selection evidence, and the same CV-accepted protocol; `[training].max_num_epochs` remains independent of target-size `n3`; and screen, CV, and final-production runs cannot collide even when their N and numeric seed coincide.

After implementation, stage-local closure, fresh assembled affected regression/integration, and independent review all pass, mark P5 implemented/accepted and commit the formal P5 closure checkpoint. P6 remains blocked until that closure.