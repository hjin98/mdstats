---
kind: implementation-workplan
workplan_id: DOC-MLFF-FLEXIBLE-FIDELITY-PART1-CLOSEOUT-V1
protocol_version: 5.4.0
---

# MLFF Flexible-Fidelity Part 1 Documentation Closeout Workplan

## Objective

Close Part 1 of the flexible-fidelity redesign without changing executable MLFF behavior.

The branch currently implements the fixed target-size runtime (`3 -> 10 -> 30`) while `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1` defines the accepted future `(n1,n2,n3)/n` transition. Part 1 closeout must make every **current** architecture/specification/configuration/guide surface truthful to the executable fixed-runtime generation, keep future flexible semantics owned only by active implementation workplans until Part 2 is accepted, eliminate conflicting active-workplan authority, and preserve full regression-test strength.

This workplan supersedes the staging assumptions in `DOC-MLFF-FLEXIBLE-FIDELITY-EPOCH-CONTRACT-V1` where that earlier plan instructed current/normative documents to describe behavior that had not yet been implemented. The flexible-fidelity scientific design itself is not reopened.

## Diagnosis and protected concerns

Independent review identified four related authority failures in the documentation-first staging approach:

1. repository policy defines current architecture/specifications/guides as descriptions of accepted present software, so they must not advertise the future flexible runtime before Part 2 lands;
2. `campaign.toml.example` exposes target-size epoch controls that the current parser either ignores or rejects, creating a misleading executable example;
3. several current documentation/graph surfaces mix future flexible semantics or implementation chronology into present-tense product authority;
4. older active workplans still freeze fixed `3/10/30` requirements unless their authority is explicitly and unambiguously narrowed when Part 2 implementation begins.

A final review additionally found that the Stage-11 SIZE-FIDELITY1 graph overstates `winner_recall_equals_1` as an independent hard predicate although the executable policy records winner recall while hard acceptance is governed by configured finalist-recall/equivalence/boundary requirements.

The protected concerns are therefore:

- one truthful current authority for the implemented product;
- one explicit proposed authority for the future flexible transition;
- no silently ineffective or rejected current configuration examples;
- no ambiguous workplan precedence during Part 2;
- no weakening of public/package regression checks to accommodate a dependency-limited development environment;
- no scientific change to the accepted flexible-fidelity target design.

## Frozen decisions

Implementation must preserve all of the following.

### Current product truth

Until Part 2 executable acceptance is complete, current product documentation describes the implemented fixed generation:

- target-size screening boundaries are `3`, `10`, and `30` epochs;
- current `TargetSizeStudyPolicy` owns the fixed tuple `(3,10,30)`;
- TRAIN2 full horizon remains `30` for the current target-size-v5 generation;
- current SIZE-FIDELITY1 uses the implemented target-size-v5 v2 calibration/reference semantics;
- current progress/reporting documentation describes only behavior the current reporter actually emits;
- current configuration examples expose only controls the current parser/runtime actually honors.

### Future flexible-fidelity authority

`CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1` remains the sole proposed implementation authority for:

- configurable `(n1,n2,n3)`;
- default `(1,3,10)`;
- independent full horizon `n`;
- `0 < n1 < n2 < n3 <= n`;
- same-trajectory continuation on the full-`n` schedule;
- full-`n` SIZE-FIDELITY1 reference semantics;
- semantic coarse/short/final-screen/production stage ownership;
- schema/configuration/reporting migration required by Part 2.

Permanent current architecture/specification/guide/example surfaces must not explain that future transition as present product behavior or carry developer chronology merely to point at the workplan.

### Configuration truthfulness

For the current fixed generation, `campaign.toml.example` must not expose:

- `fidelity_epochs`;
- `coarse_training_epochs`;
- `short_training_epochs`;
- `final_training_epochs`;
- `screening_optimizer_seed`.

The first four are not current authoring authorities for target-size fidelity and the scalar screening seed is explicitly rejected by the current parser. `[training].max_num_epochs = 30` remains the current TRAIN2 budget authority.

### SIZE-FIDELITY1 current semantics

The current specification and Stage-11 graph must agree with executable target-size-v5 v2 behavior:

- calibration may evaluate the implemented coarse-epoch candidate set `3/4/5` as defined by runtime policy;
- short/final reference roles remain the implemented epoch-10/epoch-30 generation;
- monitor/equivalence and configured finalist-recall/boundary requirements are hard qualification criteria;
- winner recall is recorded diagnostic evidence and may be implied by default `1.0` finalist recall, but it is not a separate unconditional hard predicate unless executable policy is changed in Part 2;
- no current spec explains future `(1,3,10)/n` behavior or references Part 2 implementation chronology.

### Active-workplan precedence

Every older still-active workplan that freezes fixed target-size fidelity requirements must contain one narrow precedence notice with this semantic trigger:

> When implementation under `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1` begins, that workplan supersedes this plan only on the target-size fidelity epoch/state/schema/configuration surface. Unrelated requirements remain authoritative.

Do not use wording such as “when ... is implemented” that could defer supersession until completion and create a circular constraint.

### Regression integrity

Documentation tests that intentionally exercise the package/public API must continue importing/testing the real package and public exports. Do not replace package/API assertions with source-text searches merely because optional dependencies are unavailable in the current environment.

Dependency-independent documentation/graph assertions may be added or retained, but they complement rather than weaken runtime/public-interface coverage.

### Historical and publication integrity

- Historical/archive documents remain truthful and are not rewritten merely to erase `3/10/30` history.
- Canonical editable documentation sources remain authoritative over generated descendants.
- Tracked generated artifacts must be regenerated only when their authoritative source changed; if the corrected current source returns to the already tracked fixed-runtime content, byte-identical existing artifacts are valid and should not be churned.

## Delegated mechanics

Implementation may choose exact sentence structure, placement of precedence notices near the top of affected workplans, and whether a dependency-independent negative assertion is expressed as a direct test or a small helper, provided the frozen authority and test-strength requirements above are preserved.

## Reopen only on evidence

Reopen design only if repository inspection proves one of the following:

- current runtime actually accepts a different configuration surface than reviewed;
- current SIZE-FIDELITY1 executable hard criteria differ materially from the reviewed reducer/policy;
- an older active workplan has a governed requirement that cannot be narrowed without changing unrelated accepted behavior;
- a generated artifact cannot be reconciled through its canonical source chain.

Do not reopen the accepted flexible-fidelity architecture merely because current runtime remains fixed before Part 2.

## Required implementation obligations

### O1 — Restore current-vs-proposed authority separation

Required end state:

- current architecture/specifications/guides/runbooks/examples describe the implemented fixed runtime only;
- future `(n1,n2,n3)/n` semantics remain in the flexible-fidelity active workplans until Part 2 lands;
- current permanent documents do not contain Part 2 implementation chronology or links whose only purpose is to explain a future product state.

Expected affected surfaces include the current architecture manual sources/assembled output, target-size/SIZE-FIDELITY/PERF-P2R/progress specifications, campaign/operator guides, FINAL-GPU1 material, README/current overview, and current machine-readable dependency graphs if any were previously transitioned.

Acceptance:

- repository search finds no current permanent-document claim that configurable `(1,3,10)/n` is implemented/current;
- future flexible semantics remain fully represented by the active Part 2 workplan;
- historical fixed-generation records remain unchanged unless a navigation label was objectively wrong.

### O2 — Make `campaign.toml.example` executable-truthful

Required end state:

- remove ineffective/rejected target-size epoch/seed authoring controls listed in the frozen configuration decision;
- preserve the actual current size-convergence controls and TRAIN2 budget authority;
- comments explain current fixed boundaries as runtime-owned behavior without naming the Part 2 workplan or proposed future schema.

Acceptance:

- TOML parses;
- forbidden keys are absent;
- `[training].max_num_epochs = 30` remains;
- static parser/policy inspection agrees with the example.

### O3 — Reconcile current SIZE-FIDELITY1 specification and Stage-11 graph

Required end state:

- maintain one current SIZE-FIDELITY1 specification that accurately describes executable target-size-v5 v2 behavior;
- remove future flexible-transition chronology from that current specification;
- reconcile the Stage-11 graph so `winner_recall_equals_1` is not an independent unconditional hard requirement unless the executable reducer enforces it;
- retain hard monitor/equivalence, configured finalist-recall, and boundary-finalist semantics actually enforced by runtime.

Acceptance:

- spec, graph, and `mdstats/training_data/size_fidelity.py` agree on hard/diagnostic roles;
- graph JSON parses;
- current spec contains no future `(1,3,10)/n` or Part 2 implementation claim.

### O4 — Eliminate active-workplan precedence ambiguity

Required end state:

- identify every still-active workplan with materially conflicting fixed target-size epoch/state/schema/configuration requirements;
- add or normalize the narrow supersession notice using the exact implementation-start semantic trigger above;
- do not supersede unrelated performance, lifecycle, resource, scientific, or acceptance requirements.

Acceptance:

- repository search of `workplans/active` finds no conflicting fixed-fidelity plan lacking the notice;
- all notices use “when implementation ... begins” semantics;
- `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1` remains active and unchanged in its scientific target.

### O5 — Restore and preserve regression-test strength

Required end state:

- documentation specification tests assert real package version/public exports where they did before Part 1;
- stale architecture revision expectations may be corrected to actual current values;
- dependency-independent tests may verify current-vs-proposed authority, config absence, and graph semantics;
- unavailable ASE or other optional dependencies are reported as unexecuted checks, never converted into weaker permanent tests.

Acceptance:

- touched test files compile;
- source inspection confirms package/public API assertions remain real imports/attribute checks;
- execute the affected documentation tests when dependencies are available; otherwise record exact collection dependency failure without counting it as pass.

### O6 — Publication and final absence closure

Required end state:

- canonical architecture assembly equals the tracked assembled Markdown;
- tracked PDF/source manifest hashes remain correct;
- no generated artifact contains semantics different from its authoritative source;
- no unnecessary PDF churn is introduced when the fixed-runtime source matches existing tracked output.

Acceptance:

- `git diff --check` equivalent whitespace validation passes on the assembled candidate;
- changed Markdown links resolve within repository scope;
- TOML/JSON parse checks pass;
- generated-source equality/hash checks pass;
- final current-document search finds no proposed-flexible implementation claims or Part 2 chronology outside active workplans.

## Implementation sequence

### C0 — Remote baseline reconciliation

Inspect the remote branch rather than assuming any local patch is present. Re-derive the affected file set from current remote content and this workplan.

Close when the actual branch state and all conflicting current/active authorities are enumerated.

### C1 — Current-document/configuration correction

Implement O1 and O2 together because they establish one coherent current-vs-proposed authority boundary.

Run TOML/JSON/Markdown/static authority checks before proceeding.

### C2 — SIZE-FIDELITY1/graph semantic reconciliation

Implement O3 and compare the resulting current spec/graph against executable `size_fidelity.py` hard criteria.

Run graph parsing and targeted semantic assertions.

### C3 — Active-workplan precedence normalization

Implement O4 across the complete conflicting active-plan set.

Run an absence/consistency search over `workplans/active`.

### C4 — Regression/publication closure

Implement O5/O6, re-derive the final affected surface, run all available affected checks, and explicitly record unavailable dependency-bound tests.

No production/GPU qualification is required because Part 1 changes no executable MLFF behavior.

### C5 — Part 1 lifecycle closeout

After all obligations pass:

- archive this closeout workplan and `DOC-MLFF-FLEXIBLE-FIDELITY-EPOCH-CONTRACT-V1` according to repository workplan conventions;
- keep `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1` active for Part 2;
- ensure no archived Part 1 plan is referenced as current product authority.

## Final acceptance

Part 1 is complete only when all of the following are true on one assembled remote candidate:

1. current documentation is truthful to the fixed `3/10/30` executable generation;
2. future flexible-fidelity semantics are owned only by active Part 2 workplan authority;
3. current configuration examples expose no ignored/rejected target-size epoch or scalar-seed controls;
4. current SIZE-FIDELITY1 spec/graph match executable v2 hard criteria and diagnostic roles;
5. every conflicting active workplan has the unambiguous implementation-start supersession boundary;
6. permanent regression tests are no weaker than the pre-Part-1 public/package checks;
7. all available affected documentation/configuration/graph/publication checks pass, and unavailable dependency-bound tests are explicitly reported as unexecuted;
8. Part 1 workplans are archived and Part 2 remains active.

No additional architecture search or production qualification is required unless a stated redesign trigger fires.
