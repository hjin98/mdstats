---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P6-R5
parent_package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
package_revision: 5
status: active
amended_date: 2026-08-30
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
amends:
  - P6_REVISION_3_BASE.md
  - P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md
precedence: this amendment overrides revision 3 and revision 4 only where explicitly stated; all other obligations remain binding
---

# P6 revision 5 amendment — cleanup/cutover closure and independent-review repairs

## 1. Purpose and bounded Design correction

Independent Software Design review found that the P6 implementation made one justified architectural retirement and then overextended that retirement into product-capability deletion.

The corrected distinction is frozen here:

1. The old `SELECT2` / `verify` orchestration, its physical-fallback selection behavior, and its V5/V6 `target_size_study_digest` / `target_data_role_freeze_digest` / label-domain lineage are obsolete and **must remain retired**.
2. Deployment parity, physical PES/relaxation/dynamics validation, uncertainty calibration, and one-shot locked testing remain materially justified MLFF product capabilities. They are **not** to be restored inside P6 using the retired architecture. They will be rebuilt by the separate successor package `CODE-MLFF-TARGET-SIZE-V7-P7` after P6 cleanup/cutover closure passes independent review.
3. P6 therefore closes the **destructive retirement/current-generation cutover and assembled P1-P5 functional lifecycle**, not the final downstream qualification capability or final release/product closure.

This is a bounded Design reopen of the downstream-qualification ownership boundary only. It does not reopen P1-P5 target-size science, selected-set semantics, CV semantics, fresh final-production semantics, current-generation persistence, or the destructive V5/V6 target-size compatibility policy.

### 1.1 Consequence for P6 acceptance language

Revision-3 wording that calls P6 an "assembled final closure" is narrowed as follows:

```text
P6 PASS = destructive cleanup/current-generation cutover + current P1-P5 assembled
          functional/restart/public-surface closure

P6 PASS != downstream deployment/physical/calibration/locked qualification implemented
P6 PASS != final release qualification
P6 PASS != completion of the parent's final downstream-evidence obligation
```

P6 evidence and review verdicts must use language such as **P6 cleanup/cutover functional acceptance**. They must not claim that downstream qualification is implemented or that the complete parent product lifecycle is release-ready.

The parent workplan remains open for the downstream-evidence obligation until P7 or an explicitly accepted successor closes it.

### 1.2 R6 correction for the deleted downstream modules

Revision-3 R6 preservation remains valid for independently supported product implementations whose architecture still conforms to the current generation. For the deleted modules `select2`, `deploy_verify`, `pes_verify`, `relax_verify`, `dyn_verify`, and `locked_test2`, the disposition is refined:

- their old **runtime/persistence/orchestration implementations** are R1 because they bind retired target-size/domain authority or permit post-development physical fallback selection;
- the **underlying product capabilities** are preserved as open product obligations and are owned by P7, not deleted from the durable product intent;
- P6 must not add compatibility wrappers, aliases, migration readers, shadow records, or a temporary replacement verification state machine merely to keep the old capability reachable;
- P6 must preserve reusable independent R6 machinery needed by the clean replacement, including current MACE deployment/export/runtime qualification, artifact staging, retained physical-observable analysis owners, resource/scheduling owners, and current post-selection persistence/currentness owners.

The old `SELECT2` fallback rule is explicitly forbidden from returning: after future final-production publication freezes, downstream qualification may reject that frozen publication but may not select a different seed/checkpoint/member based on downstream evidence.

## 2. Remaining P6 implementation gaps and required corrected end state

The current P6 implementation is not accepted until every obligation below closes on one assembled candidate.

### 2.1 Remove surviving current V5 target-size contract/public-surface leakage

Current production source still exposes V5-named prepare-receipt/current-contract identifiers and comments that describe historical receipt migration as admissible. This violates revision-3 Sections 1.2, 1.3, 2.3, 4.1, and 6.

Required end state:

- no current-write/current-authority prepare schema or contract is named `target-size-v5`;
- current prepare/restart identity uses a current-generation/V7-neutral name and semantics;
- old V5/V6 receipt identifiers may survive only inside a **narrow private reject-only detector** when strictly needed to recognize obsolete derived target-size state before reuse;
- a reject-only detector may inspect only metadata/header/version sufficient to reject and may not semantically deserialize, migrate, reconstruct, normalize, or rebind old target-size state;
- no V5/V6 target-size prepare receipt/contract symbol is exported through `mdstats`, `mdstats.training_data`, `mdstats.training_data.campaign_cli`, `_campaign_cli_core.__all__`, or another current public facade;
- a historical identifier in `docs/history/` is not an offender; a current production occurrence must be either removed or explicitly allowlisted as reject-only and structurally proven non-authoritative.

The repair must include the automatically re-exporting `campaign_cli` facade. The existing top-level-only public-symbol test is insufficient.

Acceptance evidence:

1. structural public-export test over all three public surfaces (`mdstats`, `mdstats.training_data`, campaign CLI facade);
2. current-production source scan with an exact allowlist for reject-only obsolete-generation detection;
3. current prepare/reopen focused regression;
4. P5A6 -> P6 compatibility qualification from Section 3, proving the cleanup did not break valid current state.

### 2.2 Make CLI parser, guide, status, `advance`, help, and user guide one contract

Current `GUIDE_TEXT` still advertises retired `preflight` and `verify` commands and describes `prepare` as building the old screening DATA7/DATA8 matrix even though the parser exposes neither command and the current lifecycle is different.

Required current P6 command lifecycle:

```text
init
 -> doctor
 -> prepare
 -> select-target-size
 -> cross-validate
 -> train-production
```

`status`, `advance`, parser help, `guide`, the campaign user guide, and actionable error messages must project the same current owners. `storage` remains an orthogonal management command, not a scientific lifecycle stage.

P6 must **not** advertise the future P7 `qualification` interface as available before P7 exists. After `train-production`, current P6 may report that downstream production qualification is not implemented in the current runtime / remains a later release obligation, but it may not dispatch a nonexistent verifier.

Acceptance evidence must execute the real parser/dispatch surface and assert:

- the exact current subcommand set;
- `guide` contains no retired `preflight` or `verify` step;
- `prepare` help describes the neutral/current substrate and no old per-domain DATA7/DATA8 screening matrix;
- `status` and `advance` derive the same terminal lifecycle;
- generated/user documentation agrees with the parser.

### 2.3 Reconcile generated configuration and `campaign.toml.example` with actual V7 policy

The current generated configuration still states a fixed `128..16384` target-size universe and forbids ceilings above 16384, while the V7 runtime resolves configurable `target_size_power_min` / `target_size_power_max`. It also continues to generate pre-target per-method CV knobs alongside the canonical post-selection CV surface and carries verification/performance knobs for a deleted campaign verification lifecycle.

Required end state:

- `[target_data.size_convergence]` generated/current examples expose the actual current configurable ladder contract, including `target_size_power_min`, `target_size_power_max`, `evaluation_size_powers`, and `fidelity_epochs` with accurate semantics;
- no generated/current example claims a hidden fixed 16384 scientific ceiling;
- optimizer seeds remain owned by the sole enabled training method and are not duplicated as a target-size seed namespace;
- current post-selection CV authoring is owned by the canonical `[post_selection.cv]` policy surface;
- retired pre-target CV fold-count/partition-seed knobs are not generated or documented as current target-size/CV authority. If a legacy field must remain readable for exact P5A6 current-generation compatibility or an independently supported non-target product, it is a read-only compatibility input with no current generated-authoring role and no target-size authority;
- configuration sections/keys belonging only to the deleted `verify` lifecycle are removed from current generated examples/help. Independently supported generic export/precision/resource settings may remain only under their actual current owner;
- parsing/normalization has one canonical current semantic resolution. A legacy alias cannot silently become a new current scientific setting.

Acceptance evidence:

1. `init`-generated TOML parses and resolves the expected configurable ladder;
2. power ceilings above 14 are accepted when the configured population/resources otherwise permit them; no hidden 16384 guard exists in generated/config policy;
3. generated config and `campaign.toml.example` contain no retired current-authority claims;
4. CV-only config changes leave P4 `N_selected/T_selected` current and invalidate only CV/final descendants as required by the existing P6 invalidation matrix;
5. target-size power/M-ladder/fidelity changes invalidate target-size descendants through real current owners.

### 2.4 Semantically rewrite stale current architecture/user documentation

A rendering-successful PDF is not semantic acceptance. Current Parts III, VI, and VII still contain retired per-domain/multi-view/DATA7/MLCV/TARGET-SIZE-V5 semantics.

Required current architecture after P6:

```text
canonical source/frame/numerical-label authority
 -> neutral statistical/correlation substrate
 -> one P_train/M3 split
 -> one pi_train and one nested pi_eval M1 subset M2 subset M3
 -> one common target-size preparation
 -> paired-seed controlled screen
 -> one N_selected + exact global T_selected
 -> post-selection CV derived only after selection and operating on T_selected
 -> fresh final production on full T_selected
 -> currentness-fenced final-production evidence
```

Specific corrections:

- **Part III**: remove the claim that each pre-target fold/final domain constructs its own target membership. `T_selected` is frozen once globally. Post-selection CV may construct fold-local training/monitor/held-out partitions **within the already selected `T_selected`** and may fit fold-local training-only preparation, but it cannot select a different target set or size.
- **Part VI**: remove retired DATA7 per-domain target-selection/cache topology, MLCV target-size materialization language, and `TARGET-SIZE-V5` execution descriptions. Describe only the retained current P3/P5 execution/cache/provider/resource owners.
- **Part VII**: remove pre-target CV/target-domain ownership and do not list deployment/calibration/locked-test implementations as current campaign owners while P7 is not implemented. It may retain the statistical reservation of neutral outer/calibration/locked evidence roles, clearly separated from currently implemented downstream consumers.
- reconcile the assembled architecture manual, source maps, current specifications, README/current user guide, and generated-document sources wherever the changed semantics are repeated.

Current documentation must not pretend P7 is already implemented. Historical rationale belongs in history/release notes, not as a second current architecture.

Acceptance evidence:

- focused semantic assertions for objective invariants where useful;
- current source-map/reference/link checks;
- required documentation build and PDF generation on the final candidate;
- human/Design conformance inspection of Parts III/VI/VII after generation.

### 2.5 Replace the non-reproducible P5A6 compatibility proof

Revision 4's protected outcome remains binding: a real workspace produced by exact accepted P5A6 must reopen unchanged under final P6 through real current owners. The current evidence mechanism is insufficient because the tracked builder is P6-added, its baseline commit/tree labels are hard-coded rather than machine-authenticated execution provenance, and the substantive test skips when the untracked workspace is absent.

Revision-4 Sections 2-4 are therefore superseded by the following stronger, reproducible final-qualification contract.

#### 2.5.1 Reproducible exact-baseline producer

Provide one dedicated qualification driver that can run from a clean final-P6 checkout and:

1. creates or authenticates an isolated Git worktree at exact commit `1670275487d29bbcde4c59efafdef9d1f8b0ced7`;
2. executes `git rev-parse HEAD` and the tree identity and fails unless they exactly equal the frozen commit/tree;
3. launches the fixture producer with the baseline worktree as the production import root;
4. before creating state, records/asserts that `mdstats.__file__`, `_campaign_cli_core.__file__`, the P4/P5 persistence/orchestration owners, and any baseline test helper used to drive production all resolve inside the authenticated baseline worktree;
5. drives the real P5A6 production persistence/currentness owners. Bounded numerical fakes remain allowed only below the accepted MACE numerical seam;
6. closes the baseline process/store cleanly and records a content/database snapshot of the produced workspace.

The qualification harness itself may live in final P6; that does not make its product owners P6. Its provenance claim comes from the authenticated imported/executed baseline modules, not from a hard-coded string in the harness.

#### 2.5.2 Final-P6 unchanged reopen

After baseline production, without rewriting/migrating the workspace, launch the final-P6 candidate in a separate production context and execute the revision-4 real-owner reopen/currentness checks, then close and reopen again. Verify authoritative persisted content did not change except for explicitly allowed reconstructible read caches.

#### 2.5.3 No skip in mandatory acceptance

The **mandatory P6 qualification command must create/authenticate or require the fixture and fail if it cannot do so**. A normal developer test may retain an optional skip for local convenience only if it is not cited as final P6 acceptance. Final P6 closure cannot be established by a `skipif(workspace absent)` path.

The final report must separately print PASS/FAIL for:

```text
P5A6 -> P6 authenticated current-generation compatibility
P6   -> P6 current-generation restart
V5/V6 -> reject-before-reuse
```

No result substitutes for another.

### 2.6 Strengthen structural absence tests to match the actual affected surface

`tests/test_mlff_target_size_p6_destructive_closure.py` currently checks a narrow retired-symbol set and mainly top-level package exports. Extend P6 structural acceptance to cover:

- automatic `campaign_cli` facade exports;
- current-write schema/version/receipt constants;
- current parser/guide/help text;
- generated config template and `campaign.toml.example`;
- current architecture/manual/source-map inputs;
- newly discovered aliases semantically equivalent to the retired topology.

Use exact allowlists for the narrow reject-only detector and clearly historical files; do not create an indiscriminate repository-wide string ban that rejects historical documentation or actionable obsolete-workspace error messages.

### 2.7 Repair the stage-local and final regression evidence gap

The original P6 deletion affected too broad a surface for the five-test stage-local checks to establish the claimed cutover. Do not attempt to rewrite history. Close the **revision-5 repair stages** coherently:

#### R5-A — executable public/config/current-contract repair

Implement Sections 2.1-2.3 together where ownership is coupled.

Before dependent documentation/qualification repair proceeds, run:

- focused structural/export/parser/config tests;
- current prepare/selection/CV/final-production owner tests plausibly affected by configuration resolution;
- P4 currentness/restart and P5 assembled tests;
- affected storage/cleanup tests if receipt/currentness/storage code changed;
- affected scheduler/resource/precision tests if configuration ownership changes can reach them.

#### R5-B — documentation semantic reconciliation

Perform Section 2.4 against the assembled R5-A candidate. Run required documentation link/reference/build/PDF checks. Documentation-only edits do not require unrelated executable reruns.

#### R5-C — compatibility qualification hardening

Implement Section 2.5 and run the non-skipping authenticated P5A6 -> P6 qualification plus P6 -> P6 and V5/V6 reject-before-reuse checks.

#### R5-D — final assembled P6 closure

Re-derive the affected surface from the complete P6 diff plus revision-5 repairs and run:

1. all focused current-owner tests for changed/retained P1-P5 surfaces;
2. complete affected-surface regression;
3. real parser/dispatch assembled lifecycle through `prepare -> select-target-size -> cross-validate -> train-production`, close/reopen, and currentness reauthentication, using only accepted bounded numerical seams;
4. the three persistence/compatibility cases above;
5. structural absence/current-public-surface checks;
6. repository-required static/build/documentation/PDF checks;
7. the broader/full CPU-safe repository suite unless a complete smaller bound is independently demonstrated.

New failures or failures plausibly intersecting the affected surface block. Demonstrably pre-existing unrelated failures may be attributed with baseline evidence. Deleted/disabled tests cannot be used to erase an affected regression without an accepted semantic reason.

Long target-machine GPU/real-data qualification and M-ladder production qualification remain separate/deferred as already authorized; revision 5 does not promote them into functional P6 acceptance.

## 3. P6 final disposition and evidence report

P6 may receive **PASS for cleanup/cutover** only when Sections 1-2 and all still-binding revision-3/revision-4 obligations not superseded here are satisfied.

The final evidence summary must distinguish:

```text
P6 cleanup/cutover functional acceptance       PASS / FAIL
P5A6 -> P6 current compatibility               PASS / FAIL
P6 -> P6 restart                               PASS / FAIL
V5/V6 reject-before-reuse                      PASS / FAIL
M-ladder algorithm/production qualification    PASS / DEFERRED / UNAVAILABLE
long target-GPU/real-production qualification  PASS / DEFERRED / UNAVAILABLE
P7 downstream qualification capability         NOT IMPLEMENTED BY P6 / IMPLEMENTED LATER
```

A P6 cleanup PASS authorizes merge/freeze of the destructive current-generation cutover. It does **not** authorize final release while the parent downstream-evidence obligation remains open.

## 4. Implementation authority

### Frozen

- P1-P5 accepted science and currentness semantics remain unchanged.
- Old SELECT2/verify architecture and V5/V6 derived target-size lineage remain retired.
- No downstream physical/locked evidence may become a P6 model-selection fallback.
- P6 current public lifecycle ends at fresh final production.
- P6 current surfaces must contain only current supported semantics; historical/reject-only support is explicitly isolated.
- Exact P5A6 current-generation compatibility remains mandatory and must be machine-proven/reproducible.
- P7 owns replacement downstream qualification and is not implemented as a shortcut inside P6.

### Delegated

- exact private names/modules used for a V7/current prepare receipt after removing V5 naming;
- the implementation shape of the authenticated two-worktree compatibility driver;
- test file organization and exact focused-suite partitioning;
- editorial organization of documentation, provided the current semantics above are complete and unambiguous.

### Reopen only on evidence

Reopen only the affected design surface if:

1. a valid P5A6 current-generation workspace demonstrably cannot reopen without a material current-generation schema migration;
2. removal of a surviving legacy-looking surface would destroy an independently supported current product responsibility not covered by P7 or another retained owner;
3. a generated/current configuration field thought obsolete is proven to be the sole owner of a still-required current P1-P5 scientific behavior;
4. final assembled evidence shows the P1-P5 lifecycle cannot remain functional without reviving retired target-size authority.

Do not reopen P1-P5 merely because the cleanup is large or because historical tests are easier to preserve than rewrite.

## 5. Handoff closure

The revision-5 P6 handoff is complete when an implementation agent can recover, from the current P6 revision-3 + revision-4 + revision-5 supplied files and the parent workplan, all of the following without prior chat/history:

- what old architecture remains retired;
- why downstream capability absence does not require restoring it in P6;
- which product obligation is intentionally handed to P7;
- every current P6 defect found by independent review and its required corrected end state;
- the non-skipping provenance-authenticated P5A6 compatibility boundary;
- stage-local and final acceptance required to earn a cleanup/cutover PASS;
- the explicit limitation that P6 PASS is not final product/release closure.
