---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R26
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-02
reviewed_plan_head: c36939867a4df785c106b14575cb1fe127e83827
reviewed_plan_tree: c19dd8df6fc30acfad89893217262d423e989682
reviewed_executable_commit: 8e87bc863be2470fb602a9cbb2ac411b7bc83bc4
reviewed_executable_tree: 7becdd8918f4125ed69442fa07e95ed412560566
plan_review_verdict: PLAN-CORRECTION-REQUIRED
precedence: Revision 21 remains the accepted final repair design; Revision 24 remains the accepted descriptor/root-identity repair design; Revision 25 implementation findings remain binding except where this Revision 26 explicitly replaces the over-constrained final-mutation wording and refines final acceptance. This amendment also adds the requested current-authority test-suite retirement work. No P1-P7 science is reopened.
---

# Storage/I-O reset repair-plan closure — Revision 26

## 0. Disposition

A fresh review of Revision 25 found one **plan-level defect** and one substantial repository-maintenance consequence that must be incorporated before another implementation pass.

1. Revision 25 correctly identified the remaining check-then-path-mutation weakness, but its literal requirement that the final destructive syscall be conditional on the previously observed `(device, inode)` over-specifies what the supported POSIX/Python interface can promise. POSIX directory-entry deletion is name-relative to a parent directory descriptor; it is not an inode compare-and-delete primitive. Leaving this as an implementation-time redesign trigger would make Implementation invent the trust/threat boundary or disable a capability the accepted storage product is meant to provide.
2. The repository's full `pytest` population contains a large historical layer left behind after the destructive P6 target-size/lifecycle cutover: tests and benchmark drivers still pin obsolete package versions, historical architecture gates, non-current migration/spec documents, or modules that P6 deliberately deleted. P6's own baseline recorded this debt as a major source of pre-existing full-suite failure. Current documentation authority explicitly says those retired pre-V7 owners are historical/reject-only, not current product semantics.

This amendment fixes both issues without changing Revision-24 ownership architecture.

**Design/workplan disposition after this amendment:** **CLOSED / implementation-ready under Revision 26.**

**Executable disposition:** remains **NO-PASS / reopened** until the still-binding Revision-25 source repairs, the Revision-26 mutation realization, the test-suite retirement stage, and exact-candidate affected regression/integration evidence are complete.

---

## 1. R26-A — freeze a realizable descriptor-pinned P7 mutation boundary

### Protected concern

The accepted security/ownership property is that destructive P7 authority obtained for one authenticated qualification attempt must not transfer through a substituted **generation / `attempts` / attempt ancestor chain**, follow a symlink into a foreign tree, or be reconstructed later from an unauthenticated absolute pathname.

The product already synchronizes supported P7 writers through:

```text
storage-operation lease
  -> P5 run-activity locks
  -> P5 publication barriers
  -> P7 publication barriers
  -> P7 attempt-state lock
  -> fresh P7 inventory/certification
  -> narrow mutation
```

That supported-owner synchronization remains part of the trust boundary. The storage product is not required to provide an impossible inode-CAS delete guarantee against an arbitrary privileged or same-UID external process continuously renaming entries *inside* a P7-owned tree after all supported-owner locks are held. It **is** required never to re-resolve the authenticated owner ancestry by pathname and then traverse whatever replacement answers to it.

### Required end state

For every consequential released-attempt action, the apply path must freshly acquire the strict P7 namespace **under the established owner seams** and retain an authenticated attempt-directory descriptor across exact proof/member certification and the destructive operation.

The authority-bearing chain is therefore:

```text
authenticated campaign internal directory
  -> qualification (open relative, no-follow)
  -> canonical gN (open relative, no-follow)
  -> attempts (open relative, no-follow)
  -> exact attempt (open relative, no-follow)
  -> proof/member observation relative to the retained attempt descriptor
  -> mutation relative to retained descriptor(s)
```

No downstream P7 cleanup step may close that capability and later rebuild destructive authority from `Path(...)`, `resolve()`, `is_dir()`, `iterdir()`, `glob()`, or another independent name traversal of the authority-bearing ancestry.

### Required implementation consequences

1. **Invocation-local descriptors only.** Descriptors live only for the consequential apply/certification invocation, are closed deterministically on every outcome, and are never persisted as a new inode/path authority ledger.
2. **Top-level regular files.** A proof-certified released regular file is mutated by an fd-relative, no-follow-safe path beneath the authenticated attempt descriptor, e.g. an equivalent of `os.unlink(member_name, dir_fd=attempt_fd)`, after its certified kind/current observation is established. It must not fall through to generic absolute-path `remove_durably()`.
3. **Directories.** Recursive deletion is rooted in the authenticated attempt descriptor and descends only through no-follow child directory descriptors. Every disappearing node remains bounded by the exact typed released-attempt certification and mount-boundary rules.
4. **Python 3.10 support is part of the envelope.** The project supports Python `>=3.10`; therefore the implementation may not assume a later `shutil.rmtree(..., dir_fd=...)` API is universally available. On runtimes where the standard helper cannot preserve the required dir-fd boundary, use a small bounded owner-specific descriptor-relative recursion built from supported `os.open(..., dir_fd=...)`, `os.scandir(fd)`, `os.unlink(..., dir_fd=...)`, and `os.rmdir(..., dir_fd=...)` or an engineering-equivalent realization. Do not change the package's supported Python floor merely to avoid this implementation.
5. **No authority widening.** A symlink, FIFO/device/socket/special node, wrong-kind replacement, unrecorded descendant, or nested mount remains a refusal/retention boundary. Descriptor traversal does not make a mounted subtree campaign-owned.
6. **Durability.** Preserve the accepted durable-unlink/removal semantics: sync the appropriate authenticated parent directory after successful directory-entry mutation where the current product promises that durability.
7. **Namespace instability.** If strict reacquisition says the expected generation/attempts/attempt namespace changed, disappeared after enumeration, or cannot be authenticated, refuse. Do not retry until a convenient namespace appears.
8. **No false CAS claim.** Do not document or test this as an atomic inode compare-and-delete primitive. The guarantee is descriptor-pinned owner ancestry + no-follow fd-relative mutation under the supported-owner locks.
9. **Common storage routing.** Every P7 released-scratch action, whether top-level file or directory, must route through this P7-specific mutation boundary. Generic storage removal remains valid for owners whose accepted authority does not require this specialization.

### Acceptance boundary

Exercise the real storage executor, real P7 owner classification/certification, and production owner locks. Race injection may wrap the descriptor/open/mutation primitive **below** those semantic owners but may not replace the owner decision.

Required counterfactuals:

- replace the generation, `attempts`, or attempt entry before fresh strict reacquisition: no released authority is produced and the foreign tree is untouched;
- acquire the real attempt descriptor, then replace the public attempt pathname before the fd-relative released action: the replacement tree is never traversed or mutated under the original authority; the operation may safely complete against the already-open owner object where the OS permits that semantics or may refuse, but authority may not transfer to the replacement;
- exercise both a proof-certified top-level regular file and a directory;
- preserve special-node, symlink, wrong-kind, unrecorded-node, nested-mount, and cross-generation-copy refusals;
- on an unsupported platform lacking the required no-follow/dir-fd primitives, consequential P7 reclamation refuses explicitly rather than falling back to path traversal.

This section **replaces Revision-25 §2's stronger inode-CAS-like wording**. Revision-25 §1, §3, and the substantive need for final candidate evidence remain binding as refined below.

---

## 2. R26-B — current-authority test-suite retirement policy

### Objective

Reduce the default suite to tests that protect current supported product behavior, explicitly supported compatibility, or high-value current structural absence invariants. Historical development chronology belongs in history/evidence, not in the executable regression suite.

The retirement decision is semantic, not filename-based and not motivated merely by runtime cost.

### Current authority used for classification

The implementation must classify tests against the **current** architecture and `docs/specs/training_data/README.md` index, plus accepted current compatibility code/contracts.

The current repository explicitly establishes that:

- only specs listed by the current specification index are normative current owners;
- unlisted release/gate/migration-era specs are historical residue;
- retired multi-view / migration / generated-rescue / pre-target per-domain authorities are historical or reject-only;
- unsupported old campaign artifacts require re-preparation; historical readability is not automatically a current product-semantic obligation;
- P6 destructively removed the old MVSEL/MVQUAL/FEAS/MLCV final/migration/verification/old lifecycle code and installed current negative structural guards.

### Delete/retire when all material value is historical

A test or executable benchmark belongs outside the live default suite when its only claim is one or more of:

- an exact old package version being current;
- an old architecture revision/schema/gate being current;
- historical gate ordering/status prose;
- existence/content of a migration-only or otherwise non-current specification;
- behavior of a module/public symbol that P6 intentionally deleted and current architecture rejects;
- an executable benchmark driver whose imports point only to deleted P6 machinery;
- a fixture used solely to exercise an unsupported historical schema/path that current product authority says must reject/reprepare, unless current runtime explicitly retains that schema compatibility.

Historical evidence files may remain under the repository's history/audit/benchmark evidence policy when needed to interpret durable evidence. They do not need an executable pytest asserting their old release was still current.

### Preserve or consolidate when a live contract remains

Do **not** delete a whole file merely because its filename contains `legacy`, `migration`, an old gate name, or a past release. Preserve the current behavioral portion when:

- a current runtime module/API is still owned and exercised;
- current code explicitly supports a legacy schema/read path;
- the test protects current public serialization/API/defaults;
- it is a current negative structural guard proving retired code remains absent;
- it validates a current specification in the current spec index.

Where a file mixes historical prose assertions with current behavioral assertions, delete the stale assertions and consolidate the live ones into the current owner-focused test module when that reduces duplicated fixture/import cost.

No new test registry, manifest, marker bureaucracy, or second authority index is required.

---

## 3. R26-C — confirmed retirement floor

The repository inspection identified the following as **confirmed obsolete executable test/benchmark debt**. Implementation must remove these live pytest/benchmark surfaces unless it discovers concrete current production ownership contradicting the evidence below; such a contradiction is a bounded design-reopen trigger rather than a reason to silently keep the historical assertion.

### Whole test files / helpers

- `tests/test_mlff_adaptive_training_revision_plan.py` — historical adaptive gate ordering/manual prose and exact `0.20.140a0` package pin;
- `tests/test_mlff_conventional_cv_revision_plan.py` — historical conventional-CV gate/manual chronology only;
- `tests/test_mlff_mvstate_reuse1_specification.py` — historical Revision-103/0.20.236 gate/evidence assertions and direct references to P6-deleted selection-state/repair modules;
- `tests/test_mlff_target_data2b_feas1_perf1_specification.py` and its FEAS1 historical PERF2/PERF3 specification siblings — retired FEAS/current-gate architecture snapshots;
- `tests/test_mlff_mlcv_agg1_specification.py` — retired aggregate gate/spec chronology;
- `tests/test_mlff_mlcv_final1_specification.py` — retired `mlcv_final` gate/spec chronology;
- `tests/test_mlff_mlcv_migrate1_specification.py` — migration-only, explicitly non-current contract;
- `tests/test_mlff_mlcv_verify1_specification.py` — retired verification-owner/source/spec assertions;
- `tests/test_mlff_data9a7d_specification.py` — historical profile-extension migration gate/old graph/version snapshot; current profile-extension behavior is covered separately;
- `tests/_mlff_multiview_legacy_fixtures.py` — retired MVSEL/repair fixture helper with no current owner;
- `tests/test_mlff_mvsel2_oracle.py` and `tests/support/mlff_mvsel2_oracle.py` — retired selector oracle pair;
- `tests/test_benchmark_mvqual_mem1_m5.py` — unit wrapper for the dead MVQUAL2 product benchmark.

### Dead executable benchmark drivers

At minimum remove these live benchmark scripts because they import P6-deleted target-size owners:

- `benchmarks/benchmark_mvqual_mem1_m5.py`;
- `benchmarks/benchmark_mlff_mvsel2_phase_a.py`;
- `benchmarks/benchmark_mlff_mvkernel1.py`.

The exhaustive audit in §5 must catch additional executable `.py` benchmark drivers importing P6-retired module names (including other historical `mvsel2` scripts). Historical JSON/Markdown results may remain if needed as evidence; executable drivers that cannot run against the current codebase should not remain live tooling.

### Retired test fixtures

After confirming no retained current test consumes them, remove:

- `tests/fixtures/legacy_schema_0_20_76/`;
- `tests/fixtures/mlff_mh1_base0_legacy_mpa0.json`.

Release/checksum history may continue to record their historical digests; that does not make them current pytest fixtures.

---

## 4. R26-D — mixed/current test preservation map

The following inspection findings are **preservation constraints**, preventing over-aggressive cleanup.

1. `tests/test_mlff_prec1_specification.py`: remove the stale release/architecture-revision assertion, but retain or consolidate the still-live precision public-contract assertions. `tests/test_mlff_prec1_precision_profiles.py` is the preferred current behavioral owner where equivalent coverage already exists.
2. `tests/test_mlff_data1_specification.py`: retain current sampling/numerical/API behavior, but remove old package-version/gate-status assertions and per-spec generated-PDF-size ceremony where publication/build checks already own the rendered artifact.
3. `tests/test_mlff_adapt_mon1_specification.py`: `mlff_online_monitor_spec.md` remains current. Preserve current policy/config/default behavior; remove old package-version and historical gate-status ordering assertions.
4. `tests/test_mlff_mlcv_mon1_specification.py`: the MLCV monitor runtime remains used by current DATA8. Preserve current `MlcvMonitorPolicy`/schema/default/round-trip behavior, preferably under the current DATA8/monitor owner; remove old release/manual gate chronology.
5. `tests/test_mlff_mlcv_stop1_specification.py`: remove stale release/manual-gate assertions; preserve current generated defaults and active stop-policy schema behavior, consolidating into `tests/test_mlff_adapt_stop1_adaptive_training.py` where non-duplicative.
6. `tests/test_mlff_adapt_stop1_adaptive_training.py`: **keep**. Current `adaptive_stop.py` explicitly supports v1/v2 policy/state schemas, so its legacy-schema round-trip is a real current compatibility contract and must not be deleted merely because old campaign migrations elsewhere were retired.
7. `tests/test_mlff_data9a7d_profile_extension_migration.py`: **keep** (renaming optional). Despite the filename, it exercises current material/profile Data4/Data6 canonicalization, current focus-group behavior, and current production-record behavior.
8. `tests/test_mlff_data9b3_campaign_cli_specification.py`: **keep**; it is aligned to the current specification index and current package/CLI/graph.
9. `tests/test_mlff_doc_arch1_specification.py`: **keep**; it protects current architecture assembly/current-owner absence.
10. `tests/test_mlff_target_size_p6_destructive_closure.py`: **keep**; it is the high-value current negative structural guard proving P6-retired modules/symbols do not re-enter the product.

If equivalent current behavior is already protected elsewhere, consolidate rather than duplicate. Coverage may shrink in file count without shrinking the current behavioral surface.

---

## 5. R26-E — exhaustive retirement audit before deletion closes

The confirmed floor above is not the entire cleanup. Implementation must inspect the complete live `tests/` and executable `benchmarks/**/*.py` surface and classify all candidates against current owners.

### Required audit dimensions

1. **P6-retired module imports/references.** Start from the canonical P6 destructive-closure retired-module/public-symbol set. Find any remaining test/helper/benchmark import or executable source reference to those deleted names. A live current-owner reason is required to retain it.
2. **Stale exact current-package pins.** Search executable tests for assertions that `mdstats.__version__` / `pyproject` equals a historical release. Current package-version synchronization may be checked centrally against `0.20.242a0` (or equivalent current source identity), but old gate tests must not each pin the release in which they were authored.
3. **Non-current spec/history dependency.** Tests whose only target is an unlisted migration/gate/release spec or historical architecture snapshot should leave the default functional suite. Current docs publication/structure checks remain where they protect current authority.
4. **Missing fixture errors.** P6's baseline recorded missing `tests/data/*.json` as another major source of full-suite error. For each remaining missing fixture reference: restore/minimize it if a retained current owner needs the fixture; otherwise delete the retired test/reference. Do not suppress collection/runtime failures by blanket skip.
5. **Dead benchmark tooling.** Import/parse every retained executable benchmark sufficiently to establish that it targets current modules. Historical results can remain as evidence even when the driver is removed.
6. **Orphan support files.** After test deletion, remove helper modules/fixtures with no retained consumer.

### Anti-shortcut

Do not bulk-delete all `*_specification.py`, all tests containing an old release string, or all files whose name contains `legacy`/`migration`. The mixed/current map above demonstrates why that would delete supported behavior.

Do not convert obsolete failures to broad skips. Remove historical-only tests or repair current tests so collection and execution state are truthful.

### Stage acceptance

The test-retirement stage closes only when:

- `pytest --collect-only -q` succeeds with no dangling deleted imports, missing modules, or fixture-collection errors;
- `tests/test_mlff_target_size_p6_destructive_closure.py` passes;
- retained current tests that were edited/consolidated pass;
- no live test/helper/benchmark imports a P6-retired module unless an explicitly retained current compatibility product owns it;
- no live test claims a historical package release is the current package release;
- no stale live benchmark driver imports deleted target-size owners;
- review of the diff shows current runtime/API/serialization/structural coverage was preserved rather than replaced with history checks.

This is test/product hygiene; it does not require a production GPU/HPC run.

---

## 6. R26-F — make final acceptance affected-surface based, not ceremonially full-suite based

Revision 25's exact-candidate evidence remains required, but the storage workplan must not turn the entire historical repository test population into a mandatory release gate when the affected behavior is confidently bounded.

### Mandatory final storage acceptance

After all executable storage repairs and test-retirement edits are complete on the same candidate:

1. run every focused Revision-22/23/24/25/26 P7 namespace/state/proof/root/mutation/concurrency counterfactual;
2. run full `tests/test_mlff_storage_reset_core.py`;
3. run full `tests/test_mlff_storage_reset_integration.py`;
4. run the affected **current-owner** regressions for P1/P3/P4/P5/P7 plus `test_mlff_target_size_p6_destructive_closure.py` and current lifecycle/publication/restart/retention/qualification consumers where the common owner/inventory/executor path can propagate;
5. run `pytest --collect-only -q` for the cleaned default suite;
6. re-derive the affected surface from the final executable + test-hygiene diff, then run a fresh final affected regression/integration set for every resulting behavioral dependency;
7. run repository static checks and affected current specification/document build validation.

### Whole-repository behavioral pytest

Run the entire repository behavioral suite **only** when final impact analysis cannot confidently bound the affected surface or when an independent repository/release policy requires it. A full-suite run remains useful broad evidence, but it is not a substitute for the mandatory focused/current-owner coverage above and is not a ceremonial storage gate merely because it exists.

If a broad/full run is performed after cleanup, newly introduced or affected failures block acceptance. Demonstrably unrelated failures may be attributed according to Protocol 5.10, but the cleanup goal is that default collection itself is clean rather than permanently carrying known obsolete errors.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not functional-acceptance blockers.

---

## 7. Implementation authority

### Frozen

- Revision-19/21/24 owner-driven storage architecture and P1-P7 science/currentness semantics;
- Revision-25 §1 single descriptor-bound P7 storage-facing census/proof/certification requirement;
- Revision-25 §3 proxy-proof fixture corrections, reconciled to the R26 descriptor-pinned mutation contract;
- R26 descriptor-pinned P7 authority-root/ancestor continuity and fd-relative no-follow mutation under supported-owner synchronization;
- generation-scoped released-attempt proof identity;
- workspace-wide fail-closed unknown-attempt retention;
- supported Python floor `>=3.10`;
- current-spec-index / current-runtime ownership as the authority for test retention;
- preservation of explicitly supported legacy serialization contracts;
- final affected-surface regression/integration as the functional completion gate.

### Delegated

- exact small fd-relative recursive helper structure and internal function names;
- whether current behavioral assertions from mixed historical test files are moved into existing owner-focused files or retained after stale assertions are removed;
- ordering/naming of historical evidence files that remain outside functional pytest;
- exact batching/parallelism of CPU-safe tests, provided coverage is preserved.

### Reopen only on evidence

Reopen only the affected surface if:

- the supported Python/POSIX targets lack the no-follow/dir-fd primitives needed to preserve the accepted descriptor-pinned P7 boundary without disabling materially required reclamation;
- an item in the confirmed retirement floor is proven to exercise a still-supported current runtime/API/compatibility contract not represented elsewhere;
- final affected-surface derivation discovers an unbounded behavioral dependency requiring a broader acceptance suite.

Do not reopen P1-P7 science, target-size architecture, or CampaignStore design for these cases.

---

## 8. Implementation sequence

### R26-T1 — retire historical test/tool debt first

Perform §2-§5 cleanup. This is intentionally first so subsequent final evidence runs against the suite the product actually intends to maintain.

Closure: clean collection + current retained behavioral tests + P6 destructive structural guard.

### R25-P7 — finish the single descriptor-bound owner path

Implement still-binding Revision-25 §1 and corrected proxy-proof fixtures/structural absence guard.

Closure: focused namespace/proof/state/cross-generation/mount regressions.

### R26-M — close released mutation continuity

Implement §1 for both top-level files and directory subtrees under the real executor/owner locks.

Closure: real-owner fd-bound race counterfactuals + affected cleanup regression.

### R21-E5/F — final assembled acceptance

Reconcile the complete accepted contract, re-derive the affected surface, execute §6 mandatory acceptance on the exact executable candidate, and bind evidence to its commit/tree.

No dependent production qualification is inserted between these functional stages.

---

## 9. Handoff closure

The snapshot-complete current handoff is the existing supplied storage authority set through Revision 25 plus this Revision 26 and its authority routing. An implementer who has no prior chat or Git history must still recover:

- why P7 state/proof/member authority is descriptor-bound;
- the generation-scoped proof-root identity;
- the exact owner synchronization order;
- the corrected descriptor-pinned, fd-relative mutation guarantee and its realistic threat boundary;
- the Revision-25 proxy-proof defects that must be corrected;
- the test-retirement/current-compatibility distinction and confirmed retirement floor;
- the final affected-surface acceptance boundary and conditional status of whole-repository pytest.

No still-binding requirement depends only on this conversation.

**Final plan verdict:** **CLOSED / implementation-ready under Revision 26.**

**Executable verdict:** **NO-PASS / reopened** pending implementation and evidence.