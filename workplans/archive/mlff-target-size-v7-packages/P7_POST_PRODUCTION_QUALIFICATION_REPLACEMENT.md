---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 7
status: planned
created_date: 2026-08-30
entry_condition: CODE-MLFF-TARGET-SIZE-V7-P6 cleanup/cutover functional acceptance PASS
architecture_change: material downstream qualification replacement after destructive retirement
compatibility_policy: current-generation-only-no-select2-fallback-no-retired-target-size-lineage
---

# P7 — V7-native post-production qualification and locked release evidence

## Objective and protected concerns

Rebuild the downstream MLFF verification capabilities that remain scientifically and operationally necessary after P6 retires the obsolete V5/V6 verification topology.

P7 must restore the **capabilities**, not the old architecture. The durable product outcome is:

```text
accepted current T_selected
 -> post-selection CV accepts one training method
 -> fresh final production on full exact T_selected
 -> freeze exact final-production publication before independent qualification evidence is exposed
 -> deployment parity
 -> physical PES / relaxation / finite-temperature dynamics qualification
 -> uncertainty calibration when applicable
 -> explicit one-shot locked-test activation
 -> immutable final qualification verdict for the exact frozen publication
```

Protected concerns:

- downstream evidence validates an already frozen production product and never becomes another target-size, checkpoint, seed, or committee selector;
- the old `SELECT2` fallback mechanism never returns under another name;
- target-size V5/V6 study/domain identities remain absent from current downstream persistence;
- independent neutral evidence roles remain statistically independent from training/model-selection use;
- exact model/deployment/runtime/reference identities are authenticated before scientific claims are accepted;
- absent external reference work is represented as waiting/unavailable, never fabricated success;
- a locked test is genuinely one-shot and cannot be reused as a tuning/model-selection loop;
- current P1-P5 scientific owners, persistence/currentness, provider/resource ownership, and long-GPU-qualification policy remain intact.

P7 begins only after P6 receives independent **cleanup/cutover PASS**. It must not be used to mask an incomplete P6 cleanup.

## Engineering envelope and product design

### 1. Product architecture

The globally justified architecture is one frozen publication boundary followed by one descendant qualification subsystem:

```text
P4 current N_selected / exact T_selected
        |
        v
P5 post-selection CV acceptance
        |
        v
fresh final-production run matrix
        |
        v
M3-only predeclared representative/member decision
        |
        v
+------------------------------------+
| FinalProductionPublication         |
| exact frozen deployable member set |
+------------------------------------+
        |
        | downstream evidence has no selection authority
        v
+------------------------------------+
| ProductionQualificationPlan        |
+------------------------------------+
   |          |            |        |
   v          v            v        v
 deployment  physical    calibration locked activation
 parity      PES/relax/
             dynamics
   \          |            |        /
    +---------+------------+-------+
                    |
                    v
       ProductionQualificationRecord
                    |
                    v
          release-qualified / rejected
```

Use focused numerical modules where the mathematics is materially distinct, but do **not** recreate six independent scientific lifecycle state machines. One qualification owner coordinates immutable typed component evidence under one frozen publication identity.

### 2. FinalProductionPublication — mandatory pre-qualification freeze

Add one canonical immutable current-generation owner above completed P5 final-production evidence.

It must bind, at minimum:

- exact current selected binding (`N_selected`, exact `T_selected`, current campaign generation);
- accepted post-selection method identity and CV-acceptance identity;
- final-production plan identity and production policy identity;
- ordered required production seeds;
- each completed final-production run-plan identity;
- each run's frozen representative checkpoint identity and checkpoint SHA256;
- exact target-head/deployable model artifact identity and SHA256 for every published member;
- the resolved committee/publication policy;
- the exact ordered final published member set;
- content identity sufficient for close/reopen/currentness authentication.

The publication is created **before** any deployment/PES/relaxation/dynamics/calibration/locked result is visible to the publication decision.

#### 2.1 `single_best_final_seed`

When the configured production policy is `single_best_final_seed`:

1. complete every required final-production seed run;
2. freeze each seed's representative checkpoint through the existing predeclared P5 target-only/M3 development-model-selection policy;
3. rank/select the one publication member using only the predeclared development/model-selection evidence available before downstream qualification;
4. publish exactly one member;
5. only then permit downstream qualification to open.

Downstream evidence cannot cause fallback to another seed/checkpoint.

#### 2.2 `all_qualified_final_seeds`

When the configured policy is `all_qualified_final_seeds`, the exact pre-publication-admissible required member set is frozen as the committee. A later failed mandatory qualification of any required member rejects the frozen committee; it does not silently shrink or substitute the committee after seeing qualification evidence.

If current P5 production evidence does not contain enough pre-qualification information to freeze either policy without downstream evidence, reopen Design before implementation invents a new selection rule.

### 3. Neutral evidence roles

Reuse the current neutral substrate rather than recreating label-domain/target-role freezes.

The current neutral role authority already distinguishes:

```text
DEVELOPMENT
OUTER_MONITOR
UNCERTAINTY_CALIBRATION
LOCKED_INTERPOLATION_TEST
```

Target-size development continues to consume only `DEVELOPMENT`. P7 maps descendant evidence as follows:

```text
M3/development evidence       -> pre-publication model/checkpoint/member decision only
OUTER_MONITOR                 -> candidate-independent post-production physical validation bases
UNCERTAINTY_CALIBRATION       -> predictions from the exact frozen publication/committee only
LOCKED_INTERPOLATION_TEST     -> explicit post-freeze one-shot locked evaluation only
```

P7 must preserve P1 split-exclusion/correlation identities and any role-specific purge/independence constraints. It must not synthesize an unavailable independent role from correlated development data merely to complete qualification.

### 4. Qualification state and persistence

Create one current-generation `ProductionQualificationPlan` and one terminal `ProductionQualificationRecord` (exact names may vary if equivalent semantics are clearer).

Their semantic identity must descend from the exact current publication and the material qualification inputs, including as applicable:

```text
selected binding digest
final-production plan/publication digest
qualification policy digest
neutral evidence-role membership digest(s)
exact published model/checkpoint/deployment artifact SHA256
external reference protocol + artifact identity
runtime/deployment executable capability identity
calibration/locked activation identity
```

Forbidden fields/ancestry in new current-generation records:

```text
target_size_study_digest
target_data_role_freeze_digest
label_domain_id
SELECT2 selection/frozen-candidate identity
retired V5/V6 materialization/domain maps
```

Reuse the current immutable descendant persistence/content-addressed store already used by post-selection evidence, or another existing current-generation store if it is the natural owner. `CampaignStore` may carry only the minimum currentness pointer/fence/projection needed by the public lifecycle; do not duplicate component evidence into a second authority.

All durable component records must be create-once/validate-existing or equivalent crash-safe immutable publication. Restart distinguishes waiting, incomplete, accepted, rejected, stale, and corrupt state without inferring completion from file existence.

### 5. Failure/result semantics

Use typed outcomes rather than fallback behavior:

- `passed` — all mandatory evidence for the exact publication satisfies frozen policy;
- `rejected` — a scientific/physical/deployment acceptance predicate failed for the exact publication;
- `waiting_for_reference` — required external DFT/reference evidence has not yet been supplied/authenticated;
- `not_applicable` — only for a capability explicitly inapplicable under the frozen policy (for example uncertainty calibration for a single-model product with no accepted uncertainty estimator);
- hard error — corruption, unsupported schema, currentness/lineage mismatch, missing mandatory product artifact, programming defect, or unsafe runtime mismatch.

A scientific rejection never triggers automatic retraining, checkpoint reselection, seed substitution, committee member removal, target-size change, policy loosening, or alternate publication under the same qualification evidence.

## Implementation obligations

### P7-A — freeze the exact final-production publication

**Concern / rationale:** Current P5 fresh final production stops short of an explicit immutable product boundary. Without a pre-qualification freeze, physical/locked evidence can accidentally become another selection channel.

**Required end state:** Implement the `FinalProductionPublication` owner described above and expose a real currentness-authenticated resolver/reopen path.

**Required consequences / constraints:**

- publication creation consumes only completed current P5 final-production evidence and predeclared development/model-selection policy;
- all required production runs for the configured policy must be accounted for before publication;
- every publication member's representative checkpoint and exported target-head model bytes are authenticated;
- publication currentness is fenced against P4 selected-binding, CV, method, and final-plan advancement;
- reopening the same current state yields the same publication identity;
- downstream qualification has read-only access to the frozen publication and no API to mutate its membership.

**Acceptance boundary:** Real P4/P5 selected/CV/final currentness owners and real final-production evidence/publication owner must execute. MACE numerical training may remain faked below the already accepted P5 trainer seam for bounded regression. The harness may not seed a publication or bypass current final-production completion.

**Acceptance evidence:**

- both publication policies (`single_best_final_seed`, `all_qualified_final_seeds`);
- missing/incomplete required final run fails closed;
- stale P4/CV/final pointer makes old publication non-current;
- close/reopen deterministic identity;
- structural proof that qualification modules cannot write publication membership;
- counterfactual: force a future physical failure for publication member A while B exists; publication remains A/the original committee and qualification rejects rather than selecting B.

### P7-B — deployment parity qualification

**Concern / rationale:** Static EVAL2/CV accuracy does not prove that target-head export, dtype conversion, deployed MACE representation, and ML-IAP/LAMMPS execution preserve the frozen model's E/F/stress behavior.

**Required end state:** For every frozen publication member, qualify the exact deployment path:

```text
authenticated publication model
 -> target-head/deployment export through current deployment owner
 -> exact deployed ML-IAP/LAMMPS artifact
 -> deterministic bounded parity probe
 -> E/F/(stress when available) comparison under dtype-justified tolerances
```

**Required consequences / constraints:**

- reuse current `mace_deployment`, target-head extraction/export, artifact-staging, runtime-capability, and MACE/LAMMPS ownership where applicable;
- do not recreate the old deployment campaign schema or old run-plan lineage;
- the probe cohort may be a deterministic bounded M3/development cohort because the claim is representation/runtime equivalence, not independent generalization;
- probe membership and comparison policy freeze before predictions;
- exact model/export/deployed artifact SHAs and runtime identity are bound to evidence;
- FP32/FP64 tolerances are justified by the existing/current precision policy and scientific numerical evidence, not chosen after observing failure;
- any required publication member failure rejects deployment qualification for the publication.

**Acceptance boundary:** The real mdstats export/artifact/runtime-parity semantic owner must execute. A bounded real LAMMPS/ML-IAP smoke through the actual deployed artifact is required when the repository's supported runtime is available; long target-GPU qualification is not. If the supported deployment runtime is unavailable, deployment-parity functional acceptance is `unavailable/blocking` rather than silently passed unless a governing project policy explicitly assigns that exact runtime check to release qualification.

**Acceptance evidence:** byte/artifact mutation, wrong head, wrong dtype, wrong executable/runtime identity, and deliberately perturbed predictions all fail; identical deployment passes; restart reuses only exact authenticated evidence.

### P7-C — candidate-independent physical validation plan and local PES evidence

**Concern / rationale:** Good static force RMSE does not guarantee correct local restoring physics or prevent model-dependent cherry-picking of easy validation configurations.

**Required end state:** Build one immutable `PhysicalValidationPlan` from `OUTER_MONITOR` plus P1 correlation/split-exclusion authority **without consulting final model predictions, seed identity, M3 score, or previous qualification failures**.

The plan chooses a bounded, deterministic, condition/correlation-aware base cohort. All frozen publication members are tested on the same plan.

Implement local-PES qualification over those bases with matched external reference support. Required physical semantics include, where applicable:

- deterministic symmetric atomic displacement modes;
- deterministic strain modes for periodic systems when enabled;
- exact geometry/request identity;
- matched `+/-` reference pairing;
- projected restoring force response;
- force-derived stiffness/sign checks;
- energy curvature checks;
- stress/strain response checks;
- finite/nonnegative/physical-domain validation;
- predeclared absolute/relative tolerances and resolution floors;
- all-required-mode policy when configured.

**External reference boundary:** P7 owns request identity, reference import/authentication, and matched reduction. It does not pretend to run DFT in ordinary CI. Bounded deterministic synthetic/analytic references are valid below that boundary for functional tests; production scientific qualification uses real external DFT references generated under the frozen request/protocol identity.

Missing required reference evidence produces `waiting_for_reference`, not pass/reject.

**Acceptance evidence:**

- physical plan is byte/identity-identical for different publication members;
- changing model predictions cannot change the plan;
- reference geometry/protocol mismatch is rejected;
- asymmetric/missing mode pairs fail closed;
- analytic harmonic reference fixtures recover expected stiffness/curvature within justified tolerance;
- sign-flipped or unstable local response is rejected;
- currentness/reopen preserves exact plan/evidence identity.

### P7-D — relaxation and finite-temperature dynamics qualification

**Concern / rationale:** Local pointwise/PES accuracy still does not prove that the deployed force field preserves topology during energy minimization or remains stable in finite-temperature simulation.

#### Relaxation

Use candidate-independent bases descending from the physical-validation plan and matched fixed-cell reference relaxations. Preserve separate hard topology safety and quantitative geometry fidelity.

Required semantics include:

- exact authenticated base/reference identities;
- fixed-cell deterministic relaxation policy unless a future accepted design adds variable-cell support;
- exact required protected-group connectivity/topology;
- periodic displacement handling;
- RMS/max atomic displacement;
- bond RMSE/max error;
- angle RMSE/max error;
- explicit convergence/failure reason;
- predeclared tolerances.

Where an equivalent physical-observable or topology calculation already has a canonical `mdstats.analysis` owner, call that owner instead of duplicating the numerical algorithm locally.

#### Dynamics

Run the already deployment-qualified artifact through the authenticated supported simulation runtime on the frozen DFT/reference-relaxed bases. Freeze temperature/case/velocity-seed policy before execution.

Required bounded diagnostics include:

- deterministic NVT warm-up and NVE propagation policy;
- timestep, damping, sampling interval, temperatures, velocity seeds;
- NVT/NVE temperature behavior;
- NVE energy drift per atom/time;
- minimum pair distance and maximum-force safety bounds;
- persistent protected-topology/bond damage rather than one-sample noise;
- protected-group displacement/bond/angle degradation;
- all-required-case policy when configured.

**Resource/orchestration constraint:** reuse current CPU/RAM/GPU/VRAM/disk admission, process-group cleanup, bounded concurrency, and deterministic commit-order machinery. Do not create a P7-private scheduler or let runtime pressure change scientific timestep, duration, temperature, precision, topology thresholds, or evidence membership.

**Acceptance evidence:**

- relaxation topology break rejects even if aggregate geometry error looks small;
- unstable or nonfinite dynamics rejects;
- deterministic case identity independent of worker completion order;
- worker/runtime failure propagates without partial evidence publication;
- restart reuses only fully authenticated completed cases;
- serial/concurrent bounded execution gives the same qualification record;
- provider/process/resource ownership is released on success and exception.

### P7-E — uncertainty calibration on the actual frozen publication

**Concern / rationale:** Calibration must describe the uncertainty of the product actually being deployed; it cannot be fitted on development evidence and then transferred implicitly to another committee/member set.

**Required end state:** Evaluate the exact frozen publication/committee on `UNCERTAINTY_CALIBRATION` and fit/apply only an accepted calibration method whose policy was frozen before observing calibration outcomes.

**Required consequences / constraints:**

- calibration inputs bind exact publication membership and exact calibration role membership;
- no member/checkpoint/seed/target-size/method change is permitted after calibration evidence is opened;
- calibration may not tune deployment/PES/relaxation/dynamics/locked acceptance thresholds;
- for a single-model publication with no accepted uncertainty estimator, policy may produce explicit `not_applicable`; do not invent uncertainty from seedless point predictions;
- any calibration algorithm already owned elsewhere in mdstats must be reused rather than duplicated.

**Acceptance evidence:** committee membership mutation invalidates calibration; calibration-only policy change leaves P4/CV/final publication unchanged but invalidates calibration evidence; deterministic bounded calibration fixtures recover known coverage/scaling behavior.

### P7-F — explicit one-shot locked-test activation

**Concern / rationale:** Locked evidence is meaningful only if it cannot influence prior training/model/publication/calibration-policy decisions and cannot be replayed as an optimization loop.

**Required end state:** Add explicit activation and terminal result records bound to the exact frozen publication and exact reserved `LOCKED_INTERPOLATION_TEST` role.

Activation must bind:

- publication digest and exact published model/deployment member SHAs;
- locked-role membership/artifact digest and source SHA where material;
- frozen locked-test acceptance policy;
- activation identity/time/order sufficient to prove post-freeze opening;
- exact prediction/reduction identity.

Before activation, ordinary qualification commands must not load locked labels, predictions, metrics, or use locked evidence to decide any earlier policy.

Activation preconditions:

- publication is current and immutable;
- all mandatory nonlocked qualification components required by policy have completed successfully;
- calibration status is valid for the product policy (`passed` or explicitly `not_applicable` when allowed);
- locked evidence has not already been activated for that publication/locked-role generation.

After activation:

- pass may contribute to release qualification;
- reject rejects the exact publication;
- no alternate seed/checkpoint/member/committee may be selected;
- no acceptance threshold may be loosened and the same evidence relabeled as a fresh locked test;
- retraining/republication after seeing locked evidence creates a new product publication but **does not restore independence of the same locked cohort**. Reuse of that cohort as a new locked test requires an explicit new scientific design with a genuinely independent locked role/evidence source.

**Acceptance evidence:**

- locked artifact cannot be opened through `qualification run`, status, publication creation, CV, or training paths;
- explicit activation is required;
- second activation of the same publication/role is rejected;
- forced locked failure leaves publication membership unchanged and release verdict rejected;
- modifying locked policy after activation does not create a fresh valid locked test;
- currentness/reopen preserves terminal locked result exactly.

### P7-G — public orchestration, currentness, invalidation, docs

**Concern / rationale:** Qualification must be visible and operable without becoming a second target-size/training lifecycle state machine.

**Required public interface:** add one post-production command family, for example:

```text
qualification status
qualification run
qualification activate-locked
```

Equivalent naming is delegated, but the semantic split is frozen.

- `qualification run` executes/resumes **nonlocked** publication qualification and may stop in `waiting_for_reference` with actionable reference requests.
- `qualification activate-locked` is the only public path that opens locked evidence.
- `qualification status` is observational and may report publication/currentness/component states without mutating scientific state.
- existing target-size/training `advance` remains bounded to the P1-P5 lifecycle and must not automatically activate locked evidence. Do not add a hidden auto-lock path.

Update current docs/config/source maps so the full implemented lifecycle is clear while retaining the distinction between training lifecycle and post-production qualification.

#### Invalidation DAG

Real current owners must enforce at least:

```text
target-size scientific change
 -> P4 selection stale
 -> CV stale
 -> final production/publication stale
 -> all qualification stale

CV-only scientific/policy change
 -> target-size remains current
 -> CV stale
 -> final production/publication stale
 -> all qualification stale

production-only policy change
 -> target-size and scientifically unaffected CV remain current
 -> final production/publication stale
 -> all qualification stale

publication member/bytes change
 -> qualification stale

qualification-policy change
 -> publication remains current
 -> affected qualification descendants stale

external PES/relax reference artifact/protocol change
 -> affected physical descendants stale
 -> publication unchanged

calibration-only policy change
 -> calibration descendant stale
 -> publication/physical qualification unchanged
```

Locked evidence is special: after activation, a policy/product change may make the prior locked result no longer applicable, but it cannot make the same revealed cohort a fresh locked test.

**Acceptance evidence:** execute the real CLI parser/dispatch and real currentness owners; no harness-side invalidation emulation.

## Implementation authority

### Frozen

- P6 cleanup/cutover PASS is a hard predecessor gate.
- P1-P5 target-size/CV/final-production science is not redesigned by P7.
- `FinalProductionPublication` freezes before any downstream qualification evidence is exposed.
- downstream evidence has pass/reject/waiting authority only for the frozen publication and zero model-selection/fallback authority.
- old SELECT2/verify orchestration and retired target-size/domain lineage remain absent.
- one current qualification owner coordinates typed component evidence; numerical specialization does not justify multiple independent selection/state authorities.
- neutral `OUTER_MONITOR`, `UNCERTAINTY_CALIBRATION`, and `LOCKED_INTERPOLATION_TEST` are the statistical evidence-role sources unless Design is reopened on proof they cannot satisfy the required envelope.
- explicit locked activation is mandatory and never automatic.
- real current persistence/currentness, deployment, scientific reduction, resource, and orchestration owners must remain under acceptance; expensive external/numerical work may be bounded only below those owners.
- no scientific threshold, evidence membership, timestep, temperature, precision, or model member may be adaptively changed after seeing qualification failure unless a new explicitly nonlocked product/design iteration is started; locked evidence never becomes a tuning loop.

### Delegated

- exact class/module filenames for publication, plan, component records, and orchestration;
- whether component evidence uses dataclasses/enums already standard in the package or equivalent immutable records;
- bounded deterministic OUTER_MONITOR base-selection algorithm, provided it is candidate-independent, correlation-aware, policy-identified, and scientifically representative;
- exact current post-selection descendant-store integration mechanics;
- reuse/refactoring of historical numerical kernels when available. Historical source may be consulted as an implementation aid but is **not normative authority**; the requirements in this workplan define the current behavior;
- exact CLI subparser spelling beneath the `qualification` family if semantics remain unambiguous;
- internal batching/concurrency strategy under existing resource owners.

### Reopen only on evidence

Reopen only the affected P7 design surface if:

1. current P5 final-production evidence cannot freeze the configured publication policy without introducing a new development/model-selection rule;
2. the neutral substrate cannot provide sufficiently independent OUTER_MONITOR/calibration/locked evidence for the configured product and no external role can be attached without changing the parent statistical design;
3. supported deployment bytes cannot be bound one-to-one to the exact frozen publication member through existing/current export/runtime owners;
4. a required physical validation metric would need to feed back into training/checkpoint/member selection to be meaningful;
5. an existing canonical mdstats analysis/calibration/deployment owner materially conflicts with the proposed P7 ownership and cannot be reused without duplicating authority;
6. a valid one-shot locked-test contract cannot be enforced with the available persistence/currentness model.

Do not reopen P1-P5 merely because porting old verification kernels is inconvenient.

## Affected surface and task-specific acceptance

Expected affected surface includes:

- P5 final-production evidence/publication/currentness descendants;
- post-selection immutable store/current pointers;
- target-head export and `mace_deployment`;
- artifact staging and deployment/runtime capability qualification;
- MACE provider/authentication and inference path;
- neutral outer/calibration/locked evidence-role projection;
- split-exclusion/correlation identities used to choose physical bases;
- local PES/reference request-import-reduction kernels;
- relaxation/topology/geometric comparison;
- LAMMPS/ML-IAP dynamics runner and process/resource ownership;
- reused `mdstats.analysis` observable owners where applicable;
- calibration owner;
- CLI parser/status/public guide/config/source maps;
- persistence/restart/currentness/invalidation;
- storage cleanup/retention fences so qualification evidence required for release is not reclaimed as reconstructible scratch;
- tests and generated documentation/PDFs.

### Task-specific structural/absence acceptance

Final source/current exports must prove:

- no current `SELECT2` authority or physical-fallback selection path;
- no new current record contains retired target-size-study/domain lineage;
- qualification cannot call target-size reducer, change `N_selected/T_selected`, change CV acceptance, select another final checkpoint/seed/member, or mutate publication membership;
- locked evidence has no import/call path from training, selection, CV, production publication, ordinary qualification run, or automatic advance;
- current docs/config/help do not describe old verify topology.

### Mandatory assembled integration

On one final candidate, execute through real parser/dispatch/current owners:

```text
prepare
 -> select-target-size
 -> cross-validate
 -> train-production
 -> freeze FinalProductionPublication
 -> qualification run
      -> deployment parity
      -> physical plan
      -> reference wait/import/resume as required
      -> PES
      -> relaxation
      -> dynamics
      -> calibration or explicit not_applicable
 -> close/reopen and reauthenticate all nonlocked evidence
 -> qualification activate-locked
 -> terminal qualification/release verdict
 -> close/reopen and reauthenticate terminal state
```

Use bounded deterministic datasets and accepted numerical fakes below expensive MACE/DFT boundaries for routine integration, but do not mock publication, currentness, plan construction, reference matching, qualification reduction, locked activation, or persistence owners. Any claim specifically about supported LAMMPS/ML-IAP deployed execution requires a bounded real runtime smoke rather than a Python-only proxy.

### Counterfactual acceptance cases

At minimum include:

1. publication freezes before downstream evidence;
2. frozen member A fails physical qualification while B exists -> reject A publication, never choose B;
3. one required committee member fails deployment -> reject committee, never shrink it;
4. deployment artifact or runtime identity mutation -> parity fails;
5. physical plan is identical across different publication members;
6. external reference mismatch/missing -> hard error or waiting, never fabricated pass;
7. relaxation topology break -> reject;
8. unstable dynamics -> reject;
9. calibration cannot modify publication membership or physical thresholds;
10. locked evidence inaccessible before explicit activation;
11. locked failure cannot trigger fallback/retrain-and-reuse-as-locked;
12. currentness advancement invalidates only the correct descendant scope;
13. close/reopen preserves exact publication, component evidence, activation, and verdict;
14. interruption during component publication leaves no partial evidence accepted as complete;
15. storage cleanup preserves authoritative publication/qualification/locked evidence and removes only owned reconstructible scratch.

### Regression and qualification disposition

After each material executable stage, run focused checks plus stage-local affected regression before dependent implementation. Final completion re-derives the complete affected surface and runs full affected regression plus assembled integration and repository-required checks.

The broader/full CPU-safe suite is required when the final impact cannot be bounded confidently because P7 crosses public CLI, persistence, deployment, external-reference, analysis, and release-evidence surfaces.

Production qualification is distinct:

- **functional acceptance:** required before P7 completion, including bounded real deployment-runtime smoke where supported;
- **real external DFT scientific qualification:** required for an actual production qualification campaign but not for routine software regression; functional tests use matched analytic/bounded reference fixtures below the reference owner;
- **long target-machine GPU/VRAM/performance/MD qualification:** deferred to the established final-release qualification phase, with reproducible P7 commands/config identities supplied. CPU-only tests must not be labeled GPU qualification.

## Implementation sequence and redesign risks

### Stage 1 — publication/currentness boundary

Implement P7-A first. Close semantic/currentness/persistence and affected P4/P5 regression before any downstream component can consume a publication. This is the highest-risk anti-selection boundary.

### Stage 2 — nonlocked deployment and physical qualification

Implement P7-B through P7-D on the frozen publication. Close deployment parity, physical-plan independence, reference round-trip, relaxation/dynamics, restart, resource/process cleanup, and affected deployment/analysis regression before calibration/locked work proceeds.

### Stage 3 — calibration and locked activation

Implement P7-E/P7-F. Close statistical-role isolation and the one-shot locked-test counterfactuals before public orchestration advertises release qualification.

### Stage 4 — public orchestration, invalidation, docs, final assembled acceptance

Implement P7-G, reconcile config/help/current manuals/source maps, execute the invalidation matrix, documentation/PDF checks, fresh final affected regression, real parser/dispatch assembled integration, and final structural absence/conformance review.

Material redesign risks are exactly the `Reopen only on evidence` triggers above. A failure of a predeclared scientific qualification threshold is a legitimate product qualification result, not by itself a software-design failure.

## Handoff closure

The P7 handoff freezes enough information that implementation does not need the deleted P5A6 verification source or prior chat to reconstruct product semantics:

```text
required downstream capabilities
+ pre-qualification immutable publication
+ neutral independent evidence roles
+ no-fallback/no-selection invariants
+ deployment/PES/relax/dynamics/calibration/locked semantics
+ current persistence/currentness/invalidation
+ real-owner acceptance boundaries
+ bounded-vs-production qualification separation
-> implementation obligations -> acceptance evidence
```

The snapshot-loss counterfactual is satisfied by this workplan plus the current supplied parent/P6/current architecture and repository source. Historical verification modules may inform implementation but are not required normative input.
