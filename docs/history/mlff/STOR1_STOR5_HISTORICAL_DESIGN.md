# MLFF STOR1-STOR5 Historical Campaign Storage Design

Status: Historical reference archive. Preserved from original 0.20.111a0-0.20.116a0 design notes. Current normative specification is in `docs/specs/training_data/mlff_storage_management_spec.md`.

## Overview

This document preserves the original design notes and historical milestones for STOR1 through STOR5:
- STOR1: Accounting and ownership boundary (0.20.111a0)
- STOR2: Completed-checkpoint compaction (0.20.113a0)
- STOR3: Automatic lifecycle-safe reclamation (0.20.114a0)
- STOR4: Manual tiered reclamation (0.20.115a0)
- STOR5: Immutable deduplication and authenticated cold archival (0.20.116a0)

Under P6/P7 transitional governance, consequential storage operations (`recompute`, `compact`, `archive`, `deduplicate --apply`) are quarantined and deferred to the post-P7 unified storage reset (`CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`).

---

## STOR1 - accounting and ownership - implemented in 0.20.111a0

STOR1 is read-only with respect to reclamation. It introduces artifact ownership/retention classification and a
storage report with logical bytes, allocated physical bytes when available, unique-inode
bytes, largest artifacts, restart/re-evaluation value, and reclamation eligibility.

Deletion eligibility requires campaign ownership, real-path containment, no symlink
escape, and a declared retention class. The implemented `storage` CLI emits
`results/storage-report.json` and performs no reclamation. It reports path-logical,
inode-deduplicated allocated physical, and unique-inode logical bytes, plus artifact
families, protected inputs, symlink escapes, largest files/directories, and future
reclamation/capability classifications.

The ownership boundary protects the campaign config and all configured source,
foundation, replay, and true-label inputs even when physically nested inside the
workspace. Existing cleanup/pruning now consumes the same boundary, so external paths
referenced by campaign records cannot gain deletion authority. Tests cover
malicious/accidental external references, symlink traversal, hardlinks, external
materialization roots, and campaign symlinks whose targets must survive.
The implementation distinguishes authorization to unlink a contained symlink object from
a stricter traversal authorization; cleanup roots are traversed only when their resolved
targets remain inside the campaign boundary and outside every protected input.

---

## STOR2 - completed-checkpoint compaction - implemented in 0.20.113a0

Full optimizer checkpoints remain untouched for active/interrupted training and, by
default, while the eventual production winner is still unknown. A model-state-only
**evaluation state capsule** (the STOR2 evaluation capsules representation) is therefore created only after a run has a durable
scientific checkpoint selection: the selected production checkpoint remains byte-for-byte
full/restart-capable, while each nonselected checkpoint may be replaced by an
authenticated capsule. This slightly more conservative lifetime is intentional: a
model-only capsule cannot preserve optimizer continuation for a checkpoint that might
later become the production winner.

The v1 capsule preserves the original checkpoint scientific identity and stores the exact
MACE model state plus the source checkpoint SHA-256, epoch/run lineage, immutable MACE
configuration digest, reconstruction contract, model-state digest, and capsule byte
identity. OPT-EVAL1/OPT-EVAL4 source resolution accepts either the original raw checkpoint
or a validated capsule, so true-label refresh and later checkpoint re-evaluation can reuse
the compact representation without changing selection identity. The completed-run
validator likewise accepts the immutable original checkpoint catalog represented by a
mixture of raw checkpoints and authenticated capsules.

A raw nonselected checkpoint is removed only after all of the following succeed in order:

- its original SHA-256 and run/epoch lineage are verified;
- the capsule is atomically written and authenticated;
- direct MACE reconstruction from the capsule succeeds;
- reconstructed deployable model state exactly matches reconstruction from the raw
  checkpoint;
- a real MACE 0.3.16 qualification confirms identical energy, force, and stress outputs;
- the capsule is smaller than the source checkpoint (otherwise the raw checkpoint is
  retained);
- the capsule record is committed to campaign state and independently read back and
  re-authenticated; and only then
- the raw checkpoint is deleted through the STOR1 ownership boundary.

Unsupported checkpoint layouts, missing/changed DATA8 configuration, capsule corruption,
reconstruction mismatch, ownership ambiguity, or a non-saving capsule all fail closed to
ordinary raw-checkpoint retention. The selected production checkpoint and production
model remain retained by default. STOR2 introduces no broader cache/artifact reclamation;
that authority begins at STOR3.

---

## STOR3 - automatic lifecycle-safe reclamation - implemented in 0.20.114a0

Automatic cleanup is restricted to artifact classes whose removal causes no loss of
current scientific result or required restart capability. Examples include garbage,
stale staging, obsolete runtime archives after compact diagnostics, orphan payloads,
successful-preflight temporaries, and qualified reconstructable graph/view caches.

Checkpoint/capsule removal is permitted only after EVAL-MF lifetimes and final selection
are satisfied and a stronger surviving artifact or prediction record preserves the
required capability. Automatic low-disk recovery runs this safe policy before
interrupting active jobs and never broadens deletion authority merely to meet a free
space threshold.

Every automatic cleanup appends one authenticated JSONL event to `results/cleanup-manifest.jsonl`, recording removed paths, bounded pre-deletion filesystem identities, reasons, reclaimed bytes, preserved capabilities, and an explicit empty capability-loss set. The manifest itself is ownership-checked and append-only.

STOR3 also changes low-disk training behavior: the scheduler runs this safe policy before requesting interruption. Active run roots are excluded; only if free space remains below the configured reserve are active children stopped at durable checkpoints. Evaluation graph/view caches become automatically reclaimable only after authoritative evaluation is complete. Prediction caches (`evaluation-predictions`, DATA6/model-sweep, true-label replay) remain outside STOR3 authority because they preserve expensive metric-only/reanalysis capability.

---

## STOR4 - manual tiered reclamation - implemented in 0.20.115a0

Manual cleanup exposes increasingly cumulative tiers through `storage cleanup --tier`. Every invocation first computes and prints/writes a dry-run capability plan. The historical semantics were ordered:

- `safe`: no scientific/restart capability loss;
- `cache`: only reconstructable acceleration caches; future execution may be slower;
- `recompute`: expensive but reproducible prediction/DATA6-style artifacts; future
  reselection/re-evaluation may require substantial inference;
- `compact`: nonproduction checkpoints/models and cold materializations after protocol
  freeze; exact continuation or cheap alternative-model recovery may be lost;
- `archive`: explicitly selected cold reproducibility material converted to verified
  archival representation.

The implementation distinguishes planning from authorization. `safe` and `cache` retain low-consequence behavior; `recompute` and `compact` were plan-only unless `--apply` was supplied. With STOR5, `storage cleanup --tier archive --apply` first created and independently verified a reversible cold archive of every consequential `recompute`/`compact` hot artifact; only after that receipt was committed could those hot representations be removed.

---

## STOR5 - immutable deduplication and authenticated cold archival - implemented in 0.20.116a0

STOR5 closed the optional physical-storage layer without changing scientific identities.
`storage deduplicate` scanned only verified/frozen campaign-owned immutable families. Exact byte
duplicates were SHA-256 grouped and, with explicit `--apply`, replaced atomically by
same-filesystem hardlinks backed by `.mdstats/content-store/sha256/<prefix>/<digest>`.

Cold archival was exposed through `storage archive create|verify|restore` and through
`storage cleanup --tier archive --apply`. Archive candidates were the consequential STOR4
`recompute`/`compact` actions only; safe/cache garbage need not be archived. The archive
was a self-contained `tar+gzip` representation under `.mdstats/cold-archive/`.
