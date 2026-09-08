---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
parent_review_revision: 12
parent_scientific_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
revision: 13
status: reopened
reviewed_implementation_commit: 89c6d9bf5c21236436342043e5afca194b3da4e7
reviewed_implementation_tree: 7d6ebd9ecf6423de0a6dc01448b932a760eda383
post_implementation_documentation_head: d10c643349a646b361357fc3a09372b4fb3306c6
review_verdict: NO-PASS
amended_date: 2026-08-31
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
precedence: revision 13 narrows revision 12 to remaining source/evidence defects and the still-unexecuted real-runtime/final-qualification gates; the frozen parent remains controlling and all non-conflicting revision-10/revision-11/revision-12/base P7 obligations remain binding
---

# P7 revision 13 — implementation review reopen amendment

## 1. Purpose and verdict

Independent Software Design review of the revision-12 repair implementation at executable commit
`89c6d9bf5c21236436342043e5afca194b3da4e7`, tree
`7d6ebd9ecf6423de0a6dc01448b932a760eda383`, is **NO-PASS**.
The later branch head `d10c643349a646b361357fc3a09372b4fb3306c6`
regenerates affected PDFs only and does not change the executable verdict.

Revision 12 genuinely repairs the original LAMMPS bar/GPa and pressure/stress-sign defect and the main deployed per-axis-PBC execution path. It also introduces a useful immutable resource-observation type. Those repairs are retained. The remaining defects are narrower but material: stress capability is scoped and consumed incorrectly, external-reference stress provenance is not authenticated at its source boundary, release-resource evidence is not yet an attempt-wide authenticated closure record, static deployment evidence does not preserve the executed PBC/cell observation, and the public release index does not reauthenticate every object it claims to index. R12-B11 and R12-B12 also remain explicitly unavailable/unexecuted.

The frozen parent workplan remains the scientific and architectural verdict. Revision 13 changes no target-size, CV, production-training, publication-selection, calibration, or locked-test science.

## 2. Accepted revision-12 repairs to preserve

Do not redesign these surfaces unless implementation of the residual repairs produces contradictory evidence:

- **LAMMPS pressure adapter:** `units metal` thermo pressure is treated as bar and converted to canonical ASE/MACE Cauchy stress with pressure-positive-compression -> stress-positive-tension sign reversal in a named source adapter.
- **Named tensor mapping:** LAMMPS thermo components are fetched by name and converted to the canonical symmetric tensor.
- **Per-axis PBC execution:** deployed requests carry a three-axis PBC vector, the worker emits an axis-exact LAMMPS boundary command, and dynamics minimum-image safety honors only periodic axes.
- **Dynamics case identity:** exact PBC participates in dynamics case identity and raw dynamics samples carry cell/PBC.
- **Resource-observation concept:** measured cost is release evidence rather than scientific/model-selection identity; resource pressure may schedule less work or abort but never change scientific membership/thresholds/timestep/precision.
- all revision-11 surfaces that revision 12 already preserved: P5 publication ownership, target-head product identity, exact P7 currentness, reference-bundle descendant identity, reference-relaxed dynamics, resumable one-shot locked activation, explicit reference protocol, canonical analysis ownership, and no downstream fallback/model selection.

## 3. Blocking classification

| ID | Finding | Classification | Closure consequence |
|---|---|---|---|
| R13-B9A | stress capability is one cached decision derived from only the first publication member and deployment-parity policy/cohort, then reused by other members/components | scientific/ownership nonconformance | replace with exact component/member/geometry capability/evidence ownership before stress-bearing evidence can pass |
| R13-B9B | an applicable trained stress channel can still pass deployment/physical qualification when deployed/reference stress is unavailable under default `stress_required=false`; external-reference stress source units/sign/order are not authenticated | scientific fail-open + provenance defect | make availability an evidence requirement, not an operator-controlled escape, and authenticate reference stress at import |
| R13-B7 | resource observations are per invocation rather than cumulative attempt evidence; locked timing and stable scope material are incomplete; selected-device telemetry can be wrong; disk check does not reserve expected write headroom | persistence/resource-evidence nonconformance | implement append/aggregate attempt resource evidence and safe bounded disk admission |
| R13-B13 | static deployed observations do not preserve executed cell/PBC despite revision-12 requiring exact PBC in every deployed static/dynamics observation | audit/identity nonconformance | persist and verify exact static execution geometry/PBC |
| R13-B14 | public release/terminal currentness does not dereference and authenticate the resource observation, and release-index resolution does not reauthenticate its terminal qualification record | release referential-integrity/currentness defect | close the immutable evidence graph at public exposure |
| R12-B11 | real frozen-publication MACE target-head execution in supported LAMMPS remains unavailable on the development host | mandatory real-owner acceptance unavailable | execute on supported target runtime before PASS |
| R12-B12 | final target-machine real-reference qualification + one-shot locked closure has not run | mandatory release qualification absent | execute only after source repairs freeze a final candidate |

Any one of R13-B9A, R13-B9B, R13-B14, R12-B11, or R12-B12 independently blocks P7 closure. R13-B7 and R13-B13 are also binding accepted-contract defects and must close before final qualification evidence is accepted.

## 4. R13-B9A — correct stress capability ownership and identity

### 4.1 Confirmed defect

`QualificationSession.stress_capability()` currently:

1. returns one cached `_stress_capability` once resolved;
2. probes only `self.publication.members[0]`;
3. resolves policy only from `COMPONENT_DEPLOYMENT_PARITY`;
4. derives periodic applicability from only the atom cohort used by the first caller;
5. is later reused by physical qualification even though physical has its own stress policy and different geometries/reference evidence.

That is not the frozen publication/component capability. In a committee, member 0 cannot speak for every member. A deployment M3 probe cannot speak for a physical strain/reference cohort. Deployment policy cannot silently override `[qualification.physical]` policy.

### 4.2 Required end state

Replace the singleton cached capability with an immutable **claim-scoped stress capability/evidence decision**. Exact class decomposition is delegated, but the semantic key must include every dimension that can change the stress claim:

```text
qualification binding
+ component / claim kind
+ exact publication member
+ exact geometry or frozen geometry cohort identity
+ training objective/property policy
+ model/provider stress capability
+ periodic applicability
+ deployed-runtime stress capability when the claim is deployment parity
+ authenticated external-reference stress requirement/availability when the claim is physical/reference comparison
+ component-local frozen stress policy
```

Required rules:

1. Resolve model stress capability for **every publication member** that the component judges. Never infer committee capability from member 0.
2. Resolve periodic applicability from the exact geometry/case being judged, or from a cohort only when every member of that cohort has the same proven applicability. Mixed applicability must be represented explicitly rather than collapsed.
3. Use the policy owned by the component being evaluated. Deployment and physical stress requirements/tolerances may share canonical conversion code but cannot share a cached policy decision merely because both concern stress.
4. Separate **scientific applicability** from **evidence availability**. An available trained stress channel does not become `not_applicable` because a deployment runtime or external reference failed to expose it.
5. A trained/product stress channel that is applicable to a geometry but cannot be observed through a required deployment path is `unavailable/blocking` or rejection according to the frozen component contract; it is never a pass with `stress_unavailable_count > 0`.
6. A physical/reference stress claim that is applicable but whose authenticated reference bundle lacks required stress is waiting/incomplete or a hard invalid-reference failure, never a successful comparison of zero tensors.
7. `stress_required=false` means policy does not add a stress requirement to a genuinely inapplicable product/domain. It does **not** authorize suppressing an applicable trained channel already required by the product capability contract.
8. A `stress_declared_inapplicable_reason` is audit metadata only after the product/domain capability independently resolves inapplicable. It cannot override capability.
9. The exact decision digest(s) must participate in the relevant component-input identity before completed evidence is reused. A capability change must make old deployment/physical stress-bearing evidence unreachable as current without requiring a broader unrelated binding change.
10. `execute_nonlocked_components` must establish any material capability input needed for component identity **before** calling `completed_component()` for that component.

### 4.3 Acceptance

Add executable owner-level tests, not just `StressCapabilityDecision` constructor tests:

- two-member committee: member A reports stress, member B does not; prove the exact frozen committee cannot pass by inheriting A or B's decision globally;
- reverse member ordering and prove verdict/claim semantics are unchanged except for member-identified evidence ordering;
- deployment probe cohort periodic while physical cohort contains an inapplicable geometry, and the inverse; prove no first-call cache leakage;
- set deployment `stress_required=false` and physical `stress_required=true`; prove physical uses its own policy;
- applicable trained stress + deployed runtime reports no stress -> deployment cannot PASS;
- applicable trained stress + one deployed member omits stress -> frozen committee cannot PASS;
- applicable physical stress + authenticated reference bundle omits required stress -> no PASS;
- capability digest change changes the exact relevant component-input digest and prevents stale reuse;
- a truly untrained/inapplicable product remains explicitly `not_applicable` with auditable reasons and no fabricated stress PASS.

## 5. R13-B9B — authenticate external-reference stress provenance

### 5.1 Confirmed gap

`ReferenceObservation.stress_ev_per_angstrom3` is currently treated as already canonical and passed to `canonical_stress_tensor()` with default canonical units/sign/order. `metadata` is arbitrary and neither `write_reference_bundle()` nor `load_reference_bundle()` authenticates source stress units, source sign convention, tensor/Voigt order, or the canonicalization recipe.

Revision 12 explicitly required source metadata to authenticate units/order/sign and conversion exactly once. Geometry/protocol authentication alone cannot detect a DFT/reference adapter that supplied GPa as eV/A^3, pressure-positive-compression as tensile-positive stress, or a different shear order.

### 5.2 Required end state

Define one explicit external-reference stress import contract. Implementation structure is delegated, but it must make these facts machine-checkable and content-bound:

- whether stress is present for the requested geometry;
- source representation kind (Cartesian tensor / named Voigt / supported virial form);
- source units;
- source sign convention;
- source component order when order is relevant;
- volume source when converting an extensive virial;
- canonicalization owner/version;
- resulting canonical symmetric 3x3 eV/A^3 tensile-positive tensor.

Prefer importing raw/source-declared stress through the canonical conversion owner and storing canonical stress plus immutable provenance, rather than asking external producers to silently pre-normalize it.

A reference request whose resolved claim requires stress must say so for the exact applicable geometries. `write_reference_bundle()` and `load_reference_bundle()` must reject an exact-request bundle that omits or misdeclares that required property.

### 5.3 Acceptance

- raw GPa, bar/pressure, canonical eV/A^3, and at least one nonzero-shear ordering fixture normalize to the same expected canonical tensor when their metadata is correct;
- wrong unit declaration, wrong sign declaration, wrong shear order, missing required volume for virial, double canonicalization, and missing required stress fail closed;
- reference bundle digest changes when source stress provenance or canonical stress changes;
- production physical reducer receives only authenticated canonical tensors and never reparses source units/sign/order itself.

## 6. R13-B7 — make resource evidence attempt-wide, auditable, and operationally safe

### 6.1 Confirmed defects

The new `QualificationResourceObservation` is useful, but each new `QualificationSession` constructs a fresh recorder. A waiting-for-reference run followed by resume, or a nonlocked run followed by locked activation, therefore creates separate observations with the same attempt identity while the current terminal record points only at the latest invocation. Earlier measurements remain immutable objects but are not accumulated or linked into the final attempt cost.

The locked-test component is not timed through `record_component()`. The observation stores only `resource_scope_digest`, despite the accepted requirement to record the selected execution topology/scope material. CUDA telemetry always queries device 0 rather than the selected CUDA device. The disk check verifies only `free >= reserve` immediately before a component; it does not account for the bounded amount the component is about to materialize, so a run can start at `reserve + epsilon` and immediately violate the reserve.

### 6.2 Required end state

Use one crash-safe, immutable attempt-wide measurement chain or aggregate record. A suggested low-complexity realization is immutable observation generations with `previous_observation_digest`; another is an immutable invocation-event chain plus deterministic aggregate. The exact representation is delegated, but final release evidence must authenticate the complete attempt history without rewriting prior observations.

Required semantics:

1. Every invocation contributing to one `attempt_identity` either extends the same immutable observation lineage or is deterministically included by the final aggregate.
2. Final total elapsed semantics must be explicit (active execution wall time versus calendar span); per-component timings must include deployment, physical, relaxation, dynamics, calibration, and locked test when executed, with reused components distinguished from newly executed work.
3. Waiting-for-reference -> supplied-reference resume and nonlocked -> locked activation must preserve earlier measurement history in the final release observation/aggregate.
4. Store normalized stable resource-scope material alongside its digest: effective CPU allocation/budget, resolved outer/native thread limits, selected accelerator/device identity where applicable, and the material configured fractions/scope needed to interpret the measurement. Do not make volatile free RAM/disk part of numerical currentness.
5. Accelerator telemetry must query the actually selected device (`cuda:N`/resolved device), not unconditionally device 0.
6. Before materializing bounded owner-local output/scratch, require:

   ```text
   observed free bytes >= configured reserve bytes + conservative required incremental headroom
   ```

   Derive headroom from owner-known artifact/case bounds where practical. Recheck at natural long-run/materialization boundaries. This is P7-local safety only; do not implement global inventory/archive/dedup/admission from the successor storage workplan.
7. Apply the same reserve rule before locked-test materialization/execution if it writes owner-local state.
8. Operational resource failure aborts or reports typed operational failure; it never changes scientific inputs or creates a scientific rejection used for model selection.

### 6.3 Acceptance

- waiting run -> reference supplied -> resumed run -> locked activation produces a final resource observation/aggregate that authenticates all contributing invocation/component timings;
- earlier immutable observation generations remain byte-identical after resume;
- locked component has its own non-placeholder timing when executed;
- resource-scope material reproduces its stored digest and selected device;
- `cuda:1` (or a mocked accepted device-owner equivalent) cannot report device-0 identity/VRAM;
- low-disk fixture with `free = reserve + smaller-than-required-headroom` aborts **before** materialization; merely testing an impossible reserve is insufficient;
- safe headroom passes without changing any scientific identity;
- final target-machine observation carries non-placeholder measured values and complete attempt lineage.

## 7. R13-B13 — complete static PBC/cell execution evidence

Revision 12 correctly sends exact PBC into static and dynamics LAMMPS requests, and dynamics raw samples preserve exact cell/PBC. The static worker result currently returns energy, forces, positions, atom count, and optional stress but not the executed cell/PBC. Consequently the durable deployment-parity evidence cannot independently show that a `[T,T,F]` probe was executed with `[T,T,F]` rather than merely requested that way.

Required repair:

1. Static worker observation must return the exact post-build cell and three-axis PBC vector used for the execution.
2. `deployed_static_observation` / `DeployedEvaluation` or an equivalent typed raw result must carry these fields through the deployment owner.
3. Deployment parity must verify observed cell/PBC against the authenticated requested probe geometry and bind an exact probe-geometry/request identity into component evidence.
4. A mismatch is a hard runtime/lineage error, not a numerical tolerance issue.
5. Keep current axis-exact LAMMPS boundary and dynamics behavior unchanged.

Acceptance must execute the static adapter path for `[T,T,T]`, `[F,F,F]`, `[T,T,F]`, and `[T,F,F]` using a bounded real or faithful below-owner runtime seam, and must prove a returned PBC/cell mismatch fails. Structural greps of request construction alone do not close this claim.

## 8. R13-B14 — close release-evidence referential integrity at public exposure

### 8.1 Confirmed gap

`ProductionQualificationRecord` and `ReleaseEvidenceIndex` now carry `resource_observation_digest`, but `resolve_current_qualification_record()` does not dereference that object or verify its binding/attempt/resource-scope identity. A missing or corrupt resource observation can therefore coexist with a terminal/release object still returned as current.

Likewise, when resolving a `ReleaseEvidenceIndex`, the resolver authenticates component objects named by the index but does not dereference `qualification_record_digest` and prove that the indexed terminal record is present, current, and agrees with the index. That violates the architecture in which `ProductionQualificationRecord` is the single terminal verdict owner and `ReleaseEvidenceIndex` is only an index over it.

### 8.2 Required end state

For terminal/release public currentness resolution:

1. If a terminal/release schema requires `resource_observation_digest`, dereference the immutable resource observation and validate content digest, exact `binding_digest`, exact `attempt_identity`, and exact `resource_scope_digest` against the freshly rebuilt session/binding.
2. A missing/corrupt/mismatched observation makes the terminal/release view non-current or raises hard corruption/lineage error according to existing store semantics. It can never remain current merely because the pointer exists.
3. Resolving a `ReleaseEvidenceIndex` must dereference its `qualification_record_digest`, authenticate the terminal record through the same current binding/plan, and prove agreement for publication/member/executable/spec/environment/plan/verdict/locked activation/predecessor/resource-scope/resource-observation identities.
4. The release index must not become a second terminal authority. It points at and authenticates the single terminal record.
5. Close/reopen after process restart must perform these checks from durable state, not an in-memory recorder/cache.

### 8.3 Acceptance

- delete/corrupt resource observation object -> public terminal/release resolution fails closed;
- substitute resource observation from another attempt/binding/scope -> fails closed;
- delete/corrupt indexed terminal record -> release index cannot resolve current;
- construct an index whose verdict/resource/locked digest disagrees with its terminal record -> fails closed;
- intact record/index/resource graph closes and reopens deterministically.

## 9. R12-B11 — real frozen-publication MACE product execution remains blocking

Revision-12 implementation truthfully exercises an actual frozen publication member through the real mdstats target-head exporter and real `LAMMPS_MLIAP_MACE` builder. Preserve that evidence.

The development host still lacks the ML-IAP message-passing `forward_exchange` interface needed to execute the MACE product. A skipped test is correct evidence of **unavailability**, not PASS.

Closure remains:

```text
actual current P5 publication member bytes
 -> real mdstats target-head deployment export
 -> real LAMMPS_MLIAP_MACE(head=canonical target head)
 -> supported LAMMPS/ML-IAP execution
 -> E/F/stress parity according to the repaired claim-scoped capability contract
```

Bind the exact runtime capability/environment and deployed artifact identity. Do not monkey-patch or emulate the missing product runtime and do not substitute an analytic ML-IAP model.

## 10. R12-B12 — final target-machine / real-reference qualification remains blocking

After sections 4-8 are repaired and fresh affected regression/integration passes, freeze a new executable candidate commit/tree. No executable/runtime change may occur between that freeze and accepted final qualification without invalidating affected evidence.

Final qualification must use:

- exact frozen repaired executable candidate/tree;
- exact current P5 publication and member bytes;
- exact current predecessor reclosure/rebind;
- supported real MACE target-head ML-IAP/LAMMPS runtime;
- explicit real external-reference protocol and authenticated real reference bundle, including the repaired stress provenance contract where stress applies;
- complete claim-scoped stress decisions;
- exact static/dynamics PBC observations;
- complete attempt-wide resource observation lineage;
- successful required nonlocked components;
- explicit one-shot locked activation only after nonlocked closure;
- terminal `ProductionQualificationRecord` and `ReleaseEvidenceIndex` whose entire referenced evidence graph closes/reopens current.

This is production qualification, distinct from regression/integration. It is not replaced by bounded analytic fixtures or a development-host owner-construction test.

## 11. Binding implementation order

```text
R13-P1  claim-scoped/member-scoped stress capability + fail-closed reducer semantics
R13-P2  authenticated external-reference stress import/provenance + stress-required request coverage
R13-P3  attempt-wide resource-observation lineage + selected-device/scope material + bounded disk headroom
R13-P4  static deployed PBC/cell observation and parity verification
R13-P5  terminal/release/resource referential-integrity currentness closure
R13-P6  fresh focused + affected regression/integration, including preserved R11/R12 surfaces
R13-P7  freeze new executable candidate/tree
R13-P8  real current-publication MACE target-head execution on supported runtime
R13-P9  final target-machine real-reference qualification + one-shot locked closure
R13-P10 independent Software Design closure review
```

If a repair changes an accepted P5/P6 predecessor executable owner, follow revision-10 N4: rerun affected predecessor acceptance and publish a new P6 reclosure/rebind before P7 evidence. The currently identified R13 repairs are intended to remain P7-local and should not modify P5 publication semantics.

## 12. Mandatory regression additions

In addition to all still-valid R11/R12 tests, final affected acceptance must include:

### Stress
- two-member heterogeneous stress capability and member-order invariance;
- component-policy separation (deployment vs physical);
- cohort/geometry periodicity separation;
- applicable-but-runtime-unavailable cannot pass;
- applicable-but-reference-missing cannot pass;
- actual component-input invalidation on capability change;
- authenticated external stress unit/sign/shear/virial provenance negatives.

### Resources/persistence
- cumulative waiting->resume->locked resource lineage;
- locked timing;
- selected accelerator identity;
- reserve + required-headroom admission;
- corruption/missing/mismatched resource observation through public resolver;
- release-index -> terminal-record referential integrity.

### PBC
- static observed PBC/cell exactness for full/open/mixed boundaries;
- deliberate static returned-boundary mismatch rejects;
- preserved dynamics mixed-PBC minimum-image and case-identity tests.

### Real-owner/final
- actual frozen publication member in real supported MACE ML-IAP/LAMMPS path;
- exact final target-machine reference + locked assembled run.

After the last executable edit, rerun the complete affected MLFF regression and assembled qualification integration. Existing pre-existing unrelated failures may be attributed only by exact node-ID comparison against a compatible fresh baseline. An unexecuted required real-owner gate remains unavailable/blocking, never PASS.

## 13. Closure gate

P7 may receive independent PASS only when all of the following are true on one final executable candidate:

1. R13-B9A/B9B stress capability/provenance and fail-closed semantics are source- and test-closed;
2. R13-B7 attempt-wide resource evidence and disk-safety semantics are closed;
3. R13-B13 static PBC/cell evidence is closed;
4. R13-B14 release evidence graph closes/reopens with full referential integrity;
5. preserved R11/R12 repaired surfaces remain green under fresh affected regression;
6. R12-B11 actual frozen-publication MACE product execution succeeds on a supported runtime;
7. R12-B12 final target-machine real-reference qualification succeeds;
8. explicit locked activation completes exactly once and is crash/reopen safe;
9. terminal record, release index, resource evidence, component evidence, and external-reference descendants all reauthenticate as current for the same binding;
10. independent Software Design review finds no remaining genuine blocking issue.

Until then P7 remains **REOPENED / NO-PASS**, and `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.
