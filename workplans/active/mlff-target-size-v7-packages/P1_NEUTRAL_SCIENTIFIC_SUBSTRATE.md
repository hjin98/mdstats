---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P1
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 1
status: ready
---

# P1 — Neutral scientific substrate

## Purpose

Establish the V7 current-generation **scientific identity substrate** without changing the currently reachable target-size runtime. This package removes compatibility-domain semantics from canonical numerical-label identity and neutral statistical identity while preserving precise electronic-structure provenance and proven correlation/statistical algorithms.

All V7 frozen decisions remain authoritative. This package must not create a second target-size architecture or make the new substrate publicly authoritative before P4.

## Entry conditions

- Implementation branch is based on/reconciled with the source revision governed by V7.
- Parent V7 workplan and this package are read before implementation.
- Existing DATA2/DATA3/DATA5 regression baseline is understood; known unrelated failures are recorded rather than silently absorbed.

## Pass P1-A — normative/source-map reconciliation

Update affected architecture/spec/config documentation enough that code changes have one unambiguous target:

```text
precise provenance
 -> canonical numerical labels
 -> neutral frame identities
 -> neutral correlation/statistical units
```

Required distinctions:

- provenance facts are descriptive/advisory by default;
- numerical label identity is independent of compatibility grouping;
- compatibility grouping is not a target-training eligibility or partition axis;
- CV is not part of the neutral pre-target statistical substrate.

This pass is non-executable; validate document links/spec consistency. Do not merge future-state docs independently of implementation.

## Pass P1-B — DATA2 provenance/eligibility reset

Implement/evolve source authority so that:

- full `ElectronicStructureFingerprint`-equivalent provenance remains recorded;
- unresolved/partial provenance does not automatically block usable training labels;
- source compatibility-domain assignment is no longer required for training eligibility/current identity;
- compatibility comparison/grouping may survive only as an explicitly advisory report helper;
- atomic-reference identifiability is no longer owned per compatibility domain for target training.

### P1-B acceptance

- DFT, DFT+U, hybrid, smearing/numerical provenance variants can coexist when canonical labels are usable.
- unresolved provenance remains visible in diagnostics.
- genuinely missing/corrupt/unconvertible required labels still fail.
- changing only compatibility grouping policy does not change target-usable source membership.

### P1-B verification cycle

1. focused provenance/source-policy tests;
2. affected DATA2/source-ingestion regression;
3. semantic inspection proving no compatibility-domain decision remains a generic target-training blocker.

Close both semantic and functional dimensions before P1-C.

## Pass P1-C — DATA3 canonical label/frame identity reset

Replace the compatibility-domain-dependent numerical label identity.

Required end state:

- frame UID remains source-occurrence/frame-index identity unless independently invalidated;
- label payload binds canonical numerical values plus the semantic/unit/convention information needed to interpret them;
- advisory compatibility-group/domain identity is not hashed into label payload or labeled-configuration identity;
- precise provenance is referenced separately from canonical label identity;
- geometry duplicate identity remains geometry-only.

### P1-C acceptance

Prove with paired fixtures that:

- identical canonical labels under different provenance/grouping produce the same canonical label identity;
- changing only advisory grouping policy leaves frame UID, label payload and labeled-configuration identity unchanged;
- changing actual canonical energy/force/stress values or interpretation changes numerical scientific identity;
- duplicate/labeled-duplicate semantics remain correct.

### P1-C verification cycle

1. focused identity/serialization/property tests;
2. affected DATA3/frame/duplicate regression;
3. restart/serialization round-trip tests for the new schema;
4. structural inspection proving the new label-payload owner does not consume compatibility-domain assignment.

## Pass P1-D — neutral statistical/correlation substrate

Refactor the useful DATA5 statistical machinery into a current-generation neutral base:

- retain temporal blocks/autocorrelation, events, lineage, condition/regime, replica/structural-realization/reference-group evidence, duplicate/correlation information and protected outer-role behavior where independently required;
- remove compatibility `label_domain_id` from partition-condition/unit identity;
- do not construct pre-target CV plans in the neutral V7 substrate;
- provenance may appear only as advisory diagnostics/strata, not mandatory partition or role-budget keys.

Existing DATA5 may remain for old runtime until P4, but the new V7 neutral substrate must be separately testable and not implemented as a wrapper that still uses label-domain partitioning internally.

### P1-D acceptance

- changing only provenance compatibility grouping does not change neutral unit identities or protected outer-role membership;
- real physical/statistical changes that affect condition/correlation do change the relevant identities;
- required outer/protected roles remain disjoint;
- no CV plan is needed to construct the neutral base;
- later target-size split and post-selected CV can consume its correlation groups without frame expansion.

### P1-D verification cycle

1. focused partition/correlation/leakage tests;
2. affected DATA5/statistical-role regression;
3. deterministic reconstruction/restart test;
4. structural check that the new neutral current-generation objects contain no compatibility-domain partition axis and no pre-target CV authority.

## Pass P1-E — package closure

Reconcile the complete P1 diff against V7 and re-derive the P1 affected surface.

Required closure evidence:

- all P1-B/C/D focused tests pass;
- complete affected DATA2/DATA3/identity/duplicate/neutral-partition regression passes;
- bounded integration from source provenance -> frame catalog -> neutral statistical base executes through real owners;
- old current target-size runtime remains behaviorally intact/reachable until P4; new V7 substrate is not exposed through a mixed-generation runtime;
- no compatibility shim or dual scientific identity was introduced solely to keep obsolete tests green.

## Exit gate

P1 is accepted only when the following invariant is true:

> Canonical usable data and neutral statistical identities no longer depend on an electronic-structure compatibility-group assignment, while precise provenance remains fully recorded and the production target-size runtime has not yet switched.

Commit/tag the accepted P1 checkpoint before starting P2.
