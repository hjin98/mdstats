---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R10
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
parent_scientific_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
revision: 10
status: planned
amended_date: 2026-08-31
entry_condition: CODE-MLFF-TARGET-SIZE-V7-P6 revision-13 independent acceptance-closure PASS
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
precedence: this amendment overrides prior P7 text only where explicitly stated; the frozen parent scientific workplan remains the controlling verdict and all non-conflicting P7 obligations remain binding
---

# P7 revision 10 amendment — implementation realignment after P1-P6 closure

## 1. Purpose and controlling authority

P7 was designed before the final P1-P6 implementation and therefore contains several assumptions about ownership, publication, persistence, cleanup, and evidence identity that are no longer true on the accepted assembled implementation.

This amendment re-bases P7 on the **implemented and independently accepted P1-P6 state**. It does not change the frozen parent verdict. Where the implementation has already realized a capability that older P7 text proposed to create, P7 must consume the accepted owner instead of creating a second authority. Where P1-P6 intentionally deferred a concern, P7 must not pull the successor concern forward merely because qualification needs to coexist with it.

Authority order for P7 implementation is therefore:

1. the frozen parent `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific and architectural verdict;
2. accepted P1-P6 implementation semantics and their final closure authorities define the actual predecessor product P7 receives;
3. this revision-10 amendment reconciles P7 to that predecessor product;
4. earlier P7 revisions remain binding only where they do not conflict with items 1-3.

Historical workplan/evidence records are not rewritten by this amendment.

## 2. Exact predecessor implementation baseline

P7 entry is satisfied by the final P6 revision-13 independent PASS. The accepted P6 closure identifies:

- executable P1-P6 candidate commit: `f55d59b28c9db890dcb6a3c167a067ef5f37e8a2`;
- executable P1-P6 candidate tree: `e9a6d5f9d1a798f07dab88bd56dafcc73fe0e491`;
- frozen P6 implementation-evidence commit: `82371ecdab5f981255d0853a11477596be2623d3`;
- independent P6 acceptance/closure branch head: `fe78ebf238147f0766c150ca8985fe6dc152d321`.

These identities have different meanings and must not be collapsed:

- the executable commit/tree bind the code actually accepted;
- the evidence commit binds the frozen P6 evidence record;
- the later closure head contains documentary acceptance state and is not a substitute executable identity.

`P6_REVISION_13_COMPLETION_AUTHORITY.md` is the final predecessor closure authority for P7. `P6_REVISION_13_CURRENT_AUTHORITY.md` is preserved historical/interim review state and must not be interpreted as the final P6 verdict.

Plan-only/documentation commits after the accepted executable tree do not, by themselves, make the P1-P6 executable candidate stale. A later source or generated-runtime change that can affect executable behavior does.

## 3. Reconciliation verdict: drifts in the old P7 plan

The following are material plan-to-implementation drifts and are corrected here.

### D1 — duplicate final-publication owner

**Old P7 assumption:** P5 final production stops short of an explicit immutable product boundary, so P7-A must introduce `FinalProductionPublication` as a new canonical owner.

**Implemented P1-P6 state:** P5/P6 already implement and exercise the final-production publication/currentness/reopen/idempotence path. P6 acceptance depends on that real owner path.

**Revision-10 correction:** P7 **must not create a second final-production publication authority**. The accepted current final-production publication is a predecessor input. P7-A becomes publication intake/authentication and qualification binding. If additional qualification-only metadata is required, it must be an immutable descendant binding of the existing publication, never a replacement publication, alternate membership registry, or new selector.

All older P7 text saying to "add", "freeze", or "create" a new `FinalProductionPublication` is overridden to this extent. The scientifically essential rule remains unchanged: qualification opens only after the exact production publication is already frozen, and downstream evidence has zero authority to alter it.

### D2 — qualification was phrased as if it owned fresh production

**Old P7 implication:** the assembled P7 path may appear to include fresh final production as a P7-owned action immediately before qualification.

**Implemented state:** fresh final production, publication, reopen/currentness, and idempotence are already P5/P6 runtime responsibilities.

**Correction:** P7 consumes an existing current published product. P7 may exercise the real predecessor path in bounded integration tests, but production training/materialization/publication remain P1-P6 owners. A P7 target-machine qualification run is read-only with respect to target-size selection, CV, production training, representative-checkpoint/member choice, and publication membership.

### D3 — duplicated storage/cache/cleanup authority

**Old P7/R2 envelope:** P7 anticipated a new publication/qualification persistence boundary while preparing the later storage reset.

**Implemented state:** P6 revisions 10-12 explicitly close the current storage public surface, current-cache owner, and safe-cleanup owner while intentionally keeping the transitional storage system conservative until `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

**Correction:** P7 reuses those current owners and may add only P7-owned immutable qualification evidence plus owner-local attempt state. P7 must not introduce:

- a second cache authority;
- a second safe-cleanup policy engine;
- a global retention registry;
- the successor `StorageInventorySnapshot`/archive/dedup/admission plane;
- a replacement publication registry;
- path-derived semantic classification.

P7 revision 2 remains binding as a storage-neutral handoff, but any wording that could be read as requiring P7 to redesign the already closed P6 storage/cache/cleanup owners is superseded by this correction.

### D4 — candidate identity was underspecified

**Old P7 state:** evidence currentness centers on scientific/publication identities but does not adequately distinguish the executable implementation candidate from later documentary branch heads.

**Correction:** final P7 qualification evidence must bind the exact **P7 executable candidate commit/tree** that ran the qualification, in addition to the exact predecessor final publication and all scientific/runtime identities. Documentary-only workplan/closure commits are not executable currentness inputs. Source/runtime changes are.

The P1-P6 hashes above are entry-baseline anchors only. After P7 implementation, P7 must freeze and record its own executable candidate commit/tree before final target-machine qualification.

### D5 — development qualification could be confused with final-release qualification

**Implemented state:** P6 has bounded device/resource/reference-equivalence qualification used as development evidence, while the frozen parent explicitly defers long GPU/real-production qualification to final release.

**Correction:** no P6 bounded proxy, CI smoke, fake-expensive-owner test, or development-device result can satisfy a P7 target-machine/final-release qualification gate. Such evidence may establish functionality and regression closure only.

## 4. Additionally surfaced issues that P7 must now close

### N1 — qualification must hold exact artifacts stable during long runs

Long target-machine qualification can overlap housekeeping or later operator actions. P7 must ensure the exact publication/model/deployment/reference artifacts used by an active qualification attempt remain available and immutable until the attempt reaches a terminal state or is explicitly aborted.

Use the accepted P6 currentness/safe-cleanup ownership model. A minimal P7 attempt-local **qualification retention reference/pin** is permitted only to express "this exact already-authoritative artifact is actively referenced by this qualification attempt." It is not a cache owner, storage-policy owner, publication owner, or the future global lease system.

Required behavior:

- acquire/reference exact immutable publication artifacts before expensive execution;
- safe cleanup cannot reclaim an actively referenced required artifact;
- release the reference on terminal completion or explicit abort;
- crash/restart reconstructs the reference from authenticated attempt state or fails closed;
- no reference may make a stale publication scientifically current.

If the existing P6 cleanup API cannot safely respect an owner-readable active reference without implementing the successor storage architecture, reopen only this integration surface rather than silently implementing the successor storage reset.

### N2 — target-machine environment is part of qualification identity

P7 makes claims about deployment parity, numerical behavior, runtime stability, and resource behavior. Therefore target-machine evidence must bind a normalized environment fingerprint sufficient to identify the execution environment material to those claims, including as applicable:

- operating-system/kernel and architecture;
- accelerator model and relevant driver/runtime versions;
- MACE/PyTorch/CUDA and supported deployment runtime versions;
- LAMMPS/ML-IAP capability identity when used;
- dtype/precision policy;
- container/environment lock or package-set digest when available;
- CPU/GPU/resource topology material to measured qualification;
- executable P7 commit/tree.

The exact field normalization is delegated, but materially different environments must not silently reuse target-machine evidence.

### N3 — long qualification needs resumable, idempotent attempt identity

A qualification attempt must be keyed by immutable inputs, not by a mutable directory or process lifetime. At minimum the attempt identity descends from:

```text
P7 executable commit/tree
+ exact final-production publication identity/digest
+ qualification-policy/spec identity/digest
+ target-machine environment fingerprint
+ exact evidence/reference-role identities
+ exact deployment/runtime artifact identities as applicable
```

Restart may reuse only authenticated completed component evidence with the same identity. An unchanged publication must not retrigger production training or republish final production.

### N4 — source changes during P7 require explicit reclosure

If P7 implementation or defect repair changes source/generated runtime behavior after evidence was collected:

1. affected evidence is stale for the old executable candidate;
2. run stage-local affected regression/integration;
3. if the change can affect any accepted P1-P6 owner or predecessor product semantics, re-run the affected predecessor acceptance surface and re-close/rebind P6 before using the new candidate for P7;
4. freeze the new P7 executable candidate/tree;
5. re-run affected target-machine qualification.

P7 may not repair predecessor behavior in place while retaining incompatible P6 acceptance evidence.

### N5 — protected/locked evidence must not become a tuning channel

The original no-fallback rule is strengthened for the now-implemented predecessor pipeline. Target-machine, physical, calibration, or locked failures may produce `rejected`, `waiting_for_reference`, or a defect/requalification workflow, but never automatically:

- change `N_selected` or `T_selected`;
- rerun target-size ranking seeking a different answer;
- change paired optimizer seeds/common preparation;
- change CV acceptance to rescue the product;
- select a different production checkpoint/seed/member after qualification evidence is visible;
- loosen thresholds and relabel the same locked evidence as fresh.

A product failure is a release failure for that exact published product. Any scientifically material redesign follows the frozen parent reopen rules; any implementation defect follows repair + regression/reclosure. P7 itself has no retuning authority.

### N6 — qualification evidence needs an immutable release-oriented currentness model

P7 evidence is not reconstructible cache authority. The durable record must identify, at minimum:

- P7 executable candidate commit/tree;
- accepted P6 executable/evidence baseline references;
- exact final-production publication identity/digest and ordered member/artifact identities;
- qualification spec/policy revision and digest;
- normalized environment fingerprint/digest;
- exact external-reference/evidence-role identities where used;
- exact deployment/runtime artifact identities;
- component result identities;
- locked activation identity when applicable;
- timestamps sufficient for audit ordering;
- terminal verdict and typed reason.

A current qualification record is valid only if these identities reauthenticate. Branch tip alone is never currentness authority.

## 5. Revised P7 ownership model

The current owner graph is:

```text
P1-P4 accepted selection authorities
        |
        v
P5 accepted post-selection CV + fresh final production
        |
        v
existing accepted current FinalProductionPublication owner
        |
        |  immutable/read-only to P7
        v
+-------------------------------------+
| P7 QualificationInputBinding        |  optional name; descendant only
| exact publication + exec + env/spec |
+-------------------------------------+
        |
        v
+-------------------------------------+
| ProductionQualificationPlan         |
+-------------------------------------+
   | deployment parity
   | physical/PES + references
   | relaxation/dynamics
   | calibration when applicable
   | explicit one-shot locked activation
   v
immutable component evidence
        |
        v
ProductionQualificationRecord
        |
        v
release-qualified / rejected / waiting
```

`QualificationInputBinding` is a semantic role, not a required class name. It exists only if needed to avoid overloading the predecessor publication with P7-specific executable/environment/spec identities. It has no publication-membership or selection authority.

## 6. Revised implementation gates

### P7-0 — predecessor and executable-baseline rebind gate

Before P7 executable work:

- verify final P6 revision-13 completion authority is PASS;
- bind the accepted P1-P6 executable commit/tree and evidence commit listed in section 2;
- confirm no executable source/runtime change exists between the accepted candidate and the implementation starting point except documented non-executable workplan/evidence changes;
- identify the existing final-publication resolver, currentness owner, post-selection immutable store, current-cache owner, safe-cleanup owner, deployment owner, resource owner, and supported runtime owner;
- record any source-surface change required by P7 that could plausibly alter predecessor behavior so the affected regression/reclosure obligation is known before implementation.

**Gate PASS:** P7 begins from one authenticated accepted predecessor state; no ambiguous "latest HEAD" baseline is used.

### P7-A — consume and authenticate the existing final publication

This gate **replaces the base P7-A instruction to create a new final-publication owner**.

Required end state:

- resolve the exact current predecessor publication through the real accepted owner;
- reauthenticate publication identity, ordered member set, representative checkpoint/model/deployment artifact identities available from the owner graph, and currentness;
- prove close/reopen/idempotence using the existing owner;
- create only a P7 descendant qualification-input binding if P7-specific executable/environment/spec identities need their own immutable record;
- qualification obtains read-only access; no P7 API can mutate publication membership.

If the existing publication lacks a P7-required artifact identity, prefer a descendant binding that authenticates the missing deployable artifact against the immutable publication member. Do not silently widen publication selection semantics.

**Acceptance:** stale/mismatched publication fails; artifact-byte/digest mutation fails; reopen resolves the same product; qualification cannot republish or substitute a member.

### P7-B — deployment and target-machine qualification

The base P7 deployment-parity, physical PES, relaxation, dynamics, and resource obligations remain binding, with these additions:

- execute against the exact frozen P7 executable candidate/tree and exact frozen predecessor publication;
- bind the target-machine environment fingerprint;
- treat P6 bounded proxy/device evidence only as development evidence;
- use existing resource/process ownership; no P7-private scheduler;
- use owner-local resumable attempts and exact component identities;
- acquire/release the minimal active qualification retention reference described in N1;
- collect performance/resource measurements as qualification evidence without changing scientific execution policy in response to pressure.

Target-machine failure rejects or blocks the exact candidate/product according to typed policy. It does not trigger model selection.

### P7-C — protected physical/calibration evidence

The base candidate-independent physical validation and calibration design remains binding. Additionally:

- all plans/memberships/thresholds freeze before observing corresponding product outcomes;
- evidence is read-only with respect to P1-P6 scientific state;
- missing external reference remains `waiting_for_reference`, never synthetic production PASS;
- calibration policy changes invalidate calibration descendants only unless they change an upstream qualification policy identity;
- environment-dependent claims requalify when their material environment identity changes.

### P7-D — explicit locked activation and terminal release verdict

The base one-shot locked-test contract remains binding and is the final scientific evidence gate. Add:

- locked activation binds the exact P7 executable candidate/tree, exact publication digest/member bytes, exact locked cohort identity, exact locked policy, and exact relevant environment/runtime identity;
- a locked failure cannot be repaired by selecting a different already-seen product member under the same locked cohort;
- after locked activation, any new product iteration cannot treat the same revealed cohort as a fresh locked test without an accepted scientific redesign providing new independent evidence.

Terminal `ProductionQualificationRecord` is immutable release evidence for the exact product/candidate/environment/spec combination.

### P7-E — source-change, resume, and requalification closure

Before P7 can receive independent PASS, prove:

- interruption/restart reuses only authenticated same-identity component evidence;
- plan/documentation-only branch changes do not stale executable evidence;
- executable/source/tree change does stale affected executable evidence;
- publication/member digest change stales all descendant qualification;
- material environment-fingerprint change stales environment-bound components;
- qualification-policy change stales only the correct descendants;
- cleanup preserves active referenced artifacts and does not treat a reference as scientific currentness;
- completed/aborted attempts release owner-local retention references;
- requalification never invokes target-size/CV/production reselection as a failure-recovery path.

### P7-F — release evidence and successor-storage handoff

At closure, publish one immutable P7 release-evidence record/index that points to, rather than duplicates:

- accepted predecessor publication identity;
- P7 executable candidate/tree;
- exact qualification plan/spec/environment identities;
- component evidence;
- locked activation/result when required;
- terminal qualification verdict.

This evidence becomes the accepted post-P7 baseline for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

The successor storage workplan consumes P7 owner facts. P7 does not implement the successor storage plane.

## 7. Currentness and invalidation matrix

The following matrix is binding:

| Change | P1-P4 selection | P5 CV | P5 final publication | P7 qualification | Required action |
|---|---|---|---|---|---|
| plan/docs only; executable tree unchanged | unchanged | unchanged | unchanged | unchanged | no scientific requalification |
| P7 qualification-only source change | unchanged unless affected | unchanged unless affected | unchanged unless affected | stale for old P7 executable | affected regression; freeze new P7 candidate; requalify |
| predecessor/runtime source change affecting P1-P6 | potentially stale | potentially stale | stale as dictated by owner DAG | stale | affected predecessor regression + P6 reclosure/rebind, then P7 |
| `N_selected/T_selected` or selected binding changes | stale | stale | stale | stale | follow frozen parent lifecycle |
| CV scientific/policy currentness changes | unchanged if selection unaffected | stale | stale | stale | rerun affected P5 descendants before P7 |
| production policy/member/artifact changes | unchanged | unchanged if scientifically unaffected | stale/new publication | stale | republish through P5 owner, then P7 |
| qualification-only policy changes | unchanged | unchanged | unchanged | affected descendants stale | requalify affected P7 components |
| target-machine material environment changes | unchanged | unchanged | unchanged | environment-bound evidence stale | requalify affected P7 components |
| external reference artifact/protocol changes | unchanged | unchanged | unchanged | affected physical descendants stale | reauthenticate/recompute affected evidence |
| locked evidence already revealed | unchanged | unchanged | unchanged product cannot be rescued through same cohort | terminal historical fact remains | new independent locked evidence requires explicit scientific authority |

## 8. Persistence, storage, cleanup, and resource boundary

P7 persistence follows these rules:

1. reuse the current post-selection/current-generation immutable descendant store when it is the accepted natural owner; otherwise add one clearly P7-owned descendant namespace without duplicating predecessor evidence;
2. immutable evidence is create-once/validate-existing or equivalent crash-safe publication;
3. attempt-local state is identity-derived, resumable, and distinguishable from accepted evidence;
4. terminal evidence is durable release evidence, not reconstructible cache;
5. currentness is owner-derived, never inferred from path/file existence;
6. P6 current-cache and safe-cleanup owners remain the only current general cache/cleanup authorities;
7. the minimal active qualification retention reference is coordination metadata only and cannot evolve into successor storage policy;
8. P7 does not implement global storage inventory, deduplication, archival, cross-owner reclamation, admission control, or I/O optimization.

## 9. Acceptance and regression obligations

### 9.1 Structural / authority acceptance

Prove on final source:

- exactly one final-production publication owner exists;
- P7 is a consumer/descendant of that owner, not an alternate publication authority;
- exactly one current-cache owner and one safe-cleanup owner remain;
- no P7 path can modify `N_selected`, `T_selected`, target-size reducer state, CV acceptance, production member choice, or publication membership;
- no current `SELECT2`/legacy verify fallback or retired target-size/domain lineage reappears;
- successor storage architecture is absent from P7 source except explicit handoff interfaces/documentation;
- locked evidence has no path into training/selection/CV/production or ordinary nonlocked qualification.

### 9.2 Identity/currentness negative tests

At minimum:

1. wrong predecessor publication id/digest -> fail closed;
2. one published model/deployment artifact byte mutation -> fail closed;
3. wrong P7 executable tree identity -> evidence not reusable/current;
4. plan-only branch-head change with executable tree unchanged -> no false staleness;
5. material environment fingerprint mismatch -> affected evidence not reusable;
6. qualification-spec digest mismatch -> affected evidence not reusable;
7. reference protocol/artifact mismatch -> waiting/error as policy dictates, never pass;
8. partial component publication -> never accepted as complete;
9. stale publication remains historical but cannot authorize current qualification;
10. tampered terminal record/component digest -> hard failure.

### 9.3 Resume/cleanup/resource tests

At minimum:

- interrupted same-identity attempt resumes authenticated completed work only;
- changed identity does not reuse old completed work;
- cleanup preserves artifacts referenced by an active qualification attempt;
- terminal completion/explicit abort releases the attempt reference;
- restart after process death restores or safely reconstructs owner-local reference state;
- process/provider/GPU resources are released on success and exception;
- serial vs bounded-concurrent execution yields identical scientific evidence/terminal verdict;
- resource pressure may change scheduling only, never scientific membership/threshold/timestep/precision.

### 9.4 Scientific anti-fallback tests

At minimum:

- publication member A fails while B exists -> reject exact publication; never select B;
- required committee member fails -> reject; never shrink committee;
- target-machine performance or numerical failure cannot call target-size selection/CV/production reselection;
- calibration failure cannot change publication membership or upstream thresholds;
- locked failure cannot trigger fallback/retrain-and-reuse-as-fresh-locked;
- physical validation plan is candidate-independent and frozen before product outcomes.

### 9.5 Regression and integration

Follow Protocol 5 stage-local closure:

- after each material P7 implementation pass, run regression for every modified/affected old module plus new P7 modules;
- run integration across the real parser/dispatch/currentness/persistence/resource owner graph;
- after final source freeze, run fresh affected-surface regression/integration on the exact P7 executable candidate;
- any late source repair invalidates the prior candidate evidence and requires the affected regression again;
- full production qualification is distinct from regression: routine tests prove functionality/absence of hard failures, while the final P7 target-machine run proves the deferred real-production/device claims.

The bounded assembled integration path is now semantically:

```text
real current predecessor state
 -> resolve current selected binding / accepted CV / final production
 -> resolve and authenticate existing final publication
 -> bind P7 executable + qualification spec + environment
 -> qualification run/resume
      -> deployment parity
      -> physical plan/reference/PES
      -> relaxation/dynamics
      -> calibration or explicit not_applicable
 -> close/reopen and authenticate nonlocked evidence
 -> explicit locked activation
 -> immutable terminal qualification verdict
 -> close/reopen and authenticate terminal release evidence
```

The test harness may exercise the real P1-P6 lifecycle to construct a bounded fixture, but P7 does not become the owner of predecessor training/publication.

### 9.6 Final target-machine qualification

P7 cannot receive final independent PASS on proxy evidence alone. Final-release qualification must use the exact frozen P7 executable candidate and exact frozen production publication on the intended target machine/runtime with the real required deployment/runtime path and real external reference evidence where the policy requires it.

Record runtime/performance/resource observations without converting them into adaptive scientific policy. A resource/performance failure is a release failure or engineering repair trigger, not a reason to modify frozen scientific selection behavior inside P7.

## 10. Frozen, delegated, and reopen authority

### Frozen

- the frozen parent scientific verdict is unchanged and remains controlling;
- accepted P1-P6 owners are predecessor authorities, not suggestions for P7 to recreate;
- one existing final-production publication is the immutable product boundary;
- downstream qualification has no selection/fallback authority;
- P6 bounded qualification evidence is development evidence only;
- P7 target-machine evidence binds exact executable, product, policy/spec, environment, and evidence identities;
- current cache/safe cleanup remain P6-owned transitional authorities;
- successor storage reset remains post-P7;
- explicit one-shot locked activation remains mandatory;
- regression/integration and final target-machine qualification are distinct required evidence tiers.

### Delegated

- exact class/module names for P7 descendant bindings, plans, component evidence, terminal release evidence, and attempt-local retention references;
- normalized environment-fingerprint schema, provided it captures all materially claim-relevant runtime/device facts;
- internal batching/concurrency under existing resource owners;
- whether P7 shares the accepted post-selection immutable descendant store or uses a dedicated descendant namespace, provided there is no duplicated current authority;
- exact CLI spelling beneath the already frozen qualification semantic split.

### Reopen only on material evidence

Reopen only the affected P7 surface if:

1. the accepted predecessor final publication cannot authenticate the exact product required for qualification without a new model/member selection rule;
2. a required qualification artifact cannot be bound as an immutable descendant of the existing publication;
3. the accepted P6 safe-cleanup/current-cache interface cannot protect an active qualification artifact without implementing a material part of the successor storage architecture;
4. a required supported deployment/runtime cannot be authenticated against the exact publication bytes;
5. the neutral substrate cannot supply sufficiently independent protected/calibration/locked evidence under the frozen parent statistical design;
6. the one-shot locked contract cannot be enforced by the accepted persistence/currentness model.

Do not reopen P1-P6 merely because their accepted owner graph is less convenient than the pre-implementation P7 design.

## 11. P7 closure gate

P7 is **not PASS** by virtue of this realignment. Revision 10 is the implementation contract for the next executable stage.

Independent P7 PASS requires all of the following on one frozen P7 executable candidate:

- predecessor/P7 authority and identity closure;
- no duplicate publication/cache/cleanup/storage authority;
- stage-local and final affected regression/integration PASS;
- exact publication/currentness/reopen/resume/negative-path PASS;
- target-machine deployment/physical/dynamics/calibration qualification PASS or explicitly policy-allowed `not_applicable` components;
- required external references authenticated and completed rather than proxied;
- one-shot locked activation/result PASS when required by the frozen policy;
- immutable terminal release-evidence close/reopen PASS;
- final source/tree/evidence binding recorded;
- no unresolved parent-workplan requirement or newly surfaced blocker.

Only after independent P7 PASS may the accepted post-P7 commit/tree become the implementation baseline for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.