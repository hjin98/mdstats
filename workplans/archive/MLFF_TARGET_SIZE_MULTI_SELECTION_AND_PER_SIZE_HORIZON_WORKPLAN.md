---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-MULTI-SELECTION-AND-PER-SIZE-HORIZON
protocol_version: 5.16.0
status: implementation-complete
created_date: 2026-09-07
reviewed_date: 2026-09-07
closure_reviewed_date: 2026-09-07
implementation_completed_date: 2026-09-07
closure_review_status: pass
predecessor_workplan: workplans/active/MLFF_TARGET_SIZE_PROVISIONAL_SELECTION_AUTO_DIAGNOSTIC_AND_HORIZON_STEERING_WORKPLAN.md
reviewed_implementation_branch: plan/mlff-target-size-provisional-selection-auto-diagnostic
reviewed_implementation_head: 7a38490c14999b460a634066ad8fe0d69cf673eb
reviewed_behavior_commit: fdbbea44815a79de08d77e6c58d8f45b428f114f
closure_review_base: cd79bfc377aa109c69090f39d15015f608e8271d
architecture_change: ordered-multi-target-provisional-design-and-per-size-post-selection-training
---

# MLFF target-size multi-selection and per-size horizon workplan

## Status and authority

**DESIGN CLOSURE PASS / implementation-ready.**

This file is the sole current implementation authority for the multi-target-size successor revision. It supersedes earlier contents of this same workplan path and incorporates the final closure review against the submitted predecessor implementation at `7a38490c14999b460a634066ad8fe0d69cf673eb`.

The predecessor implementation established most of the difficult authority separation correctly and is reused wherever its semantics survive. The closure review found one material predecessor conformance defect plus several successor consequences that were not explicit enough for lossless implementation. Those issues are resolved here as binding requirements rather than left for Implementation to guess.

The central product change remains:

> The operator-owned provisional downstream target design is an ordered collection of distinct qualified target sizes. A new N appends; reselecting an existing N replaces that size's complete per-size design in place. `cross-validate` freezes the entire ordered collection atomically. Existing CV and fresh-production methodology then executes independently for every frozen size while reusing one prepared generation.

The implementation baseline itself is **not** accepted as the final target because the role/provenance identity coupling described in Closure Finding R1 must be corrected. That correction is part of this successor implementation, not a reason to invent a parallel repair layer.

No production-scale or GPU qualification is required during implementation. Functional regression/integration is required through real semantic owners with bounded numerical doubles below the expensive MACE boundary.

---

# 0. Final closure review findings and resolutions

## R1 — Blocking identity coupling in the submitted scalar implementation

### Evidence

The predecessor design requires the following semantic dependency graph:

```text
TargetBinding
    N_selected
    exact T_selected
    prepared/training-order scientific lineage

CV identity
    TargetBinding
    + H_cv
    + existing CV/method fields
    - H_prod
    - selection provenance

Production identity
    TargetBinding
    + accepted CV/method ancestry
    + H_prod
    - selection provenance
```

The submitted implementation currently computes `FrozenTargetSelection.content_digest` from the complete frozen record, including:

```text
N
membership
training order
H_cv
H_prod
selection_source
auto_diagnostic_digest
```

and `PostSelectionBinding` includes that full frozen-selection digest. CV plans then include the full `PostSelectionBinding`. Therefore `H_prod`, manual-versus-auto provenance, and automatic-diagnostic provenance can change a CV descendant's digest transitively even though they are forbidden CV identity inputs.

The existing predecessor test checks that provenance field names are absent from the direct binding payload, but that oracle does not detect transitive contamination through `frozen_selection_digest`.

### Frozen repair

Separate **full frozen-entry authority/currentness** from **per-size scientific target binding identity**.

The full frozen entry may remain an authenticated record containing N, exact membership identity, both horizons, and provenance. Its content digest may cover all of those fields for persistence/audit/currentness.

However the numerical/scientific `PostSelectionBinding` or its semantic successor MUST NOT depend on the full frozen-entry digest when that digest contains role-extraneous horizons or provenance.

The minimum dependency structure is:

```text
FrozenEntry_i                 # orchestration/audit authority
    N_i
    exact T_i identity
    training-order identity
    H_cv_i
    H_prod_i
    selection provenance

TargetBinding_i               # per-size target scientific lineage
    current generation
    accepted prepared/P1/P2 lineage
    N_i
    exact T_i identity
    training-order identity

CV_i
    TargetBinding_i
    + method identity
    + CV policy identity containing H_cv_i
    + CV plan/evidence ancestry

Production_i
    TargetBinding_i
    + method identity
    + accepted CV ancestry
    + production policy identity containing H_prod_i
```

Selection source and auto-diagnostic provenance are audit fields only. They MUST NOT change TargetBinding, CV, production, run, publication, or qualification numerical identity when the actual governed scientific design is otherwise identical.

`H_prod` MUST NOT change TargetBinding or CV identity. `H_cv` MUST NOT change TargetBinding or the production policy itself; production descendants may change through the explicitly accepted CV ancestry, which is correct.

A full frozen-entry digest may be carried separately for audit/currentness if useful, but it MUST NOT be embedded transitively in role identities that are defined to exclude its extra fields.

Do not fix this with a second binding wrapper synchronized with the old one. Rewire the existing binding/identity boundary so each role hashes only its governed inputs.

## R2 — Generation rollover must retire the complete multi-size design

The current prepare owner already advances the canonical target-size generation when prepared scientific identity changes and constructs fresh campaign state. Preserve that invariant for collections.

- unchanged prepared identity -> preserve the current generation and its provisional/frozen collection exactly;
- changed prepared identity -> one fresh generation with **empty provisional selection and no freeze**;
- every old per-size binding, CV pointer, production pointer/publication, and qualification descendant remains historical under the old generation;
- no old selected N, collection order, horizon, or provenance is carried into the fresh generation merely because the new prepared ladder happens to contain the same N values.

A stale P5 writer from the retired generation cannot publish current evidence after rollover.

## R3 — Observation must remain one coherent multi-binding snapshot

The current lifecycle observer deliberately reads the target-size revision and all descendant pointer rows in one SQLite read transaction because pointer publication can change without advancing the target-size state revision.

The multi-size implementation MUST preserve that property. `status`, lifecycle projection, and other public observation must derive:

```text
one target-size revision
+ the complete ordered frozen binding set
+ every relevant P5 pointer namespace for those bindings
+ P7 pointers only where qualification is actually authorized
```

from one coherent read transaction. Do not loop over bindings with independently timed authoritative reads that can produce a hybrid state that never existed.

Observation remains non-mutating: it creates no wrappers, evidence roots, plans, sessions, or qualification attempts.

## R4 — Production admission is a collection-wide barrier

`train-production` MUST preflight the entire frozen design before starting any new production job.

Every frozen size must have current accepted CV ancestry under its own binding and H_cv. If any selected size is missing, stale, corrupt, incomplete, or rejected at the CV boundary, the invocation starts **no new production jobs** and reports the blocking N(s).

Already-existing immutable production evidence from an earlier attempt remains historical/current according to its own identity; the preflight rule only prevents new production admission from bypassing a failed/incomplete member of the frozen requested experiment.

This preserves the stage contract and prevents the product from silently turning an all-sizes experiment into a successful subset.

## R5 — Multi-size post-production state must terminate truthfully

For `k > 1`, this revision intentionally produces several final-production publications but does not authorize a rule for choosing one release product or consuming one-shot locked evidence across products.

Therefore, after every selected size has a current final publication:

- the multi-size **training experiment is complete**;
- it is **not release-qualified**;
- `advance` has no further consequential command and must not repeatedly route into a command guaranteed to fail;
- `qualification status` remains observational and reports that qualification is unavailable for the multi-size frozen design;
- consequential qualification commands such as `qualification run` and `qualification activate-locked` fail closed before creating/opening an attempt or revealing locked evidence.

For `k == 1`, existing qualification methodology and lifecycle remain unchanged.

## R6 — Outer size scheduling must not multiply resource ownership

A simple serial outer iteration over selected sizes is an acceptable default and requires no new scheduler.

If Implementation elects to overlap sizes using existing bounded scheduling, all size jobs must participate in the existing effective resource allocation. Outer size concurrency, inner fold/seed workers, MACE subprocesses, BLAS/OpenMP threads, GPU leases, RAM/VRAM reservations, and I/O budgets MUST NOT each independently assume ownership of the whole machine.

No new generic parallel runtime is authorized by this workplan.

## R7 — Compatibility migration must remain append-only and schema-authentic

The campaign state chain is append-only. Existing v1/v2 rows must be authenticated under their native schema and never rewritten in place merely to make the new collection representation uniform.

- predecessor-v2 provisional state may normalize to a one-entry provisional collection and, on the next consequential successor mutation/freeze, publish the new canonical collection schema;
- predecessor-v2 frozen state remains a frozen one-entry legacy-compatible experiment and is not appendable/thawed;
- existing predecessor-v2 P5 descendants may continue under their historical binding schema when exact legacy ancestry remains current;
- the flawed v2 transitive identity coupling is **not** copied forward into new successor collection/binding schemas merely for symmetry;
- older-v1 reducer-terminal state remains diagnostic-only under the predecessor cutover and can never become an operator freeze.

---

# 1. Original product problem and invariants

## 1.1 Product problem

The prepared target-size ladder is expensive and deliberately reusable. The operator may need several longer-horizon experiments from the same prepared generation to compare behavior across qualified target sizes without re-running preparation or allowing the newest selection command to erase an earlier requested experiment.

The frozen downstream design is therefore:

```text
D = [
  (N_1, H_cv_1, H_prod_1),
  (N_2, H_cv_2, H_prod_2),
  ...,
  (N_k, H_cv_k, H_prod_k),
]

k >= 1 at cross-validation admission
```

Each N is a distinct configured qualified target size. Each tuple snapshots its own effective CV and production horizons.

The size dimension is one more post-selection experiment dimension over the same prepared generation. It is not another campaign, another target-size screen, or another prepared dataset.

## 1.2 Frozen product invariants

### P1 — Ordered unique-by-N provisional design

The provisional collection contains at most one entry for each N and preserves first-insertion order for distinct sizes.

- new N -> append complete entry;
- existing N -> replace its complete entry in place, preserving its list position;
- duplicate-N authoritative state -> corruption, never silently deduplicated.

### P2 — Exact membership only

For every selected N:

```text
T_N = pi_train[:N]
```

through the one accepted P2 training-order owner. No arbitrary list, resampling, random target membership, or non-ladder N is introduced.

### P3 — Per-size resolved horizon snapshot

Every successful manual or auto installation resolves a complete `(N, H_cv, H_prod)` from canonical config/default owners plus explicit options on that invocation.

Existing untouched entries do not drift when config changes. Reselecting an existing N deliberately re-resolves every omitted horizon for the new invocation.

### P4 — Empty is the canonical unselected state

Immediately after a fresh prepared generation or `select-target-size --reset`, the provisional collection is empty. No fake `N=undefined` record is required.

`cross-validate` refuses zero concrete selected sizes.

### P5 — Auto remains advisory and ordinary after recommendation resolution

The predecessor's P2/P3 automatic screen remains an optional cached diagnostic. A valid recommendation is installed through the same unique-by-N merge owner as a manual N.

- warm auto performs zero new target-size TRAIN2/EVAL2 work;
- no-recommendation changes no provisional collection field;
- diagnostic evidence/report may survive reset;
- auto never clears sibling selections or receives special collection authority.

### P6 — Reset clears only provisional selection

`select-target-size --reset` is pre-freeze only. It atomically clears all provisional entries while preserving the prepared generation and valid automatic-diagnostic evidence. It performs no screen/CV/production numerical work.

### P7 — Cross-validation admission freezes the complete collection atomically

`cross-validate` is the only freeze authority. Before numerical CV begins it re-authenticates every entry against the same current prepared generation and publishes one immutable ordered frozen design in one CampaignStore/CAS transition.

After freeze, selected N values, order, exact memberships, per-size horizons, and provenance are immutable for that generation.

### P8 — CV and production gain a size dimension, not a second subsystem

Every frozen size receives the existing post-selection CV methodology using its exact T_N and H_cv, then the existing fresh final-production methodology using H_prod and accepted CV ancestry.

No new cross-size reducer or best-size rule is introduced.

### P9 — Every requested size remains accounted for

Campaign CV succeeds only if every selected size reaches the existing accepted CV predicate. Campaign production succeeds only if every selected size has the required current final publication.

Failure/staleness for one N never silently removes it. Valid completed siblings remain reusable on retry where their existing identity/currentness contract permits.

### P10 — Per-size role identities are decomposed, not collection-hashed

Sibling sizes, list position, collection digest, selection provenance, and role-extraneous horizons do not contaminate a per-size numerical identity.

The exact dependency graph is the one frozen in R1.

### P11 — One prepared generation is shared

Adding sizes does not invoke `prepare`, duplicate prepared arrays, or create per-size campaign copies. Per-run materialization remains only what the existing P5 training methodology genuinely requires.

### P12 — Qualification cannot become hidden target-size selection

For k>1, locked/qualification evidence is not used to compare or choose target sizes. For k==1 existing qualification remains the downstream release path.

## 1.3 Explicit non-goals

This revision does not:

- redesign the automatic successive-halving algorithm, ranking metric, or P2/P3 scientific identity;
- change P1/P2 partition/order science;
- allow arbitrary noncandidate N;
- add automatic horizon optimization or other per-size hyperparameters;
- change CV fold construction or acceptance predicates;
- change production seed or committee policy;
- allow screen/CV checkpoints to parent final production;
- create per-size subcampaigns or a generic experiment-management framework;
- add a second selection database/state machine;
- select a cross-size winner after production;
- use qualification or locked evidence as a cross-size reducer;
- require production-scale/GPU qualification during implementation.

---

# 2. Reconciliation with the submitted predecessor implementation

## 2.1 Completed foundations to preserve

The reviewed predecessor implementation already provides and must retain:

1. **Advisory automatic diagnostic** — P2/P3 screen/reducer remains evidence/recommendation, not freeze authority.
2. **Warm diagnostic reuse** — authenticated complete diagnostic can be reused with zero new TRAIN2/EVAL2 work.
3. **No-recommendation non-mutation** — terminal insufficient diagnostic evidence does not destroy an operator choice.
4. **Derived portable diagnostic report** — report is reconstructible and not a second authority.
5. **Qualified manual N authentication** — manual choice uses the accepted P2 training-order/membership owner.
6. **Zero numerical work on manual selection.**
7. **Per-invocation horizon resolution** from existing CV/production config-policy owners with explicit CLI override.
8. **Persisted horizon snapshots** that do not drift after config edits.
9. **One CampaignStore/CAS state authority** with serialized races and stale-auto protection.
10. **Cross-validate as the freeze boundary.**
11. **P5 independence from automatic-screen ancestry.**
12. **Binding-keyed P5 immutable evidence/pointers** under one generation root.
13. **Old-v1 cutover** where reducer-terminal state remains diagnostic-only.
14. **Fresh-start production** and existing post-selection/qualification scientific methodology.

## 2.2 Correct predecessor behavior superseded only by new cardinality

These scalar assumptions are not predecessor bugs, but they are no longer the target design:

- one `state.proposal`;
- one `state.frozen`;
- every distinct manual N replaces the previous N;
- one selected-training context per whole campaign command;
- one CV/production binding per campaign generation;
- lifecycle/status rendering one selected N;
- old provisional CLI spellings `--select-horizon-cv` / `--select-horizon`.

Generalize/remove the scalar **authority role** rather than wrapping it with a second synchronized collection. Existing scalar value records may be reused as per-size elements where that remains the simplest representation.

## 2.3 Predecessor defect that must be repaired, not preserved

R1 is a genuine implementation drift from the predecessor's own identity hierarchy. Existing direct-payload tests did not expose the transitive dependency.

Successor implementation must repair the owning identity boundary and strengthen the oracle. Do not cite existing v2 behavior as a compatibility reason to keep role/provenance contamination in new current schemas.

---

# 3. Frozen high-level architecture

## 3.1 Authority graph

```text
one authenticated prepared generation
              |
      +-------+------------------+
      |                          |
      v                          v
optional cached P2/P3      ordered provisional collection
screen/recommendation      CampaignStore current authority
      |                          |
      | N_auto                   | [entry_1 ... entry_k]
      +------------------------> | unique by N
                                 |
                                 | cross-validate admission
                                 v
                       ordered frozen collection
                       [frozen_1 ... frozen_k]
                                 |
                 +---------------+---------------+
                 |                               |
                 v                               v
        existing P5 CV per size         existing final production
        x existing folds/seeds          per size x prod seeds
                 |                               |
                 +---------------+---------------+
                                 v
                     per-size final publications

qualification:
    k == 1 -> existing P7 path
    k > 1  -> training experiment terminal; no release selection/locked opening
```

## 3.2 One canonical collection authority

`CampaignStore` remains the sole mutable current authority.

Conceptually:

```text
provisional_entries: ordered tuple[PerSizeProposal]
frozen_entries: optional ordered tuple[PerSizeFrozenEntry]
```

Exact names/layout are delegated.

Forbidden:

- authoritative scalar plus separately authoritative list kept in sync;
- one mutable row/file/database per size requiring reconciliation;
- separate manual and auto collections;
- result/report files used as authority;
- enum states for every size x seed x fold Cartesian product.

A small linear search over the bounded size collection is sufficient. Do not add registries/index services merely for lookup.

## 3.3 Full frozen entry versus TargetBinding

The full frozen entry is the operator's immutable design/audit record. TargetBinding is its role-neutral scientific projection.

Implementation may keep a full-entry digest for exact state authentication. It must not use that digest as the scientific parent when it contains H_cv, H_prod, or provenance.

The `PostSelectionBinding` surface should be altered/re-derived directly to encode the TargetBinding semantics in R1. Do not stack another synchronized wrapper over an unchanged contaminated binding.

## 3.4 Binding-keyed P5 persistence remains the per-size namespace

The existing P5 object store and pointer namespace keyed by per-size binding are the correct persistence granularity. Reuse them.

One generation root may contain immutable evidence for several current per-size bindings. There is no collection-level copy of numerical evidence and no cross-size publication object that chooses a winner.

## 3.5 Per-size descendant currentness is role-aware

A current descendant must prove:

1. the campaign generation is still current;
2. its TargetBinding matches exactly one authenticated member of the current frozen collection;
3. its role policy/ancestry matches that entry's frozen role-specific inputs.

Examples:

- CV currentness authenticates TargetBinding and the CV policy containing H_cv;
- production currentness authenticates TargetBinding, accepted CV ancestry, and production policy containing H_prod.

Equality of N alone is insufficient. Whole-collection digest/order is also insufficient and must not be injected into numerical identity.

## 3.6 Atomic freeze

The complete collection is revalidated and frozen before any CV job is admitted. No per-size incremental freeze exists.

## 3.7 Generation rollover

Prepared-identity change replaces the entire design with a fresh generation and empty selection as specified in R2. Unchanged prepare does not perturb a valid collection.

## 3.8 Deterministic ordering and bounded scheduling

Frozen list order controls user-visible ordering and deterministic orchestration/result rendering. Completion timing may differ.

Serial outer-size execution is acceptable. Concurrent outer-size scheduling is optional only through already-supported bounded resource ownership as specified in R6.

## 3.9 Qualification boundary

Single-size qualification remains scientifically unchanged.

Multi-size qualification is intentionally unavailable. This is a safety boundary, not a placeholder algorithm. A future release-selection or multi-product qualification feature requires separate explicit Design authority.

---

# 4. Public CLI and provisional-state contract

## 4.1 Manual selection

```bash
select-target-size <N> [--horizon-cv HC] [--horizon H]
```

Required path:

1. establish current prepared generation;
2. authenticate N through the existing qualified-candidate/training-order owner;
3. resolve complete H_cv/H_prod using canonical config/default owners plus this invocation's flags;
4. construct one complete per-size proposal;
5. atomically append or replace-in-place by N under CampaignStore/CAS;
6. render the complete resulting collection;
7. perform zero target-size TRAIN2/EVAL2 work.

## 4.2 Automatic selection

```bash
select-target-size --auto [--horizon-cv HC] [--horizon H]
```

Retain existing cold/warm diagnostic behavior. Once a valid recommendation exists, build the same kind of per-size proposal as the manual path and merge it through the same collection owner.

A stale long-running auto may finish/persist its diagnostic evidence/report but must not install over a newer append/update/reset/freeze. The operator can rerun warm `--auto` against the current revision to install without retraining.

## 4.3 Reset

```bash
select-target-size --reset
```

- pre-freeze only;
- atomically clears all provisional entries;
- preserves prepared generation and independently valid diagnostic evidence/report;
- zero numerical work;
- mutually exclusive with N, `--auto`, `--horizon-cv`, and `--horizon`;
- an already-empty reset may be idempotent without a meaningless new revision.

## 4.4 Bare command and operation selection

Bare `select-target-size` remains invalid and actionable.

Exactly one operation selector is present: positional N, `--auto`, or `--reset`.

## 4.5 Canonical horizon flag names

Current public spellings become:

```text
--horizon-cv
--horizon
```

The predecessor implementation's provisional `--select-horizon-cv` / `--select-horizon` names are removed rather than retained behind aliases because no governed released compatibility contract was found. If Implementation discovers concrete contrary evidence, reopen only this compatibility decision before adding alias machinery.

## 4.6 Omitted-horizon semantics

For every manual or successful auto-install invocation:

```text
H_cv = explicit --horizon-cv
       else current [post_selection.cv].max_num_epochs/default

H_prod = explicit --horizon
         else current [training].max_num_epochs/default
```

Both effective values are persisted into the affected proposal. Existing untouched entries retain their previous values. CLI never rewrites `campaign.toml`.

---

# 5. State, schema, compatibility, and append-only migration

## 5.1 Valid current states

The campaign must represent cleanly:

```text
prepared generation + empty provisional collection
prepared generation + ordered nonempty provisional collection
prepared generation + ordered nonempty frozen collection
```

No simultaneous provisional + frozen current authority.

## 5.2 Collection validation

On construction/deserialization and before freeze, enforce:

- deterministic sequence order;
- unique N;
- positive N and horizons;
- each N qualified when checked against the current prepared authority;
- exact membership and training-order identity authenticates;
- one common prepared/training-order lineage across the collection;
- no malformed or mixed-schema payload silently normalized into a guessed valid design.

## 5.3 Predecessor-v2 provisional state

Semantic projection:

```text
proposal is None -> provisional_entries = []
proposal = P     -> provisional_entries = [P]
```

Do not rewrite the old row. The read boundary may normalize it in memory. The first successor mutation/freeze may append a new canonical collection revision through the existing CAS chain.

## 5.4 Predecessor-v2 frozen state

A scalar frozen v2 campaign is already immutable and may be exposed as a one-entry frozen compatibility view. It cannot accept another selection or be reset/thawed.

Existing v2 descendants may remain current only through their exact historical v2 ancestry. Do not rewrite their identities into the successor schema merely to standardize bytes.

New successor frozen collections use the corrected R1 identity decomposition.

## 5.5 Older-v1 state

The old terminal reducer selection remains diagnostic evidence only. It never becomes a frozen operator choice through collection normalization.

## 5.6 No destructive state-chain migration

All migration/normalization respects append-only authenticated revisions. Never mutate/re-hash old state rows in place.

---

# 6. Atomic freeze and multi-size CV

## 6.1 Admission sequence

`cross-validate` is the only freeze authority. Before numerical work it must:

1. load current CampaignStore revision under normal writer/currentness discipline;
2. require at least one provisional entry;
3. load/authenticate the current prepared generation once;
4. validate unique-by-N/order invariants;
5. revalidate every selected N against the current qualified set;
6. re-derive every exact `pi_train[:N]` membership;
7. authenticate every proposal's training-order/prepared lineage;
8. construct the complete ordered frozen entry collection preserving resolved horizons/provenance;
9. CAS-publish that collection atomically and retire provisional authority in the same logical transition;
10. derive corrected per-size TargetBindings/contexts only from the committed frozen state;
11. only then admit CV jobs.

One corrupt member rejects the entire admission. No partial freeze or partial CV start.

## 6.2 Collection-level current context

Provide one production-owned collection read yielding ordered authenticated per-size contexts. Each context reuses the existing one-size membership/P5 planning semantics after the R1 binding correction.

Callers/test harnesses must not independently assemble loops from raw state as a substitute for the production owner.

## 6.3 CV execution

For each frozen entry in deterministic selection order:

- exact T_N;
- its frozen H_cv via CV policy identity;
- existing method identity;
- existing fold construction, seeds, evaluation, and acceptance predicates;
- binding-keyed P5 immutable evidence/pointers.

Campaign CV is accepted only when every frozen size has current accepted CV evidence. A rejected size remains visibly rejected; no selected size is dropped.

Whether the command continues gathering sibling CV evidence after one rejection or stops admitting further expensive work is delegated, provided it reports truthfully and cannot falsely mark the campaign accepted.

## 6.4 CV restart/currentness

Already-valid completed sibling CV evidence is reused. Live config edits do not alter frozen horizons.

If the canonical generation changes while CV is running, stale evidence may remain historical but cannot publish current. Once staleness is detected, the orchestrator stops admitting new outer-size work for the retired design.

---

# 7. Multi-size final production

## 7.1 Collection-wide preflight barrier

Before starting any new production run, authenticate the complete frozen collection and require current accepted CV for every selected binding.

If any N fails preflight, identify all known blockers and start no new production work in that invocation.

## 7.2 Per-size production

After successful preflight, enumerate the frozen entries using existing final-production owners:

- use H_prod only through final-production policy identity;
- use exact full T_N;
- require the matching N's accepted CV ancestry;
- preserve existing M3 lineage;
- preserve fresh initialization, fresh optimizer/RNG semantics, production seeds, representative selection, and committee policy;
- publish one binding-scoped final-production decision per N.

Screen/CV checkpoints never parent production.

## 7.3 No cross-size contamination

N1 cannot consume N2 membership, horizons, CV plan/acceptance, run evidence, pointer, final plan, or publication.

No cross-size final-publication committee is created.

## 7.4 Restart/failure isolation

If N1 is complete and N2 fails/interupts:

- frozen collection unchanged;
- N1 valid evidence remains reusable;
- retry recomputes only evidence existing identity/restart owners deem incomplete/stale;
- campaign production remains non-complete until every N closes.

If generation rollover occurs, all old-generation publications become historical currentness-wise even if their immutable bytes remain stored.

---

# 8. Publication currentness, observation, and lifecycle

## 8.1 P5 publication currentness

At commit-time pointer publication, verify the campaign generation and role-appropriate per-size ancestry from the current frozen collection in the same serialized CampaignStore boundary used today.

Do not authorize publication using N equality alone. Do not make role identity depend on collection digest.

## 8.2 Coherent owner snapshot

Generalize the current lifecycle snapshot from one binding to an ordered binding collection. In one SQLite read transaction capture:

- target-size state revision;
- all current frozen per-size TargetBindings derivable from that revision;
- all P5 pointer rows needed to project CV/production state for every binding;
- for k==1, the P7 pointer rows needed for qualification observation.

Interpret compact pointed records after capturing a coherent pointer set, preserving existing authentication behavior.

## 8.3 Status rendering

Every successful selection/auto/reset and `status` shows the complete design.

Before freeze:

```text
Target-size training plan: provisional
Frozen: no
Selected sizes: K
[1] N=... H_cv=... H_prod=... source=...
[2] ...
```

Empty state shows no concrete size plus current default H_cv/H_prod values and the requirement to select at least one N before CV.

After freeze, show the complete ordered list with per-size CV and production state. Auto recommendation remains separate diagnostic information.

Expose a derived side-by-side per-size result summary sufficient to locate/compare the existing governed CV/production observables/publications. It is presentation only: no ranking, sorting by performance, winner flag, or new reducer.

## 8.4 `advance`

- no provisional selections -> stop at target-size decision; never invent N or opt into auto;
- provisional nonempty -> `cross-validate`;
- frozen + any CV not accepted -> CV remains the relevant stage; never advance into production;
- all CV accepted + any production incomplete -> `train-production`;
- all production complete + k==1 -> existing qualification stage;
- all production complete + k>1 -> no next consequential command; report multi-size training experiment complete and qualification unavailable in this revision.

## 8.5 Multi-size terminal state is not release qualification

For k>1, completion of production is a terminal training-experiment state only. Do not set a release-qualified verdict or synthesize qualification completion.

`qualification status` succeeds observationally and reports the unsupported multi-size release boundary without writes. Consequential P7 commands fail closed.

---

# 9. Qualification boundary

## 9.1 k == 1

Preserve existing P7 methodology, one exact final publication, locked activation semantics, identity, and regression behavior, except for any schema-version adaptation mechanically required by the corrected TargetBinding representation.

No scientific qualification rule changes.

## 9.2 k > 1

Before opening a qualification session or reading/revealing locked evidence:

- `qualification run` -> actionable fail-closed;
- `qualification activate-locked` -> actionable fail-closed;
- any other consequential qualification entrypoint -> same;
- `qualification status` -> observational success explaining that several publications exist and no release-selection rule is authorized.

Never:

- choose first/last/auto-recommended N;
- choose best CV/production metric;
- run locked evidence across sizes and choose a winner;
- combine seeds from different N values into one committee;
- mutate the frozen collection down to one N.

---

# 10. Resource, restart, storage, and retention

## 10.1 Resource ownership

Prefer serial outer-size iteration unless already-supported bounded scheduling clearly improves throughput without adding complexity.

If concurrent:

- derive effective resources once under existing resource owners;
- outer size jobs share the same allocation;
- inner fold/seed/MACE/library concurrency is bounded accordingly;
- GPU/device leases remain explicit where applicable;
- RAM/VRAM/I/O admission remains bounded;
- completion order never changes frozen result ordering/identity.

## 10.2 Stop admitting stale outer work

Do not hold a campaign lock over expensive training. But before admitting a new outer-size unit, detect a retired generation/freeze when economically available and stop scheduling further stale work. Commit-time fences remain authoritative for publication.

## 10.3 P3 retention

Automatic diagnostic/P3 evidence remains governed by its existing retention owner; provisional/reset/multi-size state does not make valid diagnostic evidence disposable.

## 10.4 P5 retention

Retention/currentness traversal must account for every current per-size P5 binding. A cleanup path cannot treat N2 evidence as unreachable merely because it inspected N1's pointer namespace.

Preserve binding-keyed immutable ownership rather than adding collection copies.

## 10.5 Qualification retention

For k==1 retain existing P7 retention. For k>1 no new qualification attempts are opened, so there is no new multi-product qualification retention graph.

---

# 11. Documentation and current product truth

Reconcile all affected current architecture/specification/user-guide/CLI-help surfaces so they describe one coherent behavior, including:

- ordered multi-size selection;
- append versus duplicate-N replacement-in-place;
- per-size H_cv/H_prod snapshots;
- `--reset`;
- canonical `--horizon-cv` / `--horizon` names;
- advisory cached auto diagnostic;
- complete-collection freeze;
- TargetBinding versus full frozen-entry identity decomposition;
- CV and production size dimensions;
- per-size production publications;
- collection-wide production CV preflight;
- generation rollover clearing the full design;
- multi-size training terminal state;
- single-size-only qualification under this revision;
- no automatic cross-size winner.

Remove current-semantic wording that says campaign selection is always scalar or that a second distinct N replaces the first.

Historical/archive material may remain historical. Regenerate tracked PDFs/derived manuals from authoritative Markdown according to repository policy; do not hand-edit generated PDFs.

---

# 12. Implementation obligations

## O1 — Correct the predecessor identity hierarchy first

Rewire full frozen-entry authority versus TargetBinding/P5 role identity exactly as R1. Strengthen tests so transitive digest dependencies are checked, not only direct field names.

## O2 — Generalize scalar provisional authority to one ordered unique-by-N collection

Reuse the existing per-size proposal value semantics where simple. New N appends; duplicate N replaces complete entry in place without reordering.

## O3 — Preserve canonical per-size horizon resolution

Reuse existing policy/config resolution; snapshot complete effective values into only the affected entry.

## O4 — Add reset and rename horizon flags

Implement pre-freeze collection clear and canonical `--horizon-cv` / `--horizon`, without compatibility aliases absent concrete governed evidence.

## O5 — Route auto recommendation through the same merge owner

Preserve cold/warm/no-recommendation/report semantics and CAS stale-install protection.

## O6 — Freeze the complete collection atomically

Revalidate all entries against one prepared generation and commit one immutable ordered design before any CV execution.

## O7 — Provide one production-owned ordered per-size context collection

Do not leave enumeration to ad-hoc consumers/tests.

## O8 — Generalize existing P5 binding/currentness directly

Use corrected TargetBinding semantics and binding-keyed evidence. Do not introduce a parallel per-size store or binding wrapper.

## O9 — Execute real CV orchestration across all frozen sizes

Use existing fold/seed/method/acceptance owners below the size dimension.

## O10 — Enforce collection-wide CV acceptance before new production work

Preflight all N values first; no partial new production admission.

## O11 — Execute real fresh production across all frozen sizes

Use each N's own H_prod and accepted CV, preserving existing production science and one per-size publication.

## O12 — Preserve restart, generation currentness, and sibling reuse

Stop stale admission after generation movement; preserve immutable historical evidence; never silently carry selections into a fresh generation.

## O13 — Generalize coherent lifecycle observation

One revision plus all relevant per-binding pointers in one read transaction; status remains read-only.

## O14 — Make lifecycle/results collection-aware

Aggregate completion across every frozen N; expose deterministic per-size results without ranking.

## O15 — Make P5 storage/retention collection-aware

Protect every current sibling binding without duplicating prepared data or numerical evidence.

## O16 — Preserve append-only v1/v2 compatibility without importing v2 identity defects

Normalize at boundaries or append canonical successor revisions; never rewrite old rows.

## O17 — Preserve k==1 qualification and fail closed for consequential k>1 qualification

`qualification status` remains observational for k>1 and explains the boundary.

## O18 — Reconcile documentation and obsolete scalar semantics

Update current source docs/help/specs and rebuild tracked generated artifacts.

---

# 13. Frozen versus delegated implementation authority

## 13.1 Frozen

1. Ordered collection of distinct qualified N values.
2. New N appends; existing N replaces complete per-size entry in place.
3. Empty collection is canonical unselected state.
4. Each entry persists independently resolved positive H_cv/H_prod.
5. Exact membership is always `pi_train[:N]` from one P2 training order.
6. Manual selection performs zero target-size TRAIN2/EVAL2 work.
7. Auto diagnostic science/cache/report remains unchanged and advisory.
8. Auto recommendation uses the same merge owner; no recommendation changes no collection state.
9. Reset clears only provisional collection and is forbidden after freeze.
10. `cross-validate` atomically freezes all entries before numerical CV.
11. Full frozen entry authority is distinct from TargetBinding identity.
12. TargetBinding excludes H_cv, H_prod, selection source, and auto provenance.
13. CV identity adds H_cv through CV policy and excludes H_prod/provenance.
14. Production identity adds H_prod through production policy plus accepted CV ancestry and excludes provenance.
15. Whole collection digest/order/siblings do not contaminate per-size numerical identity.
16. One CampaignStore remains mutable current authority.
17. Existing binding-keyed P5 storage is reused rather than replaced by per-size subcampaigns.
18. CV existing methodology runs for every frozen size.
19. Campaign CV acceptance requires all frozen sizes accepted.
20. Production admission requires all frozen sizes currently CV-accepted before any new production job starts.
21. Existing fresh final-production methodology runs for every frozen size.
22. Every frozen size must have its own current final publication for campaign production completion.
23. No selected size disappears silently on failure.
24. Valid completed sibling evidence is reusable under existing currentness/restart rules.
25. Prepared identity change creates a fresh generation with empty selection/freeze and retires all old bindings as current.
26. Unchanged prepare preserves the current generation/design.
27. Public observation captures revision + all relevant per-binding pointer namespaces coherently in one read transaction.
28. Status/advance are observational/routing only and never authorize by themselves.
29. Deterministic user-visible ordering follows frozen selection order.
30. Concurrent size execution, if used, shares bounded effective resources and cannot multiply machine ownership.
31. Canonical CLI flags are `--horizon-cv` and `--horizon`; provisional predecessor spellings are removed absent governed compatibility evidence.
32. k==1 qualification science remains unchanged.
33. k>1 all-production-complete is a terminal training-experiment state, not release qualification.
34. k>1 consequential qualification commands fail before attempt/locked-evidence creation; qualification status remains read-only and explanatory.
35. No cross-size winner/reducer/release selection is introduced.
36. Old rows remain append-only/authenticated under native schema; old-v1 terminal reducer state remains diagnostic-only.
37. Production-scale/GPU qualification is deferred during implementation.

## 13.2 Delegated

Implementation may choose/simplify:

- exact dataclass/schema/field names;
- whether scalar proposal/frozen value records are reused or minimally renamed as per-size elements;
- exact collection serialization layout and collection orchestration digest;
- exact transition-kind names/wire versioning consistent with append-only compatibility;
- exact TargetBinding field name/schema, provided dependency rules above hold;
- exact collection iterator/helper/module boundaries;
- serial versus already-supported bounded outer-size scheduling;
- exact per-size result formatting/paths under current ownership;
- test file organization.

Prefer direct alteration/removal of obsolete scalar authority/currentness over compatibility wrappers, registries, or generic experiment engines.

## 13.3 Design reopen triggers

Reopen only the affected surface if evidence demonstrates one of these Frozen premises cannot be satisfied without architecture change:

- corrected TargetBinding cannot prove current membership without reintroducing role/provenance contamination;
- binding-keyed P5 store cannot represent multiple current target descendants safely;
- atomic collection freeze cannot be achieved under CampaignStore/CAS;
- a released external compatibility contract genuinely requires old horizon flag aliases;
- the stakeholder requires multi-size release selection/qualification in this same cycle;
- safe outer-size scheduling requires a materially new resource architecture.

Ordinary implementation inconvenience is not a redesign trigger.

---

# 14. Expected affected surface

Start with these proven owners, then re-derive final impact from the assembled candidate:

```text
mdstats/training_data/campaign_target_size_state.py
mdstats/training_data/campaign_target_size_selection.py
mdstats/training_data/campaign_target_size_runtime.py
mdstats/training_data/campaign_target_size_view.py
mdstats/training_data/campaign_target_size_cutover.py
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
mdstats/training_data/post_selection_run_identity.py

mdstats/training_data/campaign_target_size_retention.py
mdstats/training_data/storage/owners.py

mdstats/training_data/qualification/commands.py
mdstats/training_data/qualification/runtime.py
mdstats/training_data/qualification/binding.py
mdstats/training_data/qualification/observation.py
mdstats/training_data/qualification/store.py
```

Also inspect every current consumer that assumes:

- `state.proposal` or `state.frozen` is scalar;
- `load_current_selected_training_context()` returns the campaign's only size;
- one `PostSelectionContext` represents the complete command;
- one current CV/final pointer namespace exists;
- one current final publication exists;
- lifecycle `_binding_for(...)` can derive exactly one binding;
- whole `FrozenTargetSelection.content_digest` is a valid numerical parent;
- old `--select-horizon*` names are current.

Documentation includes the predecessor-touched architecture manual, target-size specification, campaign CLI spec/help, README/user guide/runbook references, and tracked generated PDFs/manifests.

---

# 15. Task-specific acceptance matrix

Protocol 5.16 focused checks, stage-local affected regression, final affected-surface regression, real-owner integration, and repository-required static checks remain binding.

## A1 — Predecessor foundation preservation

Retain executable evidence for:

- exact manual membership via real P2 owner;
- zero manual screening numerical work;
- cold/warm auto and zero-work warm path;
- auto no-recommendation atomic non-mutation;
- diagnostic report fidelity/rebuildability;
- per-invocation horizons and no config drift;
- stale-auto/CAS protection;
- old-v1 diagnostic-only cutover;
- fresh-production semantics.

Adapt scalar assertions to collection cardinality without weakening their semantic oracle.

## A2 — Identity decomposition counterfactuals — mandatory repair oracle

Use direct digest comparisons through the real production identity owners. Do **not** accept merely checking that forbidden field names are absent from a payload.

For fixed generation/prepared lineage/N/T/method:

1. same H_cv, change only H_prod -> TargetBinding unchanged; CV policy/plan/acceptance identity unchanged; production policy/plan changes as governed;
2. same H_prod, change only H_cv -> TargetBinding unchanged; CV policy/plan changes; production policy itself unchanged; final production ancestry changes only through the accepted CV dependency;
3. same N/T/horizons, manual versus auto provenance -> TargetBinding, CV numerical identity, production numerical identity unchanged;
4. change only auto diagnostic provenance -> same numerical identities;
5. change N or exact membership/training-order lineage -> TargetBinding changes;
6. add/reorder an unrelated sibling in an equivalent fresh design -> this N's TargetBinding/role identities unchanged except genuinely governed generation lineage;
7. full frozen-entry authority still detects tampered horizons/provenance if that full digest is retained.

These tests must fail against the submitted contaminated binding implementation and pass only after the owning boundary is corrected.

## A3 — CLI grammar

Prove manual/auto with zero/one/both canonical horizon flags; reset exclusivity; bare invalid command; nonpositive horizons; noncandidate N; post-freeze mutation rejection; old provisional horizon flag names rejected unless Design is explicitly reopened.

## A4 — Ordered merge, reload, and corruption

Through real CampaignStore owner:

```text
512                 -> [512]
1024                -> [512, 1024]
512(new horizons)   -> [512(updated), 1024]
2048                -> [512(updated), 1024, 2048]
1024(new horizons)  -> [512(updated), 1024(updated), 2048]
```

Assert exact order, unique N, complete per-size snapshots/provenance/membership, serialization/reload equivalence, and fail-closed duplicate/malformed authoritative state.

A bounded Hypothesis state-machine test using a simple independent ordered-map oracle is appropriate if available; real test-owned CampaignStore remains the state owner.

## A5 — Reset and cached diagnostic

From multi-entry provisional state with cached auto evidence:

- reset -> empty collection;
- prepared generation unchanged;
- diagnostic unchanged;
- zero numerical calls;
- CV refuses;
- warm auto after reset installs exactly one recommendation without retraining.

## A6 — Per-size default snapshots

Change config defaults between select/reselect calls. Only the touched entry receives current omitted defaults. Untouched entries survive reload/freeze/config edits unchanged.

## A7 — Auto merge and races

Cover:

- manual N1 -> auto N2 => [N1,N2];
- manual N1 -> auto N1 => N1 replaced in place;
- auto N1 -> manual N2 => [N1,N2];
- no recommendation => collection semantically unchanged;
- stale auto loses to append/update/reset/freeze while diagnostic evidence remains valid.

## A8 — Atomic freeze

Assembled public path with at least two sizes must prove one atomic frozen collection, exact membership reauthentication, frozen per-size horizons, no automatic diagnostic requirement, and no post-freeze selection/reset mutation.

Inject corruption into one member below persistence boundaries: entire freeze fails and no CV job is admitted.

## A9 — Per-size binding/currentness

For each frozen size, prove the selected-training adapter yields the corrected TargetBinding and exact membership.

Reject:

- another generation;
- forged membership/training order;
- N-only lookalike;
- wrong role policy horizon;
- stale binding not present in current collection.

Accept current siblings simultaneously. Whole collection digest/order cannot be required by per-size numerical identities.

## A10 — Real CV owner across size x existing dimensions

Call assembled public `cross-validate` with bounded numerical doubles only below the real P5 numerical seam. The production orchestrator, not the harness, enumerates every frozen size and passes correct T_N/H_cv into real CV plan/fold/acceptance owners.

## A11 — CV failure/restart

Deterministically fail or reject one size after another has completed valid work. Prove no selected N disappears, valid sibling evidence is reusable, campaign is not falsely accepted, and frozen settings do not drift.

## A12 — Production collection-wide preflight

With N1 accepted CV and N2 missing/rejected/stale CV, call real `train-production` and prove **zero new production job admissions** for all sizes. Existing immutable evidence is not deleted.

With all CV accepted, every N is admitted to its own real final-production plan.

## A13 — Real production separation

Through assembled `train-production`, verify every N gets correct H_prod, membership, accepted CV, M3, seeds, fresh-start semantics, and binding-scoped publication. N1 cannot consume N2 evidence or pointers.

## A14 — Production restart sibling preservation

Interrupt N2 after N1 completes. Retry/reload: N1 current work reused, N2 resumes/reruns under existing rules, no collection mutation, campaign incomplete until all publications exist.

## A15 — Generation rollover

Cover both paths:

- unchanged `prepare` -> same generation, same provisional/frozen collection and current descendants;
- changed prepared identity -> generation + 1, empty selection/no freeze, all old per-size bindings/pointers/publications unreachable as current.

Race a stale old-generation P5 publication against rollover and prove the commit-time fence rejects current publication. Once staleness is detected, no further outer-size work is newly admitted for the old design.

## A16 — Coherent multi-binding observation

With at least two bindings and concurrent pointer publication, repeatedly call lifecycle/status observation. Each result must correspond to one coherent SQLite snapshot; it cannot combine a target revision from one moment with per-size pointer sets from incompatible moments.

Assert observational commands create no files/rows/wrappers/evidence roots/sessions.

## A17 — CAS collection races

Use real CampaignStore for deterministic races:

- append N2 vs update N1;
- append/update vs reset;
- reset vs freeze;
- selection vs freeze;
- long-running auto install vs append/update/reset/freeze;
- changed prepare versus freeze/publication.

Exactly one valid transition ordering wins; no lost entry, duplicate N, partial freeze, or split ancestry.

## A18 — Resource ownership

If outer size execution is serial, prove no new size scheduler/resource multiplication exists.

If concurrent, test the effective plan so total outer + inner workers/device leases stay within existing allocation and deterministic result order remains frozen order. Do not accept each size independently claiming full CPU/GPU/RAM allocation.

## A19 — P5 store/retention

Create current P5 evidence for at least two bindings. Prove pointers coexist, both current descendants are retained, cleanup cannot delete one sibling merely because another was used for reachability, and no duplicate prepared generation is materialized per size.

## A20 — Lifecycle/results/advance

Assert complete ordered provisional/frozen state and per-size CV/production status.

- zero selection -> advance stops;
- incomplete/failed CV -> never production;
- all CV accepted + incomplete production -> train-production;
- k==1 all production -> existing qualification route;
- k>1 all production -> no next consequential command, explicit terminal training-experiment message, no release-qualified claim.

Derived results may present existing metrics side-by-side but never rank/choose N.

## A21 — Qualification boundary

For k==1, run existing qualification regression unchanged scientifically.

For k>1:

- `qualification status` succeeds read-only and reports unsupported multi-product qualification;
- `qualification run`, locked activation, and every consequential P7 path fail before attempt creation, inference, external reference request, or locked-evidence opening;
- no first/last/best/auto implicit selection exists.

## A22 — v1/v2 compatibility and append-only migration

Prove:

- v2 no proposal/freeze -> empty provisional view;
- v2 proposal -> one provisional entry; later successor mutation writes new canonical row without rewriting old;
- v2 frozen -> one immutable frozen compatibility view; cannot append/reset/thaw;
- existing valid legacy P5 descendant remains current under exact legacy ancestry where supported;
- successor new binding schema does not inherit legacy transitive H_prod/provenance coupling;
- old-v1 terminal reducer row remains diagnostic-only.

## A23 — Structural/obsolete-semantic closure

Inspect current executable/normative surfaces for:

- scalar current-selection authority still driving current decisions;
- synchronized scalar + collection representations;
- second selection store/subcampaign machinery;
- full frozen-entry digest used transitively as TargetBinding/CV identity;
- second distinct N replacing the first;
- status showing one N only;
- publication currentness comparing against one scalar `state.frozen`;
- old `--select-horizon*` current flags;
- production choosing a subset/winner;
- multi-size qualification choosing a publication.

Use structural tooling when appropriate; validate any acceptance-critical custom structural rule with known-positive and known-negative examples. Historical/archive material is excluded from current-semantic absence claims.

## A24 — Final affected regression/integration

After all material executable edits:

1. reconcile every obligation in this file against the assembled candidate;
2. re-derive actual affected surface;
3. run the adapted predecessor provisional-selection suite, including strengthened identity tests;
4. run affected target-size state/runtime/view/prepare/currentness/lifecycle tests;
5. run affected P5 CV/production/run/restart/publication/store/storage tests;
6. run single-size qualification regression and multi-size fail-closed/status tests;
7. run assembled `prepare -> select N1 -> select N2 -> cross-validate -> train-production -> reload/status` through real owners with bounded numerical doubles;
8. run a generation-rollover integration from a frozen multi-size campaign;
9. run project-configured static/lint/type checks for affected Python surfaces;
10. if impact cannot be bounded confidently, run the broader repository suite supported by the environment.

A required check that cannot execute is incomplete evidence, not a pass by inspection.

---

# 16. Implementation sequence

## Stage A — Identity repair + collection authority + CLI/compatibility

1. Correct R1 at the real binding/identity owner.
2. Generalize provisional state to ordered collection.
3. Implement append/replace/reset and new flag names.
4. Normalize v2 provisional state without rewriting history.
5. Close focused identity, state, serialization, CLI, CAS, and predecessor-foundation regression.

Do not begin multi-size P5 orchestration while the binding still contains role/provenance contamination.

## Stage B — Atomic freeze + per-size currentness + coherent observation

1. Freeze whole collection atomically.
2. Expose production-owned ordered per-size contexts.
3. Adapt P5 pointer publication/currentness to corrected TargetBinding membership.
4. Generalize lifecycle coherent snapshot across all binding namespaces.
5. Close freeze/currentness/observation/v1-v2 compatibility tests.

## Stage C — Multi-size CV + production + restart/resource closure

1. Real CV owner enumerates all sizes.
2. Add collection-wide production CV preflight.
3. Real production owner enumerates all sizes.
4. Preserve sibling restart/reuse and stop stale outer admission.
5. Validate resource ownership if any outer concurrency is used.
6. Close stage-local P5 regression and assembled bounded integration.

## Stage D — Lifecycle/storage/qualification/docs/final regression

1. Aggregate status/results/advance across all N values.
2. Implement k>1 terminal training-experiment and qualification boundary.
3. Make retention/cleanup sibling-aware.
4. Reconcile current docs/spec/help and regenerate derived manuals.
5. Run final affected-surface regression/integration/static checks.

---

# 17. Active simplicity and closure rule

If Implementation starts adding machinery whose only purpose is to keep an old scalar campaign authority synchronized with a collection, stop and generalize/remove the scalar authority instead.

If Implementation starts creating per-size subcampaigns, per-size mutable state databases, a generic nested experiment engine, or a cross-size reducer, stop and reuse the existing collection + per-binding architecture.

If the corrected R1 identity graph can be expressed by deleting/replacing one contaminated ancestry edge, prefer that over introducing a parallel identity stack.

The workplan is closed for implementation when the above Frozen requirements are accepted. Any Design reopen must be evidence-triggered under Section 13.3; ordinary code-shape difficulty stays delegated to Implementation.
