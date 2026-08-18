# mdstats 0.20.117a0 patch notes

- Consolidate the four MLFF campaign storage commands into one coherent hierarchy:
  - `storage report` — STOR1 read-only accounting/ownership report; bare `storage` remains an equivalent shorthand.
  - `storage cleanup` — STOR4 tiered reclamation and STOR5 archive-tier reclamation.
  - `storage deduplicate` — STOR5 immutable exact-byte content-addressed deduplication.
  - `storage archive create|verify|restore` — STOR5 authenticated reversible cold archive operations.
- Remove `cleanup`, `deduplicate`, and `archive` from the visible top-level parser surface. The `main()` entry point still normalizes those pre-0.20.117 spellings into the new hierarchy so existing shell scripts continue to run.
- Update the CLI guide, storage specification, architecture manual, README, and generated TOML comments to use the unified hierarchy.
- No storage algorithm, scientific identity, materialization identity, campaign-state schema, or cache identity changes. Existing campaigns remain directly reusable.
