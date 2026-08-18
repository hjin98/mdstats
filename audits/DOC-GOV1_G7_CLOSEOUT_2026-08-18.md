# DOC-GOV1 G7 — Final documentation-authority migration closeout

**Status:** PASS — DOC-GOV1 complete  
**Date:** 2026-08-18  
**Repository:** `hjin98/mdstats`  
**Working branch:** `agent/doc-gov1-g0`  
**Frozen migration base:** `main` at `89e8bade5c697152d77942d8d649c135c5d80669`

## Authority result

DOC-GOV1 establishes and qualifies the repository documentation authority model for the active MLFF family:

```text
accepted current structure       -> architecture manuals
accepted current behavior        -> specifications
proposed transition + gates      -> workplans
correctness/qualification evidence -> audits / release evidence
performance evidence             -> benchmarks
completed chronology             -> history / changelog / release notes
stable usage                     -> guides / runbooks
```

Runtime/product gates remain in current architecture/specifications when they define actual software behavior. Developer implementation gates and future engineering sequencing do not.

## Gate results

- **G0 PASS:** froze the reconciled migration base, pre-migration assembler/output identities, section-level classification, and lossless normative-clause ownership map.
- **G1 PASS:** established `workplans/{active,archive}`, template/governance guidance, updated `AGENTS.md`, and explicitly pruned `workplans` from distributions.
- **G2 PASS:** removed the developer-status chapter from current MLFF architecture, redistributed durable current contracts, preserved the old chapter in history, moved unfinished FINAL-GPU1 engineering coordination to an active workplan, regenerated the assembled Markdown/PDF/provenance pair, and resolved the temporary Typst availability blocker.
- **G3 PASS:** reframed the legacy-named stage-plan specification as the cross-cutting current system contract, removed its implementation-stage chronology from current authority, converted the training-data README to a current authority index, preserved exact pre-migration snapshots, and regenerated the specification PDF/provenance pair.
- **G4 PASS:** converted the dependency graph to `current_dependency_architecture`, removed development sequencing/status state, normalized current runtime/product dependency edge types, structurally validated all endpoints/types, and preserved the exact pre-migration graph snapshot.
- **G5 PASS:** reconciled `docs/README.md`, `docs/INDEX.md`, `docs/arch_manuals/README.md`, and `docs/history/mlff/README.md`; retained one exact migration-base assembled-manual snapshot and removed stale current-navigation descriptions of status/roadmap authority.
- **G6 PASS:** GitHub Actions run `32183157237` reproduced the assembler, checked governance sentinels, graph semantics, provenance, manifest pruning, and exact historical snapshot identities from a fresh checkout.
- **G7 PASS:** GitHub Actions run `32184450083` requalified the repaired final state: deterministic assembly; governance/graph checks; Pandoc 3.10.2 + verified Typst 0.15.1 rendering; semantic render comparison; PDF provenance; sdist/wheel build; distribution-content inspection; clean external wheel installation; `pip check`; and exact snapshot identities.

## PDF qualification

The established renderer policy is `pandoc-typst-v2` with Pandoc 3.10.2 and Typst 0.15.1. Typst was obtained from the upstream GitHub release using the official Linux x86_64 archive and verified against SHA-256:

`a6d077d0a95eed5a2eba715b2dae06be954f624ccbf85758a03f389ded33118c`

Final permanent pairs:

- `docs/arch_manuals/mlff_training_data_architecture.{md,pdf}` + `.pdf.manifest.json`
- `docs/specs/training_data/mlff_data_stage_plan_spec.{md,pdf}` + `.pdf.manifest.json`

The final architecture PDF is 35 pages. The final cross-cutting system-contract PDF is 11 pages. All pages were rendered to images for visual review. A first G7 visual pass discovered a real page-4 overlap in the original oversized record-family table; commit `686dea4d8ad68de11c5dcd3d8607dcc2eda2779f` split that table into two presentation-only tables without changing any row or normative meaning. The repaired PDF was then re-rendered, re-provenanced, requalified, and visually inspected with no clipping, overlap, black boxes, or broken glyphs.

PDF byte identity is intentionally not used as a rerender invariant because Typst embeds creation/modification timestamps and instance IDs. G7 instead requires matching source/provenance hashes for the tracked artifact plus matching page count and extracted rendered content under the locked renderer versions.

## Distribution qualification

Final artifacts built successfully as:

- `mdstats-0.20.241a0.tar.gz`
- `mdstats-0.20.241a0-py3-none-any.whl`

Qualification verified:

- `workplans/` is absent from both sdist and wheel;
- one-shot DOC-GOV1 migration helpers are absent from the sdist;
- required permanent documentation, graph, history/index files, PDFs, and provenance manifests are present in the sdist;
- the wheel retains the repository's intentional package-only layout rather than shipping root documentation trees;
- the wheel installs successfully into a fresh virtual environment outside the source checkout;
- installed package version is `0.20.241a0` and imports from the virtual environment, not the source tree;
- `pip check` passes.

No package-version bump is made for DOC-GOV1: the migration changes documentation authority/governance and generated documentation artifacts but not mdstats runtime semantics. Release policy can record the completed documentation migration without inventing a new runtime version at every documentation gate.

## Historical preservation and rollback

The following exact pre-DOC-GOV1 authority snapshots are retained under `docs/history/mlff/manual_snapshots/` and were hash-checked in G6/G7:

- assembled MLFF architecture — blob `37b44aed940d4fc4ee9e86ca0f0587c7c5f2344f`;
- former status/gates chapter — blob `39a4d44aaa25ae7838ed40b994e60f775d6af9b5`;
- former mixed stage-plan specification — blob `5454698cb5c3859ac5543967074f6ffe69bc03eb`;
- former mixed training-data specification index — blob `9bba16bac432e014b086abe4bbfb22d72c04e686`;
- former mixed dependency graph — blob `2025102638efb943338c224c6c3201e499a8cb20`.

The temporary GitHub Actions render/qualification workflows and one-shot migration helper scripts are migration machinery, not permanent repository authority. They are removed at closeout. The permanent reproducibility surface remains the normal MLFF architecture builder, tracked PDFs/provenance manifests, package metadata, governance documentation, history snapshots, and this audit evidence.

## Final decision

**DOC-GOV1 is complete. G0 through G7 all pass.** The current MLFF architecture/specification authority is unambiguous, completed chronology is preserved, future developer execution is separated into workplans, the architectural graph contains current dependency semantics rather than project-management state, permanent PDF/provenance policy is satisfied, and distribution contents are qualified.
