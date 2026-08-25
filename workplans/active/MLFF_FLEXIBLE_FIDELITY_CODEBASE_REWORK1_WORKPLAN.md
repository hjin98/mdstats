---
kind: implementation-workplan
workplan_id: CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1-REWORK1
protocol_version: 5.5.0
---

# MLFF Flexible-Fidelity Rework 1 Workplan

## 1. Authority, scope, and rework starting point

This workplan is the governing rework overlay for `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1` after independent Software Design review of implementation commit `74bc56c9672d98ce7db2f9c2b9936b9ce72abefc` on branch `feat/mlff-end-to-end-performance-v1`.

The parent workplan `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK_WORKPLAN.md` remains authoritative for all frozen decisions and obligations not explicitly strengthened or reconciled here. On conflicts within the rework scope, this workplan takes precedence.

The accepted product architecture is **not reopened**:

```text
0 < n1 < n2 < n3 <= n

default fidelity = (1,3,10)
default full TRAIN2 horizon n = 30
```

Preserve already-correct implementation from the reviewed commit unless a rework change can materially invalidate it. Do not replay completed design or unrelated implementation stages merely because the implementation was rejected for closeout.

## 2. Independent-review findings and routing

### R1 - BLOCKER: post-preflight in-place upgrade/reuse is unsafe

Classification: workplan deficiency plus implementation nonconformance.

Observed failure mode: changing an existing fixed-generation campaign to v2 flexible-fidelity configuration changes the whole campaign configuration SHA, causing completed stages to appear stale. DATA8 screening materializations are also bound to the full target-size-study digest, so a fidelity-only change can reject otherwise identical upstream materialization as a different target-size authority.

Protected concern: users with completed `prepare`/`preflight` must be able to adopt flexible fidelity without rerunning semantically unchanged upstream preparation. Reuse must remain fail-closed and evidence-based; no blanket ignore-digest path is acceptable.

Required end state: campaign/stage/materialization identity is factored by semantic dependency. A change to fidelity boundaries or downstream TRAIN2 horizon invalidates only state whose meaning actually depends on those settings. Preparation-affecting changes still invalidate preparation and all dependent state.

### R2 - BLOCKER: SIZE-FIDELITY1 does not hard-qualify the final screen

Classification: implementation nonconformance against parent O7/P3.

Observed failure mode: execution geometry includes `n3` and `n`, but the qualification reducer can certify a candidate without requiring the production final-screen decision at `n3` to be consistent with the full-horizon reference at `n`.

Protected concern: SIZE-FIDELITY1 must qualify the same coarse -> short -> final-screen funnel that production will execute, using full-`n` behavior as the scientific reference.

Required end state: final-screen selection/order at `n3` is a hard qualification input and is compared against full-reference selection/order at `n`. When `n3 == n`, one physical result may satisfy both roles, but both semantic roles remain explicit.

### R3 - HIGH: SIZE-FIDELITY1 short-screen equivalence rule drifts from production

Classification: implementation nonconformance.

Observed failure mode: calibration can use a different practical-equivalence tolerance for the short screen than the production target-size reducer. Defaults can mask the discrepancy.

Protected concern: calibration/qualification must emulate production scientific ordering exactly. A parameter set may not be certified under one ordering relation and deployed under another.

Required end state: SIZE-FIDELITY1 uses the exact production stage ordering/equivalence semantics for coarse, short, and final-screen decisions. Prefer one shared semantic ordering/stage-reduction authority over duplicated implementations.

### R4 - HIGH: documentation publication gate was skipped

Classification: implementation nonconformance against parent O12/S7.

Required end state: after executable rework integration closes, current architecture/specs/guides/config examples/generated artifacts are promoted from fixed-generation descriptions to the implemented flexible-fidelity runtime. Historical/archive records remain unchanged.

### R5 - HIGH acceptance gap: S6/S8 real-boundary integration and final affected regression are unproven

Classification: acceptance nonconformance.

Required end state: execute the parent A/B/C integration envelope plus the new legacy-post-preflight upgrade cases in this rework, through actual configuration/policy/orchestration/persistence/status consumer boundaries. Then run fresh final affected-surface regression and repository-required checks on the assembled candidate.

## 3. Frozen rework design

### 3.1 Stage-scoped semantic identity

Do not use the whole campaign configuration SHA as the sole compatibility authority for completed stages when only downstream-irrelevant configuration changes.

Required semantic identity classes:

1. **Preparation/preflight identity** — contains every input and resolved policy that can change prepared DATA6/DATA7/DATA8 bytes, admission, selection, repair/MVQUAL decisions, materialization, foundation/model-dependent preprocessing, and other upstream semantics. It excludes fidelity boundaries, later TRAIN2 schedule geometry, progress presentation, and documentation-only fields when those cannot change prepared outputs.
2. **Target-size/fidelity identity** — contains the prepared-data authority plus target-size policy, `(n1,n2,n3)`, ranking/equivalence policy, seed authority, and any other field that can change target-size screening meaning.
3. **TRAIN2 schedule/training identity** — contains full horizon `n`, LR/schedule/training/optimizer/scientific authorities, data ancestry, and all existing exact-continuation identity.
4. **Cross-dependent downstream identity** — SIZE-FIDELITY/PERF-P2R/execution plans authenticate the subset(s) they actually depend on.

A whole-config digest may remain as provenance, but it must not force invalidation when stage-local semantic identity proves compatibility.

Required implementation consequences:

- completed `prepare` and `preflight` receipts/status must be reusable after v1 -> v2 migration when all preparation-semantic inputs are unchanged;
- DATA7/DATA8 materialization identity must not be invalidated solely because `(n1,n2,n3)` or full `n` changed if those fields cannot alter the materialized bytes;
- target-size state/evidence from historical fixed `(3,10,30)` must not masquerade as new flexible evidence and must be invalidated/migrated according to its own semantics;
- changing any preparation-affecting field must still invalidate the preparation/preflight/materialization chain and downstream dependents;
- migration/re-authentication must validate the old receipt/artifact under its historical schema/identity before accepting reuse;
- if compatibility cannot be proven from persisted evidence, fail closed with an actionable message rather than guessing or silently rerunning a broader stage than required.

Suggested realization: introduce canonical stage-scoped semantic fingerprints/digests derived from normalized resolved configuration and existing data/model authorities, then migrate or reissue stage receipts after historical validation. Exact helper/schema structure is delegated.

Forbidden:

- unconditional acceptance of old config hashes;
- treating a global config SHA mismatch as sufficient proof that preparation must rerun;
- binding preparation artifacts to the full target-size-study digest when only a materialization-relevant subset is needed;
- deleting/rebuilding valid DATA7/DATA8 simply to simplify migration code;
- accepting old target-size screening evidence as if it were generated at new boundaries.

### 3.2 In-place campaign generation upgrade semantics

For an existing historical v1/schema-less campaign whose preparation/preflight is already complete:

```text
validate historical campaign + receipts + materializations
        -> normalize to v2
        -> compare preparation-semantic identity
        -> reuse compatible preparation/preflight/materializations
        -> invalidate/migrate only fidelity-dependent target-size state/evidence
        -> first newly authorized screen uses new n1
```

A default migration to `(1,3,10)/30` must therefore begin new target-size work at epoch 1 without rerunning preparation/preflight.

A nondefault migration to `(2,5,12)/40` must likewise preserve semantically unchanged preparation/preflight while establishing a new full-40 TRAIN2 schedule identity before any training work begins.

No requirement here permits cross-horizon TRAIN2 checkpoint reuse. Once TRAIN2 work exists, existing exact schedule/checkpoint compatibility rules continue to apply.

### 3.3 Exact SIZE-FIDELITY production emulation

SIZE-FIDELITY1 qualification must emulate the production funnel with one scientific definition of ordering/equivalence:

```text
coarse decision       @ candidate coarse calibration epoch(s)
short decision        @ n2
final-screen decision @ n3
reference decision    @ n
```

Required consequences:

- coarse and short survivor/finalist computation must use exactly the same stage-specific ordering/equivalence tolerances as production target-size selection;
- final-screen result at `n3` must be reduced using the same production final-screen ordering/equivalence semantics;
- full-reference winner/finalists/order derive from full-`n` metrics only;
- qualification must fail when the `n3` final-screen decision is inconsistent with the accepted full-reference rule;
- earlier-screen recall/equivalence criteria remain hard as in the parent workplan;
- rank-correlation remains diagnostic only;
- monitor/full prediction reuse remains authenticated and no duplicate inference is introduced solely by the new semantic role checks;
- `n3 == n` deduplicates physical evaluation but not semantic validation.

Preferred product-complexity direction: extract/reuse the target-size production ordering/stage-reduction mechanism so SIZE-FIDELITY1 does not carry a second divergent copy of target-size scientific ordering. An independent slower oracle is acceptable for tests, but production and qualification must share the authoritative decision semantics or prove exact equivalence at the interface.

### 3.4 Documentation publication remains mandatory

Parent O12/S7 remains frozen and was not satisfied by the reviewed implementation.

Do not declare the runtime rework complete before current documentation is reconciled after executable acceptance. Update authoritative sources first, regenerate tracked descendants, and verify generated-source integrity. Current docs must describe present flexible behavior, not workplan chronology.

## 4. Reworked implementation obligations

### O7-R1 - SIZE-FIDELITY full-funnel scientific closure

This strengthens parent O7.

Required end state:

- `n2`, `n3`, and reference `n` remain distinct roles;
- all three production screening decisions are emulated using production ordering/equivalence semantics;
- final-screen selection/order at `n3` is a hard qualification result compared against full-reference selection/order at `n`;
- short-screen tolerance/ordering is identical to production, including nondefault coarse-equivalence widths;
- `n3 == n` reuses one physical metric set without dropping either semantic role;
- existing recall/equivalence hard thresholds remain unchanged.

Acceptance evidence:

1. `(2,5,12)/40` fixture where epoch-12 final-screen selection differs from epoch-40 reference selection -> qualification must fail for final-screen inconsistency.
2. Fixture where coarse/short equivalence width differs from final equivalence width and produces different ordering -> SIZE-FIDELITY short finalists must exactly match production reducer semantics.
3. `(1,3,30)/30` fixture -> one physical epoch-30 evaluation, two semantic roles, consistent qualification.
4. Existing monitor-equivalence/finalist-recall/boundary-miss/reference identity regressions remain green.

### O10-R1 - identity/cache/reuse factoring

This strengthens parent O10.

Required end state:

- semantic dependency determines invalidation, not the whole config digest alone;
- tuple changes invalidate fidelity-dependent plans/state/evidence but not semantically independent prepared data;
- `n` changes invalidate TRAIN2 schedule/training/checkpoint and cross-dependent state but do not invalidate semantically independent preparation;
- changing preparation inputs/policies invalidates preparation plus all downstream state;
- old fixed target-size evidence cannot satisfy new flexible boundaries;
- same semantically relevant inputs produce stable stage fingerprints across irrelevant config/presentation changes.

Acceptance evidence:

- perturb `n1`, `n2`, `n3`, and `n` independently and assert the exact invalidation frontier;
- perturb one preparation-affecting field and assert prepare/preflight/materialization invalidation;
- perturb a presentation-only field and assert no scientific/preparation invalidation;
- prove current DATA8 materialization reuse does not depend on a fidelity-only target-size-study digest;
- prove cross-horizon TRAIN2 checkpoint rejection remains intact.

### O13 - post-preflight in-place generation upgrade

Protected concern: the new flexible-fidelity generation must be deployable on an already-prepared campaign without discarding valid expensive upstream work.

Required end state:

- historical v1/schema-less completed preparation/preflight can be upgraded to v2 when preparation-semantic identity is unchanged;
- historical receipts/materializations are validated before reuse;
- reusable upstream outputs remain byte/identity stable or are re-authenticated without recomputation;
- historical target-size screening state/evidence is invalidated or semantically migrated only where valid; it is never re-labeled as new `(n1,n2,n3)` evidence;
- first new target-size authorization follows v2 `n1`;
- operator-visible status makes clear that upstream state was reused and downstream target-size state was reset/migrated as applicable;
- incompatible/ambiguous historical state fails closed with the narrowest actionable rerun boundary.

Owning/affected surface:

- `_campaign_cli_core.py` config loading/normalization/stage completion/restart authorization;
- prepare/preflight receipt/status validation;
- DATA7/DATA8 materialization/reuse identity;
- target-size plan/state/evidence store migration/invalidation;
- any shared stage/config digest helpers;
- upgrade/restart/status tests.

Forbidden:

- rerunning all preparation solely because campaign schema/version or fidelity tuple changed;
- ignoring historical integrity checks;
- silently widening reuse across a preparation-affecting change;
- reusing pre-existing TRAIN2 checkpoints across incompatible full-horizon schedule identity.

Acceptance evidence is defined by Cases D1/D2/D3 in Section 6.

### O12-R1 - documentation/publication closeout

Parent O12 is unchanged but becomes an explicit rework blocker.

Required end state: no fixed-generation current normative document remains authoritative for a flexible runtime. Generated artifacts are rebuilt from canonical sources and validated. Documentation completion occurs only after executable RW3 acceptance.

## 5. Rework execution sequence and stage-local closure

Resume from the reviewed implementation; do not restart the original workplan from S0.

### RW0 - Rework characterization

Actions:

- record rework starting commit;
- add bug-reproducer tests for R1, R2, and R3 before or with their fixes;
- re-derive the actually affected rework surface from current callers/serializers/receipts/materialization stores;
- identify which parent-stage regression evidence remains valid and which executable changes invalidate it.

Closure:

- each review finding has a failing characterization or structural proof;
- no unknown persistence owner remains on prepare/preflight/DATA7/DATA8/target-size restart paths.

### RW1 - In-place upgrade and semantic identity repair

Assigned obligations: O10-R1, O13, plus parent O2/O3/O4/O5 where affected.

Actions:

- factor stage-scoped semantic identity;
- repair prepare/preflight completion compatibility;
- repair DATA7/DATA8 materialization binding;
- implement validated v1 -> v2 in-place re-authentication/migration/invalidation;
- preserve exact TRAIN2 schedule/checkpoint incompatibility rules;
- update status/restart messages and persistence schemas only as required.

Stage-local semantic closure:

- irrelevant downstream config changes cannot invalidate compatible preparation;
- preparation-affecting changes still invalidate correctly;
- no old fixed target-size evidence becomes new flexible evidence.

Stage-local functional closure before RW2:

- focused upgrade/reuse/invalidation tests pass;
- affected config/persistence/restart/materialization regressions pass;
- D1 and D3 bounded upgrade cases pass; D2 may complete in RW3 if full nondefault orchestration is not yet assembled.

### RW2 - SIZE-FIDELITY scientific correction

Assigned obligation: O7-R1.

Actions:

- make qualification consume and hard-check final-screen `n3` decision;
- align short-stage ordering/equivalence exactly with production;
- consolidate or reuse production stage-ordering semantics where justified;
- preserve full-`n` reference authority and `n3==n` physical deduplication.

Stage-local semantic closure:

- SIZE-FIDELITY cannot certify a funnel whose final-screen decision disagrees with the accepted full reference;
- calibration and production use the same stage ordering semantics.

Stage-local functional closure before RW3:

- final-screen/reference disagreement regression passes by rejecting the bad candidate;
- nondefault equivalence-width regression proves short finalists equal production semantics;
- complete SIZE-FIDELITY affected regression passes.

### RW3 - Assembled executable rework integration

Run parent Cases A/B/C plus new Cases D1/D2/D3 below through real product boundaries. Then run complete executable affected-surface regression and repository-required checks.

No documentation promotion begins until RW3 closes.

### RW4 - Documentation/publication reconciliation

Execute parent S7/O12 plus O12-R1 on the executable candidate that passed RW3.

Update current architecture/specs/guides/config examples/Stage-11 and dependency graphs/FINAL-GPU1 current material as applicable; regenerate tracked Markdown/PDF/manifest descendants; preserve archive/history.

Mechanical closure:

- documentation tests;
- local-link checks;
- canonical-source/generated equality or manifest hash checks;
- changed tracked PDF render/parse/visual QA;
- current-doc legacy/future-workplan leakage classification.

### RW5 - Final accepted-contract reconciliation and final affected-surface acceptance

On the same assembled candidate:

1. reconcile parent O1-O12 plus O7-R1/O10-R1/O12-R1/O13;
2. re-derive final affected behavioral surface from the final diff/callers/consumers;
3. rerun complete affected-surface regression after all executable changes;
4. rerun Cases A/B/C/D1/D2/D3;
5. run repository-required lint/type/static/package checks and broader suite if impact cannot be bounded;
6. rerun structural searches for duplicate epoch authority, whole-config over-invalidation, stale numeric APIs, old current-doc semantics, and obsolete adapters;
7. inspect for product-complexity regression or redundant migration/identity authorities.

Acceptance requires both semantic/conformance closure and functional closure. Unexecuted required checks are not passes.

## 6. Mandatory assembled integration cases

Parent Cases A/B/C remain mandatory:

### Case A - default fresh campaign

```text
fidelity=(1,3,10)
n=30
```

Exercise configuration -> policy -> stage authorization -> evidence admission -> survivor transitions -> final freeze -> production horizon -> progress/status.

### Case B - anti-hardcoding fresh campaign

```text
fidelity=(2,5,12)
n=40
```

Retain every parent Case-B assertion, including exact boundaries, full-40 schedule authentication, production-to-40, identity perturbations, eliminated-candidate no-work, and structure-epoch incremental accounting.

### Case C - role coincidence

```text
fidelity=(1,3,30)
n=30
```

Prove final-screen/reference role coincidence uses one physical checkpoint/evaluation while retaining both semantic roles.

### Case D1 - historical completed preflight -> default v2 upgrade

Starting state:

- historical v1/schema-less campaign;
- preparation and preflight marked complete under valid historical authorities;
- DATA7/DATA8 materializations present and authenticated;
- no incompatible TRAIN2 checkpoint reuse is required.

Upgrade:

```text
schema=v2
fidelity=(1,3,10)
n=30
```

Must prove:

1. prepare execution count does not increase;
2. preflight execution count does not increase;
3. compatible DATA7/DATA8 materialization bytes/content identity are reused, not rebuilt;
4. historical receipts/artifacts are validated before reuse;
5. old fixed target-size plan/evidence cannot satisfy new screen boundaries;
6. fidelity-dependent state is invalidated/migrated at the narrowest safe boundary;
7. first newly authorized target-size work is the coarse screen at epoch 1;
8. status/restart after migration reproduces the same next action;
9. no global-config-hash mismatch forces an unrelated upstream rerun.

### Case D2 - historical completed preflight -> nondefault v2 upgrade

Same starting state, upgraded to:

```text
schema=v2
fidelity=(2,5,12)
n=40
```

Must prove D1 reuse/invalidation properties plus:

- first new screen is epoch 2;
- full TRAIN2 schedule identity is 40 before training begins;
- no old n=30 TRAIN2 checkpoint can satisfy n=40 continuation if such a checkpoint fixture is supplied;
- production target remains 40.

### Case D3 - negative-control preparation change

Starting from the same historical campaign, change one field that demonstrably changes preparation/materialization semantics.

Must prove:

- semantic preparation identity changes;
- prepare/preflight/materialization reuse is rejected at the correct boundary;
- downstream reuse is not widened merely because migration machinery exists;
- error/status indicates the narrowest required rebuild/rerun boundary.

## 7. Mandatory focused/regression acceptance additions

### Upgrade/reuse identity

- fidelity-only change does not invalidate preparation/preflight/materialization;
- full-horizon-only change does not invalidate preparation/preflight when no preparation semantic depends on it;
- preparation-affecting change does invalidate preparation and downstream;
- presentation-only change does not invalidate scientific/preparation state;
- historical receipt/digest corruption rejects reuse;
- ambiguous historical state fails closed;
- old fixed target-size evidence cannot masquerade under new tuple;
- stage-scoped digest is stable for semantically identical normalized config.

### SIZE-FIDELITY scientific equivalence

- final-screen `n3` outcome is consumed as a hard qualification input;
- n3-vs-n disagreement fixture fails qualification;
- short-screen equivalence width matches production semantics when coarse and final tolerances differ;
- production reducer and SIZE-FIDELITY produce identical coarse/short/final decisions for the same bounded metric fixtures;
- full-reference metrics are from `n`;
- n3==n physical deduplication remains correct;
- existing recall/equivalence thresholds are unchanged.

### Regression breadth

At minimum cover all new/modified behavior and all plausibly affected existing behavior in:

- campaign configuration v1/v2 normalization;
- stage completion/restart/status;
- prepare/preflight authorization;
- DATA7/DATA8 materialization/reuse;
- target-size state/evidence migration and selection;
- TRAIN2 exact continuation and cross-horizon rejection;
- SIZE-FIDELITY1;
- PERF-P2R;
- progress/status reporting;
- public exports/serialization;
- documentation specification tests after RW4.

If shared `_campaign_cli_core.py` impact cannot be bounded confidently, run the broader available campaign/training-data suite.

## 8. Rework affected surface

Start from the reviewed implementation and expand by caller/consumer inspection. Expected additional rework surfaces include:

Executable/persistence:

- `mdstats/training_data/_campaign_cli_core.py`;
- campaign stage completion and prepare/preflight receipt validation;
- DATA7/DATA8 materialization identity/reuse helpers;
- target-size plan/state/evidence persistence;
- `mdstats/training_data/size_fidelity.py`;
- `mdstats/training_data/target_size_study.py` if shared production ordering/reduction is factored there;
- shared config/stage semantic digest utilities if introduced;
- restart/status serializers and consumers;
- relevant exports only if required by factoring.

Tests:

- campaign config/migration/restart/preflight tests;
- DATA7/DATA8 reuse/materialization tests;
- target-size persistence/identity tests;
- exact continuation/cross-horizon tests;
- SIZE-FIDELITY scientific tests;
- A/B/C/D assembled integration tests;
- affected documentation tests.

Documentation after RW3:

- all parent O12/S7 listed current docs/generated artifacts remain in scope.

## 9. Preservation and non-goals

Preserve the parent workplan's accepted science and product behavior, including candidate universe, MVQUAL2/REPAIR2 admission, funnel counts, seed aggregation, target-only selection, deterministic equivalence-aware ordering, typed failures, exact continuation, PERF-P2R structure-epoch accounting, and GPU qualification deferral.

Do not:

- redesign the flexible `(n1,n2,n3)+n` architecture;
- change default `(1,3,10)/30` merely to avoid fixing qualification;
- weaken recall/equivalence criteria;
- retime TRAIN2 LR/warm-up to make the default pass;
- re-run expensive preparation when semantic compatibility proves reuse;
- over-reuse preparation when a preparation authority changed;
- use production qualification as a substitute for regression/integration;
- add a second global/stage identity system when existing digest infrastructure can be refactored into semantic dependency-scoped authorities.

## 10. Reopen only on evidence

Retain every parent redesign trigger. Add these bounded triggers:

1. persisted historical prepare/preflight evidence is insufficient to prove semantic compatibility without recomputing an upstream stage;
2. DATA7/DATA8 materialization actually depends on fidelity or full-horizon policy through a currently undocumented execution path;
3. sharing production ordering semantics with SIZE-FIDELITY would create an unacceptable circular dependency and exact equivalence cannot otherwise be guaranteed;
4. representative scientific evidence rejects the default under unchanged hard criteria.

If a trigger fires, reopen only that affected surface. Do not discard still-valid flexible architecture, upstream preparation, or independent evidence.

## 11. Production qualification disposition

Unchanged from the parent workplan.

Required for rework acceptance: deterministic focused tests, stage-local affected regression after each executable RW stage, bounded restart/upgrade/integration cases, final affected-surface regression/integration, and documentation publication verification.

Deferred: long real-data GPU qualification, machine-specific production performance/resource characterization, and final CUDA/CuEquivariance qualification under FINAL-GPU1.

## 12. Final rework handoff checklist

The implementation must not be declared complete until all applicable items are closed:

- [ ] Rework started from recorded implementation head and valid prior evidence was reused only where unaffected.
- [ ] Stage-scoped semantic identity replaces whole-config over-invalidation for preparation/reuse decisions.
- [ ] Historical prepare/preflight receipts are validated before in-place reuse.
- [ ] Fidelity-only or full-horizon-only migration does not rerun semantically unchanged preparation/preflight.
- [ ] DATA7/DATA8 materialization is not bound to fidelity-only authority.
- [ ] Preparation-affecting changes still invalidate the correct upstream/downstream frontier.
- [ ] Old fixed target-size evidence cannot satisfy new flexible boundaries.
- [ ] D1 default post-preflight upgrade begins new target-size work at epoch 1 without upstream rerun.
- [ ] D2 nondefault post-preflight upgrade begins at epoch 2, preserves upstream work, and establishes full-40 training identity.
- [ ] D3 negative-control preparation change rejects unsafe reuse.
- [ ] SIZE-FIDELITY hard-checks final-screen `n3` against full-reference `n`.
- [ ] SIZE-FIDELITY short-stage equivalence/order exactly matches production semantics.
- [ ] n3==n role coincidence deduplicates physical work while retaining both semantic roles.
- [ ] Parent Cases A/B/C pass through real assembled boundaries.
- [ ] Complete executable affected-surface regression passes after rework.
- [ ] Current documentation/specs/guides/config examples are reconciled after executable acceptance.
- [ ] Generated documentation artifacts are regenerated and verified.
- [ ] Final parent O1-O12 plus rework obligations reconcile with no omitted authority or stale fallback.
- [ ] Repository-required checks and broader suite where needed pass.
- [ ] Heavy GPU production qualification remains explicitly deferred and is not claimed.

## 13. Handoff closure statement

This rework plan closes the independent-review gaps without reopening the accepted flexible-fidelity architecture. The main new product requirement is semantic dependency-scoped upgrade/reuse: completed upstream preparation remains reusable across downstream fidelity-generation changes when and only when persisted evidence proves semantic compatibility. The scientific repair requires SIZE-FIDELITY1 to emulate the exact production funnel and hard-qualify the final screen against the full reference. Documentation publication and fresh assembled regression/integration are mandatory closeout gates.
