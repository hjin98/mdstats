# Documentation

Start with [`INDEX.md`](INDEX.md) for the current documentation map.

The documentation tree is organized by artifact responsibility:

- `arch_manuals/` owns accepted current structure, theory, data/control flow, ownership boundaries, and durable design decisions that span modules.
- `specs/` owns accepted current behavior: APIs, schemas, numerical rules, persistence, runtime semantics, compatibility, and product acceptance contracts.
- `guides/` owns stable user/operator procedures.
- `history/` owns completed non-normative chronology and selected historical snapshots.
- repository-root `workplans/` owns proposed transitions and developer implementation gates and is excluded from user/runtime distributions.
- `../audits/`, `../benchmarks/`, and `../release/` own correctness, performance, and release/qualification evidence as appropriate.

Permanent specification/manual Markdown is kept synchronized with its repository PDF/provenance artifacts where that document family uses them.

## PDF publication

Tracked Markdown/PDF sibling pairs under `docs/` are ordinary PDF publications. A pushed Markdown change rebuilds only the publication targets that depend on the changed source; README/index/other Markdown without a declared PDF publication remains Markdown-only.

`docs/build_pdfs.py` is the publication driver. It discovers existing direct `X.md` -> `X.pdf` pairs and reads `docs/pdf_publications.json` for new publications and nontrivial source graphs. To introduce a PDF before its sibling PDF exists, declare that source/target explicitly in `pdf_publications.json`.

The MLFF architecture is composite rather than a direct editable pair: canonical chapter sources under `arch_manuals/mlff_training_data/` are assembled by `tools/build_mlff_architecture_manual.py`, then the derived `arch_manuals/mlff_training_data_architecture.md` is rendered to PDF. Derived Markdown/PDF outputs must not be edited independently.

Local maintenance commands include:

```bash
# Preview publications affected by a Git range.
python3 docs/build_pdfs.py plan --before <base> --after HEAD

# Rebuild all declared/discovered PDF publications.
python3 docs/build_pdfs.py build --all --report build/docs/publications.json

# Rebuild one publication target.
python3 docs/build_pdfs.py build --target docs/guides/mlff_campaign_cli_user_guide.pdf
```

GitHub Actions runs the same driver for pushed documentation changes on every branch and writes validated generated publications back to that branch when repository policy permits. Build-system changes deliberately use a full publication-consistency rebuild. The workflow renders transactionally and refuses stale output when a newer push changes the same publication inputs.

## MLFF data preparation and fine-tuning

- `arch_manuals/mlff_training_data_architecture.{md,pdf}` is the current normative MLFF architecture. It is assembled from indexed current-state chapter sources under `arch_manuals/mlff_training_data/` by `tools/build_mlff_architecture_manual.py`.
- `arch_manuals/mlff_training_data_dependency_graph.json` is the machine-readable **current product/data/runtime dependency architecture**; developer execution status is not stored there.
- `specs/training_data/` owns current MLFF behavior. Its legacy-named `mlff_data_stage_plan_spec.md` is the cross-cutting system contract, not an implementation roadmap.
- `guides/mlff_campaign_cli_user_guide.{md,pdf}` and `guides/mlff_final_gpu1_workstation_runbook.{md,pdf}` are operational runbooks.
- `history/mlff/` owns non-normative MLFF architecture/release lineage and selected pre-migration snapshots.
- active unfinished engineering transitions, including deferred workstation qualification work, live under `../workplans/active/` rather than in architecture/specification authority.

Current-state authority is updated when accepted software changes. Historical revision commentary and completed developer gate logs are recorded separately and must not be prepended to current architecture/specifications.

## Physical validation ownership

- `arch_manuals/structural_observables_architecture.{md,pdf}` owns structural-observable architecture.
- `arch_manuals/vacf_dynamics_architecture.{md,pdf}` owns displacement, velocity, spectra, diffusion, and current-based transport analyses.
- `arch_manuals/topology_statistics_architecture.{md,pdf}` owns graph-state statistics.
- `arch_manuals/thermomechanical_energetic_validation_architecture.{md,pdf}` owns thermomechanical/energetic validation architecture.
- `arch_manuals/framework_ring_architecture.{md,pdf}` and `arch_manuals/stage11_site_kinetics_architecture.{md,pdf}` own optional porous-framework, ring/site, and kinetic semantics.

The standardized dispatcher in `mdstats.analysis.observable_validation` binds recipes to the authoritative analysis APIs. The MLFF layer may invoke and compare those results but does not redefine their physical algorithms.
