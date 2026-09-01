---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P6-R4
parent_package_id: CODE-MLFF-TARGET-SIZE-V7-P6
protocol_version: 5.8.0
package_revision: 4
status: active
amended_date: 2026-08-30
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
amends_base_revision: 3
precedence: this amendment overrides the included revision-3 base only where explicitly stated below; all other revision-3 obligations remain binding
---

# P6 revision 4 amendment — P5A6 current-state compatibility and required documentation checks

## 1. Purpose and non-reopen statement

This amendment closes the final P6 handoff gap without reopening the frozen parent, P1-P5 science, destructive-generation policy, or revision-3 cleanup design.

Revision 3 correctly requires both current-generation restart and rejection of obsolete V5/V6 target-size derived state, but its tests could be satisfied entirely by state created after P6 cleanup. That does not prove that a real current-generation workspace produced by accepted P5A6 survives deletion of legacy modules/types/schemas/imports.

Three persistence claims are therefore frozen as distinct acceptance obligations:

```text
A. exact P5A6-created current V7 workspace -> final P6 must reopen/authenticate
B. final-P6-created current V7 workspace -> final P6 must restart/reopen
C. retired V5/V6 target-size derived workspace -> final P6 must reject before reuse
```

No one of A/B/C may be used as evidence for another.

## 2. Mandatory pre-cleanup P5A6 compatibility fixture

Before the first destructive executable P6 cleanup stage, implementation must create and preserve a **bounded persisted current-generation workspace using exact P5A6 code**:

```text
commit  1670275487d29bbcde4c59efafdef9d1f8b0ced7
tree    17e2c5609974712bda1efd3375f09f42da830f68
```

The fixture must be created through real production persistence/state owners, not by hand-authored JSON/SQLite rows or a test-only serializer.

Populate every current persisted surface plausibly affected by P6. At minimum, where P5A6 persists the corresponding state, exercise:

```text
real config/current preparation
 -> real CampaignStore/SQLite
 -> real P4 current terminal N_selected/T_selected
 -> persist selected binding/current terminal authority
 -> current post-selection CV plan/evidence sufficient to exercise persisted CV identity
 -> current final-production evidence/publication sufficient to exercise persisted final identity
 -> close store/process context cleanly
```

Production-scale numerical training/prediction is not required. Existing P5-accepted bounded numerical fakes remain allowed **below** real mdstats persistence/orchestration owners.

Record enough immutable fixture identity to prove the final test consumed the same P5A6-produced workspace. This may be a bounded manifest/digest/path set already natural to the test harness; do not invent a new product persistence layer merely for evidence.

## 3. Preserve the baseline workspace unchanged

After fixture creation and before final-P6 compatibility execution:

- do not regenerate it with P6;
- do not rewrite, normalize, migrate, or pre-open-and-save its persisted files/rows using P6;
- do not replace persisted state with semantically equivalent test data;
- do not delete affected current-generation state during cleanup merely because P6 can regenerate it;
- preserve the fixture as read-only test evidence except for ordinary filesystem metadata changes that do not alter contents.

P6 implementation may separately create fresh workspaces for normal stage-local testing. Those fresh workspaces do not satisfy this compatibility obligation.

## 4. Final-P6 real-owner compatibility acceptance

On the final P6 candidate, open the preserved P5A6-created workspace **without any prior P6 rewrite/migration** through the real production load/currentness path:

```text
preserved P5A6 workspace
 -> real CampaignStore/SQLite load/deserialization
 -> authenticate current generation/current pointer
 -> authenticate P4 terminal N_selected/T_selected
 -> authenticate exact selected-frame binding
 -> authenticate affected persisted P5 method/foundation/replay/CV/final identities
 -> expose required current terminal/final views through production owners
 -> close
 -> reopen again
 -> prove currentness/restart remains valid
```

The acceptance must fail if P6 removed or changed a required current-generation class/schema/import/decoder/current-pointer contract such that a real P5A6 workspace can no longer load or authenticate.

Forbidden shortcuts:

- create the compatibility fixture with P6 instead of P5A6;
- regenerate the workspace before testing compatibility;
- rewrite persisted representation before the first successful P6 load;
- seed reconstructed current state in the harness;
- bypass `CampaignStore`, the real deserializer, terminal loader, currentness checks, or public/current consumer path under acceptance;
- use a custom/in-memory store when disk-backed persistence/restart is the claim;
- use retired V5/V6 target-size migration machinery;
- prove only schema/unit compatibility while the actual P5A6 workspace cannot reopen.

If valid P5A6 current-generation state cannot reopen without a **material current-generation schema migration** not already authorized by the frozen parent/P1-P5/P6, trigger the existing P6 Design-reopen condition. Do not add an unplanned compatibility bridge or reinterpret this as obsolete-state rejection.

## 5. Keep P6-to-P6 restart and obsolete-state rejection separate

Revision-3 P6 restart/currentness requirements remain binding and must still prove final-P6-created current state can close/reopen/restart deterministically.

Revision-3 obsolete-generation requirements also remain binding and must still prove representative retired V5/V6 target-size derived state is rejected by the real load/preflight path before semantic old-state deserialization, candidate/checkpoint reuse, or descendant publication.

Required final evidence therefore contains three separately identified results:

```text
P5A6 -> P6 current-generation compatibility     PASS/FAIL
P6 -> P6 current-generation restart             PASS/FAIL
V5/V6 retired target-size reject-before-reuse   PASS/FAIL
```

All three must pass for functional P6 closure.

## 6. Stage-local consequence

If a P6 stage changes any serializer, schema, store reader, imported persisted type, current-pointer loader, path/layout owner, or cleanup rule that could affect the preserved P5A6 fixture, that stage's semantic closure must explicitly check that the change has not knowingly invalidated the P5A6 compatibility obligation.

The full preserved-fixture reopen is mandatory on the final assembled candidate. It may additionally be run earlier when doing so materially reduces destructive-cleanup risk.

## 7. Required documentation/PDF checks — no deferred-success loophole

Revision 3 Section 5.2 and final exit wording are tightened as follows:

- Every documentation link/reference/lint/build/PDF check required by the **frozen parent** or governing repository/project policy for the affected surface must execute and pass before P6 functional closure.
- A required check that cannot execute because a dependency/toolchain is unavailable is **blocking/unavailable**, not passed and not deferred-success.
- Only a check independently determined to be **non-required/not-applicable** under the governing parent/repository policy may be classified as not applicable or deferred.
- Changing repository policy solely to evade a failing/unavailable required P6 check is not an implementation-local workaround; it requires the normal governing-authority change process.

This clarification does not turn long target-machine GPU/real-data production qualification into a P6 requirement. That qualification remains explicitly deferred under the frozen parent.

## 8. Evidence/reporting additions

Add to the revision-3 implementation evidence ledger:

1. exact P5A6 fixture creation command/path and baseline commit/tree;
2. bounded numerical fake seams used during fixture creation, if any;
3. immutable fixture identity sufficient to prove the final candidate opened the preserved P5A6-produced workspace;
4. final-P6 real-owner reopen/authentication command/result;
5. explicit confirmation that no pre-load rewrite/migration occurred;
6. P6-to-P6 restart result;
7. retired V5/V6 reject-before-reuse result;
8. required documentation/PDF commands/results and any genuinely non-required checks classified as not applicable.

The three-way qualification report from revision 3 remains unchanged except that **Functional V7/P6 acceptance** now explicitly includes successful P5A6 -> P6 current-generation compatibility.

## 9. Revision-4 exit additions

Revision-3 final exit criteria remain binding. In addition, P6 cannot close unless:

- a real current-generation workspace was produced using exact P5A6 before destructive cleanup;
- the same preserved workspace was opened unchanged by the final P6 candidate through real persistence/currentness owners;
- selected binding and all materially affected persisted P5 identities/views authenticated correctly;
- a second reopen remained current and deterministic;
- P6-to-P6 restart passed separately;
- retired V5/V6 target-size reject-before-reuse passed separately;
- no material current-generation migration was introduced outside accepted authority;
- every required documentation/link/lint/build/PDF check executed and passed.

Once these additions and all revision-3 requirements are satisfied, P6 may proceed to independent Software Design review and merge/freeze decision.
