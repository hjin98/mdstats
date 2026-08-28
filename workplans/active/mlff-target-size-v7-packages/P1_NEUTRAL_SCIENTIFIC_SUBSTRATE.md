---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P1
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 1
status: active
package_revision: 5
amended_date: 2026-08-28
rework_reason: Independent review after P1A3 found that configured-required labels can still receive canonical label/labeled-configuration identity before frame validity is established, P1-E3/P1-E4 acceptance remains proxy-permissive, provisional source-record deserialization can synthesize newly authoritative source facts, and direct VASP canonical rebuild does not bind the source-control interpretation strongly enough for durable restart semantics.
---

# P1 — Neutral scientific substrate

## Purpose

Establish the current-generation **scientific identity substrate** without changing the currently reachable target-size runtime. P1 removes compatibility-domain semantics from canonical numerical-label identity and neutral statistical identity while preserving precise electronic-structure provenance, source facts required for scientific interpretation, and proven parsing, feature, correlation, event, material-profile, eligibility, strain, partition and parallel-execution machinery.

The parent V7 workplan remains the generation-level authority, but **durable product code and persisted schema names introduced by P1 are version-agnostic**. The new substrate remains internal/unreachable from the current target-size runtime until P4.

P1 revision 5 preserves the already-corrected revision-4 architecture — version-agnostic naming, scientifically complete compatibility-neutral source facts, real-array canonical construction, generic provider dispatch with LTA provider ownership, durable typed-profile restart, removal of the invalid DATA3 adapter, and preserved per-run parallelism — and tightens the remaining scientific trust boundary and proxy-proof acceptance obligations.

P1 remains active until the complete current-generation owner chain closes through real numerical frame data, compatibility-neutral source facts, configured-required-label authority, provider-owned typed profile rebinding, durable restart reconstruction and affected regression/integration evidence.

## Protected concerns

P1 protects the following product outcomes simultaneously:

- canonical training identity represents the actual numerical labels and semantic/unit/convention information required to interpret them;
- a physical frame may remain represented for diagnostics/statistics when appropriate, but **authoritative canonical label and labeled-configuration identity is never granted before the configured required-label contract is satisfied**;
- compatibility-neutral source facts needed by downstream scientific algorithms are not lost when moving away from legacy DATA2 identity;
- durable source reconstruction preserves the exact source/control interpretation that produced authoritative source facts rather than silently synthesizing missing facts or reparsing under incompatible semantics;
- provenance heterogeneity is recorded precisely but is not a generic target-training eligibility, identity or partition axis;
- advisory compatibility policy/group assignment cannot change scientific source/frame/feature/statistical identity;
- unresolved or partial electronic provenance can proceed through the **assembled** current-generation path when required numerical labels are usable;
- existing proven parsing, frame-array, geometry, temperature, reference-cell, strain, eligibility, duplicate, raw-feature, event, autocorrelation, material-profile, partition and parallel-execution algorithms are reused rather than gratuitously reimplemented;
- retained/reused evidence is rebound to current scientific authorities without preserving retired compatibility-bound ancestry;
- material-specific profile science remains provider-owned while the neutral core enforces a material-agnostic rebinding/persistence contract;
- persisted/restarted neutral state remains scientifically usable, not merely digest-equal;
- invalid transitional objects cannot masquerade as current-generation scientific authorities;
- the old production target-size runtime remains behaviorally intact and isolated until P4;
- functional regression/integration evidence is mandatory, while long GPU/production qualification remains deferred.

## Frozen design decisions

These decisions are frozen implementation constraints.

### 1. Version-agnostic durable naming

`V7` remains a workplan/generation identifier only. New product package names, class/function names, persisted schema identifiers and current-generation scientific concepts introduced by P1 must not carry `v7_`, `V7`, `mdstats.v7-*`, or equivalent architecture-revision prefixes.

The semantic package `mdstats.training_data.neutral_substrate` and version-agnostic names already introduced are acceptable. Do not reintroduce aliases or compatibility shims for unpublished `v7_neutral_substrate` / `V7*` symbols.

### 2. One assembled current-generation scientific-owner chain

The accepted scientific chain is:

```text
source files / manifest
  -> existing parser/cache machinery
  -> normalized per-frame arrays + precise compatibility-neutral source facts/provenance
  -> SourceAuthority
  -> CanonicalFrameAuthority
  -> NeutralFeatureEvidence
       -> provider-owned typed material-profile rebinding
  -> NeutralStatisticalBase
```

Every semantic arrow must execute through the real current-generation owner. Legacy objects may be produced in parallel for the old runtime until P4, but they cannot be scientific parents or required semantic intermediates of the new chain when they encode compatibility-domain authority.

### 3. Canonical frame identity is constructed from the actual valid numerical frame payload

The current-generation canonical-frame owner consumes normalized per-frame arrays containing the real training values, not merely legacy `TrainingFrameRecord` metadata or a pre-existing compatibility-bound label digest.

The canonical label identity for each frame binds, as configured and applicable:

- selected energy channel and semantic role;
- energy units and normalization;
- entropy/free-energy convention;
- derivative/stress convention identity;
- actual canonical energy value;
- actual canonical force array;
- actual canonical stress array;
- label-fingerprint policy/tolerances.

It is forbidden to obtain an authoritative canonical label digest by replacing actual required values with `None`, copying a legacy `label_payload_digest`, hashing only presence booleans/metadata, or hashing a missing configured-required label and treating the result as a valid labeled scientific identity.

A frame may still possess source-occurrence and geometry identity when a required label is unavailable or invalid, because physical-frame bookkeeping, rejection diagnostics, raw geometry evidence or other non-label consumers may still need the frame. However:

- authoritative canonical label identity exists only after the configured required-label set is proven present, shape-valid, finite and canonicalizable;
- authoritative labeled-configuration identity exists only when authoritative canonical label identity exists;
- geometry-duplicate reasoning may include physical frames independently of label validity;
- labeled-duplicate reasoning must not treat a frame lacking authoritative canonical label identity as a valid labeled configuration.

The exact representation of this distinction — optional identity fields, an explicit status, a split internal record, or another minimal equivalent — is delegated, but the authority boundary is not.

### 4. Current-generation frame construction does not require `label_domain_id`

No current-generation source/frame builder may require resolved compatibility-domain assignment in order to construct canonical frames. The new canonical-frame path must not require legacy DATA3 to run first merely because legacy DATA3 requires `label_domain_id`.

The old DATA3 builder may remain unchanged and reachable only through the old runtime until P4.

### 5. `SourceAuthority` retains downstream-required compatibility-neutral source facts and durable source/control identity

Removing compatibility-domain authority must not discard independent scientific facts that the canonical owner and reused algorithms require.

`SourceAuthority` / `SourceRecord` must preserve, in a version-agnostic form, every source fact required by the current-generation frame/statistical path. At minimum this includes:

- full composition identity sufficient to validate atom count and species counts, not only an opaque composition digest;
- ensemble / thermodynamic-control identity required by temperature-condition and strain-context interpretation;
- actual source quality assessment status/outcome required by established frame eligibility semantics;
- selected energy channel/units/semantic role;
- precise electronic-structure provenance;
- source-control / control-bundle interpretation identity sufficient to prove that a later direct-source rebuild is using the same authoritative control semantics that produced the source record;
- ensemble-certificate or equivalent control-interpretation binding where that certificate owns the authoritative ensemble fact;
- reference/replica/assertion facts used by current downstream algorithms;
- timestep or equivalent temporal source fact wherever the current statistical path requires it.

Compatibility grouping, `label_domain_id`, and advisory grouping-policy identity remain excluded.

Do not reconstruct authoritative ensemble or quality state from generic assertions when an actual source field owns that fact. Do not replace real quality state with synthetic values such as `"unrestricted"` merely because a source passed a coarse source-usability check.

When a direct VASP/current-source canonical builder reopens a source represented by persisted `SourceAuthority`, it must verify not only immutable source-file identity but also the relevant persisted control/control-semantics binding before using newly parsed controls or energy-channel interpretation. A matching source SHA/signature alone is insufficient if parser/control-semantics version changes could reinterpret the same bytes.

P1 current-generation persistence is still unpublished/provisional. Therefore deserialization must **not fabricate newly authoritative scientific facts** that were absent from an older provisional payload. In particular, missing composition, ensemble, quality or control-interpretation facts must not be repaired with fallback values such as reconstructed formula strings, `"unknown"`, `"not_requested"`, or similar permissive defaults and then accepted as current authority. The minimum-complexity preferred outcome is to bump the affected ordinary schema version(s) as needed and reject obsolete provisional payloads explicitly. A migration adapter is permitted only if repository evidence demonstrates a real supported persisted consumer, and such migration must recover/prove the actual facts rather than invent them.

### 6. Reuse normalized frame/parsing and established DATA3 algorithms without semantic or parallelization drift

`FrameData`-equivalent arrays and existing VASP/cache/parser machinery are the low-level input to current-generation canonical-frame construction.

Reuse the established:

- source/frame membership and composition validation;
- geometry fingerprinting;
- temperature-condition construction;
- reference-cell resolution;
- strain calculation/context classification;
- frame eligibility;
- duplicate/labeled-duplicate detection;
- per-run construction/parallel-execution machinery where applicable.

The current-generation builder must validate atom count and composition against `SourceAuthority`, not against the frame arrays themselves. It must pass the actual source ensemble and quality assessment facts into reused temperature/strain/eligibility algorithms.

Prefer a shared per-run construction kernel or another minimal consolidation that lets legacy DATA3 and the canonical owner reuse the same proven algorithms while specializing only the scientific identity fields that genuinely differ. A serial-only duplicate implementation that discards established `parallel_workers` / isolated per-run execution is not an acceptable durable endpoint when the existing machinery is applicable.

No production-scale performance qualification is required in P1; preservation is established by structure, functional parallel-path regression and bounded execution.

### 7. Source authority remains compatibility-policy neutral

`SourceAuthority.content_digest`, source membership eligible for canonical-frame construction, corpus atomic-reference identifiability and downstream scientific lineage exclude:

- `label_domain_id`;
- compatibility-group assignment;
- `LabelCompatibilityPolicy.policy_digest`;
- legacy label-domain catalogs;
- aggregate parent digests containing those values.

Advisory compatibility reports may still be serialized and inspected, but only as non-authoritative diagnostics.

### 8. Required-label validity is frame-aware and precedes label authority

Source-level aggregate label counts are insufficient to authorize every frame. The canonical frame builder/eligibility owner inspects the actual configured numerical values.

- the configured required-label contract is resolved explicitly from the active training/eligibility representation before authoritative canonical label identity is granted;
- required properties are present for each affected frame when required by that configured representation;
- supplied values have valid shape, are finite and canonicalizable;
- optional properties may be absent when the configured operation does not require them;
- supplied `NaN`, `+inf` and `-inf` cannot receive canonical scientific identity;
- missing configured-required energy, forces, or required stress cannot receive authoritative canonical label/labeled-configuration identity merely because a digest helper can encode `None`;
- explicit user filters and demonstrated mechanical training-engine constraints remain valid hard exclusions;
- actual source quality assessment remains part of established eligibility semantics;
- provenance heterogeneity alone is not a hard exclusion.

The validation/eligibility implementation may be internally staged however is simplest, but it must not construct an authoritative canonical label identity first and only afterward discover that the frame lacked a configured-required label. If physical-frame records are retained for an ineligible/missing-label frame, the representation must make their non-label authority explicit and downstream labeled consumers must honor it.

### 9. Neutral DATA4 reuse is scientific-evidence rebind, not identity laundering

Existing DATA4 raw-feature/event/material-profile computations may be reused when the physical/scientific values remain valid. Their legacy outer container identities must not be copied as scientific ancestry if those identities include retired DATA2/DATA3 compatibility semantics.

The neutral evidence layer binds reused records to `SourceAuthority` and `CanonicalFrameAuthority` with current-generation frame-record digests.

### 10. Material-profile rebinding is generic at the core and provider-owned in scientific detail

The neutral core must not encode LTA or any other material as a privileged scientific special case. It owns a small material/profile-agnostic contract:

```text
partition profile wrapper + typed scientific payload
    -> provider-owned rebind against CanonicalFrameAuthority
    -> rebound typed scientific payload
    -> recomputed scientific payload digest
    -> generic ProfileFeatureCatalog bound to canonical frame authority
```

For every partition-stage material-profile provider entering `NeutralFeatureEvidence`:

1. resolve/access the typed scientific payload;
2. invoke a provider-owned typed rebinding operation or semantically equivalent provider-specific adapter;
3. replace every scientific frame/catalog lineage field with the corresponding `CanonicalFrameAuthority` / canonical frame-record identity while preserving physical/profile state;
4. recompute the typed scientific payload digest;
5. construct/wrap the generic `ProfileFeatureCatalog` using its supported API;
6. preserve enough typed payload state for deterministic serialization/restart reconstruction;
7. reject the provider explicitly if its lineage cannot be proven neutral or it does not implement the required rebind contract.

The neutral core must **not**:

- branch on `extension_id == "lta"` to perform material-specific scientific reconstruction;
- recursively/introspectively rewrite arbitrary payload dictionaries based on field-name guesses;
- copy an opaque legacy `scientific_payload_digest` into a new wrapper and assume it is neutral;
- silently accept an unsupported provider.

A lightweight dispatch/protocol/provider-adapter surface is sufficient. Do not build a generalized plugin framework beyond what current providers require.

#### LTA mandatory reference implementation

LTA is the required P1 reference implementation because it is currently reachable and its typed payload stores frame lineage. The LTA provider/adapter must at minimum produce:

```text
LtaPartitionFeatureCatalog.frame_catalog_digest
    = CanonicalFrameAuthority.content_digest

for every LtaFramePartitionRecord:
    frame_record_digest
        = CanonicalFrameAuthority.frame(frame_uid).content_digest
```

LTA policy, frame state, mobile-site state and physical evidence remain unchanged unless independently invalidated. Re-running expensive LTA geometry analysis solely to obtain new identity is not required when typed reconstruction is scientifically sufficient.

### 11. Rebound typed profile payloads are durable across restart

A digest-bound generic wrapper is not sufficient if the typed payload becomes unavailable after serialization.

After round-trip persistence/reconstruction of `NeutralFeatureEvidence` and/or its owning persisted state:

- each supported rebound partition profile can resolve its typed scientific payload;
- its rebound frame/catalog lineage remains canonical;
- provider consumers such as profile-state-change detection execute successfully;
- `NeutralStatisticalBase` can be rebuilt/consumed without requiring the old legacy profile payload as hidden in-memory state.

The exact persistence realization is delegated: embedding, companion typed-payload storage, existing sharded/Merkle storage, or another minimal durable mechanism is acceptable if it preserves one scientific authority and avoids duplicate scientific copies.

### 12. Invalid legacy DATA3-to-canonical conversion cannot masquerade as scientific authority

A builder that has only legacy `TrainingFrameRecord` metadata and no actual numerical energy/force/stress values cannot produce an authoritative `CanonicalFrameAuthority`.

The removed `build_canonical_frame_authority_from_data3_catalog()` behavior that substituted `None` for actual labels was scientifically invalid and must remain absent from the neutral package/current-generation API.

If repository evidence demonstrates a genuine migration-only need, reopen only this surface and use an explicitly non-authoritative migration type/path that cannot be consumed where `CanonicalFrameAuthority` is required. It must not share the same scientific schema/type while omitting numerical-label identity.

### 13. Neutral statistical owner remains typed and current-generation

`NeutralStatisticalBase` / unit construction requires the version-agnostic `SourceAuthority`, `CanonicalFrameAuthority` and `NeutralFeatureEvidence` (or semantically equivalent current-generation types) and rejects silent substitution of legacy DATA2/DATA3/DATA4 containers.

Retain type/lineage checks unless a demonstrably cleaner equivalent provides the same protection.

### 14. Old production runtime remains isolated until P4

The current prepare/select-target-size orchestration may continue to build/use legacy DATA2/DATA3/DATA4/DATA5 during P1-P3. P1 must not switch the production target-size route or expose the new substrate through public campaign orchestration.

Isolation is not permission for the new substrate itself to depend scientifically on legacy compatibility-domain owners.

## Implementation authority

### Frozen

The protected concerns and frozen decisions above are authoritative, including:

- actual numerical-label identity and the rule that configured-required-label validity precedes authoritative label/labeled-configuration identity;
- compatibility-neutral but scientifically complete source facts;
- durable source/control interpretation binding and no synthesized source facts during provisional persistence reconstruction;
- real source composition/ensemble/quality semantics in reused algorithms;
- provider-owned material-profile rebinding behind a material-agnostic neutral-core contract;
- durable typed profile restart reconstruction;
- no invalid legacy DATA3 object masquerading as canonical scientific authority;
- preservation of applicable established per-run parallel machinery;
- compatibility neutrality and old-runtime isolation;
- acceptance boundaries below.

### Delegated

Implementation may choose:

- exact helper/file decomposition;
- shared legacy/canonical per-run kernel versus another semantically equivalent reuse structure;
- exact version-agnostic source-fact representation;
- exact internal representation distinguishing physical-frame identity from authoritative label/labeled-configuration identity;
- exact affected schema version numbers, provided obsolete provisional payloads cannot silently synthesize authoritative facts;
- the small provider rebind dispatch/protocol API and adapter placement;
- typed profile persistence mechanism, provided it is durable and single-authority;
- cache/local data layout and internal performance mechanics;
- exact semantic class/function names, provided durable names stay version-agnostic.

Choose the minimum product complexity satisfying the frozen scientific contract. Avoid a second parser, duplicate numerical algorithms, field-name-based generic payload rewriting, speculative generalized plugin framework, or compatibility machinery for unpublished provisional state without a demonstrated consumer.

### Reopen only on evidence

Reopen only the affected design surface if repository evidence shows one of the following:

- normalized frame arrays cannot represent a required training label/convention without loss;
- retaining physically useful frames without authoritative labels is incompatible with an established downstream contract that cannot be safely adapted;
- a compatibility-neutral source fact or control-interpretation binding required by the canonical/statistical path cannot be represented without importing a retired compatibility authority;
- an existing material-profile provider has an unavoidable scientific dependency on retired compatibility identity rather than merely stale lineage fields;
- a reused DATA4 scientific record becomes invalid when rebound to canonical frame authority rather than merely requiring identity reconstruction;
- a genuine supported migration consumer requires legacy DATA3-to-new conversion or old provisional P1 persistence and cannot use/recover the real numerical/source facts.

Do not silently carry legacy identity forward or synthesize missing scientific facts in lieu of reopening.

## Entry conditions

- Implementation branch is reconciled with P1 revision 5.
- Preserve already-valid P1A3 work: version-agnostic naming, compatibility-neutral source digest behavior, real source composition/ensemble/quality facts, real numerical frame-array construction, source/frame composition validation, typed neutral-statistical inputs, generic profile provider dispatch, typed LTA canonical rebinding/restart, invalid DATA3-adapter removal, preserved per-run parallel construction, compatibility-policy invariance, and runtime isolation.
- Treat the configured-required-label authority ordering, strict current-generation source persistence/control binding, assembled P1-E3 sensitivity coverage, and real-owner P1-E4 source-fact evidence as the active rework surfaces.
- Existing DATA2/DATA3/DATA4/DATA5 and parallel-resource regression baselines are understood; unrelated pre-existing failures are recorded rather than absorbed.

## Pass P1-A — source-map reconciliation

Update `P1_SOURCE_MAP.md` and directly affected internal architectural notes so the authoritative path is unambiguous:

```text
precise compatibility-neutral source facts/provenance/control binding
 + normalized per-frame arrays carrying actual E/F/stress/geometry
   -> SourceAuthority
   -> CanonicalFrameAuthority
        -> physical/source/geometry frame authority
        -> authoritative label/labeled identity only after configured-required-label validity
   -> NeutralFeatureEvidence
        -> provider-owned typed material-profile rebind
   -> NeutralStatisticalBase
```

The source map must state explicitly that:

- canonical-frame label identity comes from actual valid numerical frame arrays, not legacy DATA3 label digests or missing required values hashed as `None`;
- physical/source/geometry frame bookkeeping may exist without authoritative label identity where downstream non-label consumers require the frame;
- `SourceAuthority` retains composition/ensemble/quality, source/control interpretation binding and other downstream-required scientific facts while excluding compatibility authority;
- current-generation source persistence does not synthesize missing authoritative facts from obsolete provisional payloads;
- legacy DATA3 may coexist for old-runtime isolation but is not a required parent of canonical frame authority;
- material-profile rebinding is generic at the neutral-core boundary and provider-owned in scientific detail;
- LTA is the mandatory P1 reference provider, not a neutral-core special case;
- typed rebound profile payloads survive restart;
- CV is not part of the neutral pre-target substrate;
- durable product/schema naming remains version-agnostic.

This pass is non-executable. Do not alter old runtime specifications to pretend P4 cutover has occurred.

## Pass P1-B — source provenance, source facts and eligibility authority

Preserve/extend the version-agnostic source authority so that:

- full `ElectronicStructureFingerprint`-equivalent provenance is retained;
- unresolved/partial provenance is diagnostic rather than a generic blocker;
- compatibility grouping is advisory only;
- corpus/current-operation atomic-reference identifiability is not split by compatibility domain;
- source scientific/content identity excludes advisory compatibility policy/group lineage;
- source eligibility for canonicalization means at least one frame can potentially contribute;
- compatibility-neutral source facts required by P1-C/P1-D are retained with their real values, including composition/atom count, ensemble and source quality status/outcome;
- source/control interpretation identity needed to reproduce those facts is retained strongly enough for later direct-source rebuild verification;
- obsolete provisional source-authority/source-record payloads lacking newly authoritative facts fail explicitly rather than receiving invented defaults.

### P1-B acceptance

- DFT, DFT+U, hybrid, smearing/numerical variants can coexist when required labels are usable;
- unresolved provenance remains visible;
- changing only advisory compatibility policy changes advisory output but not `SourceAuthority.content_digest` or source membership eligible for canonicalization;
- no `label_domain_id` is required by the current-generation source owner;
- source round-trip preserves the downstream-required scientific facts and source/control interpretation binding exactly;
- stale/incomplete provisional payloads cannot become current authority through fallback `composition`, `ensemble`, `quality` or control values;
- a direct-source canonical rebuild rejects a source/control interpretation mismatch even when the immutable source-file identity still matches.

### P1-B verification

1. focused provenance/source-policy/usability/source-fact tests;
2. affected DATA2/source-ingestion regression;
3. serialization/restart round trip including composition/ensemble/quality and control-interpretation facts;
4. strict obsolete-provisional-payload rejection or explicit proven migration test if a real migration consumer is demonstrated;
5. direct-source reparse/rebuild mismatch test for control/control-semantics identity;
6. structural proof that compatibility-domain/policy identity is excluded from source scientific lineage.

## Pass P1-C — canonical frame authority from actual frame arrays and real source facts

### P1-C1 — real canonical-frame input boundary

Construct `CanonicalFrameAuthority` from:

- `SourceAuthority`;
- normalized `FrameData`-equivalent arrays keyed by run;
- existing temperature-target/reference-cell/policy inputs needed for established frame metadata algorithms.

The authoritative builder must not require `TrainingFrameCatalog` or another legacy DATA3 object.

Validate directly against `SourceAuthority` plus normalized arrays:

- exact run membership;
- frame counts;
- source-frame indices;
- atom count;
- species/composition counts;
- other established source/frame consistency invariants.

A frame array must not pass source validation merely because `data.n_atoms == len(data.atomic_numbers)`.

### P1-C2 — reuse established algorithms with actual owner facts

For every frame, compute through the real implementation path:

- occurrence/frame UID;
- geometry fingerprint;
- configured required-label validity;
- canonical label payload from actual valid E/F/stress values and interpretation metadata when label authority exists;
- labeled-configuration fingerprint only when authoritative canonical label identity exists;
- separate electronic-structure provenance reference;
- temperature/condition metadata using the actual source ensemble;
- strain/reference-cell metadata and context using the actual source ensemble/assertions;
- frame eligibility using actual numerical labels and actual source quality assessment status/outcome;
- geometry duplicate catalog over physical geometry identity and labeled-duplicate catalog only over authoritative labeled identities.

Do not synthesize source quality status from coarse `target_usable` state. Do not recover ensemble from assertions when `SourceAuthority` owns it. Do not create authoritative label/labeled identity and only afterward discover a missing configured-required property.

### P1-C3 — unresolved provenance, required-label authority and numerical validity

A source whose electronic provenance is unresolved/partial but whose configured required labels and mechanical source facts are valid must traverse:

```text
SourceAuthority -> CanonicalFrameAuthority
```

No `label_domain_id` assertion may appear on this path.

The real canonical-frame owner must distinguish **physical frame presence** from **label authority**:

- missing required energy prevents authoritative canonical label/labeled-configuration identity for that frame;
- missing required forces prevents authoritative canonical label/labeled-configuration identity when forces are configured required;
- missing stress prevents authoritative canonical label/labeled-configuration identity only when stress is configured required;
- optional absent stress remains permissible and must not be converted into a hard failure merely to simplify implementation;
- non-finite supplied required energy/forces/stress cannot receive valid canonical scientific identity;
- a helper's ability to deterministically hash `None` is not authorization to use that digest as current scientific label identity.

If the current owner retains a frame record for rejected/missing-label frames, its label-authority state and downstream behavior must be unambiguous. Such a frame may participate in geometry/source diagnostics as scientifically appropriate but must not masquerade as a valid labeled configuration or enter labeled-duplicate identity as one.

### P1-C4 — preserve proven parallel construction

Canonical-frame construction must preserve applicable per-run parallel execution or share the existing per-run frame-construction machinery without reintroducing compatibility-domain identity. Bounded worker=1 and worker>1 runs must be scientifically identical, including the distinction between physical-only and authoritative labeled identities.

### P1-C acceptance

Prove through the real canonical-frame owner that:

- identical actual canonical labels under different provenance/grouping produce identical canonical label identity;
- advisory grouping-policy changes do not alter frame UID, canonical label identity, labeled-configuration identity or canonical-frame-authority identity;
- changing actual energy changes canonical label and labeled-configuration identity;
- changing actual force or stress changes identity when configured;
- changing semantic/unit/convention interpretation changes identity;
- missing configured-required energy cannot obtain authoritative canonical label/labeled-configuration identity;
- missing configured-required forces cannot obtain authoritative canonical label/labeled-configuration identity;
- missing stress is rejected from label authority when stress is required but remains acceptable when stress is optional;
- non-finite supplied required values fail canonicalization/validity before authoritative label identity is granted;
- physical/source/geometry frame identity remains usable where scientifically required without being confused with valid labeled identity;
- labeled-duplicate detection excludes frames without authoritative labeled identity while geometry-duplicate behavior remains correct;
- mismatched atom count or composition between `SourceAuthority` and `FrameData` is rejected;
- NPT/NPH/other ensemble semantics reach temperature/strain owners correctly and affect context only where scientifically applicable;
- unqualified source quality is not silently promoted to eligible frame state;
- unresolved provenance with usable labels succeeds;
- worker-count changes do not change scientific output;
- the new frame owner feeds P1-D without legacy DATA3.

### P1-C verification cycle

1. focused canonical numerical identity and authority-boundary tests covering present, missing, optional, non-finite, shape and semantic cases;
2. explicit missing-energy, missing-force, required-stress-missing and optional-stress-missing real-builder cases;
3. focused geometry-versus-labeled duplicate tests including a physical frame without authoritative label identity;
4. focused source/frame composition consistency tests;
5. focused ensemble/temperature/strain-context tests;
6. focused source-quality/eligibility tests;
7. worker=1 versus bounded parallel-worker equivalence;
8. affected DATA3 frame/eligibility/temperature/reference-cell/strain/duplicate and parallel-resource regression;
9. canonical frame serialization/restart, including any new label-authority representation;
10. structural negative check that the authoritative builder does not require `TrainingFrameCatalog`, `label_domain_id`, legacy label-domain identity or compatibility-policy-containing parent digest;
11. bounded integration carrying the real canonical frame authority into neutral feature evidence.

## Pass P1-D — neutral feature/correlation evidence and material-profile contract

### P1-D1 — raw feature/event evidence rebind

Reuse valid DATA4 raw-feature/event calculations, but bind them to `SourceAuthority` and `CanonicalFrameAuthority`:

- per-frame evidence uses canonical frame-record digests;
- raw-feature catalogs bind current source/frame authority digests;
- event catalogs bind rebound raw-feature catalog and canonical frame authority;
- legacy DATA2/DATA3/DATA4 aggregate digests do not become scientific ancestors merely for transition convenience.

An old DATA4 bundle may be a **value source** while the old runtime exists; it is not current scientific authority.

Downstream neutral evidence must preserve the P1-C distinction between physical frame authority and valid labeled identity. A consumer that only needs geometry/physical evidence may consume the physical frame record; a consumer that claims labeled-configuration authority must require a valid authoritative label identity.

### P1-D2 — material-agnostic provider rebinding boundary

Introduce the minimum typed provider contract necessary for partition-stage profile evidence to rebind itself to `CanonicalFrameAuthority`.

The neutral core performs generic dispatch/validation only. Provider-owned code performs material-specific typed reconstruction. Unsupported/opaque providers are rejected unless their typed payload is independently proven lineage-neutral.

Acceptance must structurally demonstrate there is no neutral-core `if extension_id == "lta"` or equivalent material-specific scientific branch and no fallback that simply copies an opaque legacy scientific payload digest.

### P1-D3 — LTA reference provider

Implement LTA through the generic provider contract. Rebind its typed frame/catalog lineage to canonical frame identity, preserve physical state/policy, recompute its scientific digest, and wrap it using the supported generic profile API.

Verify `profile_partition_state_changed()` and downstream neutral consumers against the rebound typed payload.

### P1-D4 — durable typed profile persistence/restart

Persist enough rebound typed profile state that a serialized/reconstructed `NeutralFeatureEvidence` can resolve supported typed partition profiles and continue into the neutral statistical path without hidden dependence on the original in-memory legacy payload.

Round-trip digest equality alone is insufficient.

### P1-D5 — neutral statistical base

Preserve the typed current-generation statistical owner consuming only:

- `SourceAuthority`;
- `CanonicalFrameAuthority`;
- `NeutralFeatureEvidence`.

Retain temporal/autocorrelation blocks, events/protected windows, physical condition/regime, replica/structural-realization/reference-group evidence, duplicates/correlation groups, protected outer roles, independence grading and leakage/disjointness checks.

Continue to forbid compatibility `label_domain_id` in unit identity, compatibility-policy ancestry, provenance as a mandatory role-budget axis, and pre-target CV/fold authority.

### P1-D acceptance

- compatibility-policy changes leave neutral raw/profile/event evidence, unit IDs/catalog, protected roles and neutral-statistical-base identity unchanged;
- actual canonical-label changes propagate through canonical frame lineage and invalidate descendants where lineage is scientifically part of identity;
- physical/profile changes alter relevant evidence/identities;
- physical-only frames cannot be silently consumed as valid labeled configurations by a label-dependent downstream owner;
- provider dispatch is material-agnostic and unsupported opaque providers fail explicitly;
- LTA executes through the same generic provider contract used for future material providers;
- rebound LTA typed lineage is canonical;
- after neutral evidence serialization/restart, LTA typed payload resolves and `profile_partition_state_changed()` plus `NeutralStatisticalBase` consumer/rebuild paths still work;
- required outer/protected roles remain disjoint and leakage checks execute on real neutral units;
- no CV plan is required;
- legacy source/frame/DATA4 containers cannot silently substitute.

### P1-D verification cycle

1. focused raw-feature/event rebinding tests;
2. focused propagation/guard tests for physical-only versus authoritative labeled frame use where affected;
3. focused generic provider dispatch/rejection tests;
4. focused LTA typed provider-rebind tests;
5. typed profile serialization/restart followed by real provider consumer execution;
6. neutral partition/correlation/leakage tests;
7. affected DATA4/DATA5/profile/LTA/event/statistical-role regression;
8. structural lineage checks proving rebound typed payloads no longer retain legacy DATA3 frame/catalog ancestry;
9. real-owner integration from P1-B/P1-C through neutral feature evidence into neutral statistical base.

## Pass P1-E — package closure

Reconcile the complete P1 diff against the parent workplan and revision 5, then re-derive the affected surface from the assembled candidate.

### P1-E1 — required real-owner integration

Execute bounded deterministic integration through actual P1 owners:

```text
source files / manifest
 -> existing parser/cache machinery yielding normalized frame arrays
 -> SourceAuthority carrying real compatibility-neutral source facts and control binding
 -> CanonicalFrameAuthority built from actual frame arrays with required-label authority enforced
 -> NeutralFeatureEvidence using provider-owned typed profile rebinding
 -> NeutralStatisticalBase
```

Allowed cost bounding: small synthetic VASP/source fixtures, bounded frame counts, existing parser/cache helpers, bounded CPU parallelism; no expensive model training/GPU work.

Forbidden acceptance substitutions include:

- legacy DATA3 as semantic owner of canonical numerical identity;
- helper-only canonical identity tests while assembled owner is broken;
- prebuilt canonical frame authority instead of its real builder;
- manually `replace()`-mutated `SourceAuthority`/`SourceRecord` values as proof that the source-ingestion owner propagated ensemble or quality correctly;
- synthetic assertion-derived ensemble/quality values instead of source-owned facts;
- permissive deserializer defaults standing in for persisted source facts that were never present;
- direct helper hashing of missing labels as proof that the assembled owner correctly enforces required-label authority;
- outer-profile-only tests bypassing typed provider rebinding;
- test-harness reimplementation of canonical/profile logic.

### P1-E2 — compatibility-policy invariance proof

Using the same scientific inputs, build the complete P1 chain under at least two advisory compatibility policies producing observably different advisory output. Require equality of all applicable scientific state/behavior:

- source membership and `SourceAuthority.content_digest`;
- canonical frame UIDs/labels/labeled-configuration identities and `CanonicalFrameAuthority.content_digest`;
- physical-only versus authoritative-label status where applicable;
- rebound raw/event/profile scientific identities;
- `NeutralFeatureEvidence.content_digest`;
- neutral unit IDs/catalog;
- protected outer roles;
- `NeutralStatisticalBase.content_digest`.

Only advisory diagnostics may differ.

### P1-E3 — assembled numerical/semantic/required-label sensitivity proof

Through the **real canonical-frame builder**, execute each applicable case rather than relying on direct digest-helper tests:

1. change an actual energy value and require changed canonical label/labeled-configuration/frame authority lineage;
2. change an actual force value, or configured stress value when force is not part of the representation, and require changed canonical label identity;
3. change at least one semantic/unit/convention input consumed by the real builder and require changed canonical identity;
4. supply a non-finite configured-required value and require failure/non-authority before valid canonical label identity is granted;
5. remove configured-required energy and prove the frame cannot obtain authoritative canonical label/labeled-configuration identity;
6. remove configured-required forces and prove the same when forces are required;
7. exercise stress absence in both required and optional modes, proving required absence blocks label authority while optional absence does not.

For cases where the physical frame remains represented, also prove that geometry/source identity remains internally coherent and labeled-duplicate/label-dependent consumers do not treat the frame as a valid labeled configuration.

Direct helper tests cannot substitute for this assembled owner proof. Evidence must fail if the builder creates a canonical label/labeled fingerprint first and merely marks the frame ineligible afterward.

### P1-E4 — source-fact and control-binding preservation proof

Exercise at least:

- source/frame atom-count or composition mismatch rejection;
- NPT/NPH or another genuinely ensemble-sensitive strain/temperature context through the **real source-ingestion/control owner -> `SourceAuthority` -> canonical builder** chain;
- source quality status/outcome propagation into frame eligibility through the real source-assessment/source-record owner, including an unqualified case;
- persisted source/control interpretation binding during direct-source canonical rebuild, including a negative mismatch case.

The ensemble/quality acceptance evidence must be **proxy-proof**:

- the ensemble value under test must originate from the real parsed/inferred source/control owner, not from a `SourceAuthority`/`SourceRecord` replacement in the test;
- use no ensemble assertion, or deliberately provide a contradictory non-authoritative assertion, so the test would fail if the canonical builder recovered ensemble from assertions instead of the source-owned field;
- the unqualified quality case must originate at or below the real source quality owner before `SourceAuthority` is built; mutating `SourceAuthority` after construction is not acceptance evidence for source-fact propagation;
- bounded synthetic VASP/source inputs and bounded quality-owner fixtures are allowed below the real semantic owner, but the production owner that assigns the source field and the real downstream canonical consumer must execute;
- the control-binding mismatch case must demonstrate that unchanged source-file identity does not authorize reinterpretation under a mismatched persisted control/control-semantics identity.

The test must fail if the canonical builder substitutes assertions/`"unknown"` for real ensemble, synthesizes permissive quality state, or ignores a material persisted source/control interpretation mismatch.

### P1-E5 — unresolved-provenance assembled proof

Construct a bounded unresolved/partial provenance source with valid required numerical labels and execute:

```text
SourceAuthority
 -> CanonicalFrameAuthority from real arrays
 -> NeutralFeatureEvidence
 -> NeutralStatisticalBase
```

The path succeeds without `label_domain_id`; diagnostics still report unresolved provenance.

### P1-E6 — material-profile genericity, LTA and restart proof

Run a bounded LTA partition-stage fixture through the **generic provider rebind boundary**, then through neutral evidence/statistical consumers.

Verify:

- neutral core does not contain LTA-specific scientific branching;
- LTA provider returns a typed payload bound to canonical frame/catalog digests;
- wrapper uses the rebound typed scientific digest;
- no legacy DATA3 lineage survives;
- serialize/reconstruct the neutral evidence/owning state;
- resolve LTA typed payload after restart;
- execute `profile_partition_state_changed()` and the required neutral-statistical consumer/rebuild path after restart;
- unsupported opaque partition provider is rejected rather than rewrapped with its old digest.

### P1-E7 — invalid-adapter and obsolete-authority absence proof

Structurally prove there is no exported/current-generation path by which legacy DATA3 metadata lacking actual E/F/stress can produce an object accepted as authoritative `CanonicalFrameAuthority`.

Keep `build_canonical_frame_authority_from_data3_catalog()` absent from the neutral package/current-generation API. If design is explicitly reopened for a genuine migration consumer, prove the migration type/path cannot enter current scientific-owner APIs.

Also prove there is no deserialization/current-generation migration fallback that manufactures missing composition/ensemble/quality/control facts and returns the result as current `SourceAuthority` without recovering/proving those facts.

### P1-E8 — naming and runtime-isolation proof

Verify:

- no `v7_`, `V7*`, `mdstats.v7-*` product/schema names or aliases;
- current prepare/select-target-size remains on old runtime until P4;
- campaign CLI/public target-size exports do not expose neutral substrate prematurely;
- old runtime remains reachable;
- current P1 substrate does not require old compatibility-domain owners.

### P1-E9 — functional closure evidence

Required executable evidence on the final assembled candidate:

- all P1-B/C/D focused tests;
- affected DATA2/source-ingestion/control/quality regression;
- affected DATA3 geometry/identity/eligibility/temperature/reference-cell/strain/duplicate and parallel-resource regression;
- affected DATA4 raw-feature/event/profile/LTA regression;
- affected DATA5/statistical-role/partition/leakage regression;
- serialization/restart reconstruction for every new current-generation owner and rebound typed profile payload;
- strict obsolete-provisional-source-payload rejection or explicitly justified/proven migration if a real consumer exists;
- direct-source source/control interpretation mismatch rejection;
- P1-E1 real-owner integration;
- P1-E2 compatibility invariance;
- P1-E3 energy + force/stress + semantic + required-label/non-finite authority sensitivity;
- P1-E4 real-owner source-fact/control-binding preservation;
- P1-E5 unresolved-provenance chain;
- P1-E6 generic material-profile/LTA/restart integration;
- P1-E7 invalid-adapter/obsolete-authority absence;
- structural naming/lineage/runtime-isolation checks;
- repository/project-required Python/package checks covering the final affected surface.

A required check that did not execute is not a pass. Green helper tests do not substitute for a broken semantic owner. Source inspection does not substitute for affected executable regression. No full long GPU/production qualification is required for P1; production qualification remains deferred under the parent workplan.

## Preservation / non-goals

- Do not switch production target-size runtime before P4.
- Do not redesign target-size selection algorithm in P1.
- Do not introduce pre-target CV.
- Do not make electronic-structure compatibility grouping a hidden training/partition axis.
- Do not make the neutral core material-specific.
- Do not build a generalized material plugin framework beyond the minimal provider-rebind contract needed by current providers.
- Do not generically mutate arbitrary profile payload dictionaries by guessed field names.
- Do not add a second VASP parser, duplicate frame-normalization implementation or parallel profile-analysis engine solely for the new identity model.
- Do not retain unpublished provisional adapters/aliases or source-persistence compatibility fallbacks merely to keep old P1 tests/artifacts green.
- Do not solve missing-required-label authority by rejecting all physical-frame representation if established non-label consumers scientifically require those frames; preserve the physical-versus-labeled distinction instead.
- Do not perform long GPU training or production-scale qualification in P1.

## Exit gate

P1 is accepted only when the following invariant is true in the **assembled real-owner object graph**:

> Canonical usable source/frame identity is derived from actual compatibility-neutral source facts plus the configured numerical energy/force/stress payload and required interpretation metadata; authoritative canonical label/labeled-configuration identity exists only after the configured required-label set is present, shape-valid, finite and canonicalizable, while physical/source/geometry frame identity remains distinguishable where scientifically needed; unresolved provenance with usable labels traverses the current-generation path without compatibility-domain assignment; persisted source authority preserves and verifies the source/control interpretation that owns composition/ensemble/quality/energy semantics rather than synthesizing absent facts or silently reparsing under incompatible semantics; established source/frame consistency, ensemble, source-quality, strain, eligibility, duplicate and applicable parallel-execution semantics are preserved; neutral raw/event/material-profile evidence is rebound through a material-agnostic core contract with provider-owned typed scientific reconstruction and durable restart resolution; no compatibility-group assignment, compatibility-policy identity, retired DATA2/DATA3/DATA4/profile ancestor digest, invalid DATA3-to-canonical surrogate, obsolete provisional source payload masquerading as current authority, or pre-target CV authority participates in current-generation scientific identity or protected-role assignment; precise provenance remains fully recorded; durable naming is version-agnostic; and the production target-size runtime has not yet switched.

The following are explicitly insufficient for P1 acceptance:

- canonical helper unit tests when the assembled frame authority omits or misinterprets real numerical/source facts;
- creating a stable canonical label/labeled-configuration digest from missing configured-required values and only afterward marking the frame ineligible;
- treating a frame without authoritative label identity as a valid labeled duplicate/configuration merely because its physical frame record exists;
- a legacy DATA3-to-canonical adapter that returns an authoritative canonical type without actual numerical labels;
- source/frame validation that checks frame arrays only against themselves;
- manually replacing `SourceAuthority` ensemble/quality values in tests and treating that as proof of real source-owner propagation;
- assertion-derived `"unknown"` ensemble or synthetic permissive source-quality state in place of source-owned facts;
- permissive provisional deserialization that fabricates missing composition/ensemble/quality/control facts and returns a current authority;
- direct-source rebuild that checks only immutable source-file identity while ignoring a changed persisted control/control-semantics interpretation;
- LTA-specific branching in the neutral core as the profile architecture;
- rebinding only an outer profile wrapper while retaining legacy typed lineage or copying an opaque old scientific digest;
- round-trip digest equality when the typed profile payload cannot be resolved/consumed after restart;
- successful generic-data integration that does not exercise unresolved provenance and real source-fact preservation;
- equality of neutral unit IDs when ancestor scientific digests still depend on compatibility policy;
- source inspection without required affected regression and real-owner integration evidence.

Commit/tag the accepted corrected P1 checkpoint before starting P2.
