# DOC-GOV1 G2 qualification blocker — 2026-08-18

**Status: RESOLVED on 2026-08-18.** The temporary inability to render with Typst was cleared by using a GitHub-hosted qualification workflow that downloaded the official Typst 0.15.1 Linux x86_64 archive, verified its published SHA-256, and ran the repository's Pandoc + Typst rendering policy. G2 subsequently passed and DOC-GOV1 advanced through later gates.

## Gate

DOC-GOV1 G2 — Separate MLFF architecture from implementation history/status.

## Migration base

- repository: `hjin98/mdstats`
- frozen base ref: `main`
- frozen base commit: `89e8bade5c697152d77942d8d649c135c5d80669`
- working branch: `agent/doc-gov1-g0`

## Completed G2 work

The MLFF architecture chapter set was normalized to accepted current-state architecture. The former `70_status_and_gates.md` chapter was removed from the assembler and preserved byte-for-byte as:

`docs/history/mlff/manual_snapshots/mlff_training_data_status_and_gates_pre_doc_gov1.md`

The unfinished FINAL-GPU1 developer coordination now lives in:

`workplans/active/MLFF_FINAL_GPU1.md`

The current-state architecture chapters were normalized and the assembled Markdown regenerated. Durable scientific/runtime contracts from the former status material were retained in their current architecture/specification owners; detailed chronology/evidence remains in history, audits, release material, and benchmarks.

## Acceptance checks

PASS:

- `tools/build_mlff_architecture_manual.py` no longer includes `70_status_and_gates.md`.
- The assembled Markdown contains no former developer-status chapter or project-tracking `Next gate` / `COMPLETE in 0.20.x` material.
- The current scientific/runtime architecture remains represented, including exact multi-view coverage/selection, MVIDX execution/storage, MVSEL/REPAIR authority, deterministic resource scheduling, replay/evaluation boundaries, progress formatting, and evidence ownership.
- The pre-migration status chapter is retained losslessly in MLFF history.
- The changed assembled Markdown, PDF, and provenance manifest were regenerated and hash-verified with Pandoc 3.10.2 + Typst 0.15.1 under the `pandoc-typst-v2` policy.
- Representative PDF pages were visually inspected without clipping, overlap, or broken glyphs.

## Original blocker and resolution

The original execution container had Pandoc but no Typst binary and could not resolve external hosts, so the pre-migration PDF was intentionally not claimed as synchronized. After explicit authorization to obtain Typst, DOC-GOV1 used a temporary branch-local GitHub Actions renderer. The hosted runner downloaded Typst from the upstream Typst GitHub release, verified archive SHA-256 `a6d077d0a95eed5a2eba715b2dae06be954f624ccbf85758a03f389ded33118c`, regenerated the architecture PDF/provenance pair, and passed the source/PDF hash checks.

## Gate result

**G2 PASS — blocker resolved.**
