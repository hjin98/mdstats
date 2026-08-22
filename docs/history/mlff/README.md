# MLFF documentation history

This tree records **non-normative completed lineage and design rationale**. Current architecture authority is the numbered canonical chapter set under `docs/arch_manuals/mlff_training_data/` together with `docs/arch_manuals/mlff_training_data_dependency_graph.json`. Exact current behavior is owned only by the specifications listed in `docs/specs/training_data/README.md`.

The assembled architecture Markdown/PDF are derived publication products; historical snapshots, workplans, audits, release notes, and generated artifacts do not override the canonical current sources.

Active proposed transitions and developer implementation gates live under repository-root `workplans/active/` until accepted or abandoned. Completed chronology belongs here rather than in current architecture/specifications.

## Concept-oriented design history

- `selector_repair_evolution.md` — why the selector/repair system moved from eager/inverse and state-reuse generations to the exact forward/lazy MVSEL2/REPAIR2/MVSTATE2/MVQUAL model.
- `target_size_evolution.md` — why budget/generated/rescue ladders were replaced by one fixed typed target-size study with nested prefixes and explicit non-convergence.
- `campaign_compatibility_evolution.md` — why migration/readability layers were retired in favor of current-generation validation or re-preparation.

These narratives preserve rationale while intentionally omitting obsolete schema details that remain recoverable from Git history when needed.

## Other historical collections

- `LINEAGE.md`: era-level development-history map.
- `architecture_revisions/`: historical architecture revision notes; see its index.
- `release_notes/`: release and hotfix deltas; see its index.
- `manual_snapshots/`: selected exact historical authority snapshots retained when useful for provenance.
- `legacy_rendered_artifacts/`: historical rendered artifacts without a current canonical-source role.
- `legacy_root_documents/`: retired parent-level reports retained for lineage.

## Historical retention rule

Retain an exact superseded specification/schema snapshot only when durable audit, benchmark, or release evidence cannot be interpreted without it. Otherwise prefer a concise conceptual narrative plus Git history.

When accepted software changes current structure or behavior, update the owning canonical architecture/specification first, regenerate any maintained publication artifacts, and then record the completed rationale/delta here. Historical material never regains normative authority merely because a current file links to it.
