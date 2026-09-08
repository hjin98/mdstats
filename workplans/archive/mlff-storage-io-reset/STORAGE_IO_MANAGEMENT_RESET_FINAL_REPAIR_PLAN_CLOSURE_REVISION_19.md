---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R19
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
amended_date: 2026-09-01
reviewed_executable_commit: 408cf5495e6e361b6273770d212dfb3bd2e23d95
reviewed_executable_tree: 13bea3b6fc63366d853454313c8ee7c3d2f36a0f
reviewed_candidate_head: 00fc36001f37fa81039f17d62436fb7deda89e80
reviewed_candidate_tree: 739114a59884ca8c231a4239da6ca4820aec3272
review_verdict: NO-PASS
scope: final independent challenge of the Revision-18 repair handoff against executable 408cf549; close typed/no-follow P5/P7 recursive ownership, authenticated and bounded P7 released-attempt authority, P7 attempt-state/storage synchronization and unknown-reference failure semantics, complete CampaignStore writer serialization and observational purity, CampaignStore writer-lock ownership census, and exact candidate-bound functional acceptance without reopening P1-P7 science
precedence: this amendment composes with the complete Revision-18 supplied contract; where it tightens recursive node typing, authority-file no-follow reads, P7 released-attempt proof/liveness/reporting, CampaignStore writer exclusion/observation/census, or final acceptance evidence, this amendment controls; all unaffected R11-R18 requirements remain binding
---

# Storage/I-O reset final repair-plan closure — revision 19

## 0. Disposition and implementation boundary

The Revision-18 implementation at executable commit
`408cf5495e6e361b6273770d212dfb3bd2e23d95` / tree
`13bea3b6fc63366d853454313c8ee7c3d2f36a0f` closes most of the earlier
R17/R18 defects. The docs-only successor
`00fc36001f37fa81039f17d62436fb7deda89e80` does not change executable
semantics. An independent closure challenge nevertheless found a small number of
material ownership/concurrency holes that can still authorize the wrong node,
lose P7 liveness protection, bypass the CampaignStore writer exclusion, or make
normal reporting scale with released P7 bulk.

This amendment is the implementation handoff for those remaining repairs. It is
**not** another storage architecture redesign. Preserve the conforming R12-R18
implementation, including the owner graph, compact P5 completion anchor/full
manifest split, protected retained-archive reauthentication, exact restore-parent
identity, low event-retention bounds, separate prune/VACUUM authority, serialized
audit append/retention, storage-owned dedup staging, observation capability,
bounded P5 reporting, and all accepted archive/dedup/recovery semantics.

No target-size science, P2 statistical rule, P3/P4 currentness, P5 CV or final-
production science, P7 qualification/calibration/locked-test/release science, or
frozen target-size V7 verdict is reopened. Full external-DFT, long GPU
production, and environment-specific HPC/storage qualification remain deferred.

Implementation must resume at the earliest affected R12-S0/S1 owner-contract
work, perform stage-local regression after each material repair, and then
continue through the existing R12-S4 final affected-surface acceptance. The
subsections R19-A through R19-F below are repair gates inside that existing
lifecycle, not a parallel lifecycle.

---

## 1. R19-A — typed, no-follow closed-subtree authority must survive from owner proof to mutation

### 1.1 Observed defect

P5 now records typed topology entries, but exact certification reduces both
recorded and observed nodes to path strings before comparison. A recorded regular
file replaced by a directory at the same relative path, or the reverse, can
therefore remain apparently certified. `_run_root_nodes()` also omits symlink and
special nodes, so a same-name substituted symlink/special object can disappear
from the comparison instead of contradicting the closed-subtree proof.

The common storage contract has the same information-loss problem:
`OwnerArtifactView.certified_members` carries only relative paths and
`StorageInventorySnapshot.authorized_members()` decides coverage from those path
names. Fixing only P5's local check is insufficient if the kind information is
discarded before cleanup/archive/dedup/reclaim reaches the mutation boundary.

The P5 completion/topology authority files are also read with ordinary
`Path.is_file()` / `read_text()` semantics. Those follow a symlink substituted at
`run-completion.json` or `run-topology.json`, allowing bytes outside the owner
record to participate in destructive certification.

### 1.2 Frozen end state

1. Introduce one typed owner-node representation used by consequential
   closed-subtree authority, for example an immutable `CertifiedNode` carrying a
   canonical POSIX-relative `path` and `kind` (`file` or `directory`). An
   equivalent representation is acceptable, but destructive authorization may
   no longer depend on path strings alone.
2. `OwnerArtifactView` carries the typed nodes through the owner adapter into the
   inventory/executor. An existing path-only `certified_members` field may remain
   as a derived display/compatibility surface, but it must not be the authority
   used for recursive disappearance.
3. Exact owner observation uses no-follow classification (`lstat` or equivalent):
   regular file, directory, symlink, and special/other are distinguishable. Do
   not traverse symlink targets.
4. For an authenticated recorded node that is present, current node kind must
   equal recorded kind. A file↔directory substitution is an ownership
   contradiction. Recorded nodes may be absent where the already accepted cold-
   reclamation semantics allow absence.
5. Any unrecorded present node of any kind, and any symlink or special node in a
   would-be closed subtree, reduces/refuses recursive authority. No symlink or
   special object is made owned merely because its relative name appears in a
   historical manifest.
6. P5 compact completion and full-topology records are opened by one strict
   regular-file/no-follow reader. Preferred POSIX realization: `os.open` with
   `O_RDONLY|O_CLOEXEC|O_NOFOLLOW`, `fstat` the opened descriptor as a regular
   file, then parse from that descriptor. If `O_NOFOLLOW` is unavailable, use a
   pre/post identity check that proves the opened regular file is the lstat'd
   entry or fail closed. `lstat` followed by ordinary `read_text()` is not a
   sufficient race closure.
7. P5's compact report path remains O(1) in descendant count. No R19 repair may
   make normal reporting read/hash the full P5 topology manifest.
8. Recursive deletion must remain symlink-attack resistant at mutation time. Use
   the platform's fd/no-follow-safe recursive deletion machinery where available
   (including verifying `shutil.rmtree.avoids_symlink_attacks` if relying on it),
   or an equivalent exact no-follow removal sequence. If the platform cannot
   preserve the proof from final revalidation through deletion, refuse recursive
   deletion rather than following a swapped directory entry.
9. Archive collection, dedup enumeration, reclaim, and cleanup all consume the
   same typed/no-follow owner authority. No specialized engine may silently
   recreate path-only authorization.

### 1.3 Required tests

Use the real P5 owner, inventory, planner, and executor.

- recorded file replaced by directory at the identical pathname -> exact
  certification and consequential planning refuse;
- recorded directory replaced by file -> refuse;
- symlink substituted at a recorded member path -> refuse without reading target;
- FIFO/socket/device/other modeled special node -> refuse;
- symlink substituted for the compact P5 anchor or full topology manifest -> no
  completion/destructive authority and target bytes are not consumed as owner
  proof;
- unexpected file and unexpected empty directory remain refused;
- legitimate recorded empty directory remains certifiable;
- absent recorded cold member remains compatible with the R18 recovery contract;
- common `authorized_members()` and every consequential engine preserve the same
  typed result rather than accepting a path-only substitution.

---

## 2. R19-B — P7 released-attempt scratch needs an authenticated typed proof and the same liveness seam storage uses

### 2.1 Observed proof defects

The current `mdstats.qualification-attempt-members.v2` record is not sufficient
to grant destructive ownership:

- it is a rewriteable JSON snapshot with no self content identity;
- the reader checks the schema but does not authenticate `attempt_root`,
  `member_count`, canonical/unique paths, or a binding to the exact released
  attempt state;
- members are path-only, so same-name file↔directory substitution is not caught;
- authority files are read through ordinary symlink-following file APIs;
- `qualification_views()` marks any top-level regular file in a released attempt
  reclaimable without checking that the manifest recorded it;
- a foreign empty top-level directory can certify vacuously because only its
  descendants are compared;
- nested symlinks/special entries are skipped rather than treated as
  contradictions.

These are storage-facing ownership defects only. They do not change P7's
scientific verdict or release-evidence graph.

### 2.2 Frozen P7 released-attempt proof

1. Replace the v2 destructive-authority semantics with a versioned v3 released-
   attempt topology proof, e.g. `mdstats.qualification-attempt-members.v3`.
2. The v3 payload binds at minimum:
   - schema;
   - exact attempt identity/root identity;
   - P7 binding digest;
   - publication digest;
   - released state (`terminal` or `aborted`);
   - the exact `QualificationAttemptState.content_digest` being published;
   - typed canonical nodes (`path`, `kind`) for regular files/directories owned
     by the attempt;
   - node/file/directory counts; and
   - a canonical self `content_digest` over the payload excluding that field.
3. Node paths are unique canonical POSIX-relative paths. Reject absolute paths,
   `..`, empty/`.` alias components, duplicates, infrastructure/self entries,
   unsupported kinds, and missing parent-directory topology.
4. Publication is one owner transaction under the existing per-attempt state
   lock. Construct the intended released `QualificationAttemptState` first;
   publish/fsync the v3 topology proof binding that state's content digest;
   publish the state second. The released state is the commit point. A crash
   after the proof but before the state therefore grants no release authority
   because current state/proof identities disagree.
5. An aborted attempt may later reopen. Once it becomes active, the old release
   proof is automatically inapplicable because it binds the prior released state
   digest. A later abort/release publishes a new proof then new released state.
   Terminal state remains monotonic. Repeated terminal release validates/reuses
   the existing bound proof; if it is missing/corrupt/conflicting, fail closed
   rather than reconstructing destructive authority by rescanning a potentially
   depleted/tampered tree.
6. The v3 proof is mutable only as required by a supported aborted→active→released
   lifecycle and only under the per-attempt owner lock. It is not scientific
   release evidence and grants no currentness. Outside that lifecycle, arbitrary
   modification is detected by its self/state identities.
7. One strict P7 reader validates the attempt state and v3 proof using no-follow
   regular-file opens. The same reader is used by inventory, retention,
   certification, and storage-facing reporting decisions; do not maintain a
   permissive raw-JSON reader beside it.
8. Exact certification compares a typed no-follow observation against the v3
   proof using the R19-A rules. Every top-level file or directory must itself be
   recorded before it can be exposed as reclaimable. Missing recorded nodes may
   be absent after prior safe cleanup; unexpected or wrong-kind present nodes,
   symlinks, or special nodes refuse authority.
9. The attempt state file and member-proof file themselves remain retained P7
   infrastructure. Cleanup never removes them as released scratch.
10. v2 development manifests may be recognized for diagnosis, but they grant no
    new consequential authority. Do not migrate a released v2 tree by blindly
    scanning its current contents, because that can absorb foreign content into
    ownership. Conservative retention is the compatibility behavior unless an
    independent authoritative migration source is later established.

### 2.3 P7 attempt-state/storage synchronization

The current storage mutation barrier holds the P7 generation publication seam,
whereas `acquire_attempt_reference()` and `release_attempt_reference()` mutate
attempt state under a separate per-attempt lock. That is not the same liveness
boundary. In particular an `aborted` attempt is currently storage-released but
may legally reopen as `active`; without a shared lock storage can delete scratch
while the attempt is reopening/using it.

Required repair:

1. Extend `OwnerSynchronization` with the exact P7 attempt-state lock paths for
   attempts touched by a plan. Derive them from the plan's P7 attempt artifacts,
   never from all attempts in the campaign.
2. Common order is fixed and documented:
   `storage-operation lease -> P5 run-activity locks (path order) -> P5
   publication barriers (generation order) -> P7 publication barriers
   (generation order) -> P7 attempt-state locks (path order) -> fresh inventory /
   plan revalidation -> narrow mutation`.
3. Audit all P7 product paths that acquire both a generation publication barrier
   and an attempt-state lock. Refactor any reverse order before introducing the
   shared storage lock. No expensive qualification work is moved inside the
   critical section.
4. Consequential resnapshot/revalidation occurs while the touched attempt-state
   lock is held. If an aborted attempt reopened first, its action becomes
   ineligible/refused. If storage acquired first, it completes the released-
   scratch mutation before the reopen can proceed.
5. Lock ownership is kernel/advisory-owner based as in existing publication
   locks; exceptions/process death must release it. PID/mtime/age inference is
   not liveness authority.

### 2.4 Unknown P7 attempt state is a cross-owner planning failure

`iter_attempt_states()` currently skips unreadable/corrupt state. That is unsafe
for storage because an active P7 attempt may reference exact P5 checkpoints or
other managed artifacts outside the P7 tree. Silently dropping an unreadable
state can therefore erase a cross-owner retention edge.

Required semantics:

1. No unreadable, malformed, symlinked, unsupported-schema, digest-invalid, or
   identity-inconsistent attempt state is silently omitted from the P7 census.
2. Normal reporting stays available and names the exact state path/reason.
3. For consequential storage, unknown attempt retention state is an owner-graph
   integrity/planning blocker because its `referenced_paths` are unknowable.
   Propagate this into the existing `StorageInventorySnapshot.require_planable()`
   gate (or an equivalently early global planning gate), not merely a local P7
   warning.
4. The qualification retention fence must carry the same ambiguity. Defense in
   depth must not let another destructive path ignore the failed owner graph and
   act on a possibly referenced managed path. Do not guess the missing
   references.
5. Once the state is repaired/authenticated, the blocker disappears and the
   exact reference set is used normally.

### 2.5 Required P7 tests

- foreign top-level regular file in a released attempt -> retained;
- foreign top-level empty directory -> retained;
- same-path file↔directory substitution -> retained;
- nested unexpected file/empty directory/symlink/special node -> retained and no
  symlink traversal;
- manifest symlink or state symlink -> no destructive authority;
- independently tamper root/attempt identity, binding, publication, state digest,
  node kind/count/path/self digest -> fail closed;
- malformed/absolute/`..`/duplicate/missing-parent node -> fail closed;
- v2 record is diagnostic-only and never authorizes cleanup;
- deterministic aborted-attempt reopen vs storage cleanup race exercises both
  orderings and proves active scratch is never removed concurrently;
- corrupt an active attempt state that references an exact P5 checkpoint:
  cleanup/archive/dedup planning becomes unavailable and the checkpoint remains
  untouched; repair the state and planning becomes available again.

---

## 3. R19-C — CampaignStore writer exclusion must be thread-correct, cross-instance, constructor-complete, and observationally pure

### 3.1 Observed writer-gate defects

The current process-safe `flock` direction is correct, but its reentrancy state is
instance-global rather than owning-thread scoped. Thread A can hold
`writer_exclusion()` while thread B using the same `CampaignStore` observes a
nonzero `_writer_depth` and is incorrectly treated as reentrant, proceeding
without the flock. Multiple store instances in the same process also have
independent local gates.

Writable `CampaignStore.__init__` performs schema/meta SQLite writes before the
common writer exclusion, so a second process can construct a store and mutate the
database while VACUUM believes all supported product writers are excluded.

### 3.2 Frozen writer-gate end state

1. One writer gate is keyed by the canonical database/lock identity and shared by
   every `CampaignStore` instance for that database in the process.
2. Preferred realization: a small module-local registry mapping canonical lock
   path to a gate containing a `threading.RLock` plus the outermost flock file
   descriptor/state. Equivalent code is acceptable only if it proves the same
   semantics.
3. Hold the in-process RLock for the entire yielded critical section. Reentrancy
   belongs only to the thread that owns that RLock; another thread blocks. A
   same-thread nested writer call, including through another store instance for
   the same database, may reenter without reacquiring a conflicting flock.
4. The outermost in-process holder opens and exclusively flocks the persistent
   writer-lock file; it releases/unlocks/closes on every exit. A separate process
   blocks on that flock.
5. Writable construction may create the parent needed to locate the database and
   lock, but it acquires the common writer exclusion before any SQLite
   schema/meta mutation and holds it through schema initialization. Constructor
   writes are part of the writer census, not a special bypass.
6. VACUUM retains the R18 discipline: after storage/owner synchronization, take
   the CampaignStore writer gate; under it perform the final benefit recheck,
   storage admission recheck, and VACUUM; release on success, refusal,
   cancellation, or failure. No archive hashing, P5/P7 scan, or unrelated work
   is added under the DB writer gate.
7. Lock order never runs backward from a CampaignStore writer into the storage
   operation lease or P5/P7 owner barriers.

### 3.3 Observational capability must fail before all side effects

`replace_records_atomically()` currently serializes/externalizes records before a
read-only SQLite connection can reject the eventual write, and it lacks an early
`_require_writable()` call. `writer_exclusion()` can also create its lock path if
called on a read-only store.

Required semantics:

1. Every public/owner CampaignStore mutator calls `_require_writable()` before
   any filesystem, external-payload, lock-file, SQLite, or receipt side effect.
   Add the missing early guard to `replace_records_atomically()` and re-derive
   the complete mutation surface rather than assuming this is the only one.
2. `writer_exclusion()` itself refuses a read-only store before creating/opening
   the writer-lock file.
3. Re-derive all SQL write sites reached through `_connect()` across the
   repository. Every product write is either inside the common writer gate /
   `exclusive_transaction()` or is explicitly refactored into one. Read-only
   SELECT and non-mutating PRAGMAs remain outside.
4. Structural/AST acceptance must include constructor writes; a method-only
   whitelist that omits `__init__` is insufficient.
5. A read-only operation remains non-creating even when a nested helper calls a
   nominal write API incorrectly: it fails before changing the filesystem.

### 3.4 CampaignStore writer lock is owner infrastructure

The persistent `${state_db}.writer-lock` is currently not represented as
CampaignStore-owned infrastructure in the owner census. It can appear as an
unclassified internal path. Although that currently tends toward retention, the
contract must be explicit: unlinking a held advisory-lock pathname can split the
serialization domain between the old inode and a newly created lock file.

Required semantics:

1. Add an explicit CampaignStore owner view for the exact writer-lock path, or an
   equivalent exact infrastructure view under the CampaignStore owner.
2. It is coordination infrastructure, not scientific authority, cache, archive
   content, or reclaimable scratch. Cleanup/archive/dedup never target it.
3. Add its exact basename to the recognized internal census so it is not reported
   as an unknown external artifact.
4. Do not delete/recreate the lock as maintenance. Its presence is harmless and
   preserves one stable flock namespace.

### 3.5 Required CampaignStore tests

- same store: thread A holds writer exclusion, thread B executes a real writer
  and blocks until A exits;
- two store instances for the same DB in one process serialize through the same
  gate;
- same-thread nested real write is reentrant and does not deadlock;
- child process begins `CampaignStore(create=True)` while parent holds writer
  exclusion: constructor cannot perform schema/meta writes until release;
- second-process writer invalidates a previously positive VACUUM benefit while
  maintenance waits; final under-lock recheck skips/refuses the now-unworthy
  VACUUM;
- benefit-positive case still VACUUMs;
- after successful VACUUM and injected predicate/admission/VACUUM exception, a
  fresh process can immediately commit a normal write;
- read-only `replace_records_atomically()` with a payload large/typed enough to
  externalize fails before creating external payload, writer-lock, SQLite
  journal, or any other path; filesystem signature remains unchanged;
- structural SQL/write census proves constructor and every product write site
  participates in the common writer boundary;
- inventory identifies the persistent writer-lock as CampaignStore owner
  infrastructure and no storage plan targets it.

---

## 4. R19-D — normal P7 reporting must be bounded independently of released scratch bulk

### 4.1 Observed defect

`build_storage_inventory(..., certify=False)` correctly gives P5 its bounded
mode, but `qualification_views()` has no corresponding `certify` parameter. It
iterates released attempt children and calls `certify_closed_attempt_member()`,
which recursively walks each directory. A normal `storage report` therefore
still scales with P7 descendant count, contrary to the accepted bounded-report
contract.

### 4.2 Frozen end state

1. Propagate the inventory `certify` mode into `qualification_views()`.
2. `certify=False` normal reporting reads only compact/no-follow P7 owner state
   needed to say whether an attempt is active, terminal, aborted, unresolved, or
   potentially released. It does not parse/hash the full v3 topology proof,
   enumerate every scratch child, recursively walk descendants, or imply that
   exact deletion authority has been established.
3. A released attempt may be represented in normal report as a retained
   container with `potential/needs exact certification` detail. Exact per-member
   reclaimability is a consequential-planning fact, not a reporting guess.
4. `certify=True` consequential inventory performs the full authenticated typed
   P7 proof and may expose only the exact verified scratch nodes as candidates.
5. Deep diagnostic reporting may perform explicitly bounded/capped extra work,
   but it remains observational and cannot substitute for consequential
   certification.
6. The P7 bounded path and exact path use the same state/proof schemas and
   current owner API; there is no second reporting truth.

### 4.3 Required tests

- construct released P7 attempts with small and very large descendant counts;
  normal report's owner-entry visits/bytes opened remain bounded with respect to
  descendant count and the full topology payload is not read;
- consequential planning does read/authenticate/walk the exact proof and catches
  its corruption/unexpected descendants;
- terminal and aborted status remain truthfully visible in bounded report;
- malformed state is reported unresolved and also activates the R19-B global
  planning blocker;
- existing P5 bounded-report benchmark remains unchanged/green.

---

## 5. R19-E — repair-gate implementation sequence and stage-local regression

Do not batch all repairs and test only once. Use the existing R12-S0 through
R12-S4 workplan lifecycle with the following repair order because later gates
consume earlier contracts.

### R19-E1 — owner-proof substrate

Implement R19-A typed node/no-follow primitives and the common owner-view /
inventory contract first. Update P5 to consume it. Run the focused P5 type-
substitution, symlink/special, cold-absence, bounded-report, and common
`authorized_members` tests plus the existing R18 P5/recursive-ownership tests.
Do not proceed with a known failure in this semantic owner.

### R19-E2 — P7 proof and liveness

Implement the v3 state-bound typed proof, strict state/proof readers, P7
attempt-state synchronization, and unknown-reference planning blocker. Run all
focused R19-B tests plus existing P7 currentness/release/retention/restart and
storage integration tests that touch attempts.

### R19-E3 — CampaignStore owner serialization

Implement the process-local shared RLock/flock gate, constructor coverage,
observational early guards, SQL write census, and writer-lock owner view. Run all
focused same-thread/cross-thread/cross-instance/cross-process/VACUUM/read-only
counterfactuals plus the retained R17/R18 maintenance tests.

### R19-E4 — bounded P7 reporting

Thread `certify` through P7 owner views, add the bounded released-attempt report
path, and run the P7 scaling/corruption tests plus existing normal/deep report
bounds.

### R19-E5 — stage-local affected regression

After each material repair, rerun the tests for modules changed in that gate and
the directly dependent storage paths. A passing later aggregate suite does not
replace stage-local evidence if an earlier semantic owner was never exercised in
its repaired state.

---

## 6. R19-F — final affected-surface re-derivation and candidate-bound acceptance

Before declaring implementation complete, derive the affected surface again from
the final diff rather than reusing this design-time file list. At minimum the
expected surfaces include:

- `campaign_post_selection_runtime.py` P5 completion/topology authority;
- `qualification/store.py` attempt state/released-member authority;
- `qualification/runtime.py` paths that acquire/release attempt references if
  synchronization order changes;
- `storage/owners.py`, `storage/inventory.py`, `storage/lease.py`, and every
  cleanup/archive/dedup/reclaim consumer of closed-subtree authority;
- `_campaign_cli_core.py` CampaignStore constructor/writer/mutator paths;
- `storage/maintenance.py` final VACUUM predicate path;
- storage core/integration acceptance and affected P1/P3/P4/P5/P7/P6 tests;
- specifications/user/architecture docs whose behavior contract changes.

The final executable candidate must have truthful executed evidence, not merely
new test source. Record commands/results together with the exact executable
commit and tree. A generated-document-only successor may reuse evidence only
after proving its executable tree is identical to the tested candidate.

Required final sequence:

1. focused R19-A through R19-D counterfactual tests;
2. every still-binding R17/R18 focused storage test;
3. full `tests/test_mlff_storage_reset_core.py`;
4. full `tests/test_mlff_storage_reset_integration.py`;
5. affected P1/P3/P4/P5/P7 currentness, publication, restart, retention, and
   qualification-owner tests, including P6 destructive closure where the common
   owner-proof/executor path is affected;
6. final affected-surface re-derivation from the completed diff;
7. fresh final affected regression/integration after that re-derivation;
8. CPU-safe broader/full tests where the final impact cannot be confidently
   bounded;
9. static checks plus affected docs/spec/build validation.

Acceptance evidence must make it possible to distinguish **not run**, **run and
pass**, and **deferred production qualification**. Full external DFT, long GPU
production, and environment-specific HPC/storage qualification are not part of
this functional acceptance and remain deferred as already frozen.

---

## 7. Explicit non-goals and preservation requirements

Implementation must not:

- replace the owner-driven storage architecture with pathname inference;
- introduce a persistent storage dependency/currentness database;
- introduce a new CAS/dedup registry or age/PID-based garbage collector;
- make P5/P7 storage proof grant scientific currentness;
- broaden archive roots or restore authority;
- make normal report pay O(descendant-count) work to claim exact certification;
- make a corrupt P7 state guess its prior referenced paths;
- make a read-only command create a CampaignStore writer lock or external record;
- hold the CampaignStore writer gate across unrelated storage scans/compression;
- reopen target-size, CV, publication, qualification, calibration, locked-test,
  or release science;
- substitute full production qualification for the required bounded functional
  regression/integration suite.

---

## 8. Plan-closure verdict

With R19-A through R19-F included, the remaining repair handoff is
**snapshot-complete and implementation-ready**. The global storage architecture
remains accepted; only the bounded owner-proof, P7 liveness/reporting, and
CampaignStore serialization surfaces above are reopened.

The executable remains **NO-PASS** until these repairs are implemented and the
exact final executable candidate has the required executed acceptance evidence.
