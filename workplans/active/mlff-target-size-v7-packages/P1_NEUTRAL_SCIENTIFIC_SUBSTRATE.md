---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P1
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 1
status: active
package_revision: 7
amended_date: 2026-08-28
rework_reason: Independent review after P1A5 confirmed the revision-6 canonical persistence, quality-pair, companion replay, ensemble-certificate, and expanded P1-E3 repairs, but found four remaining closure blockers: duplicated required-label authority logic still diverges for optional-energy semantics; source-record.v2 still silently defaults omitted authoritative fields; SourceAuthority construction can omit or mis-associate manifest companion truth; and direct VASP rebuild does not verify persisted selected-energy units/semantic role against the reparsed authoritative channel.
---

# P1 — Neutral scientific substrate

## Purpose

Establish the current-generation **scientific identity substrate** without changing the currently reachable target-size runtime. P1 removes compatibility-domain semantics from canonical numerical-label identity and neutral statistical identity while preserving precise electronic-structure provenance, source facts required for scientific interpretation, and proven parsing, feature, correlation, event, material-profile, eligibility, strain, partition and parallel-execution machinery.

The parent V7 workplan remains the generation-level authority, but **durable product code and persisted schema names introduced by P1 are version-agnostic**. The new substrate remains internal/unreachable from the current target-size runtime until P4.

P1 revision 7 preserves all scientifically valid P1A5 work: version-agnostic naming; compatibility-neutral source identity; actual source composition/ensemble/quality facts; canonical construction from real normalized arrays; assembled required-label gating; physical-versus-labeled frame distinction; geometry-versus-labeled duplicate separation; constructor/deserializer coherence for canonical label/fingerprint pairs; `mdstats.source-record.v2`; coherent quality status/outcome validation; explicit companion-file persistence and replay; source-control and ensemble-certificate verification; expanded real-owner P1-E3 coverage; generic provider dispatch with provider-owned LTA rebinding; durable typed-profile restart; invalid DATA3-adapter removal; and preserved bounded per-run parallelism.

Revision 7 is a **final narrow closure amendment**. It does not reopen P1 architecture. It freezes the exact P1A6 repair strategy for the four remaining authority/integrity defects so implementation does not have to rediscover ownership or choose among semantically weaker alternatives.

P1 remains active until the complete current-generation owner chain closes through real numerical frame data, compatibility-neutral source facts, one shared required-label authority mechanism, structurally strict source persistence, verified manifest-to-source companion binding, exact source/control/energy interpretation replay, provider-owned typed profile rebinding, and affected regression/integration evidence.

## Protected concerns

P1 protects the following product outcomes simultaneously:

- canonical training identity represents the actual numerical labels and semantic/unit/convention information required to interpret them;
- **every authoritative constructor, record, identity object, deserializer and assembled owner obeys the same required-label authority rule**; no secondary helper/export may bypass or independently reinterpret it;
- physical/source/geometry frame identity may remain available for diagnostics/statistics when scientifically needed, but authoritative canonical label and labeled-configuration identity is never granted before the configured required-label contract is satisfied;
- authoritative label digest and labeled-configuration fingerprint are an internally coherent pair and cannot be independently absent, forged or inconsistent;
- compatibility-neutral source facts needed by downstream scientific algorithms are not lost when moving away from legacy DATA2 identity;
- durable source reconstruction preserves complete source-quality state and the exact source/control/companion-file/energy-channel interpretation that produced authoritative source facts rather than silently synthesizing, dropping or reparsing material facts;
- source authority cannot be constructed with companion locator truth that is absent, unverified, or associated with a different manifest than the DATA2 catalog being converted;
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
source files / verified manifest / explicit companion bindings
  -> existing parser/cache/control machinery
  -> normalized per-frame arrays + precise compatibility-neutral source facts/provenance/control binding
  -> SourceAuthority
  -> one shared required-label authority mechanism
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
- actual canonical energy value when supplied/required;
- actual canonical force array when supplied/required;
- actual canonical stress array when supplied/required;
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
- treating an optional absent property as required merely because a second authority implementation drifted from the assembled owner;
- copying a legacy `label_payload_digest`;
- hashing only presence booleans/metadata;
- constructing a labeled fingerprint without a valid authoritative label digest;
- invoking a secondary identity constructor that does not use the same required-label authority evaluator as the assembled owner.

A low-level canonical payload digest helper may remain representation-neutral and permit optional absent values if that is useful. Such a helper is **not itself an authority decision**.

**Exact P1A6 implementation consequence:** required-label numerical validity must have one semantic owner. Extend `mdstats.training_data.eligibility` with one pure version-agnostic evaluator (exact name delegated; e.g. `evaluate_required_label_contract`) that accepts the active `FrameEligibilityPolicy`, atom count, energy, forces and stress and returns a deterministic result containing at minimum whether the configured label contract is satisfied plus the same label-specific reason/warning semantics used by `assess_frame_eligibility`. `assess_frame_eligibility()` must call that evaluator rather than maintaining its own independent E/F/stress validation. Both `_build_canonical_frame_records_for_run()` and retained `build_canonical_frame_identity()` must call the same evaluator and may grant canonical label/labeled identity **iff** that evaluator says the configured label contract is satisfied.

The shared evaluator owns only numerical label-contract validity. Source quality, SCF state, cell/geometry validity and other whole-frame eligibility remain owned by `assess_frame_eligibility()` and must not be accidentally promoted into the narrower label-authority predicate.

For optional properties the evaluator semantics are frozen:

```text
require_energy=False + energy=None
    -> energy dimension satisfies required-label contract

require_forces=False + forces=None
    -> force dimension satisfies required-label contract

stress_requirement=OPTIONAL + stress=None
    -> stress dimension satisfies required-label contract

stress_requirement=REQUIRED + stress=None
    -> required-label contract fails

stress_requirement=FORBIDDEN + stress is not None
    -> required-label contract fails
```

Any supplied label value still must be shape-valid, finite and canonicalizable even when the property is optional.

If repository evidence shows `build_canonical_frame_identity()` has no genuine supported current-generation owner, removing/reclassifying it remains acceptable and lower complexity. If it remains authoritative/exported, duplicated handwritten authority predicates are no longer delegated: it must consume the shared evaluator.

### 4. Physical frame identity and labeled identity remain distinct

A frame may possess source-occurrence and geometry identity when a required label is unavailable or invalid, because physical-frame bookkeeping, rejection diagnostics, raw geometry evidence or other non-label consumers may still need the frame.

However:

- authoritative canonical label identity exists only after the configured required-label set is proven present where required, shape-valid, finite and canonicalizable;
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

The P1A5 implementation of this invariant is accepted and should not be redesigned during P1A6 unless a direct regression demonstrates a defect.

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
- exact source/manifest locator facts needed to replay explicitly bound companion-file roles that materially participate in source/control identity;
- reference/replica/assertion facts used by current downstream algorithms;
- timestep or equivalent temporal source fact wherever the current statistical path requires it.

Compatibility grouping, `label_domain_id`, and advisory grouping-policy identity remain excluded.

Do not reconstruct authoritative ensemble or quality state from generic assertions when an actual source field owns that fact. Do not replace real quality state with synthetic values such as `"unrestricted"` merely because a source passed a coarse source-usability check.

### 8. Source persistence is structurally strict; obsolete provisional state does not become current authority

P1 current-generation persistence remains unpublished/provisional. Therefore current source-record deserialization must not fabricate **or silently drop** authoritative scientific facts.

`mdstats.source-record.v2` remains the accepted current schema. The schema identifier need not bump again for P1A6 because the v2 implementation is not yet accepted/frozen; instead make the v2 decoder actually satisfy its frozen contract.

**Exact P1A6 implementation consequence:** every field emitted by `SourceRecord._payload()` that represents current authoritative source state must be structurally required by `SourceRecord.from_dict()`. The required set is therefore:

```text
run_id
source_locator
source_identity_signature
source_control_digest
ensemble_certificate_digest
frame_count
composition
selected_energy_channel
selected_energy_units
selected_energy_semantic_role
electronic_structure
ensemble
quality_assessment_status
quality_outcome
timestep_fs
replica_id
reference_group
reference_run_id
assertions
companion_files
target_usable
mechanical_rejection_codes
```

A legitimate nullable/empty value is represented by a **present key** whose value is `null`, `{}`, or `[]` as appropriate. An absent key is not equivalent.

After required-key validation:

- `assertions` must be a mapping;
- `companion_files` must be a mapping in current v2 serialization; do not accept a sequence fallback unless a demonstrated supported v2 producer requires it;
- `mechanical_rejection_codes` must be a sequence of codes, not an omitted/defaulted field;
- quality status/outcome coherence already implemented in P1A5 remains required;
- content-digest verification remains required;
- old v1 continues to fail explicitly.

Do not use `payload.get(..., default)` for any authoritative v2 field. `.get()` is acceptable only after structural presence has already been established and only to decode an explicit `None` cleanly.

Outer source-authority schema versioning may remain unchanged if its decoder unambiguously rejects obsolete nested source-record state and no semantic ambiguity remains; bump it only if implementation evidence shows that is required.

### 9. SourceAuthority construction and direct-source rebuild must bind one verified manifest/source/control/energy interpretation

When `build_vasp_canonical_frame_authority()` or another direct-source current-generation builder reopens a source represented by persisted `SourceAuthority`, it must reproduce the same source/control/energy interpretation that produced that source authority.

It must verify at least:

- immutable primary source identity;
- relevant source-control/control-semantics binding;
- explicitly bound companion-file role -> locator mapping that participated in the source/control bundle;
- ensemble-certificate interpretation;
- selected energy-channel name, units and semantic role used by the source authority.

The currently supported `TrainingDataRunSpec.companion_files` model is part of the accepted source surface. A source that was validly ingested with explicit companion bindings must be able to traverse the direct current-generation canonical rebuild without being spuriously rejected merely because the rebuild dropped those bindings.

#### 9.1 Exact P1A6 SourceAuthority-construction strategy

Do **not** expand legacy `TrainingDataSource`/DATA2 persistence merely to carry P1 companion locators. The minimum-complexity accepted endpoint is to make the originating `TrainingDataManifest` a required authority input when converting a `TrainingDataSourceCatalog` into current-generation `SourceAuthority`.

`build_source_authority_from_data2_catalog()` must therefore require a concrete `TrainingDataManifest` (or an equivalently typed verified manifest owner) rather than treating `manifest=None` as authoritative. Before constructing any `SourceRecord`, it must verify:

1. `manifest.content_digest == catalog.manifest_digest`;
2. `manifest.dataset_id == catalog.dataset_id`;
3. manifest run IDs equal catalog source run IDs exactly — no missing, extra or duplicate association;
4. for every run ID, `run.vasprun == catalog.source(run_id).source_locator` under the same locator representation already used by DATA2; do not silently normalize a materially different locator into equality;
5. companion bindings persisted into the `SourceRecord` come only from that verified run spec.

After these checks, pass each run's exact sorted `companion_files` to `source_record_from_data2()`.

Remove or reject the current ambiguous route where `manifest` is absent and `companion_files_by_run` defaults to `{}`. Also remove/reject a caller-supplied companion mapping as an independent authority source unless implementation can prove it is derived from the same verified manifest; a free-form mapping whose association cannot be checked against `catalog.manifest_digest` is not sufficient current authority.

This intentionally makes all P1 callers — including fixtures with zero companions — pass the originating manifest. An explicit empty companion map from a verified run spec is scientifically different from “companion context was unavailable.” P1 is unpublished scaffolding, so updating these internal callers is preferred over retaining an unsafe optional path.

`build_source_authority()` may remain as a lower-level constructor only if its authority contract is made explicit and it cannot be mistaken for a catalog-to-authority conversion that has verified manifest association. If retained for focused tests/internal composition, callers that provide companion bindings directly own that low-level input; P1-E1/E4 acceptance must use the verified catalog+manifest owner path.

#### 9.2 Exact P1A6 direct-rebuild strategy

`build_vasp_canonical_frame_authority()` must continue to:

- resolve `source.source_locator` and every persisted `source.companion_files` role;
- call `read_vasp_run_controls(path, companion_files=...)`;
- require reparsed `bundle.source_identity.signature == source.source_identity_signature`;
- require reparsed `bundle.signature == source.source_control_digest`;
- require regenerated ensemble certificate signature equals `source.ensemble_certificate_digest`.

After resolving `channel = bundle.energy_catalog.channel(source.selected_energy_channel)`, direct rebuild must additionally require:

```text
channel.source_name == source.selected_energy_channel
channel.units == source.selected_energy_units
channel.semantic_role == source.selected_energy_semantic_role
```

before `channel.as_array()` enters `FrameData` or any canonical digest is produced. A mismatch must raise `TrainingDataInputError` with a source/run-specific message and must not be repaired by changing persisted SourceRecord semantics or by trusting whichever side is more convenient.

If canonical normalization later introduces an explicit conversion layer, the comparison may be performed against the canonicalized interpretation owned by that layer, but P1A6 must not invent such a conversion to avoid the direct equality check. Current DATA2 VASP energy channels are already expressed in the expected current units/roles.

The accepted behavior is:

```text
same verified manifest + same source + same explicit companion bindings
+ same control/ensemble + same selected-energy interpretation
    -> SourceAuthority/direct rebuild succeeds

foreign or mismatched manifest association
    -> SourceAuthority construction rejects

same primary source but changed/missing/rebound companion/control semantics
    -> direct rebuild rejects

same source/control bundle but persisted selected-energy units/semantic role drift
    -> direct rebuild rejects before canonical label hashing
```

Do not guess standard filenames for an explicitly overridden companion binding. Do not weaken source-control, ensemble-certificate, or selected-energy checks to make a fixture pass.

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

`SourceAuthority.content_digest`, source membership eligible for canonical-frame construction, corpus/current-operation atomic-reference identifiability and downstream scientific lineage exclude:

- `label_domain_id`;
- compatibility-group assignment;
- `LabelCompatibilityPolicy.policy_digest`;
- legacy label-domain catalogs;
- aggregate parent digests containing those values.

Advisory compatibility reports may still be serialized and inspected, but only as non-authoritative diagnostics.

### 12. Required-label validity is frame-aware and precedes label authority

Source-level aggregate label counts are insufficient to authorize every frame. The shared current-generation required-label authority mechanism inspects the actual configured numerical values.

- required properties are present for each affected frame when required by the configured training representation;
- supplied values have valid shape, are finite and canonicalizable;
- optional properties may be absent when the configured operation does not require them;
- supplied `NaN`, `+inf` and `-inf` cannot receive canonical scientific identity;
- missing configured-required energy, forces, or required stress cannot receive authoritative canonical label/labeled-configuration identity merely because a digest helper can encode `None`;
- optional missing energy/forces/stress do not become false negatives merely because a secondary builder independently encoded stricter semantics;
- explicit user filters and demonstrated mechanical training-engine constraints remain valid hard exclusions;
- actual source quality assessment remains part of established full-frame eligibility semantics but is not itself a numerical label-presence predicate;
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

- one shared required-label numerical authority evaluator across `assess_frame_eligibility`, assembled canonical frame construction, and every retained direct authoritative identity constructor;
- optional-energy/optional-force/optional-stress absence semantics exactly match the active `FrameEligibilityPolicy` and cannot diverge by constructor;
- physical/source/geometry identity is distinct from authoritative label/labeled identity;
- canonical label digest and labeled fingerprint form an atomic, deterministic pair;
- `mdstats.source-record.v2` is structurally strict across every authoritative field emitted by its current payload;
- source persistence preserves coherent quality status/outcome and explicit null/empty state without interpreting omitted keys as legitimate emptiness;
- catalog-to-`SourceAuthority` conversion uses the verified originating manifest; unverified/free-form companion mappings are not an equivalent authority source;
- manifest digest, dataset ID, exact run membership and run primary locator association are checked before companion truth is accepted;
- direct-source canonical rebuild replays/validates explicit companion bindings, source-control identity, ensemble certificate, and selected-energy channel name/units/semantic role;
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

- exact name and return representation of the shared required-label evaluator, provided there is one semantic implementation and all required owners consume it;
- exact helper/file decomposition around that evaluator;
- whether to remove the direct `build_canonical_frame_identity()` authority surface or route it through the shared evaluator;
- exact internal representation distinguishing physical-frame identity from authoritative label/labeled identity;
- exact constructor validation placement provided contradictory label/fingerprint state cannot exist;
- exact error-message wording for strict source-persistence, manifest-association and selected-energy mismatch failures, provided failures are explicit and source-specific where applicable;
- whether lower-level `build_source_authority()` remains available for focused/internal use, provided P1 real-owner conversion uses the verified manifest path and no lower-level shortcut is accepted as proof of manifest association;
- whether outer `SourceAuthority` schema must bump; no bump is required merely because v2 implementation is being completed before acceptance;
- shared legacy/canonical per-run kernel versus another semantically equivalent reuse structure;
- the small provider rebind dispatch/protocol API and adapter placement;
- typed profile persistence mechanism, provided it is durable and single-authority;
- cache/local data layout and internal performance mechanics;
- exact semantic class/function names, provided durable names stay version-agnostic.

Choose the minimum product complexity satisfying the frozen scientific contract. Avoid a second parser, duplicate required-label policy implementations, speculative generalized plugin machinery, guessed companion paths, free-form unverified companion authority, or compatibility machinery for unpublished provisional state without a demonstrated consumer.

### Reopen only on evidence

Reopen only the affected design surface if repository evidence shows one of the following:

- normalized frame arrays cannot represent a required training label/convention without loss;
- an established downstream non-label consumer fundamentally cannot operate with the physical-versus-labeled distinction;
- a real supported current-generation consumer requires a direct authoritative identity builder whose required-label contract cannot consume the shared policy evaluator;
- a real P1 caller cannot provide the originating `TrainingDataManifest`, and the catalog can independently prove exact companion role/locator association without extending or importing retired compatibility authority;
- selected-energy units/semantic role require a real normalization/conversion owner rather than direct equality, with repository evidence demonstrating such a supported path;
- a genuine supported migration consumer requires old provisional P1 source persistence and the missing scientific facts can be independently recovered/proven;
- an existing material-profile provider has an unavoidable scientific dependency on retired compatibility identity rather than merely stale lineage fields.

Do not silently carry legacy identity forward, weaken verification, synthesize missing scientific facts, or make unverified caller input authoritative in lieu of reopening.

## Entry conditions

- Implementation branch is reconciled with P1 revision 7 at the P1A5 head.
- Preserve already-valid P1A5 work: canonical label/fingerprint constructor/deserializer coherence; `source-record.v2`; quality status/outcome coherence; direct companion replay; source-control and ensemble-certificate checks; expanded P1-E3 energy/force/semantic/missing-label/stress/physical-duplicate coverage; assembled required-label gating; physical/labeled frame distinction; geometry/labeled duplicate split; source composition/ensemble/quality propagation; generic profile provider dispatch; typed LTA canonical rebinding/restart; invalid DATA3-adapter removal; compatibility-policy invariance; preserved per-run parallel construction; naming; and runtime isolation.
- Treat only the following as active P1A6 rework surfaces unless implementation evidence broadens impact:
  1. shared required-label numerical validity ownership across `eligibility.py`, neutral `identity.py`, and neutral `frame_authority.py`;
  2. exhaustive structural strictness of `SourceRecord.from_dict()` for current v2 payload fields;
  3. verified manifest ownership in `build_source_authority_from_data2_catalog()` and all P1 callers;
  4. selected-energy units/semantic-role verification in direct VASP canonical rebuild;
  5. tests/regression invalidated by those four changes.
- Existing DATA2/DATA3/DATA4/DATA5 regression baselines are understood; unrelated pre-existing failures are recorded rather than absorbed.

## P1A6 exact repair sequence

Implement in the following order so each authority boundary can close before dependent evidence is updated.

### Stage A — consolidate required-label numerical validity

Affected owners expected: `mdstats/training_data/eligibility.py`, `mdstats/training_data/neutral_substrate/frame_authority.py`, `mdstats/training_data/neutral_substrate/identity.py`, focused tests.

Required implementation:

1. Extract the existing E/F/stress presence, shape, finite, stress-symmetry and forbidden/required/optional logic from `assess_frame_eligibility()` into one pure evaluator owned by `eligibility.py`.
2. Make `assess_frame_eligibility()` consume its result to populate the existing label-related hard/warning codes. Preserve existing reason-code vocabulary unless a demonstrated defect requires change.
3. Replace the handwritten E/F/stress authority predicate in `_build_canonical_frame_records_for_run()` with the same evaluator.
4. Replace the handwritten E/F/stress predicate in retained `build_canonical_frame_identity()` with the same evaluator, or remove/reclassify that constructor if no current owner needs it.
5. Grant canonical label/labeled identity only when the evaluator reports the configured label contract satisfied.
6. Do not let SCF/source-quality/cell/geometry exclusions enter this narrower predicate; those remain full-frame eligibility concerns.

Mandatory focused acceptance before Stage B:

- table/property-style equivalence across assembled builder and retained direct builder for:
  - required energy present/missing/nonfinite;
  - optional energy present/missing/nonfinite;
  - required forces present/missing/bad shape/nonfinite;
  - optional forces present/missing/bad shape/nonfinite;
  - stress required present/missing/bad shape/nonfinite/nonsymmetric;
  - stress optional present/missing/bad supplied value;
  - stress forbidden absent/present;
- explicit regression reproducer for `require_energy=False, energy=None, require_forces=True, valid forces, optional stress`, requiring both authoritative paths to make the same positive authority decision;
- existing DATA3 eligibility reason-code tests and neutral P1-C tests pass.

Stage A fails if two separate handwritten policy predicates remain authoritative even if tests currently agree.

### Stage B — make source-record.v2 structurally exact

Affected owner expected: `mdstats/training_data/neutral_substrate/sources.py`, source serialization tests.

Required implementation:

1. Replace the partial `required_keys` set with the complete authoritative v2 field set frozen in section 8.
2. Reject any missing field before decoding values.
3. Decode `timestep_fs`, replica/reference fields and other nullable values from present keys; explicit `None` remains valid where allowed.
4. Require `assertions` and `companion_files` mappings and `mechanical_rejection_codes` sequence representation matching `to_dict()`.
5. Remove permissive `companion_files` sequence fallback and all default-empty `.get()` behavior for authoritative fields unless a real supported producer is proven.
6. Preserve v1 rejection and quality-pair validation.

Mandatory focused acceptance before Stage C:

- round trip a fully populated v2 record and a record containing legitimate explicit null/empty values;
- delete **each authoritative field at least once** via parameterized negative test and require `TrainingDataSerializationError` rather than default reconstruction;
- specifically prove missing `companion_files`, `assertions`, `mechanical_rejection_codes`, `timestep_fs`, `replica_id`, `reference_group`, and `reference_run_id` are rejected;
- invalid type for assertions/companions/rejection-codes rejects;
- old v1 remains rejected.

### Stage C — verify manifest association before SourceAuthority construction

Affected owners expected: `neutral_substrate/sources.py`, P1 helper/fixture callers, P1 source map if signatures change.

Required implementation:

1. Change `build_source_authority_from_data2_catalog()` so the originating manifest is required for authoritative catalog conversion.
2. Verify manifest digest, dataset ID, exact run-ID set and per-run primary locator equality against the catalog before building records.
3. Derive companion bindings only from the verified manifest run specs.
4. Remove the silent `manifest=None -> empty companion mapping` authority path.
5. Remove or reject independently supplied `companion_files_by_run` as a competing authority input on this high-level conversion path.
6. Update every P1 real-owner caller/helper to pass the same manifest used to construct the DATA2 catalog. This includes zero-companion fixtures.
7. Keep low-level `build_source_authority()` only if useful, but do not use it to satisfy P1 manifest-association acceptance.

Mandatory focused acceptance before Stage D:

- normal zero-companion catalog + matching manifest succeeds;
- explicit non-empty companion catalog + matching manifest succeeds and persists exact role/locator pairs;
- omitted manifest fails at the API boundary rather than creating empty companion state;
- foreign manifest with same dataset ID/run IDs but different content digest rejects;
- manifest with wrong dataset ID rejects;
- manifest with missing/extra run rejects;
- manifest run with same run ID but different `vasprun` locator rejects;
- existing source authority content remains compatibility-policy invariant when the same verified manifest is used.

### Stage D — verify selected-energy interpretation during direct rebuild

Affected owner expected: `neutral_substrate/frame_authority.py`, direct-source tests.

Required implementation:

1. Preserve all P1A5 primary source, source-control, companion replay and ensemble-certificate checks.
2. Resolve the persisted selected channel by name from the reparsed bundle.
3. Before reading values into `FrameData`, compare reparsed `source_name`, `units`, and `semantic_role` against the persisted `SourceRecord` fields.
4. Reject any mismatch explicitly before canonical label hashing.
5. Do not mutate or normalize the stored SourceRecord to make the comparison pass.

Mandatory focused acceptance before package closure:

- unchanged source/companion/control/energy interpretation rebuild succeeds;
- tampered persisted `selected_energy_units` with unchanged real source rejects;
- tampered persisted `selected_energy_semantic_role` with unchanged real source rejects;
- missing selected channel rejects;
- existing source-control mismatch, companion-content mismatch and ensemble-certificate mismatch tests remain green.

### Stage E — final assembled closure

After Stages A-D and their stage-local affected regressions pass:

1. update `P1_SOURCE_MAP.md` only as needed to reflect the actual final signatures/owner placement; do not rewrite settled architecture;
2. reconcile the entire P1 diff against revision 7;
3. re-derive affected DATA2-DATA5 surfaces from the assembled candidate;
4. run the complete P1-B/C/D/E affected regression/integration surface listed below;
5. run repository/project-required Python/package checks covering the final affected surface;
6. do not run long GPU/production qualification.

## Pass P1-A — source-map reconciliation

Update `P1_SOURCE_MAP.md` and directly affected internal architectural notes so the authoritative path is unambiguous:

```text
precise compatibility-neutral source facts/provenance/control + verified manifest companion bindings
 + normalized per-frame arrays carrying actual E/F/stress/geometry
   -> SourceAuthority
   -> one shared required-label authority mechanism
        -> physical/source/geometry frame authority
        -> authoritative label/labeled identity only after configured-required-label validity
   -> CanonicalFrameAuthority
   -> NeutralFeatureEvidence
        -> provider-owned typed material-profile rebind
   -> NeutralStatisticalBase
```

The source map must state explicitly that:

- no exported/helper authoritative identity path may bypass or duplicate configured required-label authority;
- canonical label digest and labeled fingerprint are an atomic deterministic pair;
- physical/source/geometry frame bookkeeping may exist without authoritative label identity where downstream non-label consumers require the frame;
- `SourceAuthority` retains composition/ensemble/quality, source/control interpretation binding, and verified originating-manifest companion-binding truth for deterministic direct rebuild;
- current-generation source persistence does not synthesize or drop missing authoritative facts from obsolete/incomplete payloads;
- direct rebuild verifies persisted selected-energy channel name/units/semantic role against the reparsed authoritative channel;
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
- compatibility-neutral source facts required by P1-C/P1-D are retained with their real values, including composition/atom count, ensemble, source quality status **and outcome**, selected energy semantics, source/control interpretation identity and verified explicit companion-binding truth needed for direct rebuild;
- obsolete/incomplete source-record payloads lacking authoritative facts fail explicitly rather than receiving invented/defaulted values;
- catalog-to-current-source-authority conversion proves the manifest association from which companion locator truth is taken.

### P1-B acceptance

- DFT, DFT+U, hybrid, smearing/numerical variants can coexist when required labels are usable;
- unresolved provenance remains visible;
- changing only advisory compatibility policy changes advisory output but not `SourceAuthority.content_digest` or source membership eligible for canonicalization;
- no `label_domain_id` is required by the current-generation source owner;
- source round-trip preserves all downstream-required scientific facts and source/control/companion interpretation binding exactly;
- source-record current schema is `mdstats.source-record.v2` and structurally requires its complete authoritative payload;
- stale/incomplete provisional payloads cannot become current authority through fallback composition, ensemble, quality, companion, reference, assertion or control values;
- omission of any authoritative v2 field is rejected while legitimate explicit null/empty values remain representable;
- invalid quality status/outcome combinations are rejected rather than becoming permissive eligibility state;
- matching DATA2 catalog + originating manifest succeeds; missing/foreign/mismatched manifest association rejects;
- a direct-source canonical rebuild succeeds for unchanged explicitly companion-bound sources and rejects changed/missing/rebound material companion/control/energy interpretation.

### P1-B verification

1. focused provenance/source-policy/usability/source-fact tests;
2. affected DATA2/source-ingestion regression;
3. source-record/source-authority serialization/restart round trip including composition/ensemble/quality status+outcome/control/companion/reference/assertion facts;
4. exhaustive current-v2 required-field omission rejection;
5. constructor/deserializer tests for quality status/outcome combinations;
6. verified-manifest catalog conversion success + missing/foreign/dataset/run/locator mismatch negatives;
7. bounded direct-source rebuild with at least one non-empty explicit `TrainingDataRunSpec.companion_files` binding;
8. negative companion/control/ensemble/selected-energy mismatch cases with unchanged primary source where feasible;
9. structural proof that compatibility-domain/policy identity is excluded from source scientific lineage.

## Pass P1-C — canonical frame authority and identity from actual arrays

### P1-C1 — one authority mechanism

Construct `CanonicalFrameAuthority` from `SourceAuthority`, normalized `FrameData`-equivalent arrays keyed by run, and the established temperature/reference/policy inputs.

The authoritative builder must not require `TrainingFrameCatalog` or another legacy DATA3 object.

Resolve configured required-label authority through the single shared evaluator in `eligibility.py`. `assess_frame_eligibility()`, assembled canonical record construction, and every retained direct authoritative identity constructor must consume this one result. No authoritative constructor may reimplement the E/F/stress required/optional/forbidden logic.

If `build_canonical_frame_identity()` remains exported as an authoritative constructor, it must accept enough policy/representation context to produce exactly the same authority decision as the assembled frame owner, including optional-energy and optional-force absence. If it cannot do so without owning duplicate policy semantics, remove or explicitly reclassify it as non-authoritative.

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
- configured required-label validity through the shared evaluator;
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

The P1A5 implementation already satisfies this contract and should be preserved.

### P1-C4 — unresolved provenance and numerical validity

A source whose electronic provenance is unresolved/partial but whose configured required labels and mechanical source facts are valid must traverse `SourceAuthority -> CanonicalFrameAuthority` without `label_domain_id`.

The real owner must prove:

- actual `energies_ev=None` or frame-equivalent missing required energy cannot obtain authoritative canonical label/labeled identity;
- `energy_ev=None` is accepted by the label-authority mechanism when energy is explicitly optional and all other configured label constraints are satisfied;
- actual `forces_ev_per_angstrom=None` cannot obtain authoritative canonical label/labeled identity when forces are required;
- missing forces are accepted when forces are explicitly optional and all other configured label constraints are satisfied;
- missing stress blocks label authority only when stress is configured required;
- optional absent stress remains valid;
- supplied forbidden stress blocks label authority;
- supplied non-finite/shape-invalid required or optional labels cannot receive valid canonical scientific identity;
- physical/source/geometry identity remains coherent where retained;
- labeled-duplicate consumers exclude physical-only frames.

### P1-C5 — preserve proven parallel construction

Canonical-frame construction must preserve applicable per-run parallel execution. Bounded worker=1 and worker>1 runs must be scientifically identical, including physical-only versus authoritative-labeled identity status.

### P1-C acceptance

Prove through the real current-generation owner(s) that:

- no authoritative constructor can mint label/labeled identity from a missing configured-required property;
- no authoritative constructor falsely withholds label authority solely because a configured-optional property is absent;
- assembled and direct authoritative constructors make identical required-label decisions for the same policy and numerical payload;
- identical actual canonical labels under different provenance/grouping produce identical canonical label identity;
- advisory grouping-policy changes do not alter scientific frame identity;
- changing actual energy changes canonical label/labeled identity when energy participates;
- changing actual force or configured stress changes identity when applicable;
- changing semantic/unit/convention interpretation changes identity through the real builder;
- missing required energy/forces and required stress absence withhold label authority while configured-optional absence does not;
- non-finite supplied values withhold/fail label authority;
- canonical label digest/labeled fingerprint pair is constructor- and restart-coherent;
- geometry duplicate semantics remain geometry-only and labeled duplicates use only authoritative labels;
- source/frame atom-count/composition mismatch is rejected;
- NPT/NPH/other ensemble semantics and real source quality propagate correctly;
- unresolved provenance with usable labels succeeds;
- worker-count changes do not change scientific output;
- the new frame owner feeds P1-D without legacy DATA3.

### P1-C verification cycle

1. focused shared required-label evaluator tests;
2. assembled/direct authority-equivalence matrix including the optional-energy reproducer;
3. direct authoritative identity-constructor tests or structural removal/non-authoritative proof;
4. explicit missing-energy, missing-force, required/optional/forbidden-stress and non-finite real-builder cases;
5. semantic/unit/convention sensitivity through the real builder;
6. constructor + deserializer coherence negatives for the label/fingerprint pair;
7. geometry-versus-labeled duplicate tests including physical-only frames;
8. source/frame composition consistency tests;
9. ensemble/temperature/strain-context tests;
10. source-quality/eligibility tests;
11. worker=1 versus bounded parallel-worker equivalence;
12. affected DATA3 frame/identity/eligibility/temperature/reference-cell/strain/duplicate and parallel-resource regression;
13. canonical frame serialization/restart;
14. structural negative check that the authoritative builder does not require `TrainingFrameCatalog`, `label_domain_id`, legacy label-domain identity or compatibility-policy-containing parent digest;
15. bounded integration carrying real canonical frame authority into neutral feature evidence.

## Pass P1-D — neutral evidence, provider contract and statistical owner

Preserve the accepted P1A5 realization unless P1-C/source-authority signature changes force a narrow caller adaptation.

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

Retain the existing accepted P1A5 P1-D focused and affected DATA4/DATA5/profile/LTA/event/statistical-role tests. Update only callers requiring the verified manifest and add affected propagation guards required by the shared label evaluator/source lineage changes. Do not gratuitously rewrite already-valid provider/profile machinery.

## Pass P1-E — package closure

Reconcile the complete P1 diff against the parent workplan and revision 7, then re-derive the affected surface from the assembled candidate.

### P1-E1 — required real-owner integration

Execute bounded deterministic integration through actual P1 owners:

```text
source files / originating manifest / explicit companion bindings
 -> existing parser/cache/control machinery yielding normalized frame arrays
 -> DATA2 catalog
 -> verified manifest-to-catalog association
 -> SourceAuthority carrying real compatibility-neutral source facts/control/companion/energy interpretation
 -> shared required-label authority
 -> CanonicalFrameAuthority built from actual frame arrays
 -> NeutralFeatureEvidence using provider-owned typed profile rebinding
 -> NeutralStatisticalBase
```

Allowed cost bounding: small synthetic VASP/source fixtures, bounded frame counts, existing parser/cache helpers, bounded CPU parallelism; no expensive model training/GPU work.

Forbidden acceptance substitutions include:

- legacy DATA3 as semantic owner of canonical numerical identity;
- helper-only canonical tests while an exported/assembled authoritative constructor remains broken;
- separate handwritten required-label predicates that happen to agree on tested fixtures;
- prebuilt canonical frame authority instead of its real builder;
- manually mutated `SourceAuthority`/`SourceRecord` values as proof that source ingestion propagated ensemble/quality correctly;
- synthetic assertion-derived ensemble/quality values instead of source-owned facts;
- permissive deserializer defaults or omitted authoritative v2 fields standing in for explicit persisted source facts;
- constructing current `SourceAuthority` from a DATA2 catalog without verifying the originating manifest;
- accepting a free-form companion mapping whose association to `catalog.manifest_digest` is not proven;
- dropping explicit companion bindings during direct rebuild and weakening source-control verification to compensate;
- verifying selected channel existence while ignoring persisted units/semantic-role mismatch;
- direct helper hashing of missing labels as proof that the assembled owner enforces required-label authority;
- outer-profile-only tests bypassing typed provider rebinding;
- test-harness reimplementation of canonical/profile logic.

### P1-E2 — compatibility-policy invariance proof

Using the same scientific inputs and the same verified originating manifest, build the complete P1 chain under at least two advisory compatibility policies producing observably different advisory output. Require equality of all applicable scientific state/behavior:

- source membership and `SourceAuthority.content_digest`;
- canonical frame UIDs/labels/labeled identities/physical-only status and `CanonicalFrameAuthority.content_digest`;
- rebound raw/event/profile identities;
- `NeutralFeatureEvidence.content_digest`;
- neutral unit IDs/catalog;
- protected outer roles;
- `NeutralStatisticalBase.content_digest`.

Only advisory diagnostics may differ.

### P1-E3 — assembled numerical/semantic/required-label sensitivity and equivalence proof

Through the **real canonical-frame builder**, shared label evaluator, and every retained exported authoritative direct identity constructor, execute each applicable case:

1. change an actual energy value and require changed canonical label/labeled/frame/downstream lineage when energy participates;
2. change an actual force value, or configured stress value where appropriate, and require changed canonical label identity;
3. change at least one real semantic/unit/convention input consumed by the builder — for example energy normalization or entropy convention — and require changed canonical identity;
4. supply a non-finite configured-required or configured-optional value and prove authoritative label identity is not granted;
5. represent genuinely missing configured-required energy (`energies_ev=None` or semantically equivalent missing owner state), not merely `NaN`, and prove no authoritative label/labeled identity is granted;
6. represent genuinely missing configured-required forces (`forces_ev_per_angstrom=None` or equivalent) and prove the same when forces are required;
7. exercise stress absence in required and optional modes plus stress presence in forbidden mode;
8. exercise optional-energy absence and optional-force absence, proving absence itself does not block authority when the policy makes that property optional;
9. for physical-only frames, prove geometry/source identity remains coherent and labeled-duplicate/label-dependent consumers do not treat them as valid labeled configurations;
10. if a direct authoritative identity builder remains, run the same policy/value matrix through both direct and assembled paths and require identical authority booleans; otherwise prove structurally that the builder is non-authoritative/removed.

Direct digest-helper tests cannot substitute for this assembled owner proof. Evidence must fail if any authoritative path creates a canonical label/labeled fingerprint from a missing configured-required value **or** if a secondary path falsely rejects a legitimate optional-absence configuration.

### P1-E4 — source-fact, manifest, quality and companion/control/energy preservation proof

Exercise at least:

- source/frame atom-count or composition mismatch rejection;
- NPT/NPH or another genuinely ensemble-sensitive context through the real source-ingestion/control owner -> verified catalog/manifest conversion -> `SourceAuthority` -> canonical builder chain;
- source quality status/outcome propagation into frame eligibility through the real source-assessment/source-record owner, including an unqualified case;
- source-record round-trip and exhaustive negative deserialization proving omitted authoritative fields cannot become permissive/current authority;
- matching catalog + originating manifest success;
- missing manifest rejection;
- foreign manifest digest rejection even when convenient run IDs overlap;
- wrong dataset/run membership/primary locator association rejection;
- unchanged direct-source canonical rebuild with at least one explicit non-empty companion-file binding;
- changed/missing/rebound companion/control binding rejection while primary source identity remains unchanged where feasible;
- persisted source/control interpretation mismatch rejection;
- persisted selected-energy units mismatch rejection with unchanged real source;
- persisted selected-energy semantic-role mismatch rejection with unchanged real source.

The ensemble/quality/manifest/companion/energy evidence must be proxy-proof: the production owner assigning the source field/binding and the real downstream canonical consumer must execute. Manually replacing `SourceAuthority` after construction is not acceptance evidence for owner propagation; targeted post-construction replacement remains acceptable only as a negative consumer-guard test after real-owner propagation is separately proven.

### P1-E5 — unresolved-provenance assembled proof

Construct a bounded unresolved/partial provenance source with valid required numerical labels and execute:

```text
TrainingDataManifest + DATA2 catalog
 -> verified SourceAuthority
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
- an exported direct identity builder owns a second required-label predicate or mints authoritative label identity without the shared configured required-label contract;
- contradictory canonical label/fingerprint pair state can be constructed or deserialized as valid current scientific state;
- `SourceRecord.from_dict()` manufactures omitted authoritative v2 fields through defaults;
- catalog-to-SourceAuthority conversion omits manifest verification or silently substitutes empty/free-form companion context;
- direct VASP rebuild accepts selected-energy units/semantic role that disagree with the reparsed channel.

Keep `build_canonical_frame_authority_from_data3_catalog()` absent. Remove/reclassify any other invalid authority surface rather than preserving it merely for provisional tests.

### P1-E8 — naming and runtime-isolation proof

Verify:

- no `v7_`, `V7*`, `mdstats.v7-*` product/schema names or aliases;
- `mdstats.source-record.v2` remains ordinary/version-agnostic;
- current prepare/select-target-size remains on old runtime until P4;
- campaign CLI/public target-size exports do not expose neutral substrate prematurely;
- old runtime remains reachable;
- current P1 substrate does not require old compatibility-domain owners.

### P1-E9 — functional closure evidence

Required executable evidence on the final assembled candidate:

- all P1-B/C/D focused tests;
- Stage A shared-evaluator and direct/assembled authority-equivalence matrix;
- explicit optional-energy absence reproducer and optional-force/stress cases;
- affected DATA2 source-ingestion/control/manifest-companion/quality/persistence regression;
- verified-manifest catalog conversion positives and missing/foreign/dataset/run/locator negatives;
- exhaustive source-record.v2 required-field omission/type rejection;
- affected DATA3 geometry/identity/eligibility/temperature/reference-cell/strain/duplicate and parallel-resource regression;
- affected DATA4 raw-feature/event/profile/LTA regression;
- affected DATA5 statistical-role/partition/leakage regression;
- serialization/restart reconstruction for every new current-generation owner and rebound typed profile payload;
- quality status/outcome coherence tests;
- explicit companion-bound direct rebuild success and mismatch rejection;
- selected-energy channel name/units/semantic-role direct-rebuild verification and mismatch rejection;
- canonical constructor/deserializer label/fingerprint coherence tests;
- P1-E1 real-owner integration;
- P1-E2 compatibility invariance;
- P1-E3 numerical + semantic + required/optional label sensitivity/equivalence;
- P1-E4 real-owner source-fact/manifest/quality/companion/control/energy preservation;
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
- Do not duplicate required-label policy logic in multiple authoritative constructors; one shared evaluator is now the required endpoint.
- Do not broaden full-frame eligibility semantics merely to solve label-authority consistency; label validity and full eligibility remain distinct owners.
- Do not retain unpublished provisional adapters/aliases or source-persistence compatibility fallbacks merely to keep old P1 tests/artifacts green.
- Do not permit current catalog-to-source-authority conversion without the verified originating manifest merely to preserve a convenient optional API.
- Do not accept a free-form companion mapping as equivalent to verified manifest association.
- Do not weaken source-control/ensemble/selected-energy verification to accommodate lost or inconsistent source context; preserve/replay and compare the context instead.
- Do not solve missing-required-label authority by rejecting all physical-frame representation if established non-label consumers scientifically require those frames; preserve the physical-versus-labeled distinction instead.
- Do not perform long GPU training or production-scale qualification in P1.

## Exit gate

P1 is accepted only when the following invariant is true in the **assembled real-owner object graph and every exported authoritative construction/restart path**:

> Canonical usable source/frame identity is derived from actual compatibility-neutral source facts plus the configured numerical energy/force/stress payload and required interpretation metadata; one shared required-label evaluator governs the E/F/stress required/optional/forbidden decision used by full frame eligibility, assembled canonical construction and every retained direct authoritative identity constructor; authoritative canonical label/labeled-configuration identity exists only after the configured required-label set is present where required and every supplied participating value is shape-valid, finite and canonicalizable, while legitimate optional absence is not falsely rejected; canonical label digest and labeled fingerprint are an atomic deterministic pair; physical/source/geometry frame identity remains distinguishable where scientifically needed; unresolved provenance with usable labels traverses the current-generation path without compatibility-domain assignment; `mdstats.source-record.v2` structurally preserves every authoritative source field with explicit null/empty state rather than omitted-key defaults; catalog-to-SourceAuthority conversion verifies the originating manifest digest, dataset, exact run set and primary locators before accepting companion bindings; persisted source authority preserves coherent quality status/outcome and the exact source/control/explicit-companion/selected-energy interpretation needed for deterministic direct rebuild rather than synthesizing, dropping, guessing or silently reinterpreting material facts; direct rebuild verifies selected energy name, units and semantic role against the reparsed channel; established source/frame consistency, ensemble, source-quality, strain, eligibility, duplicate and applicable parallel-execution semantics are preserved; neutral raw/event/material-profile evidence is rebound through a material-agnostic core contract with provider-owned typed scientific reconstruction and durable restart resolution; no compatibility-group assignment, compatibility-policy identity, retired DATA2/DATA3/DATA4/profile ancestor digest, invalid DATA3-to-canonical surrogate, secondary identity-authority predicate, contradictory canonical persistence state, incomplete source payload, unverified manifest/companion association, energy-interpretation mismatch, or pre-target CV authority participates in current-generation scientific identity or protected-role assignment; precise provenance remains fully recorded; durable naming is version-agnostic; and the production target-size runtime has not yet switched.

The following are explicitly insufficient for P1 acceptance:

- fixing the assembled `CanonicalFrameAuthority` while retaining a second handwritten `build_canonical_frame_identity()` policy predicate;
- direct and assembled constructors agreeing on required-energy tests while disagreeing on optional-energy or optional-force absence;
- canonical helper unit tests when an assembled/exported semantic owner is broken;
- a stable label digest with missing configured-required values merely because the digest helper supports optional fields;
- withholding authority from a valid optional-absence payload because a secondary builder is stricter than `FrameEligibilityPolicy`;
- label digest and labeled fingerprint being independently optional without constructor/deserializer coherence;
- accepting a labeled fingerprint inconsistent with stored geometry + label digest;
- treating a frame without authoritative label identity as a valid labeled duplicate/configuration merely because its physical frame record exists;
- a legacy DATA3-to-canonical adapter that returns an authoritative canonical type without actual numerical labels;
- source/frame validation that checks frame arrays only against themselves;
- manually replacing `SourceAuthority` ensemble/quality values in tests and treating that as proof of real source-owner propagation;
- assertion-derived `"unknown"` ensemble or synthetic permissive source-quality state in place of source-owned facts;
- any missing authoritative `source-record.v2` key silently decoding to `None`, `{}`, `[]`, or another default;
- accepting `companion_files` sequence/default fallback in current v2 without a demonstrated producer contract;
- constructing `SourceAuthority` from a DATA2 catalog without the originating manifest or without checking `manifest.content_digest == catalog.manifest_digest`;
- accepting a foreign manifest/free-form companion mapping because run IDs happen to overlap;
- direct-source rebuild that drops explicit manifest companion bindings or checks only primary source identity;
- direct-source rebuild that finds the selected energy channel by name but fails to verify units and semantic role against persisted source authority;
- weakening source-control, ensemble-certificate, companion, or selected-energy verification instead of preserving/replaying the context that originally produced it;
- LTA-specific branching in the neutral core as the profile architecture;
- rebinding only an outer profile wrapper while retaining legacy typed lineage or copying an opaque old scientific digest;
- round-trip digest equality when typed scientific payload/state cannot be resolved and consumed after restart;
- successful generic-data integration that does not exercise unresolved provenance and real source-fact preservation;
- equality of neutral unit IDs when ancestor scientific digests still depend on compatibility policy;
- source inspection without required affected regression and real-owner integration evidence.

Commit/tag the accepted corrected P1 checkpoint before starting P2.
