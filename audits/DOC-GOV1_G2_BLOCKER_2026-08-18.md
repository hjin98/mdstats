# DOC-GOV1 G2 qualification blocker — 2026-08-18

## Gate

DOC-GOV1 G2 — Separate MLFF architecture from implementation history/status.

## Migration base

- repository: `hjin98/mdstats`
- frozen base ref: `main`
- frozen base commit: `89e8bade5c697152d77942d8d649c135c5d80669`
- working branch: `agent/doc-gov1-g0`

## Completed G2 work

The MLFF architecture chapter set has been normalized to accepted current-state architecture. The former `70_status_and_gates.md` chapter was removed from the assembler and preserved byte-for-byte as:

`docs/history/mlff/manual_snapshots/mlff_training_data_status_and_gates_pre_doc_gov1.md`

The unfinished FINAL-GPU1 developer coordination now lives in:

`workplans/active/MLFF_FINAL_GPU1.md`

The following current-state architecture chapters were normalized and the assembled Markdown regenerated:

- `00_front_matter.md`
- `10_foundations.md`
- `20_data_contracts.md`
- `30_statistical_design.md`
- `40_training_evaluation.md`
- `50_target_multiview.md`
- `60_execution_performance.md`
- `80_ownership_and_decisions.md`
- `mlff_training_data_architecture.md`

Durable scientific/runtime contracts from the former status material were retained in Parts V/VI/VII as appropriate. Detailed performance chronology/evidence remains represented by the existing benchmark/audit/history material and by the preserved pre-migration snapshot.

## Acceptance checks completed

PASS:

- `tools/build_mlff_architecture_manual.py` no longer includes `70_status_and_gates.md` in its ordered source list.
- The assembled Markdown contains no former developer-status chapter.
- Targeted scans of the assembled Markdown find no `Next gate`, no `COMPLETE`, and no `Status and forward gates` project-tracking text.
- The current scientific/runtime architecture remains represented in the current-state chapters, including exact multi-view coverage/selection, MVIDX execution/storage, MVSEL/REPAIR authority, deterministic resource scheduling, replay/evaluation boundaries, progress formatting, and evidence ownership.
- The pre-migration status chapter is retained losslessly in MLFF history.

## Blocked acceptance item

G2 requires the changed permanent architecture Markdown to regenerate and check its synchronized PDF and provenance manifest using the repository's established renderer policy.

The existing manifest identifies that policy as:

- driver: `render_markdown_pdfs.py`
- policy: `pandoc-typst-v2`
- PDF engine: `typst`
- prior renderer versions: Pandoc 3.10.2 and Typst 0.15.1

The current execution environment provides Pandoc (`pandoc 3.1.11.1`) but has no Typst executable in PATH or the available system locations. The configured `mace` Conda environment is also not available in this execution environment. No repository CI workflow is present under `.github/workflows/` that can provide the approved renderer.

The checked-in `mlff_training_data_architecture.pdf` and its `.pdf.manifest.json` therefore remain the pre-migration versions and are intentionally **not** claimed as synchronized.

Per DOC-GOV1, PDF closeout must be reported blocked when the established renderer is unavailable and installing/bootstraping a replacement has not been authorized.

## Gate result

**G2 BLOCKED — PDF/provenance regeneration unavailable in the current execution environment.**

Do not advance to G3 until the established Typst-capable rendering environment is available or installation of the required renderer is explicitly authorized.
