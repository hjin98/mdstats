---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P6-R13-FINAL-BINDING
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P6-R13
protocol_version: 5.8.0
revision: 13
status: active
amended_date: 2026-08-31
reviewed_candidate_commit: 84b2af7ba1117065c33f58f504a852e3000dbe8a
reviewed_candidate_tree: 5f5fb7d5fb6e255ecd47e20c05477b2d58cc1589
precedence: this addendum supersedes only revision-13 final-candidate identity, post-test mutation, import-order reconciliation, and executable-evidence binding details; all other composed P6 revisions 3-13 requirements remain binding
---

# P6 revision 13 — final candidate identity and executable-evidence binding addendum

## 1. Review disposition and scope

Independent review accepts the substantive revision-13 proxy-proof corrections in `P6B5`:

- the SHA-256 receipt-retention test now exceeds the real 100,000-row pruning boundary and would fail if cleanup-triggered receipt pruning were restored;
- the external-record retention test now publishes a real `CampaignStore` external pointer, ages the referenced artifact beyond the cleanup grace period, and proves owner-based retention while an equally stale unreferenced sibling is reclaimed;
- the previously accepted revision-12 conservative storage semantics remain intact.

P6 remains **NO PASS** for one implementation/evidence reason: the tracked execution evidence is bound to commit `4c4b2f5a93fa86aa17613afae2279c5faf5446a5` / tree `164a2393613faa2aa2c116117e266ee56abf15eb`, while the committed `P6B5` candidate `84b2af7ba1117065c33f58f504a852e3000dbe8a` / tree `5f5fb7d5fb6e255ecd47e20c05477b2d58cc1589` changes both acceptance tests and executable/import behavior.

This addendum reopens **only final executable-candidate reconciliation and exact-tree evidence binding**. It does not reopen target-size science, revision-9 multi-seed P5 behavior, revision-11/12 storage semantics, the accepted R13 proxy-proof design, P7 behavior, or the successor storage reset.

Do **not** create a P6 revision 14 for this closure. Complete the existing revision-13 contract.

## 2. Frozen accepted behavior

The following remain frozen and must not be changed during this closure:

```text
safe  -> current-owner zero-capability-loss cleanup only
cache -> safe + no currently authorized cache-family eviction
```

Specifically preserve:

- no deletion authority from `workspace/runs`, `active_process.json`, PID liveness, run age, or historical path names;
- no `checkpoint-model-cache`, `frame-cache`, SHA-256 receipt-cache, or uncertified historical-cache eviction through public safe/cache cleanup;
- real CampaignStore orphan reclamation only for genuinely unreferenced current-store external artifacts after age/ownership checks;
- current P3 `.mdstats/target-size/g<generation>` and P5 `.mdstats/post-selection/g<generation>` authority;
- revision-9 multi-seed final-production interruption/resume/integrity semantics;
- A/B/C compatibility distinctions;
- current public parser lifecycle `prepare -> select-target-size -> cross-validate -> train-production`;
- no P7 or post-P7 storage-reset implementation in this stage;
- no long GPU/real-production qualification in P6.

The R13-A and R13-B test designs are accepted. Do not weaken, replace, or proxy them.

## 3. Resolve the two unaccounted P6B5 import/test-harness edits before final testing

`P6B5` contains two changes outside the R13 proxy-test files that must be reconciled before any final acceptance run:

1. `mdstats/preprocess/normalize.py` changes `RawFrameCollection` from a runtime import to a `TYPE_CHECKING`-only import.
2. `tests/conftest.py` adds a top-level `import mdstats` that is otherwise unused.

### 3.1 `tests/conftest.py`: remove global package preloading

Remove the added top-level:

```python
import mdstats
```

from `tests/conftest.py` unless a concrete, independently supported fixture contract actually consumes that module object at module scope. The current file does not.

Reason: globally pre-importing the package changes test collection/import order and can hide or create import-cycle behavior. It is not an acceptable mechanism for making the suite pass and must not become part of the acceptance environment.

Acceptance after removal:

- pytest collection still succeeds for the R13 focused suite;
- density-resource fixtures retain their existing lazy `from mdstats import ...` behavior inside the fixture;
- no test depends on package preloading from `conftest.py`.

### 3.2 `normalize.py`: keep only if it fixes a real supported import-order defect

Do not automatically keep or revert the `TYPE_CHECKING` change. Resolve it from product behavior:

1. Remove the global `tests/conftest.py` preload first.
2. On the candidate without that preload, execute direct supported import-order smoke checks outside pytest, at minimum:

```bash
python -c "import mdstats"
python -c "import mdstats.preprocess.normalize"
python -c "import mdstats.io; import mdstats.preprocess.normalize"
python -c "import mdstats.preprocess.normalize; import mdstats.io"
```

3. Determine whether the parent production behavior without the `TYPE_CHECKING` change has a genuine circular/import-initialization failure under any supported ordering.

Then apply exactly one disposition:

**Disposition N1 — no real production defect:**
- if supported imports already work without the `TYPE_CHECKING` change, revert the `normalize.py` edit because it is unrelated to the R13 acceptance closure;
- do not retain production-source churn merely because it is harmless.

**Disposition N2 — real import-order defect established:**
- if a supported direct import fails on the pre-fix production source and the `TYPE_CHECKING` change fixes it, retain the change as a newly discovered local import-dependency repair;
- add a focused subprocess/import-order regression that executes the real package imports without pytest/conftest preloading;
- verify no runtime code performs `isinstance(..., RawFrameCollection)`, runtime annotation resolution, or another operation requiring the name to be imported at module runtime;
- include `mdstats/preprocess`, `mdstats/io`, package-root import/export, and their affected tests in the final regression surface.

Do not add lazy wrappers, fallback imports, package preload hooks, or other compatibility machinery. The accepted realization, if N2 applies, is the minimal owning-layer dependency correction.

## 4. Freeze the final executable candidate before running acceptance

After Sections 3.1-3.2 and the already accepted R13-A/R13-B test corrections are complete:

1. finish all production-source, test, qualification-driver, and executable-tool edits;
2. commit them together as the **final executable candidate**;
3. require a clean working tree for all product/test paths;
4. record:

```bash
git rev-parse HEAD
git rev-parse HEAD^{tree}
git status --short
```

The first two values define the executable candidate identity. `git status --short` must show no uncommitted changes under at least:

```text
mdstats/
tests/
qualification/
tools/
build_support/
campaign.toml.example
```

Do not run the final acceptance first and commit the tested changes afterward. Evidence must correspond to a Git-representable committed tree.

## 5. Required final execution on that exact committed tree

All commands in this section must execute after the final executable commit exists and before any later executable/test edit.

### 5.1 Direct import-order checks

Run the four direct Python import commands from Section 3.2. If disposition N2 applies, also run the newly added focused import-order regression.

All required import checks must pass without relying on `tests/conftest.py` to preload `mdstats`.

### 5.2 Focused R13 storage/proxy-proof closure

Run:

```bash
conda run -n mace pytest -v \
  tests/test_mlff_target_size_p6_destructive_closure.py \
  tests/test_mlff_stor1_storage_accounting.py \
  tests/test_mlff_stor3_safe_reclamation.py \
  tests/test_mlff_stor4_manual_reclamation.py
```

Requirements:

- zero failures;
- zero errors;
- no skip of any required R11-R13 acceptance case;
- R13 receipt test must actually execute the >100,000-row population;
- R13 external-pointer test must actually execute the real stale referenced-pointer/stale orphan sibling case.

### 5.3 Inherited target-size/storage regression

Run the current complete target-size/storage surface, at minimum:

```bash
conda run -n mace pytest -n 32 \
  tests/test_mlff_target_size_*.py \
  tests/test_mlff_stor*.py \
  tests/test_mlff_campaign_cli.py \
  tests/test_mlff_doc_arch1_specification.py
```

This must include and pass the inherited R8-R12 P3/P4/P5, revision-9 multi-seed, storage, cutover, restart, and public-surface cases.

If disposition N2 applies, add the affected preprocess/io/import tests to this stage-local/affected regression before proceeding.

### 5.4 A/B/C qualification — separately reported

Run:

```bash
conda run -n mace python qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py
```

The output must independently establish:

```text
A  accepted P5A6 -> P6 authenticated compatibility     PASS
B  fresh final-P6 -> close/reopen/restart              PASS
C  V5/V6 retired state -> reject-before-reuse           PASS
```

One result may not substitute for another.

If the qualification driver or its fixtures change after this run, rerun A/B/C.

### 5.5 Real parser/dispatch lifecycle

Execute the assembled real-owner lifecycle tests that drive the public parser/dispatcher through:

```text
prepare -> select-target-size -> cross-validate -> train-production
```

including close/reopen/currentness. At minimum rerun:

```bash
conda run -n mace pytest -v \
  tests/test_mlff_target_size_p4g_assembled_integration.py \
  tests/test_mlff_target_size_p5g_assembled_integration.py \
  tests/test_mlff_target_size_p5e_production_and_restart.py
```

All required cases must pass. Preserve bounded numerical fakes only below the already accepted real mdstats owners.

### 5.6 Final repository-wide CPU-safe regression — exact command

Run the established R13 command **exactly**:

```bash
conda run -n mace python -m pytest -n 16 -q -p no:randomly
```

Do not substitute the previous `-n 32` run as the final R13 full-suite evidence.

Classify every final failure/error by exact node ID against the recorded pre-P6 baseline or, if necessary, a detached comparison worktree. Required result:

```text
zero new P6/R13-attributable nonpasses
```

All required P6/R8-R13 tests themselves must be passing regardless of unrelated baseline failures.

If disposition N2 retains the `normalize.py` production change, any new import/preprocess/io failure is within the affected surface and cannot be dismissed as unrelated without baseline proof.

## 6. Evidence invalidation rules after the final run

After Section 5 starts, apply these rules strictly:

### Executable/test mutation

Any later change under any of the following invalidates at least the affected evidence:

```text
mdstats/
tests/
qualification/
tools/          # when the changed tool participates in acceptance/runtime
build_support/
campaign.toml.example  # if parser/config behavior is affected
```

A later executable/test edit requires:

1. commit the change;
2. derive a new executable commit/tree identity;
3. rerun every check whose behavior could plausibly be affected;
4. rerun the final full CPU-safe regression before claiming P6 closure.

Do not point evidence at the parent commit merely because tests were executed from a dirty working tree containing later changes.

### Evidence-only update

After all required execution passes, update only:

```text
workplans/active/mlff-target-size-v7-packages/P6_IMPLEMENTATION_EVIDENCE.md
```

in a separate evidence-only commit where practical.

The evidence document must record the **final executable commit/tree from Section 4**, not the planning parent and not the later evidence commit/tree.

After committing evidence, prove:

```bash
git diff --name-only <tested-executable-commit>..HEAD
```

contains no product source, test, qualification-driver, or executable-tool changes. If it does, the exact-tree acceptance is not closed.

Workplan/design-only files created before the final executable run are part of the tested repository state but do not themselves define executable identity beyond the Git tree. Documentation-only/evidence-only edits made after testing do not invalidate unrelated executable evidence unless they alter a required executable/documentation check.

## 7. Required contents of `P6_IMPLEMENTATION_EVIDENCE.md`

Reconcile the existing evidence document; do not create another evidence ledger.

It must state, unambiguously:

1. `package_revision: 13`;
2. exact final tested executable commit;
3. exact final tested executable tree;
4. clean-tree confirmation before final execution;
5. disposition N1 or N2 for `normalize.py`, with concise evidence;
6. confirmation that top-level `import mdstats` was removed from `tests/conftest.py`;
7. direct import-order smoke results;
8. focused R13 command and result;
9. inherited target-size/storage regression command and result;
10. A, B, C results separately;
11. real parser lifecycle result;
12. exact final full-suite command using `-n 16`, counts, and exact-node-ID attribution of any remaining baseline failures/errors;
13. statement that no required acceptance test was skipped;
14. documentation/PDF evidence status, reusing earlier still-valid documentation evidence only if the final compare proves documentation source did not change in a way that invalidates it;
15. explicit statement that long GPU/real-production qualification remains deferred and is not claimed;
16. post-evidence compare proving no executable/test/qualification changes occurred after the tested executable commit.

Do not describe `4c4b2f5...` as the tested executable if the R13-A/R13-B tests or any executable source were not committed in that tree.

## 8. Final PASS boundary for revision 13

Independent P6 revision-13 PASS requires one coherent final state:

```text
accepted revision-12 runtime/storage/scientific/public semantics preserved
+ accepted R13-A >100,000-row receipt proxy proof PASS
+ accepted R13-B stale real external-pointer/orphan proof PASS
+ no conftest package-preload shortcut
+ normalize.py import change either reverted as unrelated OR retained with real direct-import defect proof and affected regression
+ final executable candidate committed before final testing
+ clean product/test working tree at test start
+ R8-R12 inherited acceptance PASS
+ revision-9 multi-seed restart/integrity PASS
+ A PASS separately
+ B PASS separately
+ C PASS separately
+ real parser lifecycle PASS
+ exact `-n 16` repository-wide CPU-safe regression executed
+ zero new P6/R13-attributable nonpasses
+ P6_IMPLEMENTATION_EVIDENCE.md bound to the exact tested executable commit/tree
+ no executable/test/qualification mutation after that test run without rerun
+ valid documentation/PDF evidence
```

Only then does P6 revision 13 close and the existing P7 revision-9 predecessor gate open.

## 9. Anti-shortcuts

The following are explicitly nonconforming:

- creating revision 14 instead of completing this bounded revision-13 closure;
- retaining global `import mdstats` in `tests/conftest.py` merely to stabilize import order;
- keeping `normalize.py` production churn without establishing a supported import-order defect or reverting it when unnecessary;
- running acceptance from a dirty working tree and recording the parent commit as the tested candidate;
- executing tests, then committing acceptance-test or production-source changes and treating the earlier run as final evidence;
- recording the evidence commit/tree instead of the executable commit/tree as the tested product identity;
- using the prior `-n 32` whole-repository run instead of the required final `-n 16` command;
- changing the R13-A/R13-B tests after they pass without rerunning them;
- weakening A/B/C, revision-9 multi-seed, P3/P5 real-owner, or lifecycle tests to save runtime;
- using pytest/conftest import side effects as evidence that normal package import works;
- reopening accepted science/storage architecture without a corrected acceptance test exposing a real product defect.

## 10. Reopen Design only on evidence

Do not reopen Design again unless one of these occurs after following this addendum:

1. removing the conftest preload exposes a real package import cycle that cannot be repaired by the minimal dependency correction without broader architectural impact;
2. corrected R13-A/R13-B tests expose a new runtime/storage defect;
3. A/B/C or current P3/P5 lifecycle fails because of a production-state regression;
4. the final `-n 16` regression introduces a new P6-attributable failure outside the bounded import/test-evidence closure;
5. the final candidate cannot be represented as a clean committed Git tree before acceptance.

Otherwise implementation should finish revision 13 directly, update the existing evidence document, and return the exact final executable commit/tree for independent review.
