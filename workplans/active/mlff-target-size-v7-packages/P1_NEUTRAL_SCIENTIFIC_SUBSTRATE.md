---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P1
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 1
status: active
package_revision: 3
amended_date: 2026-08-28
rework_reason: P1 independent review found canonical-frame construction dropping actual numerical labels and profile/LTA evidence retaining or mis-rebinding legacy DATA3 lineage
---

# P1 — Neutral scientific substrate

## Purpose

Establish the current-generation **scientific identity substrate** without changing the currently reachable target-size runtime. P1 removes compatibility-domain semantics from canonical numerical-label identity and neutral statistical identity while preserving precise electronic-structure provenance and proven parsing, feature, correlation, event, profile, eligibility, strain and partition algorithms.

The parent V7 workplan remains the generation-level authority, but **durable product code and persisted schema names introduced by P1 are version-agnostic**. The new substrate remains internal/unreachable from the current target-size runtime until P4.

P1 revision 3 incorporates two rounds of independent review. The first implementation left the new neutral statistical path dependent on legacy compatibility-bound owners. Revision 2 corrected that direction and the second implementation substantially improved naming, typed ownership and neutral lineage, but two blocking defects remain:

1. the assembled `CanonicalFrameAuthority` is currently reconstructed from legacy DATA3 records without the actual energy/force/stress arrays, so its canonical label identities do not bind the numerical labels they claim to represent; and
2. neutral profile evidence is not correctly rebound at the typed scientific-payload level, and LTA/profile payloads can retain legacy DATA3 frame/catalog ancestry even when the outer wrapper is rebound.

P1 is not accepted until these two defects are closed through the real current-generation owner path.

## Protected concerns

P1 protects the following product outcomes simultaneously:

- canonical training identity must represent the actual numerical labels and the semantic/unit/convention information required to interpret them;
- provenance heterogeneity is recorded precisely but is not a generic target-training eligibility, identity or partition axis;
- advisory compatibility policy/group assignment cannot change scientific source/frame/feature/statistical identity;
- unresolved or partial electronic provenance can proceed through the **assembled** current-generation path when its required numerical labels are usable;
- existing proven parsing, frame-array, raw-feature, profile, event, autocorrelation, eligibility, strain and partition algorithms are reused rather than gratuitously reimplemented;
- retained/reused evidence must be rebound to current scientific authorities without preserving retired compatibility-bound ancestry;
- the old production target-size runtime remains behaviorally intact and isolated until P4;
- functional regression/integration evidence is mandatory, while long GPU/production qualification remains deferred.

## Frozen design decisions

These decisions are frozen implementation constraints.

### 1. Version-agnostic durable naming

`V7` remains a workplan/generation identifier only. New product package names, class/function names, persisted schema identifiers and current-generation scientific concepts introduced by P1 must not carry `v7_`, `V7`, `mdstats.v7-*`, or equivalent architecture-revision prefixes.

The semantic package `mdstats.training_data.neutral_substrate` and version-agnostic names introduced by the revision-2 implementation are acceptable. Do not reintroduce aliases or compatibility shims for the unpublished `v7_neutral_substrate` / `V7*` symbols.

### 2. One assembled current-generation scientific-owner chain

The accepted scientific chain is:

```text
source files / manifest
  -> parsed normalized frame arrays + precise source provenance
  -> SourceAuthority
  -> CanonicalFrameAuthority
  -> NeutralFeatureEvidence
  -> NeutralStatisticalBase
```

Every semantic arrow must execute through the real current-generation owner. Legacy objects may be produced in parallel for the old runtime until P4, but they cannot be scientific parents or required semantic intermediates of the new chain when they encode compatibility-domain authority.

### 3. Canonical frame identity must be constructed from the actual numerical frame payload

The current-generation canonical-frame owner must consume the normalized per-frame arrays that contain the real training values, not merely legacy `TrainingFrameRecord` metadata or a pre-existing compatibility-bound label digest.

The canonical label identity for each frame must bind, as configured and applicable:

- selected energy channel and semantic role;
- energy units and normalization;
- entropy/free-energy convention;
- derivative/stress convention identity;
- actual canonical energy value;
- actual canonical force array;
- actual canonical stress array;
- label-fingerprint policy/tolerances.

It is explicitly forbidden to obtain an authoritative canonical label digest by calling the canonical-label digest function with actual required values replaced by `None`, by copying a legacy `label_payload_digest`, or by hashing only presence booleans/metadata.

### 4. Current-generation frame construction must not require `label_domain_id`

No current-generation source/frame builder may require resolved compatibility-domain assignment in order to construct canonical frames. In particular, the new canonical-frame path must not require legacy DATA3 to run first if legacy DATA3 rejects unresolved provenance because `label_domain_id` is absent.

The old DATA3 builder may remain unchanged and reachable only through the old runtime until P4.

### 5. Reuse the normalized frame-array/parsing machinery, not the legacy scientific identity

`FrameData`-equivalent normalized frame arrays and their existing VASP/cache/parser machinery are the preferred low-level input to current-generation canonical-frame construction because they already carry geometry, energy, forces, stress, temperature and source-frame indexing.

Reuse the established geometry, temperature-condition, reference-cell, strain, eligibility and duplicate algorithms where their semantics remain valid. Do not create a second parser or a second independent implementation of those algorithms merely to avoid legacy identities.

A thin shared algorithm/helper extraction is acceptable when needed to let both legacy DATA3 and the canonical-frame owner use the same computation without sharing the retired label-domain identity.

### 6. Source authority remains compatibility-policy neutral

`SourceAuthority.content_digest`, source membership eligible for canonical-frame construction, corpus atomic-reference identifiability and downstream scientific lineage must exclude:

- `label_domain_id`;
- compatibility-group assignment;
- `LabelCompatibilityPolicy.policy_digest`;
- legacy label-domain catalogs;
- any aggregate parent digest containing those values.

Advisory compatibility reports may still be serialized and inspected, but only as non-authoritative diagnostics.

### 7. Required-label validity is frame-aware

Source-level aggregate label counts are insufficient to authorize every frame. The canonical frame builder/eligibility owner must inspect the actual configured numerical values.

- required properties must be present for the affected frame when required by the configured training representation;
- supplied values must have valid shape, be finite and be canonicalizable;
- optional properties may be absent when the configured operation does not require them;
- supplied `NaN`, `+inf` and `-inf` cannot receive canonical scientific identity;
- explicit user filters and demonstrated mechanical training-engine constraints remain valid hard exclusions;
- provenance heterogeneity alone is not a hard exclusion.

### 8. Neutral DATA4 reuse is a scientific-evidence rebind, not identity laundering

Existing DATA4 raw-feature/event/profile computations may be reused when the physical/scientific values remain valid. Their legacy outer container identities must not be copied as scientific ancestry if those identities include retired DATA2/DATA3 compatibility semantics.

The neutral evidence layer must bind reused scientific records to `SourceAuthority` and `CanonicalFrameAuthority` with current-generation frame-record digests.

### 9. Profile/LTA rebinding must occur inside the typed scientific payload

Rebinding only `ProfileFeatureCatalog.frame_catalog_digest` or another outer wrapper is insufficient when the referenced scientific payload itself stores legacy frame/catalog lineage.

For every partition-stage profile provider consumed by the neutral statistical path:

- identify the payload fields that bind frame-catalog or frame-record identity;
- replace/reconstruct those identity references against `CanonicalFrameAuthority` while preserving the actual scientific/profile state;
- recompute the typed scientific payload digest after rebinding;
- then construct/wrap the generic `ProfileFeatureCatalog` using its real supported constructor/adapter API.

For LTA specifically, the accepted minimum consequence is:

```text
LtaPartitionFeatureCatalog.frame_catalog_digest
    = CanonicalFrameAuthority.content_digest

for every LtaFramePartitionRecord:
    frame_record_digest
        = CanonicalFrameAuthority.frame(frame_uid).content_digest
```

The actual LTA frame state, mobile-site state, policy and physical evidence remain unchanged unless independently invalidated. The rebound typed LTA catalog obtains a new scientific payload digest, after which the existing profile-wrapper machinery should be reused.

Do not merely copy the legacy LTA `scientific_payload_digest` into a new outer wrapper.

### 10. Neutral statistical owner remains typed and current-generation

`NeutralStatisticalBase` / unit construction must continue to require the version-agnostic `SourceAuthority`, `CanonicalFrameAuthority` and `NeutralFeatureEvidence` (or semantically equivalent current-generation types) and must reject silent substitution of legacy DATA2/DATA3/DATA4 containers.

Preserve the revision-2 implementation's type/lineage checks unless a demonstrably cleaner equivalent provides the same protection.

### 11. Old production runtime remains isolated until P4

The current prepare/select-target-size orchestration may continue to build/use legacy DATA2/DATA3/DATA4/DATA5 during P1-P3. P1 must not switch the production target-size route or expose the new substrate through public campaign orchestration.

Isolation is not permission for the new substrate itself to depend scientifically on legacy compatibility-domain owners.

## Implementation authority

### Frozen

The protected concerns and frozen design decisions above, the semantic owner chain, numerical-label identity requirement, profile-payload rebinding requirement, compatibility neutrality, old-runtime isolation and acceptance boundaries are frozen.

### Delegated

Implementation may choose:

- exact helper/file decomposition;
- whether canonical-frame construction is a new builder over existing `FrameData`, or a shared refactor of the old DATA3 computation pipeline that emits both legacy and canonical outputs;
- whether neutral profile rebinding is implemented by provider-specific adapters, a small generic protocol plus provider implementations, or equivalent typed reconstruction;
- cache/local data layout and internal performance mechanics;
- exact semantic class/function names, provided durable names stay version-agnostic.

Choose the minimum product complexity that satisfies the frozen scientific contract. Avoid a second parser, duplicate numerical algorithms, or generalized plugin infrastructure not justified by the current profile providers.

### Reopen only on evidence

Reopen only the affected design surface if repository evidence shows one of the following:

- normalized frame arrays cannot represent a required training label/convention without loss;
- an existing profile provider has an unavoidable scientific dependency on retired compatibility-domain identity rather than merely stale lineage fields;
- a reused DATA4 scientific record becomes invalid when rebound to the canonical frame authority rather than merely requiring identity reconstruction.

Do not silently carry legacy identity forward in lieu of reopening.

## Entry conditions

- Implementation branch is reconciled with the latest P1 revision-3 workplan commit.
- Preserve the valid revision-2 implementation portions: version-agnostic naming, `SourceAuthority` compatibility-neutral digest behavior, typed current-generation neutral-statistical inputs, runtime isolation, and valid focused tests.
- Treat `build_canonical_frame_authority_from_data3_catalog()` and the current profile-rebinding path as provisional/rework surfaces, not supported compatibility APIs.
- Existing DATA2/DATA3/DATA4/DATA5 affected-regression baseline is understood; unrelated pre-existing failures are recorded rather than absorbed.

## Pass P1-A — source-map reconciliation

Update `P1_SOURCE_MAP.md` and any directly affected internal architectural notes so the authoritative current-generation path is unambiguous:

```text
precise source provenance
 + normalized per-frame arrays carrying actual E/F/stress/geometry
   -> SourceAuthority
   -> CanonicalFrameAuthority
   -> rebound NeutralFeatureEvidence
   -> NeutralStatisticalBase
```

The source map must state explicitly that:

- canonical-frame scientific identity comes from actual numerical frame arrays, not legacy DATA3 label digests;
- legacy DATA3 may coexist for old-runtime isolation but is not a required parent of the new canonical frame authority;
- profile scientific payloads that bind legacy frame identity are rebound internally, not merely rewrapped;
- CV is not part of the neutral pre-target substrate;
- durable product/schema naming remains version-agnostic.

This pass is non-executable. Do not alter old runtime specifications to pretend P4 cutover has already occurred.

## Pass P1-B — source provenance and eligibility authority

Preserve and close the version-agnostic source authority so that:

- full `ElectronicStructureFingerprint`-equivalent provenance is retained;
- unresolved/partial provenance is diagnostic rather than a generic blocker;
- compatibility grouping is advisory only;
- corpus/current-operation atomic-reference identifiability is not split by compatibility domain;
- source scientific/content identity excludes advisory compatibility policy/group lineage;
- source eligibility for canonicalization means at least one frame can potentially contribute; actual frame usability is resolved using the real frame arrays in P1-C.

### P1-B acceptance

- DFT, DFT+U, hybrid, smearing/numerical variants can coexist when required labels are usable;
- unresolved provenance remains visible;
- changing only advisory compatibility policy changes advisory output but not `SourceAuthority.content_digest` or source membership eligible for canonicalization;
- no `label_domain_id` is required by the current-generation source owner.

### P1-B verification

1. focused provenance/source-policy/usability tests;
2. affected DATA2/source-ingestion regression;
3. serialization/restart round trip;
4. structural proof that compatibility-domain/policy identity is excluded from source scientific lineage.

## Pass P1-C — canonical frame authority from actual frame arrays

This is the primary revision-3 corrective pass.

### P1-C1 — establish the real canonical-frame input boundary

Construct `CanonicalFrameAuthority` from:

- `SourceAuthority`;
- normalized `FrameData`-equivalent arrays keyed by run;
- existing temperature-target/reference-cell/policy inputs needed for the established frame metadata algorithms.

The authoritative canonical-frame builder must not require `TrainingFrameCatalog` or another legacy DATA3 object. If a legacy adapter remains temporarily useful for tests/migration, it cannot be the production/current-generation semantic owner and cannot claim scientific acceptance.

Validate run membership, frame counts, atom counts, source-frame indices, composition and other established frame/source consistency invariants directly against `SourceAuthority` plus the normalized arrays.

### P1-C2 — compute canonical identity from real values

For every frame, compute through the actual implementation path:

- occurrence/frame UID;
- geometry fingerprint;
- canonical label payload from actual energy/force/stress values and interpretation metadata;
- labeled-configuration fingerprint;
- separate electronic-structure provenance reference;
- temperature/condition metadata;
- strain/reference-cell metadata;
- frame eligibility using the actual numerical labels and existing eligibility semantics;
- duplicate and labeled-duplicate catalogs based on the new canonical identities.

Do not rely on the legacy compatibility-bound `TrainingFrameRecord.label_payload_digest` or the old frame record's `energy_present` / `forces_present` / `stress_present` booleans as substitutes for numerical values.

### P1-C3 — unresolved provenance must traverse the real path

A source whose electronic provenance is unresolved/partial but whose configured required labels are valid must successfully traverse:

```text
SourceAuthority -> CanonicalFrameAuthority
```

No `label_domain_id` assertion may appear on this path.

### P1-C acceptance

Prove through the real canonical-frame owner that:

- identical actual canonical labels under different provenance/grouping produce identical canonical label identity;
- advisory grouping-policy changes do not alter frame UID, canonical label identity, labeled-configuration identity or canonical-frame-authority content identity;
- changing an actual per-frame energy changes that frame's canonical label and labeled-configuration identity;
- changing actual force or stress values changes identity when those labels are part of the configured canonical payload;
- changing semantic/unit/convention interpretation changes identity;
- non-finite supplied required numerical labels are rejected or make the affected frame non-usable according to the configured contract, and never receive valid canonical scientific identity;
- geometry duplicate semantics remain geometry-only and labeled duplicate semantics use the actual canonical labels;
- unresolved provenance with usable labels succeeds through the real current-generation frame owner;
- the new frame owner can feed P1-D without substituting legacy DATA3.

### P1-C verification cycle

1. focused canonical numerical identity, finite/shape/error and duplicate tests;
2. focused current-generation frame-builder tests using real `FrameData` values;
3. affected DATA3/frame/eligibility/temperature/reference-cell/strain/duplicate regression for reused algorithms;
4. serialization/restart round trip of current-generation frame state;
5. structural negative check that the authoritative builder does not require `TrainingFrameCatalog`, `label_domain_id`, legacy label-domain catalog identity, or compatibility-policy-containing parent digest;
6. bounded integration carrying the real canonical frame authority into neutral feature evidence.

Close both semantic and functional dimensions before P1-D closure.

## Pass P1-D — neutral feature/correlation evidence and statistical substrate

### P1-D1 — raw feature/event evidence rebind

Reuse valid DATA4 raw-feature/event calculations, but bind them to `SourceAuthority` and `CanonicalFrameAuthority`:

- per-frame evidence that stores a frame-record digest must reference the corresponding canonical frame-record digest;
- raw-feature catalogs must bind the current source/frame authority digests;
- event catalogs must bind the rebound raw-feature catalog and canonical frame authority;
- do not import legacy `TrainingDataSourceCatalog.content_digest`, legacy `TrainingFrameCatalog.content_digest` or legacy `Data4FeatureBundle.content_digest` as a scientific ancestor merely for transition convenience.

The implementation may consume an old DATA4 bundle as a **value source** during P1 because the old runtime still produces it, but all reused records entering `NeutralFeatureEvidence` must be validated/rebound so that the neutral evidence identity is current-generation. A legacy container is input evidence, not authority.

### P1-D2 — typed profile scientific-payload rebind

For each partition-stage profile catalog in DATA4:

1. resolve/access its typed scientific payload;
2. identify every frame-catalog/frame-record lineage field in that payload;
3. reconstruct those identity fields from `CanonicalFrameAuthority` while preserving the computed physical/profile values;
4. recompute the typed payload digest;
5. create the generic profile wrapper using the actual supported `ProfileFeatureCatalog` API or existing wrapper helper;
6. bind the wrapper to the rebound canonical frame authority and new scientific payload digest.

Do not construct `ProfileFeatureCatalog` with nonexistent/legacy constructor fields and do not copy an old profile scientific digest after only changing the outer wrapper.

#### Required LTA realization

For the existing LTA partition provider:

- rebuild `LtaFramePartitionRecord.frame_record_digest` from canonical frame records;
- rebuild `LtaPartitionFeatureCatalog.frame_catalog_digest` from `CanonicalFrameAuthority.content_digest`;
- preserve LTA policy, frame state, mobile-site state and actual physical evidence;
- recompute the LTA catalog scientific digest;
- reuse `wrap_lta_partition_features()` or a semantically equivalent valid wrapper path;
- verify `profile_partition_state_changed()` and downstream event/statistical consumers operate on the rebound LTA payload.

Do not re-run expensive LTA geometry analysis solely to obtain new identity when typed reconstruction of unchanged scientific values is sufficient.

#### Other profile providers

For any other partition-stage provider currently supported and reachable, either implement the same typed rebind contract or demonstrate that its scientific payload contains no legacy frame/catalog lineage beyond the wrapper. Do not silently assume opaque payload digests are neutral.

### P1-D3 — neutral statistical base

Preserve the improved typed current-generation statistical owner. It must consume only:

- `SourceAuthority`;
- `CanonicalFrameAuthority`;
- `NeutralFeatureEvidence`.

Retain independently required temporal/autocorrelation blocks, events/protected windows, physical condition/regime, replica/structural-realization/reference-group evidence, duplicates/correlation groups, protected outer roles, independence grading and leakage/disjointness checks.

Continue to forbid:

- compatibility `label_domain_id` in partition condition/unit identity;
- compatibility-policy or label-domain-containing ancestor digests;
- provenance as a mandatory role-budget axis;
- pre-target CV/fold authority.

### P1-D acceptance

- advisory compatibility-policy changes leave neutral raw/profile/event evidence identity, unit IDs, unit-catalog identity, protected-role assignment and neutral-statistical-base identity unchanged;
- actual canonical label changes propagate through canonical frame lineage and invalidate the appropriate rebound feature/statistical descendants even when the raw physical observable itself is numerically unchanged;
- physical/profile changes alter relevant scientific evidence and downstream identities;
- LTA/profile partition evidence can execute through `NeutralFeatureEvidence` and `NeutralStatisticalBase` without constructor errors or legacy frame lineage;
- required outer/protected roles remain disjoint and leakage checks execute on real neutral units;
- no CV plan is required;
- later target-size split/post-selected CV can consume correlation groups without frame expansion;
- legacy source/frame/DATA4 containers cannot silently substitute for the required current-generation owners.

### P1-D verification cycle

1. focused raw-feature/event rebinding tests;
2. focused typed profile/LTA rebinding tests;
3. focused neutral partition/correlation/leakage tests;
4. affected DATA4/DATA5/profile/LTA/event/statistical-role regression covering reused algorithms;
5. deterministic serialization/reconstruction of neutral feature evidence and statistical state;
6. structural lineage checks proving rebound profile scientific payloads no longer retain legacy DATA3 frame/catalog digests;
7. real-owner integration from P1-B/P1-C through neutral feature evidence into the neutral statistical base.

## Pass P1-E — package closure

Reconcile the complete P1 diff against the parent V7 workplan and this revision, then re-derive the P1 affected surface from the assembled candidate.

### P1-E1 — required real-owner integration

Execute a bounded deterministic integration through the actual P1 owners:

```text
source files / manifest
 -> existing parser/cache machinery yielding normalized frame arrays
 -> SourceAuthority
 -> CanonicalFrameAuthority built from actual frame arrays
 -> NeutralFeatureEvidence with typed profile rebinding
 -> NeutralStatisticalBase
```

Allowed cost bounding:

- small synthetic VASP/source fixtures;
- bounded frame counts;
- existing parser/cache test helpers;
- no expensive model training/GPU work.

Forbidden acceptance substitutions:

- using legacy DATA3 as the semantic owner of canonical-frame numerical identity;
- invoking only `build_canonical_frame_identity()` with hand-supplied values while the assembled authority builder drops those values;
- seeding a prebuilt canonical frame authority in place of exercising its real builder;
- testing only an outer profile wrapper while bypassing the typed profile scientific payload;
- rebuilding canonical/profile identity logic inside the test harness instead of executing the production owner.

### P1-E2 — compatibility-policy invariance proof

Using the same scientific source/frame arrays, build the complete P1 chain under at least two advisory compatibility policies that produce observably different advisory compatibility output. Require equality of all applicable scientific state/behavior:

- source membership eligible for canonicalization;
- `SourceAuthority.content_digest`;
- canonical frame UIDs;
- canonical label payload digests;
- labeled-configuration fingerprints;
- `CanonicalFrameAuthority.content_digest`;
- rebound raw-feature/event/profile scientific payload identities;
- `NeutralFeatureEvidence.content_digest`;
- neutral unit IDs and unit-catalog content identity;
- protected outer-role assignments;
- `NeutralStatisticalBase.content_digest`.

Only explicitly advisory compatibility diagnostics/policy/group identifiers may differ.

This test must fail if a legacy compatibility-bound source/frame/DATA4/profile digest is reintroduced as scientific ancestry.

### P1-E3 — assembled numerical-change sensitivity proof

Through the **real canonical-frame authority builder**, alter at least one actual normalized frame-array energy value while leaving geometry and provenance unchanged. Require:

- the changed frame's canonical label payload digest changes;
- its labeled-configuration fingerprint changes;
- canonical frame-authority content identity changes;
- neutral feature evidence lineage changes as appropriate because it binds the changed canonical frame authority;
- neutral statistical-base identity changes where its ancestor lineage is intentionally part of its scientific identity.

Also exercise at least one actual force or stress change when that property is configured in the canonical payload, and at least one semantic/unit/convention change.

Separately verify supplied non-finite required values cannot obtain canonical scientific identity.

A direct unit test of `canonical_training_label_payload_digest()` remains useful but **cannot substitute** for this assembled owner test.

### P1-E4 — unresolved-provenance assembled proof

Construct a bounded source with unresolved/partial electronic provenance but valid required numerical labels and execute:

```text
SourceAuthority
 -> CanonicalFrameAuthority from real normalized arrays
 -> NeutralFeatureEvidence
 -> NeutralStatisticalBase
```

The path must succeed without `label_domain_id` assignment. Provenance diagnostics must still report the unresolved state.

### P1-E5 — real LTA/profile integration proof

Run at least one bounded partition-stage profile fixture through the real neutral evidence/statistical path. The existing LTA provider is mandatory because it is a currently supported DATA4 partition profile and its scientific payload stores frame lineage.

Verify:

- the rebound LTA catalog references `CanonicalFrameAuthority.content_digest`;
- each rebound LTA frame record references the corresponding canonical frame-record digest;
- the rebound LTA scientific payload digest is used by the generic wrapper;
- `profile_partition_state_changed()` and any event/statistical consumer needed by the bounded fixture resolve the rebound payload successfully;
- no legacy DATA3 frame/catalog digest survives as an authoritative ancestor inside the rebound LTA payload;
- round-trip serialization/reconstruction preserves the rebound scientific identity.

### P1-E6 — naming and absence proof

Structurally verify new current-generation code/schema paths contain no architecture-generation prefix such as `v7_`, `V7*` or `mdstats.v7-*`. Workplan/history paths may continue to use V7.

Also verify there are no compatibility aliases for the removed provisional P1 names.

### P1-E7 — runtime isolation proof

Verify:

- current prepare/select-target-size orchestration remains on the old runtime until P4;
- campaign CLI/public target-size exports do not expose the neutral substrate prematurely;
- old runtime behavior remains reachable;
- the current-generation P1 substrate does not require old compatibility-domain owners merely to remain isolated.

### P1-E8 — functional closure evidence

Required executable evidence on the final assembled candidate:

- all P1-B/C/D focused tests;
- affected DATA2/source-ingestion regression;
- affected DATA3 geometry/identity/eligibility/temperature/reference-cell/strain/duplicate regression for reused shared algorithms;
- affected DATA4 raw-feature/event/profile/LTA regression;
- affected DATA5/statistical-role/partition/leakage regression;
- serialization/restart reconstruction for every new persisted/current-generation owner and rebound profile payload;
- real-owner integration P1-E1;
- compatibility invariance P1-E2;
- numerical-change sensitivity P1-E3;
- unresolved-provenance chain P1-E4;
- real LTA/profile integration P1-E5;
- structural naming/lineage/runtime-isolation checks;
- repository/project-required Python/package checks covering the final affected surface.

A required check that did not execute is not a pass. Green helper tests do not substitute for a broken semantic owner. No full long GPU/production qualification is required for P1; production qualification remains deferred under the parent workplan.

## Preservation / non-goals

- Do not switch the production target-size runtime before P4.
- Do not redesign the target-size selection algorithm in P1.
- Do not introduce pre-target CV.
- Do not reclassify electronic-structure compatibility grouping as a hidden training/partition axis.
- Do not add a second VASP parser, duplicate frame-normalization implementation, or parallel profile-analysis engine solely for the new identity model.
- Do not retain unpublished provisional adapters/aliases merely to keep old P1 tests green.
- Do not perform long GPU training or production-scale qualification in this package.

## Exit gate

P1 is accepted only when the following invariant is true in the **assembled real-owner object graph**:

> Canonical usable data and frame identity are derived from the actual configured numerical energy/force/stress payload and required interpretation metadata; unresolved provenance with usable labels can traverse the current-generation path without a compatibility-domain assignment; neutral raw/event/profile evidence is rebound through its typed scientific payloads to canonical frame identity; no compatibility-group assignment, compatibility-policy identity, retired DATA2/DATA3/DATA4/profile ancestor digest or pre-target CV authority participates in current-generation scientific identity or protected-role assignment; precise provenance remains fully recorded; durable code/schema naming is version-agnostic; and the production target-size runtime has not yet switched.

The following are explicitly insufficient for P1 acceptance:

- canonical helper unit tests when the assembled frame authority omits real numerical values;
- a legacy DATA3-to-canonical adapter as the only authoritative frame-construction path;
- successful generic-data integration that does not exercise unresolved provenance;
- rebinding only the outer profile wrapper while retaining legacy lineage inside LTA/other typed payloads;
- equality of neutral unit IDs when ancestor scientific digests still depend on compatibility policy;
- source inspection without the required affected regression and real-owner integration evidence.

Commit/tag the accepted corrected P1 checkpoint before starting P2.
