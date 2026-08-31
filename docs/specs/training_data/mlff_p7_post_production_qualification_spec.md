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

# 4. Components and typed outcomes

Every component publishes one immutable `QualificationComponentEvidence` record
with one of four statuses: `passed`, `rejected`, `waiting_for_reference`, or
`not_applicable`. There is no `degraded` and no automatic retry.

| Component | Claim | Independent role |
|---|---|---|
| `deployment_parity` | export, dtype conversion, and ML-IAP/LAMMPS execution preserve the frozen model's E/F | none needed: a bounded M3 development cohort is correct, because the claim is representation equivalence, not generalization |
| `physical_pes` | correct local restoring physics: force agreement, restoring sign, stiffness and energy curvature | `OUTER_MONITOR` plus matched external references |
| `relaxation` | fixed-cell minimization preserves protected topology and geometry | `OUTER_MONITOR` bases plus matched reference relaxations |
| `dynamics` | finite-temperature stability of the deployed artifact | bases descending from the same frozen physical plan |
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

# 6. The one-shot locked test

Locked evidence is meaningful only while it is unseen. `qualification
activate-locked --confirm` is the only path that opens the reserved cohort. It
requires that every mandatory nonlocked component has already completed
successfully, and it records an immutable activation binding the publication
digest, the ordered member digest, the locked role digest, the locked policy
digest, the executable and environment identities, the prerequisite component
evidence, and the activation time.

A second activation for the same publication and locked cohort is refused. The
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

# 8. Concurrency

Independent qualification cases may run with bounded concurrency
(`qualification run --case-workers N`). Case identity is a pure function of the
frozen plan and policy, and every reduction is keyed by identity and sorted
before it is recorded, so serial and concurrent execution produce byte-identical
evidence and the same terminal verdict. Resource pressure may change scheduling
only; it can never change evidence membership, a threshold, a timestep, a
temperature, or a precision.

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
