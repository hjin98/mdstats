---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 11
status: active
amended_date: 2026-09-01
current_authority_pointer: true
implementation_intake_commit: 45b85e5dfb98bed4abbfee47cdb020bb2bd401c8
implementation_intake_tree: 3efc6297c31c1d233a733ec792f0fba08aea10a1
entry_condition: satisfied by P6 revision 13 independent PASS and P7 revision 13.7 software/functional closure PASS
precedence: this authority supersedes earlier mlff-storage-io-reset authority pointers; read STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md, STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md, and this revision-11 authority as one current snapshot-complete implementation contract; the frozen parent target-size V7 workplan remains the scientific and architectural verdict
---

# Storage/I-O reset package authority — revision 11 final review closure

## Current handoff

The current implementation contract is the composed set:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. this `AUTHORITY_REVISION_11.md` final archive-boundary correction.

Revision 11 adds only the two archive/integrity constraints below. All revision-2 and final-closure-amendment semantics remain binding. Earlier storage authority pointers and the original storage workplan are historical provenance only.

The package is **Design-closed / active / implementation-ready** at:

```text
commit 45b85e5dfb98bed4abbfee47cdb020bb2bd401c8
tree   3efc6297c31c1d233a733ec792f0fba08aea10a1
```

No P1-P7 scientific/currentness decision is reopened.

---

## R11-1 — archive/catalog locator containment is distinct from archive-member containment

The final low-level primitive inspection found that the historical archive verifier constructs the archive path from `manifest_path.parent / manifest["archive_file"]`. Archive-v2 must not inherit an assumption that a manifest-provided archive locator is automatically campaign-owned merely because archive members themselves pass traversal checks.

### Frozen end state

Archive-v2 has one storage-owned archive catalog/root. Every catalog, manifest, archive blob, journal, and receipt used by a storage operation must be resolved through that owner and pass the normal campaign/storage ownership boundary.

Required rules:

- archive blob locator in a manifest is a canonical identity-owned relative locator, not an arbitrary filesystem path;
- reject an absolute archive locator, `..`, empty/ambiguous normalization, symlink escape, or a locator resolving outside the authorized archive root;
- the manifest path/catalog entry itself must be inside the storage owner's authorized root and must bind the expected archive identity;
- do not follow a manifest field to read an arbitrary external file even when its bytes happen to satisfy a supplied digest;
- archive member path safety from the final-closure amendment remains separately mandatory; validating the outer archive locator does not replace member validation;
- restore through a user-supplied arbitrary external archive is not added implicitly by this package. If external archive import later becomes a supported product feature, it requires an explicit trust/import contract rather than reusing internal-catalog assumptions.

### Mandatory acceptance

- manifest `archive_file` absolute path rejects;
- `../` archive locator rejects;
- archive-root symlink escape rejects;
- manifest/catalog archive-identity mismatch rejects;
- valid identity-keyed archive in the authorized storage root verifies/restores normally.

---

## R11-2 — archive/catalog/restore terminal records require crash-durable publication ordering

Atomic rename prevents readers from observing a partial file during ordinary execution, but archive replacement is a durability/recovery feature. A terminal archive or restore receipt must not be published before the bytes and directory entries it authenticates have reached the repository's supported durable-publication boundary.

### Frozen end state

Reuse the repository's established crash-safe publication discipline where applicable:

```text
write/stage
 -> flush + fsync file content where supported/required
 -> atomic publish/replace
 -> persist parent-directory entry where supported
 -> authenticate published bytes
 -> publish dependent manifest/catalog/terminal receipt
```

For hot deletion after archive publication:

```text
authenticated archive + manifest/catalog durable
 -> fresh owner/dependency/race revalidation
 -> remove only still-authorized hot members
 -> persist deletion directory entries where supported when required by the promised recovery boundary
 -> publish truthful terminal/reclamation status
```

For restore:

```text
bounded authenticated staging
 -> durable file publication into canonical hot paths
 -> parent-directory publication durability where supported
 -> final owner/content authentication
 -> only then terminal restore receipt
```

Rules:

- do not claim power-loss durability stronger than the supported filesystem/runtime can provide;
- on filesystems where directory fsync or the selected atomicity primitive is unavailable, use the repository's accepted conservative fallback if it preserves the declared recovery contract; otherwise fire the existing filesystem-semantics Design reopen trigger;
- a manifest/catalog receipt may exist while some hot members remain after interrupted reclamation, but it must describe that state truthfully as specified in the final-closure amendment;
- existing current P1-P7 owner publication ordering is preserved and not weakened to make storage publication simpler.

### Mandatory acceptance

Ordinary tests need not simulate real power loss, but they must establish ordering and failure behavior with injected failures at each publication boundary:

- failure before archive blob publication leaves no terminal catalog receipt;
- failure after archive blob publication but before manifest/catalog terminality cannot authorize hot deletion;
- failure after authenticated catalog but during hot reclamation remains safely resumable/truthful;
- failure during restore publication cannot produce a terminal restore receipt;
- final receipt is emitted only after final canonical-byte authentication.

Structural inspection must confirm terminal receipt publication occurs downstream of the required flush/publish/authentication sequence, using the repository's durable publication helpers or an equivalent single owner rather than ad hoc divergent implementations.

---

## Final disposition

Independent final review now finds no remaining known material design gap at the bound intake baseline.

Implementation proceeds through S0 -> S6 under the composed current handoff. The highest-risk implementation boundaries that must remain explicit are:

- transitive cross-owner retention, including post-terminal P7 -> P5 checkpoint dependency;
- real P5 object-before-pointer race safety;
- current hot-owner evidence excluded from archive replacement;
- storage-native catalog/journal ownership;
- canonical storage-policy identity and replan behavior;
- bounded archive locator/member/expansion handling;
- crash-durable archive/restore publication ordering;
- hardlink metadata/immutability safety;
- truthful idempotent partial-operation recovery.

Full external-DFT scientific qualification, long GPU production qualification, and environment-specific HPC storage qualification remain deferred and are not routine implementation gates.