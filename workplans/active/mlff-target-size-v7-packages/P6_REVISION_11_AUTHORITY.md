---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 6
status: active
package_revision: 11
amended_date: 2026-08-31
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
reviewed_candidate_commit: 61148c14da71e762c5d05e2c0c7dab338639a95d
reviewed_candidate_tree: 6bd795ede89a77cf645f243f084ea951ebdd567e
compatibility_policy: destructive-generation-reset-current-generation-cutover-no-derived-migration
---

# P6 revision 11 — authoritative composed cleanup/cutover contract

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific/architectural authority for V7. P6 revision 11 supersedes revision 10 as the current Design -> Implementation handoff.

## Authoritative supplied artifact set

Read all of the following as one composed P6 authority:

1. `P6_REVISION_3_BASE.md` — baseline destructive cleanup/current-owner preservation contract.
2. `P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md` — exact accepted-P5A6 current-workspace compatibility requirement, except where later revisions tighten its evidence mechanism.
3. `P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md` — public/config/docs cleanup, compatibility-proof hardening, and corrected P6 closure semantics.
4. `P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral P1-P5 handoff and conservative quarantine pending the post-P7 storage reset.
5. `P6_REVISION_7_FINAL_CLOSURE_AMENDMENT.md` — final-owner/config/completion/storage/qualification closure contract.
6. `P6_REVISION_8_BLOCKER_REPAIR_AMENDMENT.md` — CV-plan-free fresh DATA5, evidence-authenticated final-production completion, current-generation STOR quarantine, genuinely distinct A/B/C qualification, and tied documentation/dependency corrections.
7. `P6_REVISION_9_FINAL_IMPLEMENTATION_CLOSURE_AMENDMENT.md` — accepted multi-seed final-production interruption/restart closure plus prior storage tightening.
8. `P6_REVISION_10_STORAGE_PUBLIC_SURFACE_FINAL_CLOSURE_AMENDMENT.md` — truthful safe/cache public/config/report surface, hidden-alias removal, safe/cache separation, frame-cache retention, and transitional storage cleanup closure, except for the positive checkpoint-model-cache deletion premise superseded by revision 11.
9. `P6_REVISION_11_CURRENT_CACHE_OWNER_CLOSURE_AMENDMENT.md` — current authority for the final cache-owner correction: no P6/P7 cache-family eviction, checkpoint-model-cache retention/deferment, removal of fabricated PID/path authorization, neutral storage-report wording, and replacement acceptance evidence through real current P3/P5 owners.

Precedence is revision 11 over revision 10 over revision 9 over revision 8 over revision 7 over revision 6 over revision 5 over revision 4 over revision 3 only where later text explicitly changes or tightens earlier wording. All other obligations remain binding.

## Revision-11 review disposition

Independent review of the revision-10 candidate accepted the revised public/configuration surface, hidden-alias removal, safe zero-cache-eviction behavior, frame-cache retention, and neutralized serialized storage-report policy. It found one remaining blocker: the positive `checkpoint-model-cache` eviction path was not backed by a current P3/P5 semantic owner or authenticated reconstruction authority, and its active/inactive acceptance fixture fabricated `workspace/runs/*/active_process.json` state rather than exercising a real current producer.

Repository inspection fired revision 10's narrow redesign trigger. Current P3 and P5 use canonical `.mdstats/target-size/...` and `.mdstats/post-selection/...` owner trees and direct authenticated checkpoint/evidence reconstruction rather than the assumed `workspace/runs/*/checkpoint-model-cache` contract.

Revision 11 therefore changes only that storage decision and the remaining `STOR1` current wording. It does not reopen accepted P1-P5 science or revision-9 P5 production/restart behavior.

## Scope and PASS boundary

P6 remains a **cleanup/cutover functional-closure package**. It does not implement P7 downstream publication/qualification and does not implement `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

Revision-11 P6 PASS requires:

```text
all accepted revision-9 scientific/P5 ownership and restart behavior preserved
+ revision-10 truthful generated config/help/guide/spec safe|cache surface preserved
+ no unsupported hidden top-level cleanup alias
+ safe cleanup has zero acceleration-cache eviction
+ cache cleanup has no additional destructive cache authorization in P6/P7
+ checkpoint-model-cache retained/deferred by safe and cache
+ frame-cache retained/deferred by safe and cache
+ historical path names remain non-authoritative for deletion
+ current P3/P5 owner trees protected without fabricated workspace/runs cache ownership
+ storage report is advisory, uses current neutral product wording, and contains no retired STOR/recompute/compact/protocol-freeze mutation policy
+ no new cache lease/registry/control plane is introduced in P6
+ exact P5A6 unchanged compatibility
+ independent fresh-P6 production/restart
+ V5/V6 reject-before-reuse
+ stage-local and final affected regression/integration closure
```

Only an independently reviewed **P6 revision-11 PASS** opens the P7 implementation gate. P7 completion then opens the separate post-P7 storage/I-O reset gate.
