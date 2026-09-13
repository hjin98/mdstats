---
kind: implementation-workplan-review-amendment
workplan_id: CODE-MLFF-P5-TRAIN2-EVAL2-CUEQ-ARCHITECTURE-RECURRENCE-REVIEW-REOPEN-1
parent_workplan: workplans/active/MLFF_P5_TRAIN2_EVAL2_CUEQ_ARCHITECTURE_RECURRENCE_REPAIR_WORKPLAN.md
protocol_version: 6.3.0
status: reopened-ready-for-repair
review_date: 2026-09-13
reviewed_candidate_head: 5ceb298ea6187aaf46da9ec98b409130dd0ae788
reviewed_candidate_tree: 5bc9873ba0fb7209abf015926d1e2c3216acb52d
accepted_project_baseline: b65fa3b02807815d8eca758bc04fb70d514d1f45
review_verdict: no-pass
highest_affected_domain: D4 implementation/concretization under unchanged accepted P5 TRAIN2/EVAL2 phase-separated CuEq architecture
serious_challenge: not-established
precedence: This independent SSDP 6.3 review amendment reopens the parent workplan at D4. It preserves the accepted H1/H2 repairs and all non-conflicting parent requirements. It supersedes the implementation-status recommendation to change D3 portable identity before the existing dependency-native canonical-target projection route is falsified.
---

# Independent SSDP 6.3 implementation review — NO-PASS / reopened

## 0. Verdict

**NO-PASS.** The candidate is materially improved but does not yet solve the core problem of concern: an authenticated phase-separated CuEq TRAIN2 checkpoint still cannot cross the production authentication/projection boundary into the authorized portable e3nn EVAL2 provider. The implementation itself records that foundation-backed CuEq state stops at the portable round-trip guard and marks the required round-trip test as a strict xfail.

The independent Challenge Pass does **not** accept the implementation's proposed D3 Serious Challenge on current evidence. Accepted D3 remains coherent:

```text
source / DATA6 / pseudolabel / evaluation / verification = portable e3nn
TRAIN2                                                = transient CuEq
only_cueq=false                                       = portable e3nn product required
```

Current specifications and the accepted P5 recovery lineage state that same separation. The observed A/G failure establishes that one particular D4 use of pinned MACE's `convert_cueq_e3nn.run()` rebuilds a portable shell whose registration/static-buffer details differ from the already-authorized foundation-loaded shell. It does **not** yet establish that dependency-native CuEq -> e3nn state projection cannot populate the authorized shell.

Pinned `mace-torch==0.3.16` already exposes `mace.cli.convert_cueq_e3nn.transfer_weights(source_model, target_model, ...)`. That dependency owner transfers CuEq symmetric contractions, all remaining compatible state, and `avg_num_neighbors` into a caller-provided e3nn target model, then loads that target's state dictionary. Therefore the lower-level D4 alternative identified by the implementer as option (b) must be falsified before trigger 3 can justify a D3 challenge.

Do **not** authorize option (a), descriptor narrowing, alternate portable identity, or checkpoint bypass merely because the converter-created shell differs. Those would change or weaken the identity contract before the existing canonical-target projection route has been exhausted.

---

## 1. Independent authority reconstruction

### 1.1 Governing invariants

The review re-established the following accepted constraints from current specifications, the parent workplan, and directly affected accepted relatives:

1. TRAIN2 architecture authentication remains exact and fail closed before checkpoint state controls EVAL2.
2. `Train2RuntimeSummary.model_architecture_digest` denotes the actual state-owning TRAIN2 realization.
3. CuEq is transient for the qualified `only_cueq=false` route; EVAL2 and exported products remain portable e3nn.
4. The portable provider must satisfy the authorized P5 architecture, including genuine parameter/buffer registration and architecture-derived buffers; a different deterministic shell is not automatically an equivalent identity.
5. Target/replay membership, foundation/head semantics, optimizer/loss/LR/EMA/precision/batch/exposure/CV science and checkpoint convention remain frozen.
6. Frozen model-affecting normalization, including `avg_num_neighbors`, is not recomputed from fold-local data.
7. Raw checkpoint, companion, epoch/live/EMA, materialization, execution and ancestry provenance remain independently authenticated.
8. Valid completed TRAIN2 work is preserved and reused when the defect is representation/reconstruction-only.
9. Temporary accelerator models remain bounded to their actual lifetime owner; TRAIN scheduling does not absorb EVAL2.
10. Repair should reduce or alter existing owners before adding compatibility state or parallel identity machinery.

### 1.2 Historical Applicability Set refreshed for this review

The parent workplan predates the candidate PEM and explicitly required refresh if one appeared. The accepted project baseline itself still has no accepted PEM, so the candidate PEM remains non-authoritative evidence only.

```yaml
pem_basis:
  accepted_project_state: b65fa3b02807815d8eca758bc04fb70d514d1f45
  accepted_pem: NONE_PROTOCOL_6.2_PRE_PEM
  candidate_overlay_semantic_candidate: 637ecf02b561cc16c7daee9e1008efa90e04dc2f:PROJECT-ENGINEERING-MEMORY.md
has:
  - id: FF-001
    disposition: APPLICABLE
    reason: The candidate concerns the same realized-model identity family; use it to search shared construction/projection owners, not to weaken the architecture guard.
  - id: FF-002
    disposition: APPLICABLE
    reason: Reuse of the five completed TRAIN2 runs depends on exact authenticated restart/checkpoint boundaries.
  - id: SP-001
    disposition: APPLICABLE
    reason: Remaining repair should alter/consolidate the existing projection owner rather than add a second portable identity or compatibility layer.
  - id: SP-002
    disposition: APPLICABLE
    reason: The architecture and state gates correctly fail closed and must remain so.
  - id: SP-003
    disposition: APPLICABLE
    reason: Correct repair should preserve and reuse already-authenticated expensive TRAIN2 work.
  - id: SP-004
    disposition: APPLICABLE
    reason: The claim depends on real pinned-MACE construction/conversion and a bounded real CUDA/CuEq route, not configuration or mock parity alone.
  - id: NT-001
    disposition: APPLICABLE
    reason: The current unresolved notice is exactly the reviewed P5 TRAIN2/EVAL2 CuEq failure family.
  - id: FF-004
    disposition: APPLICABLE
    reason: Only the failure/success lifetime subclaim is relevant; GPU admission policy itself is not reopened.
```

PEM lessons remain evidence support, never D1-D4 authority.

---

## 2. What the implementation got right

These findings are **not** reopened unless new repair evidence contradicts them.

### C1 — H1 portable construction drift is genuinely repaired

The candidate correctly discovered that real P5 multihead MACE forms its element table from target plus replay-head data, while the old independent reconstruction used target elements only. The repair routes replay-head element discovery through pinned MACE's own dataset loader and reconstructs per-head calibration/zero-padding through the existing model-construction owner.

The focused real-owner test captures actual pinned `run_train` immediately before conversion and proves A == B, including a replay-only element. Stakeholder read-only reauthentication also reports the corrected independent CuEq architecture digest equal to the persisted TRAIN2 digest.

No blocker was found in this H1 repair.

### C2 — H2 device-sensitive CuEq realization drift is genuinely repaired

Actual MACE `run_train` passes the converter the result of `mace.tools.init_device`, i.e. a `torch.device`. The previous mdstats helper supplied the configured string. Because the CuEq conversion uses the device argument in its realization policy, this was a real topology drift.

The candidate now delegates device realization through `init_device` inside the existing conversion owner. The real-owner parity test proves C == D == F. No alternate converter or persistent realization authority was added.

No blocker was found in this H2 repair.

### C3 — H3 timing/nondeterminism and actual-method divergence are not supported by current evidence

The implementation records stable persisted architecture identity across all observed epoch boundaries/runs and deterministic equivalent independent realizations. After H1/H2 repair, the actual stakeholder checkpoint state structure agrees with the independently realized training model. The five existing runs therefore remain presumptively reusable subject to completing the portable projection/EVAL2 proof.

### C4 — the fail-closed guard remains intact

`authenticate_train2_checkpoint_provider()` still requires exact training-realization architecture equality before state load, verifies raw/latest/earlier and live/EMA provenance, and then checks portable architecture before exposing a provider. No digest tolerance, warning downgrade, backend fallback, checkpoint blessing, or second persistent identity was introduced.

### C5 — changed-owner scope remains small

Structural search found one shared realization definition and the expected production consumers: EVAL2 authentication plus recovery/admission preflight. Portable restoration has one production consumer in EVAL2 authentication. The candidate did not introduce a second scheduler, registry, migration store, checkpoint format, or wrapper hierarchy.

---

## 3. Blocking findings

### B1 — core D4 contract remains unsatisfied: foundation-backed CuEq cannot reach EVAL2

**Severity:** blocking correctness/acceptance defect.  
**Owner:** `model_features.restore_mace_portable_model()` + `target_size_execution/evaluation.authenticate_train2_checkpoint_provider()`.  
**Affected invariants:** 3, 7, 8 and parent G5/G6/G8/G10.

The current implementation authenticates the corrected transient CuEq realization and selected live/EMA state, then calls `restore_mace_portable_model()`. That helper invokes `convert_cueq_e3nn.run()`, which constructs a new e3nn shell from extracted CuEq configuration. The returned shell is compared against the already-reconstructed authorized P5 portable shell and fails for foundation-backed models (`first_difference=parameters`). The production route therefore raises before EVAL2 provider exposure.

This is not a cosmetic test issue: the implementer's read-only G5 exercise reports the same stop for all five stakeholder runs. The required G6 portable-round-trip and real-EVAL2-forward cases are absent by construction, and the focused test intentionally records the failure as strict xfail.

**Required repair:** keep exact training-realization authentication and the canonical portable architecture guard. Repair the projection at the existing owner; do not redefine what counts as portable.

### B2 — the D3 Serious Challenge is premature because the dependency-native canonical-target route was not falsified

**Severity:** blocking design-disposition error.  
**Owner:** same projection owner; no D3 change authorized.

Pinned MACE 0.3.16's `convert_cueq_e3nn.run()` is only a convenience orchestration around a lower-level native operation. It first constructs a target shell and then calls `transfer_weights(source_model, target_model, ...)`. `transfer_weights` is explicitly written to project CuEq state into a caller-provided e3nn target, including symmetric-contraction remapping, compatible remaining state, and per-interaction `avg_num_neighbors`.

The candidate already owns the correct authorized target shell as `provider_model` before accelerator realization. Therefore option (b) is not a new representation, checkpoint format, compatibility wrapper, or duplicate converter. It is the existing dependency-native state-transfer mechanism applied to the existing canonical target shell.

The implementer did not test this route before recommending option (a), which would authorize a different deterministic projection shell as portable identity. Under SSDP 6.3, a D3 challenge is not established while a simpler D4 concretization consistent with current authority remains unfalsified.

**Required repair sequence:**

1. Alter the existing `restore_mace_portable_model()` owner rather than adding a sibling projection API/registry.
2. For the CuEq phase-separated path, allow that owner to receive/reuse the already-authenticated canonical portable target shell built from the P5 configuration.
3. Delegate the actual CuEq -> e3nn state remapping to pinned MACE's `convert_cueq_e3nn.transfer_weights`, using pinned MACE's own extracted configuration to supply the converter parameters. Do not hand-reimplement symmetric-contraction remapping.
4. Preserve the target shell's authorized module/parameter/buffer registration and static architecture-derived buffers while transferring the authenticated trained state into it.
5. Continue to require exact canonical portable architecture equality after transfer; this should become structural identity by construction, not a bypass.
6. Verify that transferred live/EMA state produces the same governed numerical semantics as the dependency-native projection/CuEq source using the already accepted backend-parity numerical authority. Do not invent a new tolerance for this repair.
7. Preserve the OEq/nonaccelerated paths unless evidence shows they need the same target-shell treatment; do not broaden the patch mechanically.

Only if this native target-shell transfer is executed on the real governed foundation-backed CuEq cases and is shown unable to preserve both authorized portable architecture and accepted numerical state semantics may §10 trigger 3 be raised again. Converter argument plumbing or the fact that `run()` builds its own shell is not by itself a D3 contradiction.

### B3 — required executable acceptance is knowingly incomplete

**Severity:** blocking acceptance gap.  
**Owner:** focused/affected/assembled qualification under parent G6-G10.

The candidate records:

- a strict xfail for the portable architecture round-trip;
- all five real stakeholder runs stopping at the portable guard;
- no successful foundation-backed CuEq real EVAL2 forward;
- no completed CuEq assembled G8 `campaign cross-validate` route through real inference and restart-without-retraining.

SSDP 6.3 treats an unexecuted or xfailed required acceptance check as unavailable evidence, not PASS. The e3nn assembled restart test is useful routing evidence but it cannot substitute for the CuEq claim because the defect is device/converter-specific.

**Required acceptance after B1/B2 repair:** close every still-applicable parent G6 case, with particular emphasis on 3-5, 9, 12-14; then execute G8 on a bounded real CuEq/CUDA configuration. The assembled route must reach actual provider authentication and real bounded inference, interrupt after authenticated TRAIN2 completion, rerun, and show zero TRAIN2 relaunches for completed runs.

This is bounded defect qualification, not broad final-release GPU qualification.

### B4 — final affected-regression evidence is not independently auditable yet

**Severity:** blocking closeout-evidence gap, not a new product defect.  
**Owner:** parent G7/G10.

The implementation status reports `1081 passed, 2 skipped, 1 xfailed, 4 failed` and says the four failures reproduce on a "clean HEAD worktree," but does not identify the four failing tests or bind the comparison to the accepted baseline commit. The candidate has no GitHub commit-status/check-run evidence for the reviewed head.

After the executable repair, rerun the affected surface on one unchanged candidate. If any failures remain, record the exact test IDs and compare them against `b65fa3b02807815d8eca758bc04fb70d514d1f45` (or a demonstrably content-equivalent accepted baseline) before classifying them as pre-existing. The final candidate cannot close with an unexplained strict xfail or an unnamed regression delta.

---

## 4. Non-blocking review notes / plan corrections

### N1 — diagnostic G4 should not cause a new persistent descriptor authority

The candidate's extended first-difference helper can identify parameter/buffer/state structural differences visible from raw checkpoint state. Some true architecture differences such as `avg_num_neighbors` are not serialized in a way that permits the summary digest alone to reveal a first canonical descriptor field, so `not visible in checkpoint state` is an honest bounded result.

For closeout, interpret parent G4 as: report the first canonical/structural difference when it is derivable from already-authenticated in-memory/persisted evidence; otherwise report realization kind, both digests, and that the difference is not recoverable from checkpoint state. Do **not** add a second persisted full architecture descriptor solely to improve an error message.

### N2 — preserve the H1/H2 repairs while fixing projection

Do not roll back replay-element union, per-head calibration reconstruction, `init_device`, strict training digest authentication, or failure-path accelerator release simply because the later A/G gate still fails. The remaining owner is the post-authentication CuEq -> canonical-portable projection.

### N3 — `only_cueq=true` remains non-production-qualified

Current accepted policy qualifies `only_cueq=false`; parent G6-11 is a regression guard against accidentally forcing the phase-separated conversion path into a different dependency mode, not a request to production-qualify `only_cueq=true`. Keep existing behavior unchanged and prove no regression at the appropriate existing test boundary.

---

## 5. Reopened repair gates

The next implementation pass is intentionally smaller than the original workplan.

### R1 — canonical-target projection falsification/repair

Using the existing real-owner CUDA fixture, project authenticated foundation-backed CuEq state through pinned MACE's native `transfer_weights` into the exact B/provider canonical e3nn shell.

Required observations:

- target shell architecture digest before transfer;
- target shell architecture digest after transfer (must remain identical);
- no missing/unexpected structurally required state;
- selected live and EMA parameter-state semantics preserved;
- bounded prediction parity under existing accepted numerical authority;
- scratch and foundation-backed paths both covered.

If R1 passes, make this the existing `restore_mace_portable_model()` realization for the governed CuEq phase-separated path and delete/replace the converter-created-shell branch that causes the mismatch. Do not keep both as alternate production routes.

If R1 fails, record the exact first failure and whether it is (a) dependency transfer cannot represent required state, (b) target shell cannot accept dependency-native remapping, or (c) numerical semantics diverge beyond accepted authority. Only category evidence that makes accepted portable semantics unrealizable may re-open a D3 Serious Challenge.

### R2 — production provider completion

Route `authenticate_train2_checkpoint_provider()` through the repaired existing projection owner:

```text
canonical portable shell
 -> native training realization
 -> exact TRAIN2 architecture auth
 -> raw checkpoint/live-or-EMA auth and load
 -> native CuEq state transfer into the same canonical portable shell
 -> exact canonical portable architecture check
 -> portable provider
 -> EVAL2
```

No alternate digest, projected-shell identity, state-shape-only acceptance, descriptor exception, migration, or fallback is permitted.

### R3 — stakeholder artifact reuse

Read-only classify the existing five completed runs again. If the corrected route authenticates them, execute EVAL2 from those artifacts with **zero TRAIN2 retraining**. If any individual artifact now fails an independent provenance/currentness check, reject only that artifact for that evidence-backed reason; do not bulk-delete the set.

### R4 — focused and affected regression

Required focused evidence:

- A == B remains true;
- C == D == F remains true;
- authentic checkpoint + latest companion succeeds through portable projection;
- earlier checkpoint semantics remain correct;
- live and EMA succeed through projection;
- foundation/head/dtype/replay-element/normalization perturbations reject before inference;
- portable architecture is exact after transfer;
- real bounded EVAL2 forward succeeds;
- failure and success paths release transient accelerator ownership;
- nonaccelerated and existing `only_cueq=true` regression behavior is unchanged.

Then rerun the complete affected regression surface. No required check may remain strict-xfailed.

### R5 — assembled bounded CuEq restart proof

Run the real parser/CLI `campaign cross-validate` route with the production P5 owners and a bounded real CuEq workload. Prove TRAIN2 -> durable summary/checkpoint -> scheduler release -> EVAL2 provider authentication -> canonical portable projection -> real bounded inference. Interrupt at the TRAIN2/EVAL2 boundary, rerun, and prove completed TRAIN2 runs are not relaunched.

### R6 — closeout and memory reconciliation

On one unchanged candidate:

1. account for all parent G6-G10 requirements;
2. name and baseline-classify any residual regression failures;
3. update the PEM candidate overlay based on accepted evidence: resolve/retire NT-001 or leave it REVIEW_REQUIRED with an explicit reason; do not manufacture a recurrence count without Protocol 6.3 repair-acceptance lineage;
4. keep permanent architecture/specification documents unchanged unless a genuine D3 challenge is newly proven and accepted;
5. request a new independent SSDP 6.3 Review only after the required executable evidence is complete.

---

## 6. Tool-assisted review record

Serena and Semgrep were requested as optional understanding tools. Neither executable/tool surface is available in the review environment, and the isolated shell has no GitHub network access for installing/cloning them. Under SSDP 6.3 tool policy their absence is not an acceptance failure. The review therefore used:

- exact candidate/base commit and tree inspection;
- GitHub patch and source inspection;
- repository-wide symbol/text search for realization/projection call sites;
- dependency-source inspection of pinned MACE 0.3.16 conversion owners;
- structural comparison of changed call paths and required acceptance tests.

No claim in this review depends on Serena/Semgrep-only evidence.

---

## 7. Review disposition

**NO-PASS / REOPENED at D4.**

The accepted high-level architecture remains coherent and should not be changed on the current record. Preserve the H1/H2 repairs. Repair or falsify the existing dependency-native canonical-target projection route, then complete the blocked G5/G6/G8/G10 evidence. If that route is genuinely proven impossible while preserving both exact portable architecture and accepted numerical semantics, return to Software Design with that concrete evidence and re-evaluate §10 trigger 3.