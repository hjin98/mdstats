---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-MULTI-SELECTION-AND-PER-SIZE-HORIZON
protocol_version: 5.16.0
status: implementation-ready
created_date: 2026-09-07
reviewed_date: 2026-09-07
predecessor_workplan: workplans/active/MLFF_TARGET_SIZE_PROVISIONAL_SELECTION_AUTO_DIAGNOSTIC_AND_HORIZON_STEERING_WORKPLAN.md
reviewed_implementation_branch: plan/mlff-target-size-provisional-selection-auto-diagnostic
reviewed_implementation_head: 7a38490c14999b460a634066ad8fe0d69cf673eb
reviewed_behavior_commit: fdbbea44815a79de08d77e6c58d8f45b428f114f
architecture_change: ordered-multi-target-provisional-design-and-per-size-post-selection-training
---

# MLFF target-size multi-selection and per-size horizon workplan

## Status and authority

**PASS / implementation-ready for the successor revision.**

This workplan is the reconciled successor authority after review of the submitted implementation of `MLFF_TARGET_SIZE_PROVISIONAL_SELECTION_AUTO_DIAGNOSTIC_AND_HORIZON_STEERING_WORKPLAN.md` at implementation head `7a38490c14999b460a634066ad8fe0d69cf673eb`.

The predecessor implementation is not treated as throwaway scaffolding. It has already established most of the hard authority separation needed by this successor. This plan therefore preserves completed predecessor work wherever its semantic claim survives, and changes only the scalar cardinality and downstream orchestration that conflict with the new multi-size product requirement.

The core successor change is:

> The operator-owned provisional downstream target design becomes an ordered collection of distinct per-size designs. Selecting a new `N` appends a design; selecting an already-present `N` replaces that size's complete design in place. `cross-validate` freezes the whole ordered collection atomically. CV and final production then execute the existing per-size methodology for every frozen size while reusing the one prepared generation.

All predecessor requirements not explicitly superseded remain binding, including exact `T_N = pi_train[:N]`, advisory/cached automatic screening, P2/P3 scientific identity, prepared-generation reuse, CampaignStore/CAS ownership, fresh final production, role-specific horizon identity, and existing per-size CV/production scientific methodology.

No independent executable test run was available in the review harness and no commit-status checks were exposed for the reviewed head. The predecessor implementation therefore receives strong source/test-conformance evidence but is not independently requalified here by execution. Successor Implementation must run the preserved predecessor affected tests plus the new multi-size acceptance described below.

---

# 1. Reconciliation with the submitted predecessor implementation

## 1.1 Completed and preserved

The reviewed implementation already provides the following successor foundations and they MUST be reused rather than reimplemented behind parallel machinery.

### C1 — Automatic screening is advisory, cached evidence

Implemented:

- P2/P3 screen/reducer science remains the automatic diagnostic owner;
- public/current state projects historical internal `selected_*` evidence as a recommendation;
- automatic diagnostic evidence is independent from operator selection/freeze;
- warm `--auto` reuses authenticated evidence and can perform zero new TRAIN2/EVAL2 work;
- a terminal no-recommendation diagnostic leaves the operator proposal unchanged;
- the portable diagnostic report is derived from authenticated evidence rather than a second authority.

**Successor disposition:** preserve unchanged. Multi-selection changes only how a valid `N_auto` is installed into operator selection state.

### C2 — Exact manual membership and per-invocation horizon resolution

Implemented:

- manual `N` is restricted to the qualified target-size ladder;
- membership is authenticated through the existing P2 training-order owner;
- manual selection reaches no target-size trainer/evaluator;
- CV and production horizons are resolved from existing canonical policy/config owners plus CLI overrides;
- resolved horizons are persisted as explicit values and do not drift after later config edits;
- a later selection command re-resolves omitted horizon values rather than inheriting hidden sticky CLI state.

**Successor disposition:** preserve the existing per-size value semantics. Generalize only the campaign authority from one value to an ordered collection of these values.

### C3 — One CampaignStore/CAS current authority and race protection

Implemented:

- one durable CampaignStore state chain;
- serialized/CAS transitions;
- proposal-vs-freeze serialization;
- stale long-running auto completion cannot overwrite a newer manual decision/freeze;
- no proposal-history database or mirrored target-selection authority.

**Successor disposition:** preserve the same owner and CAS model. A collection update/reset/freeze is one campaign transition; do not add per-size mutable databases or synchronized rows as competing current authority.

### C4 — Cross-validation admission is the freeze boundary

Implemented for the scalar design:

- `cross-validate` is the first freeze boundary;
- membership is re-derived/authenticated at admission;
- target identity and both effective horizons freeze before numerical CV work;
- post-freeze target-selection commands refuse mutation.

**Successor disposition:** widen the exact same admission operation from one entry to the complete ordered collection and keep the transition atomic.

### C5 — Post-selection lineage no longer depends on auto-screen ancestry

Implemented:

- P5 consumes an authenticated frozen target binding rather than P3 reducer/head selection authority;
- manual and auto origins share one downstream path;
- `PostSelectionBinding` is content-addressed per selected target and excludes manual/auto provenance from numerical identity;
- CV and production horizons are projected separately into their respective policy identities.

**Successor disposition:** retain these records and semantics per selected size. Do not replace them merely because there are now several size entries.

### C6 — Binding-keyed P5 persistence already supplies the right per-size namespace

Implemented:

- P5 immutable evidence is content-addressed;
- mutable current pointers are keyed by `PostSelectionBinding.content_digest`;
- one generation root may contain evidence from distinct bindings without a second store;
- final-production publication decisions are themselves bound to one `PostSelectionBinding`.

**Successor disposition:** reuse this as the per-size evidence namespace. The main required change is currentness: a per-size binding is current when its frozen entry is a member of the one current frozen collection, not only when it equals a scalar `state.frozen` digest.

### C7 — Predecessor legacy cutover and documentation rewrite

Implemented:

- pre-rework reducer-terminal state cannot masquerade as the new operator freeze;
- valid old automatic-screen evidence can remain diagnostic evidence;
- current documentation/specification/help was substantially rewritten for advisory auto/manual scalar selection.

**Successor disposition:** preserve the old-v1 cutover semantics, then reconcile the newly introduced predecessor-v2 scalar current representation into the collection representation described in this workplan.

## 1.2 Superseded by the new design; not predecessor bugs

The following implementation is correct for the predecessor but no longer satisfies the new product requirement:

1. `TargetSizeCampaignState.proposal` as one scalar current proposal.
2. `TargetSizeCampaignState.frozen` as one scalar frozen design.
3. `commit_target_size_proposal()` replacement semantics for every distinct N.
4. `resolve_frozen_target_selection()` admitting exactly one N.
5. `CurrentSelectedTrainingContext` / `PostSelectionContext` exposing exactly one current size per command invocation.
6. `execute_current_cross_validate()` and `execute_current_train_production()` executing one selected size.
7. publication currentness that requires the current scalar frozen digest to equal one binding's frozen-selection digest.
8. status/lifecycle wording and stage aggregation that assume one selected target.
9. predecessor CLI names `--select-horizon-cv` and `--select-horizon`.
10. the public qualification path assuming one current final-production publication.

Do not preserve these scalar assumptions with wrappers that create a second collection authority. Reuse the good scalar **value objects** as collection entries when that is simpler; remove only their scalar authority role.

## 1.3 Remaining successor work

The following capabilities are genuinely missing and constitute the implementation scope of this plan:

- ordered unique-by-N provisional collection;
- duplicate-N in-place replacement;
- pre-freeze `--reset`;
- canonical `--horizon-cv` / `--horizon` CLI names;
- atomic freeze of all selected entries;
- per-size currentness against one frozen collection;
- CV orchestration across size x existing CV seeds/folds;
- production orchestration across size x existing production seeds;
- collection-aware stage completion, restart, status, results, and retention/currentness;
- predecessor-v2 scalar current-state projection/migration;
- explicit multi-size qualification boundary described in Section 7;
- affected regression/integration over all of the above.

---

# 2. Objective / problem invariants / non-goals

## 2.1 Product problem

The prepared target-size generation is expensive and intentionally reusable. The operator may want to run the established downstream training methodology at several qualified sizes from the same ladder to compare longer-horizon behavior without re-running `prepare` or allowing the latest `select-target-size` command to erase an earlier requested experiment.

The requested frozen downstream design is therefore:

```text
D = [
  (N_1, H_cv_1, H_prod_1),
  (N_2, H_cv_2, H_prod_2),
  ...,
  (N_k, H_cv_k, H_prod_k),
]

k >= 1 at cross-validation admission
```

where all `N_i` are distinct configured qualified target sizes and every tuple snapshots its own effective role horizons.

The target-size dimension is another post-selection experiment dimension over the same prepared generation. It is not another campaign, another target-size diagnostic, or another prepared dataset.

## 2.2 Product invariants

### P1 — Ordered unique-by-size selection

The provisional design contains at most one entry for each `N` and preserves first-insertion order for distinct sizes.

For a newly resolved size `N_new`:

- if `N_new` is absent, append its complete entry;
- if `N_new` is already present, replace that complete entry in place and preserve its position.

Example:

```text
select-target-size 512
select-target-size 1024 --horizon-cv 40 --horizon 100

=> [(512, HC_default_at_first_call, H_default_at_first_call),
    (1024, 40, 100)]

select-target-size 512 --horizon-cv 60 --horizon 200

=> [(512, 60, 200),
    (1024, 40, 100)]
```

Duplicate N entries are invalid authoritative state.

### P2 — Horizons are per selected size

Each successful manual or auto installation resolves one complete `(N, H_cv, H_prod)` entry from the current canonical config/default values plus the explicit options on that invocation.

Existing untouched entries never drift when config/defaults later change. Reselecting the same N deliberately creates a new complete entry and therefore re-resolves every omitted horizon for that new invocation.

### P3 — Unselected initialization is absence, not a fake record

Immediately after `prepare` or `--reset`, the user-visible state is logically equivalent to:

```text
N = undefined
H_cv = current/default H_cv
H_prod = current/default H_prod
```

but there is no requirement to persist a fake `N=undefined` tuple. An empty provisional collection is the simpler authoritative representation.

`cross-validate` MUST refuse with zero concrete selected sizes.

### P4 — Reset clears only provisional operator selection

```bash
select-target-size --reset
```

before freeze:

- atomically clears all provisional entries;
- leaves the prepared generation intact;
- leaves independently valid cached automatic-diagnostic evidence/report intact;
- performs no target-size/CV/production numerical work.

Reset never thaws a frozen experiment.

### P5 — Auto recommendation uses the same merge owner

`select-target-size --auto` retains the predecessor diagnostic behavior. Once a valid `N_auto` is resolved, it is installed by the same unique-by-N merge semantics as manual selection.

Thus:

```text
[N1] + auto -> N2 != N1  => [N1, N2]
[N1] + auto -> N1        => [N1(updated in place)]
```

A no-recommendation diagnostic changes no provisional collection field. Warm auto remains zero-new-screen-work.

### P6 — Exact membership remains unchanged

For every selected size:

```text
T_N = pi_train[:N]
```

using the one authenticated P2 training order. No arbitrary target membership, resampling, non-ladder size, or independently mutable `T_N` list is introduced.

### P7 — Freeze is atomic over the complete ordered design

At `cross-validate` admission, every provisional entry is revalidated against the same current prepared generation and the complete ordered collection is frozen in one CampaignStore/CAS transition before numerical CV work starts.

After freeze, order, selected N values, exact membership identities, per-size horizons, and selection provenance are immutable for that campaign generation.

### P8 — CV and production gain a size dimension

For every frozen selected size, execute the existing post-selection methodology with that size's exact target data and role horizon.

Conceptually:

```text
for entry in frozen_selection_order:
    CV(entry.N, entry.H_cv, existing seeds/folds)

for entry in frozen_selection_order:
    final_production(entry.N, entry.H_prod, existing production seeds)
```

Existing CV fold construction, acceptance predicates, production seed/committee policy, optimizer semantics, and fresh-start production remain unchanged per size.

### P9 — No requested size may disappear silently

Campaign-level CV completion means required current CV is complete/accepted for every frozen selected size under the existing per-size predicate.

Campaign-level production completion means required current production/publication is complete for every frozen selected size.

Failure, missing evidence, or stale evidence for one size must be attributed to that N and must not mutate the frozen design or silently shrink it. Valid completed siblings remain reusable on retry when their identity/currentness remains valid.

### P10 — Per-size scientific identity is independent of siblings/order

The frozen collection/order is orchestration authority. It MUST NOT contaminate the numerical scientific identity of an otherwise identical per-size target/CV/production experiment.

For size `N_i`:

```text
TargetBinding_i
  depends on prepared/training-order identity + N_i + exact T_i

CV policy_i
  depends on TargetBinding_i + H_cv_i + existing CV policy fields
  does not depend on H_prod_i or sibling sizes/order

Production policy_i
  depends on TargetBinding_i + accepted method/CV ancestry + H_prod_i
  does not depend on sibling sizes/order
```

Manual/auto provenance remains provenance rather than numerical identity.

### P11 — Prepared data are shared

Adding selected sizes MUST NOT invoke `prepare` again, clone prepared-generation data, or create per-size campaign copies. All selected sizes share the same authenticated prepared generation/training order and derive only their existing exact prefixes/materializations.

## 2.3 Explicit non-goals

This revision does NOT:

- redesign automatic successive halving or target-size ranking;
- change P1/P2/P3 scientific identities or metrics;
- add arbitrary non-ladder target sizes;
- introduce automatic horizon optimization;
- add new per-size hyperparameters beyond the two horizons;
- change CV methodology/acceptance;
- change production seed/committee policy;
- allow screen or CV checkpoints to parent final production;
- create per-size subcampaigns or a generic experiment framework;
- create a second target-selection authority/database;
- select a cross-size winner after production;
- use qualification/locked evidence to choose among target sizes;
- run production-scale/GPU qualification during implementation.

---

# 3. Frozen high-level architecture

## 3.1 Authority graph

```text
one authenticated prepared target-size generation
                  |
          +-------+----------------+
          |                        |
          v                        v
optional cached auto         ordered provisional design
P2/P3 diagnostic             CampaignStore current authority
          |                        |
          | N_auto                 | [entry_1, ..., entry_k]
          +----------------------> | unique by N
                                   |
                                   | cross-validate admission
                                   v
                          ordered frozen design
                          [frozen_1, ..., frozen_k]
                                   |
                    +--------------+--------------+
                    |                             |
                    v                             v
          existing P5 CV per entry      existing final production
          x existing folds/seeds        per entry x prod seeds
                    |                             |
                    +--------------+--------------+
                                   v
                      per-size production publications

qualification:
  k == 1 -> existing qualification architecture unchanged
  k > 1  -> fail closed; no implicit multi-product qualification/release selection
```

## 3.2 One collection authority; reuse scalar records as elements where simpler

The existing predecessor `TargetSizeProposal` and `FrozenTargetSelection` semantics are already appropriate for one size. Implementation SHOULD prefer reusing or minimally adapting those records as per-size collection elements if doing so preserves clean ownership and schema compatibility.

What must disappear is their role as the one scalar campaign authority, not necessarily the record types themselves.

Acceptable shape conceptually:

```text
Campaign target-size state
  provisional_entries: ordered tuple[TargetSizeProposal]
  frozen_entries: optional ordered tuple[FrozenTargetSelection]
```

Exact names/layout are delegated.

Forbidden:

- authoritative scalar proposal plus separately authoritative collection kept in sync;
- authoritative scalar frozen selection plus separately authoritative frozen list;
- one mutable row/file/database per size requiring reconciliation;
- result/report files used as selection authority.

## 3.3 Reuse per-size PostSelectionBinding and evidence namespaces

The reviewed `PostSelectionBinding` is already one-size scientific lineage and its pointer namespace is keyed by binding digest. Preserve that model where possible.

The important currentness change is conceptual:

```text
old scalar currentness:
  current_state.frozen.digest == binding.frozen_selection_digest

new collection currentness:
  binding's frozen-entry digest is an authenticated member
  of the one current frozen collection for the same generation
```

Do NOT add the whole frozen-collection digest into the per-size scientific `PostSelectionBinding` merely to perform currentness checks; doing so would invalidate otherwise identical N-specific evidence when an unrelated sibling size/order changes.

The collection digest may exist as campaign orchestration/currentness state, but per-size records should remain bound to the per-size entry and established scientific authorities.

## 3.4 P5 store and publication reuse

The current P5 evidence store can hold immutable objects for several bindings under one generation, and current pointers are already binding-keyed. Prefer adapting existing currentness membership checks and orchestration rather than creating another per-size persistence subsystem.

`FinalProductionPublicationDecision` remains one per-size binding. Multi-size `train-production` produces one such publication for every frozen selected size; it does not manufacture a new cross-size committee/publication that chooses among sizes.

## 3.5 Deterministic ordering versus execution scheduling

Frozen selection order is deterministic user-visible orchestration order and result ordering.

Implementation may use existing bounded scheduling where it clearly preserves resource ownership, restart, and deterministic identity. It need not introduce new parallelism. A simple outer iteration over the bounded size list is acceptable and preferred over a new scheduler unless existing orchestration already supplies an equally simple safe mechanism.

## 3.6 No enum/state explosion

Target size is a bounded data dimension, not a reason to create lifecycle states for every size x fold x seed combination. Existing immutable per-size evidence and binding-keyed pointers remain the progress/restart truth; campaign-level stage state is a derived/aggregate operational view.

---

# 4. Public CLI and provisional-state contract

## 4.1 Manual selection

```bash
select-target-size <N> [--horizon-cv HC] [--horizon H]
```

Required path:

1. establish current prepared generation;
2. authenticate N through the existing qualified-candidate/training-order owner;
3. resolve complete per-invocation horizons through the existing horizon resolver;
4. build one complete per-size entry;
5. merge it atomically into the current ordered collection;
6. render the complete resulting plan;
7. perform zero target-size TRAIN2/EVAL2 work.

## 4.2 Automatic selection

```bash
select-target-size --auto [--horizon-cv HC] [--horizon H]
```

Retain cold/warm diagnostic execution exactly as currently implemented. After obtaining a valid recommendation, build one ordinary per-size entry and route it through the same merge owner as manual selection.

Long-running auto concurrency remains predecessor-style optimistic/CAS installation: diagnostic evidence/report may complete even when installation loses to a newer collection revision or freeze.

## 4.3 Reset

```bash
select-target-size --reset
```

- pre-freeze only;
- clears the full provisional collection in one transition;
- preserves prepared generation and valid auto diagnostic evidence;
- zero numerical work;
- mutually exclusive with N, `--auto`, `--horizon-cv`, and `--horizon`.

An already-empty reset may be idempotent and avoid a meaningless revision.

## 4.4 Bare command and mutual exclusion

Bare `select-target-size` remains invalid and actionable.

Exactly one of positional N, `--auto`, or `--reset` is the operation selector.

## 4.5 Horizon flag rename

Canonical flags are now:

```text
--horizon-cv
--horizon
```

The predecessor implementation currently exposes:

```text
--select-horizon-cv
--select-horizon
```

This feature has just been submitted on the predecessor development branch and no governed released compatibility requirement was found during review. Therefore the successor should **rename/remove** the predecessor provisional spellings rather than accumulate aliases/wrappers.

If implementation discovers an actual released/external governed compatibility requirement, reopen only this CLI compatibility decision.

## 4.6 Per-size omission/default semantics

For every manual or successful auto-install invocation:

```text
H_cv   = explicit --horizon-cv
         else current [post_selection.cv].max_num_epochs/default

H_prod = explicit --horizon
         else current [training].max_num_epochs/default
```

The resulting effective values are persisted in the affected entry. Existing untouched entries retain their snapshot.

The CLI does not rewrite `campaign.toml`.

---

# 5. Provisional/frozen state, schema, and compatibility

## 5.1 Empty/provisional/frozen states

Current state must cleanly represent:

```text
prepared generation + empty provisional collection
prepared generation + ordered nonempty provisional collection
prepared generation + ordered nonempty frozen collection
```

No separate authoritative list/count/map is required when one canonical ordered representation can derive those views.

## 5.2 Collection validation

On construction/deserialization and before consequential freeze, enforce:

- deterministic order;
- no duplicate N;
- every N positive and qualified when checked against live prepared authority;
- every entry's membership/training-order digest authenticates;
- every horizon positive;
- no mixed prepared/training-order lineage inside one current collection.

Do not silently deduplicate corrupt authoritative state. Duplicate-N persisted state is corruption, not an invitation to guess which entry wins.

## 5.3 Predecessor-v2 scalar state

The submitted implementation introduced a valid scalar proposal/freeze schema. Its semantic projection is lossless:

```text
proposal is None                 -> provisional_entries = []
proposal = P                     -> provisional_entries = [P]
frozen = F                       -> frozen_entries = [F]
```

Prefer a READ/NORMALIZE/MIGRATE realization that makes this a bounded compatibility boundary and then exposes only the canonical collection to current decision logic.

A predecessor scalar proposal may become one provisional entry and then accept additional selections under this successor.

A predecessor scalar frozen selection is already frozen. It may be treated as a one-entry frozen collection for continuation/currentness, but MUST NOT become appendable or be thawed.

Because the existing per-size `PostSelectionBinding` refers to the scalar frozen-entry digest, preserving that entry digest during one-entry projection can preserve valid existing P5 descendants without rebinding them to a fabricated new scientific identity. Do not rewrite descendant ancestry merely to make the collection wrapper look uniform.

## 5.4 Old pre-predecessor state remains subject to the predecessor cutover

The predecessor's older-v1 rule remains binding: an old reducer-terminal automatic selection is diagnostic evidence, not operator-approved freeze authority. This successor must not accidentally promote it while normalizing the newer scalar schema.

---

# 6. Atomic collection freeze and per-size P5 execution

## 6.1 Cross-validation admission

`cross-validate` is still the only freeze authority.

Admission MUST, before numerical CV work:

1. load current CampaignStore state under existing writer/currentness discipline;
2. require at least one provisional entry;
3. load/authenticate the current prepared generation once;
4. revalidate every selected N against the current qualified set;
5. re-derive every exact `pi_train[:N]` membership digest;
6. authenticate every entry against the one current training order;
7. construct the complete ordered frozen collection from the persisted resolved entries;
8. CAS-publish that frozen collection atomically and remove/retire provisional authority in the same logical transition.

There must be no state where CV for one N is current while the campaign freeze omits another N that was part of the admitted design.

## 6.2 Per-size current context

After freeze, expose a collection-level read that yields ordered authenticated per-size contexts. Each element should reuse the existing per-size selected-training/binding semantics.

Do not require callers to rebuild a size loop from raw state independently. The production orchestration owner must own enumeration so a missing size cannot be hidden by a test harness or consumer.

## 6.3 Cross-validation execution

For every frozen entry in deterministic selection order:

- use its exact `T_N`;
- use its frozen `H_cv`;
- construct/resolve the existing real P5 CV plan under that size's `PostSelectionBinding`;
- execute the existing seeds/folds and acceptance rules;
- publish/reuse binding-keyed evidence through the existing P5 store/currentness owners.

Campaign CV is complete only when every selected binding has current accepted CV evidence.

## 6.4 Final production execution

`train-production` enumerates the same frozen entries and requires the existing accepted CV ancestry for each entry.

For every entry:

- use its frozen `H_prod`;
- preserve fresh-start production;
- preserve existing production seed/committee policy;
- produce the existing binding-scoped final plan/completion/publication decision;
- never use another size's membership, horizon, CV acceptance, or publication.

Campaign production is complete only when every selected binding has its required current final publication.

## 6.5 Restart and failure isolation

If one size fails or is interrupted after another size completed:

- the frozen collection remains unchanged;
- already-valid sibling plans/evidence/publications remain available and reusable;
- retry resumes/recomputes only work that existing per-size identity/restart rules deem incomplete/stale;
- no live config edit can change frozen horizons;
- campaign-level stage state remains incomplete/failed as appropriate until all required sizes close.

## 6.6 Publication currentness fence

Adapt the existing commit-time publication fence so a per-size binding may publish as current only when:

- campaign generation is still current; and
- the binding's frozen target entry is still an authenticated member of the current frozen collection.

Do not compare a per-size binding against the whole collection digest as its scientific ancestry. Do not allow mere equality of N to substitute for the exact frozen-entry/binding identity.

---

# 7. Qualification boundary — preserve one-product locked semantics

Review of the submitted implementation shows that P7 qualification is defined for **one exact final-production publication**, and locked activation is intentionally one-shot for that exact product. Multi-size production creates several predeclared production publications, but this workplan does not contain a scientifically justified rule for selecting one of them or for treating one locked cohort as a multi-product comparison experiment.

Therefore the Frozen rule for this revision is:

### 7.1 Single selected size

For `k == 1`, existing qualification behavior and identity remain unchanged. The successor must preserve the current qualification regression surface.

### 7.2 Multiple selected sizes

For `k > 1`, qualification commands MUST fail closed before opening/running qualification evidence and clearly report that the frozen campaign contains multiple production publications and this revision does not authorize cross-size release selection or multi-product locked qualification.

Specifically, do NOT:

- silently choose the first/last/auto-recommended size for qualification;
- choose the size with the best CV/production metric after the collection is frozen;
- run the one-shot locked test across several sizes and use the outcomes to select a winner;
- merge different sizes' production seeds into one committee;
- mutate the frozen collection down to one size.

A future feature may design explicit multi-product qualification or an independent pre-locked release-selection rule, but that is outside this narrow revision.

`train-production` still completes all requested sizes and exposes all per-size publications/results. Multi-size production is therefore useful as the requested training experiment even though P7 release qualification remains intentionally unavailable for `k > 1` in this cycle.

---

# 8. Lifecycle, status, results, and observability

## 8.1 Selection/status rendering

Every successful manual selection, auto installation, reset, and `status` must render the complete current design, not only the entry touched by the command.

Before freeze, show at minimum:

```text
Target-size training plan: provisional
Frozen: no
Selected sizes: K
[1] N=... H_cv=... H_prod=... source=...
[2] N=... H_cv=... H_prod=... source=...
...
```

When empty, explicitly show:

- no concrete selected sizes;
- current effective H_cv/H_prod defaults that a future omitted-horizon command would resolve;
- that at least one size is required before `cross-validate`.

After freeze, show the complete ordered frozen list and per-size CV/production state.

Auto diagnostic availability/recommendation remains separately visible and must not obscure operator-selected sibling entries.

## 8.2 `advance`

`advance` never invents N and never silently opts into auto.

- zero provisional selections -> stop at target-size decision boundary;
- one or more provisional selections -> next consequential stage is `cross-validate`;
- frozen collection with incomplete CV -> CV remains current next work;
- all CV accepted but incomplete production -> `train-production`;
- all production complete and k==1 -> existing qualification next step;
- all production complete and k>1 -> report production complete and qualification unavailable under this revision, rather than choosing a size.

## 8.3 Campaign stage summaries

Existing campaign stage rows are operational summaries, not the authority for per-size completion. Derive aggregate status from real binding-scoped P5 evidence. Do not add a second mutable per-size stage database when binding-keyed immutable evidence/pointers already supply currentness.

---

# 9. Storage, retention, and documentation

## 9.1 Storage/retention

Prepared-generation data remain one shared authority.

P5 evidence remains binding-keyed under the existing generation root. Update retention/currentness traversal only where scalar assumptions would otherwise omit evidence for sibling selected bindings.

No cleanup path may treat one selected size's current P5 evidence as unreachable merely because another selected binding is being inspected.

Do not duplicate prepared arrays/materialization authorities per size beyond the existing per-run artifacts required by the actual P5 training methodology.

## 9.2 Current documentation/specification

Reconcile current normative/user-facing sources, including at minimum the predecessor-touched target-size architecture/manual/spec/CLI help and relevant post-selection/qualification documentation.

Current docs must consistently describe:

- ordered multi-size selection;
- duplicate-N replacement in place;
- reset;
- canonical `--horizon-cv` / `--horizon` names;
- per-size horizon snapshots;
- whole-collection freeze at `cross-validate`;
- CV and production size dimension;
- per-size production publications;
- single-size-only qualification in this revision;
- no automatic cross-size winner.

Remove current-semantic wording that says a second distinct selection simply replaces the first or that only one selected target can exist. Historical/archive material may remain historical.

Regenerate tracked derived manuals/PDFs from their authoritative sources according to repository policy.

---

# 10. Implementation obligations

## O1 — Generalize campaign selection authority from scalar to ordered collection

Use zero-or-more provisional per-size entries, stable first-insertion order, unique by N, and duplicate-N replacement in place. Reuse the existing per-size proposal record semantics where practical. No synchronized scalar + list authority.

## O2 — Preserve canonical per-size horizon resolution

Reuse the predecessor resolver/config owners; snapshot complete values into the affected entry. Untouched entries do not drift.

## O3 — Rename horizon CLI flags and add reset

Canonicalize to `--horizon-cv`/`--horizon`, remove predecessor provisional spellings absent a real compatibility obligation, and implement mutually exclusive pre-freeze `--reset`.

## O4 — Route auto through the same collection merge owner

Preserve cold/warm/no-recommendation/report behavior. Recommendation installation differs from manual selection only in source/provenance.

## O5 — Freeze the entire collection atomically

Revalidate every entry against the one current prepared generation and commit one frozen ordered design before any CV work.

## O6 — Reuse per-size P5 binding/evidence machinery

Keep `PostSelectionBinding`, binding-keyed pointers, content-addressed store, and per-size publication semantics wherever their existing contracts remain sufficient. Alter scalar currentness checks to collection-membership currentness rather than creating another storage system.

## O7 — Make real CV orchestration enumerate every frozen binding

The assembled production `cross-validate` owner—not a test harness—must create/resolve and execute every per-size CV plan with the correct membership/H_cv and existing subordinate fold/seed dimensions.

## O8 — Make real production orchestration enumerate every frozen binding

The assembled `train-production` owner must require current accepted CV for and execute every size with correct H_prod/fresh-start/seed policy, publishing one current binding-scoped production decision per size.

## O9 — Preserve restart and completed siblings

Failure/interruption of one selected size must not erase/recompute unrelated valid siblings or mutate the frozen design.

## O10 — Reconcile P5 publication currentness and retention

Currentness/retention must recognize every frozen per-size binding in the current collection. Exact entry identity, not N equality, controls adoption.

## O11 — Make lifecycle/status/results collection-aware

Render all selected sizes and derive campaign-level completion from all required binding-scoped evidence.

## O12 — Preserve predecessor-v2 scalar state without dual authority

Normalize compatible scalar proposal/freeze to a one-entry collection boundary; keep old-v1 reducer-terminal state subject to predecessor diagnostic-only cutover.

## O13 — Preserve qualification for k==1 and fail closed for k>1

Do not invent cross-size release selection or multi-product locked-test semantics.

## O14 — Close current documentation and obsolete scalar assumptions

Current source/help/docs/specs expose one coherent final multi-size behavior; generated docs are rebuilt from source.

---

# 11. Implementation authority

## 11.1 Frozen

1. Provisional selection is an ordered collection of distinct qualified N values.
2. New N appends; existing N replaces its complete entry in place.
3. Each entry owns independently resolved persisted H_cv/H_prod values.
4. Empty collection is the canonical unselected state; at least one concrete size is required for CV admission.
5. `--reset` clears provisional entries only and is forbidden after freeze.
6. `--auto` preserves existing diagnostic science/cache and merges its recommendation through the same collection owner.
7. Auto no-recommendation changes no collection state.
8. Manual selection performs zero target-size TRAIN2/EVAL2 work.
9. Exact membership remains `pi_train[:N]` from the one P2 training order.
10. Cross-validation admission freezes the complete ordered collection atomically.
11. Selection is immutable after freeze.
12. CV executes the existing methodology for every frozen size using that entry's H_cv.
13. Production executes the existing fresh-start methodology for every frozen size using that entry's H_prod.
14. All selected sizes must be accounted for; no failure silently removes a size.
15. Valid completed sibling work remains reusable under existing identity/currentness rules.
16. Per-size target/CV/production numerical identity does not depend on sibling sizes/list position/provenance.
17. One prepared generation is shared by all selected sizes.
18. One CampaignStore remains the mutable current authority.
19. Existing per-size P5 binding/evidence ownership should be preserved where semantically sufficient; no new per-size subcampaign/state database.
20. Canonical flags are `--horizon-cv` and `--horizon`; predecessor provisional spellings are not retained absent governed compatibility evidence.
21. Existing automatic-screen science/identity/report remains unchanged.
22. Existing CV/production scientific methodology remains unchanged per size.
23. `k==1` qualification remains unchanged.
24. `k>1` qualification fails closed and cannot choose/compare/reduce target sizes using qualification/locked evidence.
25. Full production/GPU qualification remains deferred during implementation.

## 11.2 Delegated

Implementation may choose/simplify:

- exact collection/dataclass/schema field names;
- whether existing scalar value objects are reused directly or minimally renamed as per-size entries;
- collection serialization shape;
- transition-kind names/wire evolution consistent with compatibility rules;
- exact collection-level digest representation;
- exact iterator/helper/module boundaries;
- whether size execution is serial or uses already-supported bounded scheduling;
- exact per-size result formatting/paths under existing binding ownership;
- test organization.

Prefer direct alteration of current scalar authority/currentness/orchestration over additive wrappers. A linear search through the bounded selected-size collection is sufficient; do not add registries/index services for this scale.

## 11.3 Reopen only on evidence

Reopen only the affected design surface if evidence demonstrates:

- exact per-size P5 identity cannot remain independent while safely proving membership in one current frozen collection;
- existing P5 binding-keyed store cannot represent multiple current size descendants without materially different persistence ownership;
- atomic collection freeze cannot be achieved under existing CampaignStore/CAS ownership;
- a governed released compatibility contract requires predecessor horizon-option aliases;
- multi-size qualification is independently required now and cannot preserve the current one-product/locked-evidence scientific contract without a separate explicit design.

Ordinary code-shape difficulty is not a redesign trigger.

---

# 12. Expected affected surface

Start with the implementation-proven owners rather than rediscovering the subsystem from scratch:

```text
mdstats/training_data/campaign_target_size_state.py
mdstats/training_data/campaign_target_size_selection.py
mdstats/training_data/campaign_target_size_runtime.py
mdstats/training_data/campaign_target_size_view.py
mdstats/training_data/campaign_lifecycle.py
mdstats/training_data/_campaign_cli_core.py

mdstats/training_data/campaign_post_selection.py
mdstats/training_data/campaign_post_selection_runtime.py
mdstats/training_data/post_selection_store.py
mdstats/training_data/post_selection_identity.py
mdstats/training_data/post_selection_cv_plan.py
mdstats/training_data/post_selection_cv_acceptance.py
mdstats/training_data/post_selection_production.py
mdstats/training_data/post_selection_publication.py

mdstats/training_data/campaign_target_size_retention.py
mdstats/training_data/storage/owners.py

mdstats/training_data/qualification/commands.py
mdstats/training_data/qualification/runtime.py
mdstats/training_data/qualification/binding.py
```

Also inspect every current consumer that assumes `state.proposal`, `state.frozen`, `load_current_selected_training_context()`, one `PostSelectionContext`, one current CV/final pointer, or one current final publication.

Documentation includes the predecessor-touched README, target-size architecture/manual/specification, CLI user guide, campaign CLI spec, embedded help/guide text, and generated tracked manuals.

Final affected surface must be re-derived from the assembled candidate.

---

# 13. Task-specific acceptance matrix

Generic focused checks, stage-local affected regression, final affected-surface regression, real-owner integration, and repository-required checks are inherited from Protocol 5.16.0.

## 13.1 Preserve predecessor foundations

Before/through the refactor, retain executable evidence for:

- exact manual membership via P2 and zero manual screen numerical work;
- cold/warm auto diagnostic and no-new-work warm path;
- no-recommendation atomic non-mutation;
- diagnostic-report fidelity/rebuildability;
- per-invocation horizon resolution/no config drift;
- stale-auto/CAS protection;
- old-v1 reducer-terminal state remaining diagnostic-only;
- manual/auto provenance excluded from numerical P5 identity.

Existing predecessor tests may be adapted for collection cardinality but must not be weakened merely because scalar assertions changed.

## 13.2 CLI grammar

Prove valid manual/auto forms with zero/one/both canonical horizon flags; reset exclusivity; bare invalid command; nonpositive horizons; invalid/noncandidate N; post-freeze mutation rejection; and absence/rejection of old `--select-horizon*` names unless Design is reopened for real compatibility evidence.

## 13.3 Ordered merge and reload

Through the real CampaignStore selection owner prove representative sequences:

```text
512                    -> [512]
1024                   -> [512, 1024]
512(new horizons)      -> [512(updated), 1024]
2048                   -> [512(updated), 1024, 2048]
1024(new horizons)     -> [512(updated), 1024(updated), 2048]
```

Verify exact order, one entry per N, complete horizons/provenance/membership identity, durable reload equivalence, and duplicate/corrupt serialized state rejection.

A broad stateful/property test is appropriate if Hypothesis is available, using real test-owned CampaignStore state and an independent simple ordered-map oracle.

## 13.4 Reset

From a multi-entry collection with cached auto evidence:

- reset -> empty collection;
- prepared generation unchanged;
- diagnostic evidence unchanged;
- zero numerical calls;
- status shows unselected/default state;
- CV refuses zero entries;
- later warm auto reuses cached evidence and installs exactly one entry without retraining.

## 13.5 Per-size horizon snapshots

Change config defaults between selection/reselection commands. Prove only the affected entry receives newly resolved omitted values, untouched entries retain their snapshots, and all values remain unchanged across reload/freeze and later config edits.

## 13.6 Auto merge

Cover:

- manual N1 -> auto N2 => `[N1, N2]`;
- manual N1 -> auto N1 => N1 replaced in place;
- auto N1 -> manual N2 => `[N1, N2]`;
- no-recommendation => collection unchanged;
- stale auto completion loses to newer append/update/reset/freeze while retaining valid diagnostic evidence.

## 13.7 Atomic multi-size freeze

Assembled public path:

```text
prepare
select-target-size N1 ...
select-target-size N2 ...
cross-validate
```

must prove one atomic ordered frozen collection, exact re-authentication of both memberships, frozen per-size horizons, no P3-auto ancestry requirement, and post-freeze rejection of N/auto/reset mutation.

Inject a corrupt member below persistence boundaries and prove the entire admission fails without partial freeze/CV execution.

## 13.8 Per-size binding identity/currentness

For each frozen entry prove the real selected-training adapter yields the correct existing-style `PostSelectionBinding`/membership. Prove:

- N1 binding is different from N2 binding;
- adding/reordering a sibling in an otherwise equivalent fresh design does not alter N1's numerical per-size binding/policy identity beyond truly governed campaign-generation identity;
- publication currentness accepts a binding whose exact frozen entry belongs to the current collection;
- an entry from another generation, altered horizons where relevant, forged membership, or N-only lookalike is rejected;
- whole-collection digest/order is not injected into per-size numerical identity.

## 13.9 Real CV owner across size x existing dimensions

Use bounded numerical doubles below the real P5 owner and call the assembled public `cross-validate`. Verify every frozen size is enumerated by production orchestration and receives:

- correct exact T_N;
- correct H_cv;
- real CV plan/binding;
- existing required seeds/folds and acceptance semantics.

A harness-side loop that directly calls one-size helpers cannot close this claim.

## 13.10 Real production owner across size x existing seeds

Through assembled `train-production`, verify every selected size with accepted current CV gets its own real final plan/run evidence/publication under correct binding/H_prod/fresh-start semantics.

Assert N1 cannot consume N2's CV acceptance, membership, horizons, pointers, run evidence, or publication.

## 13.11 Failure/restart sibling preservation

Deterministically fail/interrupt one size after another completes. On retry/reload prove:

- frozen collection unchanged;
- completed sibling evidence is reused when still current;
- failed/incomplete size resumes according to existing owner semantics;
- campaign stage remains non-complete until every required size closes;
- no selected entry is dropped.

## 13.12 Concurrency/CAS

Use the real CampaignStore writer/CAS owner for deterministic races including:

- append N2 vs update N1;
- append/update vs reset;
- reset vs CV freeze;
- selection vs CV freeze;
- long-running auto installation vs append/update/reset/freeze.

Exactly one transition order becomes authoritative. No lost entry, duplicate N, partial collection, or split freeze/CV ancestry is allowed.

## 13.13 P5 store, retention, and cleanup

Create current P5 evidence for at least two selected bindings. Prove binding-keyed pointers coexist, currentness resolves both, storage/retention traversal protects both where required, and cleanup of stale/historical data cannot delete one current sibling because another binding was used for reachability analysis.

## 13.14 Lifecycle/status/results

Assert the complete ordered provisional/frozen list is visible, per-size CV/production progress/failure is attributable by N, campaign completion requires all selected sizes, `advance` never invents N, and singular legacy wording cannot hide additional entries.

## 13.15 Predecessor-v2 scalar compatibility

Representative predecessor scalar states:

- no proposal/freeze -> empty collection;
- valid proposal -> one provisional entry with identical N/membership/horizons/provenance;
- valid frozen scalar -> one frozen entry, immutable/non-appendable, with existing bound P5 descendant still current when its exact identity remains valid.

Retain the older-v1 diagnostic-only cutover test separately so the two compatibility generations cannot be conflated.

## 13.16 Qualification boundary

Prove:

- one selected size reaches the existing qualification owner unchanged after production;
- more than one selected size causes `qualification run`, locked activation, and any other consequential qualification entrypoint to fail **before** creating/opening a qualification attempt or locked evidence;
- status/help explains the multi-size limitation without choosing a size;
- no first/last/best/auto-recommended implicit product selection exists.

## 13.17 No-obsolete-current-semantics closure

Inspect current executable/normative surfaces for obsolete assumptions including:

- campaign current selection is always scalar;
- second distinct N replaces first;
- only one current frozen size may exist;
- publication currentness requires equality with a scalar state.frozen digest;
- status/results print only one selected size;
- production chooses one size from the collection;
- old `--select-horizon*` flags remain current;
- multi-size qualification silently selects a publication.

Use AST/structural tooling when available and appropriate; validate any acceptance-critical custom structural rule against known-positive/known-negative examples. Literal docs/help may use bounded text search. Historical/archive documents are excluded from current-semantic absence claims.

## 13.18 Final regression and integration

After all material executable edits:

1. reconcile every obligation above against the assembled candidate;
2. re-derive the actual affected surface;
3. run the adapted predecessor target-size provisional-selection suite;
4. run all affected target-size state/runtime/view/lifecycle tests;
5. run all affected P5 CV/production/restart/currentness/publication/store/storage tests;
6. run single-size qualification regression plus multi-size fail-closed qualification tests;
7. run assembled `prepare -> multi-select -> cross-validate -> train-production -> reload/status` integration through real owners with bounded numerical doubles;
8. run repository/project-required static/lint/type checks and the broader suite if impact cannot be confidently bounded.

A required check that cannot execute remains incomplete evidence; do not convert it to a pass by inspection.

Production-scale/GPU qualification is not required for implementation acceptance.

---

# 14. Implementation sequence and simplification/redesign triggers

## Stage A — Collection authority, CLI, and compatibility

Generalize scalar proposal authority to the ordered collection, preserve/reuse the existing per-size value object, implement duplicate replacement/reset/flag rename/rendering, and normalize predecessor-v2 scalar state. Close focused + affected state/CLI/CAS regression before dependent P5 changes.

## Stage B — Atomic freeze and per-size currentness

Generalize freeze to the whole collection; expose ordered per-size selected contexts; adapt `PostSelectionBinding` currentness membership and binding-keyed pointer publication without contaminating scientific identity. Close freeze/currentness/store/legacy regression.

## Stage C — Multi-size CV and production orchestration

Make the real public CV and production owners enumerate every frozen entry, aggregate completion correctly, preserve restart/completed siblings, and keep existing per-size numerical owners unchanged. Close stage-local P5 affected regression and assembled bounded integration.

## Stage D — Lifecycle/storage/qualification/documentation closure

Make status/advance/results/retention collection-aware, preserve single-size qualification and fail closed for multi-size qualification, reconcile current docs/spec/help, regenerate derived manuals, then run final affected regression/integration/project checks.

## Active simplicity trigger

If implementation begins adding adapters solely to keep a scalar authoritative proposal/freeze synchronized with a collection, stop and remove/generalize the scalar authority instead. If it begins creating per-size subcampaigns/stores/lifecycle enums despite existing binding-keyed P5 ownership, stop and reuse the existing per-binding architecture.

Reuse of the current `TargetSizeProposal`, `FrozenTargetSelection`, `PostSelectionBinding`, P5 object store, and publication record as **per-size values** is encouraged when it reduces migration and identity churn; preserving their old scalar campaign cardinality is not.

## Genuine Design reopen triggers

Reopen only when evidence invalidates a Frozen premise listed in Section 11.3, especially if per-size binding currentness cannot be proven without collection identity contaminating science, or if the stakeholder explicitly requires multi-size qualification/release selection in this same cycle.
