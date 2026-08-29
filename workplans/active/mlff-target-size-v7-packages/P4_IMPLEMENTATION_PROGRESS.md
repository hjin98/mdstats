# P4 implementation progress and evidence log

Working record for `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` **package revision 7**.
Authority: frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` plus the revision-7 overlay in the P4 package.

The exact revision-6 candidate/evidence reviewed at `142026700e2b1ba2f7597d5f236f66eb32f8ee29` are preserved in:

- `P4_REVISION6_IMPLEMENTED_BASELINE.md`;
- `P4_REVISION6_IMPLEMENTATION_PROGRESS.md`.

Revision-4 and revision-5 baselines/evidence remain preserved unchanged.

## Revision-7 status summary

| Pass | Scope | State |
|---|---|---|
| Entry/P3 | accepted P3 revision 7 through P3A9 | **CLOSED / PRESERVED** |
| P4-A | CampaignStore state, canonical generation, CAS, transition identity | **CLOSED / PRESERVED** |
| P4-B | destructive regime cutover | **CLOSED / PRESERVED** |
| P4-C2 | single canonical execution-root construction owner | **CLOSED / PRESERVED** |
| P4-C3 | first-publication retention through actual production STOR ownership/removal | **OPEN** |
| P4-D | production switch architecture | **CLOSED / AFFECTED REGRESSION REQUIRED** |
| P4-E2 | canonical current-terminal loader/full validation chain | **CLOSED / PRESERVED** |
| P4-E3 | exposure-time CampaignStore currentness for current terminal view/write/report/consumer | **OPEN** |
| P4-F | STOR/result-view/docs/structural integration | **CLOSED / AFFECTED REGRESSION REQUIRED** |
| P4-G3 | final assembled affected-surface closure | **OPEN / BLOCKED ON C3+E3** |

## Independent-review blockers routed to revision 7

### P4-C3 — production STOR semantic owner not yet exercised

Revision 6 fixed production root ownership and improved the runtime side of the publication race. Its mandatory test now drives real `select-target-size`, calls the real P3 initializer exactly once, and captures the actual runtime root while CampaignStore is still `AUTHORITIES_BOUND` with no persisted root/attempt.

The spawned cleanup child still manually creates `CampaignOwnershipBoundary`, manually injects `build_target_size_retention_fence`, calls `destructive_authorization` directly, and directly unlinks authorized files. Therefore it can pass even if the actual production STOR boundary assembly or production cleanup/removal helper stops honoring the fence. The root directory is also not genuinely challenged because the helper only deletes files.

**Required closure:** use the real production STOR ownership-boundary constructor and real production cleanup/removal helper in the independent child. Submit the actual observed root directory plus representative first-publication files, and submit an unrelated reclaimable campaign-owned control through the same path. Root/files must survive; the control must be removed.

### P4-E3 — legitimate validated snapshot can become stale before exposure

Revision 6 fixed the canonical loader: it reloads CampaignStore current state first and validates the full P1/P2/common/P3/head/reducer/projection chain on that current revision.

A legitimately returned `ValidatedTargetSizeTerminalResult` can nevertheless be retained after CampaignStore advances. `g1_revision + g1_validated` still form a self-consistent historical pair, and pure view/report helpers can expose them after real `prepare` has made `g2` current without re-reading CampaignStore.

**Required closure:** every public/current terminal exposure re-establishes CampaignStore currentness in the same invocation before terminal file publication, stdout/reporting, or downstream current-result return. Pure snapshot rendering may remain internal/non-current, but a validated snapshot is not perpetual current authority.

## Preserved evidence

The following claims remain accepted unless the revision-7 implementation unexpectedly expands their affected surface:

- P1-P3 scientific/reducer/checkpoint/provider/replay semantics;
- P4-A CampaignStore/CAS/transition identity;
- P4-B destructive regime cutover/quarantine;
- revision-6 single canonical execution-root constructor and runtime/retention reuse;
- revision-6 canonical current-terminal loader’s CampaignStore-first behavior and complete terminal validation chain;
- target-size decision/reducer semantics and nonterminal screen science.

Preserved evidence is not permission to skip fresh regression for a surface actually touched by C3/E3.

## Evidence invalidated / must rerun

### After P4-C3 executable changes

- `tests/test_mlff_target_size_p4c_cross_store_adoption.py`;
- affected P4-D runtime-cutover tests;
- affected P4-F STOR/storage/structural tests;
- production cleanup/accounting/reclamation tests intersecting the real STOR removal helper;
- external-path/symlink/reclaimable-residue negatives;
- canonical root uniqueness/source-absence check.

### After P4-E3 executable changes

- `tests/test_mlff_target_size_p4e_terminal_and_invalidation.py`;
- affected P4-D terminal and initial-completion runtime tests;
- affected P4-F result-view/storage/structural tests;
- P3A9 resolver/reconciliation tests if terminal exposure intersects adopted-head resolution;
- any P5-facing current-result API seam tests introduced now.

### Final P4-G3

Fresh final assembled affected-surface regression after all C3/E3 changes, including P4-A through P4-G affected suites and P3A9 where intersected. Broaden to the full available suite only if impact cannot be bounded confidently.

## P4-C3 mandatory acceptance checklist

The acceptance test is not closed until all items below are true on one assembled candidate:

- [ ] real `prepare` binds current `AUTHORITIES_BOUND` generation;
- [ ] real parser/function `select-target-size` is running;
- [ ] real production root constructor supplies root to real P3 initializer;
- [ ] synchronization wrapper calls real initializer exactly once and captures the actual root argument after first publication;
- [ ] before release, CampaignStore still has `attempt=None`, `execution_root=None`, `adopted_execution_head_digest=None`;
- [ ] independent spawned process loads real cfg/paths and opens real CampaignStore;
- [ ] child invokes the actual production STOR ownership-boundary assembly, not direct `CampaignOwnershipBoundary(...)` construction;
- [ ] child invokes the actual production cleanup/removal helper, not direct `destructive_authorization`/filesystem deletion;
- [ ] actual observed root **directory** is submitted to that removal path and survives;
- [ ] representative freshly published P3 files are submitted and survive;
- [ ] unrelated reclaimable campaign-owned control is submitted through the same path and is removed;
- [ ] external/symlink containment negatives remain denied appropriately;
- [ ] real `select-target-size` resumes and reaches OPEN_ATTEMPT/reconciliation, preferably terminal bounded completion;
- [ ] source/structural review confirms no duplicate root owner was reintroduced.

Direct fence/boundary unit tests remain useful but cannot satisfy this checklist.

## P4-E3 mandatory acceptance checklist

Construct a genuine stale snapshot:

```text
terminal g1
 -> canonical loader returns legitimate g1_validated while g1 is current
 -> preserve g1 immutable evidence
 -> change target-size scientific identity
 -> real prepare advances current CampaignStore generation to nonterminal g2
```

Then establish all of the following:

- [ ] public/current terminal view/write path given retained g1 state/snapshot re-reads CampaignStore and rejects g1;
- [ ] exact self-consistent historical pair `g1_revision + g1_validated` cannot publish a current terminal result after g2 exists;
- [ ] stale view/write attempt does not create or overwrite `target-size-state.json` with g1 terminal data;
- [ ] public/current terminal reporting path given retained g1 snapshot re-reads CampaignStore and rejects g1;
- [ ] stale report attempt emits no selected-N / “already selected and frozen” / “scientifically terminal” terminal authority line;
- [ ] repeated unchanged current terminal reload still succeeds with zero trainer/evaluator work;
- [ ] initial terminal completion validates currentness before its first terminal view/report publication;
- [ ] P5-facing current-result seam is defined to use the same canonical current loader/exposure owner;
- [ ] missing/corrupt adopted head, CampaignStore tamper, scientific invalidation, neutral config, terminal failure, and stale/missing rebuildable `current_head.json` regression remain passing;
- [ ] source/structural review confirms one canonical current-terminal loader and no public/current stale-snapshot bypass.

A raw-projection type rejection or `g2_revision + g1_validated` mismatch test does not substitute for the exact retained legitimate `g1_revision + g1_validated` case.

## P4-G3 assembled closure checklist

After C3 and E3 both close:

- [ ] re-derive final affected surface from the assembled implementation;
- [ ] run fresh final P4 affected regression and relevant P3A9 regression;
- [ ] run bounded assembled integration: `prepare -> select terminal -> fresh current terminal reload -> real production STOR cleanup -> second current terminal reload`;
- [ ] prove the second reload performs zero retraining and returns identical N/T/reason;
- [ ] run missing/corrupt immutable-head and scientific-invalidation negatives;
- [ ] run stale legitimate old-generation snapshot after new-generation prepare negative;
- [ ] include the real production-STOR first-publication race;
- [ ] structural search: exactly one root owner, one current-terminal loader/currentness core, no current stale-snapshot exposure bypass, no V7-prefixed production naming;
- [ ] only then set P4 `status: implemented`, record fresh commands/results, and unblock P5.

## Closure discipline

P4 metadata remains `status: active` and P5 remains blocked while P4-C3, P4-E3, or P4-G3 is open.

The implementation agent must not obtain closure by:

- weakening/removing the mandatory owner-level tests;
- replacing production STOR with a test-built equivalent boundary;
- treating a previously validated Python object as permanently current;
- duplicating terminal validation or root authority;
- adding unrelated scientific or persistence redesign;
- relying on the revision-6 `166 passed` result as final revision-7 evidence.

Full long GPU/real-production qualification remains deferred to final release.