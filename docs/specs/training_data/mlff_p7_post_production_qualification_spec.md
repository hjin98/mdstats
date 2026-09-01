---
title: "MLFF-P7: Post-Production Qualification and Locked Release Evidence"
author: "mdstats development"
date: "2026-08-31"
status: "implementation specification"
---

## Implemented public records

`mdstats.training_data.qualification` exposes `AuthenticatedFinalPublication`,
`PublishedProductionMember`, `ExecutableCandidateIdentity`,
`EnvironmentFingerprint`, `QualificationSpecIdentity`, `EvidenceRoleMembership`,
`QualificationInputBinding`, `PhysicalValidationPlan`,
`ProductionQualificationPlan`, `PhysicalReferenceRequest`,
`AuthenticatedReferenceBundle`, `QualificationComponentEvidence`,
`LockedActivationRecord`, `ProductionQualificationRecord`,
`ReleaseEvidenceIndex`, `QualificationAttemptState`, and
`QualificationRetentionFence`. The public command family is
`qualification status`, `qualification run`, and
`qualification activate-locked`.

# 1. Purpose

P7 validates a product that has already been frozen. It consumes the accepted
final-production publication produced by the P5 post-selection owners, binds the
identities that make a qualification claim meaningful, executes deployment,
physical, dynamical, and calibration components against that exact product, and
- only after an explicit one-shot activation - the reserved locked
interpolation test. It publishes one immutable terminal release verdict.

It does **not** own target-size selection, cross-validation acceptance,
production training, representative-checkpoint or seed choice, publication
membership, cache policy, or cleanup policy. There is no code path from a
qualification outcome back into any of those authorities.

# 1a. Where the product boundary is

The released product is decided by P5, not by P7. `train-production` publishes a
`FinalProductionPublicationDecision` immediately after the required seeds
complete: it binds the selected binding, final plan and policy, CV/method
lineage, frozen M3 membership, every required seed's run evidence and
already-frozen representative identity, the canonical target head, the committee
policy, the exact ordered published member set, and a deterministic
decision-policy identity. Both `all_qualified_final_seeds` and
`single_best_final_seed` are decided there, using only pre-qualification
evidence and the accepted target-only EVAL2 ordering.

P7's `AuthenticatedFinalPublication` is a read-only view that copies that
decision's ordered member set. It contains no ranking, no membership registry,
and no path that could add, remove, or reorder a member.

# 2. Why the product must be frozen first

Downstream physical evidence is only independent while it cannot influence the
decisions upstream of it. If a physical, dynamical, or locked result could
select among seeds, checkpoints, or committee members, it would stop being
validation and become another model-selection channel - and the resulting error
estimate would be optimistically biased by exactly the amount of selection it
performed. P7 therefore resolves an already frozen publication through the
accepted P5 completion owner and holds a read-only view of it.

The same reasoning drives three further rules:

- the physical validation plan is constructed from the neutral `OUTER_MONITOR`
  role and the P1 split-exclusion/correlation authority alone, so it is
  byte-identical for every publication member and cannot be steered toward
  configurations a particular model happens to handle well;
- every threshold is resolved from configuration into a digested specification
  before any product outcome is observed;
- absent external reference evidence is `waiting_for_reference`, never a pass.

# 3. Qualification identity

A qualification claim is about one product, produced by one executable, on one
machine, under one policy. The attempt identity descends from:

```text
selected binding digest
+ final-production publication digest
+ ordered published member digest
+ executable candidate identity
+ target-machine environment fingerprint
+ qualification specification digest
+ neutral evidence-role membership digest
```

The executable candidate identity is a digest over the importable mdstats source
surface. Workplan, review, and documentation changes therefore cannot stale
executable evidence, while any source or generated-runtime change does. The Git
commit and tree travel alongside for audit ordering and are never used as
currentness authority.

The environment fingerprint binds operating system and kernel, architecture,
Python, PyTorch, CUDA runtime, accelerator model and driver, MACE, ASE, the
LAMMPS runtime and its ML-IAP capability, the dtype policy, and the device.
Machine *capacity* - thread count and installed memory - is recorded but
deliberately excluded from the identity, because it does not change what a
deterministic numerical claim means.

# 3a. Product identity through deployment

The canonical P5 target head travels with every published member and is part of
both the member identity and the deployment identity. Deployment export and the
MACE ML-IAP builder are both called with that exact head; neither accepts `None`
for a multihead-capable product, and a model whose heads do not contain it fails
closed. An artifact built from the replay or foundation head is therefore a
different product, not the same product serialized differently.

Deployed artifacts are published create-once under an advisory per-artifact lock
and re-authenticated from a durable receipt plus their bytes before every reuse,
including after a process restart with an empty in-memory cache. A full PyTorch
model pickle is not byte-deterministic, so two independent builds of the same
logical artifact are serialized rather than compared byte-for-byte.

Executing *an* ML-IAP unified model and executing *this MACE product* are
separate runtime capabilities. The runtime probe reports both, and when the real
deployed path is in use the stronger one is required; its absence is
unavailable/blocking, never a pass.

# 3b. Exposure-time currentness

Every public resolver for the qualification plan, the terminal record, and the
release-evidence index re-establishes the current `QualificationInputBinding` at
exposure time and validates the located object against it. The campaign-store
pointer is a locator only. A record published under an older specification,
executable, environment, or product is historical, and `qualification status`
cannot report it as the current release verdict. There is deliberately no
unfenced public read.

Locked disclosure history is kept outside that fence in an append-only reveal
index, so a currentness change can make a verdict historical without ever making
a revealed cohort fresh again.

# 3c. Component-input identity

Reference-dependent components are keyed by a component-input identity that
includes the exact frozen reference request and the exact authenticated bundle
digest, on top of the qualification binding. Replacing a bundle under the same
request therefore stales local PES, relaxation, and dynamics - the components
that consume it - while deployment parity and calibration remain reusable. Old
evidence stays immutable and historical rather than being overwritten.

# 4. Components and typed outcomes

Every component publishes one immutable `QualificationComponentEvidence` record
with one of four statuses: `passed`, `rejected`, `waiting_for_reference`, or
`not_applicable`. There is no `degraded` and no automatic retry.

| Component | Claim | Independent role |
|---|---|---|
| `deployment_parity` | export, dtype conversion, and ML-IAP/LAMMPS execution preserve the frozen model's E/F | none needed: a bounded M3 development cohort is correct, because the claim is representation equivalence, not generalization |
| `physical_pes` | correct local restoring physics: force agreement, restoring sign, stiffness and energy curvature | `OUTER_MONITOR` plus matched external references |
| `relaxation` | fixed-cell minimization preserves protected topology and geometry | `OUTER_MONITOR` bases plus matched reference relaxations |
| `dynamics` | finite-temperature stability of the deployed artifact, started from the authenticated reference-relaxed geometry | the same frozen physical bases, plus their matched reference relaxations |
| `calibration` | uncertainty of the exact frozen committee | `UNCERTAINTY_CALIBRATION` |
| `locked_interpolation_test` | one-shot post-freeze generalization evidence | `LOCKED_INTERPOLATION_TEST` |

Topology safety and geometric fidelity are judged separately and never traded
off: a broken bond rejects the product even when averaged geometry error is
small, because a small average over a collapsed structure is not evidence of
correctness.

For a single-model publication with no accepted uncertainty estimator,
calibration resolves to `not_applicable`. Uncertainty is never invented from a
point prediction, and a member is never added to make calibration possible.

# 5. The external reference boundary

P7 owns request identity, reference import and authentication, and matched
reduction. It does not run DFT. `qualification run` publishes an exact
`reference-request.json` enumerating every geometry the frozen plan needs, keyed
by an exact geometry identity and a declared reference protocol. A supplied
bundle is authenticated against that request in full: a wrong protocol, a wrong
request digest, a missing geometry, an unexpected geometry, or a wrong atom
count is a hard lineage failure rather than a partial pass.

Bounded deterministic analytic references are legitimate below this boundary for
functional testing. A production scientific qualification supplies real external
references generated under the exact frozen request and protocol identity.

# 4b. Exact periodic boundary conditions

The three-axis periodicity vector is carried exactly through every deployed
static and dynamics request, the LAMMPS boundary command, the raw observations,
and the dynamics case identity. Collapsing it to a single boolean would execute a
mixed-boundary system such as `[True, True, False]` as a fully nonperiodic one -
a different physical system - and would let minimum-image safety reductions wrap
an axis that has no images. Two geometries that differ only in periodicity are
therefore different cases with different identities, and a request that does not
state its periodicity fails closed rather than assuming one.

# 5a. Dynamics inputs and diagnostics

Each dynamics case starts from the authenticated `relaxed_positions_angstrom` of
its physical base. A missing or malformed relaxed reference is
`waiting_for_reference` or a lineage failure; it never falls back to the
unrelaxed base geometry. Case identity binds the reference-bundle digest and the
exact initial relaxed-geometry identity.

The runtime worker returns raw observations only - NVT and NVE temperatures,
energy components, lossless geometry, forces, and cell identity - and makes no
scientific decision. The reducer then evaluates, under thresholds frozen before
execution: NVT stabilization, finite NVE temperature and its tolerance, NVE
energy drift per atom per picosecond, minimum pair distance, maximum force,
protected topology damage, and protected displacement, bond, and angle
degradation. Topology damage must persist for a configured number of consecutive
sampled violations before it rejects, so transient noise is not read as a broken
framework; that persistence threshold is part of the specification digest and
cannot be chosen after seeing a trajectory.

A nonfinite observation is a rejection reason, not a serialization failure:
immutable evidence is JSON-exact and records the measurement as absent.

# 5b. Stress and deformation conventions

Stress applicability is a capability decision, not a configuration switch. It is
resolved before any component executes, from the accepted training objective's
stress weight, the reference frames' stress labels, whether the authenticated
model actually returns a stress tensor, whether the configuration is periodic at
all, and whether the deployed runtime can report stress. Policy composes with
those facts in one direction only: it may *require* stress, and it may record a
scientifically justified inapplicability reason for audit, but it cannot relabel
an available trained stress channel as `not_applicable` to avoid qualifying it.
The decision is immutable, carries its reason codes, and participates in
component identity, so a capability change stales stress-bearing descendants
rather than silently reinterpreting existing evidence.

Every source converts to one canonical form once: a symmetric 3x3 Cauchy stress
in eV/Angstrom^3, positive in tension, matching the repository's ASE/MACE label
contract. Unit and sign conventions belong to each source adapter rather than to
the caller, because they are facts about that source. In particular, LAMMPS
`units metal` thermo pressure is in **bar** and is positive in **compression**;
`canonical_stress_from_lammps_metal_pressure` is the only place that knows this,
and it is not parameterized by units or sign. An extensive virial must be divided
by the instantaneous periodic-cell volume. Missing stress is an

# 6. The one-shot locked test

Locked evidence is meaningful only while it is unseen. `qualification
activate-locked --confirm` is the only path that opens the reserved cohort. It
requires that every mandatory nonlocked component has already completed
successfully, and it records an immutable activation binding the publication
digest, the ordered member digest, the locked role digest, the locked policy
digest, the executable and environment identities, the prerequisite component
evidence, and the activation time.

Activation is an irreversible *open* event, not proof that the evaluation
completed, and those two facts are recorded separately. If the process dies
between opening the cohort and publishing the locked result, a rerun resumes the
same activation identity and finishes the same test rather than opening a second
one or refusing forever. A second activation is refused only once a genuinely
terminal result - the terminal record and the release index both referencing
that activation - already exists. The
refusal is keyed by product and cohort, not by policy, so loosening a threshold
after a locked failure cannot manufacture a fresh locked test. A locked failure
rejects the exact published product; retraining afterwards creates a new product
but does not restore the independence of the revealed cohort.

# 7. Persistence, attempts, and retention

Durable evidence lives under one canonical generation-scoped root,
`<workspace>/.mdstats/qualification/g<N>/`. `objects/` is a create-once,
validate-existing content-addressed store; `attempts/<attempt-identity>/` holds
attempt state, per-component position records, and bulk scratch under a root
derived from the immutable attempt identity rather than from a mutable path.

Currentness is not persisted as a second truth. It is re-established through the
P4/P5/P7 owners and published as a generation-fenced pointer inside one
serialized campaign-store transaction, so a long qualification that finishes
after a newer `prepare` cannot publish stale evidence as current.

An active attempt pins the exact artifacts it needs. The pin is coordination
metadata only: it grants no scientific currentness, owns no cache, cannot make a
stale publication current, and is released on terminal completion or explicit
abort. Restart reconstructs it from durable attempt state or fails closed. The
retention fence reduces deletion authority in two ways - durable release
evidence is never reconstructible scratch, and an artifact referenced by an
in-flight attempt is not reclaimable - and composes with, rather than replaces,
the existing target-size retention fence.

P7 introduces no cache authority, no second cleanup policy engine, no global
retention registry, and no part of the successor storage inventory, archive,
deduplication, or admission plane.

# 8. Concurrency and resource ownership

Concurrency, nested BLAS/OpenMP/PyTorch thread budgets, and worker counts are
resolved through the accepted campaign resource owner rather than a
qualification-private policy. The resolved resource scope is bound to the
attempt separately from the numerical environment identity: machine capacity is
recorded without making a deterministic numerical claim machine-specific, while
a materially different resource scope still cannot silently reuse a performance
or resource claim.



Independent qualification cases may run with bounded concurrency
(`qualification run --case-workers N`), capped by that owner. Case identity is a pure function of the
frozen plan and policy, and every reduction is keyed by identity and sorted
before it is recorded, so serial and concurrent execution produce byte-identical
evidence and the same terminal verdict. Resource pressure may change scheduling
only; it can never change evidence membership, a threshold, a timestep, a
temperature, or a precision.

# 8a. Measured resource evidence and disk safety

The resource-scope digest is identity: it says which machine budget a run was
entitled to, and it is the same whether a component took two seconds or two
days. Target-machine qualification also records what the attempt actually cost,
in one immutable observation bound to the exact binding and attempt: total and
per-component elapsed time, workspace filesystem total/free bytes and the
attempt's own footprint at start and end, the configured free-disk reserve and
whether it held, peak process RSS, and accelerator model/total VRAM/peak
allocation where an existing owner reports them. The terminal record and the
release index both point at it.

Those observations are evidence, never policy. Free disk and RAM fluctuate for
reasons unrelated to the product, so an observation never stales numerical
evidence. The single place they act is safety: the campaign's existing
`[execution].minimum_free_disk_gib` reserve is checked before each component
materializes artifacts or scratch, and an attempt that cannot proceed safely
aborts rather than changing any timestep, duration, precision, membership,
threshold, or model choice. Reading that reserve is an owner-local safety check;
deduplication, archival, inventory, and cross-owner admission remain the
successor storage workplan's.

# 9. Verdicts

`ProductionQualificationRecord` is the single terminal owner:

- `rejected` - a required component rejected the exact publication;
- `waiting_for_reference` - a required component lacks its external evidence;
- `incomplete` - a required component has not produced a terminal success yet,
  including the locked test before activation;
- `release_qualified` - every required component is `passed` or an explicitly
  allowed `not_applicable`.

`ReleaseEvidenceIndex` points at, and never duplicates, the record, the
publication, the executable, the specification, the environment, the plan, the
component evidence, and the locked activation. It is the accepted post-P7
baseline for the successor storage workplan.

# 10. Qualification tiers

Routine regression and bounded integration establish functionality and the
absence of hard failures. They are not a production qualification. Final
release qualification requires the exact frozen executable candidate and the
exact frozen publication, on the intended target machine and runtime, with the
real deployment path and real external reference evidence where the policy
requires it. A CPU-only or proxy result is never labelled as target-machine
qualification, and a resource or performance failure is a release failure or an
engineering repair trigger - never a reason to modify frozen scientific
behaviour.
