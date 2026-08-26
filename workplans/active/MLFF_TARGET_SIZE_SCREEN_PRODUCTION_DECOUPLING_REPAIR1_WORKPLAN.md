---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-SCREEN-PRODUCTION-DECOUPLING-REPAIR1
protocol_version: 5.7.0
status: active
created_date: 2026-08-25
reviewed_head: 5916adb71adc7818b2969904c9486dbf90c8ff40
parent_workplan: ../archive/MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md
reopens: acceptance-and-local-repair-only
---

# MLFF Target-Size Screen / Production Decoupling Repair-1 Workplan

## Objective

Close the blocking independent-review finding on the completed target-size screen/production-horizon decoupling implementation by replacing proxy acceptance with bounded **real-owner** persistence, restart, migration, authorization, and runtime-plan integration tests, and repair any concrete local product defect those tests expose.

This workplan does **not** reopen the accepted decoupling architecture. The implementation at reviewed head `5916adb71adc7818b2969904c9486dbf90c8ff40` is substantially conformant at the source/design level. The no-pass is caused by unestablished high-risk product claims at real orchestration/persistence boundaries, especially historical/pre-decoupling compatibility and config-change restart behavior.

Successful closure requires evidence that the real product path—not a helper-level reimplementation—preserves the intended scientific state and authorizes exactly the intended screen/production work.

## Routing and precedence

This is an **implementation nonconformance / acceptance-repair** workplan under the architecture frozen by `../archive/MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md` and the current architecture/specification documents.

The parent workplan remains the scientific/product authority. This Repair-1 plan reopens only:

- G6 proxy-proof assembled acceptance;
- any local executable defect exposed by that acceptance;
- G7 closeout status insofar as it depended on unproven G6 claims.

Do not restart the original architecture search or rewrite already-correct screen/production semantics merely because acceptance evidence was insufficient.

## Independent-review diagnosis

### Finding R1 — assembled target-size selection acceptance bypasses the runtime/authorization owner

The current persisted-funnel acceptance patches the production training/evaluation entry points and preflight authorization, then manufactures boundary evidence directly. That proves target-size reduction/state transitions, but it does not prove that the assembled product actually builds a screen-local `n3` TRAIN2 budget, restricts candidate authorization after each reduction, resumes the same surviving trajectory, or prevents eliminated candidates from receiving later work.

A broken `_build_campaign`, preflight authorization, DATA8 schedule compatibility, TRAIN2 policy assembly, runtime-plan budget, or continuation owner could therefore remain green.

### Finding R2 — config-change frontier acceptance calls the invalidation helper directly

The current frontier test changes TOML and proves target-size study identity behavior, but then invokes `_invalidate_train2_downstream_state(...)` directly. That cannot establish that normal close/reopen/config reconciliation detects the change and chooses the correct preservation/invalidation frontier.

The high-value product claim is the caller/orchestration behavior, not whether the helper deletes records when explicitly asked.

### Finding R3 — historical/pre-decoupling migration acceptance replaces most compatibility owners

The current migration fixture uses a custom store and patches preparation-contract comparison, DATA8 discovery, target-size reconstruction, DATA8 matrix validation, and stage-config identity. Those are precisely the owners whose real behavior determines whether a historical campaign can preserve expensive unchanged scientific materialization while invalidating obsolete screen/schedule state.

The current test therefore cannot distinguish:

```text
correct narrow scientific reuse + schedule/job regeneration
```

from:

```text
unnecessary expensive DATA7/DATA8 rebuild
```

or from an unsafe compatibility bypass.

### Finding R4 — cross-role restart isolation needs assembled companion evidence

Run-ID namespace separation is correctly implemented and unit-tested, but final acceptance should exercise the actual TRAIN2 companion/restart owner so a screen checkpoint cannot satisfy production restart, production state cannot satisfy screen restart, and normal `n1 -> n2 -> n3` screen continuation still succeeds.

## Frozen product decisions

The following remain unchanged and implementation must not reinterpret them:

1. Current executable geometry is:

   ```text
   0 < n1 < n2 < n3 < n
   ```

2. Default screen is `1 -> 3 -> 10` with screen scheduler/budget horizon `10`.
3. Default production is a fresh selected-size campaign with horizon `30`.
4. Screen boundaries for one surviving `(size, seed)` are exact continuation of one screen trajectory; they are not independent retrainings.
5. Candidate multiplicity shrinks `q -> min(q,4) -> 2 -> 1`; eliminated or scientifically failed candidates receive no later screen work.
6. No target-size screen execution is authorized beyond `n3`.
7. Production model/optimizer/scheduler/RNG state is fresh and does not continue the final screen checkpoint.
8. Screen and production run/filesystem/restart namespaces remain distinct.
9. Production `n` does not enter target-size study identity, screen budget/schedule identity, or DATA7/DATA8 candidate scientific authority.
10. Other scientifically material training parameters that affect screen ranking remain screen-authoritative.
11. A production-`n`-only change preserves a valid current screen/selection and invalidates production-dependent state only.
12. Any `n1/n2/n3` change invalidates current screen evidence/selection and restarts screening from configured `n1`, while scientifically unchanged preparation material may be reused.
13. Historical fixed and pre-decoupling flexible screen/checkpoint/evaluation/selection state is not relabeled current.
14. Routine target-size selection does not execute exhaustive SIZE-FIDELITY full-reference calibration.
15. Full production/GPU qualification remains deferred; Repair-1 requires bounded functional integration only.

## Clarified scientific-materialization preservation boundary

The original workplan's preservation intent is retained but made mechanically precise so the implementer does not have to choose between unsafe reuse and unnecessary expensive recomputation.

When only screen fidelity/horizon generation or production `n` changes and preparation science is otherwise identical:

### Must be preserved/reused

- REPAIR2 and MVQUAL scientific authorities;
- policy-independent candidate-prefix authority;
- DATA7 scientific selection/content whose identity does not depend on TRAIN2 schedule;
- DATA8 **scientific corpus payloads** derived from the same candidate prefixes, including target/replay ExtXYZ data and their scientific content/tree-entry digests where unchanged;
- expensive upstream prediction/selection/materialization work that is not scientifically affected by the changed schedule role.

### May/must be regenerated when their authority changed

- schedule/budget-dependent `mace_config.yaml` or equivalent trainer configuration;
- run scripts/command realization containing the schedule horizon;
- job/protocol manifests and bundle/plan digests that include those schedule-dependent files or policy digests;
- screen/production run plans, companions, checkpoints, evaluations, ranking, selection, and downstream execution state as required by the exact invalidation frontier.

Therefore **full DATA8 bundle/tree byte identity is not required** when schedule-bearing realization files legitimately change. The required invariant is: unchanged expensive scientific payloads are reused byte-for-byte and are not recomputed merely to change a scheduler/job realization.

If current ownership combines expensive scientific payload materialization and cheap schedule realization so tightly that this invariant cannot be achieved, refactor that local ownership boundary minimally rather than weakening validation or accepting old full-`n` protocols as current.

## Repair design: one reusable bounded real-campaign harness

Implement one shared test fixture/harness that constructs a small deterministic campaign while executing the real repository owners needed by the claims below.

The harness must use:

- real generated/current TOML and `_load_config` normalization;
- real filesystem paths/workspace;
- real SQLite `CampaignStore` for persistence/reopen claims;
- real REPAIR2/MVQUAL/current target-size authority classes;
- real DATA7/DATA8 record/materialization structures sufficient for the production compatibility owners to inspect them;
- real `_ensure_target_size_study` or its current production successor;
- real DATA8 discovery/integrity/schedule compatibility owner when reuse is the claim;
- real `_require_train2_preflight_authorization` when training authorization is the claim;
- real `_build_campaign` and current training run/job owner;
- real TRAIN2 budget/LR/optimizer/runtime-plan/continuation-companion assembly when horizon/restart behavior is the claim;
- real target-size evidence reduction and `CampaignStore` persistence;
- real normal close/reopen/config-change reconciliation/next-operation caller when invalidation is the claim.

Use bounded synthetic scientific contents and tiny file payloads. The harness is not required to run actual long MACE training.

### Allowed test-double boundary

Only dependencies **below/outside** the repository semantic owners above may be replaced, including:

- external/expensive MACE numerical training step/subprocess after the real run/job/runtime plan and authorization are fixed;
- expensive prediction/evaluation numerical values after the real evaluation authorization and checkpoint identity are fixed;
- GPU execution;
- reduced synthetic scientific data volume.

The fake training boundary must consume the real authorized run/runtime plan and emit minimally valid checkpoint/runtime artifacts through the same filesystem/serialization interface expected by the real continuation/evaluation consumers. It must not directly mutate target-size study state or manufacture a post-reduction plan.

### Forbidden substitutions for gate-closing tests

The gate-closing acceptance module(s) must not monkeypatch, replace, custom-reimplement, or bypass the following owners when their behavior is the claim:

- `_load_config` / current config normalization and geometry validation;
- `CampaignStore` or durable storage/reopen behavior;
- `_ensure_target_size_study` / current target-size construction and generation reconciliation owner;
- `_current_data8_entries` or current DATA8 discovery owner;
- `_validate_train2_data8_matrix` / current matrix/scientific compatibility owner;
- `_train2_data8_schedule_matches_config` / current schedule compatibility owner;
- `_require_train2_preflight_authorization` for screen authorization acceptance;
- `_build_campaign` / campaign run-plan owner;
- `_train2_policy_set`, `_optimizer_policy`, and the current runtime-plan budget/schedule owner for horizon acceptance;
- target-size `next_training_sizes` / `next_training_epoch` caller path and evidence reducers;
- normal restart/config-change/next-operation reconciliation caller;
- `_invalidate_train2_downstream_state` as a direct substitute for proving its production caller invokes the correct frontier;
- historical candidate-authority authentication and supported-generation compatibility owner;
- PERF-P2R/production consumer when fresh screen-to-production handoff is the claim.

A dedicated small structural guard may inspect only the gate-closing acceptance test module(s) and fail if they patch one of these named owners. Do not create a repository-wide mock ban or general-purpose test framework.

## Implementation obligations

### O-R1 — Build the bounded real-owner campaign fixture

**Protected concern:** all later repair gates need a reusable fixture that cannot pass while production owners are broken.

**Required end state:** one disk-backed, deterministic, inexpensive fixture can create current and historical campaign states, close/reopen them, edit TOML, invoke normal orchestration, and capture real authorization/runtime-plan decisions.

**Implementation consequences:**

- use real `CampaignStore`, not `_MigrationStore`/in-memory substitutes, for persistence claims;
- use real repository serializers/digests for current records;
- for historical generation fixtures, use authentic serialized payloads produced by the historical authoritative serializer or a frozen golden payload captured from the relevant pre-decoupling commit; do not hand-reimplement the old digest formula in the acceptance harness;
- isolate only the external numerical execution seam;
- instrument observations without replacing decisions: spies/wrappers may record real return values/calls if they delegate to the original owner unchanged.

**Acceptance:** intentionally perturb one semantic owner input (for example wrong screen budget in a DATA8 protocol) and prove the real harness fails closed. This establishes that the fixture is sensitive to owner breakage.

### O-R2 — Real fresh default and nondefault screening authorization

**Protected concern:** reducer-only tests do not prove runtime budget and candidate pruning.

**Required end state:** assembled current selection proves the real product authorizes exactly the successive-fidelity workload.

**Cases:**

- default `(1,3,10)/30`;
- nondefault `(2,5,12)/40`.

**Required observable evidence per authorized `(size,seed)` run:**

- screen training budget planned epochs equals `n3` (`10` or `12`), never production `n`;
- optimizer/trainer max-epoch authority and LR planned-update horizon match that same screen horizon;
- current execution limit equals active boundary;
- initial population is every qualified size × screen seed;
- after coarse reduction, only survivors are authorized again;
- after short reduction, only finalists are authorized again;
- eliminated candidates have no later execution attempt/run authorization;
- surviving continuation uses the same screen run identity and authentic parent checkpoint/optimizer/RNG lineage;
- no screen run is authorized beyond `n3`;
- `select-target-size` freezes selection and returns before production training.

For a representative `q=5`, `s=2`, default funnel, the authorization record must be consistent with the bounded successful-work geometry:

```text
5*2*1 + 4*2*(3-1) + 2*2*(10-3) = 54 candidate-epochs maximum
```

Do not require actual 54 physical MACE epochs; bounded fake numerical stepping may emit the real authorized endpoint artifacts.

### O-R3 — Real production-`n`-only restart frontiers

**Protected concern:** direct helper invocation does not prove normal config reconciliation.

Use actual TOML edit + store close + new process/store reopen + normal production reconciliation. Do not call `_invalidate_train2_downstream_state` directly in the acceptance test.

#### Case R3A — change `n:30 -> 40` during partial screen

Persist a valid current screen after `n1` (and preferably parameterize one `n2` case), close the store, edit actual TOML production horizon only, reopen normally.

Required result:

- same target-size study content/selection authority remains valid;
- same screen horizon remains `10`;
- same surviving screen run/checkpoint lineage resumes rather than restarting at epoch 0;
- DATA7/DATA8 scientific payload identities remain unchanged;
- screen schedule/runtime owner still authorizes the next boundary on horizon 10;
- eventual post-selection production plan uses horizon 40.

#### Case R3B — change `n:30 -> 40` after completed selection

Required result:

- target-size screen evidence and selected target size remain preserved;
- DATA7/DATA8 scientific payload identities remain preserved;
- old production budget/schedule/run/checkpoint/evaluation dependent state is invalidated through the normal caller;
- fresh production authorization uses horizon 40, selected size only, and no screen continuation state.

### O-R4 — Real screen-boundary restart frontiers

Independently change `n1`, `n2`, and `n3` through actual TOML close/reopen/reconciliation.

Required result:

- scientifically unchanged REPAIR2/MVQUAL/DATA7/DATA8 corpus payloads are preserved;
- current screen evidence/selection is invalidated;
- new screen starts from configured `n1`;
- changing `n3` invalidates even earlier `n1`/`n2` screen evidence because the entire screen LR/budget trajectory changed;
- schedule-dependent job/config realization is regenerated to the new screen horizon when required;
- no old screen checkpoint is silently accepted under a new schedule digest.

### O-R5 — Real historical fixed/pre-decoupling generation upgrade

**Protected concern:** this is the highest-risk expensive-reuse and fail-closed compatibility boundary.

Exercise at least two real persisted populations:

1. authenticated fixed predecessor with historical `(3,10,30)/30` semantics;
2. pre-decoupling flexible `1/3/10` screen evidence/jobs bound to production/full horizon 30.

The fixtures must contain authentic historical schema/digest material. Prefer frozen golden serialized payloads generated by the corresponding historical code rather than current-test reimplementation of legacy digests.

Run the actual current compatibility/restart path using real `CampaignStore`, historical authentication, DATA8 discovery/matrix validation, study reconstruction, and next-operation logic.

Required result:

- historical generation is correctly recognized or fails closed if unsupported/ambiguous;
- expensive scientific REPAIR2/MVQUAL/DATA7/DATA8 corpus payloads that remain valid are reused byte-for-byte;
- old schedule-dependent job/config realization may be regenerated for screen horizon 10;
- old historical screen checkpoints/optimizer/RNG/evaluation/ranking/selection are not current authority;
- fresh current target-size study defaults/configures to current fidelity and first authorized boundary `n1` (default 1);
- no full-30 screen protocol is accepted as a current screen protocol;
- no scientifically unchanged candidate corpus is rebuilt merely because schedule-bearing realization changed.

If this test exposes unnecessary expensive recomputation, repair the owning preparation/materialization boundary by separating stable scientific payload reuse from cheap schedule/job regeneration. Do **not** weaken schedule validation and do **not** label a horizon-30 execution protocol as current horizon-10 authority.

### O-R6 — Real cross-role restart isolation

Use actual TRAIN2 runtime summary/companion/checkpoint serialization with overlapping selected size and seed.

Required cases:

```text
screen n1 checkpoint -> screen n2 continuation    ACCEPT
screen n2 checkpoint -> screen n3 continuation    ACCEPT
screen checkpoint     -> production restart       REJECT
production checkpoint -> screen restart           REJECT
```

The rejection must come from real role/run/budget/restart identity validation rather than the test pre-filtering the candidate.

### O-R7 — Targeted anti-bypass integrity check

Add the minimum robust guard needed to prevent the same acceptance drift from recurring.

Recommended realization: a focused AST/source assertion over the Repair-1 gate-closing integration test module(s) that rejects monkeypatch/mock replacement of the forbidden semantic-owner names listed above. The guard may allow patching the explicitly named external-compute seam(s).

Do not create global mocking policy or scan unrelated unit tests.

### O-R8 — Repair only demonstrated product defects

If O-R2 through O-R6 fail because a production owner is wrong, fix that owner minimally under the frozen design.

Examples of legitimate local repairs include:

- separating scientific DATA8 payload reuse from regenerated schedule-bearing job files;
- correcting normal config-change caller logic so production `n` does not invalidate screen state;
- correcting historical generation detection/re-authentication;
- correcting role-aware companion/restart validation;
- correcting authorization so eliminated candidates cannot receive later runs.

Do not change frozen architecture to make the acceptance fixture easier.

## Expected affected surface

The repair may touch, depending on real-owner failures:

- `tests/test_mlff_flexible_fidelity.py` and/or a new dedicated real-owner integration test module;
- campaign CLI orchestration/restart/config reconciliation in `mdstats/training_data/_campaign_cli_core.py`;
- DATA7/DATA8 preparation/materialization ownership if scientific/schedule realization is currently over-coupled;
- `campaign_control.py` only if role namespace/restart ownership is incomplete;
- TRAIN2 runtime/companion code only if cross-role or continuation validation fails;
- historical target-size compatibility/migration code;
- target-size workplan/active index closeout state;
- documentation only if an actual product semantic clarification must be reflected.

Do not churn already-correct target-size policy/reducer/PERF-P2R code without evidence from the real-owner tests.

## Gate sequence

### G-R0 — Reopen acceptance without reopening architecture

- install this Repair-1 plan as active;
- treat the parent decoupling architecture as frozen;
- mark prior `216 passed, 1 skipped` evidence as still-valid regression evidence for unaffected behavior, but **not** as closure for R1-R4;
- identify the exact lowest external-compute seam that can be faked while real orchestration/runtime owners execute.

**Gate:** implementer can name the real owner path and allowed double boundary for each R2-R6 claim before changing product code.

### G-R1 — Build and validate the real-owner fixture

Implement O-R1 and O-R7 first.

Run focused fixture/anti-bypass tests and the relevant campaign-store/runtime unit regression.

**Gate:** fixture is disk-backed, exercises real owners, fails closed under one deliberate incompatible schedule/identity perturbation, and cannot patch forbidden owners.

### G-R2 — Fresh/default/nondefault assembled screening

Implement O-R2, repairing product code only if this real path exposes a failure.

Run stage-local affected regression for target-size, campaign orchestration, TRAIN2 runtime, continuation, and progress.

**Gate:** default and nondefault authorization geometry, screen budgets, continuation, pruning, and command termination are proven through real owners.

### G-R3 — Current-generation restart/invalidation frontiers

Implement O-R3 and O-R4 using actual TOML edits and real close/reopen reconciliation.

Run stage-local persistence/config/restart/materialization regression.

**Gate:** production-`n` changes preserve valid screen/selection; fidelity changes restart screen from `n1`; scientific corpus reuse and schedule/job regeneration boundaries are exact.

### G-R4 — Historical generation upgrade and expensive-data preservation

Implement O-R5.

Use authentic historical golden payloads and real current compatibility owners. Repair the data/materialization boundary only if necessary.

Run stage-local predecessor/DATA7/DATA8/preflight/prepare/restart regression.

**Gate:** both historical populations either migrate safely as specified or fail closed for a genuinely unsupported generation; no acceptance proxy remains; expensive unchanged scientific corpus is not rebuilt.

### G-R5 — Cross-role restart isolation

Implement O-R6 and run stage-local TRAIN2 runtime/companion/campaign-control regression.

**Gate:** screen continuation succeeds while both cross-role restart directions fail closed through the real companion owner.

### G-R6 — Final assembled acceptance

On one final assembled candidate:

1. reconcile O-R1 through O-R8;
2. re-derive affected behavioral surface from the actual repair diff;
3. rerun all Repair-1 real-owner integration cases fresh;
4. rerun the complete affected CPU/control-plane regression including the previous `216 passed, 1 skipped` slice or its current superseding set;
5. run repository-required checks and broader available regression if impact cannot be bounded;
6. record environment-dependent real-LTA/GPU/long production checks as unavailable/deferred rather than passed;
7. inspect gate-closing tests to confirm no forbidden semantic owner is patched or custom-reimplemented.

**Gate:** no blocking owner claim relies on proxy evidence and no affected regression is failing/unexecuted.

### G-R7 — Closeout

Only after G-R6:

- mark Repair-1 complete and archive it;
- leave the parent decoupling workplan archived as completed architecture history;
- update `workplans/active/README.md` accordingly;
- retain full GPU/long production qualification as FINAL-GPU1 deferred work.

## Task-specific acceptance summary

Repair-1 is accepted only if all of the following are executed through the required real owners:

- **A:** default `(1,3,10)/30` screen uses planned horizon 10 and exact shrinking authorization;
- **B:** nondefault `(2,5,12)/40` screen uses planned horizon 12 and fresh production 40;
- **C:** mid-screen production `n:30->40` preserves/resumes same horizon-10 screen trajectory;
- **D:** post-selection production `n:30->40` preserves selection and invalidates/rebuilds production state only;
- **E:** independent `n1`, `n2`, `n3` changes preserve unchanged scientific corpus but restart screen from new `n1`;
- **F:** authenticated fixed predecessor upgrades to fresh current screen without relabeling historical screen state;
- **G:** pre-decoupling flexible 1/3/10-on-30 state cannot be relabeled current 1/3/10-on-10 state;
- **H:** unchanged expensive scientific DATA7/DATA8 corpus payloads survive F/G without unnecessary recomputation while schedule-bearing realization is regenerated when required;
- **I:** same-size/same-seed screen and production restart identities are mutually incompatible, while normal screen continuation remains compatible;
- **J:** final affected regression/integration passes with no gate-closing proxy substitution.

## Implementation authority

### Frozen

All scientific/product decisions listed under `Frozen product decisions`, the clarified scientific-payload preservation boundary, and the real-owner/test-double acceptance boundaries in this Repair-1 plan.

### Delegated

- exact name/location of the bounded integration fixture;
- exact synthetic scientific payload sizes/content;
- exact lowest external MACE execution seam used as the allowed fake boundary;
- whether call observation uses spies, logs, execution records, or persisted runtime summaries, provided real owner decisions execute unchanged;
- exact historical golden-fixture storage format;
- exact local refactor used to separate stable scientific payloads from schedule/job realization if the real migration test proves it necessary;
- exact targeted anti-bypass implementation.

### Reopen only on evidence

Reopen design only if a real-owner Repair-1 test proves one of these frozen premises false:

- the generic TRAIN2 runtime cannot represent a screen-local `n3` schedule with boundary pause/resume semantics;
- current DATA7/DATA8 storage cannot preserve scientifically unchanged corpus content without an incompatible fundamental persistence redesign;
- authentic supported historical records lack enough information to re-authenticate stable scientific content safely;
- production training is governed elsewhere by an irreconcilable contract requiring continuation from screen state;
- normal orchestration cannot distinguish screen and production roles without changing a governed external interface beyond this workplan.

A failing proxy test, legacy fixture inconvenience, test runtime cost, or the need to regenerate schedule-bearing files is **not** a redesign trigger.

## Handoff closure

```text
independent review blocker:
  high-risk persistence/restart/migration/orchestration claims were proxy-tested

+ accepted architecture:
  screen horizon n3; production horizon n; exact screen continuation;
  fresh production; policy-independent candidate scientific authority

+ clarified preservation boundary:
  preserve expensive scientific payloads;
  regenerate cheap schedule/job realization when authority changes

+ repair design:
  one reusable real CampaignStore/config/DATA8/orchestration/runtime harness;
  fake only external numerical compute;
  targeted anti-bypass guard

-> O-R1..O-R8
-> G-R0..G-R7
-> acceptance A..J
```

This Repair-1 workplan is intentionally narrower than the parent architecture plan. Its purpose is to make successful implementation review depend on the real product behavior that was previously unestablished, while minimizing unnecessary rework of already-correct code.
