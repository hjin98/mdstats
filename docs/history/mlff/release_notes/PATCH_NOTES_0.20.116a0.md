# mdstats 0.20.116a0 patch notes

- Implement MLFF STOR5 immutable exact-byte deduplication and authenticated reversible cold archival.
- Add `deduplicate [--apply]`: after verification plus protocol freeze, known immutable campaign-owned families are SHA-256 grouped and exact duplicates may be atomically replaced by same-filesystem hardlinks backed by `.mdstats/content-store/sha256/...`. Active checkpoints, campaign state, logs, production models, selected raw checkpoints, configured external inputs, and symlink targets are excluded.
- Add `archive create|verify|restore`. Cold archives are self-contained `tar+gzip` objects with workspace-relative members, per-file SHA-256/size/mode records, a manifest-content digest, and archive SHA-256. Hardlinks are dereferenced in the archive so restoration never depends on the hot content store.
- Enable `cleanup --tier archive --apply`: after the mandatory STOR4 plan and any independently lossless STOR2 checkpoint compaction, mdstats recollects the exact consequential hot layout, creates and independently verifies the archive, commits its receipt, and only then deletes archived hot roots. Any archive/manifest/member/ownership failure leaves consequential hot bytes intact.
- Add exact restore staging/conflict checks and post-restore rehashing. Existing conflicting bytes are never overwritten. Restore receipts are persisted in campaign state/results.
- Prune orphan content-addressed objects after reclamation so prior deduplication cannot pin bytes that archive/cleanup has removed from the hot layout.
- Extend STOR1 storage classification with `immutable_content_store` and `cold_archive` families.
- Advance the MLFF architecture dependency graph to revision 34. The post-0.20.105 EVAL-MF/PREC/STOR roadmap is complete.

- Restore the historical 0.20.76 legacy-schema JSON fixtures to packaged sdists so compatibility tests exercise the same byte identities as the source tree.
