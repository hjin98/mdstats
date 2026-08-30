---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 5
status: active
package_revision: 5
amended_date: 2026-08-29
entry_p4_closure_commit: 145388e5ad11733be1c19539886e34b82cc7d7d2
revision4_baseline_commit: e19962966116586da8a028c252a53deb80cd6795
revision3_baseline_commit: 178a4e653693b810cb02e5ea8bd6bd376da93ab0
revision2_baseline_commit: 2a3c3776aa03ac7e45dd0de2986a6bb390deb710
revision1_baseline_commit: 5bf53c99ce31d1438c21bae81c0f30c79176bdc4
compatibility_policy: current-generation-cutover-no-derived-migration
reconciliation_reason: Final independent design review of revision 4 found one remaining P5-local identity-layer inconsistency without invalidating the frozen parent or any accepted P1-P4/P5 scientific decision: CvValidationPolicyIdentity was described as owning exact selected-relation projection and fold-local fitted-product lineage even though the same revision required policy/recipe identity to remain separate from realized plans and evidence; FinalProductionPolicyIdentity likewise listed inherited M3 scientific lineage as if it were a mutable production-policy choice. Revision 5 normalizes the hierarchy to an acyclic policy -> plan -> realized-evidence graph and preserves every unaffected revision-2/revision-3/revision-4 obligation.
---

# P5 revision 5 — final identity normalization and implementation handoff closure

## 0. Authority, precedence, and preserved design

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. P5 remains bound to Protocol 5.8.0.

Revision 4 at `e19962966116586da8a028c252a53deb80cd6795` is the complete immediate baseline and is incorporated here by reference. Revisions 2 and 3 remain incorporated through revision 4. Every prior P5 obligation remains mandatory except where this revision explicitly corrects identity ownership.

Revision 5 does **not** reopen or weaken:

- exact `T_selected = pi_train[:N_selected]` semantics or P1-P4 authority;
- P4 currentness reauthentication and commit-time stale-generation publication fencing;
- complete selected-only post-selection CV with configured `K >= 2` and no current `cv_not_performed` production bypass;
- complete canonical P1 split-exclusion/protected-relation authority projected onto selected data;
- target-only outer-fold CV acceptance and target-only checkpoint/seed ordering after mandatory replay/physical admissibility;
- all-required-fold and all-required-CV-seed/variant acceptance;
- replay and cross-fold dispersion as non-ranking diagnostics/admissibility evidence unless a future governing scientific revision explicitly promotes them;
- M3 as development/model-selection evidence only, never independent validation;
- fresh final-production model/optimizer/RNG ancestry and collision-proof screen/CV/final execution namespaces;
- `[training].max_num_epochs` as a final-production-only horizon independent of target-size `n3` and CV budget;
- the parent invalidation DAG separating upstream target-size, CV-only policy, and production-only policy;
- no CV -> target-size feedback;
- deferred long GPU/full-production qualification.

Revision 5 has precedence only for identity ownership, dependency direction, restart binding, and acceptance evidence on those surfaces.

---

## 1. Defect corrected by revision 5

Revision 4 correctly split the downstream design into shared-method, CV-specific, and final-production-specific policy identities. Two phrases nevertheless left a circular/over-invalidating interpretation available:

1. `CvValidationPolicyIdentity` was said to bind the exact selected split-exclusion projection and fold-local fitted-product lineage even though those are realized descendants of policy/configuration.
2. `FinalProductionPolicyIdentity` was said to bind frozen M3 lineage even though M3 is inherited P2/P4 scientific evidence, not a mutable production-policy choice.

A policy identity must be computable from canonical resolved configuration plus stable method/policy definitions **before** expensive numerical realization. Exact selected memberships, projected P1 components, fold assignments, fitted DATA7/DATA8 products, checkpoints, EVAL2 results, M3 lineage, and other realized scientific evidence bind downstream plans/evidence; they do not redefine the policy that authorized them.

The corrected graph is acyclic:

```text
current authenticated predecessor authority
        + resolved method/policy configuration
                    |
                    v
             policy identities
                    |
                    v
               plan identities
                    |
                    v
         materialization/run/evidence
                    |
                    v
            acceptance/publication
```

No descendant digest or realized output may flow upward into a policy identity.

---

## 2. Frozen revision-5 identity hierarchy

Exact durable product names are delegated and must remain version-agnostic. The ownership/dependency boundaries below are frozen.

### 2.1 `PostSelectionMethodIdentity` — shared scientific method definition

Preserve revision 4. This identity contains only the scientifically material method definition that CV validates and final production must share, such as the accepted foundation/model/head family and initialization policy, objective/weighting recipe, replay/exposure/admissibility semantics, optimizer family and shared non-role-specific settings, LR/stopping policy family where shared, precision/backend/runtime lock where scientifically material, checkpoint admissibility semantics, target-only ordering semantics, and genuinely common integrity constraints.

It must be computable without:

- exact CV fold membership;
- exact P1 selected-relation projection;
- fold-local fitted products;
- CV evaluation outputs;
- M3 membership/evidence lineage;
- final-production fitted products/checkpoints;
- production result/committee identity.

If an algorithm/schema/recipe version materially changes the method, that stable recipe identity belongs here or in the appropriate role-specific policy. The **realized output** of executing the recipe does not.

### 2.2 `CvValidationPolicyIdentity` — CV policy/configuration only

`CvValidationPolicyIdentity` owns the canonical resolved CV choices that are known before the CV plan is realized, including as applicable:

- configured `K >= 2`;
- fold/partition seed and seed-mode policy;
- fold-construction algorithm/policy version;
- CV checkpoint-monitor/evaluation **policy**, not exact membership;
- CV-only TRAIN2 budget/stopping policy;
- target-only outer-validation metric/threshold predicate;
- all-required-fold/all-required-variant aggregation rule;
- diagnostic-only dispersion/replay-summary policy;
- fold-local preparation **recipe/policy** where it is CV-specific rather than part of the shared method.

It explicitly does **not** own:

- `T_selected` membership or P4 current revision;
- the current P1 relation-authority digest;
- the selected-only P1 relation projection/component digest;
- exact fold gradient/monitor/outer-evaluation/purge memberships;
- fold-specific fitted E0/transforms/features/weights or other DATA7/DATA8 products;
- TRAIN2 checkpoints, optimizer/RNG state, EVAL2 records, or CV acceptance outcomes.

The CV policy digest must therefore be computable before fold construction and before numerical execution.

### 2.3 `CvPlanIdentity` — current selected scientific inputs plus CV policy realization

Introduce or adapt one immutable current CV plan identity below the policy layer. It binds enough exact scientific lineage to make a CV campaign reproducible and restart-safe, including at minimum:

```text
current P4 selected binding / generation lineage
exact N_selected / T_selected membership identity
PostSelectionMethodIdentity digest
CvValidationPolicyIdentity digest
canonical current P1 split-exclusion/protected-relation authority identity
selected-only projected/transitive component identity
exact deterministic per-fold role memberships
configured required CV seed/variant run matrix as applicable
```

This is derived plan state, not a new target-size or P1 authority.

Changing the P1 relation authority or exact selected projection may change/reject the CV plan while leaving the CV **policy** digest unchanged when configuration is unchanged. Changing fold assignment because policy/seed changes changes both the policy as appropriate and the derived plan. Exact memberships never flow upward to redefine the policy.

### 2.4 `CvFoldRunPlan` and realized CV evidence

Each fold/run descends from `CvPlanIdentity` and binds the exact fold/seed/run role needed by the shared DATA7/DATA8/TRAIN2/EVAL2 execution owners.

Realized descendants include, as applicable:

- fold-local fitted preparation products;
- materialized DATA8 bundle/job identities;
- fresh optimizer/RNG/run state;
- checkpoint and monitor evidence;
- frozen representative identity;
- exact held-out EVAL2 evidence;
- fold/seed/campaign acceptance records.

These descendants bind their parent plan/policy/method digests. They cannot alter those parent digests to make themselves current.

A deterministic fitted product that does not match the plan + recipe + authorized fold-training evidence is invalid evidence; it is not a reason to mutate the policy or plan after the fact.

### 2.5 `FinalProductionPolicyIdentity` — production policy/configuration only

`FinalProductionPolicyIdentity` owns canonical resolved production-only choices known before final realization, including as applicable:

- `[training].max_num_epochs`;
- final-production seed/job policy and multiplicity;
- production-only adaptive/stopping/runtime controls that are scientifically relevant;
- final checkpoint/export/committee policy not already part of the shared method;
- other production-only configured choices permitted by the frozen parent.

It explicitly does **not** own:

- current P4 generation/selected membership;
- M3 membership/digest or other inherited P2 scientific evidence;
- accepted CV evidence/result digest;
- final fitted preparation/materialization products;
- checkpoints, model exports, or committee members actually produced.

M3 remains an inherited P2/P4 development/model-selection evidence lineage. It binds the final plan/evidence that consumes it; it is not a production-policy knob.

### 2.6 `FinalProductionPlanIdentity` — authorization and exact inherited scientific lineage

Introduce or adapt one immutable final-production plan below the production-policy layer. It binds, at minimum:

```text
current P4 selected binding / exact full T_selected identity
PostSelectionMethodIdentity digest
accepted current CV authorization/evidence identity for that method
FinalProductionPolicyIdentity digest
frozen P2/P4 M3 development/model-selection lineage
exact final seed/job/run-role matrix
required replay/source lineage and other inherited scientific parents
```

The plan authorizes fresh full-`T_selected` production under the already accepted method and current production policy. It does not continue screening/CV model/optimizer/RNG state.

If current predecessor lineage changes, stale final plans reject through currentness/restart validation; the implementation must not counterfeit currency by rehashing the old plan locally.

### 2.7 Final materialization/run/evidence layer

Final DATA7/DATA8/TRAIN2/EVAL2 materialization and training evidence descend from `FinalProductionPlanIdentity`.

Realized fitted products, checkpoint sets, selected representatives, exports, committee membership, runtime summaries, attempt/recovery state, and publication records belong here or in narrower existing descendant records. They may be content-addressed and reused when their complete parent identity still matches, but they never become inputs to the production-policy digest that authorized them.

---

## 3. Identity and invalidation invariants

The following dependency rules are frozen.

### 3.1 Policy identities are pre-execution and acyclic

Every shared/CV/final policy digest must be deterministically computable from canonical resolved configuration, stable policy/algorithm/schema identity, and predecessor **policy definitions** needed to define the method. No DATA7/DATA8/TRAIN2/EVAL2 result, fitted-product digest, exact fold membership, current M3 evidence digest, checkpoint, model export, or acceptance result may be required to compute a policy digest.

### 3.2 Plans bind exact current scientific lineage

Plan identities bind exact predecessor/current scientific state needed for their realization. This includes `T_selected`, P1 relation projection and exact folds for CV, and M3/current accepted-CV authorization for final production.

Plans may depend on policy identities; policy identities may not depend on plans.

### 3.3 Evidence binds plans

Realized evidence binds the exact plan plus the materialized/run-specific identity required by its semantic owner. Evidence may not rewrite its parent plan/policy identity to preserve apparent validity.

### 3.4 Parent invalidation DAG remains unchanged

- production-only `[training].max_num_epochs` change -> `FinalProductionPolicyIdentity` and affected final plan/evidence change; P4 and accepted CV remain valid;
- CV-only fold/partition/monitor/budget/acceptance-policy change -> `CvValidationPolicyIdentity` and CV plan/evidence/current authorization change; P4 remains valid; production-only policy digest is unchanged;
- P1 relation-authority/current selected-data change -> follow accepted upstream currentness/invalidation; derived CV/final plans/evidence become stale as appropriate without turning that scientific change into a CV-policy edit;
- exact fold-local fitted-product/evidence change or corruption -> descendant evidence changes/rejects; method/CV-policy/plan identity is not post-hoc rewritten;
- M3 lineage/current predecessor change -> final plan/evidence changes/rejects through upstream lineage; `FinalProductionPolicyIdentity` remains unchanged if production configuration is unchanged;
- shared method-definition change -> shared method digest changes and stale CV cannot authorize final production; if the changed field is also upstream target-size scientific identity, existing P1-P4 invalidation rules remain authoritative.

### 3.5 No new mutable authority

These identities are dependency records, not additional current-state registries. P4 CampaignStore/current terminal authority remains the only upstream current selected-state owner. Revision-3/4 commit-time fencing and currentness-by-resolution remain mandatory.

---

## 4. Revision-5 implementation obligations

### P5-B5 — normalize policy, plan, and evidence ownership

Required end state: the downstream identity graph is acyclic, minimally scoped, restart-safe, and matches the parent invalidation DAG.

Required consequences:

1. Reconcile revision-4 shared-method/CV-policy/final-policy code design so policy records contain only canonical policy/configuration and stable recipe/algorithm identity.
2. Add/reuse a distinct CV plan owner for current selected lineage, P1 selected-only split-exclusion projection, exact folds, and required CV run matrix.
3. Add/reuse a distinct final-production plan owner for current selected lineage, accepted CV authorization, final policy, M3 lineage, and exact final run matrix.
4. Keep fold/final fitted products and TRAIN2/EVAL2 outputs below their plan owners.
5. Reuse existing repository protocol/run-plan/content-addressed objects when they already provide these semantics; do not add wrappers or duplicate digest records merely to match conceptual names.
6. Make policy identities available before expensive numerical work and persist enough canonical resolved configuration to reproduce them.
7. Restart/current exposure must authenticate the full parent chain rather than trust a stored child digest as authority.
8. Preserve revision-4 identity separation for CV budget versus production horizon and preserve all revision-3 publication/currentness hardening.

### Required focused and structural acceptance

Through the real configuration/identity/plan owners, prove:

- **pre-execution construction:** shared-method, CV-policy, and final-policy identities can be resolved before DATA7/DATA8/TRAIN2/EVAL2 execution and do not inspect descendant result files/records;
- **CV projection separation:** same method + same resolved CV configuration, but a changed authenticated selected-only P1 relation projection/current selected lineage, keeps the CV-policy digest stable while the CV-plan digest changes or the stale plan rejects;
- **fold realization separation:** tampering/changing a fold-local fitted-product/evidence record cannot change the method/CV-policy/CV-plan digests; it changes or invalidates only the descendant evidence;
- **production horizon:** changing only `[training].max_num_epochs` changes final-policy/final-plan descendants while leaving P4 and accepted CV policy/evidence valid;
- **M3 lineage separation:** changing authenticated M3/current predecessor lineage changes/rejects the final plan/evidence without changing `FinalProductionPolicyIdentity` when production configuration is unchanged;
- **parent mismatch rejection:** CV/final restart rejects evidence whose method/policy/plan parent digests or current selected binding do not match;
- **no circular fields:** structural inspection proves CV-policy serialization contains no exact fold memberships, selected relation-projection digest, or fitted-product/evidence digest, and final-policy serialization contains no M3/current-CV/result/fitted-product digest;
- **no reverse authority:** structural/current-path inspection proves child evidence cannot be supplied as an input that determines its parent policy identity.

If the implementation changes existing shared protocol/run-plan serializers, run their complete affected persistence/restart/API regression. If new records are introduced, add exact serialization/digest stability and malformed-parent rejection tests.

### P5-F5/G5 — assembled current-path reclosure

The final assembled P5 path must have this ownership order:

```text
current P4 SELECTED authority
 -> current selected-training context
 -> shared method identity
 -> CV policy identity
 -> CV plan from exact T_selected + complete P1 protected-relation projection
 -> fresh fold materialization/TRAIN2/EVAL2 evidence
 -> exact all-required-fold target-only CV acceptance
 -> final-production policy identity
 -> final-production plan from full T_selected + accepted CV + M3 lineage
 -> fresh final materialization/TRAIN2/EVAL2
 -> currentness-fenced publication
```

Fresh assembled acceptance must include all revision-2/revision-3/revision-4 real-owner, race, leakage, role, CV-acceptance, replay, fresh-production, M3, locked/calibration, namespace, restart, and invalidation negatives plus the revision-5 identity-layer tests above.

The material semantic owners under acceptance are the production current selected adapter/currentness path, current CV plan/authorization owner, current final-production plan/authorization owner, and real persistence/restart/publication boundaries. Expensive ML training/inference may be bounded/faked below those owners; helper-only identity tests cannot substitute for assembled authorization/restart acceptance.

Stage-local affected regression remains mandatory after material executable stages. Final P5 closure requires fresh affected-surface re-derivation, complete affected regression, repository-required checks, and bounded assembled P4 -> P5 integration on the final candidate.

---

## 5. Implementation authority

### Frozen

Implementation must preserve:

- the complete revision-2 + unaffected revision-3 + unaffected revision-4 contract;
- Protocol 5.8.0 binding and the frozen parent verdict;
- the acyclic `policy -> plan -> realized evidence` dependency direction;
- shared method identity separate from CV/final role-specific policies;
- CV policy separate from exact selected/P1 projection/fold realization;
- final-production policy separate from M3/current-CV/current-selected realization;
- exact current scientific lineage bound at plan/evidence level;
- no upward/reverse digest dependency from evidence to plan/policy;
- all prior currentness, CV completeness/leakage, target-only acceptance/ranking, replay, M3, fresh-production, namespace, invalidation, and qualification-disposition rules.

### Delegated

Implementation may choose:

- exact version-agnostic class/module/schema names;
- whether existing protocol-family/run-plan/materialization records can satisfy one or more conceptual layers without new wrapper types;
- whether exact run matrices are embedded in a plan or represented by deterministic child run-plan records, provided ownership and parent binding remain unambiguous;
- exact content-addressed storage layout for plan/evidence records;
- exact error types/messages consistent with established package conventions;
- local factoring and bounded fixtures below the semantic owner boundaries.

### Reopen only on evidence

Reopen only the affected P5 identity surface if implementation demonstrates that:

1. an existing authoritative repository contract intentionally requires realized fitted/evaluation evidence to define a policy identity and cannot be separated without changing scientific semantics;
2. M3 is intentionally a user-configurable production-policy choice rather than inherited P2/P4 scientific lineage, contrary to the frozen parent;
3. exact CV fold realization must be part of the policy definition rather than a deterministic plan derived from that policy, and repository evidence shows this is a material governing contract rather than legacy topology;
4. an acyclic policy -> plan -> evidence representation cannot satisfy restart/currentness without adding a second current-state authority;
5. another frozen revision-4 assumption is disproved by implementation evidence.

Do not reopen P1-P4 or the target-size scientific design merely because existing legacy MLCV types mix these layers; refactor/bypass obsolete topology under P5 unless a genuine governing contradiction is demonstrated.

---

## 6. Exit gate

P5 revision 5 is implementation-ready only under the complete cumulative revision-2 + revision-3 + revision-4 + revision-5 contract.

P5 is accepted after implementation only when:

> Current P4-selected authority remains the sole upstream selection/currentness owner; downstream method and role-specific **policy identities are resolved before numerical realization and contain no descendant evidence**; exact selected/P1/CV/M3 scientific lineage is bound by immutable plans; fitted/materialized/TRAIN2/EVAL2/checkpoint/acceptance products remain descendants of those plans; every required selected-only CV fold/seed/variant passes the configured target-only predicate after mandatory admissibility; and fresh full-`T_selected` final production executes under the CV-accepted shared method plus independent production policy without any reverse evidence-to-policy authority, stale-generation publication, or cross-role restart collision.

After stage-local closure, fresh assembled affected regression/integration, and independent review pass, mark P5 implemented/accepted and commit the formal P5 closure checkpoint. P6 remains blocked until that closure.
