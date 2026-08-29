# P4 implementation progress and evidence log

Working record for `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` **package revision 5**.
Authority: frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` plus the revision-5 overlay in the P4 package.

The complete revision-4 implementation/evidence log is preserved unchanged in
`P4_REVISION4_IMPLEMENTATION_PROGRESS.md`. Reuse that evidence only where the revision-5 workplan
explicitly says it remains valid.

## Revision-5 status summary

| Pass | Scope | State |
|---|---|---|
| Entry/P3 | accepted P3 revision 7 through P3A9 | **CLOSED / PRESERVED** |
| P4-A | CampaignStore state, canonical generation, CAS, transition identity | **CLOSED / PRESERVED** |
| P4-B | destructive regime cutover | **CLOSED / PRESERVED** |
| P4-C1 | first-publication execution-root retention fence | **REOPENED / OPEN** |
| P4-D | production switch architecture | **CLOSED**, affected CLI regression must rerun after P4-E1 |
| P4-E1 | terminal real-owner reload, invalidation, terminal-view validation | **REOPENED / BLOCKING** |
| P4-F | STOR/docs/structural integration | **CLOSED**, affected STOR regression must rerun after P4-C1 |
| P4-G1 | final assembled affected-surface closure | **INVALIDATED / OPEN** |

## Reopening authority

Independent review of the revision-4 closure identified one genuine blocking defect and one required
hardening consequence:

1. The real `execute_current_select_target_size()` terminal branch can report the persisted terminal
   projection and return before reconstructing/revalidating current P1/P2/P3 authority. This means a
   missing/corrupt adopted P3 head or a changed target-size scientific identity can be hidden by the
   early terminal return. Direct helper tests of `validate_terminal_projection(...)` do not prove
   the production caller invokes it.
2. The execution root can be created/initialized before the later campaign transition has persisted
   an `execution_root` locator, while the retention fence is inert when no locator exists. Revision 4
   already protects the later P3-publication -> SQLite-adoption frontier, but revision 5 must also
   prove protection from the **first** real P3 publication.

P4 closure commit under review: `53800cf3e4862326643b1708863f9b07573669ef`.
Reviewed branch tip differs only by generated documentation PDF:
`a66d32ffb3b3da2b1d51d2e8d970bd0083839f23`.

## Evidence invalidation

### Preserved

- P4-A state/CAS/transition-identity evidence;
- P4-B cutover/quarantine evidence;
- accepted P1/P2/P3 scientific and restart semantics;
- revision-4 nonterminal target-size execution evidence not intersected by the caller/root changes;
- revision-4 documentation evidence not made false by the revision-5 implementation.

### Must rerun

- P4-C retention/storage race tests covering first publication;
- P4-D `select-target-size` caller regression affected by terminal-flow refactoring;
- all P4-E terminal/invalidation tests, with the new mandatory real-CLI negatives;
- P4-F STOR tests affected by canonical-root protection changes;
- P3A9 resolver/reconciliation regression if the terminal loader touches those call paths;
- final P4-G1 assembled integration and affected-surface regression.

## Mandatory evidence to record before reclosure

### P4-C1

Record the exact production point at which the canonical generation root becomes deletion-protected,
and the real-owner race test proving:

- real CampaignStore/SQLite;
- real P3 screen initializer executes once;
- real production STOR destructive authorization runs from an independent process/connection during
  the first-publication interval;
- root and freshly published evidence cannot be deleted despite no adopted head;
- unrelated reclaimable residue is not permanently pinned;
- no CampaignStore write transaction encloses P3 mutation/I/O.

### P4-E1

Record real parser + real CampaignStore + real P1/P2 + real P3 resolver/reconciler results for:

- unchanged fresh-process terminal selection reload, including stale/missing rebuildable
  `current_head.json`, with zero retraining;
- missing immutable adopted head -> corruption before terminal result exposure;
- corrupt immutable adopted head -> corruption before terminal result exposure;
- tampered CampaignStore terminal state -> rejection;
- target-size scientific identity changes covering seeds/order, fidelity, metric/policy,
  partition/protected relation/hard support, and common preparation/training/execution context ->
  fail closed with guidance to `prepare`, no stale terminal output;
- CV-only/production-only changes -> identical validated terminal result, same target-size generation,
  zero retraining;
- terminal scientific failure unchanged reload -> validated terminal failure; missing/corrupt P3
  evidence -> corruption instead of persisted-failure output;
- terminal result view cannot render current terminal state from a raw CampaignStore revision alone.

Direct calls to `validate_terminal_projection(...)` remain useful focused tests but do **not** close
these real-caller claims.

### P4-G1

After both reopened stages close, record:

- final semantic reconciliation against the frozen parent + revision-4 baseline + revision-5 overlay;
- re-derived final affected surface;
- complete affected regression and required P3A9/STOR/CLI subsets;
- bounded assembled `prepare -> select-target-size -> fresh-process terminal reload -> real STOR
  cleanup authorization -> second terminal reload` integration;
- negative assembled missing/corrupt-head and changed-scientific-identity cases;
- broader/full suite if impact cannot be bounded, with failure-identifier comparison against the
  preserved pre-P4/revision-4 baseline;
- structural proof that no second terminal authority/loader, duplicate generation/root authority,
  retired target-size call path, or version-prefixed production name was introduced.

Only after those results are recorded may P4 metadata return to `status: implemented` and P5 become
unblocked.
