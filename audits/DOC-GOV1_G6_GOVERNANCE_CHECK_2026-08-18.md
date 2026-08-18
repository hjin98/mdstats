# DOC-GOV1 G6 — Documentation governance regression qualification

**Status:** PASS  
**Date:** 2026-08-18  
**Branch:** `agent/doc-gov1-g0`  
**Controlled-check commit:** `0af4e6fe45791e00a7cb4d8d0d5376deb5e6c058`  
**GitHub Actions run:** `32183157237`

G6 used a fresh GitHub-hosted checkout and lightweight structural checks only. No permanent governance-checker framework was introduced.

The controlled check verified that:

- `tools/build_mlff_architecture_manual.py` rebuilds the assembled MLFF architecture with no diff and does not include `70_status_and_gates.md`;
- the current assembled architecture contains none of the former developer-status sentinels (`Next gate`, `COMPLETE in 0.20.x`, or `Status and forward gates`);
- the current cross-cutting MLFF system contract contains no `# Stage gates` section;
- the training-data specification index contains neither `Canonical plan and current status` nor a version-history section;
- current navigation files no longer describe a dependency/status graph, module/gate contracts, or current-status/forward-gate architecture;
- `MANIFEST.in` explicitly prunes `workplans`;
- all five selected pre-DOC-GOV1 authority snapshots exist and retain the exact frozen blob identities recorded by G0;
- the current dependency graph declares `authority_model=current_dependency_architecture`, has no top-level project-status keys, contains no `implementation_requires` or `documentation_requires` edges, has valid endpoint references, and has definitions for every used edge type;
- graph nodes contain no `implementation_status`, `next_gate`, or `gate_name` fields;
- the current assembled architecture and cross-cutting system-contract Markdown/PDF/provenance triples have matching SHA-256 identities and use the `pandoc-typst-v2` renderer policy.

Result: the DOC-GOV1 authority separation is reproducibly checkable from a clean repository state. G7 may proceed to final render, distribution, installation, and closeout qualification.
