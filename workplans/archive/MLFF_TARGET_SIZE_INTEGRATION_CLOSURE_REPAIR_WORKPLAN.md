---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-INTEGRATION-CLOSURE-REPAIR
protocol_version: 5.16.0
status: completed
created_date: 2026-09-08
completed_date: 2026-09-08
reviewed_date: 2026-09-08
review_status: pass
review_round: implementation-review-6
accepted_candidate_head: 03ff58f9e839edf345e52b8a4aeef612dbd1b092
accepted_executable_head: add7fcfe647b2d7f91e0fe94e8fc9c64a710fa75
branch: plan/mlff-target-size-integration-closure-repair
implementation_base_head: 32bd59d12de334a2e5c29d80d6c1cf5cceb4506c
predecessor_workplan: workplans/archive/MLFF_TARGET_SIZE_MULTI_SELECTION_NEXT_ROUND_REPAIR_WORKPLAN.md
---

# MLFF target-size integration closure repair workplan

## Final disposition — PASS / closed

Independent Software Design review round 6 accepts candidate `03ff58f9e839edf345e52b8a4aeef612dbd1b092`, whose substantive executable implementation is `add7fcfe647b2d7f91e0fe94e8fc9c64a710fa75`. The candidate child records implementation evidence only; no executable product files changed after the accepted executable commit.

All blocking findings carried by the previous active revision are closed. No remaining defect was found that violates the core target-size scientific problem, the frozen multi-size architecture, the supported exact-P5A6 historical compatibility boundary, or final affected-surface functional acceptance.

## Tier-1 product invariants accepted

1. Manual `select-target-size N --horizon-cv HC --horizon H` is an operator decision over the prepared qualified ladder and performs no target-size TRAIN2/EVAL2 work.
2. `--auto` is advisory only: it emits a recommendation or typed no-recommendation and freezes nothing.
3. Every selected membership is exactly `T_N = pi_train[:N]` under authenticated P2 training-order authority.
4. P2 owns one canonical target-size scientific policy, one population/split, one `pi_train`, one `pi_eval`, and one nonempty ordered set of unique nonnegative optimizer seeds.
5. One prepared generation is shared by all selected sizes; manual selection does not hydrate unrelated P3/frame-array work.
6. The provisional/frozen design is one ordered unique-by-N collection; `cross-validate` is the sole atomic freeze authority for current designs.
7. Post-selection CV and fresh final production run independently for every frozen size with its exact membership and role horizon; there is no cross-size winner rule.
8. Derived target-size result JSON is presentation only and never scientific/currentness input.
9. The exact accepted P5A6 current-generation workspace remains a supported unchanged-reopen boundary under its native historical schemas. Historical descendants validate parent -> child and cannot manufacture an upstream scientific authority.
10. Production-scale GPU/CuEq/LAMMPS qualification remains deferred to the established final-release/user-machine stage and is not part of this bounded functional closure.

## Frozen high-level architecture accepted

- one `CampaignStore` mutable campaign authority;
- one prepared generation and one ordered current selected-size collection;
- separate manual and automatic selection branches converging only at the proposal merge owner;
- minimum authenticated P2 dependency for manual selection;
- full P3 numerical dependency only for the automatic diagnostic that actually screens candidates;
- pure committed-state result-view projection and strict diagnostic exposure currentness;
- current per-size ancestry `P1/P2/P4 -> selected binding -> method/CV -> final production`;
- supported P5A6 ancestry follows the same parent -> child direction under native historical wire identities, with no preload migration or rewrite;
- V1 head/reducer fields remain historical wire identity only and never enter current-V3 target ancestry.

## Final closure findings

### R15 — P2 optimizer-seed invariant: PASS

`ResolvedTargetSizePolicy.__post_init__()` again rejects negative optimizer seeds in the existing single owner. The same nonnegative domain applies to V1 and V2 policy construction; no second validator, wrapper, migration, policy registry, or schema-specific public path was introduced.

Focused P2 tests now reject negative seeds through direct construction, dataclass replacement, policy resolution, and config resolution, while confirming that zero is valid and seed ordering continues to participate in policy identity.

### R17 — historical V1/current-V3 binding isolation: PASS

The existing architecture guard now proves all of the required distinctions:

- normal `target_size_binding()` produces a V3 binding with every `legacy_v1_*` field unset even when the input state carries diagnostic head/reducer digests;
- a historical V1 binding preserves and round-trips the native revision/head/reducer fields and reproduces its historical digest;
- focused AST inspection prevents V1/adopted head/reducer fields or `auto_diagnostic` from feeding the current `target_size_binding()` owner;
- synthetic `_Legacy*` experiment/aggregate classes remain absent;
- the campaign-state compatibility comment now states the actual boundary: historical P5A6 descendants can reopen under native historical identity, but a prerework row cannot create a current-V3 freeze or new current binding.

The production implementation itself remained on the already accepted parent -> child compatibility design; this round strengthened the oracle rather than adding new compatibility machinery.

### R16 — final affected-surface acceptance: PASS

Final affected-surface evidence covers the changed P2 policy owner, current/historical binding owner, all P5 consumers, assembled MACE execution semantics, current multi-size behavior, target-size execution/terminal-policy/cutover consumers, downstream P7 qualification consumers, documentation, compile/static importability, and the exact historical compatibility driver.

Recorded final results on the accepted assembled implementation:

- `python -m compileall mdstats tests qualification/p6-p5a6-compat`: 0 errors;
- `python qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py`: 3/3 phases PASS;
- P2 statistical-authority suite: 23 passed;
- exact P5A6 compatibility suite: 4 passed;
- provisional-selection/architecture suite: 20 passed;
- complete `tests/test_mlff_target_size_p5*.py` family: 179 passed;
- assembled MACE execution semantics: 3 passed;
- downstream P7 qualification suites: 85 passed, 1 skipped;
- multi-size selection/integration: 46 passed;
- target-size execution P3 / terminal decision / policy-domain / identity-cutover slice: 154 passed;
- documentation/PDF structure checks: 40 passed.

Total recorded affected-surface functional assertions: **554 passed, 1 skipped**. The single skip is the already-established unavailable host LAMMPS/MACE deployed-product execution that remains deferred to final target-machine GPU/CuEq/LAMMPS qualification; it is not a substitute for any bounded functional regression required by this workplan.

Implementation also reports Serena reference derivation for `ResolvedTargetSizePolicy` and `PostSelectionBinding`; independent web review cross-checked the final executable diff and production ownership using repository source/reference inspection because Serena/Semgrep were unavailable in the review environment.

## Compatibility architecture closeout

The exact accepted P5A6 workspace remains supported without preload rewrite or migration. Its historical selected `N/T` is re-established from upstream P1/P2 authority before post-selection descendants are consulted. Final-plan M3 lineage is checked against independently rebuilt P2 authority, and poisoned/missing post-selection descendants cannot redefine selected membership. The earlier descendant-to-ancestor synthetic bridge remains removed.

This historical path is accepted as the minimum justified compatibility specialization for the supported P5A6 product boundary. No compatibility database, sidecar, migration layer, fake experiment definition/order/aggregate, or blanket prerework-currentness mechanism is retained.

## Final review conclusion

**PASS.** The implementation satisfies the frozen scientific and architectural contract with no remaining blocking drift, gap, or evidence deficiency found in the reviewed scope. This workplan is complete and archived.

No further implementation repair is authorized by this plan. Any future defect is a new issue unless it demonstrates that one of the accepted Tier-1/Frozen assumptions above is false.
