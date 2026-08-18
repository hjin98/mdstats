---
title: "MLFF-DATA9A6c Observable Evidence and Leakage Closure Specification"
author: "mdstats project"
date: "2026-07-30"
geometry: margin=0.82in
toc: true
numbersections: true
fontsize: 10.5pt
---

# Purpose

DATA9A6c closes the remaining integrity defects in the analysis-owned observable
bridge before general material-profile migration. It changes evidence identity
and dependency ordering but does not change any RDF, coordination, dynamics,
transport, or thermomechanical algorithm.

# Collection identity verification

**Supplied collection identities** are verification inputs, never trusted substitutes for identities recomputed from the analyzed arrays.

The bridge MUST recompute an `ObservableCollectionIdentity` from every collection
actually passed to analysis. A caller-supplied identity MUST match the
recomputed scientific content digest and expected label or execution fails.

Scientific identity MUST be relocation invariant. Filesystem paths are retained
only as location hints. Source content digests, when available, remain identity
fields. Object-dtype arrays MUST be rejected.

Composition evidence MUST include species counts and an atomic-number sequence
digest. The explicit sequence may be omitted for large systems.

# Symmetric generation lineage

Reference and candidate trajectories MUST use one
`TrajectoryGenerationIdentity` schema. The record MUST include generator kind,
artifact and protocol digests, output collection digest, engine/version, and
precision policy. Optional fields include manifest, runtime environment, initial
configuration, source provenance, seed, and notes.

With `require_complete_lineage=True`, both records are mandatory and each
`output_collection_digest` MUST equal the analyzed collection identity. The
legacy `MLFFTrajectoryGenerationIdentity` is a compatibility wrapper and MUST
provide an explicit output digest in complete-lineage mode.

# Analysis-owned result identity

Every registered observable result MUST produce an `ObservableResultIdentity`
containing call ID, observable ID, native result type, serializer ID, and
canonical SHA-256 digest. The analysis facade owns this identity. It MUST support
current dataclass, mapping, sequence, enum, scalar, and NumPy-array result
structures and reject unstable opaque/object-dtype representations.

The MLFF bridge MUST reference these result identities. It MUST NOT duplicate or
redefine scientific arrays.

# Statistical role and leakage control

Every plan MUST declare one `ObservableEvidenceRole`:

```text
training_diagnostic
checkpoint_monitor
outer_validation
calibration
locked_test
external_benchmark
```

An `ObservableValidationActivationRecord` MUST bind the upstream identities
required by the role. Outer validation, calibration, and locked test require
partition policy and assignment. Outer validation, calibration, locked test,
and external benchmark require a predeclared comparison-policy digest. Locked
test additionally requires protocol-freeze and evaluation-activation digests.

The dependency direction is normative:

```text
comparison policy + activation -> evidence -> comparison result -> decision
```

The following reverse dependencies are forbidden:

- realized evidence to comparison-policy fitting;
- locked-test evidence to feature fitting, selection, protocol choice,
  checkpoint selection, calibration policy, or acquisition;
- post-training physical validation to retroactive dataset selection.

# Runtime and capability identity

Runtime evidence MUST distinguish executing-source version from installed
package metadata. It records source/install mode, executing module path and hash,
Python/platform identity, and numerical library versions.

Capability identity MUST include owner source implementation and function
signature, stable owner-manual ID, source-path hint, versioned manual URI,
parameter codec, and result type.

# Restorable evidence

`MLFFObservableValidationEvidenceRecord` MUST be JSON-safe, restore without
loading native result arrays, and reject any content-digest mismatch.

# Documentation and packaging

Automated **source/wheel registry parity** MUST be enforced: the source package and wheel MUST expose the same capability registry. The wheel
MUST include the owner-manual index. **Valid JSON release artifacts** MUST contain JSON only; console warnings belong in separate stderr/log files. Distributed
checksums MUST use relative artifact names.

# Acceptance tests

DATA9A6c passes only when tests cover:

1. supplied identity mismatch rejection;
2. relocation-invariant identity;
3. object-dtype rejection;
4. symmetric reference/candidate generation lineage;
5. output-collection mismatch rejection;
6. locked-test activation gates;
7. result identities for all 22 registered calls;
8. evidence-record round trip and tamper rejection;
9. source/wheel registry parity and packaged manual index;
10. dependency graph acyclicity and forbidden leakage edges;
11. valid JSON release artifacts;
12. updated manuals and rendered PDFs.
