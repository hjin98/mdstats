# DOC-MVSEL2 Repository Handoff State

This file records repository preparation state for implementation workplan `DOC-MVSEL2`. It is coordination evidence, not scientific authority.

## Frozen handoff

- Canonical workplan: `workplans/active/DOC-MVSEL2_forward_lazy_selector.md`
- Workplan ID/revision: `DOC-MVSEL2` / `4`
- Review protocol: `software-design-review` protocol `2.0.1`
- Analyzed/rebased base: `main` at `1918f940debecade786b9b89c13c1bca3d787c89`
- Implementation branch: `feat/mvsel2-forward-lazy`
- Gate approval: `AUTO`
- Stop conditions: persistent FAIL, BLOCKED, `STALE_WORKPLAN`, `DESIGN_REVISION_REQUIRED`, an irreversible/external action requiring approval, or a genuinely unresolved user decision.

## Documentation-governance reconciliation

The DOC-GOV1 documentation migration is already present in the analyzed base. The former design-preparation branch was created before that migration and is intentionally not merged.

Revision 4 adapts the handoff to the migrated authority model:

- architecture manuals describe accepted current structure only;
- specifications describe accepted current behavior;
- developer transition/gate chronology lives under `workplans/`;
- completed chronology/evidence lives under `docs/history/`, `audits/`, `release/`, and `benchmarks/` as appropriate;
- the former architecture `70_status_and_gates.md` is not a current assumption path.

The implementation branch contains one small Part-V architecture clarification about the **current v1 execution-state coupling** among MVSEL1, MVSTATE-REUSE1, and REPAIR1. It does not present MVSEL2 as current behavior. All proposed MVSEL2/MVSTATE2/REPAIR2 semantics remain in the active workplan until G8 acceptance.

## Required first G0 documentation action

The MLFF assembled architecture Markdown, PDF, and provenance are generated artifacts. Before runtime implementation, Codex must run the repository's canonical architecture assembler and PDF/provenance workflow and verify that the Part-V source edit is synchronized without introducing gate chronology into normative architecture.

If the current implementation or documentation base materially disagrees with revision 4, stop `STALE_WORKPLAN` rather than silently changing scientific design.

## Implementation boundary

No MVSEL2 runtime code exists in this handoff. MVSEL1/MVSTATE-REUSE1/REPAIR1 remain current runtime authorities. Codex starts at G0 and introduces v2 separately, retaining v1 as legacy authority/oracle until the explicit G8 migration.
