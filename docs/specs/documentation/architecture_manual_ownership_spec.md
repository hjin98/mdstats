---
title: "Architecture Manual Ownership and PDF Parity Specification"
version: "0.20.16a0"
date: "2026-07-26"
---

# Purpose

This specification defines ownership, cross-reference, and generated-PDF parity
for the framework-topology and statistical-site architecture manuals.

**Temporary DOCS-INCREMENTAL-PDF-AUTOSYNC1 disjoint-target CI marker.**

# Manual partition

The architecture is split into two normative parts plus one descriptive status appendix.

1. `framework_ring_architecture.{md,pdf}` is **Part I**. It owns the
   species-independent periodic framework: connectivity, primitive rings,
   symmetry, embedding, natural tiling, tile/cage/window geometry, persistent
   ring geometry, atom-resolved serrated ring boundaries, and framework
   semantics through Stage 11D.
2. `stage11_site_kinetics_architecture.{md,pdf}` is **Part II**. It owns the
   registered, species-dependent statistical analysis beginning at Stage C0 and
   continuing through density evidence, site validation, temporal segmentation,
   observed paths/networks, pilot execution, and deferred kinetic models.

3. `stage11_site_kinetics_status_history.{md,pdf}` is descriptive. It owns
   release history, audit outcomes, and historical stage progression. It must not
   define current scientific contracts or the authoritative stage order.

Part II may summarize Part I input contracts, but it must not maintain a second
independent structural roadmap. Part I may state the handoff to Part II, but it
must not duplicate the statistical-site or kinetic plan. Historical "next stage"
statements belong only in the status appendix.

# Status vocabulary

Every planned branch must be labeled with one of:

- `implemented`;
- `implemented_but_scientifically_blocked`;
- `deferred`;
- `not_started`.

A release-complete implementation must not be described as architecture-complete
when deferred branches remain.

# PDF parity

For every maintained Markdown/PDF pair:

- the PDF must be generated from the same Markdown source in the release tree;
- title, revision/version, major headings, and completion status must agree;
- generated PDFs must be visually rendered before release;
- stale PDFs are release-blocking documentation defects.

Stage-local implementation notes may remain as Markdown-only audit records.
Permanent module specifications and architecture manuals must retain synchronized
PDF counterparts.

# Acceptance

- The duplicated Stage 11C-I roadmap is removed from Part I.
- Part I ends with the Stage 11D structural handoff.
- Part II begins with the Part I dependency contract and owns C0 onward.
- The status appendix is labeled non-normative and contains no current acceptance gate.
- The architecture-manual README names both parts and their boundary.
- Related PDFs are regenerated and render without clipping or broken glyphs.
## MLFF assembled-manual convention

The MLFF training-data architecture is maintained as numbered chapter sources under `docs/arch_manuals/mlff_training_data/` and deterministically assembled into `docs/arch_manuals/mlff_training_data_architecture.md`. The assembled Markdown/PDF pair is normative; chapter files are maintainable source partitions and must assemble byte-deterministically. Historical MLFF revision notes and release notes live under `docs/history/mlff/` and are non-normative. Root-level duplicate manual/spec/history artifacts are prohibited.

