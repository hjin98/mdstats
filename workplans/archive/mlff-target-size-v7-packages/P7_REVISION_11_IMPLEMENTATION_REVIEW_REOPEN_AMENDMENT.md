---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R11
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
parent_scientific_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
revision: 11
status: reopened
amended_date: 2026-08-31
reviewed_implementation_commit: afe4d690f1f7c084ac33077ecdcb24d67cd14802
reviewed_implementation_tree: ab4c1d32e44585615ba0501fb44d5666afe82190
post_implementation_documentation_head: f86b2de68072394dd189d21c46b8b0d4987a1a7c
review_verdict: NO-PASS
entry_condition: P7 revision-10 implementation exists but has unresolved blocking conformance and closure defects
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
precedence: this amendment reopens and supersedes revision 10 only on the explicit defect surfaces below; the frozen parent scientific workplan remains controlling and every non-conflicting P7 obligation remains binding
---

# P7 revision 11 — implementation-review reopen and closure repair

## 1. Independent review verdict

**NO-PASS. P7 remains open.**

The revision-10 implementation establishes a substantial qualification subsystem and its bounded regression evidence shows meaningful functional progress, but independent source review found multiple requirements whose semantics are either unavailable, incorrectly owned, insufficiently currentness-fenced, or not exercised through the required real owner/runtime path. These are release-meaningful defects, not documentation polish.

The frozen parent scientific verdict is unchanged. This revision does not relax any P1-P7 scientific requirement to accommodate the implementation.

The reviewed executable implementation is commit `afe4d690f1f7c084ac33077ecdcb24d67cd14802`, tree `ab4c1d32e44585615ba0501fb44d5666afe82190`. Commit `f86b2de68072394dd189d21c46b8b0d4987a1a7c` is a documentation/PDF-only successor and does not change the reviewed executable behavior. The previously reported stale-PDF item is therefore **closed** and is not a revision-11 blocker.

The implementation evidence correctly reports that final target-machine qualification has not run and that `single_best_final_seed` is unavailable. Independent review additionally found owner/currentness, deployment-head, reference-lineage, dynamics, locked-restart, and resource-ownership defects described below.

## 2. Review classification

| ID | Finding | Classification | Closure consequence |
|---|---|---|---|
| R11-B1 | `single_best_final_seed` cannot be frozen from accepted predecessor evidence | material P5/P7 reopen trigger; predecessor evidence-owner gap | repair P5 publication decision evidence, then affected P5/P6 reclosure before P7 |
| R11-B2 | deployment uses `head=None`; exact P5 `target_head` is not bound to the deployed artifact | implementation nonconformance / product-identity defect | repair source before any target-machine evidence |
| R11-B3 | current P7 record/release pointers are fenced only by P4 selected binding | currentness/lineage defect | repair P7 current resolver and invalidation tests |
| R11-B4 | external reference bundle content changes do not stale completed physical evidence | descendant identity/restart defect | add component-input identity and immutable reference binding |
| R11-B5 | dynamics starts from original OUTER_MONITOR bases, not authenticated reference-relaxed bases, and omits required diagnostics | scientific conformance defect | repair dynamics plan/input/reduction before qualification |
| R11-B6 | locked activation has an unrecoverable crash window after activation publication | restart/one-shot persistence defect | make activation resume idempotent without re-opening the cohort |
| R11-B7 | P7 concurrency bypasses material parts of the accepted resource-admission owner and deployment artifact creation can race on restart | resource/orchestration defect | integrate stage resource scope and create-once deployment artifact owner |
| R11-B8 | reference protocol may silently default to a placeholder | fail-closed external-evidence defect | require explicit production protocol identity |
| R11-B9 | required stress/deformation parity and response are not represented where stress is applicable | qualification coverage defect | add explicit stress capability/policy/evidence path |
| R11-B10 | topology/geometry helpers duplicate or bypass canonical `mdstats.analysis` owners without proving semantic non-overlap | ownership/algorithm drift | reconcile to canonical analysis owners or prove a narrow adapter boundary |
| R11-B11 | the claimed real deployment smoke does not execute an actual published MACE target-head artifact | proxy-proof acceptance defect | add real MACE -> deployment -> ML-IAP/LAMMPS acceptance or leave unavailable/blocking |
| R11-B12 | final target-machine / real-reference qualification is unexecuted | mandatory closure-evidence absence | run only after source freeze and all prior blockers close |

Repository-wide pre-existing failures are not independently promoted to P7 blockers merely because the suite is not globally green. The implementation evidence reports zero newly failing/erroring node IDs relative to its fresh P6 baseline. Revision 11 nevertheless requires fresh affected-surface and assembled regression after the repairs below, because the source candidate will change.

## 3. R11-B1 — restore the predecessor-owned final publication decision for both committee policies

### Demonstrated defect

Current P5 configuration still accepts both:

```text
all_qualified_final_seeds
single_best_final_seed
```

but `qualification/publication.py` supports only `all_qualified_final_seeds` and deliberately raises for `single_best_final_seed`. This is the exact reopen condition already frozen in P7: qualification may not invent a post-hoc member selection rule when predecessor evidence is insufficient.

P5 final-production run evidence currently stores only digests of the representative EVAL2 record and monitor metric record. The actual representative record and its M3 target metrics are not durably published by the final-production owner, so P7 cannot authenticate a cross-seed pre-qualification ranking.

### Required owner repair

Repair this at the **P5 final-production/publication owner**, not inside P7 qualification.

1. For each completed final-production seed, durably publish the exact already-computed representative EVAL2/admissibility record and the exact M3 target-monitor metric record that selected that seed's representative checkpoint. These records must be immutable descendants of the run plan and must be authenticated on reopen.
2. Add one P5-owned immutable final-publication decision record after all required production seeds complete. The exact class name is delegated, but it must bind:
   - selected binding;
   - final-production plan and policy;
   - accepted CV/method lineage already bound by the final plan;
   - exact frozen M3 membership digest;
   - every required seed's run evidence, representative EVAL2 record, checkpoint SHA, and M3 metric record;
   - committee policy;
   - exact ordered published member set;
   - deterministic decision-policy identity.
3. `all_qualified_final_seeds`: publish every required seed whose already-frozen representative is admissible under the accepted P5 checkpoint policy. Do not use P7 evidence to remove a member later.
4. `single_best_final_seed`: rank only the already-frozen per-seed representatives using the existing P5 target-only EVAL2 ordering semantics (`CheckpointSelectionPolicy` / canonical admissible EVAL2 ordering) over the common frozen M3 development evidence. Seed/tie material must descend deterministically from the final-production plan identity. Choose exactly the first canonical admissible representative. Replay evidence remains admissibility-only and contributes no ranking weight.
5. Do **not** add a new downstream metric, target-size statistic, physical score, locked score, or qualification score to the publication decision.
6. The P5 current final-publication resolver must return the exact decided ordered member set. P7 `AuthenticatedFinalPublication` must consume that owner rather than reconstructing membership from every run.
7. For old completed run roots that lack the newly durable representative records, do not synthesize records from stored digests. Re-evaluate the exact authenticated existing checkpoints on the frozen M3 through the real P5 EVAL2/provider owner, or rerun the affected final-production work when exact deterministic re-evaluation is impossible. Training need not be repeated merely to reconstruct evidence if authenticated immutable run/checkpoint state is sufficient.

### Mandatory predecessor reclosure

This changes an accepted P5/P6 predecessor surface. Therefore:

- run affected P5 semantic/functional acceptance, including both committee policies;
- rerun affected P6 assembled/publication/storage-currentness regression required by revision-10 N4;
- publish a new P6 reclosure/rebind record identifying the new executable predecessor tree before P7 evidence is accepted;
- do not retain the old P6 executable/evidence hashes as if they authenticated the modified predecessor implementation.

### Acceptance

At minimum:

- two or more production seeds with deliberately different M3 target metrics select the canonical best seed under `single_best_final_seed`;
- changing only downstream P7 predictions cannot change the P5 decision;
- replay diagnostics cannot change ranking among admissible representatives;
- tie behavior is deterministic across close/reopen/process order;
- missing/corrupt representative evidence fails closed;
- all-qualified publishes the exact required set; later P7 failure does not shrink it;
- P7 source contains no cross-seed publication ranking logic.

## 4. R11-B2/R11-B11 — bind the canonical P5 target head and prove the actual deployed MACE product

### Demonstrated defect

P5 defines the canonical target fine-tuning head as `target_head` and, for multihead replay, retains a separate replay head. P7 currently calls both deployment export and `LAMMPS_MLIAP_MACE` construction with `head=None`. The primary P7 fixture also substitutes MACE conversion/deployed evaluation, while the separate real-LAMMPS test uses an analytic `MLIAPUnifiedLJ` object rather than an actual P5 MACE publication artifact.

That does not prove the required semantic path:

```text
authenticated P5 publication member
 -> exact target-head export
 -> exact MACE ML-IAP artifact
 -> actual supported LAMMPS/ML-IAP execution
```

### Required repair

1. Extend the authenticated publication-member view/descendant deployment binding to carry the exact canonical P5 `target_head_name` resolved through the accepted P5 method/runtime owner. Do not use a P7-local configurable alias or string fallback.
2. Bind that head identity into the member/deployment descendant digest so wrong-head evidence cannot authenticate as the same product.
3. `QualificationSession.deployed_artifact(...)` must call both the existing mdstats deployment exporter and MACE ML-IAP builder with the exact authenticated target head, never `None` for a multihead-capable product.
4. Reauthenticate the produced deployment artifact SHA before every reuse and make deployed artifact publication create-once/validate-existing or equivalently atomic.
5. Add a negative wrong-head case that creates a valid-looking artifact from the replay/foundation head and proves parity/currentness rejects it.
6. Add bounded owner-level acceptance using an actual MACE checkpoint that represents the P5 multihead-replay topology where the supported MACE/LAMMPS stack is available. The real `mace_deployment` exporter and real `LAMMPS_MLIAP_MACE(..., head=target_head)` owner must execute. An analytic ML-IAP potential proves the LAMMPS process plumbing only; it cannot satisfy this MACE product-path acceptance.
7. If the exact MACE -> ML-IAP path is unavailable on the development host, preserve bounded proxy tests but record the exact owner-level check as unavailable/blocking and execute it in the final target-machine qualification. Do not label the analytic smoke as product-path PASS.

## 5. R11-B3 — make P7 currentness exposure-time exact, not selected-binding-only

### Demonstrated defect

P7 `CampaignStore` pointer keys are selected-binding scoped. The current resolver validates only `selected_binding_digest`. A previous terminal record can therefore remain exposed as the "current verdict" after a qualification-specification, executable, environment, or final-publication change, until a new record happens to overwrite the pointer.

### Required repair

1. Keep the selected-binding-scoped mutable pointer if desired, but treat it only as a locator.
2. Every public/current resolver for qualification plan, terminal record, and release-evidence index must re-establish a **current `QualificationInputBinding`** at exposure time and validate the located object against it.
3. At minimum reauthenticate:
   - selected binding;
   - exact predecessor publication digest and ordered member digest;
   - exact current P7 executable identity;
   - exact qualification specification identity;
   - material environment identity;
   - plan digest for terminal/release objects;
   - referenced component digests and immutable store objects.
4. Mismatch means stale/historical, never current. Return a typed stale state or `None` according to the existing public API convention; corruption/tampering remains a hard error.
5. `qualification status` must never print an old `release_qualified` record as current after a current binding change.
6. The successor storage handoff must use the same real current resolver rather than reading pointer/file presence directly.
7. Locked disclosure history is special. The system must retain enough immutable cohort-generation activation history to prevent a revealed cohort from becoming fresh after an otherwise-staling P7 change. Do not erase one-shot history merely because the current product binding moved.

### Acceptance

Before publishing any new P7 record, independently change each of: qualification-only spec, P7 executable source digest, material environment identity, production publication/member identity. The old terminal/release record must be historical and not current. A documentation-only commit with unchanged executable source must not stale it.

## 6. R11-B4 — bind exact external-reference content to the components that consume it

### Demonstrated defect

The reference request is immutable, but `reference-bundle.json` is mutable and its actual observation content is not part of the top-level attempt identity. Completed PES/relaxation evidence is reused by `binding_digest` alone, even though its payload records the old reference-bundle digest. Replacing a same-request/same-protocol bundle can therefore leave old physical evidence reusable.

### Required repair

Preserve the useful property that a waiting attempt can receive references without invalidating deployment work. Therefore do **not** put mutable reference-bundle content into the global attempt identity merely to solve this problem.

Instead:

1. Introduce an immutable authenticated reference-bundle publication/binding. A supplied bundle must receive a content digest over the exact request, protocol, observations, relaxed coordinates, stress when present, and any required reference metadata.
2. Position/component reuse must be keyed by a component-input identity rather than only the global P7 binding. For every reference-dependent component, that identity must include the exact reference request digest and exact authenticated bundle digest.
3. Physical PES and relaxation are reference-dependent. Dynamics becomes reference-dependent under R11-B5 because its initial state is the matched reference-relaxed geometry.
4. Deployment parity and calibration remain reference-bundle-independent and may be reused when only the external bundle changes.
5. Do not overwrite an immutable old component-position record. Either include component-input identity in the position key/path or maintain an immutable generation index so old evidence remains historical while the current dependency resolves to new evidence.
6. Replacing or superseding a reference bundle under the same protocol/request must stale only the affected physical descendants, exactly as the frozen invalidation DAG requires.
7. A corrupt/partial/wrong-protocol bundle remains a hard lineage failure; absence remains `waiting_for_reference`.

### Acceptance

Run physical evidence against bundle A, replace/supersede with authenticated bundle B for the same request, and reopen. Deployment evidence may reuse; PES/relaxation/dynamics must not reuse A evidence. Old A evidence remains immutable historical evidence.

## 7. R11-B5 — correct dynamics inputs and complete the frozen physical diagnostics

### Demonstrated defect

Current dynamics starts each case from the original OUTER_MONITOR frame. The base P7 contract requires dynamics on the frozen authenticated **DFT/reference-relaxed base**. Current dynamics also checks only final broken bonds, one NVT terminal-temperature comparison, energy drift, minimum pair distance, and maximum force. It does not implement the required NVE-temperature behavior, persistent protected-topology damage, or protected-group displacement/bond/angle degradation.

### Required input repair

1. `qualify_dynamics` must consume the exact authenticated reference bundle.
2. For every physical base, resolve its matched `RELAXED_MODE` reference observation and construct the initial dynamics geometry using the authenticated `relaxed_positions_angstrom` on the same atom/cell identity.
3. Missing matched relaxed coordinates means `waiting_for_reference`/lineage failure as appropriate; never silently fall back to the original OUTER_MONITOR coordinates.
4. Case identity/component-input identity must bind the reference-bundle digest and the exact initial relaxed-geometry identity.

### Required raw observations and reduction

The runtime worker should return raw deterministic observations sufficient for the reducer to decide policy; the worker must not make scientific acceptance decisions. At required sampling points record, as applicable:

- NVT and NVE temperatures;
- energy components;
- positions or a lossless deterministic geometry representation sufficient for topology/displacement/bond/angle calculation;
- forces or maximum-force statistic under an authenticated raw definition;
- cell/periodic identity when needed.

The P7 reducer must then implement, under specification fields frozen before execution:

- NVT stabilization/tolerance;
- finite NVE temperature behavior and a predeclared NVE temperature tolerance/range rule;
- NVE energy drift per atom/time;
- minimum pair-distance and maximum-force hard safety bounds;
- protected topology/bond damage persistence, not a single noisy sample;
- protected-group displacement degradation;
- bond error/degradation;
- angle error/degradation;
- all-required-case semantics.

Define a deterministic persistence rule in the qualification specification (for example, a configured minimum consecutive sampled violations or equivalent predeclared rule). Do not choose the persistence threshold after observing a trajectory.

### Canonical topology/geometry owner reconciliation

`qualification.geometry` currently builds its own covalent-radius bond graph and angle table. The repository already exposes canonical `mdstats.analysis` atomic-connectivity, bond-angle, framework-topology, and periodic geometry owners. Before retaining local algorithms:

1. map the qualification's protected topology requirement onto the applicable existing `mdstats.analysis` owner(s);
2. use the canonical owner directly when it represents the same observable;
3. if a narrow single-configuration adapter is genuinely required, make it an adapter over canonical definitions/periodic geometry rather than a second scientific connectivity definition;
4. document and test the semantic boundary if a local helper remains.

The protected topology must be the configured/authoritative structure to preserve, not merely whichever whole-system covalent-radius edges happen to exist in one final frame.

### Acceptance

At minimum prove:

- case starts exactly from authenticated reference-relaxed coordinates;
- bundle change changes the dynamics dependency identity;
- missing relaxed reference cannot pass dynamics;
- transient one-sample geometric noise below the frozen persistence rule does not masquerade as persistent damage;
- persistent protected bond/topology damage rejects;
- displacement/bond/angle degradation independently rejects when its frozen threshold fails;
- nonfinite or out-of-policy NVE temperature rejects;
- serial/concurrent execution produces the same case/reduction evidence.

## 8. R11-B6 — make locked activation crash-resumable while preserving one-shot semantics

### Demonstrated defect

The activation record is durably published before locked predictions/component evidence. Any crash in that interval leaves a same-cohort activation that every later `activate-locked` call rejects as "already activated". No current path can finish the exact already-opened locked test.

### Required state machine

Treat activation as an irreversible **open event**, not as proof the locked evaluation completed.

1. On first activation after all prerequisites pass, durably publish exactly one immutable activation record.
2. If that exact activation already exists and locked component evidence is absent, `activate-locked` must **resume the already-open activation** using the same activation identity/timestamp/cohort. It must not create a second activation or claim the cohort is fresh.
3. If locked component evidence exists but terminal record/release index is missing, reauthenticate the component and complete reduction/publication without rerunning or reopening the cohort.
4. Only when a valid terminal locked result is already complete does a second activation command reject as a duplicate terminal activation.
5. If the cohort was revealed under an older/stale product/policy identity, preserve the historical reveal and fail closed; do not treat it as a fresh cohort for a new product.
6. Acquire/reconstruct the P7 attempt retention reference before activation-path prerequisite work and keep it through terminal publication. Release it only on terminal close or explicit abort under the already-defined retention semantics.

### Crash acceptance

Inject interruption at least:

- immediately after activation publication;
- after locked component publication;
- after terminal record publication but before release-index publication;
- after release-index publication but before retention-reference release.

Every restart must converge to one activation identity and one terminal result. A truly terminal second activation remains rejected.

## 9. R11-B7 — use the accepted resource owner and eliminate deployment-artifact races

### Demonstrated defect

P7 case parallelism currently caps only by `available_cpu_threads()`. The accepted `resources` owner already provides campaign CPU fractions, RAM budget, GPU/VRAM observations, worker resolution, and nested-thread stage scopes. P7 therefore bypasses material resource-admission semantics it was required to reuse.

In addition, the in-memory deployed-artifact cache is not a synchronization primitive. On restart, deployment parity may already be durable while concurrent dynamics cases for the same member race to create the same deployment artifact path.

### Required repair

1. Resolve one P7 execution-only `SystemResourceSnapshot` / `StageResourceScope` through the accepted resource owner for each material parallel stage.
2. Derive case worker count through `resolve_worker_count` or an equivalent accepted owner path, honoring campaign CPU fraction and RAM estimates; apply existing nested BLAS/OpenMP/PyTorch thread limiting where applicable.
3. GPU/VRAM materialization/execution must respect the accepted selected-device and memory-budget owner where GPU work is used. Runtime pressure may reduce concurrency only; it may not alter temperatures, timesteps, duration, precision, membership, or thresholds.
4. Do not introduce the post-P7 storage/admission subsystem. If no current P6 owner defines cross-owner disk admission, record disk usage/availability in release observations and keep owner-local scratch bounded rather than inventing successor storage policy.
5. Prebuild/re-authenticate each member's deployment artifact before launching same-member concurrent dynamics, or protect create-once publication with an owner-level per-member lock/atomic create-or-verify protocol.
6. Artifact reuse after process restart must authenticate source member/checkpoint/head/dtype/export/runtime identity and bytes, not rely on an in-memory cache hit.
7. Bind stable resource topology/scope material to any performance/resource qualification claim. Volatile free-memory values need not make numerical evidence stale, but materially different CPU allocation/affinity/quota, selected accelerator/model/total VRAM, resource fractions, or execution scope must not silently reuse a performance/resource claim. This may be a separate release-resource identity if keeping the numerical environment digest capacity-neutral is desirable.

### Acceptance

- resource pressure reduces worker count without changing scientific identities;
- nested worker counts stay within accepted stage budget;
- resume with deployment-parity already complete and an empty in-memory cache, then launch concurrent dynamics: exactly one authenticated artifact per member is used and no race/partial artifact is observable;
- serial/concurrent evidence is identical;
- materially different resource scope cannot reuse a resource/performance claim as if it were the same target-machine evidence.

## 10. R11-B8 — external reference protocol must be explicit for production qualification

`external-reference-protocol-unset` is a placeholder, not an authenticated scientific protocol.

When any required component consumes external PES/relaxation reference evidence:

- require an explicit non-placeholder `[qualification.reference].protocol` before publishing a production reference request;
- fail closed before expensive physical qualification if it is absent;
- bind the protocol identity to the request and authenticated bundle as already intended;
- bounded analytic test fixtures may use an explicit fixture protocol identity, but production release evidence must identify the real reference method/protocol and artifact provenance.

No matching bundle may turn an unset placeholder into a valid release claim.

## 11. R11-B9 — implement stress/deformation evidence where stress is applicable

The base P7 contract requires deployment E/F/**stress when available** and physical stress/strain response where applicable. Current deployed evaluation and external-reference observation schemas contain only energy/forces (plus relaxed coordinates), and the strain path checks only energy curvature.

Required repair:

1. Resolve, before execution, whether stress is scientifically applicable from the accepted training/model/reference capability and qualification policy.
2. Add optional-but-authenticated stress to provider/deployed/reference observation types and their content identities.
3. For periodic configurations where both the product/reference path supports stress and policy requires it, compare in-framework vs deployed stress under a frozen tolerance and evaluate stress/strain response against the authenticated external reference.
4. Normalize tensor ordering, sign/virial convention, units, and periodic cell volume through one documented canonical conversion owner; add analytic/reference tests for the conversion.
5. If the supported runtime genuinely cannot expose stress for a configuration/product where stress is not required, record explicit capability unavailability rather than silently claiming stress parity. If stress is required by the resolved product/specification, unavailability is blocking.
6. Bind stress applicability and thresholds into the qualification specification digest.

## 12. R11-B10 — ownership reconciliation for physical geometry/topology

The implementation must perform a focused ownership pass over `qualification.geometry`, `relaxation`, `physical`, and `dynamics` against current `mdstats.analysis` capabilities, especially:

- `atomic_connectivity`;
- `bond_angle`;
- `framework_topology` where framework/protected-role semantics apply;
- periodic displacement/neighbor owners.

For each local helper, classify it as:

```text
adapter to canonical owner
new numerical observable with no existing owner
duplicate owner (must be removed/refactored)
```

Do not preserve a duplicate merely because the current bounded tests pass. Add a source/architecture test or documentation assertion sufficient to keep the chosen owner boundary explicit.

## 13. R11-B12 — final target-machine qualification remains a hard final gate

Do not run the one-shot locked test or claim final qualification on the reviewed `afe4d690...` candidate. The executable candidate will change during revision-11 repair.

After B1-B11 are semantically and functionally closed:

1. complete required P5/P6 predecessor reclosure and bind its new accepted executable/evidence identities;
2. freeze one final P7 executable source tree/commit;
3. run fresh affected-surface regression/integration on exactly that candidate;
4. construct/resolve the exact frozen final-production publication through the repaired P5 owner;
5. execute real deployment parity through actual target-head MACE export and supported ML-IAP/LAMMPS runtime on the intended target machine;
6. supply/authenticate real external reference evidence under the explicit frozen protocol;
7. execute PES, reference-relaxed relaxation/dynamics, and calibration under the exact frozen P7 spec/environment/resource scope;
8. close/reopen and authenticate all nonlocked evidence;
9. only then explicitly activate the reserved locked test once;
10. publish and close/reopen the immutable terminal qualification record/release index;
11. record exact final executable commit/tree/source digest, predecessor reclosure identities, publication/member digests, environment/resource identity, reference bundle/protocol identities, component evidence, locked activation, and terminal verdict.

Any source/runtime repair after step 2 invalidates affected target-machine evidence and requires the revision-10 source-change/requalification rule.

## 14. Required implementation order

The repair order is binding because later evidence depends on earlier owner identity:

```text
R11-P1  P5 final-publication decision + both committee policies
  -> affected P5 acceptance
  -> P6 reclosure/rebind
R11-P2  P7 publication intake + target-head deployment binding
R11-P3  exact P7 currentness + component-input/reference identity
R11-P4  reference-relaxed dynamics + complete diagnostics + canonical topology ownership
R11-P5  locked activation crash/restart closure
R11-P6  resource-scope/admission + race-free deployment artifact reuse
R11-P7  explicit reference protocol + stress capability/evidence completion
R11-P8  fresh structural/negative/concurrency/restart regression
R11-P9  bounded real MACE target-head ML-IAP/LAMMPS owner acceptance
R11-P10 freeze executable candidate
R11-P11 final target-machine + real-reference qualification
R11-P12 independent closure review
```

If a later stage changes source covered by an earlier accepted stage, rerun the affected earlier regression rather than relying on stale evidence.

## 15. Mandatory regression/acceptance matrix

The existing revision-10 tests remain binding. Add at minimum:

### Publication / predecessor
- both committee policies with >=2 seeds;
- canonical single-best ordering and deterministic tie;
- missing/corrupt durable representative evidence;
- all-qualified member failure does not shrink publication;
- P5/P6 close/reopen after new publication decision.

### Deployment
- canonical target head reaches both export and ML-IAP builder;
- wrong replay/foundation head rejects;
- artifact byte mutation rejects;
- dtype mismatch rejects;
- actual bounded MACE multihead -> target-head -> ML-IAP/LAMMPS execution;
- stress parity when applicable.

### Currentness / identity
- spec-only stale before republishing;
- executable-source stale;
- environment-material stale;
- publication/member stale;
- documentation-only non-stale;
- release index and terminal record both enforce exact current binding;
- historical locked reveal remains non-reusable after currentness changes.

### References
- waiting -> supply reference reuses unrelated deployment evidence;
- bundle A -> bundle B stales only reference-dependent descendants;
- wrong protocol/request/geometry/count/stress convention rejects;
- placeholder protocol cannot begin required production reference qualification.

### Dynamics / physical
- exact reference-relaxed start coordinates;
- missing reference cannot run/pass dynamics;
- NVT and NVE temperature failures;
- energy drift;
- minimum distance / maximum force;
- transient versus persistent topology damage;
- bond, angle, displacement degradation independently;
- serial/concurrent equivalence;
- canonical topology owner equivalence/adaptation.

### Locked restart
- crash after activation;
- crash after locked evidence;
- crash after terminal record;
- crash before retention release;
- one activation identity after every resume;
- terminal second activation rejected.

### Resources / orchestration
- CPU/RAM worker reduction through accepted resource owner;
- nested thread budget;
- GPU/VRAM scope where affected;
- restart concurrent deployment artifact race;
- process/provider cleanup on exception.

### Final assembled integration

Run through the real public parser/dispatch and current owners:

```text
prepare
 -> select-target-size
 -> cross-validate
 -> train-production
 -> P5 final-publication decision
 -> P7 resolve/authenticate exact publication + target head
 -> qualification run
      -> exact MACE deployment parity
      -> reference request/import
      -> local PES + stress/strain when applicable
      -> relaxation
      -> reference-relaxed dynamics
      -> calibration/not_applicable as frozen policy permits
 -> close/reopen exact current nonlocked evidence
 -> explicit locked activation
 -> close/reopen terminal release evidence
```

Routine integration may continue to fake expensive MACE/DFT work only below accepted owners. It may not claim the real MACE deployment owner/path is proven by an analytic ML-IAP substitute.

## 16. Non-blocking / retired review items

- The stale generated PDFs reported by the implementation evidence were regenerated in documentation-only commit `f86b2de68072394dd189d21c46b8b0d4987a1a7c`; this item is closed.
- Pre-existing repository-wide failures/errors are not by themselves a P7 defect when the fresh baseline comparison proves no new affected failure. They remain repository health debt and must not be used to waive targeted regression.
- The post-P7 storage reset remains outside P7. Revision 11 must not introduce `StorageInventorySnapshot`, archive-v2, global dedup/reclamation/admission, or another cache/safe-cleanup authority.

## 17. Revision-11 closure gate

P7 may return to independent closure review only when one frozen candidate demonstrates all of the following:

- R11-B1 through R11-B11 source/design repairs are implemented and accepted;
- P5/P6 predecessor reclosure is complete after the publication-owner repair;
- no duplicate P7 publication/cache/cleanup/storage or physical-analysis authority remains;
- exact target-head deployment identity and actual MACE deployed-runtime path are proven;
- P7 public/current record/release resolvers reauthenticate the exact current P7 binding;
- reference-bundle changes invalidate only their correct descendants;
- dynamics consumes authenticated reference-relaxed bases and satisfies the complete frozen diagnostic policy;
- locked activation is crash-resumable yet permanently one-shot;
- accepted resource owners bound concurrency/material execution and deployed-artifact publication is race-safe;
- explicit production reference protocol and stress semantics are fail-closed;
- fresh affected regression/integration passes on the final source candidate;
- final target-machine real-reference qualification passes on that exact candidate/product/environment, with only explicitly policy-allowed `not_applicable` components;
- one-shot locked result and immutable terminal release evidence close/reopen exactly;
- implementation evidence records exact final source/tree/predecessor/publication/environment/reference/component/locked identities;
- an independent final design review finds no remaining parent/P7 blocker.

Until that gate is satisfied, **P7 is REOPENED / NO-PASS** and `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.