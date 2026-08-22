# DOC-MLFF-ARCH-RESET1 A4 — historical consolidation review

**Status:** PASS  
**Branch:** `docs/mlff-architecture-reset`  
**Architecture:** revision 105

## Consolidated design history

A4 preserves durable rationale in three concept-oriented, explicitly non-normative records:

1. `docs/history/mlff/selector_repair_evolution.md`
2. `docs/history/mlff/target_size_evolution.md`
3. `docs/history/mlff/campaign_compatibility_evolution.md`

The history index now identifies the canonical current architecture as the numbered chapter source set, not a historical assembled/single-file authority.

## Removed superseded current-spec surfaces

The following obsolete semantic families were removed from the current specification tree rather than preserved one file per gate:

- MVSEL1 progressive selector;
- REPAIR1 deficit-exchange authority;
- MVSTATE-REUSE1 selector/repair state handoff;
- MVMIGRATE generated-policy migration;
- generated upper rescue ladder;
- adaptive campaign migration;
- ML-CV migration;
- material-profile extension migration;
- first target-size revision / SIZE-HALVE1;
- superseded SIZE-HALVE2 gate document after its durable rules moved to the single target-size-study specification;
- SIZE-FIDELITY1 and SIZE-FIDELITY2 gate specifications after their durable screening/qualification rules were consolidated;
- MVPLAN1/MVPLAN2 roadmap specifications after their useful multi-view design rationale was absorbed by current architecture/history;
- directly paired obsolete generated PDFs for the removed documents where present.

Git history remains the exact recovery mechanism for deleted obsolete schemas unless a durable release/audit artifact later proves that an exact historical snapshot is necessary.

## Retention rule applied

Not every gate-shaped or performance-era file was deleted merely because its name contains chronology. A file is retained when it may still encode current narrow runtime behavior or product evidence not yet proven redundant. Such a retained file is not automatically current authority: only entries explicitly listed by `docs/specs/training_data/README.md` are current normative specifications.

A5 stale-marker/source-chain review is responsible for detecting any retained file or link that accidentally reintroduces obsolete current semantics.

## Navigation review

- `docs/specs/training_data/README.md` is current-only and points readers to present-tense conceptual owners.
- `docs/history/mlff/README.md` is non-normative and points to current canonical source directories plus consolidated history.
- no current architecture chapter requires a historical file to determine present behavior.

## Acceptance

- **PASS:** useful selector/repair, size-policy, and compatibility lessons remain discoverable.
- **PASS:** history is visibly non-normative and does not define fallback product semantics.
- **PASS:** obsolete semantic generations are not preserved one file per gate for completeness.
- **PASS:** current navigation determines present behavior without consulting history.

A5 may proceed.
