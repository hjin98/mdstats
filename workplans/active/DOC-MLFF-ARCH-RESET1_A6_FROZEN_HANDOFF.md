---
kind: architecture-documentation-handoff
workplan_id: DOC-MLFF-ARCH-RESET1
status: FROZEN_HANDOFF
protocol_version: 5.2.0
---

# DOC-MLFF-ARCH-RESET1 A6 — frozen handoff record

## Purpose

This document records completion of the documentation authority reset transition. It does not modify product behavior or establish new implementation requirements.

## Completed gates

### A5 — publication chain

Status: PASS

Completed:

- canonical Markdown remains the editable authority;
- assembled Markdown and PDF remain derived products;
- documentation build is reproducible through GitHub Actions;
- documentation toolchain is pinned through `mace-dependencies`;
- generated PDF artifact and checksum provenance are produced by CI;
- publication artifact was inspected for rendering and authority leakage.

## Frozen authority model

Current ownership:

- architecture documents own durable structure, scientific concepts, and invariants;
- specifications own exact schemas, numerical rules, policies, and failure semantics;
- methods/theory documents explain rationale without creating competing contracts;
- guides/runbooks provide task-oriented usage;
- history records superseded designs and chronology only;
- evidence artifacts provide validation evidence only.

## Superseded design handling

The following are not current execution authorities:

- MVSEL1
- REPAIR1
- MVSTATE-REUSE1
- migration-era compatibility paths
- generated-size rescue mechanisms
- FINAL-GPU1 campaign authority

Historical references remain acceptable only when they explain design evolution or preserve reproducibility context.

## Source chain

The canonical architecture source remains the chapter-based Markdown hierarchy under:

`docs/arch_manuals/mlff_training_data/`

The assembled Markdown, PDF, and publication metadata are generated artifacts and must not be edited independently.

## Transition complete

Future changes require a new design decision or implementation workplan. This reset workplan is no longer a source of current architectural exceptions.
