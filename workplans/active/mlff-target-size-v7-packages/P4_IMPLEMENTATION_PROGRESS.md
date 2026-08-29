# P4 implementation progress and evidence log

Working record for `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` **package revision 6**.
Authority: frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` plus the revision-6 overlay in the P4 package.

The complete revision-5 candidate and evidence are preserved in:

- `P4_REVISION5_IMPLEMENTED_BASELINE.md`;
- `P4_REVISION5_IMPLEMENTATION_PROGRESS.md`.

Revision-4 baseline/evidence remain preserved unchanged.

## Revision-6 status summary

| Pass | Scope | State |
|---|---|---|
| Entry/P3 | accepted P3 revision 7 through P3A9 | **CLOSED / PRESERVED** |
| P4-A | CampaignStore state, canonical generation, CAS, transition identity | **CLOSED / PRESERVED** |
| P4-B | destructive regime cutover | **CLOSED / PRESERVED** |
| P4-C2 | one canonical execution-root owner + real-runtime first-publication retention race | **OPEN** |
| P4-D | production switch architecture | **CLOSED / AFFECTED REGRESSION REQUIRED** |
| P4-E2 | current-terminal authority/currentness + terminal view/report sealing | **OPEN** |
| P4-F | STOR/docs/structural integration | **CLOSED / AFFECTED REGRESSION REQUIRED** |
| P4-G2 | final assembled affected-surface closure | **OPEN / BLOCKED ON C2+E2** |

## Independent-review blockers routed to revision 6

### P4-C2

Revision-5 runtime and retention independently construct the `.mdstats/target-size/g<N>` execution-root layout. The revision-5 first-publication test also manually chooses that same path and directly calls P3 initialization rather than traversing the production `select-target-size` root owner. This can remain green if runtime and STOR later diverge.

Required closure evidence:

- one dependency-leaf canonical root constructor imported by runtime and retention;
- no duplicate root-name/path formula in those owners;
- real `prepare -> select-target-size` path;
- wrapper around real `initialize_target_size_screen` calls real initializer exactly once and pauses after first publication;
- actual root comes from the runtime call argument, not test reconstruction;
- while CampaignStore remains `AUTHORITIES_BOUND` with `attempt=None`, `execution_root=None`, and no adopted head, an independent process builds the real `_campaign_ownership_boundary` and performs production destructive authorization/removal against that actual root/files;
- zero protected first-publication files removed;
- runtime resumes successfully;
- external/symlink/ambiguous paths remain denied and unrelated reclaimable residue remains reclaimable.

The existing direct-initializer first-publication test does not close this claim by itself.

### P4-E2

Revision-5 terminal reload correctly validates the public repeated CLI path, but the reusable loader can accept a caller-supplied historical revision and the terminal view can render raw terminal revision + old resolver/definition. Both can reauthenticate an internally valid historical generation after CampaignStore has advanced.

Required closure evidence:

- canonical current-terminal loader always loads the actual current CampaignStore revision first;
- caller-provided revision, if retained at all, is only a strict expected-current assertion and must match current state revision/sequence/generation;
- terminal views/reporter consume only a validated-current terminal result, not raw terminal projection/revision;
- build terminal g1, change target-size scientific identity, run real `prepare` to bind g2, then prove g1 cannot be returned/rendered/reported as current despite intact g1 P3 evidence;
- unchanged current terminal reload still validates/reports with zero numerical work;
- revision-5 corruption/invalidation/terminal-failure cases remain passing.

## Evidence invalidation

### Preserved

- P1-P3 scientific/reducer/execution semantics;
- P4-A CAS/transition-identity evidence;
- P4-B destructive cutover/quarantine evidence;
- revision-5 terminal helper behavior not intersecting currentness, subject to fresh P4-E2 regression;
- nonterminal screen science not intersected by root/helper refactor, subject to affected P4-D regression.

### Must rerun

- P4-C retention/root/storage race tests;
- P4-D `select-target-size` affected regression;
- all P4-E terminal/currentness/view/report tests;
- P4-F STOR/structural tests affected by root ownership and view changes;
- P3A9 resolver/reconciliation tests if terminal loader routing touches those surfaces;
- final P4-G2 assembled integration and affected-surface regression.

## Closure discipline

Do not mark P4-C2 or P4-E2 closed from helper-level tests. Their semantic owners are respectively:

```text
real select-target-size -> real P3 first publication -> real production STOR authorization
```

and

```text
real CampaignStore current revision -> full current terminal validation -> terminal view/report/current consumer
```

P4 metadata remains `status: active` and P5 remains blocked until both stages and fresh P4-G2 assembled closure pass.
