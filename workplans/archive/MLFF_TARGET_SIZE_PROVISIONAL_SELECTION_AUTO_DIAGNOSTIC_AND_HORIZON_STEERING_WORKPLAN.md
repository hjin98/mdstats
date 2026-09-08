---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-PROVISIONAL-SELECTION-AUTO-DIAGNOSTIC-AND-HORIZON-STEERING
protocol_version: 5.16.0
status: implementation-ready
created_date: 2026-09-07
reviewed_date: 2026-09-07
reviewed_source_branch: main
reviewed_code_baseline: 7cfb932cf8f3f8390aeeb98fa2c444c699c9ea11
architecture_change: bounded-target-size-authority-lifecycle-and-post-selection-rewire
---

# MLFF target-size provisional selection, advisory auto diagnostic, and horizon steering workplan

## Status and authority

**PASS / implementation-ready.**

This workplan is the snapshot-complete implementation authority for a bounded rework of the MLFF target-size decision boundary.

It preserves the existing target-size scientific substrate, nested candidate memberships, automatic screening algorithm, optimizer-normalization implementation, objective/weighting corrections, P3 execution/restart machinery, post-selection CV methodology, fresh-production methodology, and downstream qualification architecture except where this workplan explicitly changes their authority or control relationship.

The central semantic change is:

> The target-size screen is no longer the authority that freezes the downstream training-set size. It becomes an optional, cached diagnostic that may recommend a size. The operator owns a mutable provisional downstream training design until `cross-validate` begins, at which point the selected target size and role-specific training horizons are frozen atomically for downstream work.

The existing automatic screen is retained because it contains useful empirical evidence. Its scientific interpretation is narrowed: it is evidence about short-horizon target-force RMSE under the configured screening protocol, not proof of asymptotic target-size convergence or final physical-model quality.

This workplan supersedes current architecture/specification/CLI wording that says:

- the reducer is the only authority allowed to select the target size;
- completion of the target-size screen immediately freezes `N_selected` and `T_selected`;
- automatic screening is mandatory before post-selection work;
- a terminal automatic scientific outcome necessarily terminates the campaign;
- post-selection selection lineage must derive from a P3 execution head/reducer;
- bare `select-target-size` means "run the automatic screen and select N".

It does **not** retire the P2/P3 automatic-screen implementation or invalidate scientifically current screen evidence merely because its downstream authority is being reduced.

---

# 1. Objective / problem invariants / non-goals

## 1.1 Original scientific and product problem

The campaign ultimately needs an explicit choice of:

```text
how much target data to train on
+
how much optimization budget to spend
```

before beginning expensive post-selection validation and production.

The current target-size screen attempts to infer the first quantity from short-horizon force-RMSE behavior. Recent fixed-optimizer and normalized-optimizer experiments demonstrate that candidate size and short-horizon optimizer progress are strongly coupled. They also demonstrate that apparently reasonable optimizer controls can materially change the ranking across target sizes.

That evidence does **not** establish whether:

- the fixed-LR experiment was closer to long-horizon truth;
- the normalized-LR experiment was closer to long-horizon truth;
- the target-size/error relationship is linear;
- an early RMSE ranking predicts a long training trajectory;
- force RMSE alone predicts the quality or stability of the final potential in actual MD.

Consequently, the product must not force a short-horizon proxy experiment to masquerade as a conclusive scientific target-size authority.

The system must instead support a scientifically explicit experimental-design decision:

```text
N
H_cv
H_prod
```

while retaining the existing automatic screen as optional evidence that can help the operator make that decision.

## 1.2 Product invariants

### P1 — Exact selected target membership

For any chosen admissible size `N`, the target dataset remains exactly:

```text
T_N = pi_train[:N]
```

There is no alternate membership constructor, resampling path, random target membership, or manually supplied arbitrary list.

### P2 — Operator-steerable provisional decision

Before post-selection work begins, the operator may freely change the current provisional target size.

Examples:

```bash
select-target-size 512
select-target-size 1024
```

```bash
select-target-size 512
select-target-size --auto
```

```bash
select-target-size --auto
select-target-size 1024
```

The most recently accepted provisional command defines the current provisional downstream design.

### P3 — Automatic screening is advisory

`select-target-size --auto` means:

> run or reuse the automatic target-size diagnostic and use its recommendation as the current provisional target-size choice.

It does not independently create frozen `N_selected`/`T_selected`.

### P4 — Automatic diagnostics are reusable

An authenticated complete automatic diagnostic for the current automatic-screen scientific/execution identity must be reused.

A second `select-target-size --auto` must not rerun target-size candidate training/EVAL merely because the operator wants the existing recommendation to become the current provisional choice again.

### P5 — Diagnostic failure does not remove manual choice

A terminal automatic-screen outcome such as insufficient comparison is a diagnostic conclusion, not a campaign-level prohibition on manual target-size choice.

If the prepared target-size substrate remains valid and a particular candidate is individually qualified, the operator may select that candidate manually even if the automatic diagnostic could not make a valid comparison.

Shared corruption, invalid preparation, invalid membership, or other defects that also make manual selection scientifically unauthentic remain blocking.

### P6 — Target size and optimization horizon are distinct but coupled experiment controls

The selected downstream design exposes independent provisional horizons:

```text
H_cv
H_prod
```

The software must not infer an unproven automatic target-size-to-horizon mapping.

### P7 — Freeze occurs only on downstream admission

Neither:

```bash
select-target-size <N>
```

nor:

```bash
select-target-size --auto
```

freezes the downstream experiment.

The freeze point is admission to:

```bash
cross-validate
```

At that boundary the current target choice, exact membership, and effective role-specific horizons become immutable ancestry for downstream work.

### P8 — One downstream path

Manual and automatically recommended provisional selections must converge onto the same post-selection machinery. There is one frozen target binding, one CV architecture, one final-production architecture, and one qualification architecture.

### P9 — Stronger downstream evidence remains stronger

Documentation and diagnostics must clearly distinguish:

```text
short-horizon automatic screening
    = target-size heuristic / diagnostic evidence

post-selection CV
    = validation of the training method on the chosen target dataset

full production
    = long-horizon realization of the chosen training design

post-production physical / MD qualification
    = stronger evidence about actual potential behavior
```

No target-size screening metric may be documented as proof of final MD quality.

## 1.3 Explicit non-goals

This workplan does **not**:

- redesign the automatic successive-halving algorithm;
- change the current `1/3/10` default fidelity ladder;
- decide whether LR/EMA normalization is scientifically optimal;
- derive a new target-size-to-training-horizon scaling law;
- replace target-force RMSE as the automatic screen's ranking metric;
- alter the P1 neutral statistical substrate;
- alter `P_train`, `M3`, `pi_train`, or `pi_eval`;
- add arbitrary noncandidate target sizes;
- change post-selection fold-construction methodology;
- weaken existing CV acceptance predicates;
- make screen or CV checkpoints production parents;
- change the fresh-start final-production requirement;
- change qualification/MD release gates;
- run full production/GPU qualification during implementation;
- create a second campaign state machine;
- create a separate manual-training subsystem;
- introduce a generic experiment-management framework;
- add automatic horizon optimization.

---

# 2. Frozen high-level architecture and engineering envelope

## 2.1 New authority graph

The following high-level architecture is Frozen for this cycle:

```text
canonical frame / neutral statistical authorities
                  |
                  v
       prepared target-size generation
                  |
          +-------+----------------------+
          |                              |
          v                              v
optional automatic diagnostic      provisional design
P2/P3 screen + reducer             mutable CampaignStore state
          |                              |
          | recommendation/evidence      | N_provisional
          +----------------------------> | H_cv_provisional
                                         | H_prod_provisional
                                         | selection source
                                         |
                                         | cross-validate admission
                                         v
                              immutable frozen target binding
                              + frozen role-specific budgets
                                         |
                               +---------+---------+
                               |                   |
                               v                   v
                         cross-validation    final production
                                                   |
                                                   v
                                              qualification
```

Automatic diagnostic execution and operator selection are orthogonal concerns.

Implementation must not replace the current coupling with a larger Cartesian-product lifecycle enum.

## 2.2 One campaign-state authority

`CampaignStore` remains the single mutable current campaign authority.

The rework may revise its target-size schema and records, but it must not introduce a second authoritative target-selection file, separate mutable manual-selection database, parallel auto-selection state machine, or synchronized authoritative JSON/SQLite copy.

P3 content-addressed screen evidence remains immutable scientific evidence. Portable reports and result views remain derived, rebuildable projections.

## 2.3 P2/P3 screen remains the automatic diagnostic owner

The existing target-size scientific experiment remains the owner of automatic-screen calculations:

```text
qualified candidates
-> paired optimizer seeds
-> configured fidelity boundaries
-> EVAL2 target-force metric
-> arithmetic seed aggregation
-> practical-equivalence ranking
-> successive halving
-> terminal reducer result
```

Its terminal internal `selected_target_size` may remain in its existing persisted schema where preserving that schema is necessary to reuse expensive existing evidence.

At the public/current campaign boundary that value means `recommended_target_size`, not frozen `N_selected`.

No P5 consumer may obtain its target dataset merely because P2/P3 internally uses the historical word `selected`.

## 2.4 Provisional design is mutable and snapshot-complete

Before freeze, the campaign owns one complete mutable proposal:

```text
N_provisional
selection_source
H_cv_provisional
H_prod_provisional
optional auto-diagnostic provenance
```

`T_provisional` is never an independently mutable list. It is always derived as `pi_train[:N_provisional]` and may carry its derived digest for integrity/currentness.

Repeated target-size commands update this one proposal through the existing serialized CampaignStore/CAS ownership model.

**Review amendment — proposal/config drift:** once a proposal is accepted, its effective horizons are persisted as explicit resolved values. Later edits to `campaign.toml` do not silently mutate that existing proposal. A subsequent `select-target-size ...` invocation creates a new complete proposal by resolving omitted horizon arguments from the then-current configuration/defaults.

No separate proposal-history subsystem is required; the normal campaign revision chain is sufficient history.

## 2.5 Freeze decomposes identity correctly

Although the operator chooses `(N, H_cv, H_prod)` together, implementation must not collapse them into one scientific identity whose every field invalidates every descendant.

Freeze must preserve:

```text
FrozenTargetBinding
    N_selected
    T_selected

CV policy
    depends on FrozenTargetBinding
    depends on H_cv
    does NOT depend on H_prod

Production policy
    depends on FrozenTargetBinding
    depends on accepted method/CV ancestry
    depends on H_prod
```

Selection-source provenance and automatic-diagnostic provenance must not alter numerical downstream identity when the actual frozen scientific design is otherwise identical.

## 2.6 Frozen downstream values override later live defaults

Once `cross-validate` freezes the proposal, later reconstruction must use the frozen effective horizons. Later config edits must not silently rewrite the already frozen experiment.

Existing reset/new-generation mechanisms remain the route for intentionally starting another experiment; do not add an ad-hoc post-freeze mutation command.

---

# 3. Public CLI contract

## 3.1 Manual/default selection

Primary interface:

```bash
select-target-size <N>
```

Required behavior:

1. load the current prepared target-size generation;
2. establish currentness;
3. resolve the P2 qualified candidate set;
4. require `N` to be one of those configured qualified candidates;
5. derive `T_N = pi_train[:N]`;
6. validate membership identity through the existing P2 training-order owner;
7. resolve a complete provisional CV/production horizon snapshot;
8. CAS-publish the new provisional proposal;
9. perform no target-size candidate training or EVAL2 work.

## 3.2 Automatic recommendation

Optional interface:

```bash
select-target-size --auto
```

If no current reusable automatic diagnostic exists, run/resume the existing screen and render its diagnostic report. If a current reusable complete diagnostic exists, authenticate/reload it, do zero new target-size TRAIN2/EVAL2 work, and report reuse.

When the diagnostic has a valid recommendation, its recommended N becomes the new provisional N.

**Review amendment — atomic no-recommendation semantics:** if the auto diagnostic completes without a recommendation, the command must not partially modify `N_provisional`, `selection_source`, `H_cv_provisional`, or `H_prod_provisional`. Any previously valid proposal remains unchanged. The diagnostic evidence/report is still committed and reusable.

## 3.3 Invalid bare command

`select-target-size` with neither positional N nor `--auto` is invalid and must provide actionable usage guidance.

## 3.4 Mutual exclusion

`select-target-size 512 --auto` is invalid.

## 3.5 Horizon controls

Both modes accept:

```text
--select-horizon-cv <positive integer>
--select-horizon <positive integer>
```

`--select-horizon-cv` controls provisional CV max epochs. `--select-horizon` controls provisional final-production max epochs.

## 3.6 Omitted horizon semantics

Each successful proposal-setting invocation resolves a complete proposal from current config/defaults plus explicit options on that invocation.

If `--select-horizon-cv` is absent:

```text
H_cv = [post_selection.cv].max_num_epochs or default 30
```

If `--select-horizon` is absent:

```text
H_prod = [training].max_num_epochs or default 30
```

An earlier CLI override does not become a hidden sticky default for a later proposal-setting invocation.

The CLI must not rewrite `campaign.toml`.

---

# 4. Automatic diagnostic contract

## 4.1 Epistemic status

The automatic procedure must be described consistently as an automatic target-size diagnostic/recommendation. It must not be described as proof of optimal target size, asymptotic data convergence, long-horizon training quality, physical MLFF quality, or MD stability.

Its current ranking metric remains target-force component RMSE in meV/Å.

## 4.2 Diagnostic identity and cache reuse

Automatic diagnostic reuse identity remains defined by the scientific/execution fields that actually affect the screen.

The following must not invalidate a current diagnostic:

- provisional N changes;
- `--select-horizon-cv`;
- `--select-horizon`;
- configured CV horizon;
- configured final-production horizon;
- auto-report presentation;
- status wording;
- report output path;
- selection-source provenance.

This workplan changes P4/control-plane authority semantics. It must not bump P2/P3 scientific identity merely to rename their user-facing role.

Scientifically current existing P3 evidence should remain reusable.

## 4.3 Warm `--auto`

A warm `--auto` must authenticate current diagnostic evidence, obtain the recommendation, regenerate/reuse the derived human diagnostic, resolve a complete proposal for the current invocation, CAS-update the proposal, and explicitly state that no screening jobs were rerun.

No trainer/evaluator call is permitted on this path.

## 4.4 Interrupted auto run

Interrupted/nonterminal auto diagnostics remain resumable under existing P3 recovery semantics. A provisional manual selection that existed before the auto run must not be destroyed merely because the diagnostic is interrupted.

## 4.5 Terminal diagnostic failure

A complete automatic diagnostic may fail to produce a recommendation because its evidence is scientifically insufficient.

That outcome must be persisted as diagnostic evidence, rendered, reusable on later `--auto`, and must not transition the campaign into a terminal scientific failure that prohibits manual target selection.

If no provisional target existed, status continues to request an explicit manual choice.

**Review amendment — command result semantics:** completion of a valid diagnostic with no recommendation is a successful execution of the diagnostic operation, not an operational command failure. The CLI should return normal success unless the repository has an existing stronger convention for successful typed scientific outcomes. It must print that no recommendation was established and that the proposal was left unchanged.

## 4.6 Operational/shared-authority failures

Manual selection still fails when the system cannot establish the underlying facts needed to authenticate `T_N`, including missing/corrupt prepared generation, invalid current generation, malformed training order, candidate not qualified, candidate N not in the configured qualified set, membership digest mismatch, or source/currentness corruption that invalidates prepared authority.

---

# 5. Portable automatic diagnostic report

Every terminal automatic diagnostic, successful or scientifically unsuccessful, must have a portable human-readable report under the campaign `results/` tree using a stable generation-specific filename. Markdown is preferred; exact filename is delegated.

The report is derived, non-authoritative, rebuildable, portable, and sufficiently self-contained for human interpretation.

It must include:

- canonical generation and relevant experiment/execution/head/reducer identity;
- candidate sizes, evaluation populations, fidelity boundaries, optimizer seeds;
- ranking metric/unit, seed aggregation, practical-equivalence rule, funnel rule;
- optimizer normalization reference policy;
- per-candidate updates per epoch, effective LR, EMA state/effective decay;
- every completed boundary's per-seed RMSE, paired mean, success/failure, survive/eliminate outcome and reason;
- a filtering decision tree projected from authenticated reducer transitions;
- final recommendation or explicit no-recommendation result;
- warning/reason codes including `nonconverged_at_configured_ceiling` when applicable;
- a scientific limitation statement explaining that the result is a short-horizon diagnostic and may be overridden before CV freeze.

Report generation must not independently reimplement the ranking reducer.

Console rendering must show enough to understand per-boundary scores, survivor progression, recommendation/failure, important warnings, report path, whether evidence was new or reused, resulting proposal when applicable, and `frozen = no`.

---

# 6. Provisional target-design state

Before freeze, current campaign state must represent one proposal equivalent to:

```text
N_provisional
derived T_provisional identity
selection_source = manual | auto_recommendation
H_cv_provisional
H_prod_provisional
optional latest-auto-diagnostic identity/recommendation
```

Manual N is restricted to the configured qualified candidate set. Arbitrary positive prefixes are out of scope.

The immediate origin of the current proposal is recorded truthfully. Overriding an auto recommendation manually retains the auto diagnostic provenance rather than rewriting it.

Selection source is provenance, not a numerical variable. Same N/T and same role policies must produce the same downstream scientific target identity regardless of manual vs auto origin.

---

# 7. Concurrency and provisional-state precedence

Repeated provisional changes use the existing CampaignStore serialized/CAS transition ownership.

## 7.1 Long-running `--auto` versus later manual decision

An automatic diagnostic may run for hours. Its completion must not overwrite a newer explicit human choice.

Required semantics:

1. `--auto` captures the campaign/proposal revision against which it intends to install its recommendation;
2. expensive P3 diagnostic execution may proceed independently;
3. after recommendation is available, proposal update is conditional;
4. if proposal/freeze state changed since auto began, diagnostic evidence/report is retained but stale auto must not overwrite the newer proposal;
5. CLI reports recommendation computed but not installed because current selection state changed concurrently.

## 7.2 `--auto` versus cross-validation freeze

If CV freezes a proposal while auto diagnostic is running, diagnostic evidence may finish/publish but cannot alter frozen target design or create another selected binding.

## 7.3 Manual selection versus cross-validation freeze

Concurrent selection and CV freeze must serialize at the authoritative transition boundary. Exactly one ordering becomes current. No state may exist where campaign current selection and CV plan disagree.

---

# 8. Cross-validation admission is the freeze boundary

`cross-validate` must begin by establishing one coherent current proposal and converting it into frozen downstream ancestry.

The real admission path must:

1. load current campaign state under consequential writer/currentness discipline;
2. require a current provisional proposal;
3. load/authenticate current prepared target-size generation;
4. revalidate proposed N against current qualified candidate set;
5. derive exact `T_selected = pi_train[:N_provisional]`;
6. reproduce/authenticate membership digest;
7. take `H_cv_frozen` and `H_prod_frozen` from the persisted resolved proposal snapshot;
8. freeze target selection and both effective horizon decisions;
9. construct target binding and role-specific policy identities from frozen values;
10. bind the CV plan to the same admission state;
11. publish through existing currentness/CAS boundaries before numerical CV work begins.

No P3 auto diagnostic head is required for this transition.

The immutable target binding must establish current campaign generation, prepared/P2 lineage needed to authenticate `pi_train`, training-order identity, `N_selected`, and selected-membership digest.

Auto provenance may be retained as optional audit provenance but is not the source from which N is re-derived.

At freeze, both horizons are fixed in the same admission decision, while identity projection remains role-specific: CV sees `H_cv_frozen`, not `H_prod_frozen`; production sees `H_prod_frozen`.

After freeze, `select-target-size <N>` and `select-target-size --auto` must not mutate the current design.

---

# 9. Post-selection binding and P5 rewiring

The current P5 binding requires adopted execution head/reducer state because current selection is a reducer projection. That dependency is no longer valid.

P5 must instead consume the authenticated frozen target binding created at CV admission.

Automatic-screen head/reducer identities may remain optional diagnostic provenance but may not be mandatory post-selection ancestry.

Retain one authoritative current-selection exposure path for P5. Do not create permanent `manual` and `auto` selected-context loaders.

Final production remains fresh; this workplan does not authorize resuming from auto-screen or CV checkpoints.

---

# 10. Campaign state/schema rework and legacy cutover

Current campaign target-size state encodes assumptions that are no longer true, including reducer-derived terminal selection and campaign-terminal scientific failure.

Those semantics must not survive as current behavior behind aliases.

Evolve/version affected campaign-state and dependent persisted schemas whose meaning changes.

The new current state must represent independently:

```text
prepared/scientific generation identity
optional auto diagnostic execution/evidence
optional mutable provisional proposal
optional immutable frozen target selection
```

without encoding every cross-product as a lifecycle enum.

Do not solve this with an enum maze.

## 10.1 Old automatic terminal selection cannot authorize new P5

A persisted pre-rework `TERMINAL_SELECTED` reducer-derived record must never be silently interpreted as operator-approved frozen selection under this workplan.

Post-selection admission requires the new frozen-selection authority.

## 10.2 Preserve expensive P3 evidence where valid

Scientifically current P3 screen evidence may be explicitly adopted/reprojected as automatic diagnostic evidence/recommendation without retraining when identities match.

The cutover must not fabricate evidence, silently call old selection frozen, or rerun expensive training solely because authority role changed.

## 10.3 Pre-rework P5 descendants are historical

**Review amendment — old downstream descendants:** any existing P5 CV plan/acceptance, production plan/publication, or downstream qualification state that descends from the old reducer-derived `PostSelectionBinding` must not be silently rebound to a new operator-approved frozen target binding, even when N happens to match.

Those descendants remain historical under their old lineage. New post-selection work under this architecture requires a new freeze/admission under the new binding schema. Reuse is allowed only for lower-level evidence whose governed identity is independently proven equivalent and whose owner contract explicitly permits reuse; no cross-schema ancestry adoption is inferred from equality of N alone.

## 10.4 Historical internal terminology

Existing immutable P2/P3 schemas may retain fields such as `selected_target_size` / `status = selected` when renaming would invalidate/rewrite expensive scientific evidence.

If retained, current code must encapsulate that historical terminology behind the automatic-diagnostic boundary and publicly project it as `recommended_target_size`.

Structural tests must prevent P5/current frozen selection from consuming that field as direct selection authority.

---

# 11. Lifecycle, status, `advance`, and result views

The public workflow remains:

```text
init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production -> qualification
```

but `select-target-size` now means establish/revise the current provisional target training design, optionally using automatic diagnostic evidence.

After prepare with no proposal, status must request an explicit manual choice or opt-in auto diagnostic.

With a proposal, status must report provisional target size, selection source, membership identity, CV horizon, production horizon, latest auto diagnostic availability/recommendation, recommendation accepted/overridden, `Frozen: no`, and next consequential command `cross-validate`.

An active auto diagnostic must not obscure an already valid manual proposal.

After freeze, status reports selected target size, selected membership identity, frozen CV/production horizons, selection-source provenance, and `Frozen: yes`.

`advance` must never invent a target-size choice. When no proposal exists, it stops at the target-size decision boundary and instructs the operator to run either `select-target-size <N>` or `select-target-size --auto`. It must not silently route to auto.

---

# 12. Automatic-diagnostic scientific failures and warnings

`nonconverged_at_configured_ceiling` remains meaningful within auto diagnostic evidence and means the diagnostic recommends the practical ceiling while warning that convergence below it was not demonstrated. It does not freeze that size.

`too_few_complete_comparable_candidates` and analogous scientific failures mean the automatic diagnostic cannot make its configured recommendation. They do not mean no valid manually selected target experiment may proceed.

Do not convert diagnostic failure into fake reducer success; keep diagnostic truth intact and change campaign authority relationship instead.

---

# 13. Horizon-resolution and identity integration

Existing configuration owners remain canonical defaults:

```text
CV: [post_selection.cv].max_num_epochs, default 30
production: [training].max_num_epochs, default 30
```

Do not introduce second persistent configuration authorities under target-size configuration.

The two CLI flags are explicit user overrides at proposal-resolution time. They do not edit the config file.

The persisted proposal carries complete resolved effective values, so later freeze does not reconstruct earlier CLI arguments from live config.

Adapt existing CV and production policy resolvers so their horizon field can come from frozen effective values while all other policy fields continue to come from existing owners. Avoid cloning entire policy resolvers merely to override one field.

Neither provisional nor frozen CV/production horizon participates in automatic target-size diagnostic identity.

---

# 14. Storage, retention, and derived-artifact consequences

P3 auto evidence remains retainable independently of frozen selection.

Storage ownership/retention must recognize that auto diagnostics may exist with no proposal, manual proposal may exist with no auto diagnostic, auto evidence may remain useful after override, and auto evidence may still publish while CV freezes manual selection.

No cleanup rule may infer diagnostic candidate evidence is disposable merely because a provisional/frozen N exists unless the existing target-size retention owner independently certifies it disposable.

Portable reports remain derived and non-authoritative. They must never be read as authority for recommendation or frozen N.

---

# 15. Documentation and specification rewrite

This is a semantic architecture change and requires coherent current-document replacement rather than additive caveats.

At minimum reconcile:

```text
README.md
docs/arch_manuals/mlff_training_data/50_target_size_selection.md
docs/arch_manuals/mlff_training_data_architecture.md
docs/guides/mlff_campaign_cli_user_guide.md
docs/specs/training_data/README.md
docs/specs/training_data/mlff_data_stage_plan_spec.md
docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md
mdstats/training_data/_campaign_cli_core.py embedded help/config guide text
```

Rewrite current claims that reducer is sole frozen-selection authority, screen terminality freezes N, auto scientific failure is campaign terminality, or bare `select-target-size` means automatic selection.

Generated PDFs/assembled manuals tracked by repository policy must be regenerated from authoritative Markdown sources and verified; do not hand-edit derived PDFs.

Historical/archive documents may preserve old behavior as history.

---

# 16. Implementation obligations

## O1 — Re-derive target-size state ownership

Campaign state must separate prepared science, optional auto diagnostic evidence, mutable proposal, and frozen selection without a second authority or combinatorial lifecycle enum.

## O2 — Implement positional manual selection

`select-target-size <N>` sets a valid complete proposal through real prepared-generation/P2 membership owners and performs zero target-size TRAIN2/EVAL2 work.

## O3 — Reclassify auto as advisory diagnostic

Existing automatic screen produces recommendation/diagnostic and may update proposal, but never freezes selection.

## O4 — Reuse completed auto evidence

A second `--auto` on unchanged identity adds zero new target-size TRAIN2/EVAL2 calls.

## O5 — Produce trustworthy diagnostic report

Report is a projection of authenticated evidence and does not independently reimplement reducer ranking.

## O6 — Make auto scientific failure nonblocking for manual choice

Diagnostic scientific failure remains reportable/reusable and leaves a prior proposal untouched; valid manual proposal/freeze remains possible.

## O7 — Implement provisional CV and production horizons

Proposal resolves independent positive-integer `H_cv` and `H_prod`, including omission/default behavior.

## O8 — Freeze target and horizons on CV admission

`cross-validate` is the first freeze point; post-freeze selection edits fail.

## O9 — Preserve role-specific P5 identity hierarchy

CV identity depends on H_cv, production identity on H_prod, without unrelated cross-invalidation.

## O10 — Re-root P5 selection ancestry

P5 binds to frozen target selection from CV admission. No fake P3 reducer/head is generated for manual selection.

## O11 — Close concurrency races

Older auto completion cannot overwrite newer proposal/freeze; manual update versus freeze serializes exactly.

## O12 — Rewire lifecycle/status/advance

Status/advance reflect proposal/freeze semantics and never silently choose auto.

## O13 — Perform explicit schema/cutover handling

Old auto-terminal state cannot authorize new P5; compatible P3 evidence can be reused as diagnostic without retraining.

## O14 — Keep pre-rework P5 descendants historical

Old reducer-derived P5/qualification descendants are not rebound to new frozen-selection ancestry merely because N matches.

## O15 — Remove legacy current interpretations

Current executable/normative surfaces expose one interpretation; structural/negative checks close obsolete authority paths.

---

# 17. Implementation authority

## 17.1 Frozen

1. `select-target-size <N>` is the primary explicit-selection interface.
2. `select-target-size --auto` is optional automatic diagnostic/recommendation.
3. bare `select-target-size` is invalid.
4. `<N>` and `--auto` are mutually exclusive.
5. manual N is restricted to configured qualified candidate set.
6. automatic screening does not freeze the target.
7. repeated current `--auto` reuses complete authenticated diagnostic evidence.
8. no-recommendation auto completion changes no proposal fields.
9. auto diagnostic scientific failure does not prohibit valid manual selection.
10. proposal is mutable until `cross-validate` admission.
11. proposal persists complete resolved horizon values and does not drift with later config edits.
12. `cross-validate` freezes target membership and effective horizons.
13. `--select-horizon-cv` controls CV horizon.
14. `--select-horizon` controls final-production horizon.
15. omitted horizon flags resolve from current config/default on each proposal-setting invocation.
16. CLI steering does not rewrite `campaign.toml`.
17. CV and production horizon identities remain independent.
18. auto screen remains existing P2/P3 diagnostic algorithm for this cycle.
19. auto screen LR/EMA normalization remains unchanged by this workplan.
20. P3 diagnostic evidence is not mandatory P5 selection ancestry.
21. one P5 CV/production path serves every frozen selection.
22. final production remains fresh.
23. current docs present auto screen as heuristic/diagnostic rather than conclusive long-horizon/MD evidence.
24. `advance` never invents or silently auto-selects N.
25. old auto-terminal campaign state never silently becomes new frozen operator-approved selection.
26. scientifically current old P3 auto evidence should remain reusable as diagnostic evidence.
27. old P5/qualification descendants remain historical and are not rebound across the new selection-binding schema from N equality alone.
28. full production/GPU qualification remains deferred.

## 17.2 Delegated

Implementation may choose/simplify exact dataclass names, schema field layout, transition enum names, diagnostic-report filename, helper/module boundaries, terminal-projection helper disposition, exact cutover realization, console formatting, storage location inside existing owners, local policy-override projection, and test organization.

Equivalent simpler realization is preferred.

## 17.3 Reopen only on evidence

Reopen Design only if implementation evidence demonstrates that a Frozen premise is unsound, including inability to authenticate exact candidate/manual membership independently of P3 screen without changing P2 architecture; inability to atomically freeze proposal/CV ancestry within CampaignStore ownership; incompatibility between safe schema currentness and preserving valid P3 evidence; inability to preserve role-specific frozen horizon resolution within existing P5 architecture; or a genuine governed compatibility requirement for old bare `select-target-size` behavior.

Ordinary code-shape difficulty is not a redesign trigger.

---

# 18. Expected affected surface

Current likely executable surfaces include:

```text
mdstats/training_data/_campaign_cli_core.py
mdstats/training_data/campaign_lifecycle.py
mdstats/training_data/campaign_target_size_state.py
mdstats/training_data/campaign_target_size_runtime.py
mdstats/training_data/campaign_target_size_terminal.py
mdstats/training_data/campaign_target_size_view.py
mdstats/training_data/campaign_target_size_adoption.py
mdstats/training_data/campaign_target_size_cutover.py
mdstats/training_data/campaign_target_size_retention.py
mdstats/training_data/campaign_post_selection.py
mdstats/training_data/campaign_post_selection_runtime.py
mdstats/training_data/post_selection_identity.py
mdstats/training_data/post_selection_store.py
mdstats/training_data/storage/owners.py
```

Also inspect downstream consumers that construct/deserialize `PostSelectionBinding`, including qualification compatibility/currentness code.

Final affected surface must be re-derived from the assembled implementation.

---

# 19. Task-specific acceptance matrix

## 19.1 CLI contract

Prove valid/invalid parsing and admission for manual N, `--auto`, bare command, mutual exclusion, invalid horizons, unqualified/noncandidate N.

## 19.2 Manual path

Assembled `prepare -> select-target-size 512 -> status -> cross-validate` must demonstrate zero target-size trainer/EVAL calls, provisional state before CV, frozen exact membership at CV admission, real P5 context creation, and real CV owner receiving frozen H_cv.

## 19.3 Auto cold path

Public auto orchestration with bounded numerical doubles below P2/P3 owner must execute real orchestration/reducer, produce diagnostic report, set provisional N on recommendation, and leave selection unfrozen.

## 19.4 Auto warm path

Second unchanged `--auto` must produce zero new target-size TRAIN2/EVAL2 calls and set proposal from cached recommendation.

## 19.5 Auto/manual steering

Cover manual->manual, manual->auto, auto->manual override, and auto recommendation subsequently selected manually.

## 19.6 Diagnostic failure/manual bypass

Real P2/P3 owner reaches scientific no-recommendation outcome; report says no recommendation; existing proposal remains unchanged; a qualified manual candidate can subsequently be proposed/frozen.

## 19.7 Horizon behavior

Cover manual/auto with no flags, one-sided flags, and both flags. Prove omitted values are resolved only when proposal is set, persisted thereafter, and do not drift from later config edits. Prove horizons do not change auto diagnostic identity.

## 19.8 Freeze/currentness

Before CV proposal is replaceable; at CV admission exact target/horizons freeze; after freeze selection command fails; membership is re-derived from P2 order; corrupt proposal membership/digest cannot be accepted.

## 19.9 Identity hierarchy

Prove same N/T but different selection source/auto provenance yields same downstream scientific target identity; H_cv-only changes CV role policy; H_prod-only changes production role policy; presentation changes no scientific identity.

## 19.10 Concurrency

Use real CampaignStore writer/CAS owner with bounded deterministic synchronization for manual update vs CV freeze, auto completion vs newer manual update, and auto completion vs CV freeze.

Given the broad Python state-transition space, use Hypothesis stateful/property testing when available and materially useful to supplement deterministic race/admission cases; keep the real production state owner live.

## 19.11 Legacy cutover

Representative old auto-terminal state must fail as new frozen P5 authority, preserve compatible P3 evidence as diagnostic, support manual proposal, and support cached auto recommendation without retraining when compatible.

Representative old P5/qualification descendants must remain historical and must not be remapped to new ancestry from N equality.

## 19.12 Diagnostic oracle strength

For deterministic fixture, prove report fields equal authenticated evidence for all per-seed RMSE values, arithmetic means, boundaries, survivors/eliminations, recommendation, warnings/reasons, effective LR/EMA, updates per epoch. Inconsistent report copies never affect campaign state.

## 19.13 No-legacy-route structural closure

Search assembled current executable/normative surface for obsolete semantics including bare auto default, reducer sole frozen-selection authority, screen completion freezes N, auto failure blocks manual N, manual selection requires synthetic reducer/head, P5 requires auto reducer/head ancestry, advance silently invokes auto.

Use Semgrep for AST-structural forbidden/legacy owner paths when its model matches the claim and available; validate acceptance-critical rules against known-positive and known-negative constructs. Literal documentation wording may use bounded text search. Exclude explicitly historical/archive content from current-semantic absence claims.

---

# 20. Regression and integration requirements

After each coherent executable implementation stage, run focused tests plus stage-local affected regression.

Final assembled acceptance requires fresh affected-surface regression across P2 target-size definitions/qualification/reducer, P3 execution/restart/cache/reconciliation, P4 state/CAS/currentness/view/retention, P5 selected context/CV identity/runtime/production identity/runtime, campaign lifecycle/status/advance, storage ownership/retention, qualification consumers of selected binding, and CLI parser/config/help/guide behavior.

Then run the broad repository/project-required MLFF regression subset. If final impact cannot be bounded confidently, run the broader applicable suite.

Integration must execute real public orchestration/state owners. Expensive MACE training/inference may use bounded deterministic substitutes below those owners.

No production-scale GPU training is required for implementation acceptance.

---

# 21. Implementation sequence

## Stage A — State and identity authority reset

Implement separation of auto diagnostic, proposal, frozen selection, schema/CAS/currentness, and old-state cutover. Close stage-local state/CAS/legacy-read regression.

## Stage B — Manual proposal and horizon steering

Implement positional N and two horizon flags through real prepared-generation/P2 membership owners. Verify zero screen numerical work and persisted no-drift proposal snapshots.

## Stage C — Auto diagnostic reclassification, caching, report

Implement cold/warm auto, report, no-recommendation behavior, scientific failure, stale-completion CAS. Preserve existing screen algorithm/evidence identities unless genuine compatibility defect is found.

## Stage D — Freeze and P5 lineage re-root

Move frozen selection authority to CV admission. Rework post-selection binding/current context and role-specific horizon resolution. Close manual-with-no-P3 integration.

## Stage E — Lifecycle, status, advance, retention, compatibility

Reconcile lifecycle projection, status, advance, views, retention, storage owners, qualification/currentness consumers, old auto-terminal cutover, and historical old-P5 descendants.

## Stage F — Documentation rewrite and final closure

Rewrite current normative/user documentation coherently. Regenerate tracked derived manuals/PDFs as applicable. Perform structural no-legacy scan, final workplan reconciliation, re-derive affected surface, run final affected regression/integration.

---

# 22. Simplification triggers

Implementation must stop and simplify before adding durable machinery if it starts producing:

- separate manual and auto post-selection bindings;
- synchronized manual/auto selection authorities;
- proposal duplicated authoritatively in SQLite and result files;
- fake reducer objects for manual selection;
- compatibility wrappers that secretly retain old bare auto behavior;
- enum-state proliferation for combinations of independent facts;
- duplicate CV/production policy resolvers solely for horizon overrides;
- duplicate ranking implementation solely for reporting;
- separate history/provenance database when CampaignStore revisions/P3 evidence suffice;
- an unfreeze state machine merely to repair consequences of premature freezing.

Prefer removing old selection coupling over preserving it behind adapters.

---

# 23. Final design review closure

The final review found and closed four material gaps before implementation:

1. **Proposal/config drift:** accepted proposals now persist complete resolved horizons and remain stable until replaced/frozen.
2. **Atomic failed-auto semantics:** a completed diagnostic with no recommendation commits diagnostic evidence only and leaves all proposal fields unchanged.
3. **Legacy downstream ancestry:** pre-rework P5/qualification descendants remain historical and are not silently rebound under the new selection-binding schema.
4. **No-recommendation command semantics:** a valid completed diagnostic without recommendation is reported as a successful diagnostic result, not an operational campaign failure.

With those amendments, the plan is **PASS / implementation-ready**.

The revised architecture answers the scientific uncertainty without pretending to resolve it algorithmically:

```text
automatic screen
    -> optional, cached, inspectable evidence

operator
    -> chooses provisional N
    -> chooses CV horizon
    -> chooses production horizon
    -> may change any of them before downstream commitment

cross-validate
    -> authenticates and freezes the selected design

CV / production / qualification
    -> provide progressively stronger evidence
```

The automatic target-size machinery remains useful but is no longer permitted to overstate what its short-horizon force-RMSE experiment establishes.

The implementation should therefore be a **rewire and reduction of authority**, not an additive bypass layered on top of the current reducer-owned selection architecture.
