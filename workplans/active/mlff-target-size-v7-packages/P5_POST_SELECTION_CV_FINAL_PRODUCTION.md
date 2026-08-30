---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 5
status: active
package_revision: 4
amended_date: 2026-08-29
entry_p4_closure_commit: 145388e5ad11733be1c19539886e34b82cc7d7d2
revision3_baseline_commit: 178a4e653693b810cb02e5ea8bd6bd376da93ab0
revision2_baseline_commit: 2a3c3776aa03ac7e45dd0de2986a6bb390deb710
revision1_baseline_commit: 5bf53c99ce31d1438c21bae81c0f30c79176bdc4
compatibility_policy: current-generation-cutover-no-derived-migration
reconciliation_reason: Final independent design review of revision 3 found three remaining P5-local contract defects without invalidating the frozen parent or accepted P1-P4 architecture: revision 3 incorrectly bound production-only max_num_epochs and role-specific monitoring into one CV-to-production protocol identity contrary to the parent invalidation DAG; its CV leakage authority narrowed accepted P1 split-exclusion semantics to correlation/duplicate groups; and it removed legacy replay-weighted scoring without positively freezing the current target-only all-required-fold CV acceptance rule. Revision 4 corrects only those surfaces and preserves all unaffected revision-2/revision-3 hardening.
---

# P5 revision 4 — final parent-alignment and CV acceptance closure

## 0. Authority, precedence, and preserved state

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. P5 remains bound to Protocol 5.8.0.

Revision 3 at `178a4e653693b810cb02e5ea8bd6bd376da93ab0` is the complete immediate baseline and is incorporated here by reference. Revision 2 remains incorporated through revision 3. Every revision-2/revision-3 obligation remains mandatory except where this revision explicitly corrects it.

Revision 4 does **not** reopen or weaken:

- exact `T_selected = pi_train[:N_selected]` semantics;
- P1-P4 accepted scientific/runtime/currentness authorities;
- commit-time stale-generation fencing for P5 current publication;
- selected-only post-selection CV with `K >= 2` and no current `cv_not_performed` production bypass;
- target-only checkpoint/seed ordering after replay/physical admissibility;
- M3 as development/model-selection evidence only, never independent validation;
- fresh final-production optimizer/model/RNG ancestry;
- collision-proof screen/CV/final execution namespaces;
- `[training].max_num_epochs` as the fresh final-production horizon independent of target-size `n3`;
- no CV -> target-size feedback;
- deferred long GPU/full-production qualification.

This revision has precedence only for the three corrected surfaces below.

---

## 1. Defects corrected by revision 4

### 1.1 Revision 3 over-coupled CV and final-production identity

Revision 3 required one `PostSelectionTrainingProtocolIdentity` containing production `[training].max_num_epochs`, target-evidence/monitor policy, and other fields that are not actually shared between CV and final production. It then required CV and final runs to carry the same complete digest.

That conflicts with the parent invalidation DAG:

```text
CV-only settings -> invalidate CV descendants only
production-only budget/adaptive settings -> invalidate production descendants only
```

It also conflicts with the parent rule that CV owns its own fold monitoring/evaluation policy and fold-local preparation, while final production may use frozen M3 for development/model selection.

### 1.2 Revision 3 narrowed accepted P1 leakage authority

Revision 3 described CV grouping through neutral correlation/duplicate groups. Accepted P2 revision 3 already established that those relations are not exhaustive: P1 may own additional relations explicitly marked split-excluding/protected, and their deterministic transitive closure must be respected.

P5 must inherit that same P1 authority rather than rediscover or narrow it.

### 1.3 CV methodological acceptance was under-specified

Revision 3 correctly removed legacy target+replay combined-score authority, but did not positively freeze the replacement CV acceptance rule. The current non-conflicting behavior is target-only outer-fold acceptance, all required folds present and accepted, all required CV seed/variant aggregates accepted, and dispersion diagnostic-only.

Implementation may not invent mean-only, majority-fold, best-seed, replay-weighted, or partial-fold acceptance.

---

## 2. Frozen revision-4 design

### 2.1 Hierarchical downstream identity: shared method plus role-specific policies

Replace revision 3's monolithic CV/final identity with the minimum three-level ownership necessary to preserve both comparability and the parent invalidation DAG.

Conceptually:

```text
CurrentSelectedTrainingContext
  + PostSelectionMethodIdentity
      + CvValidationPolicyIdentity
          -> exact CV plan/run/evidence descendants
      + FinalProductionPolicyIdentity
          -> exact final-production run/evidence descendants
```

Exact product names are delegated and must remain version-agnostic. The ownership split is frozen.

#### A. `PostSelectionMethodIdentity` — shared scientific method

This identity binds only method-defining facts that genuinely must match between the method CV validates and the method final production executes, including as applicable:

- foundation/model/head initialization family and scientific identity;
- training mode and architecture-relevant method identity;
- objective/property/configuration weighting **policy/recipe**;
- replay source/exposure semantics and TRUE_DFT retention/admissibility policy;
- optimizer family and non-role-specific optimizer settings;
- learning-rate/stopping **policy family/recipe** where scientifically shared;
- target/replay head weights and exposure/balancing semantics;
- precision/dtype/backend/runtime-lock identity where scientifically material;
- checkpoint admissibility semantics;
- target-only checkpoint/model-ordering semantics;
- physical/integrity constraints that are genuinely common to both roles;
- any other method field for which changing the field means CV validated a scientifically different training method.

It binds policy/recipe identity, not role-specific fitted products or role-specific evidence memberships.

The following do **not** belong in the shared method identity merely because both phases use TRAIN2/EVAL2:

- CV fold count or partition seed;
- exact CV fold memberships;
- CV checkpoint-monitor/evaluation membership;
- fold-specific fitted E0/transforms/features/weights or other fitted fold products;
- final M3 development/model-selection membership;
- final-production seed/job multiplicity;
- final-production `[training].max_num_epochs`;
- final-production-only adaptive/runtime controls.

A change to `PostSelectionMethodIdentity` invalidates both CV and final-production descendants and, when that method field is also upstream target-size scientific identity, follows the existing P1-P4 invalidation DAG exactly as before.

#### B. `CvValidationPolicyIdentity` — CV-only validation policy

This identity binds current post-selection CV choices that are allowed to vary without changing P4 target-size state or final-production-only configuration, including:

- configured fold count `K >= 2`;
- fold/partition seed and seed-mode policy;
- exact CV-universe/split-exclusion projection identity;
- CV fold monitoring/evaluation policy;
- target-only CV acceptance metric/threshold policy;
- all-required-fold/all-required-variant aggregation rule;
- diagnostic-only dispersion policy;
- CV-specific training-budget/stopping realization if the accepted current CV methodology requires one;
- the preparation **recipe** inherited from the shared method plus exact fold-local fitted-product lineage.

CV fold execution may fit E0/transforms/features/objective-derived products only from authorized fold-training evidence according to the shared recipe. Held-out outer-fold evidence cannot contribute to fitted preparation or checkpoint choice.

**CV budget rule:** P5 must not derive the CV training budget from target-size `n3` or from production-only `[training].max_num_epochs`. Resolve it through one canonical CV-only TRAIN2 budget/stopping owner. Reuse an existing current owner if one exists. If the current code has no separate canonical CV budget field/owner, introduce the smallest version-agnostic CV-only policy surface needed to make this separation explicit; preserve the established default CV execution extent rather than aliasing the field to `[training].max_num_epochs`. A production-only `max_num_epochs` edit must not change the CV policy digest.

If repository evidence shows CV cannot be executed correctly without making production `max_num_epochs` a CV scientific input, stop and reopen only this P5 budget decision rather than silently violating the parent invalidation DAG.

Changing only CV policy invalidates affected CV evidence and any downstream authorization that depends on that CV acceptance; it does not invalidate/rebuild P4 target-size state. Existing final-production artifacts may cease to be *currently authorized* if their required CV acceptance binding changes, but the production-only scientific identity itself is not rewritten.

#### C. `FinalProductionPolicyIdentity` — production-only realization

This identity binds final-production choices that the parent declares downstream of CV, including:

- resolved `[training].max_num_epochs` production horizon;
- final-production seed/job policy and multiplicity;
- frozen M3 development/model-selection role identity;
- production-specific adaptive/runtime controls that are scientifically relevant;
- final run/checkpoint/export/committee policy not shared with CV.

Changing only `[training].max_num_epochs` or another production-only field:

```text
P4 target-size authority -> remains current
accepted CV evidence      -> remains scientifically valid
old final-production descendants -> stale/rebuild as appropriate
```

No CV rerun is required solely because a production-only horizon/adaptive setting changes.

#### D. Authorization relation

Final production is authorized by:

```text
current P4 selected binding
+ matching PostSelectionMethodIdentity
+ accepted CvValidationPolicyIdentity/evidence for that method
+ current FinalProductionPolicyIdentity
```

CV and final production therefore share the **method digest**, not one complete role-specific policy digest.

Every revision-3 statement requiring CV and final runs to carry the same complete `PostSelectionTrainingProtocolIdentity` digest is superseded by this hierarchy.

### 2.2 Complete P1 split-exclusion authority projected onto `T_selected`

Current P5 CV construction must consume the same canonical P1-owned split-exclusion/protected-relation authority accepted by P2, not a locally redefined subset.

Frozen data flow:

```text
accepted current P1 relation authority
  -> exact T_selected projection
  -> deterministic transitive selected-only split-exclusion components
  -> CV fold role assignment
```

Rules:

1. Same neutral correlation/partition unit and canonical geometry-duplicate relations remain mandatory.
2. They are not exhaustive. Every additional P1 relation whose accepted semantics are `split-excluding`, `protected`, or equivalent must participate.
3. P5 does not infer or reconstruct these relations from provenance, geometry, labels, CV outcomes, or ad hoc heuristics. P1 owns relation semantics.
4. Only endpoints already in `T_selected` enter the CV universe. An unselected related sibling never enlarges `T_selected`.
5. Relations are reduced to deterministic transitive connected components over selected endpoints. Mixed chains across unit, duplicate, and additional protected relation types remain one indivisible leakage component.
6. CV training, checkpoint-monitor, outer-evaluation, and purge/defer assignment must obey these selected-only components according to the accepted CV-role disjointness policy.
7. The canonical P1 relation-authority identity/digest and the exact selected-only projection/component identity bind the CV plan and restart evidence.
8. A changed P1 relation authority follows the existing upstream currentness/invalidation chain; P5 cannot preserve stale CV lineage by trusting a locally stored component digest.

Revision-3 shorthand referring only to `neutral correlation/duplicate groups` is superseded by this complete P1 relation authority.

### 2.3 Frozen target-only CV acceptance semantics

Introduce or adapt one canonical serialized current CV acceptance policy. Exact class/schema names are delegated; semantics are frozen.

For every required `(method, CV seed/variant, fold)`:

```text
fresh fold training
 -> checkpoint candidates
 -> mandatory target/replay/physical admissibility
 -> target-only checkpoint selection on authorized fold monitor
 -> freeze representative
 -> outer target evaluation on held-out fold
 -> fold acceptance
```

The held-out outer fold is never visible to the checkpoint-selection owner before the representative is frozen.

#### Fold acceptance

A fold is accepted only when:

- its required representative exists and passed mandatory admissibility;
- its exact held-out outer evaluation completed successfully under the bound EVAL2 role;
- the canonical target-only outer-validation metric satisfies the configured serialized threshold/predicate.

The exact metric and threshold remain configuration/policy-owned; P5 does not hard-code the current numerical default into architecture.

Replay TRUE_DFT can make a checkpoint inadmissible according to its bound retention/safety policy, but replay performance contributes no score bonus, weighted average, tie-break, or outer-fold acceptance credit.

#### Seed/variant acceptance

A required CV seed/variant is accepted only when:

- every configured fold is present exactly once;
- every required fold is accepted;
- no fold is silently skipped, substituted, duplicated, or replaced by an aggregate mean.

One failing required fold fails that seed/variant. A good average over folds cannot override a failing fold.

#### Campaign/method acceptance

The post-selection method is CV-accepted only when every required CV seed/variant in the resolved current CV policy is accepted.

No `best seed wins`, majority-seed, majority-fold, incomplete-fold, or `cv_not_performed` production authorization is permitted on the current path.

Cross-fold/cross-seed dispersion and replay summaries remain diagnostic unless a future explicit parent-level scientific revision makes one a gate. They cannot silently become an acceptance threshold.

CV failure remains a downstream methodological-validation failure. It cannot mutate `N_selected`, rerun the target-size reducer, choose a different N, or reinterpret P4 state.

---

## 3. Revision-4 implementation obligations

### P5-B4 — repair identity hierarchy and invalidation ownership

This stage replaces only revision-3 identity/config coupling. Revision-3 currentness fencing remains accepted design.

Required consequences:

1. Create/reuse one canonical shared method identity plus separate CV-validation and final-production policy identities.
2. Route all three through the canonical resolved configuration path.
3. Keep policy/recipe identity separate from fold/final fitted-product lineage.
4. Ensure fold-local preparation uses only fold-training evidence; held-out outer evaluation is absent from fit/checkpoint owners.
5. Remove `[training].max_num_epochs`, M3 membership, and final-only seed/adaptive policy from the shared method/CV identity.
6. Ensure changing only `[training].max_num_epochs` leaves P4 and accepted CV evidence current while invalidating only affected final-production descendants.
7. Ensure changing a shared method field invalidates CV and final descendants and follows upstream target-size invalidation when the field is also part of P1-P4 scientific identity.
8. Ensure changing only fold count/partition/monitor/CV-only budget invalidates CV/downstream authorization without mutating P4 target-size state.

Mandatory tests through real config/identity owners:

- production horizon change: P4 unchanged, CV method/policy evidence still valid, final-production identity changes;
- CV fold-count/partition change: P4 unchanged, CV identity changes, production-only identity unchanged;
- shared LR/objective/replay/method field change: shared method digest changes and stale CV cannot authorize final production;
- fold-specific fitted product differs across folds while shared method identity remains equal;
- held-out outer-fold data cannot enter fold fitting/checkpoint-monitor inputs;
- no `max_num_epochs -> CV budget` or `n3 -> CV/production budget` hidden dependency edge.

### P5-C4 — inherit full P1 split-exclusion authority

Required consequences:

1. Reuse the canonical P1 split-exclusion/protected relation owner already consumed by accepted P2.
2. Project that authority onto exact `T_selected` without enlarging membership.
3. Compute deterministic transitive selected-only components before fold allocation.
4. Bind relation-authority and projected-component identity into CV plan/restart validation.
5. Keep legacy DATA5/label-domain CV authority unreachable.

Mandatory focused tests:

- **relation-only protection:** two selected frames in different neutral units and with different geometry fingerprints, connected only by an additional P1 protected relation, cannot be placed in leakage-conflicting CV roles;
- **mixed transitive closure:** unit relation -> geometry duplicate -> additional protected relation collapses to one selected component;
- selected frame + unselected protected sibling does not enlarge `T_selected`;
- stale/rebuilt P1 relation authority rejects old CV plan through the real P1/P5 validation path;
- structural inspection proves one P1 relation input and no P5 ad hoc relation taxonomy.

Affected P1/P2 relation-authority regression must be rerun if implementation touches their exposed owner/API; otherwise preserve accepted upstream evidence and run P5 consumption regression.

### P5-D4 — freeze current CV acceptance owner

Required consequences:

1. Replace/bypass legacy replay-weighted CV acceptance/ranking fields on the current path.
2. Preserve the configured target-only outer-fold threshold/predicate as the fold scientific gate.
3. Preserve mandatory replay/physical admissibility as constraints, not score credit.
4. Require every configured fold for every required CV seed/variant to pass.
5. Keep dispersion/replay summaries diagnostic-only.
6. Make final-production authorization consume this exact accepted CV evidence plus matching shared method identity.

Mandatory negatives:

- one fold fails target threshold while overall mean would pass -> campaign fails;
- one required fold missing -> campaign fails;
- duplicate fold with another missing -> campaign fails;
- one required CV seed/variant fails while another passes -> method CV fails;
- replay-weighted combined score would reverse target ordering -> target-better admissible representative remains selected;
- replay changes within admissible range cannot turn target-failed outer fold into pass;
- high dispersion alone cannot fail an otherwise accepted campaign under the frozen diagnostic-only policy;
- `cv_not_performed`, K=0, K=1 cannot authorize current final production.

### P5-F4/G4 — orchestrator and assembled reclosure

All current P5 orchestration must resolve:

```text
P4 current selected authority
 -> currentness-safe selected binding
 -> PostSelectionMethodIdentity
 -> complete P1-selected split-exclusion projection
 -> CvValidationPolicyIdentity + complete K-fold plan
 -> fresh CV TRAIN2/EVAL2
 -> exact all-required-fold target-only CV acceptance
 -> FinalProductionPolicyIdentity
 -> fresh full-T_selected production TRAIN2
 -> currentness-fenced downstream publication
```

Fresh assembled acceptance must additionally prove:

- production-only `max_num_epochs` mutation does **not** require CV rerun;
- CV-only mutation does not mutate P4 or rewrite production-only scientific policy;
- shared method mutation invalidates stale CV authorization;
- complete P1 protected-relation closure is obeyed by CV roles;
- exact CV acceptance cannot be counterfeited by averages, best-seed selection, partial folds, replay-weighted scores, or `cv_not_performed`;
- all revision-3 race, role, replay, fresh-production, M3, locked/calibration, namespace, restart, and currentness negatives remain mandatory.

Stage-local affected regression remains required after every material executable stage. Final P5 closure requires fresh affected-surface re-derivation, complete affected regression, and bounded assembled real-owner P4 -> P5 integration on the final candidate.

---

## 4. Implementation authority

### Frozen

Implementation must preserve:

- revision-2 + unaffected revision-3 contract;
- Protocol 5.8.0 binding;
- parent one-way scientific dependency and P1-P4 accepted authority;
- shared-method / CV-policy / production-policy identity separation;
- parent invalidation DAG: CV-only settings do not invalidate P4, production-only budget/adaptive settings do not invalidate CV;
- complete canonical P1 split-exclusion/protected relation authority projected onto exact `T_selected`;
- mandatory K >= 2 complete selected-only CV;
- target-only outer-fold acceptance and target-only checkpoint/seed ordering after admissibility;
- all required folds and required CV seed/variants must pass;
- dispersion/replay summaries diagnostic-only unless explicitly promoted by a future governing scientific revision;
- `[training].max_num_epochs` as final-production-only horizon, independent of `n3` and CV budget;
- M3 development/model-selection classification;
- fresh final training and cross-role namespace isolation;
- commit-time stale-generation exclusion.

### Delegated

Implementation may choose:

- exact version-agnostic class/module/schema names for the three identity levels;
- whether existing current protocol/policy records can be refactored to supply the shared method identity rather than adding a new wrapper;
- exact CV-only budget/stopping configuration field/owner if the current code lacks one, provided it is canonical, reproducible, independent of production `max_num_epochs` and preserves established default CV behavior;
- exact data structure/algorithm for selected-only protected-relation connected components, provided it consumes P1 authority and preserves deterministic transitive closure;
- exact current target metric/threshold schema owner for CV acceptance, provided no hard-coded workplan constant replaces configured policy;
- ordinary internal factoring and bounded test doubles below the semantic owners under acceptance.

### Reopen only on evidence

Stop dependent implementation and reopen only the affected P5 surface if evidence shows:

1. no scientifically coherent CV-only TRAIN2 budget/stopping owner can preserve the parent invalidation DAG;
2. accepted P1 relation authority cannot be consumed/projected by P5 without changing P1 semantics;
3. target-only all-required-fold CV acceptance conflicts with an explicit current governing scientific policy not superseded by the parent;
4. final M3 evidence cannot serve its accepted development/model-selection role;
5. shared method identity cannot be separated from role-specific fitted products/policies without changing the scientific method;
6. a material training-method change invalidates the upstream target-size experiment;
7. the frozen parent and implemented predecessor authorities are materially contradictory rather than locally reconcilable.

---

## 5. Exit gate

P5 revision 4 is implementation-ready only under the complete revision-2 + revision-3 + revision-4 contract.

P5 is accepted after implementation only when:

> The current P4-selected dataset remains the sole upstream selection authority; P5 current publication is fenced against concurrent generation changes; exact `T_selected` is completely cross-validated under the full inherited P1 split-exclusion/protected relation authority; CV validates the shared training **method** while retaining independent CV-specific folds/monitoring/budget and production-specific horizon/M3/final-run policy; every required fold and required CV seed/variant passes the configured target-only outer-validation predicate after mandatory admissibility; replay receives no ranking or acceptance-score credit; and fresh final production uses full `T_selected`, the CV-accepted shared method, its independent `[training].max_num_epochs` production horizon, authorized M3 development evidence, and collision-proof fresh execution lineage.

After stage-local closure, fresh assembled affected regression/integration, and independent review all pass, mark P5 implemented/accepted and commit the formal P5 closure checkpoint. P6 remains blocked until that closure.
