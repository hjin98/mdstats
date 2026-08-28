---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P1
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 1
status: active
package_revision: 6
amended_date: 2026-08-28
rework_reason: Independent review after P1A4 confirmed the assembled canonical-frame builder repair but found remaining authority bypasses and restart gaps: the exported direct canonical-identity builder can still mint authoritative label identity from missing labels; canonical record/identity persistence does not enforce label/fingerprint atomicity or deterministic fingerprint coherence; SourceRecord deserialization can lose an authoritative quality outcome; direct VASP canonical rebuild cannot replay explicit manifest companion-file bindings; and mandatory P1-E3 real-owner cases remain incomplete.
---

# P1 — Neutral scientific substrate

## Purpose

Establish the current-generation **scientific identity substrate** without changing the currently reachable target-size runtime. P1 removes compatibility-domain semantics from canonical numerical-label identity and neutral statistical identity while preserving precise electronic-structure provenance, source facts required for scientific interpretation, and proven parsing, feature, correlation, event, material-profile, eligibility, strain, partition and parallel-execution machinery.

The parent V7 workplan remains the generation-level authority, but **durable product code and persisted schema names introduced by P1 are version-agnostic**. The new substrate remains internal/unreachable from the current target-size runtime until P4.

P1 revision 6 preserves all scientifically valid P1A4 work: version-agnostic naming; compatibility-neutral source identity; actual source composition/ensemble/quality facts; canonical construction from real normalized arrays; required-label gating in the assembled frame authority; physical-versus-labeled frame distinction; geometry-versus-labeled duplicate separation; generic provider dispatch with provider-owned LTA rebinding; durable typed-profile restart; removal of the invalid DATA3 adapter; source-control checking; and preserved bounded per-run parallelism.

Revision 6 is a **narrow closure amendment**. It does not reopen the P1 architecture. It closes every remaining path by which current-generation authoritative label/source state can be created or reconstructed without satisfying the same scientific invariants enforced by the assembled owner, and completes the real-owner acceptance evidence required to freeze P1.

P1 remains active until the complete current-generation owner chain closes through real numerical frame data, compatibility-neutral source facts, uniform required-label authority across every authoritative constructor, coherent persistence/restart reconstruction, replayable source/control bindings, provider-owned typed profile rebinding, and affected regression/integration evidence.

## Protected concerns

P1 protects the following product outcomes simultaneously:

- canonical training identity represents the actual numerical labels and semantic/unit/convention information required to interpret them;
- **every authoritative constructor, record, identity object, deserializer and assembled owner obeys the same required-label authority rule**; no secondary helper/export may bypass it;
- physical/source/geometry frame identity may remain available for diagnostics/statistics when scientifically needed, but authoritative canonical label and labeled-configuration identity is never granted before the configured required-label contract is satisfied;
- authoritative label digest and labeled-configuration fingerprint are an internally coherent pair and cannot be independently absent, forged or inconsistent;
- compatibility-neutral source facts needed by downstream scientific algorithms are not lost when moving away from legacy DATA2 identity;
- durable source reconstruction preserves complete source-quality state and the exact source/control/companion-file interpretation that produced authoritative source facts rather than silently synthesizing, dropping or reparsing material facts;
- provenance heterogeneity is recorded precisely but is not a generic target-training eligibility, identity or partition axis;
- advisory compatibility policy/group assignment cannot change scientific source/frame/feature/statistical identity;
- unresolved or partial electronic provenance can proceed through the **assembled** current-generation path when required numerical labels are usable;
- existing proven parsing, frame-array, geometry, temperature, reference-cell, strain, eligibility, duplicate, raw-feature, event, autocorrelation, material-profile, partition and parallel-execution algorithms are reused rather than gratuitously reimplemented;
- retained/reused evidence is rebound to current scientific authorities without preserving retired compatibility-bound ancestry;
- material-specific profile science remains provider-owned while the neutral core enforces a material-agnostic rebinding/persistence contract;
- persisted/restarted neutral state remains scientifically usable, not merely digest-shaped or digest-equal;
- invalid transitional objects cannot masquerade as current-generation scientific authorities;
- the old production target-size runtime remains behaviorally intact and isolated until P4;
- functional regression/integration evidence is mandatory, while long GPU/production qualification remains deferred.

## Frozen design decisions

### 1. Version-agnostic durable naming

`V7` remains a workplan/generation identifier only. New product package names, class/function names, persisted schema identifiers and current-generation scientific concepts introduced by P1 must not carry `v7_`, `V7`, `mdstats.v7-*`, or equivalent architecture-revision prefixes.

The semantic package `mdstats.training_data.neutral_substrate` and version-agnostic names already introduced are acceptable. Do not reintroduce aliases or compatibility shims for unpublished `v7_neutral_substrate` / `V7*` symbols.

### 2. One assembled current-generation scientific-owner chain

The accepted scientific chain is:

```text
source files / manifest / explicit companion bindings
  -> existing parser/cache/control machinery
  -> normalized per-frame arrays + precise compatibility-neutral source facts/provenance/control binding
  -> SourceAuthority
  -> CanonicalFrameAuthority
  -> NeutralFeatureEvidence
       -> provider-owned typed material-profile rebinding
  -> NeutralStatisticalBase
```

Every semantic arrow must execute through the real current-generation owner. Legacy objects may be produced in parallel for the old runtime until P4, but they cannot be scientific parents or required semantic intermediates of the new chain when they encode compatibility-domain authority.

### 3. One canonical required-label authority rule across all authoritative construction paths

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

The configured required-label contract is resolved before **authoritative** label identity is granted. The rule applies uniformly to:

- `CanonicalFrameAuthority` construction;
- any exported or internal `build_canonical_frame_identity()`-equivalent authoritative constructor;
- direct `CanonicalFrameIdentity` / `CanonicalFrameRecord` construction when those types permit label authority;
- deserialization/restart reconstruction;
- duplicate/labeled-configuration conversion helpers;
- future current-generation callers introduced before P1 is frozen.

It is forbidden to obtain authoritative canonical label identity by:

- replacing a configured-required numerical value with `None`;
- hashing a missing required value because a lower-level digest helper can encode `None`;
- copying a legacy `label_payload_digest`;
- hashing only presence booleans/metadata;
- constructing a labeled fingerprint without a valid authoritative label digest;
- invoking a secondary identity constructor that does not know or enforce the required-label representation.

A low-level canonical payload digest helper may remain representation-neutral and permit optional absent values if that is useful. Such a helper is **not itself an authority decision**. Any function returning an authoritative current-generation frame/label identity must either enforce the configured required-label contract itself through the shared authority mechanism or be removed/reclassified as non-authoritative.

Prefer one shared internal required-label validation/authority operation used by every authoritative constructor rather than duplicate policy logic. If `build_canonical_frame_identity()` has no genuine supported owner, removal from the authoritative package surface is lower complexity than maintaining a second authority path.

### 4. Physical frame identity and labeled identity remain distinct

A frame may possess source-occurrence and geometry identity when a required label is unavailable or invalid, because physical-frame bookkeeping, rejection diagnostics, raw geometry evidence or other non-label consumers may still need the frame.

However:

- authoritative canonical label identity exists only after the configured required-label set is proven present, shape-valid, finite and canonicalizable;
- authoritative labeled-configuration identity exists if and only if authoritative canonical label identity exists;
- geometry-duplicate reasoning may include physical frames independently of label validity;
- labeled-duplicate reasoning must not treat a frame lacking authoritative canonical label identity as a valid labeled configuration;
- label-dependent downstream consumers must reject or bypass physical-only frames explicitly rather than relying on incidental `None` handling.

The exact representation of this distinction — optional identity fields, an explicit status, a split internal record, or another minimal equivalent — is delegated, but the authority boundary is frozen.

### 5. Canonical label/fingerprint persistence is self-consistent

`CanonicalFrameIdentity` and `CanonicalFrameRecord` are scientific state, not loose transport structs. Their constructor and deserializer invariants must guarantee:

```text
canonical_label_payload_digest is None
    <=> labeled_configuration_fingerprint is None
```

and, when present:

```text
labeled_configuration_fingerprint
    == labeled_configuration_fingerprint(
           geometry_fingerprint,
           canonical_label_payload_digest,
       )
```

A payload with only one member of the pair, or a labeled fingerprint that does not match the stored geometry + label digest, must be rejected as invalid scientific state. `has_authoritative_label` may rely on this invariant; it must not be used to mask malformed objects.

Round-trip persistence must preserve physical-only frames and authoritative labeled frames without allowing contradictory combinations to enter the current owner graph.

### 6. Current-generation frame construction does not require `label_domain_id`

No current-generation source/frame builder may require resolved compatibility-domain assignment in order to construct canonical frames. The new canonical-frame path must not require legacy DATA3 to run first merely because legacy DATA3 requires `label_domain_id`.

The old DATA3 builder may remain unchanged and reachable only through the old runtime until P4.

### 7. `SourceAuthority` retains complete downstream-required compatibility-neutral source facts

Removing compatibility-domain authority must not discard independent scientific facts that the canonical owner and reused algorithms require.

`SourceAuthority` / `SourceRecord` must preserve, in a version-agnostic form, every source fact required by the current-generation frame/statistical path. At minimum this includes:

- full composition identity sufficient to validate atom count and species counts;
- ensemble / thermodynamic-control identity required by temperature-condition and strain-context interpretation;
- actual source quality assessment status **and outcome** required by established frame eligibility semantics;
- selected energy channel/units/semantic role;
- precise electronic-structure provenance;
- source-control / control-bundle interpretation identity sufficient to prove that a later direct-source rebuild uses the same authoritative control semantics that produced the source record;
- ensemble-certificate or equivalent control-interpretation binding where that certificate owns the authoritative ensemble fact;
- source/manifest locator facts needed to replay the exact explicitly bound companion-file roles that materially participate in source/control identity;
- reference/replica/assertion facts used by current downstream algorithms;
- timestep or equivalent temporal source fact wherever the current statistical path requires it.

Compatibility grouping, `label_domain_id`, and advisory grouping-policy identity remain excluded.

Do not reconstruct authoritative ensemble or quality state from generic assertions when an actual source field owns that fact. Do not replace real quality state with synthetic values such as `"unrestricted"` merely because a source passed a coarse source-usability check.

### 8. Source persistence is structurally strict; obsolete provisional state does not become current authority

P1 current-generation persistence remains unpublished/provisional. Therefore current source-record deserialization must not fabricate **or silently drop** authoritative scientific facts.

For the current source-record schema:

- every scientific field emitted by `to_dict()` that belongs to authoritative source state must be structurally present on decode, even when its legitimate value is explicit `null`, empty tuple, or equivalent;
- `quality_assessment_status` and `quality_outcome` must be decoded as a coherent pair according to the established source-quality vocabulary; an omitted outcome must not silently become `None` and make a completed/unqualified source permissive;
- missing composition, ensemble, source quality, source-control digest, ensemble-certificate digest, or required companion/control replay facts must fail explicitly;
- no fallback such as reconstructed formula strings, `"unknown"`, `"not_requested"`, synthetic quality values, or guessed companion paths may return a current `SourceAuthority`.

Because the unpublished `mdstats.source-record.v1` identifier has already represented materially different provisional shapes, the current-generation source-record schema must move to a new ordinary version (for example `mdstats.source-record.v2`) rather than giving one schema identifier incompatible authority contracts. No architecture-generation prefix is permitted. The old provisional shape need not be migrated unless repository evidence demonstrates a genuine persisted consumer; if migration is required, it must recover/prove the actual facts and must not invent them.

Outer source-authority schema versioning may remain unchanged if its decoder unambiguously rejects obsolete nested source-record state and no semantic ambiguity remains; bump it only if implementation evidence shows that is required.

### 9. Direct-source canonical rebuild must replay exact companion/control bindings

When `build_vasp_canonical_frame_authority()` or another direct-source current-generation builder reopens a source represented by persisted `SourceAuthority`, it must reproduce the same source/control interpretation that produced that source authority.

It must verify at least:

- immutable primary source identity;
- relevant source-control/control-semantics binding;
- explicitly bound companion-file role -> locator/identity mapping that participated in the source/control bundle;
- selected energy-channel interpretation used by the source authority.

The currently supported `TrainingDataRunSpec.companion_files` model is part of the accepted source surface. A source that was validly ingested with explicit companion bindings must be able to traverse the direct current-generation canonical rebuild without being spuriously rejected merely because the rebuild dropped those bindings.

Implementation may satisfy this by either:

- retaining sufficient companion role/locator binding information in current-generation source authority; or
- requiring a verified manifest/run-spec input at direct rebuild and checking it against the persisted manifest/source authority before reparsing.

Whichever realization is chosen, the real accepted behavior is:

```text
same source + same explicit companion bindings + same control semantics
    -> direct rebuild succeeds and reproduces the source/control identity

same primary source but changed/missing/rebound material companion/control semantics
    -> direct rebuild rejects
```

Do not guess standard filenames for an explicitly overridden companion binding. Do not weaken the source-control signature check to make companion-bound sources pass.

### 10. Reuse normalized frame/parsing and established DATA3 algorithms without semantic or parallelization drift

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

### 11. Source authority remains compatibility-policy neutral

`SourceAuthority.content_digest`, source membership eligible for canonical-frame construction, corpus atomic-reference identifiability and downstream scientific lineage exclude:

- `label_domain_id`;
- compatibility-group assignment;
- `LabelCompatibilityPolicy.policy_digest`;
- legacy label-domain catalogs;
- aggregate parent digests containing those values.

Advisory compatibility reports may still be serialized and inspected, but only as non-authoritative diagnostics.

### 12. Required-label validity is frame-aware and precedes label authority

Source-level aggregate label counts are insufficient to authorize every frame. The current-generation required-label authority mechanism inspects the actual configured numerical values.

- required properties are present for each affected frame when required by the configured training representation;
- supplied values have valid shape, are finite and canonicalizable;
- optional properties may be absent when the configured operation does not require them;
- supplied `NaN`, `+inf` and `-inf` cannot receive canonical scientific identity;
- missing configured-required energy, forces, or required stress cannot receive authoritative canonical label/labeled-configuration identity merely because a digest helper can encode `None`;
- explicit user filters and demonstrated mechanical training-engine constraints remain valid hard exclusions;
- actual source quality assessment remains part of established eligibility semantics;
- provenance heterogeneity alone is not a hard exclusion.

### 13. Neutral DATA4 reuse is scientific-evidence rebind, not identity laundering

Existing DATA4 raw-feature/event/material-profile computations may be reused when the physical/scientific values remain valid. Their legacy outer container identities must not be copied as scientific ancestry if those identities include retired DATA2/DATA3 compatibility semantics.

The neutral evidence layer binds reused records to `SourceAuthority` and `CanonicalFrameAuthority` with current-generation frame-record digests.

Downstream neutral evidence must preserve the physical-versus-labeled distinction. A consumer that only needs geometry/physical evidence may consume physical frame state; a consumer that claims labeled-configuration authority must require a valid authoritative label identity.

### 14. Material-profile rebinding is generic at the core and provider-owned in scientific detail

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

The neutral core must **not** branch on LTA for material-specific scientific reconstruction, recursively rewrite arbitrary payload dictionaries by guessed field names, copy an opaque legacy scientific digest into a neutral wrapper, or silently accept an unsupported provider.

LTA remains the mandatory current reference implementation. Its rebound typed catalog/frame-record lineage must point to the current canonical frame authority and remain resolvable/usable after restart.

### 15. Neutral statistical owner remains typed and current-generation

`NeutralStatisticalBase` / unit construction requires the version-agnostic `SourceAuthority`, `CanonicalFrameAuthority` and `NeutralFeatureEvidence` and rejects silent substitution of legacy DATA2/DATA3/DATA4 containers.

Retain temporal/autocorrelation blocks, events/protected windows, physical condition/regime, replica/structural-realization/reference-group evidence, duplicates/correlation groups, protected outer roles, independence grading and leakage/disjointness checks. Continue to forbid compatibility `label_domain_id` in neutral unit identity, compatibility-policy ancestry, provenance as a mandatory role-budget axis, and pre-target CV/fold authority.

### 16. Old production runtime remains isolated until P4

The current prepare/select-target-size orchestration may continue to build/use legacy DATA2/DATA3/DATA4/DATA5 during P1-P3. P1 must not switch the production target-size route or expose the new substrate through public campaign orchestration.

Isolation is not permission for the new substrate itself to depend scientifically on legacy compatibility-domain owners.

## Implementation authority

### Frozen

The following are authoritative and must not be reinterpreted away:

- one uniform required-label authority rule across all authoritative frame/identity constructors and persistence paths;
- physical/source/geometry identity is distinct from authoritative label/labeled identity;
- canonical label digest and labeled fingerprint form an atomic, deterministic pair;
- source persistence is structurally strict and preserves coherent quality status/outcome;
- current source-record schema must advance beyond the ambiguous provisional `mdstats.source-record.v1` shape;
- direct-source canonical rebuild must replay/verify explicit companion-file bindings and control interpretation rather than dropping them or weakening verification;
- compatibility-neutral but scientifically complete source facts;
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
- whether to remove the direct `build_canonical_frame_identity()` authority surface or route it through one shared required-label authority helper;
- exact internal representation distinguishing physical-frame identity from authoritative label/labeled identity;
- exact constructor validation placement provided contradictory label/fingerprint state cannot exist;
- exact companion replay realization: persist role/locator bindings in current source authority or require/verify manifest/run-spec input at direct rebuild;
- whether outer `SourceAuthority` schema must bump in addition to the required source-record schema bump;
- shared legacy/canonical per-run kernel versus another semantically equivalent reuse structure;
- the small provider rebind dispatch/protocol API and adapter placement;
- typed profile persistence mechanism, provided it is durable and single-authority;
- cache/local data layout and internal performance mechanics;
- exact semantic class/function names, provided durable names stay version-agnostic.

Choose the minimum product complexity satisfying the frozen scientific contract. Avoid a second parser, duplicate required-label policy implementations, speculative generalized plugin machinery, guessed companion paths, or compatibility machinery for unpublished provisional state without a demonstrated consumer.

### Reopen only on evidence

Reopen only the affected design surface if repository evidence shows one of the following:

- normalized frame arrays cannot represent a required training label/convention without loss;
- an established downstream non-label consumer fundamentally cannot operate with the physical-versus-labeled distinction;
- a real supported current-generation consumer requires a direct authoritative identity builder whose required-label contract cannot be derived from the same policy used by `CanonicalFrameAuthority`;
- a compatibility-neutral source fact or companion/control binding required by direct rebuild cannot be represented without importing retired compatibility authority;
- a genuine supported migration consumer requires old provisional P1 source persistence and the missing scientific facts can be independently recovered/proven;
- an existing material-profile provider has an unavoidable scientific dependency on retired compatibility identity rather than merely stale lineage fields.

Do not silently carry legacy identity forward, weaken verification, or synthesize missing scientific facts in lieu of reopening.

## Entry conditions

- Implementation branch is reconciled with P1 revision 6.
- Preserve already-valid P1A4 work: assembled required-label gating; physical/labeled frame distinction; geometry/labeled duplicate split; source composition/ensemble/quality owner propagation; generic profile provider dispatch; typed LTA canonical rebinding/restart; invalid DATA3-adapter removal; compatibility-policy invariance; source-control signature checking; preserved per-run parallel construction; naming; and runtime isolation.
- Treat only the following as active P1A5 rework surfaces unless implementation evidence broadens impact:
  1. all authoritative identity-construction paths;
  2. canonical identity/record constructor + deserializer invariants;
  3. source-record quality/persistence schema strictness;
  4. explicit companion-file replay/control binding in direct VASP canonical rebuild;
  5. missing P1-E3 real-owner cases and the affected regression surface.
- Existing DATA2/DATA3/DATA4/DATA5 regression baselines are understood; unrelated pre-existing failures are recorded rather than absorbed.

## Pass P1-A — source-map reconciliation

Update `P1_SOURCE_MAP.md` and directly affected internal architectural notes so the authoritative path is unambiguous:

```text
precise compatibility-neutral source facts/provenance/control + companion bindings
 + normalized per-frame arrays carrying actual E/F/stress/geometry
   -> SourceAuthority
   -> one required-label authority mechanism
        -> physical/source/geometry frame authority
        -> authoritative label/labeled identity only after configured-required-label validity
   -> CanonicalFrameAuthority
   -> NeutralFeatureEvidence
        -> provider-owned typed material-profile rebind
   -> NeutralStatisticalBase
```

The source map must state explicitly that:

- no exported/helper authoritative identity path may bypass configured required-label authority;
- canonical label digest and labeled fingerprint are an atomic deterministic pair;
- physical/source/geometry frame bookkeeping may exist without authoritative label identity where downstream non-label consumers require the frame;
- `SourceAuthority` retains composition/ensemble/quality, source/control interpretation binding, and enough source/manifest companion-binding truth for deterministic direct rebuild;
- current-generation source persistence does not synthesize or drop missing authoritative facts from obsolete provisional payloads;
- legacy DATA3 may coexist for old-runtime isolation but is not a required parent of canonical frame authority;
- material-profile rebinding is generic at the neutral-core boundary and provider-owned in scientific detail;
- LTA is the mandatory P1 reference provider, not a neutral-core special case;
- typed rebound profile payloads survive restart;
- CV is not part of the neutral pre-target substrate;
- durable product/schema naming remains version-agnostic.

This pass is non-executable. Do not alter old runtime specifications to pretend P4 cutover has occurred.

## Pass P1-B — source provenance, source facts and durable rebuild authority

Preserve/extend the version-agnostic source authority so that:

- full `ElectronicStructureFingerprint`-equivalent provenance is retained;
- unresolved/partial provenance is diagnostic rather than a generic blocker;
- compatibility grouping is advisory only;
- corpus/current-operation atomic-reference identifiability is not split by compatibility domain;
- source scientific/content identity excludes advisory compatibility policy/group lineage;
- source eligibility for canonicalization means at least one frame can potentially contribute;
- compatibility-neutral source facts required by P1-C/P1-D are retained with their real values, including composition/atom count, ensemble, source quality status **and outcome**, selected energy semantics, source/control interpretation identity and explicit companion-binding truth needed for direct rebuild;
- obsolete provisional source-record payloads lacking newly authoritative facts fail explicitly rather than receiving invented/defaulted values.

### P1-B acceptance

- DFT, DFT+U, hybrid, smearing/numerical variants can coexist when required labels are usable;
- unresolved provenance remains visible;
- changing only advisory compatibility policy changes advisory output but not `SourceAuthority.content_digest` or source membership eligible for canonicalization;
- no `label_domain_id` is required by the current-generation source owner;
- source round-trip preserves all downstream-required scientific facts and source/control/companion interpretation binding exactly;
- source-record current schema is no longer the ambiguous provisional `mdstats.source-record.v1` shape;
- stale/incomplete provisional payloads cannot become current authority through fallback composition, ensemble, quality or control values;
- omission of `quality_outcome` is rejected when the current schema requires the field, including the legitimate explicit-`null` case being represented by a present key;
- invalid quality status/outcome combinations are rejected rather than becoming permissive eligibility state;
- a direct-source canonical rebuild succeeds for unchanged explicitly companion-bound sources and rejects changed/missing/rebound material companion/control interpretation.

### P1-B verification

1. focused provenance/source-policy/usability/source-fact tests;
2. affected DATA2/source-ingestion regression;
3. source-record/source-authority serialization/restart round trip including composition/ensemble/quality status+outcome/control/companion facts;
4. strict obsolete-provisional-payload rejection;
5. constructor/deserializer tests for quality status/outcome combinations;
6. bounded direct-source rebuild with at least one non-empty explicit `TrainingDataRunSpec.companion_files` binding;
7. negative companion/control mismatch cases with unchanged primary source where feasible;
8. structural proof that compatibility-domain/policy identity is excluded from source scientific lineage.

## Pass P1-C — canonical frame authority and identity from actual arrays

### P1-C1 — one authority mechanism

Construct `CanonicalFrameAuthority` from `SourceAuthority`, normalized `FrameData`-equivalent arrays keyed by run, and the established temperature/reference/policy inputs.

The authoritative builder must not require `TrainingFrameCatalog` or another legacy DATA3 object.

Resolve configured required-label authority through one shared semantic mechanism used by every current-generation authoritative identity path. If `build_canonical_frame_identity()` remains exported as an authoritative constructor, it must accept enough policy/representation context to produce exactly the same authority decision as the assembled frame owner. If it cannot do so without duplicating policy semantics, remove or explicitly reclassify it as non-authoritative.

### P1-C2 — source/frame validation and established algorithms

Validate directly against `SourceAuthority` plus normalized arrays:

- exact run membership;
- frame counts;
- source-frame indices;
- atom count;
- species/composition counts;
- other established source/frame consistency invariants.

For every frame, compute through the real implementation path:

- occurrence/frame UID;
- geometry fingerprint;
- configured required-label validity;
- canonical label payload from actual valid E/F/stress values and interpretation metadata when label authority exists;
- labeled-configuration fingerprint only when authoritative canonical label identity exists;
- separate electronic-structure provenance reference;
- temperature/condition metadata using actual source ensemble;
- strain/reference-cell metadata and context using actual source ensemble/assertions;
- frame eligibility using actual numerical labels and actual source quality assessment status/outcome;
- geometry duplicate catalog over physical geometry identity and labeled-duplicate catalog only over authoritative labeled identities.

### P1-C3 — constructor/persistence coherence

`CanonicalFrameIdentity` and `CanonicalFrameRecord` constructors and deserializers must reject:

- label digest present but labeled fingerprint absent;
- labeled fingerprint present but label digest absent;
- labeled fingerprint inconsistent with stored geometry fingerprint + label digest;
- malformed/non-digest identity fields;
- any serialized state that would cause `has_authoritative_label` to report authority for an internally incoherent object.

Round-trip both physical-only and authoritative labeled frames through current persistence.

### P1-C4 — unresolved provenance and numerical validity

A source whose electronic provenance is unresolved/partial but whose configured required labels and mechanical source facts are valid must traverse `SourceAuthority -> CanonicalFrameAuthority` without `label_domain_id`.

The real owner must prove:

- actual `energies_ev=None` or frame-equivalent missing required energy cannot obtain authoritative canonical label/labeled identity;
- actual `forces_ev_per_angstrom=None` cannot obtain authoritative canonical label/labeled identity when forces are required;
- missing stress blocks label authority only when stress is configured required;
- optional absent stress remains valid;
- supplied non-finite required energy/forces/stress cannot receive valid canonical scientific identity;
- physical/source/geometry identity remains coherent where retained;
- labeled-duplicate consumers exclude physical-only frames.

### P1-C5 — preserve proven parallel construction

Canonical-frame construction must preserve applicable per-run parallel execution. Bounded worker=1 and worker>1 runs must be scientifically identical, including physical-only versus authoritative-labeled identity status.

### P1-C acceptance

Prove through the real current-generation owner(s) that:

- no authoritative constructor can mint label/labeled identity from a missing configured-required property;
- identical actual canonical labels under different provenance/grouping produce identical canonical label identity;
- advisory grouping-policy changes do not alter scientific frame identity;
- changing actual energy changes canonical label/labeled identity;
- changing actual force or configured stress changes identity when applicable;
- changing semantic/unit/convention interpretation changes identity through the real builder;
- missing required energy/forces and required stress absence withhold label authority while optional stress absence does not;
- non-finite required values withhold/fail label authority;
- canonical label digest/labeled fingerprint pair is constructor- and restart-coherent;
- geometry duplicate semantics remain geometry-only and labeled duplicates use only authoritative labels;
- source/frame atom-count/composition mismatch is rejected;
- NPT/NPH/other ensemble semantics and real source quality propagate correctly;
- unresolved provenance with usable labels succeeds;
- worker-count changes do not change scientific output;
- the new frame owner feeds P1-D without legacy DATA3.

### P1-C verification cycle

1. focused shared required-label authority tests;
2. direct authoritative identity-constructor tests or structural removal/non-authoritative proof;
3. explicit missing-energy, missing-force, required-stress-missing, optional-stress-missing and non-finite real-builder cases;
4. semantic/unit/convention sensitivity through the real builder;
5. constructor + deserializer coherence negatives for the label/fingerprint pair;
6. geometry-versus-labeled duplicate tests including physical-only frames;
7. source/frame composition consistency tests;
8. ensemble/temperature/strain-context tests;
9. source-quality/eligibility tests;
10. worker=1 versus bounded parallel-worker equivalence;
11. affected DATA3 frame/identity/eligibility/temperature/reference-cell/strain/duplicate and parallel-resource regression;
12. canonical frame serialization/restart;
13. structural negative check that the authoritative builder does not require `TrainingFrameCatalog`, `label_domain_id`, legacy label-domain identity or compatibility-policy-containing parent digest;
14. bounded integration carrying real canonical frame authority into neutral feature evidence.

## Pass P1-D — neutral evidence, provider contract and statistical owner

Preserve the accepted P1A4 realization unless P1-C changes force a narrow adaptation.

### P1-D1 — raw feature/event evidence rebind

Reuse valid DATA4 raw-feature/event calculations, but bind them to `SourceAuthority` and `CanonicalFrameAuthority`. Per-frame evidence uses canonical frame-record digests; raw/event catalogs bind current source/frame authority; retired compatibility-bound aggregate digests do not become neutral scientific ancestry.

Label-dependent downstream consumers must not silently consume physical-only frames as valid labeled configurations.

### P1-D2 — material-agnostic provider rebinding boundary

Neutral core performs generic dispatch/validation only; provider-owned code performs material-specific typed reconstruction. Unsupported/opaque providers are rejected unless independently proven lineage-neutral. No neutral-core LTA scientific branch or opaque legacy digest copy is allowed.

### P1-D3 — LTA reference provider and restart

Keep the provider-owned LTA typed rebind, canonical frame/catalog lineage, scientific digest recomputation, embedded/durable typed payload reconstruction, `profile_partition_state_changed()` restart behavior and neutral statistical consumer path already established.

### P1-D4 — neutral statistical base

Preserve the typed current-generation statistical owner consuming only `SourceAuthority`, `CanonicalFrameAuthority` and `NeutralFeatureEvidence`, with existing temporal/event/condition/replica/reference/duplicate/correlation/protected-role/leakage semantics and no pre-target CV or compatibility-domain axis.

### P1-D acceptance / verification

Retain the existing accepted P1A4 P1-D focused and affected DATA4/DATA5/profile/LTA/event/statistical-role tests. Add only affected propagation guards required by changes to physical-versus-labeled identity or source lineage. Do not gratuitously rewrite already-valid provider/profile machinery.

## Pass P1-E — package closure

Reconcile the complete P1 diff against the parent workplan and revision 6, then re-derive the affected surface from the assembled candidate.

### P1-E1 — required real-owner integration

Execute bounded deterministic integration through actual P1 owners:

```text
source files / manifest / explicit companion bindings
 -> existing parser/cache/control machinery yielding normalized frame arrays
 -> SourceAuthority carrying real compatibility-neutral source facts/control binding
 -> uniform required-label authority
 -> CanonicalFrameAuthority built from actual frame arrays
 -> NeutralFeatureEvidence using provider-owned typed profile rebinding
 -> NeutralStatisticalBase
```

Allowed cost bounding: small synthetic VASP/source fixtures, bounded frame counts, existing parser/cache helpers, bounded CPU parallelism; no expensive model training/GPU work.

Forbidden acceptance substitutions include:

- legacy DATA3 as semantic owner of canonical numerical identity;
- helper-only canonical tests while an exported/assembled authoritative constructor remains broken;
- prebuilt canonical frame authority instead of its real builder;
- manually mutated `SourceAuthority`/`SourceRecord` values as proof that source ingestion propagated ensemble/quality correctly;
- synthetic assertion-derived ensemble/quality values instead of source-owned facts;
- permissive deserializer defaults or omitted quality outcome standing in for persisted source facts;
- dropping explicit companion bindings during direct rebuild and weakening source-control verification to compensate;
- direct helper hashing of missing labels as proof that the assembled owner enforces required-label authority;
- outer-profile-only tests bypassing typed provider rebinding;
- test-harness reimplementation of canonical/profile logic.

### P1-E2 — compatibility-policy invariance proof

Using the same scientific inputs, build the complete P1 chain under at least two advisory compatibility policies producing observably different advisory output. Require equality of all applicable scientific state/behavior:

- source membership and `SourceAuthority.content_digest`;
- canonical frame UIDs/labels/labeled identities/physical-only status and `CanonicalFrameAuthority.content_digest`;
- rebound raw/event/profile identities;
- `NeutralFeatureEvidence.content_digest`;
- neutral unit IDs/catalog;
- protected outer roles;
- `NeutralStatisticalBase.content_digest`.

Only advisory diagnostics may differ.

### P1-E3 — assembled numerical/semantic/required-label sensitivity proof

Through the **real canonical-frame builder** and, where retained, every exported authoritative direct identity constructor, execute each applicable case:

1. change an actual energy value and require changed canonical label/labeled/frame/downstream lineage;
2. change an actual force value, or configured stress value where appropriate, and require changed canonical label identity;
3. change at least one real semantic/unit/convention input consumed by the builder — for example energy normalization or entropy convention — and require changed canonical identity;
4. supply a non-finite configured-required value and prove authoritative label identity is not granted;
5. represent genuinely missing configured-required energy (`energies_ev=None` or semantically equivalent missing owner state), not merely `NaN`, and prove no authoritative label/labeled identity is granted;
6. represent genuinely missing configured-required forces (`forces_ev_per_angstrom=None` or equivalent) and prove the same when forces are required;
7. exercise stress absence in both required and optional modes, proving required absence blocks label authority while optional absence does not;
8. for physical-only frames, prove geometry/source identity remains coherent and labeled-duplicate/label-dependent consumers do not treat them as valid labeled configurations;
9. if a direct authoritative identity builder remains, prove the same missing/optional/required contract through that builder or prove structurally that the builder is non-authoritative/removed.

Direct digest-helper tests cannot substitute for this assembled owner proof. Evidence must fail if any authoritative path creates a canonical label/labeled fingerprint from a missing configured-required value.

### P1-E4 — source-fact, quality and companion/control preservation proof

Exercise at least:

- source/frame atom-count or composition mismatch rejection;
- NPT/NPH or another genuinely ensemble-sensitive context through the real source-ingestion/control owner -> `SourceAuthority` -> canonical builder chain;
- source quality status/outcome propagation into frame eligibility through the real source-assessment/source-record owner, including an unqualified case;
- source-record round-trip and negative deserialization proving omitted/malformed quality outcome cannot become permissive current authority;
- unchanged direct-source canonical rebuild with at least one explicit non-empty companion-file binding;
- changed/missing/rebound companion/control binding rejection while primary source identity remains unchanged where feasible;
- persisted source/control interpretation mismatch rejection.

The ensemble/quality/companion evidence must be proxy-proof: the production owner assigning the source field/binding and the real downstream canonical consumer must execute. Manually replacing `SourceAuthority` after construction is not acceptance evidence for owner propagation.

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

Retain the existing bounded LTA partition-stage proof through the generic provider rebind boundary, durable typed restart resolution, `profile_partition_state_changed()`, neutral statistical consumer/rebuild path, and explicit unsupported-provider rejection.

### P1-E7 — invalid-authority absence proof

Structurally prove there is no current-generation path by which:

- legacy DATA3 metadata lacking actual E/F/stress becomes authoritative `CanonicalFrameAuthority`;
- an exported direct identity builder mints authoritative label identity without the configured required-label contract;
- contradictory canonical label/fingerprint pair state can be constructed or deserialized as valid current scientific state;
- obsolete source-record persistence manufactures or drops composition/ensemble/quality/control/companion facts and returns current authority.

Keep `build_canonical_frame_authority_from_data3_catalog()` absent. Remove/reclassify any other invalid authority surface rather than preserving it merely for provisional tests.

### P1-E8 — naming and runtime-isolation proof

Verify:

- no `v7_`, `V7*`, `mdstats.v7-*` product/schema names or aliases;
- any source-record schema bump is ordinary/version-agnostic;
- current prepare/select-target-size remains on old runtime until P4;
- campaign CLI/public target-size exports do not expose neutral substrate prematurely;
- old runtime remains reachable;
- current P1 substrate does not require old compatibility-domain owners.

### P1-E9 — functional closure evidence

Required executable evidence on the final assembled candidate:

- all P1-B/C/D focused tests;
- affected DATA2 source-ingestion/control/manifest-companion/quality/persistence regression;
- affected DATA3 geometry/identity/eligibility/temperature/reference-cell/strain/duplicate and parallel-resource regression;
- affected DATA4 raw-feature/event/profile/LTA regression;
- affected DATA5 statistical-role/partition/leakage regression;
- serialization/restart reconstruction for every new current-generation owner and rebound typed profile payload;
- source-record schema/strict obsolete-payload rejection;
- quality status/outcome coherence tests;
- explicit companion-bound direct rebuild success and mismatch rejection;
- canonical constructor/deserializer label/fingerprint coherence tests;
- P1-E1 real-owner integration;
- P1-E2 compatibility invariance;
- P1-E3 energy + force/stress + semantic + genuine missing required-label + non-finite authority sensitivity;
- P1-E4 real-owner source-fact/quality/companion/control preservation;
- P1-E5 unresolved-provenance chain;
- P1-E6 generic material-profile/LTA/restart integration;
- P1-E7 invalid-authority absence;
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
- Do not duplicate required-label policy logic in multiple authoritative constructors; share or remove the secondary authority path.
- Do not retain unpublished provisional adapters/aliases or source-persistence compatibility fallbacks merely to keep old P1 tests/artifacts green.
- Do not weaken source-control verification to accommodate lost companion-file context; preserve/replay the context instead.
- Do not solve missing-required-label authority by rejecting all physical-frame representation if established non-label consumers scientifically require those frames; preserve the physical-versus-labeled distinction instead.
- Do not perform long GPU training or production-scale qualification in P1.

## Exit gate

P1 is accepted only when the following invariant is true in the **assembled real-owner object graph and every exported authoritative construction/restart path**:

> Canonical usable source/frame identity is derived from actual compatibility-neutral source facts plus the configured numerical energy/force/stress payload and required interpretation metadata; one required-label authority rule governs every authoritative constructor and deserializer; authoritative canonical label/labeled-configuration identity exists only after the configured required-label set is present, shape-valid, finite and canonicalizable; canonical label digest and labeled fingerprint are an atomic deterministic pair; physical/source/geometry frame identity remains distinguishable where scientifically needed; unresolved provenance with usable labels traverses the current-generation path without compatibility-domain assignment; persisted source authority preserves coherent quality status/outcome and the exact source/control/explicit-companion interpretation needed for deterministic direct rebuild rather than synthesizing, dropping, guessing or silently reinterpreting material facts; established source/frame consistency, ensemble, source-quality, strain, eligibility, duplicate and applicable parallel-execution semantics are preserved; neutral raw/event/material-profile evidence is rebound through a material-agnostic core contract with provider-owned typed scientific reconstruction and durable restart resolution; no compatibility-group assignment, compatibility-policy identity, retired DATA2/DATA3/DATA4/profile ancestor digest, invalid DATA3-to-canonical surrogate, secondary identity-authority bypass, contradictory canonical persistence state, obsolete provisional source payload masquerading as current authority, or pre-target CV authority participates in current-generation scientific identity or protected-role assignment; precise provenance remains fully recorded; durable naming is version-agnostic; and the production target-size runtime has not yet switched.

The following are explicitly insufficient for P1 acceptance:

- fixing `CanonicalFrameAuthority` while leaving another exported authoritative identity constructor able to hash missing required labels into authority;
- canonical helper unit tests when an assembled/exported semantic owner is broken;
- a stable label digest with missing configured-required values merely because the digest helper supports optional fields;
- label digest and labeled fingerprint being independently optional without constructor/deserializer coherence;
- accepting a labeled fingerprint inconsistent with stored geometry + label digest;
- treating a frame without authoritative label identity as a valid labeled duplicate/configuration merely because its physical frame record exists;
- a legacy DATA3-to-canonical adapter that returns an authoritative canonical type without actual numerical labels;
- source/frame validation that checks frame arrays only against themselves;
- manually replacing `SourceAuthority` ensemble/quality values in tests and treating that as proof of real source-owner propagation;
- assertion-derived `"unknown"` ensemble or synthetic permissive source-quality state in place of source-owned facts;
- a missing `quality_outcome` key silently decoding as `None` when that omission can change eligibility;
- reusing the materially changed provisional `mdstats.source-record.v1` schema identifier for current authority;
- permissive provisional deserialization that fabricates or drops composition/ensemble/quality/control/companion facts and returns current authority;
- direct-source rebuild that drops explicit manifest companion bindings or checks only primary source identity;
- weakening source-control verification instead of replaying the source/control context that originally produced it;
- LTA-specific branching in the neutral core as the profile architecture;
- rebinding only an outer profile wrapper while retaining legacy typed lineage or copying an opaque old scientific digest;
- round-trip digest equality when typed scientific payload/state cannot be resolved and consumed after restart;
- successful generic-data integration that does not exercise unresolved provenance and real source-fact preservation;
- equality of neutral unit IDs when ancestor scientific digests still depend on compatibility policy;
- source inspection without required affected regression and real-owner integration evidence.

Commit/tag the accepted corrected P1 checkpoint before starting P2.
