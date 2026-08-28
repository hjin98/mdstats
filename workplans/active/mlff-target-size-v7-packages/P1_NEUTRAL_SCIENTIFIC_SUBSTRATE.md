---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P1
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 1
status: active
package_revision: 8
amended_date: 2026-08-28
rework_reason: Independent review after P1A6 confirmed that the revision-7 shared required-label evaluator, structurally strict source-record.v2 decoding, verified manifest association, and selected-energy interpretation checks were implemented correctly, but found one remaining scientific-consistency blocker and two explicit closure gaps: direct VASP rebuild verifies the ensemble-certificate digest without verifying that the independently persisted SourceRecord.ensemble equals the freshly reconstructed certificate ensemble; the frozen Stage-A/Stage-D focused acceptance matrix is incomplete; and P1_SOURCE_MAP.md was not reconciled to the final manifest/shared-evaluator ownership. Revision 8 freezes a final narrow P1A7 repair and closure strategy without reopening the P1 architecture.
---

# P1 — Neutral scientific substrate

## Purpose

Establish the current-generation **scientific identity substrate** without changing the currently reachable target-size runtime. P1 removes compatibility-domain semantics from canonical numerical-label identity and neutral statistical identity while preserving precise electronic-structure provenance, source facts required for scientific interpretation, and proven parsing, feature, correlation, event, material-profile, eligibility, strain, partition, persistence and parallel-execution machinery.

The parent V7 workplan remains the generation-level authority, but **durable product code and persisted schema names introduced by P1 are version-agnostic**. The new substrate remains internal/unreachable from the current target-size runtime until P4.

P1 revision 8 preserves all scientifically valid P1A6 work:

- version-agnostic durable names;
- compatibility-neutral source identity and scientific lineage;
- actual source composition, ensemble, source-quality and electronic-provenance facts;
- verified originating-manifest association for DATA2-catalog to `SourceAuthority` conversion;
- exact explicit companion role/locator persistence and replay;
- `mdstats.source-record.v2` with structurally strict authoritative-field decoding;
- coherent quality status/outcome validation;
- canonical construction from real normalized numerical arrays;
- one shared numerical required-label evaluator consumed by established frame eligibility, assembled canonical-frame construction and retained direct canonical-identity construction;
- correct optional-energy/optional-force/optional-stress semantics;
- physical-versus-labeled frame distinction;
- geometry-versus-labeled duplicate separation;
- atomic constructor/deserializer coherence for canonical label digest and labeled-configuration fingerprint;
- direct primary-source, source-control, companion, ensemble-certificate-digest and selected-energy channel/units/semantic-role verification;
- real-owner numerical/semantic/missing-label tests already implemented;
- generic material-profile provider dispatch with provider-owned LTA rebinding;
- durable typed-profile restart;
- invalid DATA3-adapter removal;
- compatibility-policy invariance;
- bounded worker-count-independent per-run parallel construction;
- old production runtime isolation through P4.

Revision 8 is a **final narrow closure amendment**. It does not reopen P1 architecture and must not cause valid P1A6 mechanisms to be reimplemented. P1A7 has exactly four active obligations:

1. close the remaining persisted-ensemble versus reconstructed-certificate coherence hole in direct VASP rebuild;
2. finish the already-frozen required-label focused acceptance matrix and missing-channel direct-rebuild negative test;
3. reconcile `P1_SOURCE_MAP.md` to the actual final owners introduced by P1A6/P1A7;
4. execute final assembled affected regression/integration and repository-required checks on the same candidate.

P1 remains active until those obligations close.

## Protected concerns

P1 protects the following product outcomes simultaneously:

- canonical training identity represents the actual numerical labels and the semantic/unit/convention information required to interpret them;
- **every authoritative constructor, record, identity object, deserializer and assembled owner obeys the same configured required-label authority rule**;
- physical/source/geometry frame identity may remain available when a required label is invalid or absent, but authoritative canonical label and labeled-configuration identity cannot be granted before the configured label contract is satisfied;
- canonical label digest and labeled-configuration fingerprint are an internally coherent pair and cannot be independently absent, forged or inconsistent;
- compatibility-neutral source facts required by downstream scientific algorithms are not lost when moving away from legacy DATA2/DATA3 identity;
- durable source reconstruction preserves the exact source/control/companion/ensemble/energy interpretation used to create current scientific authority rather than silently synthesizing, dropping or contradicting those facts;
- a verified ensemble certificate cannot coexist with a contradictory persisted `SourceRecord.ensemble` and still enter temperature/strain/statistical interpretation;
- source authority cannot be constructed from companion locator truth that is absent, unverified, or associated with a different manifest than the DATA2 catalog being converted;
- precise electronic provenance is recorded but is not a generic target-training eligibility, identity or partition axis;
- advisory compatibility grouping cannot change scientific source/frame/feature/statistical identity;
- unresolved or partial provenance can proceed through the assembled current-generation path when required numerical labels remain scientifically usable;
- established parsing, frame-array, geometry, temperature, reference-cell, strain, eligibility, duplicate, raw-feature, event, autocorrelation, material-profile, partition and parallel algorithms are reused rather than gratuitously reimplemented;
- retained evidence is rebound to current scientific authority without retaining retired compatibility-bound ancestry;
- material-specific profile science remains provider-owned behind a material-agnostic neutral core;
- persisted/restarted neutral state remains scientifically usable rather than merely digest-shaped;
- invalid transitional objects cannot masquerade as current-generation authority;
- the old production target-size runtime remains behaviorally intact and isolated until P4;
- executable acceptance requires focused checks, affected regression and real-owner integration; full production/GPU qualification remains deferred.

## Frozen design decisions

### 1. Version-agnostic durable naming

`V7` remains a workplan/generation identifier only. New product package names, class/function names, persisted schema identifiers and current-generation scientific concepts introduced by P1 must not carry `v7_`, `V7`, `mdstats.v7-*`, or equivalent architecture-revision prefixes.

The semantic package `mdstats.training_data.neutral_substrate` and version-agnostic names already introduced are accepted. Do not add aliases/shims for unpublished `v7_neutral_substrate` / `V7*` symbols.

### 2. One assembled current-generation scientific-owner chain

The accepted chain is:

```text
source files
 + verified originating TrainingDataManifest
 + explicit companion role/locator bindings
  -> existing parser/cache/control machinery
  -> normalized per-frame arrays + precise compatibility-neutral source facts
  -> SourceAuthority
  -> shared required-label numerical authority evaluator
  -> CanonicalFrameAuthority
  -> NeutralFeatureEvidence
       -> provider-owned typed material-profile rebinding
  -> NeutralStatisticalBase
```

Every material semantic arrow must execute through the real current-generation owner. Legacy objects may still be produced for the old runtime until P4, but compatibility-bound DATA2/DATA3/DATA4/DATA5 identities cannot be required scientific parents of the new chain.

### 3. One canonical required-label authority mechanism

The current-generation canonical-frame owner consumes actual normalized numerical values, not merely legacy `TrainingFrameRecord` metadata or a compatibility-bound label digest.

The canonical label identity binds, as configured and applicable:

- selected energy channel and semantic role;
- energy units and normalization;
- entropy/free-energy convention;
- derivative/stress convention identity;
- actual canonical energy value when supplied;
- actual canonical force array when supplied;
- actual canonical stress array when supplied;
- label-fingerprint policy/tolerances.

Required-label numerical validity has one semantic owner: the version-agnostic pure evaluator now implemented in `mdstats.training_data.eligibility` (`evaluate_required_label_contract` or a semantically equivalent retained name). It owns only numerical label-contract validity: E/F/stress presence where required, supplied-value shape, finiteness, stress symmetry, and required/optional/forbidden stress semantics.

The following owners must consume that same evaluator:

- `assess_frame_eligibility()` for label-related reason/warning codes;
- `_build_canonical_frame_records_for_run()` / assembled canonical frame construction;
- retained authoritative `build_canonical_frame_identity()`;
- any future authoritative current-generation label-construction path introduced before P1 freeze.

SCF status, source quality, cell/geometry validity and other whole-frame eligibility concerns remain owned by `assess_frame_eligibility()` and must not be promoted into the narrower label-authority predicate.

The frozen optional semantics remain:

```text
require_energy=False + energy=None
    -> energy dimension satisfies the required-label contract

require_forces=False + forces=None
    -> force dimension satisfies the required-label contract

stress_requirement=OPTIONAL + stress=None
    -> stress dimension satisfies the required-label contract

stress_requirement=REQUIRED + stress=None
    -> required-label contract fails

stress_requirement=FORBIDDEN + stress present
    -> required-label contract fails
```

Any supplied optional value still must be shape-valid, finite and canonicalizable.

A low-level canonical payload digest helper may remain optional-aware. Such a helper is representation machinery, not the authority decision.

P1A6's shared evaluator implementation is accepted. P1A7 must not reintroduce duplicate handwritten predicates.

### 4. Physical frame identity and labeled identity remain distinct

A frame may possess source-occurrence and geometry identity when a required numerical label is unavailable or invalid because non-label diagnostics/statistics may still need physical-frame bookkeeping.

However:

- authoritative canonical label identity exists only after the configured required-label set is satisfied;
- authoritative labeled-configuration identity exists if and only if authoritative canonical label identity exists;
- geometry-duplicate reasoning may include physical-only frames;
- labeled-duplicate reasoning must exclude frames lacking authoritative label identity;
- label-dependent downstream consumers must require labeled authority explicitly.

### 5. Canonical label/fingerprint persistence is self-consistent

`CanonicalFrameIdentity` and `CanonicalFrameRecord` must guarantee:

```text
canonical_label_payload_digest is None
    <=> labeled_configuration_fingerprint is None
```

and when present:

```text
labeled_configuration_fingerprint
    == labeled_configuration_fingerprint(
           geometry_fingerprint,
           canonical_label_payload_digest,
       )
```

One-sided or inconsistent state is invalid scientific state and must be rejected by constructors and deserializers.

The P1A5/P1A6 implementation of this invariant is accepted and outside P1A7 rework unless a regression demonstrates a defect.

### 6. Current-generation construction does not require `label_domain_id`

No current-generation source/frame builder may require resolved compatibility-domain assignment. Legacy DATA3 may still require it on the isolated old runtime, but the new scientific chain cannot.

### 7. SourceAuthority owns complete compatibility-neutral scientific source facts

Current `SourceRecord` / `SourceAuthority` must preserve at minimum:

- run/source locator identity;
- primary source identity signature;
- source-control interpretation digest;
- ensemble-certificate digest;
- exact persisted ensemble value;
- composition/atom count;
- frame count;
- selected energy channel, units and semantic role;
- precise electronic-structure provenance;
- actual quality assessment status and outcome;
- explicit companion role/locator bindings;
- timestep where retained by current source state;
- replica/reference/assertion facts;
- current mechanical usability/rejection state.

No compatibility grouping or `label_domain_id` enters scientific source identity.

### 8. `source-record.v2` remains structurally strict

Every authoritative scientific field emitted by current `SourceRecord._payload()` must be structurally present on decode, even if its legitimate value is `null`, `{}`, or `[]`.

Omission is not equivalent to explicit emptiness.

`SourceRecord.from_dict()` must continue to:

- reject obsolete `mdstats.source-record.v1` payloads;
- require all current v2 authoritative keys;
- require the actual serialized mapping/sequence shapes for assertions, companion files and rejection codes;
- preserve explicit null/empty state;
- enforce coherent quality status/outcome pairs;
- verify record content digest where supplied.

P1A6's implementation and exhaustive required-field test are accepted.

### 9. Verified manifest is the authoritative DATA2 catalog -> SourceAuthority companion-binding source

`build_source_authority_from_data2_catalog()` is the accepted high-level conversion owner and requires the originating `TrainingDataManifest`.

Before accepting any companion locator truth it must verify:

- `manifest.content_digest == catalog.manifest_digest`;
- matching dataset ID;
- exact manifest run-ID set equals catalog source run-ID set;
- each run's manifest `vasprun` locator equals the corresponding DATA2 source locator.

Only after those checks may explicit companion role/locator bindings be copied from manifest run specs into `SourceRecord`.

The high-level path must not accept free-form/unverified companion mappings as equivalent authority.

The lower-level `build_source_authority()` may remain for focused/internal construction, but it cannot satisfy P1 manifest-association evidence and must not replace the verified high-level path in the assembled P1 chain.

P1A6's implementation is accepted.

### 10. Direct VASP canonical rebuild must verify all independently persisted source interpretation fields it consumes

`build_vasp_canonical_frame_authority()` directly reopens VASP sources using the persisted current `SourceAuthority`. Before numerical arrays enter canonical-frame construction it must verify that reconstructed scientific interpretation agrees with persisted source authority.

The accepted verification sequence per run is:

1. resolve primary source locator and every persisted explicit companion role/locator binding;
2. parse/reconstruct the VASP control bundle using those exact companion bindings;
3. require reconstructed primary source identity signature equals `source.source_identity_signature`;
4. require reconstructed source-control bundle signature equals `source.source_control_digest`;
5. reconstruct the simulation-control/ensemble certificate from that bundle and exact companions;
6. require certificate signature equals `source.ensemble_certificate_digest`;
7. **require `certificate.ensemble.value == source.ensemble`;**
8. resolve the persisted selected energy channel by name;
9. require reparsed channel `source_name`, `units` and `semantic_role` equal the corresponding persisted `SourceRecord` fields;
10. only then read channel values into `FrameData` and proceed to canonical hashing/temperature/strain/statistical construction.

P1A7 freezes step 7 as a required new implementation consequence. Certificate digest equality alone is not enough because `SourceRecord.ensemble` is an independently persisted field and is later consumed directly by temperature and strain algorithms.

The exact intended code location is immediately after the existing certificate-signature check in `build_vasp_canonical_frame_authority()`:

```python
certificate = certify_vasp_simulation_controls(...)
if certificate.signature != source.ensemble_certificate_digest:
    raise TrainingDataInputError(...)

if certificate.ensemble.value != source.ensemble:
    raise TrainingDataInputError(
        f"Ensemble interpretation mismatch for {source.run_id!r}: "
        f"reparsed={certificate.ensemble.value!r} != persisted={source.ensemble!r}"
    )
```

Equivalent source-specific wording is allowed. The comparison itself is not delegated.

Do not "repair" a mismatch by mutating the persisted source record, choosing whichever side is convenient, performing loose substring matching, or weakening the certificate-digest check. The established certificate's canonical `EnsembleKind.value` is the reconstructed authority and must agree exactly with the value that DATA2 originally persisted.

Accepted direct-rebuild behavior is therefore:

```text
same verified manifest + same primary source + same explicit companions
+ same source controls + same ensemble certificate and ensemble value
+ same selected-energy channel/units/semantic role
    -> direct rebuild succeeds

changed/missing/rebound material companion/control
    -> reject

correct certificate digest but tampered persisted SourceRecord.ensemble
    -> reject before temperature/strain/canonical downstream use

same source/control but tampered persisted energy units/semantic role/channel
    -> reject before canonical label hashing
```

This is the only new scientific owner change in P1A7.

### 11. Do not broaden P1A7 into timestep redesign without evidence

`timestep_fs` is retained in current source persistence and remains structurally strict. Independent review noted it is another control-derived fact, but no current P1A6/P1A7 defect has been demonstrated in which an independently tampered `timestep_fs` changes the assembled current P1 canonical/statistical result while the real source path remains accepted.

Therefore:

- P1A7 does **not** require a new timestep reconstruction/verification mechanism;
- preserve current timestep persistence behavior;
- if implementation evidence shows a current P1 consumer directly uses persisted timestep as scientific authority independently of reconstructed source/control state, reopen only that affected surface and apply the same coherence principle rather than silently expanding scope.

### 12. Reuse established DATA3 algorithms and parallel machinery

Current-generation frame construction must continue to reuse established:

- source/frame membership and composition validation;
- geometry fingerprinting;
- temperature-condition construction;
- reference-cell resolution;
- strain calculation/context classification;
- frame eligibility;
- duplicate/labeled-duplicate detection;
- per-run isolated parallel construction.

Validate atom count/composition against `SourceAuthority`. Use actual source ensemble and quality facts. Scientific output must be worker-count independent.

No production-scale performance qualification is required in P1.

### 13. Source authority remains compatibility-policy neutral

Scientific source/frame/feature/statistical identity excludes:

- `label_domain_id`;
- compatibility-group assignment;
- `LabelCompatibilityPolicy.policy_digest`;
- legacy label-domain catalogs;
- aggregate compatibility-bound parent digests.

Advisory compatibility output may vary without changing scientific source/content identity.

### 14. Neutral DATA4 reuse is scientific-evidence rebinding

Existing DATA4 raw features/events/material profiles may be reused when physical/scientific values remain valid, but compatibility-bound legacy outer lineage must not become the new scientific parent.

Neutral evidence binds reused values to current `SourceAuthority` and `CanonicalFrameAuthority` identities.

### 15. Material-profile rebinding remains generic at the core and provider-owned in scientific detail

The neutral core owns a small material-agnostic contract:

```text
partition profile wrapper + typed scientific payload
    -> provider-owned rebind against CanonicalFrameAuthority
    -> rebound typed scientific payload
    -> recomputed scientific digest
    -> generic ProfileFeatureCatalog wrapper
```

LTA remains the mandatory P1 reference provider. The core must not implement LTA-specific scientific reconstruction or arbitrary guessed dictionary rewriting.

Supported provider payloads must remain reconstructible and scientifically usable after restart.

### 16. Neutral statistical owner remains typed/current-generation

`NeutralStatisticalBase` requires current `SourceAuthority`, `CanonicalFrameAuthority` and `NeutralFeatureEvidence`, retains temporal/autocorrelation/event/condition/replica/reference/duplicate/correlation/outer-role evidence, and excludes compatibility domains and pre-target CV authority.

### 17. Old production runtime remains isolated until P4

P1-P3 may coexist with legacy preparation/select-target-size runtime. P1 must not switch production orchestration or expose the new substrate through public campaign behavior. Isolation does not permit the new substrate itself to depend scientifically on retired compatibility-domain owners.

## Implementation authority

### Frozen

The following are authoritative and must not be reinterpreted away:

- all accepted P1A6 mechanisms listed in Purpose remain preserved;
- one shared required-label numerical evaluator remains the sole authority implementation for E/F/stress label validity;
- optional-label semantics exactly match `FrameEligibilityPolicy` across assembled and retained direct builders;
- physical identity remains distinct from authoritative label/labeled identity;
- canonical label digest and labeled fingerprint remain an atomic deterministic pair;
- `source-record.v2` remains structurally exact;
- verified originating manifest remains mandatory on authoritative catalog-to-SourceAuthority conversion;
- exact companion role/locator truth comes only from that verified manifest on the high-level path;
- direct VASP rebuild continues to verify primary source identity, control digest, certificate digest, selected channel name, selected channel units and semantic role;
- **direct VASP rebuild additionally verifies reconstructed certificate ensemble value equals persisted `SourceRecord.ensemble` before any downstream scientific use;**
- established ensemble, quality, strain, eligibility, duplicate and parallel semantics are preserved;
- provider-owned material rebind, typed restart, compatibility neutrality and old-runtime isolation remain unchanged;
- P1A7 acceptance must complete the exact missing focused cases and final assembled regression described below.

### Delegated

Implementation may choose:

- exact error-message wording for the new ensemble mismatch, provided it is explicit and source/run-specific;
- exact parameterization/helper structure of the missing focused tests;
- whether focused test fixtures invoke a small helper to build direct and assembled paths, provided the real semantic owners still execute;
- exact wording/formatting of the `P1_SOURCE_MAP.md` reconciliation, provided the final owner graph and verification responsibilities are unambiguous;
- exact ordering of inexpensive test commands within each stage;
- local cleanup of now-unused imports/comments created by the P1A7 edits.

Implementation may **not** choose to:

- reimplement the shared required-label predicate;
- compare ensemble loosely by substring/case heuristics when the certificate owner already supplies the canonical stored value;
- mutate persisted `SourceRecord.ensemble` to the reparsed value and continue;
- remove or weaken source-control/certificate/channel verification;
- satisfy missing acceptance cases only through the lower-level label digest helper;
- skip source-map reconciliation;
- substitute an unverified lower-level `build_source_authority()` path for the real verified-manifest owner in integration acceptance;
- perform unrelated architecture cleanup or production cutover.

### Reopen only on evidence

Reopen only the affected design surface if repository evidence shows one of the following:

- the established certificate's canonical ensemble value is intentionally represented differently from the value persisted by supported DATA2 sources, and a single existing canonicalization owner can be reused without lossy inference;
- a supported real P1 caller cannot provide the originating manifest and catalog independently proves exact companion role/locator association;
- a current P1 consumer is shown to use persisted timestep as independent scientific authority such that direct-source restart can silently contradict it;
- normalized arrays cannot represent a required training label/convention without loss;
- a supported provider has unavoidable scientific dependency on retired compatibility identity.

Do not silently weaken verification or synthesize missing scientific facts in lieu of reopening.

## Entry conditions for P1A7

- Implementation branch head is reconciled with P1 revision 8 and the P1A6 implementation commit `a9e9bce5e7ba4941a4a832592be05ff2fde0ea34`.
- Preserve all already-valid P1A6 code and evidence unless a P1A7 edit directly invalidates it.
- Treat only these surfaces as active unless evidence broadens impact:
  1. `mdstats/training_data/neutral_substrate/frame_authority.py` — certificate ensemble-value coherence;
  2. `tests/test_mlff_neutral_scientific_substrate.py` — missing Stage-A/Stage-D focused cases plus new NPT ensemble-tamper reproducer;
  3. `workplans/active/mlff-target-size-v7-packages/P1_SOURCE_MAP.md` — final ownership reconciliation;
  4. final affected regression/integration evidence.
- `eligibility.py`, `neutral_substrate/identity.py`, `neutral_substrate/sources.py`, provider/profile/statistical implementations are preservation surfaces, not planned rework surfaces, unless a focused regression demonstrates a real defect.

## P1A7 exact repair sequence

Implement in this order.

### Stage A — bind persisted ensemble to reconstructed certificate

**Primary owner:** `mdstats/training_data/neutral_substrate/frame_authority.py`

Required implementation:

1. Locate `build_vasp_canonical_frame_authority()` after the current reconstructed certificate signature comparison.
2. Add an exact comparison:

   ```python
   certificate.ensemble.value == source.ensemble
   ```

3. On mismatch raise `TrainingDataInputError` before:
   - selected-energy values enter `FrameData`;
   - `build_canonical_frame_authority()` is called;
   - temperature-condition construction consumes `source.ensemble`;
   - strain classification consumes `source.ensemble`.
4. Preserve all existing primary-source, source-control, companion, certificate-signature and selected-energy checks unchanged.
5. Do not alter `SourceRecord`, DATA2 ensemble inference, `EnsembleKind`, temperature, strain or persistence schemas for this repair unless a failing real regression proves a separate defect.

Mandatory focused acceptance before Stage B:

- existing real NPT source + unchanged `SourceAuthority` direct rebuild succeeds;
- create a tampered authority by replacing only `SourceRecord.ensemble` for that real NPT source with a contradictory supported value such as `"NVE"`, while leaving the actual source, source-control digest and ensemble-certificate digest unchanged;
- `build_vasp_canonical_frame_authority()` must reject that tampered authority with an ensemble-interpretation mismatch;
- the reproducer must use the actual direct VASP rebuild owner, not call the comparison helper in isolation;
- existing certificate-digest mismatch, source-control mismatch, companion mismatch, units mismatch and semantic-role mismatch tests remain green.

Stage A fails if certificate digest equality remains sufficient to admit a contradictory persisted `source.ensemble`.

### Stage B — finish the frozen required-label acceptance matrix

**Primary test surface:** `tests/test_mlff_neutral_scientific_substrate.py`

No new production policy implementation is expected.

Use one parameterized/table-driven test or equivalent compact coverage that exercises the real shared evaluator and the retained authoritative construction paths. At minimum complete the cases P1A6 did not close.

The final matrix must establish:

#### Energy

- required + finite present -> satisfied/authoritative;
- required + missing -> fail `missing_energy` / no authoritative label;
- required + nonfinite -> fail `nonfinite_energy` / no authoritative label;
- optional + missing -> satisfied/authoritative when other required labels are valid;
- optional + nonfinite supplied -> fail / no authoritative label.

#### Forces

- required + valid `(n_atoms, 3)` finite -> satisfied;
- required + missing -> fail `missing_forces`;
- required + wrong shape -> fail `force_shape_mismatch`;
- required + nonfinite supplied -> fail `nonfinite_forces`;
- optional + missing -> satisfied when other required labels are valid;
- optional + wrong shape supplied -> fail;
- optional + nonfinite supplied -> fail.

#### Stress

- required + valid finite symmetric `(3, 3)` -> satisfied;
- required + missing -> fail `missing_stress`;
- required + wrong shape -> fail `stress_shape_mismatch`;
- required + nonfinite supplied -> fail `nonfinite_stress`;
- required + nonsymmetric supplied -> fail `nonsymmetric_stress`;
- optional + missing -> satisfied and preserves existing optional-absence warning semantics where full eligibility is inspected;
- optional + wrong shape supplied -> fail;
- optional + nonfinite supplied -> fail;
- optional + nonsymmetric supplied -> fail;
- forbidden + absent -> satisfied;
- forbidden + present -> fail `stress_present_but_forbidden`.

For each case where the contract is expected to fail, the assembled `CanonicalFrameAuthority` path must withhold canonical label/labeled identity. For representative cases across each dimension, the retained direct `build_canonical_frame_identity()` path must make the same authority decision. The pure evaluator may be asserted directly for reason codes, but helper-only coverage is not sufficient.

The explicit former bug reproducer remains mandatory:

```text
require_energy=False
energy=None
require_forces=True
forces valid
stress optional/absent
    -> shared evaluator satisfied
    -> direct builder authoritative
    -> assembled builder authoritative
```

Stage B fails if the missing cases are tested only through `canonical_training_label_payload_digest()` or another non-authority helper.

### Stage C — add the missing selected-channel direct-rebuild negative

**Primary test surface:** direct VASP canonical rebuild test.

Required acceptance:

1. Build a real VASP source/catalog/verified-manifest `SourceAuthority` using the normal owner path.
2. Replace only the persisted `SourceRecord.selected_energy_channel` with a name absent from the reparsed VASP energy catalog.
3. Leave the real source/control/certificate content unchanged.
4. Call `build_vasp_canonical_frame_authority()`.
5. Require `TrainingDataInputError` indicating the selected energy channel is absent.
6. Ensure failure occurs before canonical label hashing.

Retain and rerun the already-valid negative tests for tampered selected-energy units and semantic role.

### Stage D — reconcile `P1_SOURCE_MAP.md` to final P1 ownership

Update only the source map necessary for an accurate P1 handoff. Do not rewrite settled architecture.

The source map must explicitly show this authoritative chain:

```text
source files
 + verified originating TrainingDataManifest
 + exact explicit companion role/locator bindings
  -> DATA2 parser/control/source facts
  -> build_source_authority_from_data2_catalog(catalog, manifest=...)
       verifies manifest digest + dataset ID + exact run set + primary locators
  -> SourceAuthority / source-record.v2
  -> eligibility.evaluate_required_label_contract
       shared by full frame eligibility + direct/assembled canonical label authority
  -> CanonicalFrameAuthority
  -> NeutralFeatureEvidence
       -> provider-owned typed profile rebind
  -> NeutralStatisticalBase
```

It must also state that direct VASP reconstruction verifies, before downstream use:

```text
primary source identity
source-control digest
exact persisted companion bindings
ensemble-certificate digest
reconstructed certificate ensemble value == persisted SourceRecord.ensemble
selected energy channel name
selected energy units
selected energy semantic role
```

And it must retain these boundaries:

- `source-record.v2` is structurally strict; omitted authoritative fields do not default to emptiness;
- canonical label digest/labeled fingerprint are atomic and deterministic;
- physical-only frames may exist without authoritative labels;
- legacy DATA3 is not a scientific parent;
- compatibility grouping remains advisory/non-authoritative;
- material profile rebinding remains generic-core/provider-owned;
- old production runtime remains isolated until P4.

Stage D is documentation/architecture reconciliation only; it must not trigger product-code refactoring.

### Stage E — final assembled functional closure

After Stages A-D:

1. reconcile the final implementation against revision 8;
2. re-derive the affected behavioral surface from the assembled candidate;
3. execute the complete affected regression/integration set below on the same candidate;
4. resolve any newly introduced or plausibly affected hard failure;
5. record demonstrably unrelated pre-existing failures separately rather than absorbing them;
6. do not perform long GPU/production qualification.

A required check that did not execute is not a pass.

## Pass P1-A — source-map closure

P1-A passes only when `P1_SOURCE_MAP.md` accurately identifies:

- verified manifest as the high-level companion/source association authority;
- `build_source_authority_from_data2_catalog()` as the verified current conversion owner;
- `evaluate_required_label_contract` as the single E/F/stress label-validity owner used by both canonical construction paths and full eligibility;
- strict source-record.v2 persistence;
- direct source/control/companion/certificate-ensemble/energy-interpretation replay checks;
- physical-versus-labeled distinction;
- compatibility neutrality;
- provider-owned rebinding;
- old-runtime isolation.

## Pass P1-B — source authority and durable reconstruction

Preserve P1A6 behavior and rerun affected source tests:

- compatibility-policy-invariant source content identity;
- exact composition/ensemble/quality/timestep/reference/replica/assertion persistence;
- fully populated source-record.v2 round trip;
- explicit-null/empty source-record.v2 round trip;
- deletion of every authoritative source-record.v2 field rejects;
- invalid assertions/companion/rejection-code representations reject;
- obsolete v1 rejects;
- quality status/outcome incoherence rejects;
- verified manifest required;
- foreign manifest/content-digest mismatch rejects;
- dataset/run-set/locator mismatches reject;
- explicit non-empty companion mapping persists exact role/locator pairs.

No new P1-B product behavior beyond ensemble direct-rebuild coherence is required.

## Pass P1-C — canonical label/frame authority

Preserve and verify:

- one shared required-label evaluator;
- assembled and retained direct authority-path consistency;
- optional energy/forces/stress semantics;
- nonfinite/shape/symmetry failure behavior;
- canonical label/fingerprint atomicity and deterministic coherence;
- physical-only frame survival;
- geometry/labeled duplicate distinction;
- source/frame composition rejection;
- actual ensemble and quality propagation into established algorithms;
- worker=1 versus worker>1 scientific equivalence;
- no `label_domain_id` dependency;
- direct source rebuild selected-energy interpretation checks;
- **new certificate ensemble-value coherence check.**

## Pass P1-D — neutral feature/profile/statistical preservation

P1A7 does not redesign this pass. Rerun affected regression proving:

- neutral feature evidence binds current source/frame authority;
- generic provider dispatch remains material-agnostic;
- LTA provider-owned typed rebind remains correct;
- typed profile restart remains resolvable/usable;
- unsupported provider fails explicitly;
- neutral statistical base consumes current typed authorities;
- partition/leakage/independence behavior remains intact;
- compatibility domains/CV remain absent from neutral scientific identity.

## Pass P1-E — assembled closure

### E1 — real-owner source -> neutral-statistical chain

Exercise the real assembled path:

```text
real/synthetic-bounded VASP source files
 + TrainingDataManifest
 + explicit companions where applicable
  -> DATA2 parser/source catalog
  -> verified SourceAuthority conversion
  -> direct VASP CanonicalFrameAuthority reconstruction
  -> NeutralFeatureEvidence
  -> provider-owned typed rebind
  -> NeutralStatisticalBase
```

Allowed cost-bounding fakes may remain below these semantic owners, but the owners themselves may not be patched/reimplemented in the harness.

### E2 — compatibility-policy invariance

Two compatibility policies may produce different advisory grouping output while scientific source/frame/feature/statistical identities and usable membership remain unchanged.

### E3 — numerical/semantic/required-label proof

Execute through real authoritative paths:

1. energy-value mutation changes canonical label identity;
2. force or stress mutation changes canonical label identity;
3. semantic/unit/convention mutation changes canonical label identity;
4. nonfinite required value withholds label authority;
5. actual `energies_ev=None` under required energy withholds label authority;
6. actual `forces_ev_per_angstrom=None` under required forces withholds label authority;
7. stress absent under required versus optional policy behaves differently as specified;
8. physical-only frames remain geometrically coherent and are excluded from labeled duplicate/label-dependent reasoning;
9. optional-energy reproducer succeeds identically through direct and assembled builders;
10. completed Stage-B invalid-shape/nonfinite/nonsymmetric matrix behaves consistently.

### E4 — source fact/quality/companion/control/ensemble/energy proof

Real-owner proof must include:

- source/frame composition mismatch rejection;
- real NPT source inference through actual source/control owner;
- real source-quality status/outcome including unqualified trajectory behavior;
- strict source roundtrip and malformed quality negative cases;
- unchanged explicit companion direct rebuild succeeds;
- companion/control mismatch with primary source unchanged rejects where feasible;
- persisted source-control mismatch rejects;
- persisted selected-energy units mismatch rejects;
- persisted selected-energy semantic-role mismatch rejects;
- persisted selected-energy channel absent from real catalog rejects;
- **real NPT certificate plus tampered persisted `SourceRecord.ensemble="NVE"` rejects before downstream temperature/strain use.**

The last item is the P1A7 scientific blocker reproducer.

### E5 — unresolved provenance chain

Unresolved/partial electronic provenance proceeds from SourceAuthority through real canonical frame, neutral feature and neutral statistical construction without compatibility-domain authority when labels remain usable.

### E6 — provider/LTA restart

Preserve current provider-owned LTA typed rebinding and durable restart acceptance.

### E7 — invalid authority absence

Structurally verify:

- no DATA3-to-canonical surrogate authority;
- no duplicated required-label predicate;
- no contradictory canonical label/fingerprint persistence;
- no obsolete source-record.v1 authority;
- no high-level unverified companion authority path;
- no direct rebuild that verifies certificate digest while ignoring contradictory persisted ensemble;
- no public production cutover before P4.

### E8 — naming/isolation

- no new durable `v7_`/`V7` product/schema names;
- ordinary schema versions remain acceptable;
- neutral substrate remains unreachable from current production campaign orchestration until P4.

### E9 — functional closure

The final same-candidate regression must include at minimum:

- focused P1-B source/manifest/persistence tests;
- focused P1-C shared-label/canonical/direct-source tests including the full Stage-B matrix;
- P1-D neutral feature/provider/statistical tests;
- P1-E real-owner integration tests;
- affected DATA2 source/control/manifest/companion/quality/persistence tests;
- affected DATA3 geometry/identity/eligibility/temperature/reference/strain/duplicate/parallel tests;
- affected DATA4 feature/event/profile/LTA tests;
- affected DATA5 statistical/partition/leakage tests;
- current-owner restart/roundtrip tests;
- structural naming/legacy-path/isolation checks;
- repository/project-required Python/package checks for the final affected surface.

If impact cannot be confidently bounded, run the broader available regression suite rather than claiming unaffected status without evidence.

No long GPU/full-production qualification is part of P1A7.

## Exact P1A7 acceptance checklist

P1A7 cannot be marked complete until all of the following are true:

- [x] `build_vasp_canonical_frame_authority()` compares `certificate.ensemble.value` to persisted `source.ensemble` after certificate-signature verification and before downstream use.
- [x] Real NPT direct rebuild still succeeds unchanged.
- [x] Real NPT + only persisted ensemble tampered to contradictory value rejects.
- [x] Existing source-control, certificate-digest, companion, selected-energy units and selected-energy role mismatch tests remain green.
- [x] Missing selected-energy channel direct-rebuild negative executes and passes.
- [x] Shared required-label acceptance covers nonfinite forces.
- [x] Shared required-label acceptance covers stress wrong shape.
- [x] Shared required-label acceptance covers stress nonfinite.
- [x] Shared required-label acceptance covers stress nonsymmetry.
- [x] Optional forces/stress supplied-invalid cases fail even though the property is optional.
- [x] Required/optional/forbidden semantics remain consistent across shared evaluator and authoritative construction paths.
- [x] Former optional-energy bug reproducer remains positive across direct and assembled builders.
- [x] `P1_SOURCE_MAP.md` records verified manifest ownership, shared evaluator ownership and direct certificate-ensemble/energy replay checks.
- [x] Final affected DATA2-DATA5/P1 regression/integration executes on the same candidate.
- [x] Repository-required Python/package checks execute.
- [x] No long GPU/production qualification is run merely to close P1.

## P1 exit gate

P1 is accepted only when the assembled current-generation graph and every retained authoritative construction/restart path satisfy all of the following:

- source authority is compatibility-neutral but scientifically complete;
- high-level source authority derives explicit companion truth only from the verified originating manifest;
- source-record.v2 cannot silently default omitted authoritative state;
- one shared required-label numerical authority rule governs all authoritative label construction;
- canonical label/labeled identity exists only when the configured numerical contract is satisfied;
- canonical label digest and labeled fingerprint remain an atomic deterministic pair;
- physical identity remains available independently where allowed;
- real source composition, ensemble, quality, strain, eligibility, duplicate and parallel semantics are preserved;
- direct VASP restart verifies source identity, control digest, exact companions, ensemble-certificate digest, **certificate ensemble value versus persisted ensemble**, and selected-energy channel/units/semantic role before downstream use;
- unresolved provenance remains non-blocking when required labels are valid;
- neutral feature/profile/statistical owners remain current-generation and provider-owned where appropriate;
- no compatibility lineage, DATA3 surrogate, duplicate label authority, contradictory persistence, obsolete source payload, unverified manifest/companion association or pre-target CV enters scientific authority;
- durable names are version-agnostic;
- current production runtime has not been switched;
- all mandatory focused, affected-regression, integration and repository-required checks executed successfully or any unrelated pre-existing failures are explicitly demonstrated and bounded.

## Explicitly insufficient / non-closing states

The following do **not** qualify P1:

- certificate digest equality while `SourceRecord.ensemble` can independently contradict the reconstructed certificate;
- testing the new ensemble comparison only by directly comparing two strings instead of executing direct VASP rebuild;
- mutating `SourceRecord.ensemble` to the reparsed value and continuing;
- weakening certificate/source-control checks to accommodate a fixture;
- helper-only nonfinite/shape/symmetry tests that do not exercise canonical authority decisions;
- leaving nonfinite forces or malformed/nonfinite/nonsymmetric stress cases unexecuted despite the frozen matrix;
- testing selected-energy units/role but never the absent-channel branch;
- leaving `P1_SOURCE_MAP.md` on the pre-P1A6 owner graph;
- using lower-level `build_source_authority()` as proof of verified manifest association;
- relying on green tests while a frozen owner obligation is absent;
- source inspection without final affected regression/integration;
- a production-scale/GPU run as substitute for missing functional tests;
- unrelated cleanup or architectural redesign presented as necessary P1A7 work without evidence.

Once P1A7 satisfies this exit gate, P1 should be frozen and downstream package work may proceed without reopening these settled scientific-owner decisions absent new evidence.
