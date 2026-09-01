---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R12
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
parent_review_revision: 11
parent_scientific_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
revision: 12
status: reopened
reviewed_implementation_commit: d24c16cecfd25f2dfcd83b10e0850981d5b64318
reviewed_implementation_tree: 2a01d92197ae4663fc7fc789ddb0aa21a97cdb4e
post_implementation_documentation_head: 4f8b624acedf23c0cf15a59ba5d7994336dc9755
review_verdict: NO-PASS
amended_date: 2026-08-31
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
precedence: revision 12 narrows revision 11 to residual and newly surfaced blocking repairs; the frozen parent remains controlling and all non-conflicting revision-10/revision-11/base P7 obligations remain binding
---

# P7 revision 12 — final implementation review reopen amendment

## 1. Purpose and verdict

Independent review of the revision-11 repair implementation at executable commit
`d24c16cecfd25f2dfcd83b10e0850981d5b64318`, tree
`2a01d92197ae4663fc7fc789ddb0aa21a97cdb4e`, is **NO-PASS**.
The later branch commit `4f8b624acedf23c0cf15a59ba5d7994336dc9755`
regenerates documentation PDFs only and does not change the executable review
verdict.

Revision 11 materially repaired most of the original defects. This amendment is
therefore deliberately narrow: it does not reopen already-conformant P7/P5
surfaces merely because final release qualification remains outstanding.

The frozen parent
`MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md`
remains the scientific and architectural verdict. Revision 12 changes no target
size, CV, production-training, publication-selection, calibration, or locked-test
science.

## 2. Revision-11 closure classification

Source review of the repaired owner graph finds the following revision-11
surfaces conformant, subject to ordinary regression after the remaining source
repairs:

- **R11-B1 PASS at source/design level:** P5 now owns a durable final-production
  publication decision, supports both `all_qualified_final_seeds` and
  `single_best_final_seed`, persists the pre-qualification representative/M3
  evidence required to decide them, and P7 consumes rather than ranks members.
- **R11-B2 PASS except for the real-runtime portion carried forward as B11:** the
  canonical P5 `target_head` is now publication/member/deployment identity and is
  passed to both the real mdstats deployment exporter and
  `LAMMPS_MLIAP_MACE` builder.
- **R11-B3 PASS:** public current plan/verdict/release resolution rebuilds and
  validates the exact current P7 binding rather than trusting the selected-binding
  pointer as authority.
- **R11-B4 PASS:** reference-dependent component-input identity contains the exact
  immutable authenticated reference-bundle content; bundle replacement stales
  only the correct descendants.
- **R11-B5 PASS for the repaired reference-relaxed dynamics architecture and
  diagnostic vocabulary**, subject to the mixed-periodicity repair in section 5.
- **R11-B6 PASS:** locked disclosure is append-only and an opened-but-incomplete
  activation resumes onto the same activation identity rather than reopening the
  cohort.
- **R11-B8 PASS:** production reference-dependent qualification rejects an absent
  or placeholder reference-protocol identity.
- **R11-B10 PASS:** qualification connectivity/minimum-image operations now route
  through canonical `mdstats.analysis` owners where equivalent semantics exist,
  with narrow qualification adapters only where the analysis API aggregates away
  identity required by P7.

The affected P5/P6 repair is accepted as the predecessor implementation surface
for continuing P7 repair only after its existing affected regression/reclosure
checks remain green on the final repaired source candidate. The old revision-13
P6 executable hashes remain historical anchors, not authenticators of the new
predecessor source tree.

## 3. Residual blocking classification

| ID | Blocking finding | Consequence |
|---|---|---|
| R12-B7 | resource-scope scheduling is repaired, but required disk admission/availability and measured target-machine performance/resource observations are not represented in release evidence | implement owner-local disk safety plus immutable resource observations before final qualification |
| R12-B9 | stress qualification is not scientifically closed: LAMMPS `units metal` pressure is read in bar but converted as GPa, the LAMMPS pressure-to-ASE/MACE sign boundary is not fixed correctly, and `stress_applicable` is still primarily an operator boolean rather than a capability decision | repair canonical stress capability/conversion/evidence before any real target-machine stress claim |
| R12-B13 | deployed static/dynamics requests collapse the three-axis PBC vector to one Boolean, so mixed periodicity such as `[T,T,F]` is silently executed as fully nonperiodic | preserve exact per-axis boundary conditions or fail closed |
| R12-B11 | actual MACE target-head artifact construction is exercised, but this development host cannot execute that MACE ML-IAP product in LAMMPS because the installed ML-IAP Python data object lacks the message-passing exchange interface | remains unavailable/blocking until exercised on a supported runtime |
| R12-B12 | mandatory final target-machine qualification on one frozen repaired executable/publication with real external reference evidence and one-shot locked closure has not run | P7 cannot receive independent PASS |

Any one of B9, B13, B11, or B12 is independently sufficient to block P7 closure.
B7 is also a binding revision-10/revision-11 release-evidence obligation and must
be closed before the final target-machine run can serve as production
qualification evidence.

## 4. R12-B9 — repair the stress capability and canonical LAMMPS boundary

### 4.1 Confirmed implementation defect

`qualification/_lammps_worker.py` obtains `pxx`, `pyy`, `pzz`, `pxy`, `pxz`, and
`pyz` from LAMMPS while running `units metal`. Those thermo quantities are
**pressure in bar**. The current implementation passes the numeric values to
`canonical_stress_tensor(..., units="gpa", ...)`, producing a factor-10,000 unit
error before any tolerance is applied.

In addition, the repository's canonical label contract is ASE/MACE Cauchy stress.
ASE stress is positive in tension while pressure is positive in compression.
The LAMMPS thermo-pressure adapter therefore owns a source-convention sign
conversion; a default operator value of `+1` must not silently redefine the
canonical scientific sign.

### 4.2 Required end state

Implement one source-specific conversion boundary for LAMMPS thermo pressure:

```text
LAMMPS thermo pxx/pyy/pzz/pxy/pxz/pyz
  source units = bar under `units metal`
  source semantic = pressure, positive compression
        |
        v
canonical ASE/MACE symmetric Cauchy stress
  units = eV / Angstrom^3
  sign = positive tension
  explicit tensor ordering
```

Required rules:

1. The worker/conversion owner must treat LAMMPS thermo pressure as `bar`, never
   GPa. Do not infer source units from a target-output unit setting.
2. Pressure-to-stress sign conversion must be fixed by the documented source and
   canonical conventions. Prefer a named source adapter such as
   `canonical_stress_from_lammps_metal_pressure`; if a generic sign parameter is
   retained internally, the LAMMPS adapter must supply the scientifically fixed
   pressure-to-ASE/MACE sign rather than an arbitrary user-tunable default.
3. Named tensor components must be mapped explicitly. Include nonzero shear in
   acceptance so `xy/xz/yz` ordering errors cannot hide behind diagonal tests.
4. Canonical output remains a symmetric `3x3` eV/Angstrom^3 tensor. The
   deployment, provider, and external-reference paths must compare the same
   convention.
5. Remove `stress_applicable = false` as a sufficient operator mechanism for
   suppressing an actually available stress channel. Before component execution,
   resolve a **stress capability decision** (exact class name delegated) from the
   accepted product/training/reference/runtime capability plus frozen
   qualification policy.
6. A policy may require stress and may explicitly declare a scientifically
   justified inapplicable channel, but it may not relabel an available trained
   stress channel as `not_applicable` merely to avoid qualification. At minimum,
   the decision must consider the accepted training-objective/property policy,
   target/reference stress-label availability, published model/provider stress
   support, periodic applicability, and deployment/runtime stress capability.
7. The capability decision and its reasons must be immutable identity/evidence
   bound to the qualification specification/binding or exact component input.
   Capability changes must stale affected stress-bearing descendants.
8. Reference metadata must continue to authenticate source units/order/sign and
   canonicalize them exactly once; no double sign/unit conversion is permitted.

### 4.3 Acceptance

Add owner-level tests that fail on the current defect:

- feed known LAMMPS `metal` pressure values in **bar**, including nonzero shear,
  through the production source adapter and compare to the analytically expected
  eV/Angstrom^3 ASE/MACE stress tensor;
- prove positive compression in LAMMPS maps to negative diagonal tensile stress
  under the canonical convention;
- prove a deliberate `bar -> GPa` misclassification differs by 10,000 and is
  rejected by the test;
- run deployment parity with a nonzero-stress bounded model/deployed observation
  so stress is actually compared rather than merely marked unavailable;
- positive case: capability resolves applicable and correct stress passes;
- negative cases: wrong unit, wrong sign, wrong shear order, missing required
  product stress, missing required reference stress, or wrong runtime stress
  capability fail closed;
- explicit truly inapplicable case remains auditable and does not fabricate a
  stress pass.

## 5. R12-B13 — preserve exact per-axis periodic boundary conditions

### 5.1 Confirmed drift

The current deployed static and dynamics requests reduce `atoms.get_pbc()` to
`bool(np.all(...))`. The LAMMPS worker consequently chooses only `boundary p p p`
or `boundary f f f`. A valid mixed-boundary configuration such as `[True, True,
False]` is silently changed into a different physical system.

No P7 plan owner currently forbids mixed periodicity, and the base P7 contract
requires exact authenticated geometry/cell identity and periodic displacement
handling. Silent coercion is therefore not admissible.

### 5.2 Required repair

1. Carry the exact three-axis PBC tuple in every deployed static/dynamics runtime
   request, case observation, and relevant runtime/deployment identity.
2. Emit the corresponding LAMMPS boundary string axis-by-axis (`p` or `f`).
3. Update worker-side minimum-image/safety logic to honor periodicity per axis,
   not through one scalar boolean.
4. Preserve the exact cell and PBC vector in raw observations used by protected
   topology/displacement reduction.
5. If a particular MACE/ML-IAP/LAMMPS path cannot safely execute a supported mixed
   boundary, return typed unavailable/blocking or a hard unsupported-domain
   error. Never coerce it to all-periodic or all-fixed.
6. Case/request identity must distinguish otherwise-identical geometries with
   different PBC vectors.

### 5.3 Acceptance

At minimum exercise `[T,T,T]`, `[F,F,F]`, `[T,T,F]`, and `[T,F,F]` requests.
Assert the exact LAMMPS boundary command and minimum-image behavior. Include a
counterexample whose result differs if a nonperiodic axis is incorrectly wrapped.

## 6. R12-B7 — complete resource/disk and performance observation evidence

Revision 11 correctly moved case concurrency under `SystemResourceSnapshot`,
`StageResourceScope`, `resolve_worker_count`, native-thread limiting, and
create-once deployment artifact publication. That source repair is retained.

Two release obligations remain:

1. Base P7 requires reuse of CPU/RAM/GPU/VRAM/**disk** admission. Revision 11
   explicitly says that if there is no generic current P6 cross-owner disk
   admission API, P7 must record disk availability/usage and keep local scratch
   bounded rather than invent the post-P7 storage subsystem.
2. Revision 10 requires target-machine **performance/resource measurements as
   qualification evidence**. A stable resource-scope digest is identity, not a
   measurement of what the qualification actually consumed.

### 6.1 Required repair

Add one immutable attempt/release resource-observation record (exact name
delegated) bound to the exact P7 binding/attempt. It must remain evidence rather
than scientific-policy identity unless a field is itself a stable scope identity.

Record, at minimum where available:

- resource-scope digest and selected CPU/GPU execution topology;
- target-machine start/end timestamps and total elapsed qualification time;
- per-component elapsed time sufficient to locate pathological runtime cost;
- workspace/attempt filesystem total/free bytes at start and end;
- configured existing disk reserve (for example the current
  `[execution].minimum_free_disk_gib` policy) and whether it remained satisfied;
- attempt-local scratch/deployment/reference-evidence footprint or a bounded
  defensible equivalent;
- process/host RAM peak when an existing owner can provide it without invasive
  new machinery;
- accelerator model/total VRAM and peak allocated/reserved or equivalent
  existing telemetry when GPU work is used;
- supported LAMMPS/MACE runtime identity already captured elsewhere, referenced
  rather than duplicated.

Use the existing disk-reserve policy and existing resource/telemetry owners where
possible. If no reusable generic disk-admission function exists, a P7 owner-local
safety check may read the existing reserve and `disk_usage` before material
artifact/case creation; this is not a new global storage authority. Do not create
archive/dedup/inventory/admission infrastructure reserved for
`CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

Volatile observations do not make identical numerical evidence stale merely
because free RAM/disk fluctuated. They are immutable observations attached to the
exact attempt. Hard safety exhaustion may abort/reject according to existing
operational policy, but must never alter scientific timestep, duration,
precision, membership, thresholds, or model selection.

### 6.2 Acceptance

- resource observation is present in terminal release evidence and authenticates
  to the exact binding/attempt;
- low-disk simulation fails/aborts before unsafe materialization while preserving
  the configured reserve;
- observed disk/RAM/GPU pressure can reduce execution scheduling or abort but
  cannot change scientific case identity;
- serial/concurrent scientific evidence remains identical while resource
  observations truthfully differ where execution cost differs;
- restart preserves/extends one exact attempt's resource observation without
  rewriting prior immutable samples as a different attempt;
- final target-machine evidence contains non-placeholder timing/resource values.

## 7. R12-B11 — real published MACE product execution remains blocking

The revision-11 repair now proves a real multihead MACE model can be exported
through the real mdstats deployment owner at `target_head` and wrapped by the
real `LAMMPS_MLIAP_MACE(..., head=target_head)` builder. Retain that positive
owner-level evidence.

The development host nevertheless reports that its activated LAMMPS ML-IAP
Python data object lacks the message-passing `forward_exchange` contract required
by MACE. The real product execution test therefore skips as
**UNAVAILABLE/BLOCKING**. This is truthful behavior, but it is not P7 closure.

Required closure:

1. Use a target runtime whose LAMMPS/ML-IAP/MACE combination genuinely supports
   the MACE message-passing product path. Do not monkey-patch or emulate the
   missing exchange interface merely to make qualification pass.
2. Execute an **actual member of the frozen P5 publication**, with its exact
   checkpoint bytes and canonical target head, through:

   ```text
   P5 published checkpoint
     -> real mdstats deployment export
     -> real LAMMPS_MLIAP_MACE target-head artifact
     -> real supported LAMMPS/ML-IAP static execution
     -> parity against the authenticated in-framework member
   ```

3. Bind the runtime capability/version/environment and deployed artifact SHA to
   the component/release evidence.
4. The existing tiny-MACE owner test remains useful development evidence but is
   not a substitute for the frozen publication path.
5. If the intended target machine still lacks this capability, P7 remains
   `unavailable/blocking`; do not downgrade the gate to an analytic ML-IAP pass.

## 8. R12-B12 — final target-machine / real-reference qualification

After B9, B13, and B7 source repairs and their regression are closed, freeze a
new executable candidate commit/tree. No source/runtime change may occur between
that freeze and final qualification without staling affected evidence.

Run the final qualification on the intended target machine using:

- the exact frozen repaired P7 executable candidate/tree;
- one exact current P5 final-production publication and its exact member bytes;
- the current predecessor reclosure/rebind identity;
- explicit non-placeholder external-reference protocol identity;
- real external DFT/reference observations for every required physical and
  relaxation request, including canonical stress evidence wherever the resolved
  stress capability says applicable;
- the actual supported MACE target-head deployment/ML-IAP/LAMMPS runtime;
- the exact frozen qualification policy/specification;
- the exact environment and resource-scope identities;
- the immutable resource/performance observation required by B7.

Required sequence:

```text
freeze repaired source candidate
 -> re-run affected regression/integration
 -> resolve exact current P5 publication + predecessor reclosure
 -> qualification run (nonlocked)
 -> publish/import/authenticate real reference bundle
 -> resume qualification to complete all nonlocked components
 -> close/reopen current nonlocked evidence
 -> explicit `qualification activate-locked --confirm`
 -> terminal ProductionQualificationRecord
 -> ReleaseEvidenceIndex + resource observations
 -> close/reopen/re-authenticate terminal state
 -> independent P7 closure review
```

The locked cohort is one-shot. Do not activate it until all nonlocked mandatory
components have passed on the final frozen candidate/product/environment.
A scientific rejection is a release result for that exact product; it must not
cause alternate seed/member/checkpoint selection or threshold tuning.

## 9. Regression and acceptance after source repair

Because B9/B13/B7 require source changes, all current executable evidence is
historical after the repair. Before freezing the target-machine candidate, rerun
at least:

1. revision-12 stress/PBC/resource negative and positive tests;
2. the full revision-11 repair acceptance suite;
3. the still-binding revision-10 P7 acceptance suite;
4. affected P5 publication/CV/final-production acceptance, including both
   committee policies;
5. affected P6 publication/storage/currentness/reclosure acceptance;
6. CLI/config/documentation specification tests affected by new fields;
7. assembled P5 -> P6 reclosure -> P7 nonlocked -> locked bounded integration;
8. repository-wide or equivalently complete affected-surface regression sufficient
   to prove the source repair introduced no new failures on modules it changed.

Do not require full real-production/GPU work in ordinary regression. The final
B11/B12 target-machine run is the separate production qualification tier.

## 10. Closure gate

P7 remains **REOPENED / NO-PASS** until one final frozen source/product candidate
satisfies all of the following:

- R12-B9 canonical stress capability, units, sign, tensor order, and evidence PASS;
- R12-B13 exact per-axis PBC runtime semantics PASS;
- R12-B7 disk/resource/performance observation and safety PASS;
- all previously closed R11 B1-B8/B10 semantics remain conformant after repair;
- R12-B11 actual frozen MACE publication executes through the supported
  target-head ML-IAP/LAMMPS path and deployment parity passes;
- R12-B12 final target-machine physical/PES/relaxation/dynamics/calibration
  qualification passes with real authenticated references or policy-valid
  `not_applicable` only where scientifically justified;
- explicit one-shot locked activation/result passes on that exact candidate;
- immutable terminal qualification record, release index, resource observation,
  and all referenced component evidence close/reopen and reauthenticate against
  the exact current binding;
- exact final executable commit/tree, predecessor reclosure, publication,
  specification, environment, runtime, reference, resource, component, and
  locked identities are recorded;
- no source change occurs after the qualifying candidate freeze;
- an independent Software Design closure review finds no unresolved parent or
  package blocker.

Only then may P7 be closed and its exact accepted executable tree become the
baseline for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.