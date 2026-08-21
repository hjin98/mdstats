# TARGET-DATA2C MVSEL2 HARDEN1 v3 runtime clarification

**Release candidate:** `mdstats 0.20.242a0`  
**Governing chain specification:** `mlff_target_data2c_mvsel2_forward_lazy_chain_spec.md`  
**Governing workplan:** `DOC-MVSEL2-HARDEN1-V3` revision 1  
**Status:** candidate runtime contract; acceptance remains qualification/verification-owned

This specification is a narrow normative clarification of the existing
MVSEL2/MVSTATE2/REPAIR2 forward-lazy chain.  It does not change selector or
repair scientific semantics, MVIDX1 scientific identity, target sizes,
coverage thresholds, or legacy v1 readability.

## Native forward-only campaign boundary

Production MVSEL2 and REPAIR2 runtime construction obtains its MVIDX1 execution
view from the authenticated native forward-only record.  The v2 selection and
repair execution boundary does not require mapping the MVIDX1 witness-to-
candidate inverse arrays.  Independent qualification and legacy consumers may
open the complete MVIDX1 authority outside that measured boundary.

## Interrupted MVSEL2 continuation

When a complete `target_multi_view_selection_v2` authority is absent, campaign
selection searches authorized MVSTATE2 rung checkpoints from highest compatible
materializable rank downward.  A checkpoint must pass its existing lineage,
manifest, array, selected-prefix, and policy validation before use.  A corrupt,
stale, truncated, or incompatible newest checkpoint is skipped in favor of the
next earlier compatible checkpoint; if none is valid, selection rebuilds from
rank zero.

Historical `TargetMultiViewSelectionEntry` and rung evidence preceding the
restored rank is reconstructed only by replaying the already-selected
candidate prefix through forward rows.  Historical candidate choice is not
rerun.  The authenticated stored FP64 continuation values are retained after
structural replay validation so a restart does not create last-bit tie drift.
If continuation begins in Phase B, the lazy frontier is rebuilt by one exact
deterministic rebase before further candidate choice.

Resumed and uninterrupted execution must produce identical complete entries,
rungs, master order, and content digest under the same semantic inputs.

## Selector-to-REPAIR2 state reuse

At a materializable repair boundary, REPAIR2 may restore the corresponding
compatible MVSTATE2 pure-selector state while the repair order is still equal
to the selector order.  Missing or invalid state falls back to selected-prefix
forward replay only.

After the first accepted repair swap, later pure-selector checkpoints are no
longer eligible.  The exact repaired mutable state is carried forward through
subsequent rungs.  A later pure-selector checkpoint must never be reconciled
with a diverged repaired order to synthesize repair state.

Execution telemetry distinguishes at least:

- `mvstate2` / authenticated checkpoint restoration;
- `selected_prefix_forward_replay` / exact fallback reconstruction;
- `post_divergence_carried_state` / repaired-state continuation.

## Exact no-copy REPAIR2 proposal evaluation

A rejected REPAIR2 proposal does not clone or mutate the complete
`TargetMultiViewForwardStateV2`.  The frozen zero-unique and hard-safe removal
admission invariants allow exact pair-specific hypothetical scoring from the
current state with bounded reusable scratch:

1. removed-row witnesses are marked with epoch/stamp scratch;
2. hard and coverage replacement frontiers are evaluated from forward rows;
3. correlation balance is corrected for the hypothetical removal;
4. representative gain uses the exact shared-witness multiplicity correction;
5. diversity uses the same hypothetical multiplicity correction;
6. the frozen repair objective and tie hierarchy choose the winner;
7. only the accepted winner mutates authoritative state, exactly once for the
   deselection and once for the replacement selection, with the replacement
   score recomputed in the actual post-removal state.

Reusable proposal scratch is execution-only and does not enter scientific
identity.  Complete accepted swap records and terminal repaired order remain
required to equal REPAIR1 on shared oracle fixtures.

## Production-scale qualification boundary

Current acceptance requires default-policy REPAIR2 evidence for every
materializable fixed-eight rung through 16,384 on the production
36,408-candidate / 165-family graph.  Evidence records per-rung wall time,
proposal count and shortlist limit, swap count, state restore/replay mode,
RSS/peak RSS, no full-state proposal clones, and forward-only/inverse-array
status.  The campaign integration path remains bounded by `StageResourceScope`.

The selector + checkpoint/resume + repair chain must retain the governing
same-host at-least-10x performance floor versus the frozen MVSEL1 baseline or
projection.  Missing production input/environment evidence is `BLOCKED`, not a
PASS.  GPU qualification remains `DEFERRED_NOT_RUN` unless actually executed.
