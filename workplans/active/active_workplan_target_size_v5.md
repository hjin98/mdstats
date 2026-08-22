# Active Workplan — Clean Fixed-Ladder Target-Size Selection

**Status:** Active / implementation-ready  
**Design state:** Frozen after final software-design review  
**Scope:** MLFF target-size selection path in `mdstats`  
**Priority:** Architecture and ownership correctness first; qualification adapts afterward and must not block this redesign.

## 1. Objective

Replace the current mixed legacy/current target-size workflow with one clean, authoritative production path:

```text
FEAS1
  -> MVIDX1
  -> MVSEL2
  -> REPAIR2 / MVSTATE2
  -> MVQUAL
  -> qualified fixed-size population Q
  -> TargetSizeStudyPolicy + TRAIN2
       epoch 3  -> epoch 10 -> epoch 30
  -> selected_target_size
  -> selected REPAIR2 prefix / production target corpus
  -> held-out CV / EVAL / VERIFY
```

The redesign must eliminate structural dependence on legacy target-ladder generation, migration, rescue, and downstream size-selection machinery. Existing useful ranking/evidence logic may be reused, but there must be only one semantic authority for target-size selection.

## 2. Root cause

The current implementation mixes two incompatible ownership models:

1. the newer fixed eight-size qualification/halving path; and
2. the older `TARGET-DATA2C` / active-ladder / migration / rescue topology.

As a result, a correct fixed-ladder result can be abandoned or superseded by legacy ladder state. Downstream verification can also participate in size-state advancement, which violates the intended architecture: target-size selection must finish before held-out protocol validation begins.

This is an ownership and dependency-direction defect, not a missing algorithm. The existing 3/10/30 successive-fidelity machinery is broadly sufficient once detached from obsolete ladder semantics.

## 3. Canonical data and mathematical contract

### 3.1 Fixed nominal size population

The only production target-size candidates are

\[
\mathcal N_0 = (128, 256, 512, 1024, 2048, 4096, 8192, 16384).
\]

No runtime-generated intermediate, rescue, or larger target sizes are allowed.

### 3.2 Candidate membership

REPAIR2 owns the master target order `R`. Candidate corpus membership is defined only by prefixes:

\[
T_N = R[:N].
\]

No target-size subsystem may reorder, independently resample, repair, or synthesize candidate membership.

### 3.3 Qualification authority

MVQUAL is the sole hard eligibility authority. Define

\[
\mathcal Q = \{N \in \mathcal N_0 : T_N \text{ is materializable and MVQUAL-qualified}\}.
\]

Let

\[
q = |\mathcal Q|.
\]

The target-size study must not perform a second qualification stage or duplicate MVQUAL semantics.

### 3.4 Successive-fidelity funnel

If

\[
q < 3,
\]

the study terminates with

```text
insufficient_qualified_sizes
```

Otherwise:

\[
q
\xrightarrow{\text{epoch 3}}
\min(q,4)
\xrightarrow{\text{epoch 10}}
2
\xrightarrow{\text{epoch 30}}
1.
\]

Required cases include:

```text
q = 3  -> 3 -> 3 -> 2 -> 1
q = 4  -> 4 -> 4 -> 2 -> 1
q = 5  -> 5 -> 4 -> 2 -> 1
...
q = 8  -> 8 -> 4 -> 2 -> 1
```

The former hard minimum of four qualifiers is retired.

### 3.5 Continuation semantics

A surviving candidate must continue from epoch 3 to epoch 10 to epoch 30 without semantic restart. Preserve the exact continuation lineage required for scientific comparability, including at minimum:

- model/checkpoint lineage;
- optimizer state where part of the training contract;
- RNG state / deterministic seed lineage;
- training schedule identity;
- candidate data identity.

The later fidelity stage must represent continuation of the same candidate training trajectory, not an independent retraining experiment that merely uses the same target size.

### 3.6 Fixed ceiling

`16384` is the hard production ceiling.

If the selected or boundary-best candidate is `16384` and the convergence policy determines that the study remains boundary-nonconverged, terminate with a dedicated state such as

```text
nonconverged_at_fixed_ceiling
```

Do not synthesize `>16384` sizes and do not invoke rescue generation.

## 4. Ownership and dependency rules

### 4.1 Sole current target-size authority

The current target-size plan must be conceptually constructed from:

```text
TargetSizeStudyPlan
  <- REPAIR2 authority
  <- MVQUAL authority
  <- TargetSizeStudyPolicy
```

It must not depend structurally on `TargetDataLadderPlan`, `TARGET-DATA2C`, migration provenance, active-ladder resolution, rescue state, or old convergence generations.

### 4.2 Separation of selection and validation

The complete 3/10/30 funnel must finish and freeze `selected_target_size` before any held-out CV, EVAL, or VERIFY stage begins.

After selection:

- downstream stages may accept or reject the resulting protocol/model;
- downstream stages may report diagnostics;
- downstream stages may not change the selected size;
- downstream stages may not revive discarded candidates;
- downstream stages may not advance target-size state;
- downstream stages may not request rescue sizes.

`selected_target_size` is immutable once terminally selected.

### 4.3 Candidate views versus production corpus

During the study, qualified target sizes may use transient prefix views, manifests, or content-addressed cache materializations corresponding exactly to `R[:N]`.

These are candidate-study artifacts only.

After selection, only the selected prefix is promoted/materialized as the production target corpus. The system must preserve a clear distinction between:

```text
candidate prefix view/materialization
```

and

```text
selected production target corpus
```

### 4.4 Persistence and restart

Do not migrate legacy derived target-size authority into the new architecture.

On contract/schema change:

- bump the relevant preparation/target-size contract version;
- reject or ignore obsolete derived target-size/migration/rescue/convergence records;
- rebuild current derived target-size authority from valid upstream current state;
- selectively reuse valid FEAS1, MVIDX1, MVSEL2, REPAIR2/MVSTATE2, and MVQUAL state where their own current contracts authenticate correctly.

The restart policy is therefore a **hard cut of obsolete derived target-size state**, not a semantic translation layer.

## 5. Legacy machinery to retire from the active runtime

The clean path must not route through or require:

- `TARGET-DATA2C` generation semantics;
- dynamic target-ladder rescue;
- active-ladder bridge/resolution as target-size authority;
- `MVMIGRATE1` promotion/migration machinery;
- migration provenance as a prerequisite for fixed-eight operation;
- `SIZE-HALVE2` as a separate campaign authority;
- `SIZE-FIDELITY2` as a production architecture gate;
- old v4 rescue fields such as `coverage_rescue_activated`, `coverage_rescue_candidate_sizes`, and `coverage_rescue_min_qualifiers`;
- downstream `with_stage_b*_evidence(...)` / `with_stage_c_evidence(...)` style advancement from CV/EVAL/VERIFY;
- any configuration, CLI, serialization, state, or tests whose only purpose is the retired topology.

Useful local algorithms may be reused only after moving them under the surviving semantic owner. Do not retain duplicate authorities merely for compatibility.

## 6. Implementation gates

### Gate 1 — Establish the sole current authority contract

Refactor the target-size data model and planner first.

Required changes:

1. Make the current target-size study consume REPAIR2 + MVQUAL + `TargetSizeStudyPolicy` directly.
2. Remove current-path dependence on `TargetDataLadderPlan` generation/version semantics.
3. Implement canonical `q >= 3` admission.
4. Preserve or consolidate useful existing 3/10/30 ranking/evidence logic under the single target-size owner.
5. Define terminal states for at least:
   - insufficient qualified sizes;
   - selected target size;
   - fixed-ceiling nonconvergence.

**Gate acceptance:** A target-size study can be constructed and reasoned about with no ladder migration/rescue object present.

### Gate 2 — Cut migration, rescue, and alternate ladder authority from preparation

Refactor campaign preparation/orchestration so the production route no longer executes the obsolete chain.

Remove the active-path dependency on operations equivalent to:

```text
_ensure_size_halve2_plan(...)
_ensure_size_fidelity2_execution_plan(...)
_ensure_target_multi_view_migration(...)
_resolve_active_target_data_ladder(...)
```

where they currently act as prerequisites or competing authorities for production target-size selection.

Preparation must terminate with:

```text
REPAIR2 current authority
MVQUAL current authority
Q frozen
target-size study ready
```

**Gate acceptance:** Legacy migration/rescue constructors may be monkeypatched to raise, and the clean preparation path still succeeds.

### Gate 3 — Move the complete 3/10/30 funnel before held-out validation

Make TRAIN2 / target-size-study execution own the entire candidate funnel:

```text
Q
 -> epoch 3 survivors <= 4
 -> epoch 10 survivors = 2
 -> epoch 30 survivor = 1
 -> selected_target_size frozen
```

Requirements:

- support `q=3` exactly as `3 -> 3 -> 2 -> 1`;
- preserve exact continuation lineage;
- use only REPAIR2 prefixes;
- allow transient candidate views/materializations;
- ensure no held-out CV/EVAL/VERIFY begins before terminal selection.

**Gate acceptance:** Once this gate completes, `selected_target_size` is immutable and no downstream component possesses an API that can advance the size funnel.

### Gate 4 — Rewire production materialization and downstream consumers

After selection:

1. promote/materialize exactly `R[:selected_target_size]` as the production target corpus;
2. authenticate the corpus against the selected REPAIR2 prefix;
3. run held-out CV/EVAL/VERIFY only after selection;
4. update downstream consumers to read the terminal target-size authority without depending on an active ladder bridge;
5. remove any verification code that derives Stage-B/Stage-C size-selection evidence or mutates convergence state.

**Gate acceptance:** Held-out validation can fail the protocol/model but cannot alter target-size selection.

### Gate 5 — State/schema cleanup and legacy deletion

Once the clean route is working:

1. bump the relevant current contract/schema version;
2. reject obsolete target-size/migration/rescue derived records on restart;
3. retain selective reuse only for independently valid upstream current authorities;
4. delete unreachable runtime implementations for the retired topology;
5. remove obsolete configuration and CLI vocabulary;
6. remove obsolete serialization/deserialization branches;
7. remove or rewrite tests that encode the retired architecture;
8. update architecture documentation and inline ownership comments to describe only the surviving production topology.

**Gate acceptance:** Repository search should not reveal a second active authority for target-size population, qualification, selection, or rescue.

### Gate 6 — Topology and regression validation

Add direct tests through the real campaign path that mechanically prove the architecture.

Mandatory acceptance invariants:

1. Candidate population is exactly `{128,256,512,1024,2048,4096,8192,16384}`.
2. No rescue/generated sizes can enter the current production path.
3. Epoch-3 entrants are exactly the MVQUAL-qualified population `Q`.
4. Candidate membership for every `N` is exactly `REPAIR2[:N]`.
5. `q=3` succeeds as `3 -> 3 -> 2 -> 1`.
6. `q<3` terminates as `insufficient_qualified_sizes`.
7. Epoch 3 -> 10 -> 30 survivors preserve exact continuation lineage.
8. Held-out CV/EVAL/VERIFY cannot begin until `selected_target_size` is terminal.
9. `selected_target_size` is immutable after selection.
10. Candidate-study materializations are distinguishable from the single promoted production target corpus.
11. Restart cannot authenticate legacy v4/rescue/migration/old convergence state as current authority.
12. Valid current FEAS1/MVIDX1/MVSEL2/REPAIR2/MVQUAL state remains selectively reusable.
13. Boundary nonconvergence at 16384 terminates at the fixed ceiling without rescue.
14. There is no hidden second hard-qualification stage after MVQUAL.
15. Legacy migration/rescue constructors monkeypatched to raise are never called by the clean workflow.
16. The production target corpus authenticates to the exact selected REPAIR2 prefix.

Prefer end-to-end or owning-layer tests over test harnesses that reimplement the selection algorithm.

## 7. Implementation guidance

The intended change is primarily **deletion, consolidation, and dependency rewiring**, not invention of a new optimization algorithm.

Prefer:

```text
reuse useful local logic
 -> consolidate under the surviving semantic owner
 -> refactor dependency direction
 -> delete obsolete authorities and compatibility paths
```

Do not preserve legacy migration/rescue abstractions merely to minimize the diff. The objective is the simpler globally correct architecture.

## 8. Non-goals

This workplan does not require:

- GPU qualification as an architectural prerequisite;
- generation of target sizes outside the fixed eight-size population;
- migration of legacy target-size derived state;
- changes to FEAS1, MVIDX1, MVSEL2, REPAIR2, or MVQUAL semantics unless an implementation defect is found while wiring their existing authorities into the clean path;
- redesign of the core ranking/equivalence metric unless implementation proves the existing policy cannot satisfy the frozen funnel semantics.

Qualification and hardware-specific validation may follow the completed architecture; they must not preserve obsolete ownership or block removal of legacy machinery.

## 9. Genuine redesign triggers

Stop and return to design only if implementation demonstrates one of the following material facts:

1. REPAIR2 cannot provide deterministic/authenticatable prefixes for all qualified sizes.
2. MVQUAL cannot expose a stable qualified fixed-size population without duplicating hard qualification downstream.
3. Existing training infrastructure cannot preserve exact continuation lineage across 3/10/30 fidelity stages without materially changing scientific semantics.
4. A downstream scientific requirement genuinely requires target-size choice to depend on held-out CV evidence, contradicting the present protocol-separation contract.
5. The fixed 16384 ceiling is shown to be scientifically invalid as a product requirement rather than merely nonconverged in a particular campaign.

Ordinary implementation difficulty, obsolete persisted state, test breakage caused by the retired topology, or GPU qualification availability are **not** redesign triggers.

## 10. Completion criterion

The work is complete when the campaign has one mechanically demonstrable production target-size topology:

```text
FEAS1 -> MVIDX1 -> MVSEL2 -> REPAIR2/MVSTATE2 -> MVQUAL
      -> Q -> 3/10/30 successive fidelity -> selected_target_size
      -> selected REPAIR2 prefix -> held-out CV/EVAL/VERIFY
```

and no legacy ladder, migration, rescue, or downstream verification path can supersede, mutate, or bypass that authority chain.
