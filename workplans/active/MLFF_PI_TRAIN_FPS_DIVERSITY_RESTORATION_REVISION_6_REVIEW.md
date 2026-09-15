# Revision-6 independent workplan review — PASS

Date: 2026-09-15
Canonical plan: exact Revision-5 body at `d06d98c70455714065035bc434bd949d5b71856d` + `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_6.md`
Disposition: **PASS AS WORKPLAN**

## 1. Review question

Does the Revision-5 + Revision-6 composition now provide a complete, internally coherent and falsifiable plan for restoring the latest mature pre-P6 MVSEL2 selection path under the current one-P_train/P2/prepared-generation architecture, while removing only historically incompatible topology and preserving current ownership/currentness?

## 2. Historical recovery — PASS

The plan now binds recovery to one exact coherent pre-deletion snapshot:

```text
hjin98/mdstats@3937881ef00222e80845aa81f5471d89a4a7736c
```

with P6 deletion identified separately at `747bf1d...`. Historical code, current-at-that-snapshot specs, architecture, fixtures and policies are no longer allowed to be mixed opportunistically across commits.

The plan correctly treats the recovery-snapshot specification index and integrated MVSEL2 chain specification as normative historical owners, with code as concretization/evidence. Any spec/code discrepancy is routed to R1 rather than silently resolved by implementation convenience.

## 3. Capability and ownership restoration — PASS

The restoration boundary is now coherent:

```text
P_train
 -> DATA6
 -> selector-relevant DATA7 projection
 -> TargetCoveragePolicy/TargetCoverageReference
 -> FEAS1
 -> MVIDX1
 -> MVSEL2
 -> REPAIR2
 -> MVQUAL
 -> current P2 TargetTrainingOrder
```

MVSTATE2 is subordinate restart state only.

The plan restores the missing target-coverage reference owner and avoids restoring selector-irrelevant historical DATA7 ownership of E0 fitting, training objective/weights and checkpoint policy, which now belong to current P3/P5 owners. This prevents both capability loss and duplicated current authority.

## 4. D1/D2 method fidelity — PASS AS GATED PLAN

The plan does not pre-accept the restored D1/D2 method. R1 remains mandatory and human-gated.

Within that gate, the recovery target is now precise enough to falsify:

- exact coverage-reference semantics;
- exact neighborhood adjacency;
- hard obligations;
- coverage thresholds, including named family/profile overrides where historically authoritative;
- Phase-A ordering: max hard gain -> canonical bottleneck family -> best bottleneck-family gain -> total gain -> least-used correlation unit -> harmonic representative gain -> sparse diversity -> UID;
- Phase-B representative -> correlation -> diversity -> UID;
- FP64/tolerance/reduction/order semantics;
- REPAIR2 policy and no-regression rules;
- independent MVQUAL predicates;
- current-ladder and full-P_train continuation adaptation.

Revision 6 also prevents the mature sparse-neighborhood diversity term from being mislabeled as classic Euclidean FPS.

## 5. Obligation and qualification ownership — PASS

The plan identifies the collision between current P2 hard-support obligations and recovered historical selector obligations and requires one canonical membership-obligation identity, with current P2 condition identity remaining authoritative.

MVQUAL independently verifies the canonical obligations and coverage predicates, while current P2 exposes one qualification projection. There is no second public qualification owner. Configured but unqualified N cannot be manually selected into training/CV.

The current >=3-qualified-candidate funnel rule remains preserved; infeasibility does not authorize a rescue size or threshold relaxation.

## 6. Full-order / repair / restart semantics — PASS

The current full-permutation requirement is explicitly reconciled with the historical rung-focused chain. Configured repaired prefixes remain protected; continuation after the last configured repaired shell is reconstructed from the exact repaired prefix and primitive sparse authority rather than patched from stale pre-repair mutable state.

MVSTATE2 identity now includes the repair-policy/repaired-prefix position needed for valid post-repair continuation. Accepted REPAIR2 swaps invalidate pre-swap frontier/checkpoint state. This closes the historical mutation-history ambiguity rather than recreating it.

## 7. Persistence/currentness/resource ownership — PASS

The current prepared generation and CampaignStore remain the only completed-preparation/currentness owners. The plan preserves:

- prepare-only live-input interpretation;
- immutable content-addressed selector components;
- external file-backed sparse objects by authenticated content identity;
- publish-before-adopt;
- pre-build currentness expectation and CAS adoption;
- stale-build inertness;
- downstream no-reconstruction rule;
- preparation-configuration invalidation for selector-policy/provider/schema changes.

Provider/model lifetime is routed to the existing provider owner if recovered selector evidence still needs foundation inference. The plan does not create an MVSEL-specific model loader or resource scheduler.

## 8. Independent-oracle architecture — PASS

Revision 6 closes the remaining common-mode evidence defects.

TargetCoverageReference gets an independent bounded family/weight/radius/support oracle. MVIDX1 gets a direct mathematical adjacency oracle independent of production sparse arrays, including the inclusive radius boundary and a wrong-edge counterfactual where all downstream consumers share the same corrupted relation.

Exact numerical-boundary fixtures cover inclusive `best - epsilon`, canonical bottleneck-family ties, Phase-B outward lazy bounds and optimized/native near-tie equivalence. Therefore a self-consistent wrong MVIDX or numerically altered optimized backend can no longer hide behind selector/MVQUAL agreement.

## 9. Storage and packaging closure — PASS

Revision 6 adds real-owner external-artifact retention/reclamation/corruption tests and explicitly reuses the current storage owner. It also requires clean current package/install evidence for any restored native/OpenMP backend, or an explicit omission plus qualification of the exact retained fallback.

This prevents historical native performance evidence from being misapplied to a current package that silently failed to ship the backend.

## 10. Evidence provenance — PASS

Historical-equivalence expected values must now be tied to immutable recovery-snapshot artifacts, an independent reference procedure, or hand/analytical bounded results. Candidate-self-generated goldens are explicitly insufficient. Shared implementation provenance is treated as a common evidence cluster rather than false independent corroboration.

## 11. PEM/HAS and capability transfer — PASS

The plan binds accepted project memory to:

```text
hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
```

with no same-branch semantic candidate overlay. SP-001 through SP-004 and FF-001 through FF-005 receive explicit applicability dispositions, including conditional resource/model items. The accepted PEM's PARTIAL historical coverage is not treated as proof of absence, and direct historical intake supplements it.

The required capability-transfer map covers the mature selector capabilities and their current owner/evidence routes.

## 12. Challenge pass

No remaining plan-level Serious Challenge was found.

The **product's current UID-capable target-order method remains under the existing Serious Challenge** until R1 D1/D2 acceptance and downstream implementation/qualification complete. PASS AS WORKPLAN does not self-ratify the restored scientific/numerical method.

No incompatible simultaneous requirement was found among:

- restoring latest MVSEL2 semantics;
- one current P_train;
- exact nested current T_N prefixes;
- current configurable ladder;
- current EVAL2/reducer;
- current prepared-generation/currentness ownership;
- current P5 CV/production;
- deferred final GPU qualification.

## 13. Final disposition

**PASS AS WORKPLAN.**

Revision 5 closed the semantic/ownership/history gaps. Revision 6 closed the remaining independent-oracle, numerical-boundary, external-artifact lifecycle, packaging and evidence-provenance gaps. No further workplan-level blocker was found in this pass.

Implementation must begin at R1 D1/D2 reconstruction and independent falsification; it must not jump directly to restoring deleted Python modules as accepted current behavior.
