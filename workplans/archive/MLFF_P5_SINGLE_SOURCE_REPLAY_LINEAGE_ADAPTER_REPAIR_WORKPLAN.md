---
kind: superseded-workplan-record
workplan_id: CODE-MLFF-P5-SINGLE-SOURCE-REPLAY-LINEAGE-ADAPTER-REPAIR
protocol_version: 5.8.0
status: completed-and-superseded
created_date: 2026-09-08
completed_date: 2026-09-08
baseline_commit: d6f5338b21a792420bf363fc858be8d4a39a5f71
implementation_commit: 0dcb43611409b540b85089912761ffc0394f166c
implementation_branch: fix/mlff-p5-single-source-replay-lineage-adapter
superseded_by: workplans/active/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md
---

# Retired MLFF P5 single-source replay-lineage adapter repair

This bounded repair is complete and no longer defines the current implementation handoff.

The implementation at `0dcb43611409b540b85089912761ffc0394f166c` corrected the P5 single-source replay adapter so `campaign_post_selection_runtime._resolve_post_selection_replay_resolution()` consumes the canonical runtime-context `source` and `split` artifacts rather than persistence-record names at the wrong nesting level. The repair preserves fail-closed `compute_replay_lineage_digest()` semantics and added real producer -> adapter -> lineage coverage for TRUE_DFT and foundation-pseudolabel replay, restart stability, mutation invalidation, and bounded multi-size admission.

The subsequent downstream integration review found broader, independent nonconformances in foundation/configured-path ownership, P5 locator/execution/restart integration, multi-size CV completion, P7 reference-root resolution, and current architecture documentation. Those findings are consolidated into:

`workplans/active/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md`

That workplan is snapshot-complete for the next implementation round and incorporates the still-binding preservation requirement that the completed replay-lineage repair must not regress.

The original full active-plan text remains available in Git history at commit `8dab3701932545c8f6106ce440263ed9f11ae37b`; it is historical coordination, not current authority.
