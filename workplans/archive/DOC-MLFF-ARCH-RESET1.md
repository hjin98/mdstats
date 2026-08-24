---
kind: architecture-documentation-workplan
workplan_id: DOC-MLFF-ARCH-RESET1
protocol_version: 5.2.0
status: ACTIVE
analysis_base_ref: main@36420c2fc67b832e8be5783716bba97932b80d4a
target_branch: docs/mlff-architecture-reset
supersedes_active_workplans:
  - DOC-MLFF-SIMPLIFY1
  - DOC-REPAIR2-PERF1
  - MLFF_FINAL_GPU1
---

# DOC-MLFF-ARCH-RESET1 — single-generation MLFF architecture and documentation reset

## Objective

Replace the current hybrid MLFF documentation authority with one coherent present-tense architecture and one mutually consistent set of current specifications before any further code cleanup, campaign preparation, or qualification work.

The redesign deliberately drops backward-compatibility as an architectural goal for superseded campaign generations. Existing campaigns may be restarted under the new architecture. Scientific clarity, single ownership, reproducibility, bounded resource behavior, and maintainability take precedence over preserving obsolete schemas, migration latches, readers, generated-size conventions, or alternate runtime authorities.

The documentation result must be usable in two ways at once:

1. a technically competent human should be able to read the architecture linearly and understand the scientific/statistical/computational design without reconstructing development chronology; and
2. an AI system should be able to retrieve a small authoritative section and obtain unambiguous terminology, ownership, invariants, inputs/outputs, and dependency direction without needing historical context to interpret the current system.

This plan changes documentation authority only. Product-code conformance is a later implementation task after the revised architecture/specifications are accepted and frozen.

## Diagnosis

The scientific direction has converged, but the current normative documentation still mixes multiple generations:

- current architecture names MVSEL2/REPAIR2/MVSTATE2 as new-campaign authorities while also retaining MVSEL1/REPAIR1/MVSTATE-REUSE1 readers and execution descriptions;
- SIZE-HALVE2/SIZE-FIDELITY2 describe a fixed-eight design but remain written as pre-migration control planes tied to REPAIR1 and old TARGET-DATA generations;
- MVMIGRATE1 and ADAPT-MIGRATE1 keep migration/compatibility machinery in the current specification layer even though migration is no longer a product requirement;
- DATA7 still appears to own an independent quota/FPS `TrainingSelectionPlan` while Part V assigns target-membership authority to MVSEL2/REPAIR2;
- generic size/budget records can be read as owning target-training size while monitor specifications independently use values such as target 256 and replay 512;
- the current specification index mixes current, historical, and `historical/current` documents;
- release/gate chronology and schema-transition prose appear inside documents that claim to describe only current behavior;
- the cross-cutting DATA0 contract contains repeated supersession sections and other accumulated editorial debt.

This is an authority and information-architecture defect, not merely stale prose. The documentation must be refactored rather than patched with another migration layer.

## Governing documentation model

Use exactly one current normative owner for each material contract:

```text
architecture   -> accepted current structure, ownership, durable scientific/algorithmic invariants
specification  -> exact current behavior, schemas, policies, numerical rules, failure semantics
methods/theory -> explanatory material; non-normative unless explicitly stated otherwise
guide/runbook  -> current task-oriented operation and interpretation
workplan       -> temporary proposed transition
history        -> completed chronology and superseded designs
audits/benchmarks/release evidence -> evidence, not semantic authority
```

Current architecture/specifications are written as though the accepted current system had been designed in its final form from the beginning. Do not preserve an old explanation and append exceptions, migration notes, or newer overrides.

Historical material may explain why a superseded design existed, but no current document may require historical knowledge to determine present behavior.

## Frozen target architecture

The following decisions are the design baseline for this documentation revision. A later change requires an explicit design decision rather than editorial reinterpretation.

### 1. One current target-selection generation

The current multi-view chain is:

```text
selection inputs
    -> FEAS1
    -> MVIDX1
    -> MVSEL2
    -> REPAIR2 / MVSTATE2
    -> MVQUAL
    -> target-size study
    -> selected target size
```

MVSEL2 is the sole current scientific ordering authority. REPAIR2 is the sole current repair authority. MVSTATE2 is reconstructible continuation state. MVQUAL independently verifies hard coverage/obligation evidence.

MVSEL1, REPAIR1, MVSTATE-REUSE1, generated-size rescue, old TARGET-DATA generations, and migration machinery are historical designs, not alternate current paths.

### 2. DATA7 prepares selection inputs; it does not select target membership

DATA7 continues to own fold/final-domain fitted products such as feature transforms/metrics, atomic-reference fits, training objective/weights, difficulty evidence, condition/provenance structure, and the inputs needed by multi-view selection.

DATA7 must not own a second target-membership order. The old quota/FPS `TrainingSelectionPlan` authority is superseded. Still-useful representative, diversity, environment, event, and difficulty concepts become inputs, hard obligations, or objective terms of the one MVSEL2 policy.

### 3. One target-size authority

Introduce one conceptual owner, `TargetSizeStudyPolicy`, for scientific target-training sizes. Monitor budgets and target sizes are distinct record families and cannot substitute for one another.

At minimum distinguish:

```text
TargetSizeStudyPolicy
OnlineTargetMonitorPolicy
ReplayMonitorPolicy
SizeScreenEvaluationPolicy (if a separate evaluation subset remains materially justified)
```

A replay-monitor size of 512 is never a target-size ladder merely because the integer is equal.

### 4. Separate available, nominal, materializable, qualified, and selected sizes

For required training domain `d`,

$$
N_{\mathrm{available},d}=|\mathcal D_{\mathrm{eligible},d}|.
$$

The nominal target-size population is fixed:

$$
\mathcal N_0=\{128,256,512,1024,2048,4096,8192,16384\}.
$$

No dynamic rescue/intermediate size is created.

The materializable common population is

$$
\mathcal N_M=\{N\in\mathcal N_0: N\le \min_d N_{\mathrm{available},d}\},
$$

where the required domains include the final-development domain and every required cross-validation gradient-training domain.

Independent MVQUAL evidence defines the qualified population

$$
\mathcal Q=\{N\in\mathcal N_M:\text{all hard requirements pass in every required domain}\}.
$$

The final choice must satisfy

$$
N_{\mathrm{selected}}\in\mathcal Q\subseteq\mathcal N_0.
$$

An arbitrary pool cardinality such as 13,568 may be `N_available`; it can never silently become `N_selected`.

### 5. Domain-local membership, protocol-global size

Each fold/final training domain constructs its own leakage-safe MVSEL2/REPAIR2 order from only the evidence authorized for that domain:

$$
D_{d,N}=\pi_d[:N].
$$

The selected size `N_selected` is one protocol hyperparameter shared across required training domains; the actual frame membership remains domain-local.

### 6. One repaired order per domain

REPAIR2 publishes one authoritative ordered sequence per domain. Every rung is a prefix view of that same sequence. Do not persist or independently repair unrelated copies of each rung.

### 7. Coverage monotonicity is an invariant

Because larger rungs are strict supersets of smaller rungs under one nested order, hard coverage/obligation satisfaction cannot regress solely by increasing `N`. Qualified sizes therefore form a contiguous suffix of the materializable ladder. A pass/fail/pass pattern is an invariant violation indicating broken nesting, qualification, identity, or numerical logic; the funnel must not work around it.

### 8. Size study uses development/model-selection evidence, not held-out CV evaluation

Target size is selected using the authorized development/model-selection evidence, including the common target monitor. Held-out cross-validation evaluation folds do not choose `N_selected`; otherwise they cease to be independent protocol-validation evidence unless nested CV is introduced.

After `N_selected` is frozen, protocol-matched cross-validation validates the complete protocol containing that size. Locked tests remain sealed throughout size selection and CV.

### 9. Dedicated size-study training control

The size study compares common training trajectories at exact fidelity boundaries:

```text
0 -> 3 epochs
3 -> 10 epochs
10 -> 30 epochs
```

The epoch-10 continuation authenticates the exact epoch-3 model/optimizer/RNG parent; epoch 30 continues epoch 10. Size candidates use the same foundation, replay semantics, objective, optimizer/LR schedule, exposure policy, precision/backend, and frozen seed set.

Ordinary target-success early stopping is disabled during the size experiment because candidates must reach comparable fidelity boundaries. Hard numerical/scientific failure may still reject a candidate. Normal production/CV stopping policy resumes after target size is frozen.

### 10. Successive-fidelity funnel and paired seed comparison

Let `q=|Q|`. Require at least three qualified candidate sizes:

```text
q < 3      -> insufficient_qualified_sizes
q >= 3     -> epoch 3:  q -> min(q,4)
              epoch 10: <=4 -> 2
              epoch 30: 2 -> 1
```

Every candidate uses the same frozen optimizer/training seed set. Ranking uses paired seed-aggregated target-monitor evidence rather than comparing unrelated stochastic realizations.

At epoch 3 and epoch 10, candidates within the frozen practical-equivalence width of 1 meV/Angstrom in the primary target-force metric prefer the smaller size. Early stages do not require the final absolute force-accuracy threshold.

At epoch 30, only candidates satisfying the complete frozen hard admissibility policy may win, including applicable target/focus-group, replay-retention, energy/stress, physical-integrity, relaxation/deployment, and other mandatory constraints. Replay/integrity are constraints, not score bonuses unless a future explicit policy changes that scientific rule.

### 11. Explicit terminal outcomes

Target-size authority returns a typed decision, not merely an integer. The current outcome vocabulary must cover at least:

```text
selected(N)
insufficient_materializable_sizes
insufficient_qualified_sizes
no_admissible_finalist
nonconverged_at_available_ceiling
nonconverged_at_fixed_ceiling
hard_scientific_failure
```

If the available corpus stops below 16,384 and the largest materializable rung remains materially superior, return `nonconverged_at_available_ceiling`. If 16,384 is available and remains materially superior, return `nonconverged_at_fixed_ceiling`. Never synthesize an intermediate size to avoid a non-convergence result.

### 12. Production halving is distinct from release/algorithm qualification

Retrospectively training the complete candidate population to 30 epochs to verify survivor recall is algorithm/release qualification, not the normal scientific production path. Production executes the actual successive-fidelity funnel and does not repay eliminated candidates.

If representative qualification later shows the epoch-3/10 screens cannot reliably retain eventual finalists, revise the screening policy explicitly. Do not require every campaign to run an exhaustive parallel qualification matrix forever.

### 13. Superseded campaigns are unsupported, not migrated

Current architecture has no MVMIGRATE/ADAPT-MIGRATE state machine and no low-level legacy construction mode. After implementation conforms to this architecture, artifacts from unsupported generations fail clearly and require campaign re-preparation.

No current product requirement exists to reinterpret, migrate, or continue an obsolete campaign generation.

### 14. Bounded execution remains an architectural requirement

The scientific fixed-size ladder must not imply eight independent product-scale copies of descriptors, sparse graphs, or target datasets.

Per domain, prefer:

```text
one fitted selection-input authority
one exact neighborhood authority
one MVIDX authority
one MVSEL2/REPAIR2 master order
prefix metadata for candidate rungs
MVQUAL evidence per required prefix
training artifacts only for candidates actually authorized to train
```

Execution caches are reconstructible and bounded. Resource optimization must not alter scientific membership, coverage, ranking, or decision authority.

## Documentation structure and writing requirements

### Concept-first current narrative

Architecture headings and prose should introduce the scientific/computational concept before internal stage identifiers. Prefer:

```text
Multi-view target subset selection (MVSEL2)
```

over a section whose meaning is only `MVSEL2`.

DATA*/MV*/ADAPT* identifiers remain useful for traceability in specifications and code mapping, but they must not become the ontology a reader must memorize before understanding the workflow.

### Progressive disclosure

The architecture manual should flow approximately as:

1. purpose and authority;
2. source/evidence/statistical concepts;
3. fitted preparation and role separation;
4. target subset construction and target-size study;
5. training/evaluation/deployment;
6. execution/performance/restart architecture;
7. ownership/extension boundaries;
8. references.

Chapter numbering/file names may be changed when doing so materially improves the conceptual hierarchy. Do not preserve an obsolete section order merely to minimize the diff.

### Stable terminology and local context

Use one preferred current term per concept. Define symbols close to first use. State units, tolerances, stochastic semantics, nesting assumptions, and failure meaning where they matter.

Each major architecture/specification section should make its ownership clear: what it owns, what it consumes, what it emits, and what it explicitly does not own.

For AI retrieval, each chapter should contain enough local context to interpret its equations and dependency direction without requiring chronology or an implicit `latest override` from another document.

### Avoid duplicate authority

Architecture owns durable structure/invariants; specifications own detailed exact policy and schema. A change-sensitive constant should have one normative owner. Architecture may explain a spec-owned value only when the ownership remains unambiguous and the explanation cannot become a second independent contract.

Methods/theory documents may explain the rationale but must point back to the current normative owner rather than restating a competing policy.

### Canonical source chain

The editable architecture sources remain the chapter files under `docs/arch_manuals/mlff_training_data/` unless this gate deliberately revises that source graph. The assembled Markdown and PDF are derived products and must be regenerated from canonical sources rather than patched independently.

## Superseded-document retention policy

Do not move every obsolete file into history mechanically. Classify superseded material by information value.

### Preserve/consolidate when useful

Create a small number of concept-oriented historical records when old designs contain lasting engineering context, for example:

- evolution from generated/free-form target sizes to fixed nested size study;
- MVSEL1/REPAIR1 eager/inverse state and why MVSEL2/REPAIR2 replaced it;
- migration/compatibility layers that once connected campaign generations;
- rejected scaling/qualification approaches whose failure explains an important current design constraint.

Prefer consolidation over one historical file per implementation gate.

### Preserve an exact snapshot only when necessary

If an old schema/specification is materially needed to interpret durable release evidence or reproduce a past result, move/reclassify an exact snapshot under `docs/history/mlff/` and mark it non-normative.

### Discard inconsequential superseded material

Gate bookkeeping, duplicate migration prose, obsolete future plans, duplicated PDFs, and specs whose only unique content is already preserved in Git history or a consolidated historical explanation may be deleted from the current tree rather than archived again.

Deletion from the current tree does not rewrite Git history.

## Scope

Included:

- `docs/arch_manuals/mlff_training_data/` canonical chapters;
- assembled `docs/arch_manuals/mlff_training_data_architecture.md` and its generated PDF/source-chain metadata as applicable;
- `docs/specs/training_data/README.md` and every MLFF specification whose current/historical classification or semantics are affected;
- the cross-cutting MLFF system contract;
- current documentation/dependency/navigation indexes and diagrams directly affected by the reset;
- relevant MLFF history documents and history indexes;
- architecture/manual build tooling only where needed to keep the canonical source chain reproducible.

Excluded from this workplan:

- changes to `mdstats/` product behavior;
- compatibility implementation, schema migration, or campaign conversion code;
- training/evaluation execution;
- GPU qualification;
- performance tuning;
- large real-data qualification;
- unrelated analysis architecture/documentation.

Implementation mismatches discovered while revising documentation are recorded as inputs for the later code-conformance plan; they do not cause the architecture to regress toward obsolete behavior merely to match current code.

## Gates

### A0 — authority inventory and semantic-preservation map

**Goal:** establish exactly what is current, superseded, duplicated, or historically valuable before rewriting.

**Work:**

- inspect all canonical MLFF architecture chapters, the assembled manual, current training-data specifications, current indexes, build/source-chain rules, and directly relevant history;
- classify every normative-looking document as `current-owner`, `merge/rewrite`, `historical-useful`, or `discardable`;
- identify every place that currently claims ownership of target membership, target size, monitor size, selection ordering, repair state, migration, stopping, and campaign authority;
- extract still-valid scientific/statistical/execution requirements that must survive the refactor;
- identify change-sensitive constants and choose one normative owner for each;
- identify generated/derived documents so edits occur at the canonical source.

**Acceptance:**

- no material current contract has two intended normative owners;
- every superseded document has a deliberate retain/consolidate/discard decision;
- still-valid requirements are accounted for before large editorial deletion;
- no implementation behavior is silently promoted to architecture merely because it exists in code.

### A1 — freeze the single-generation normative model

**Goal:** rewrite the cross-cutting ownership/dependency model around the frozen target architecture above.

**Work:**

- define the current end-to-end conceptual dependency graph from source evidence through deployment;
- establish DATA7 as fitted/selection-input preparation rather than target-membership authority;
- establish MVSEL2/REPAIR2/MVSTATE2/MVQUAL as the sole current multi-view chain;
- establish `TargetSizeStudyPolicy` and the distinct size concepts/monitor types;
- establish domain-local membership with protocol-global selected size;
- establish size-study evidence roles, fixed fidelity, paired seeds, ranking, hard admissibility, non-convergence, and failure outcomes;
- remove migration/backward-compatibility as a current architectural requirement;
- state bounded resource/materialization invariants.

**Acceptance:**

- one clear authority exists for every scientific decision;
- the dependency graph contains no alternate legacy/migration path;
- old campaigns are either current-generation compatible or explicitly unsupported; there is no third interpretation state;
- all formulas/terms needed to distinguish available/candidate/qualified/selected data are unambiguous.

### A2 — refactor the architecture manual for human and AI comprehension

**Goal:** produce one coherent present-tense architecture document rather than a chronology-shaped patchwork.

**Work:**

- rewrite/reorder/merge/split canonical chapters as needed for natural conceptual flow;
- replace v1/legacy/migration prose with the current design, moving historical explanation out of the normative manual;
- introduce concept-first names and stable terminology;
- add/repair concise dependency/data-flow figures or pseudocode only where they materially improve comprehension;
- ensure major sections state motivation, ownership, inputs/outputs, invariants, algorithmic basis, assumptions, failure behavior, and scaling where relevant;
- update front matter, reading/context retrieval index, glossary/notation, ownership summary, and references;
- remove release/gate chronology from current architectural narrative.

**Acceptance:**

- a technically competent reader can follow the current workflow linearly without learning old generations first;
- an AI retrieval of one relevant chapter obtains enough local context to identify the current owner and dependency direction;
- no current chapter calls MVSEL1/REPAIR1/MVMIGRATE/legacy schema handling a current authority;
- no section requires a later amendment/caveat to reverse an earlier explanation.

### A3 — rebuild the current specification layer

**Goal:** make `docs/specs/training_data/` contain current behavior only, with exact contracts aligned to the architecture.

**Work:**

- rewrite/rename/consolidate specifications whose names or structure are implementation-gate chronology rather than durable concepts;
- remove DATA7 target-membership selection authority while preserving its fitted-preparation responsibilities;
- create or consolidate a durable target-subset/target-size-study specification that owns exact ladder, qualification, fidelity, ranking, outcomes, and identity contracts;
- make monitor policies type/ownership-distinct from target-size policy;
- rewrite MVSEL2/REPAIR2/MVSTATE2 current contracts without v1 runtime compatibility requirements;
- remove MVMIGRATE/ADAPT-MIGRATE and obsolete generation-readability requirements from current specifications;
- deduplicate and simplify the cross-cutting system contract;
- rebuild `docs/specs/training_data/README.md` so every listed entry is genuinely current and no entry is labeled `historical/current`;
- preserve external runtime locks (for example a currently supported MACE version) only when they remain actual current product requirements rather than historical release facts.

**Acceptance:**

- current spec index contains no historical/migration-only documents;
- architecture and narrow specs have compatible ownership with no duplicate current authority;
- each current spec is present-tense and concept-oriented enough to understand without release chronology;
- unsupported historical schema behavior is not promised by current specifications.

### A4 — consolidate historical design context and remove inconsequential residue

**Goal:** preserve useful engineering history without recreating a parallel historical specification tree.

**Work:**

- consolidate important superseded selector/repair/size/migration rationale into a small number of historical design narratives;
- retain exact historical snapshots only when needed to interpret durable release evidence;
- move/reclassify useful old documents under `docs/history/mlff/`;
- delete duplicate/inconsequential obsolete current docs and generated duplicates whose information is already preserved elsewhere;
- repair directly affected historical/current indexes and links;
- make every historical document visibly non-normative.

**Acceptance:**

- useful rationale and development lessons remain discoverable;
- history does not masquerade as current authority;
- the repository does not retain one historical file per obsolete gate merely for completeness;
- no current navigation requires a reader to consult history to determine present behavior.

### A5 — publication and semantic consistency review

**Goal:** prove that the revised documentation source chain is mechanically sound and semantically single-generation.

**Work:**

- rebuild the assembled architecture Markdown and PDF from canonical sources;
- regenerate other tracked derived documents only where repository policy requires them;
- validate directly affected links/indexes/source-chain relationships;
- search current architecture/specs for stale authority markers such as MVSEL1, REPAIR1, MVSTATE-REUSE1, MVMIGRATE1, dynamic rescue sizes, old TARGET-DATA generation authority, `legacy construction semantics`, and `historical/current` classification;
- inspect any remaining occurrence and allow it only if it is a non-authoritative rejection/contrast that genuinely improves current understanding; otherwise remove/move it;
- visually inspect materially changed PDF pages for heading/equation/table/code/layout quality;
- perform an independent software-design review of ownership, scientific fidelity, statistical role separation, size semantics, resource feasibility, and total conceptual complexity;
- perform a software-documentation review of narrative flow, terminology, progressive disclosure, local context, source-chain integrity, and human/AI retrievability.

**Acceptance:**

- canonical-source build succeeds and tracked generated outputs match it;
- current docs have one generation and one owner per material contract;
- no stale migration/compatibility promise survives accidentally;
- mathematical notation and policy terms are internally consistent;
- no unresolved material semantic contradiction remains.

### A6 — freeze architecture and hand off implementation conformance

**Goal:** establish the revised documentation as the reference against which code will be judged.

**Work:**

- record the new architecture revision/current-specification state after A5 acceptance;
- summarize implementation mismatches discovered during documentation review without fixing them in this workplan;
- create a separate implementation workplan for code conformance, deletion of obsolete authorities, and bounded qualification;
- archive this workplan after the architecture/specification transition is accepted.

**Acceptance:**

- implementation can be reviewed against a single unambiguous normative design;
- no code-cleanup task needs to choose between competing current specifications;
- the next workplan can delete/refactor obsolete implementation rather than adding another compatibility layer.

## Architecture acceptance checklist

The revision is not complete unless all of the following are true:

- [ ] one current target selector: MVSEL2;
- [ ] one current repair authority: REPAIR2;
- [ ] one current continuation state: MVSTATE2;
- [ ] one independent target-qualification authority: MVQUAL;
- [ ] DATA7 does not independently choose target membership;
- [ ] target size and monitor sizes have distinct owners/types;
- [ ] available/materializable/qualified/selected size concepts are explicit;
- [ ] no arbitrary pool cardinality can become a selected training size;
- [ ] domain-local membership and protocol-global size are explicit;
- [ ] target-size study does not consume held-out CV evaluation or locked-test evidence;
- [ ] fixed 3/10/30 continuation and common seed semantics are explicit;
- [ ] the `q >= 3`, `q -> min(q,4) -> 2 -> 1` funnel is explicit;
- [ ] 1 meV/Angstrom practical equivalence and smaller-size preference are explicit;
- [ ] terminal non-convergence/failure outcomes are explicit;
- [ ] hard-coverage monotonicity is an invariant;
- [ ] one repaired master order defines all prefixes;
- [ ] exhaustive survivor-recall calibration is release/algorithm qualification, not ordinary production;
- [ ] migration/legacy campaign execution is absent from the current architecture;
- [ ] old campaign artifacts are unsupported rather than automatically migrated;
- [ ] fixed-size study does not require eight duplicated product-scale data/graph states;
- [ ] current spec index contains current behavior only;
- [ ] superseded designs are consolidated into history only where useful;
- [ ] current architecture can be understood without historical context;
- [ ] canonical Markdown/PDF source chain is synchronized and readable.

## Risks and redesign triggers

Stop and return to design review if documentation reconciliation reveals any of the following:

- a supposedly superseded component owns a unique scientific requirement not represented by the new architecture;
- two current statistical roles cannot be separated without changing the scientific experiment;
- the global selected-size / fold-local membership model conflicts with a required validation guarantee;
- the fixed ladder cannot be materialized across required domains under realistic corpus sizes often enough to make the method usable;
- the 3/10/30 screen requires held-out evidence to be scientifically defensible;
- preserving exact multi-view semantics under the target resource envelope would require a materially different data representation or algorithm;
- current MACE/runtime behavior imposes a material constraint that the architecture has not accounted for.

Do not respond to those findings by restoring old compatibility machinery automatically. Resolve the current scientific/engineering requirement directly.

## Closeout

This architecture reset intentionally supersedes the previously active simplification, REPAIR2 performance, and FINAL-GPU1 workplans. Their durable observations remain in `workplans/archive/` as historical coordination records, but none may control the redesign.

After this plan is accepted, the next phase starts from the frozen architecture, inspects the implementation for conformance, and removes or refactors obsolete product machinery. No previous campaign is required to remain restart-compatible across that implementation transition.
