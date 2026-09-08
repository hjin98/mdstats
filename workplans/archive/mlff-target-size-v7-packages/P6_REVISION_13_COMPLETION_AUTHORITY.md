---
kind: implementation-workplan-completion-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P6
protocol_version: 5.8.0
revision: 13
status: completed
review_date: 2026-08-31
accepted_executable_commit: f55d59b28c9db890dcb6a3c167a067ef5f37e8a2
accepted_executable_tree: e9a6d5f9d1a798f07dab88bd56dafcc73fe0e491
evidence_commit: 82371ecdab5f981255d0853a11477596be2623d3
evidence_tree: c83db85b1536b7f79ca2edca7634bda6768773db
verdict: PASS
successor_gate: CODE-MLFF-TARGET-SIZE-V7-P7 revision 9 entry condition satisfied
precedence: this completion authority supersedes status-only fields in earlier P6 revision-13 authority/addendum files; all accepted scientific, runtime, storage, restart, public-surface, testing, and documentation semantics remain unchanged
---

# P6 revision 13 — independent completion authority

Independent Software Design review closes `CODE-MLFF-TARGET-SIZE-V7-P6` revision 13 with **PASS**.

## Accepted candidate

The accepted executable candidate is:

```text
commit  f55d59b28c9db890dcb6a3c167a067ef5f37e8a2
tree    e9a6d5f9d1a798f07dab88bd56dafcc73fe0e491
```

The later evidence commit is:

```text
commit  82371ecdab5f981255d0853a11477596be2623d3
tree    c83db85b1536b7f79ca2edca7634bda6768773db
```

The compare from accepted executable commit to evidence commit contains only:

```text
workplans/active/mlff-target-size-v7-packages/P6_IMPLEMENTATION_EVIDENCE.md
```

No production source, test, qualification driver, executable tool, configuration, or product documentation changed after the accepted executable tree was tested.

## Closure findings

The final candidate satisfies the revision-13 closing addendum and all still-binding P6 obligations:

1. `tests/conftest.py` no longer pre-imports `mdstats`; pytest collection does not mask package import order.
2. `mdstats/preprocess/normalize.py` follows Disposition N1: the temporary `TYPE_CHECKING` import change was reverted after all four direct supported import orders passed outside pytest.
3. The discriminating SHA-256 receipt retention test crosses the real 100,000-row prune threshold and verifies public safe/cache cleanup preserves receipts and validation receipts.
4. The CampaignStore external-record proof publishes a real >4 MiB external pointer through `CampaignStore.put_record()`, ages it beyond the grace interval, retains it through safe/cache cleanup, reloads the exact payload, and positively reclaims an equally stale unreferenced sibling.
5. Historical `workspace/runs` trap retention remains proven for absent, malformed, dead-PID, and live-PID marker cases.
6. Focused R11-R13 storage/proxy acceptance passed: 51 passed, 0 failed, with no required acceptance skip.
7. Target-size/storage affected regression passed: 517 passed, 0 failed.
8. Compatibility/restart cases are separately established: A accepted-P5A6 -> P6 PASS; B fresh P6 close/reopen/restart PASS; C V5/V6 reject-before-reuse PASS.
9. Real parser/dispatch lifecycle plus revision-9 production/restart coverage passed: 32 passed, 0 failed.
10. The exact required repository-wide command executed on the accepted executable tree:

```bash
conda run -n mace python -m pytest -n 16 -q -p no:randomly
```

with result:

```text
202 failed, 2843 passed, 14 skipped, 2185 warnings, 100 errors in 426s
```

All 302 failing/erroring node IDs are pre-existing baseline members; zero new nonpasses are attributable to P6 revision 13.
11. Documentation/manual generation evidence remains valid; no documentation source changed in the final executable reconciliation.
12. Long target-machine GPU / real-production qualification remains explicitly deferred to the established final-release phase and is not claimed by P6.

## Final disposition

P6 revision 13 is **completed and closed**. No further P6 implementation or acceptance work is authorized unless a later independent issue materially invalidates an accepted P6 invariant.

The entry condition for `CODE-MLFF-TARGET-SIZE-V7-P7` revision 9 is now satisfied. P7 remains a separate successor workplan and may begin under its existing authority; this completion record changes no P7 scientific or qualification semantics.
