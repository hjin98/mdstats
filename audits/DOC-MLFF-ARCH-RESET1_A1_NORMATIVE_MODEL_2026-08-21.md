# DOC-MLFF-ARCH-RESET1 A1 — single-generation normative-model review

**Status:** PASS  
**Branch:** `docs/mlff-architecture-reset`  
**Inputs:** frozen workplan target architecture + A0 authority map  
**Changed normative surfaces:** `80_ownership_and_decisions.md`, `mlff_training_data_dependency_graph.json`

## Review result

A1 freezes one present-tense ownership/dependency model before the wider architecture rewrite.

### Single-owner decisions

- DATA7 owns fitted selection inputs, never target membership.
- FEAS1 owns full-pool feasibility evidence.
- MVIDX1 owns the exact sparse neighborhood relation.
- MVSEL2 owns target ordering.
- REPAIR2 owns the one repaired master order per domain.
- MVSTATE2 owns reconstructible continuation state.
- MVQUAL owns independent hard qualification evidence.
- `TargetSizeStudyPolicy` owns scientific target size.
- `OnlineTargetMonitorPolicy` and `ReplayMonitorPolicy` own monitor families independently of target size.
- DATA5 owns evidence roles/training domains; actual selected members inside a domain are MVSEL2/REPAIR2 products.
- training/checkpoint specifications own checkpoint policy after target size freezes.
- held-out CV evaluates the frozen protocol and cannot choose target size.

### Size semantics

The architecture now distinguishes `N_available`, fixed nominal population `N0`, common materializable population `NM`, qualified population `Q`, and the protocol-global `N_selected`. Domain-local membership is `D[d,N] = pi_d[:N]` over one repaired order per domain.

### Legacy-state decision

There is no current dependency path through MVSEL1, REPAIR1, MVSTATE-REUSE1, MVMIGRATE, ADAPT-MIGRATE, or generated-size rescue. An old artifact is either compatible with the current generation or unsupported and must be re-prepared.

### Statistical review

The global-size/fold-local-membership model preserves the intended CV independence boundary because held-out fold evidence enters only after size/protocol freeze. The size experiment uses development/model-selection evidence and common monitors, not held-out or locked-test evidence.

### Resource/complexity review

The fixed eight-rung scientific population is represented by one sparse authority and one repaired master order per domain plus prefix metadata/qualification evidence. This prevents the scientific ladder from implying eight descriptor, graph, selector-state, or dataset replicas. Runtime chunking/out-of-core/caching choices remain non-semantic.

## Acceptance

- **PASS:** every material scientific decision in A1 has one current owner.
- **PASS:** the dependency graph contains no alternate legacy/migration path.
- **PASS:** superseded campaigns have two states only: current-generation compatible or unsupported.
- **PASS:** available/materializable/qualified/selected size concepts and domain-local/protocol-global semantics are explicit.

A2 may proceed.
