---
kind: implementation-workplan
workplan_id: DOC-MLFF-FLEXIBLE-FIDELITY-EPOCH-CONTRACT-V1
protocol_version: 5.4.0
---

# MLFF Flexible-Fidelity Documentation Revision Workplan

## Objective

Rewrite the current/normative MLFF target-size documentation so that it defines a configurable three-boundary successive-fidelity screen `(n1, n2, n3)` with default `(1, 3, 10)`, independently bounded by the full TRAIN2 training horizon `n` with default `30`, with no current-documentation leakage of the former fixed `3/10/30` architecture.

This workplan is documentation-only. It establishes the normative contract that the separate codebase rework workplan must implement.

## Diagnosis

The current documentation and examples still encode the old target-size architecture as a fixed `3/10/30` funnel. The codebase currently mirrors that documentation with epoch-number-specific state names and configuration keys, and the current SIZE-FIDELITY1 description treats the third screening boundary as the eventual/reference endpoint. That coupling becomes invalid when the last screening boundary becomes `n3=10` while full TRAIN2 training remains `n=30`.

The documentation change must therefore do more than replace literals. It must establish four separate concepts consistently:

1. coarse screening boundary `n1`;
2. short screening boundary `n2`;
3. final screening boundary `n3`;
4. full TRAIN2 training horizon `n`.

The architectural invariant is:

```text
0 < n1 < n2 < n3 <= n
```

The default policy is:

```text
(n1, n2, n3) = (1, 3, 10)
n = 30
```

These are defaults, not architectural constants.

## Engineering envelope

The revised documentation must preserve the following product semantics and scientific guarantees.

### Functional/scientific contract

- Target-size screening uses exactly three ordered screening boundaries.
- Every screening checkpoint belongs to one uninterrupted TRAIN2 trajectory whose full planned horizon is `n`.
- The learning-rate schedule and all schedule-dependent identities are computed for the full `n`-epoch trajectory, not retimed independently for `n1`, `n2`, or `n3`.
- Surviving candidates continue from the authenticated checkpoint at the preceding screening boundary; they are not restarted from epoch zero.
- Discarded candidates perform no later screening work.
- Only exact configured boundary checkpoints may contribute to screening decisions.
- The target size is selected/frozen after the `n3` screening decision.
- `n3` is a screening endpoint, not the production-training endpoint.
- The selected production model trains to the independent full horizon `n`.
- SIZE-FIDELITY1 must evaluate screening decisions against evidence at full `n`, not merely at `n3`.
- When `n3 == n`, the same physical checkpoint may satisfy both the final-screen endpoint and full-horizon reference role; documentation must describe this as role coincidence, not as two required training runs.

### Configuration contract

Current authoring must expose one target-size fidelity tuple and one full TRAIN2 horizon:

```toml
[target_data.size_convergence]
fidelity_epochs = [1, 3, 10]

[training]
max_num_epochs = 30
```

The old three-key screening surface:

```text
coarse_training_epochs
short_training_epochs
final_training_epochs
```

must no longer be documented as the current authoring contract. Historical/legacy configuration documentation may describe those keys only inside an explicitly marked compatibility section.

### Terminology contract

Use semantic stage names in current documentation:

- `coarse screen` / `coarse-screen` for `n1`;
- `short screen` / `short-screen` for `n2`;
- `final screen` / `final-screen` for `n3`;
- `production` / `full training` for training to `n`.

Do not use bare `final` where it could mean either the third screen or production completion.

### Historical integrity

Archived historical workplans/results may retain the former fixed `3/10/30` wording when it accurately records historical behavior. Historical text must not be rewritten to falsely imply that the old implementation already used the new contract.

The no-leakage requirement applies to current/normative documentation, generated current documentation, examples, runbooks, diagrams, and other current-facing surfaces. Historical archive exceptions must be explicit and isolated.

## Product design

The documentation authority is divided as follows.

1. The target-size architecture/specification owns the meaning of `(n1, n2, n3)` and the successive-halving state machine.
2. TRAIN2 documentation owns the meaning of the full planned training horizon `n` and the fact that screening checkpoints remain on the full `n` schedule.
3. SIZE-FIDELITY1 documentation owns calibration/qualification of shortened screening against full-horizon reference behavior.
4. PERF-P2R documentation owns execution geometry and cost accounting, with screening work and production work explicitly separated.
5. Campaign configuration documentation exposes only one fidelity tuple plus the existing full TRAIN2 epoch budget for current authoring.
6. CLI/operator documentation owns the distinction between current stage progress and full schedule horizon.

The normative screening flow is:

```text
all qualified candidates: 0 -> n1
        |
        v  coarse halving
survivors:              n1 -> n2
        |
        v  short finalist selection
finalists:              n2 -> n3
        |
        v  final-screen target-size selection/freeze
selected target size

production model:        0 -> n
```

The final-screen `n3` checkpoint is therefore selection evidence; it is not automatically the production model.

## Implementation authority

### Frozen

The following decisions are fixed by this workplan and are not delegated to documentation implementation:

- The configurable screening tuple is exactly three positive strictly increasing integer epochs.
- The default tuple is `(1, 3, 10)`.
- The full TRAIN2 horizon remains independently configurable and defaults to `30`.
- The invariant is `0 < n1 < n2 < n3 <= n`.
- Screening checkpoints remain on the full `n` schedule.
- Production training remains distinct from target-size screening and runs to `n`.
- SIZE-FIDELITY1 uses full `n` as the eventual/reference endpoint.
- The current public configuration contract uses `fidelity_epochs` plus `[training].max_num_epochs`.
- The old three screening epoch keys are legacy-only documentation.
- Current documentation must use semantic stage names and must not encode epoch numbers in API/state terminology.
- Current generated documentation must be regenerated after authoritative sources change.
- Historical archived records remain truthful and may retain old terminology only as history.

### Delegated

The implementer may choose local wording, table layout, diagram formatting, and cross-link placement when those choices preserve the frozen semantics above and repository documentation conventions.

### Reopen only on evidence

Reopen only the affected documentation design surface if repository inspection proves that a different document is the actual normative authority, if the current configuration hierarchy differs materially from the reviewed branch, or if a generated-document pipeline cannot represent the frozen contract without changing its source authority. Do not reopen the epoch architecture merely because old prose or code still reflects the old implementation.

## Initially expected affected documentation surface

At minimum inspect and reconcile:

- `docs/arch_manuals/mlff_training_data/50_target_multiview.md`;
- `docs/specs/training_data/mlff_target_subset_size_study_spec.md`;
- TRAIN2/EVAL2 documentation that describes planned epochs or screening checkpoints;
- SIZE-FIDELITY1 documentation/specification/runbooks;
- PERF-P2R documentation/specification/runbooks;
- MLFF campaign/operator documentation;
- configuration reference material;
- `campaign.toml.example` comments and target-size example keys;
- README/current overview text that states target-size epoch behavior;
- current active workplans that are themselves referenced as current architecture authority;
- diagrams/tables/state-transition descriptions;
- generated current PDFs or other derived documentation.

This list is provisional. The implementer must perform a full repository documentation search and add every current/normative affected surface discovered before declaring completion.

## Task-specific acceptance

### Documentation inventory acceptance

Before editing, produce an implementation-local inventory of every occurrence or semantic equivalent of the old fixed contract in current documentation. Search at least for:

```text
3/10/30
3 -> 10 -> 30
3 ->10 ->30
(3, 10, 30)
epoch-3
epoch 3
epoch-10
epoch 10
epoch-30
epoch 30
coarse_training_epochs
short_training_epochs
final_training_epochs
awaiting_epoch_3
awaiting_epoch_10
awaiting_epoch_30
```

Also inspect prose that says the last target-size screen is the final/full training endpoint without using those exact strings.

Each hit must be classified as one of:

- current/normative: revise;
- generated derivative: revise source and regenerate;
- historical/archive: preserve as historical truth;
- compatibility-only: retain only with explicit legacy labeling.

### Normative target-size acceptance

The current target-size architecture/spec must state all of the following explicitly:

- exactly three configurable boundaries `(n1, n2, n3)`;
- default `(1, 3, 10)`;
- independent full horizon `n`, default `30`;
- strict ordering and `n3 <= n`;
- exact-boundary evidence only;
- same uninterrupted full-`n` TRAIN2 trajectory for screening continuation;
- semantic stage names;
- target-size freeze after final screen;
- production training to `n` is a separate stage.

### SIZE-FIDELITY1 acceptance

The current SIZE-FIDELITY1 documentation must explicitly define:

```text
screening endpoints: n1, n2, n3
reference endpoint:  n
```

It must say that qualification asks whether shortened screening preserves the scientifically relevant outcome implied by the full `n` trajectory. It must not call `n3` the eventual/full endpoint unless `n3 == n` in a specific configured campaign.

### PERF-P2R acceptance

Current PERF-P2R documentation must describe four distinct execution concepts:

- coarse screening segment `0 -> n1`;
- short continuation `n1 -> n2`;
- final-screen continuation `n2 -> n3`;
- production training `0 -> n`.

Screening cost and production cost must not share a variable/term named `final_training_epochs`.

### Configuration acceptance

Current configuration examples and current authoring documentation must use:

```toml
[target_data.size_convergence]
fidelity_epochs = [1, 3, 10]

[training]
max_num_epochs = 30
```

The old three screening keys may appear only in an explicitly labeled legacy/migration section.

### Reporter/operator acceptance

Document stage progress and full schedule horizon separately. Examples must resemble:

```text
stage=coarse-screen; phase=epoch 1/1; schedule_horizon=30
stage=short-screen; phase=epoch 2/3; schedule_horizon=30
stage=final-screen; phase=epoch 7/10; schedule_horizon=30
stage=production; phase=epoch 17/30
```

The exact punctuation may follow the implemented CLI format, but the semantic distinction is required.

### Legacy-leak acceptance

After revision/regeneration, run a full-tree documentation search. In current/normative documentation there must be no unqualified fixed-policy statements such as:

```text
3/10/30
(3, 10, 30)
epoch-3 target-size screen
epoch-10 finalist selection
epoch-30 size selection
final_training_epochs  # meaning the third screening boundary
```

The literal number `30` is not globally banned because it remains the default `n` and may be unrelated elsewhere.

Every remaining old-policy hit must be demonstrably inside an archived/historical or explicitly legacy-compatibility surface.

### Cross-document consistency acceptance

No current document may simultaneously claim any of the following contradictions:

- `n3` is configurable but fixed at 30;
- the final screen is at `n3` while production also necessarily stops at `n3`;
- screening checkpoints use shortened independent LR schedules;
- SIZE-FIDELITY1 compares early screening only against `n3` when `n3 < n`;
- current campaigns should author the old three epoch keys.

Production qualification: unnecessary for this documentation-only workplan. Documentation must not claim that the new behavior is implemented until the codebase rework workplan is completed.

## Implementation sequence

### D0 — Inventory and authority classification

Actions:

1. Search all documentation, examples, runbooks, generated-current-doc sources, and current workplans for fixed-epoch terminology and semantic equivalents.
2. Identify the normative authority for target-size selection, TRAIN2 planned epochs, SIZE-FIDELITY1, PERF-P2R, campaign configuration, and CLI reporting.
3. Classify each old-policy occurrence as current, generated, historical, or compatibility-only.

Acceptance before proceeding:

- every current authoritative surface is identified;
- historical exceptions are explicitly known rather than accidentally skipped.

### D1 — Rewrite the normative architecture and specification

Actions:

1. Replace fixed `3/10/30` architecture language with `(n1, n2, n3)`.
2. State default `(1,3,10)` and independent `n=30` as defaults only.
3. Add the invariant `0 < n1 < n2 < n3 <= n`.
4. Rewrite state-machine diagrams/tables using semantic stages.
5. State same-trajectory continuation and exact-boundary evidence rules.
6. State target-size freeze after `n3` and production training to `n`.

Stage acceptance:

- reread all changed normative documents together;
- no internal contradiction between target-size selection and TRAIN2 schedule ownership;
- no current normative fixed `3/10/30` statement remains.

### D2 — Rewrite SIZE-FIDELITY1 and PERF-P2R documentation

Actions:

1. Make full `n` the SIZE-FIDELITY1 reference endpoint.
2. Explain the `n3 == n` role-coincidence edge case.
3. Separate PERF-P2R screening geometry from production geometry.
4. Rename prose concepts from numerical/final-training terminology to semantic/final-screen terminology.
5. Ensure performance examples use differences `(n2-n1)` and `(n3-n2)` for continuation work.

Stage acceptance:

- no SIZE-FIDELITY1 text uses the third screen as the full reference unless configuration makes them equal;
- no PERF-P2R text conflates `n3` with full training.

### D3 — Revise current configuration and operator documentation

Actions:

1. Replace old three-key target-size epoch authoring examples with `fidelity_epochs`.
2. Retain `[training].max_num_epochs` as the full horizon authority.
3. Move old keys to an explicitly legacy section if compatibility documentation is required.
4. Rewrite progress examples to expose current stage target separately from schedule horizon.

Stage acceptance:

- a reader can determine exactly where to configure `(n1,n2,n3)` and `n` without encountering two competing current authorities.

### D4 — Regenerate derived documentation

Actions:

1. Regenerate every current PDF/derived document affected by revised sources using the repository's documented generation mechanism.
2. Verify headings, links, tables, diagrams, and generated examples.

Stage acceptance:

- generated current artifacts contain the same contract as their sources.

### D5 — Final documentation closure

Actions:

1. Re-run the full documentation leakage search.
2. Review every remaining old-policy hit manually.
3. Verify all remaining hits are historical or explicitly legacy-only.
4. Check cross-references from current documents do not point readers to historical fixed-policy text as current authority.

Final acceptance:

- current/normative documentation is flexible-fidelity and legacy-leak-free;
- historical records remain accurate;
- this workplan can be archived only after its revised documentation contract is frozen as the implementation target for `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1`.

## Risks / redesign triggers

- A supposedly historical document is actually imported/referenced as current normative authority. Resolve authority before editing.
- A generated document has no reproducible source/generation path. Reopen only publication mechanics; do not hand-edit a generated artifact if doing so creates divergent authorities.
- Current configuration schema ownership differs materially from the reviewed `campaign.toml.example`. Reconcile with the actual parser/writer authority while preserving the frozen two-authority model: fidelity tuple plus full TRAIN2 horizon.
- Documentation discovers a scientific rule that requires a different reference endpoint than full `n`. Stop the affected SIZE-FIDELITY1 documentation stage and reopen that scientific design surface before proceeding.
