---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P1
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 1
status: active
package_revision: 2
amended_date: 2026-08-28
rework_reason: P1 independent review found disconnected current-generation owners and legacy compatibility-policy lineage in the neutral statistical base
---

# P1 — Neutral scientific substrate

## Purpose

Establish the V7 current-generation **scientific identity substrate** without changing the currently reachable target-size runtime. This package removes compatibility-domain semantics from canonical numerical-label identity and neutral statistical identity while preserving precise electronic-structure provenance and proven correlation/statistical algorithms.

All V7 frozen decisions remain authoritative. This package must not create a second target-size architecture or make the new substrate publicly authoritative before P4.

P1 revision 2 incorporates the independent review of the first implementation. That implementation correctly created several local compatibility-agnostic objects, but it did not assemble them into one real scientific-owner chain: the new neutral partition still consumed legacy DATA2/DATA3/DATA4 objects and therefore inherited compatibility-policy-dependent lineage. P1 is not accepted until the current-generation owners compose directly and the complete scientific identity graph, not merely leaf unit IDs, is invariant to advisory compatibility grouping.

## Frozen corrective decisions

These decisions are part of P1 and are not delegated implementation preferences.

1. **Version-agnostic product naming.** `V7` remains a workplan/generation identifier only. New production code, package names, class/function names, persisted schema identifiers and public/current-generation concepts introduced by P1 must not carry a `v7_`, `V7`, or equivalent architecture-revision prefix. The first implementation's `mdstats.training_data.v7_neutral_substrate`, `V7*` classes, `build_v7_*` functions and `mdstats.v7-*` persisted schema names are transitional implementation artifacts and must be renamed or consolidated before P1 acceptance. Do not retain aliases or compatibility shims for these unpublished names.
2. **One assembled scientific-owner chain.** P1-B, P1-C and P1-D are not independent sidecars. The accepted chain is:

   ```text
   precise source provenance
      -> version-agnostic source authority
      -> canonical usable frame authority
      -> neutral feature/correlation evidence
      -> neutral statistical base
   ```

   Every arrow must execute through the real current-generation owner. A builder that accepts legacy objects merely because they have similar attributes does not close this requirement.
3. **No compatibility-policy lineage in scientific identity.** `label_domain_id`, compatibility-group assignment, `LabelCompatibilityPolicy.policy_digest`, legacy label-domain catalogs, or a parent digest containing those values must not participate in the content identity of source usability, canonical frames, neutral feature/correlation evidence, neutral units, protected-role assignment, or the neutral statistical base. Advisory compatibility reports may be serialized and inspected, but their policy/grouping identity is non-authoritative and must not invalidate scientific descendants.
4. **Reuse algorithms, not retired identity topology.** Existing DATA4/DATA5 raw-feature, event, autocorrelation, partition, leakage and profile algorithms may be reused/refactored. Their legacy container/content digests must not be imported wholesale when those digests bind retired DATA2/DATA3 compatibility-domain identity. Introduce the minimum neutral evidence/view needed to reuse the algorithms without preserving retired lineage.
5. **Canonical labels reject invalid supplied numerics.** Required numerical labels must be present when required, shape-valid, finite and canonicalizable into the configured training representation. Optional absent properties may remain absent. A supplied `NaN`, `+inf` or `-inf` is not a valid canonical scientific label and must not be converted into a stable canonical-label digest.
6. **Old production runtime remains isolated until P4.** The current prepare/select-target-size route may continue using the old DATA2/DATA3/DATA5 architecture during P1-P3. The new substrate remains internal/unreachable from the current target-size runtime until the explicit P4 cutover. Isolation is not permission for the new substrate itself to depend scientifically on the old compatibility-domain authorities.

## Implementation authority

### Frozen

The purpose, corrective decisions above, owner direction, identity invariants, old-runtime isolation and acceptance requirements in this package are frozen.

### Delegated

Implementation may choose local file decomposition, helper factoring, dataclass layout, cache representation and whether the version-agnostic substrate remains in a temporary internal package or is cleanly integrated into existing modules, provided there is one unambiguous current-generation owner per concept and no compatibility shim/duplicate scientific authority is introduced.

A semantic package name such as `mdstats.training_data.neutral_substrate` is acceptable if an isolated package remains useful before P4. Exact semantic names are delegated; revision-number names are forbidden.

### Reopen only on evidence

Reopen the affected design surface only if repository evidence shows that a required legacy DATA4/DATA5 algorithm cannot be reused without a scientifically necessary dependency on compatibility-domain identity, or that the external training representation requires a label interpretation not expressible by the canonical-label contract. Do not silently carry the old lineage forward.

## Entry conditions

- Implementation branch is based on/reconciled with the source revision governed by V7 and includes the reviewed first P1 implementation or an equivalent reconciled state.
- Parent V7 workplan and this amended package are read before reimplementation.
- Existing DATA2/DATA3/DATA4/DATA5 regression baseline is understood; known unrelated failures are recorded rather than silently absorbed.
- The first P1 implementation is treated as provisional code subject to destructive rename/refactor; no compatibility obligation exists for its unpublished `V7*` symbols or schemas.

## Pass P1-A — normative/source-map and naming reconciliation

Update affected architecture/spec/config documentation enough that code changes have one unambiguous target:

```text
precise provenance
 -> canonical numerical labels
 -> canonical usable frame authority
 -> neutral feature/correlation evidence
 -> neutral statistical units and protected outer roles
```

Required distinctions:

- provenance facts are descriptive/advisory by default;
- numerical label identity is independent of compatibility grouping;
- compatibility grouping is not a target-training eligibility or partition axis;
- CV is not part of the neutral pre-target statistical substrate;
- implementation-generation labels such as V7 are absent from durable code/schema names;
- old runtime isolation and new scientific ownership are separate concerns: the new substrate may be unreachable without being a wrapper over legacy scientific identities.

Update `P1_SOURCE_MAP.md` consistently with this revision. This pass is non-executable; validate document links/spec consistency. Do not merge future-state docs independently of implementation.

## Pass P1-B — source provenance and eligibility authority

Implement/evolve a **version-agnostic source authority** so that:

- full `ElectronicStructureFingerprint`-equivalent provenance remains recorded;
- unresolved/partial provenance does not automatically block canonicalizable training labels;
- source compatibility-domain assignment is not required for training eligibility/current identity;
- compatibility comparison/grouping may survive only as an explicitly advisory report helper;
- atomic-reference identifiability is evaluated for the authorized corpus/current training operation rather than owned per compatibility domain;
- the source authority's scientific/content digest excludes advisory compatibility policy/group IDs and any legacy parent digest that embeds them;
- source-level usability does not falsely certify every frame merely from an aggregate label count. Actual training membership is decided by canonical frame usability/eligibility. A source may remain eligible for canonicalization when it contains at least one usable frame; a source with no usable required-label frames cannot contribute training data.

### Required-label validity

P1-B/P1-C together must preserve the configured training-label contract:

- missing required numerical properties reject the affected frame/data contribution;
- corrupt, non-finite, shape-invalid or unconvertible required values reject the affected frame/data contribution;
- optional properties may be absent when the configured training operation does not require them;
- explicit user filters and positively demonstrated mechanical training-engine constraints remain valid hard exclusions;
- provenance heterogeneity by itself is not a hard exclusion.

### P1-B acceptance

- DFT, DFT+U, hybrid, smearing/numerical provenance variants can coexist when canonical labels are usable.
- unresolved provenance remains visible in diagnostics.
- genuinely unusable required labels do not become training-authorized merely because another frame in the source contains a label.
- changing only compatibility grouping policy does not change source membership eligible for canonical-frame construction or the source authority's scientific/content digest.
- advisory compatibility output may change under a compatibility-policy change without changing scientific descendants.

### P1-B verification cycle

1. focused provenance/source-policy/usability tests, including partial-source and invalid-label cases;
2. affected DATA2/source-ingestion regression;
3. serialization/restart round trip of the version-agnostic source authority;
4. semantic/structural inspection proving no compatibility-domain decision or compatibility-policy-containing parent digest remains a generic target-training blocker or source scientific-identity axis.

Close both semantic and functional dimensions before dependent P1-C/P1-D work proceeds.

## Pass P1-C — canonical label and frame authority

Replace the compatibility-domain-dependent numerical label identity and make the resulting frame authority usable by P1-D rather than leaving it as an identity-only sidecar.

Required end state:

- frame UID remains source-occurrence/frame-index identity unless independently invalidated;
- canonical label payload binds canonical numerical values plus the semantic/unit/convention information needed to interpret them;
- advisory compatibility-group/domain identity is not hashed into label payload or labeled-configuration identity;
- precise provenance is referenced separately from canonical label identity;
- geometry duplicate identity remains geometry-only;
- supplied non-finite energy/force/stress values are rejected rather than serialized as canonical scientific identity;
- the canonical frame authority exposes or owns the neutral metadata P1-D actually requires, including the frame/source occurrence relationship, canonical usability/eligibility, duplicate identity and the condition/strain/temperature/event linkage needed to build neutral correlation units. Do not require P1-D to fall back to a legacy DATA3 frame catalog to recover those semantics.

The exact representation may compose canonical identities with separately owned neutral frame metadata rather than place every field on one dataclass, but the composed authority must be current-generation and its lineage must not include compatibility-domain identity.

### P1-C acceptance

Prove with paired fixtures that:

- identical canonical labels under different provenance/grouping produce the same canonical label identity;
- changing only advisory grouping policy leaves frame UID, label payload, labeled-configuration identity and canonical frame-authority content identity unchanged;
- changing actual canonical energy/force/stress values or interpretation changes numerical scientific identity and appropriate descendants;
- non-finite supplied numerical labels fail canonicalization;
- duplicate/labeled-duplicate semantics remain correct;
- the canonical frame authority can be consumed by the neutral evidence/statistical path without substituting the legacy DATA3 authority.

### P1-C verification cycle

1. focused identity/serialization/property/finite-value tests;
2. affected DATA3/frame/eligibility/duplicate regression;
3. restart/serialization round-trip tests for the version-agnostic schema;
4. structural inspection proving the canonical label/frame owner does not consume compatibility-domain assignment or a compatibility-policy-containing legacy digest;
5. integration fixture carrying the canonical frame authority into the next neutral-evidence boundary.

## Pass P1-D — neutral feature/correlation evidence and statistical substrate

Refactor the useful DATA4/DATA5 statistical machinery into a current-generation neutral base.

### P1-D1 — neutral feature/correlation evidence boundary

Reuse existing DATA4 calculations where valid, but introduce the minimum version-agnostic evidence surface required by neutral partitioning. This surface must:

- bind only the raw/profile/event/condition evidence actually consumed by neutral correlation/statistical construction;
- reference the current source/canonical-frame authorities by compatibility-agnostic scientific identities;
- exclude legacy `source_catalog.content_digest`, `frame_catalog.content_digest`, `data4_bundle.content_digest`, or equivalent aggregate parent identities when those parents embed `label_domain_id`, compatibility policy or label-domain catalogs;
- avoid copying/reimplementing expensive scientific algorithms merely to obtain new digests. Prefer a neutral view/rebinding of proven results when the underlying calculation recipe remains scientifically valid;
- remain deterministic and serializable/reconstructible when persisted.

This is a transition/scientific-evidence boundary, not a second feature-engine authority.

### P1-D2 — neutral statistical base

The neutral statistical owner must consume the version-agnostic source authority, canonical frame authority and neutral feature/correlation evidence directly.

Retain as independently required:

- temporal blocks/autocorrelation;
- events/protected windows;
- lineage and physical condition/regime;
- replica/structural-realization/reference-group evidence;
- duplicate/correlation information;
- protected outer-role behavior and leakage/disjointness evidence.

Remove/forbid:

- compatibility `label_domain_id` from partition-condition/unit identity;
- compatibility-policy or legacy label-domain-containing ancestor digests from neutral unit/statistical-base identity;
- pre-target CV plans or CV fold authority;
- provenance as a mandatory partition or role-budget axis.

Existing DATA5 may remain for the old runtime until P4, but the new neutral substrate must be separately testable and must not be a wrapper that still uses label-domain partitioning or legacy compatibility-bound ancestry internally.

### P1-D acceptance

- changing only provenance compatibility grouping does not change neutral feature-evidence identity, neutral unit identities, unit-catalog content identity, protected outer-role membership or neutral statistical-base content identity;
- real canonical label interpretation changes propagate through frame/scientific lineage as appropriate, while advisory grouping changes do not;
- real physical/statistical changes affecting condition/correlation change the relevant neutral identities;
- required outer/protected roles remain disjoint and leakage checks execute on the real neutral units;
- no CV plan is needed to construct the neutral base;
- later target-size split and post-selected CV can consume correlation groups without frame expansion;
- the neutral statistical builder rejects or structurally cannot accept a legacy compatibility-bound source/frame authority as a silent substitute for the required current-generation owners.

### P1-D verification cycle

1. focused neutral-evidence, partition, correlation and leakage tests;
2. affected DATA4/DATA5/statistical-role regression covering reused algorithms;
3. deterministic reconstruction/restart tests for neutral evidence and neutral statistical state;
4. structural check that current-generation objects contain no compatibility-domain partition axis, compatibility-policy lineage or pre-target CV authority;
5. real-owner integration from the P1-B source authority and P1-C canonical frame authority through neutral evidence into the neutral statistical base.

## Pass P1-E — corrective package closure

Reconcile the complete P1 diff against V7 and this revision, then re-derive the P1 affected surface from the assembled candidate.

### Required real-owner integration

Execute a bounded deterministic integration through the actual P1 owners:

```text
source files / manifest
 -> version-agnostic SourceAuthority
 -> version-agnostic CanonicalFrameAuthority
 -> version-agnostic NeutralFeatureEvidence
 -> version-agnostic NeutralStatisticalBase
```

Names above describe semantic roles; exact class names may differ. The test must execute the real owner/control path. It may use small synthetic VASP/source fixtures and bounded underlying scientific data, but it must not substitute legacy DATA2/DATA3 authorities at the P1-B/P1-C owner boundaries or reconstruct the neutral lineage in the test harness.

### Compatibility-policy invariance proof

From the same scientific input, build the complete P1 owner chain under at least two advisory compatibility-grouping policies that produce observably different advisory grouping output. Require equality of all applicable scientific identities and behavior, including:

- source membership eligible for canonical-frame construction;
- source-authority scientific/content digest;
- canonical frame UID and canonical label/labeled-configuration identities;
- canonical frame-authority content digest;
- neutral feature/correlation evidence digest;
- neutral unit IDs and unit-catalog content digest;
- protected outer-role assignments;
- neutral statistical-base content digest.

Only explicitly advisory compatibility diagnostics/policy/group IDs may differ.

This acceptance must be strong enough that it would fail if legacy `TrainingDataSourceCatalog.content_digest`, legacy compatibility-dependent frame-catalog identity, or legacy `DATA4Bundle.content_digest` were reintroduced as a scientific ancestor.

### Scientific-change sensitivity proof

Using the same assembled path, change at least one actual canonical energy/force/stress value and at least one interpretation/convention identity in focused fixtures. Verify the canonical frame identity changes and that the appropriate downstream scientific lineage is invalidated. Separately verify that a supplied non-finite required numerical value cannot obtain canonical identity.

### Naming/absence proof

Structurally verify that new current-generation code and schemas introduced by P1 contain no architecture revision prefix such as `v7_`/`V7` in package paths, symbol names or persisted schema identifiers. Workplan text/history may continue to use V7. Do not create compatibility aliases for removed provisional P1 names.

### Runtime-isolation proof

Verify the old current target-size runtime remains behaviorally intact/reachable until P4 and does not import/expose the new substrate through campaign CLI or public target-size orchestration. Conversely, prove the new P1 substrate does not depend on legacy compatibility-domain authority merely to remain isolated.

### Functional closure evidence

Required closure evidence includes:

- all P1-B/C/D focused tests pass;
- complete affected DATA2/DATA3/DATA4/DATA5/identity/eligibility/duplicate/neutral-partition regression passes;
- serialization/restart reconstruction for every new persisted/current-generation owner passes;
- bounded real-owner integration above passes;
- compatibility-policy invariance and scientific-change sensitivity tests pass;
- structural naming/absence and compatibility-lineage checks pass;
- repository/project-required checks covering the affected Python/package surface execute;
- no compatibility shim, dual scientific identity or test-only surrogate owner was introduced solely to keep obsolete tests green.

A required check that is not executed is not a pass. Full long GPU/production qualification remains deferred under the parent workplan; P1 acceptance is functional/scientific and does not require long training runs.

## Exit gate

P1 is accepted only when the following invariant is true in the **assembled object graph**:

> Canonical usable data, canonical frame identity, neutral feature/correlation lineage, neutral statistical identities and protected-role assignment do not depend on an electronic-structure compatibility-group assignment or compatibility-policy identity; precise provenance remains fully recorded; all new durable code/schema naming is version-agnostic; and the production target-size runtime has not yet switched.

The first implementation's local-unit invariance is insufficient if any current-generation ancestor digest remains compatibility-bound.

Commit/tag the accepted corrected P1 checkpoint before starting P2.
