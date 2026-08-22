# TARGET-SIZE-V5-POST-REVIEW-FIX1

**Status:** Completed / archived after gated implementation on 2026-08-22
**Parent implementation plan:** `workplans/archive/TARGET_SIZE_V5_WORKPLAN.md`
**Scope:** Close design-review gaps in the fixed-eight target-size v5 path without restoring any retired ladder/migration/rescue authority.
**Priority:** Scientific/protocol identity and ownership correctness first; preserve the successful v5 hard cut.

## 1. Objective

Bring the implemented target-size-v5 path into complete agreement with the current target-size protocol after independent post-implementation review.

The surviving topology remains:

```text
FEAS1
  -> MVIDX1
  -> MVSEL2
  -> REPAIR2 / MVSTATE2
  -> MVQUAL2
  -> qualified fixed-size population Q
  -> target-size TRAIN2 fidelity study
       epoch 3 -> epoch 10 -> epoch 30
  -> immutable selected_target_size
  -> domain-local selected REPAIR2 prefixes
  -> held-out CV / EVAL / VERIFY
```

This round is corrective, not another redesign. Do not restore `TARGET-DATA2C`, rescue-size generation, active-ladder migration, `MVMIGRATE1`, `SIZE-HALVE2`, `SIZE-FIDELITY2`, or downstream size-state advancement.

## 2. Review findings that require correction

### 2.1 Domain-local membership ownership is incomplete

The selected target size is global protocol cardinality, but each required final-development and cross-validation gradient-training domain owns its own REPAIR2 master order.

For every required training domain `d` and selected size `N`, training membership must be exactly

\[
D_{d,N} = R_d[:N].
\]

Current final-development materialization consumes an authenticated REPAIR2 prefix, but CV training can still fall back to DATA7 re-selection. That leaves a second membership authority.

**Required correction:** MVSEL2/REPAIR2/MVQUAL2 must cover every required gradient-training domain, and DATA7 must consume the authenticated domain-local REPAIR2 prefix for both final-development and CV-training domains. DATA7 may not independently rerank target membership for this protocol.

### 2.2 Persisted continuation lineage is not fully self-validating

Attachment-time checks authenticate epoch 3 -> 10 -> 30 continuation, but restored current-schema `TargetSizeStudyPlan` state must revalidate the same semantic lineage.

**Required correction:** one canonical semantic validator must verify all accumulated evidence on deserialization/restart, including candidate membership identity, stage populations, checkpoint parentage, optimizer state lineage, RNG lineage, schedule/training-policy identity, survivor decisions, terminal-state consistency, and selected-size consistency.

A content-digest-valid object with forged continuation ancestry must fail closed.

### 2.3 MVQUAL2 monotonic suffix invariant is not enforced

For nested REPAIR2 prefixes and positive hard coverage/obligation predicates, qualification must be monotone with increasing size. For each required domain and for the global intersection, qualification may transition only as

```text
FAIL* -> PASS*
```

and never as

```text
PASS -> FAIL
```

or

```text
PASS -> FAIL -> PASS.
```

**Required correction:** treat a non-monotone qualification pattern as an authority/invariant error. Do not silently omit the failed rung or synthesize a replacement size.

### 2.4 Seed-set semantics require explicit closure

The normative target-size protocol requires every candidate size to use the same ordered training-seed set and comparisons to preserve seed pairing. The implementation currently exposes one `screening_optimizer_seed` scalar.

This round must make the contract explicit rather than infer policy from variable naming.

**Required correction:**

1. represent the screening seed policy as an ordered, authenticated seed set;
2. use the identical ordered set for every size;
3. aggregate comparison evidence by seed pairing before size ranking;
4. serialize the ordered seed set into policy and terminal decision identity;
5. reject missing, reordered, duplicated, or candidate-specific seed sets on restart/attachment.

The exact default seed set/cardinality must be taken from the owning current training-protocol authority or explicitly frozen in the target-size specification before implementation. Do not invent a second unrelated seed convention merely for this subsystem.

### 2.5 Early-screen practical-equivalence ordering drifts from the current rule

Within the configured practical-equivalence band, the smaller target size is preferred. The current early-screen helper can preserve the largest qualified boundary candidate even when it lies inside the equivalence band.

**Required correction:** remove boundary-preservation priority from epoch-3/epoch-10 equivalence ordering unless the current specification is deliberately revised first. Under the present rule, deterministic order is:

1. materially better paired aggregate first;
2. within the configured equivalence band, smaller target size first;
3. deterministic serialized tie resolution for any remaining exact tie.

The fixed-ceiling nonconvergence rule remains: if 16384 reaches the final comparison and is materially superior to every smaller comparable finalist by more than the configured final equivalence width, terminate as `nonconverged_at_fixed_ceiling`.

### 2.6 Fidelity-comparison failure should persist as typed study state

Numerical/scientific invalidity can leave too few comparable candidates to complete a required fidelity transition. Those scientifically meaningful failures should not disappear as an unstructured exception after partial study evidence has been accumulated.

**Required correction:** add a narrow typed terminal outcome such as

```text
insufficient_comparable_candidates
```

with the failed fidelity stage and authenticated candidate failure reasons. Do not create a broad error taxonomy for ordinary input/programming errors.

### 2.7 Current tests rely too heavily on source inspection

Topology-string/source tests are useful supplementary guards, but they do not establish runtime ownership, persistence integrity, or domain-local membership.

**Required correction:** add direct synthetic campaign-path tests for the corrected contracts, especially restart round trips and CV/final DATA7 membership.

## 3. Corrected configurable equivalence-policy contract

The equivalence policy is **configurable**. The documented values are defaults, not frozen protocol constants.

Current defaults:

```text
coarse_practical_equivalence_mev_per_a = 1.0
practical_equivalence_mev_per_a        = 1.0
```

where the coarse value controls epoch-3/epoch-10 screening and the final value controls epoch-30 final comparison / fixed-ceiling material superiority.

Requirements:

1. both values remain user-configurable positive finite policy inputs;
2. the defaults remain `1.0 meV/Angstrom` unless separately revised;
3. configured values are serialized in `TargetSizeStudyPolicy` and included in its policy digest;
4. target-size evidence and terminal decision identity bind that policy digest;
5. restart/continuation may reuse evidence only when the configured equivalence policy authenticates identically;
6. changing either equivalence width defines a different target-size study policy and invalidates reuse of derived target-size evidence from the old policy;
7. documentation must describe `1.0 meV/Angstrom` as the **default**, never as an immutable v5 constant.

No separate schema/version bump is required merely because a user selects a non-default valid width; the configured value itself is part of scientific policy identity.

## 4. Corrected ownership contract

### 4.1 One membership authority

For each required gradient-training domain:

```text
DATA5 domain identity
 -> MVSEL2 order
 -> REPAIR2 repaired order R_d
 -> MVQUAL2 prefix qualification
 -> selected N
 -> DATA7 consumes R_d[:N]
```

`TargetSizeStudyPlan` chooses `N`; it does not choose frame identities independently.

DATA7 is a materializer/consumer of the authenticated selected prefix for target-size-controlled final/CV training domains. It is not a second selector.

### 4.2 One hard size-eligibility authority

MVQUAL2 remains the sole hard size-eligibility authority.

Epoch 3/10/30 may reject a numerically invalid trajectory because no comparable score exists, but target-force acceptance thresholds, replay-retention, energy/stress quality, relaxation, physical integrity, deployment checks, and held-out CV are not target-size hard qualification or tie-break authority.

### 4.3 Immutable terminal selection

After `selected(N)`:

- no downstream component may mutate `N`;
- no discarded candidate may be revived;
- no rescue size may be generated;
- downstream protocol/model validation may accept or reject the resulting protocol only.

## 5. Implementation gates

### Gate 1 — Reconcile the normative policy before code changes

Update the current target-size specification and architecture text so they state unambiguously:

1. equivalence widths are configurable with defaults of `1.0 meV/Angstrom`;
2. configured values are policy-identity fields, not schema constants;
3. all required final/CV gradient-training domains use domain-local REPAIR2 prefixes;
4. MVQUAL2 qualification is monotone suffix authority;
5. the ordered seed-set contract and default seed authority are explicit;
6. early-screen equivalence ordering follows the smaller-size preference unless a deliberate policy revision says otherwise;
7. typed fidelity-comparison failure semantics are defined.

**Gate acceptance:** code, specification, architecture, and configuration terminology have one unambiguous target contract before implementation begins.

### Gate 2 — Make required-domain REPAIR2/MVQUAL2 ownership complete

Extend/restructure the current authority construction so every required final-development and CV gradient-training domain has:

- one authenticated MVSEL2/MVSTATE2 identity;
- one current REPAIR2 master order;
- MVQUAL2 evidence over the fixed nominal prefixes.

Compute common materializability and `Q` over all required domains.

Add explicit monotonicity validation per domain and globally.

**Gate acceptance:** a candidate size cannot enter `Q` unless it is materializable and MVQUAL2-qualified in every required training domain, and a non-monotone hard-pass pattern fails closed.

### Gate 3 — Eliminate DATA7 as a second target-membership selector

For selected target size `N`, pass the authenticated prescribed prefix into DATA7 for every target-size-controlled final-development and CV-training domain.

Required behavior:

```text
DATA7(d).selected_frame_uids == REPAIR2(d).repaired_master_order[:N]
```

for every required domain `d`.

Retain independent DATA7 selection only for workflows/domains that are genuinely outside the target-size-v5 membership contract.

**Gate acceptance:** monkeypatching the legacy/general DATA7 selector to raise must not break target-size-v5 final or CV training materialization.

### Gate 4 — Make target-size study persistence self-validating

Create one canonical semantic validation path for `TargetSizeStudyPlan` and invoke it on:

- construction/transition;
- `from_dict()` or immediately after deserialization;
- campaign-store restart authentication.

Validate at minimum:

- fixed nominal population and configured policy identity;
- qualified population and candidate prefix digests;
- stage entrant/survivor/finalist cardinalities;
- ordered seed-set completeness and pairing;
- exact checkpoint/optimizer/RNG/schedule/training-policy continuation;
- no evidence for unauthorized/eliminated candidates at later stages;
- outcome/selected-size/fixed-ceiling consistency.

**Gate acceptance:** adversarially changing a parent checkpoint/optimizer/RNG digest, seed identity, survivor set, selected size, or configured equivalence width and recomputing outer content digests still fails semantic validation.

### Gate 5 — Correct comparison and terminal-result semantics

Implement the reconciled ranking policy:

1. aggregate candidate evidence over the common ordered seed set using paired aggregation;
2. apply configured coarse equivalence width at epoch 3 and epoch 10;
3. prefer smaller size inside that equivalence band;
4. advance exactly `q -> min(q,4) -> 2 -> 1` when enough comparable candidates remain;
5. apply configured final equivalence width at epoch 30;
6. emit `nonconverged_at_fixed_ceiling` only under the fixed-ceiling material-superiority rule;
7. emit typed `insufficient_comparable_candidates` when numerical/scientific trajectory failure prevents a required comparison;
8. never add a post-MVQUAL model-quality hard gate.

**Gate acceptance:** deterministic tests cover all-equal, inside-band, outside-band, ceiling-superior, numerical-failure, and multiple-seed cases.

### Gate 6 — Direct campaign-path regression and cleanup

Add direct executable tests that traverse the real target-size control path with small synthetic data.

Mandatory cases:

1. all eight nominal sizes only;
2. common materializability across final + CV training domains;
3. monotone-suffix MVQUAL2 acceptance and pass/fail/pass rejection;
4. `q < 3 -> insufficient_qualified_sizes`;
5. `q = 3 -> 3 -> 3 -> 2 -> 1`;
6. paired ordered seed evidence is identical across candidate sizes;
7. configured non-default equivalence widths alter policy digest and ranking where expected;
8. epoch 3 -> 10 -> 30 exact continuation survives a legitimate restart;
9. forged continuation fails after restart/deserialization;
10. no held-out CV/EVAL/VERIFY evidence exists before terminal size selection;
11. selected size remains immutable afterward;
12. final-development DATA7 membership is exactly its local `R_d[:N]`;
13. every CV-training DATA7 membership is exactly its local `R_d[:N]`;
14. target-size-v5 materialization does not call the independent DATA7 selector;
15. 16384 material superiority gives fixed-ceiling nonconvergence with no rescue;
16. downstream model/protocol rejection does not change selected size;
17. current upstream FEAS1/MVIDX1/MVSEL2/REPAIR2/MVQUAL2 state remains selectively reusable when all identities match;
18. legacy ladder/migration/rescue constructors remain unreachable.

Retain source-inspection topology tests only where they catch accidental reintroduction of forbidden dependencies; they do not substitute for runtime tests.

**Gate acceptance:** all corrected invariants are proven through owning-layer or real campaign-path behavior, with no parallel test implementation of the selection algorithm.

## 6. Performance and resource constraints

This corrective round must preserve bounded materialization:

- do not persist eight independent product-scale target datasets/descriptor graphs per domain;
- represent candidate rungs as authenticated prefix metadata/views where possible;
- materialize only currently authorized training candidates;
- share immutable domain/index/descriptor state where ownership permits;
- do not multiply memory/storage footprint by the number of seeds beyond the training artifacts actually needed for the active fidelity stage;
- preserve the optimized MVQUAL2 sparse/progressive backend.

If paired-seed execution materially increases wall time, optimize scheduling/batching/reuse without weakening the paired-seed scientific contract.

## 7. Non-goals

This round does not authorize:

- sizes outside `(128,256,512,1024,2048,4096,8192,16384)`;
- rescue or adaptive ladder generation;
- legacy state migration into current target-size authority;
- held-out CV as an inner target-size selector;
- reintroduction of model-quality hard gates after MVQUAL2;
- freezing equivalence widths at their defaults;
- GPU qualification before the final consolidated release qualification.

## 8. Genuine redesign triggers

Return to design only if implementation demonstrates that:

1. required CV/final training domains cannot expose deterministic/authenticatable REPAIR2 prefixes without violating leakage boundaries;
2. MVQUAL hard predicates are not actually monotone under the current positive-coverage/obligation semantics, in which case the specification's suffix theorem must be revisited rather than patched around;
3. the owning training protocol has no coherent ordered seed-set authority suitable for paired target-size comparison;
4. exact continuation across multiple seeds cannot be represented without unacceptable state/resource growth and no simpler authenticated representation is feasible;
5. a downstream scientific requirement genuinely requires held-out evidence to control target-size selection;
6. the fixed 16384 ceiling itself is invalid as a product requirement.

Ordinary refactoring difficulty, test failures caused by stale architecture, or the need for restart-schema advancement are not redesign triggers.

## 9. Completion criterion

The corrective round is complete only when the mechanically demonstrated current topology is:

```text
required final + CV gradient-training domains
  -> domain-local MVSEL2
  -> domain-local REPAIR2 R_d
  -> monotone MVQUAL2
  -> common Q
  -> paired-seed 3/10/30 study under authenticated configurable policy
  -> immutable selected N
  -> every training domain consumes exactly R_d[:N]
  -> held-out CV / EVAL / VERIFY
```

with:

- no second target-membership selector;
- no restart path capable of authenticating forged continuation lineage;
- no hidden post-MVQUAL hard qualification;
- no rescue/migration/legacy ladder authority;
- equivalence defaults configurable and identity-bound rather than frozen.
