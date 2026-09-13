# MLFF P5 TRAIN2 -> EVAL2 CuEq architecture recurrence repair workplan

**Status:** ACTIVE / PROPOSED FOR IMPLEMENTATION  
**Protocol:** SSDP 6.3  
**Repository:** `hjin98/mdstats`  
**Branch:** `fix/mlff-p5-train2-eval2-cueq-architecture-recurrence`  
**Accepted project baseline:** `b65fa3b02807815d8eca758bc04fb70d514d1f45`  
**Problem class:** recurring P5 TRAIN2/EVAL2 realized-architecture identity nonconformance  
**Earliest affected semantic level:** D4 implementation/concretization under the accepted P5 TRAIN2/EVAL2 D3 architecture  
**Current Serious Challenge:** NONE. A bounded D3 challenge is a conditional reopen only if Gate G2 proves that the canonical execution-architecture identity cannot faithfully distinguish semantic architecture from incidental CuEq realization state.

---

## 1. Problem statement

A real post-selection cross-validation run completed all five TRAIN2 folds successfully, released the TRAIN scheduler, and entered serial EVAL2. The first EVAL2 provider-authentication step then failed before checkpoint state was admitted to inference:

```text
TrainingDataInputError: TRAIN2 and independent MACE architecture differ in the cueq realization:
summary=3c9ab615faec3391fc57b5594546279a89d7c6b5fac2ad088895ee38f976de7b;
reconstructed=62413c3cd93d48fef920cdfeb83a84a3d662b6a0968b5b269c27ad4788e0f734.
```

Observed execution facts from the stakeholder run:

- TRAIN2 completed `5/5` runs with `failed_jobs=0`.
- The last run completed epoch `10/10` and all planned gradient updates.
- Post-TRAIN occupancy fell to approximately the clean CUDA baseline before EVAL2, so the failure is not the preceding memory-pressure defect.
- EVAL2 fails at `authenticate_train2_checkpoint_provider()` before model state controls inference.
- The TorchScript/PyTorch warnings printed near the traceback are non-causal.

The immediate invariant violation is therefore:

```text
persisted digest of the actual TRAIN2 training realization
    !=
independently reconstructed digest of the configured training realization
```

The authentication guard is correct and SHALL remain fail-closed. This work does not make the mismatching checkpoint acceptable by weakening the guard. It repairs the earliest mechanism that causes two representations intended to denote the same frozen TRAIN2 method to diverge, or escalates to D3 if the identity contract itself is proven unsound.

---

## 2. Why this is a recurrence and why the work is family-level

This is materially the same semantic family as the previously repaired TRAIN2/EVAL2 realized-MACE-architecture boundary:

- real TRAIN2 construction and independent reconstruction must agree on one canonical execution-architecture identity before checkpoint state is loaded;
- for `enable_cueq=true`, `only_cueq=false`, TRAIN2 is a transient CuEq realization while EVAL2 consumes an authenticated portable e3nn representation;
- the accepted phase-separated repair already requires reconstruction of the same training realization before projecting state back to portable e3nn;
- previously discovered architecture-reconstruction drifts included dataset/model heads, `avg_num_neighbors`, scale/shift buffer shape, and atomic-energy buffer shape;
- prior repair history explicitly required a real bounded P5 CuEq parity test and reuse of valid completed TRAIN2 state when the mismatch is representation-only.

Under SSDP 6.3 convergence rules this is not to be handled as another isolated exception. The implementation pass SHALL inspect the shared realization/identity owner and obvious sibling variants, then repair or simplify that owner. Do not add a checkpoint bypass, alternate digest, fallback acceptance route, or compatibility wrapper around the failure.

---

## 3. Governing authority and preserved invariants

### 3.1 Governing current owners

The implementation SHALL resolve and obey the accepted-current owners at the branch baseline, including at minimum:

- current MLFF training/execution architecture manuals and specifications;
- P5 post-selection CV/final-production semantics;
- `mdstats/training_data/model_features.py` canonical execution-architecture descriptor and accelerator realization/projection owners;
- `mdstats/training_data/target_size_execution/evaluation.py` checkpoint/provider authentication owner;
- `mdstats/training_data/train2_runtime.py` TRAIN2 runtime-summary and checkpoint-state owner;
- `mdstats/training_data/post_selection_execution.py` P5 executable configuration/materialization owner;
- `mdstats/training_data/campaign_post_selection_runtime.py` TRAIN2/EVAL2 orchestration and phase-separation owner;
- pinned `mace-torch==0.3.16` construction and e3nn<->CuEq conversion semantics.

Historical workplans and implementation evidence are diagnostic/provenance inputs, not current product authority.

### 3.2 Invariants that SHALL NOT change in this repair

1. **Fail-closed architecture authentication.** Checkpoint state may not reach EVAL2 until the independently reconstructed actual training realization agrees with the persisted TRAIN2 architecture identity.
2. **Actual TRAIN2 identity.** `Train2RuntimeSummary.model_architecture_digest` represents the model realization that actually owns TRAIN2 state, not an intended/configured architecture guessed after the fact.
3. **Phase-separated CuEq.** For the qualified `enable_cueq=true`, `only_cueq=false` path, CuEq is transient TRAIN2 execution; portable e3nn remains the downstream EVAL2/deployment representation required by current policy.
4. **One frozen scientific method.** Do not change target/replay membership, true-label replay, foundation checkpoint/head, optimizer/loss, learning rate, EMA semantics, precision, scientific batch/exposure semantics, CV folds/seeds/horizons, or checkpoint-selection convention to make authentication pass.
5. **Canonical normalization.** No fold-local or candidate-local recomputation of model-affecting `avg_num_neighbors` may be introduced.
6. **State provenance.** Raw checkpoint bytes, companion bytes, epoch boundary, live/EMA state digests, materialization identity, execution authority, and run ancestry remain authenticated independently of architecture identity.
7. **Portable projection proof.** After authenticating and loading state into the true training realization, the projected portable model must itself satisfy the authorized portable architecture before EVAL2 is exposed.
8. **Lifetime ownership.** Temporary portable/CuEq/OEq models created for classification or authentication must be retired at their existing model-scale accelerator ownership boundary, including failure paths.
9. **Scheduler phase ownership.** TRAIN scheduling ends at authenticated TRAIN2 completion; EVAL2 is not put back inside a TRAIN resource slot.
10. **No destructive recovery by default.** Existing completed TRAIN2 checkpoints are preserved until classified by the repaired current owner.

---

## 4. Explicitly forbidden repair strategies

The implementation SHALL NOT:

- accept either the summary digest or reconstructed digest as interchangeable;
- skip the CuEq architecture comparison for P5, CUDA, replay, or resume paths;
- downgrade the mismatch to a warning;
- authenticate only `state_dict` key/shape compatibility;
- compare only portable e3nn architecture while loading state directly into a different CuEq topology;
- silently force e3nn training or change `only_cueq` to avoid the failing path;
- delete or regenerate the stakeholder's valid-looking five completed TRAIN2 runs before classification;
- change the expected digest to match existing artifacts;
- broadly remove CuEq buffers/modules from the canonical architecture descriptor merely because they differ;
- add a second persistent CuEq architecture identity, migration database, checkpoint wrapper, sidecar reconciliation format, or special P5 acceptance path when existing ownership can be corrected or consolidated;
- reimplement MACE's CuEq converter in mdstats when the pinned dependency's qualified conversion owner can be reused;
- introduce GPU resource-policy changes as part of this identity repair.

---

## 5. Historical Applicability Set

This task is memory-triggering because an accepted repair family has materially recurred. No canonical project PEM is present at the accepted repository root, so bounded immutable historical intake over the directly affected lineage is used instead.

```yaml
pem_basis:
  accepted_project_state: b65fa3b02807815d8eca758bc04fb70d514d1f45
  accepted_pem: NONE_PROTOCOL_6.2_PRE_PEM
  candidate_overlay_semantic_candidate: NONE
has:
  - id: historical-realized-mace-architecture-parity
    disposition: APPLICABLE
    reason: The same TRAIN2/EVAL2 architecture-authentication invariant previously failed because independent reconstruction did not match actual pinned-MACE construction.
  - id: historical-phase-separated-cueq-authentication
    disposition: APPLICABLE
    reason: The accepted prior repair explicitly requires transient CuEq authentication followed by native projection to portable e3nn for EVAL2.
  - id: historical-p5-checkpoint-preservation
    disposition: APPLICABLE
    reason: Prior accepted design requires reauthentication of already-trained runs before destructive deletion when the difference may be representation-only.
  - id: train2-zero-safe-admission-memory-pressure
    disposition: NOT_APPLICABLE
    reason: The reported run completed all TRAIN2 work and returned to clean post-TRAIN occupancy; the current failure begins at EVAL2 architecture authentication.
```

If a canonical project PEM is introduced or the accepted project state materially advances before closeout, refresh this basis and materially affected dispositions.

---

## 6. Root-cause decision tree

The implementation SHALL diagnose before selecting a repair. At least these three hypotheses remain open initially:

### H1 — portable reconstruction drift

The independently constructed portable model differs from the real model MACE had immediately before TRAIN2 accelerator conversion. Plausible dimensions include, but are not limited to:

- foundation-model selection/removal semantics;
- target/replay head set, order, and names;
- `pt_head` foundation-derived calibration;
- atomic energies and scale/shift structure;
- frozen `avg_num_neighbors`;
- model family/configuration fields;
- dtype/device-affecting construction;
- current P5-specific configuration projection.

### H2 — accelerator realization drift

The portable models agree, but mdstats' independent `realize_mace_training_model()` does not create the same CuEq architecture as real pinned MACE TRAIN2. CUDA-sensitive converter options, conversion timing, copied-model semantics, or dependency-internal realization configuration may differ.

### H3 — canonical descriptor overbinding or wrong timing

The same semantically valid CuEq architecture can produce different descriptor state, or architecture-classified state mutates after initial conversion but before/while TRAIN2 persists the summary. If so, the problem is not solved by reconciling one reconstruction recipe; the canonical descriptor or the time at which its identity is captured is wrong.

A fourth class, **actual method divergence**, remains possible: the real TRAIN2 process may genuinely have trained a model-affecting realization outside the frozen P5 method. That outcome invalidates the affected TRAIN2 artifact and is not repaired by migration/blessing.

---

## 7. Implementation gates

### G0 — reproduce and preserve the failing evidence

Before executable mutation:

1. preserve the stakeholder traceback and the two observed architecture digests as diagnostic evidence;
2. reproduce the mismatch with the smallest real-owner P5 configuration that crosses the actual MACE TRAIN2 -> persisted summary -> independent authentication boundary;
3. do not use a hand-built model on both sides of the comparison;
4. bind the reproducer to the pinned dependency and current executable configuration owner;
5. if the exact CUDA route is unavailable, establish the strongest CPU/control evidence possible but mark CUDA-specific realization claims unavailable rather than inferred.

**Exit:** a bounded reproducer reaches the same fail-closed owner and identifies the exact executable configuration and summary being compared.

### G1 — empirical construction census

Instrument a development-only probe/test seam around the real owner boundary; do not add a permanent production tracing subsystem.

For one exact P5 configuration compare canonical descriptors at these boundaries:

```text
A = actual MACE portable model immediately before accelerator conversion
B = independent portable reconstruction from authenticated P5 configuration
C = actual live TRAIN2 CuEq model immediately after the dependency's conversion
D = independent CuEq realization from B through the qualified conversion owner
E = actual TRAIN2 CuEq model at the point the runtime architecture digest is persisted
F = a second independent CuEq realization from the same B/configuration
G = portable model obtained by native CuEq -> e3nn projection after authenticated state load
```

For A/B, C/D, C/E, D/F, and A/G as applicable, collect:

- canonical digest;
- `mace_model_execution_architecture_first_difference()` result;
- bounded first differing descriptor entry within that dimension when safe and deterministic;
- exact config fields relevant to accelerator realization;
- dependency/runtime version and device regime.

The census SHALL distinguish learned parameter values from architectural parameter structure and SHALL NOT log model weights.

**Exit classifications:**

- `A != B` -> H1 confirmed;
- `A == B && C != D` -> H2 confirmed;
- `C == D && C != E` -> H3 timing/mutability confirmed;
- `D != F` under equivalent inputs -> H3 deterministic-identity challenge confirmed;
- real TRAIN2 consumed a model-affecting value outside frozen authority -> actual method divergence confirmed.

Do not stop after finding the first field. Once one class is confirmed, census all descriptor dimensions on that boundary so the next sibling mismatch is not left for another cycle.

### G2 — select and execute the earliest-owner repair

#### G2-A — if H1 is confirmed

Repair the existing portable-model/configuration reconstruction owner so the independent model exactly reproduces the real pinned-MACE pre-conversion construction for the governed P5 path.

Requirements:

- use one canonical P5 executable configuration authority;
- preserve current head/foundation/replay semantics;
- remove duplicated/rederived model-affecting defaults where one accepted owner already exists;
- census and close all model-affecting differences found by G1, not only the first;
- keep the architecture descriptor strict.

#### G2-B — if H2 is confirmed

Repair/consolidate `realize_mace_training_model()` so it delegates to the same qualified pinned-MACE e3nn -> CuEq realization semantics used by actual TRAIN2.

Requirements:

- reuse dependency-native conversion rather than duplicating it;
- explicitly preserve device-sensitive converter semantics;
- preserve `only_cueq=true` behavior where MACE does not perform the same transient conversion;
- keep the operation transient and non-persistent;
- keep accelerator conversion serialization/lifetime rules intact.

#### G2-C — if H3 timing/mutability is confirmed

Determine the first descriptor field that changes and its owner.

- If the field is genuine forward/execution architecture, persist/compare identity at the correct stable owner boundary and prove restart equivalence.
- If the field is learned or legitimate mutable training state misclassified as architecture, narrow the canonical descriptor specifically at the owning type/field with evidence that the excluded value is state, not architecture.
- If equivalent conversions are intrinsically nondeterministic in a descriptor-bound architectural field, stop D4 implementation and raise a bounded D3 Serious Challenge. Do not manufacture equality with tolerance or field deletion.

#### G2-D — if actual method divergence is confirmed

Keep authentication rejection. Repair the upstream executable projection that allowed the divergence, invalidate only affected run artifacts through existing currentness/state machinery, and require recomputation under the corrected frozen method. No checkpoint migration is allowed.

### G3 — consolidate the canonical realization path

After G2, inspect current call sites that independently answer this question:

```text
What exact model realization does this authenticated P5 executable configuration train?
```

At minimum inspect recovery/currentness classification, continuation authentication, EVAL2 provider authentication, and any preflight architecture classification.

Where two sites maintain parallel recipes, reduce them to one existing canonical construction/realization operation or one minimal extracted owner. Prefer alteration/consolidation of existing functions over a new wrapper hierarchy.

The canonical operation must expose enough information for callers to distinguish:

- portable model;
- transient training realization;
- realization kind (`None`/CuEq/OEq as currently supported);
- canonical architecture digest;
- ownership/lifetime boundary.

Do not create a second persistent authority record merely to return these process-local facts.

### G4 — diagnostic closure

The current failing exception reports only the two digests even though the repository already owns `mace_model_execution_architecture_first_difference()`.

Improve the fail-closed diagnostic so a future mismatch reports at least:

- realization kind;
- summary digest;
- reconstructed digest;
- first differing canonical descriptor dimension.

A bounded development/test diagnostic may report the first differing module/parameter/buffer name, structural shape/type, or non-sensitive architecture value. Normal user output SHALL NOT dump model state dictionaries, learned tensors, or whole descriptors.

Diagnostic strengthening must not alter pass/fail semantics.

### G5 — existing-run recovery and non-destructive classification

The stakeholder's completed five TRAIN2 runs are expensive durable evidence and SHALL not be deleted merely because EVAL2 reconstruction failed.

After repair, for each completed run:

1. authenticate materialization/run ancestry;
2. authenticate runtime summary and checkpoint/companion bytes;
3. independently reconstruct the corrected training realization;
4. require exact architecture-digest equality;
5. load raw TRAIN2 state only after equality;
6. verify live/EMA state digests and checkpoint epoch semantics;
7. project through the dependency-native accelerator -> e3nn owner;
8. prove the resulting portable architecture matches the authorized P5 configuration;
9. expose EVAL2 only after all prior steps pass.

Outcomes:

- **representation/reconstruction-only defect:** reuse the completed TRAIN2 artifact and resume EVAL2 with zero retraining;
- **actual method divergence:** keep typed rejection and recompute only the affected run under corrected current authority;
- **ambiguous/stale/corrupt evidence:** fail closed and preserve evidence for diagnosis.

No repair may special-case the stakeholder's observed digest values.

### G6 — focused acceptance

Required focused tests shall use the real owner at every claim boundary. Bounded doubles may control data size or external cost below the owner, but may not replace model construction, accelerator realization, checkpoint authentication, or production routing when those are the claim.

Required cases:

1. **portable parity:** actual pinned-MACE pre-conversion model and independent reconstruction have zero canonical descriptor differences;
2. **CuEq parity:** `enable_cueq=true`, `only_cueq=false` actual TRAIN2 realization and independent realization have identical canonical architecture digest;
3. **real checkpoint authentication:** a real TRAIN2 raw checkpoint and companion authenticate against the reconstructed training realization;
4. **portable round-trip:** authenticated CuEq state projects back to an authorized portable e3nn model;
5. **real EVAL2 forward:** production provider authentication followed by bounded real inference succeeds without architecture/provider override;
6. **negative architecture perturbation:** change at least one true architecture field and prove rejection occurs before state reaches inference;
7. **head/foundation negative:** perturb P5 head/foundation semantics and prove fail-closed rejection;
8. **normalization negative:** perturb frozen `avg_num_neighbors` and prove fail-closed rejection;
9. **realization determinism:** two equivalent independent CuEq realizations agree under the same supported environment, or the work escalates under G2-C;
10. **e3nn regression:** non-accelerated TRAIN2/EVAL2 retains existing behavior;
11. **`only_cueq=true` regression:** preserve current dependency semantics and do not force the phase-separated conversion path where MACE does not use it;
12. **earlier checkpoint / latest companion semantics:** preserve current earlier-boundary versus latest-companion rules;
13. **EMA/live convention:** preserve valid state selection and rejection cases;
14. **failure-path lifetime:** architecture mismatch/conversion failure retires temporary accelerator owners and does not leave model-scale CUDA residency.

### G7 — affected-surface regression

At minimum derive and run the complete affected test surface covering:

- `model_features.py` architecture identity and accelerator conversion/projection;
- P3 realized-MACE architecture tests, because the canonical reconstruction owner is shared;
- P5 post-selection executable configuration and real-owner tests;
- replay/true-label membership and execution identity guards;
- TRAIN2 continuation/recovery and checkpoint authentication;
- EVAL2 provider authentication and bounded direct inference;
- CUDA lifetime / zero-safe admission tests whose preflight classification uses the shared realization owner;
- scheduler TRAIN/EVAL phase separation;
- currentness/restart behavior for completed TRAIN2 pending EVAL2;
- assembled campaign CLI routing.

If the changed owner surface cannot be confidently bounded, run the broader/full available MLFF suite.

Stage-local focused + affected regression SHALL run after each coherent executable stage before dependent executable work proceeds.

### G8 — assembled real-boundary integration

Execute an assembled bounded `campaign cross-validate` route with the real parser/dispatch and production P5 owners:

```text
selected context
 -> P5 materialization
 -> real qualified MACE TRAIN2
 -> durable authenticated TRAIN2 summary/checkpoint
 -> TRAIN scheduler release
 -> serial EVAL2
 -> independent provider authentication
 -> accelerator-state projection if configured
 -> real bounded candidate inference
 -> evidence publication
```

The test must demonstrate restartability at the TRAIN2/EVAL2 boundary: interrupt after authenticated TRAIN2 completion, invoke again, and prove EVAL2 resumes without retraining.

Where CuEq/CUDA is unavailable on the implementation host, CPU/e3nn assembled evidence may close only the non-CUDA routing claims. The exact phase-separated CuEq architecture-parity claim remains unavailable/blocking until run on a supported CuEq environment; do not call a CPU-only substitute equivalent.

### G9 — documentation and dependency-impact closure

If the accepted current product behavior does not change and only D4 is repaired to conform, avoid rewriting architecture/specification merely to narrate the bug.

Update permanent normative documentation only if G2-C establishes a genuine accepted D3 identity-contract change. Otherwise:

- record completed chronology in the appropriate history/release evidence after acceptance;
- update user-facing diagnostics documentation only if the visible error contract materially changes;
- preserve workplan as temporary coordination and archive it after accepted closeout;
- regenerate required PDF/provenance descendants for any permanent Markdown documentation changed under repository policy.

### G10 — final assembled acceptance and review readiness

Before implementation is declared complete:

- reconcile every governing invariant in section 3;
- show G1 classification evidence and why the chosen G2 path is the earliest-owner repair;
- show no forbidden strategy from section 4 was introduced;
- account for every affected path from G7;
- run final affected regression after all material executable edits;
- run assembled real-boundary integration from G8;
- run repository-required lint/type/build/package checks relevant to changed files;
- distinguish unavailable target-hardware qualification from passed functional acceptance;
- perform closeout-learning assessment because this is a demonstrated recurrence;
- request independent SSDP 6.3 review only after implementation acceptance evidence exists.

---

## 8. Acceptance matrix

| Claim | Real semantic owner / required evidence | Insufficient proxy |
|---|---|---|
| independent reconstruction matches actual portable TRAIN2 precursor | pinned MACE construction boundary vs `build_mace_model_from_configuration()` | two mdstats-built models |
| independent CuEq realization matches real TRAIN2 realization | actual pinned-MACE conversion boundary and canonical descriptor | config flag equality only |
| checkpoint belongs to reconstructed realization | `authenticate_train2_checkpoint_provider()` with real checkpoint bytes | state-dict keys/shapes alone |
| portable projection is valid | dependency-native CuEq->e3nn projection plus canonical portable architecture check | loading state directly into portable shell |
| EVAL2 can consume repaired state | production provider authentication + real bounded forward | provider mock / forward override |
| completed runs are reusable | full currentness/ancestry/architecture/state authentication | matching filenames or digest substitution |
| mismatch remains fail-closed | counterfactual true-architecture mutation | happy-path-only test |
| temporary realization is retired | real owner failure/success lifetime observation | `del` statement inspection alone |
| resume does not retrain | assembled interruption after TRAIN2 then rerun | direct helper invocation seeded after decision |

---

## 9. Non-goals

This work does not redesign:

- target-size selection or selected tuple policy;
- CV statistics or acceptance thresholds;
- replay scientific methodology;
- optimizer defaults, epochs, horizons, batch size, gradient accumulation, precision, or loss;
- GPU concurrency/admission policy;
- warning suppression;
- MACE dependency upgrade;
- production LAMMPS/MLIAP qualification;
- general checkpoint-format migration;
- source-foundation DATA6 execution backend policy.

A required change to any of these is a reopen/challenge, not an implementation convenience.

---

## 10. Reopen / Serious Challenge triggers

Raise a bounded D3 Serious Challenge before dependent implementation if any of the following is established:

1. two independently realized CuEq models from exactly the same authenticated portable model/config/environment differ in a canonical descriptor field that genuinely affects execution architecture;
2. the canonical descriptor cannot separate model architecture from legitimate mutable TRAIN2 state without changing accepted architecture-identity semantics;
3. native CuEq->e3nn projection cannot preserve the authorized portable architecture/state semantics required by EVAL2;
4. current accepted P5 architecture simultaneously requires incompatible training-realization and provider-authentication semantics;
5. a correction would require changing scientific/numerical method identity rather than implementation fidelity.

Ordinary missing tests, additional mismatching fields, new sibling call sites, or implementation complexity do not by themselves mint a D3 revision.

---

## 11. Design-review gap closure performed before handoff

A second design pass over the initial diagnosis closed the following gaps before this workplan was published:

1. **Digest mismatch alone was underdetermined.** Added the A-G empirical boundary census and an explicit H1/H2/H3 decision tree; implementation may not assume the converter is at fault.
2. **Descriptor overbinding was previously only a possibility.** Added repeated-equivalent-realization evidence (`D/F`) and a D3 challenge trigger rather than allowing speculative field removal.
3. **Portable reconstruction and CuEq realization could fail independently.** Split their comparison boundaries and repair ownership.
4. **Real TRAIN2 architecture may change between conversion and summary persistence.** Added the `C/E` timing comparison.
5. **Existing five-fold work could be unnecessarily destroyed.** Made non-destructive classification/reuse a binding gate and defined the only condition under which retraining is allowed.
6. **Shared P3 owner risk was missing.** Added P3 realized-architecture regression because `build_mace_model_from_configuration()` is shared.
7. **`only_cueq=true` is semantically distinct.** Added a regression gate so the phase-separated repair is not overgeneralized.
8. **Earlier-checkpoint versus latest-companion semantics could regress.** Added explicit continuation-state coverage.
9. **EMA/live state selection could be accidentally simplified.** Added preservation and negative coverage.
10. **Failure-path CUDA lifetime is coupled to the same transient realization owner.** Added ownership/lifetime regression instead of treating identity repair in isolation.
11. **A green helper test could proxy the real claim.** Added a real-owner evidence matrix and assembled CLI restart test.
12. **Diagnostics already had an unused first-difference helper.** Required wiring/reuse rather than adding a second diagnostic mechanism.
13. **Potential duplicate construction recipes could cause another recurrence.** Added a bounded consolidation pass over recovery/currentness and EVAL2 authentication call sites.
14. **CPU evidence could be overclaimed for CUDA CuEq parity.** Explicitly separated functional control evidence from unavailable target-environment parity evidence.
15. **Documentation churn could falsely promote the bug into architecture authority.** Normative documentation changes are conditional on a genuine D3 change; ordinary D4 conformance repair remains implementation/history work.
16. **Recurrence learning needed closeout.** Added SSDP 6.3 closeout-learning assessment without predeclaring a PEM update; admission depends on evidence after repair.

No remaining known design gap requires expanding D1/D2/D3 authority before implementation. The workplan is intentionally mechanism-neutral until G1 evidence selects the earliest owning repair.

---

## 12. Handoff summary

Implementation should begin at G0/G1, not by editing the failing exception. The guard is currently protecting a real invariant. The first objective is to establish exactly where actual pinned-MACE construction diverges from independent reconstruction and whether the divergence is portable construction, accelerator realization, persistence timing, descriptor semantics, or an actual frozen-method violation.

Prefer reduction, correction, or consolidation of the existing canonical realization owners. Add no compatibility machinery merely to make the observed checkpoint pass. Preserve the five completed stakeholder TRAIN2 runs until the repaired owner can classify them.
