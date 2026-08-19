# DOC-MVSEL2 Repository Handoff State

This file records the current coordination state for the MVSEL2 branch. It is not scientific authority.

## Current handoff

- Active hardening workplan: `workplans/active/DOC-MVSEL2_HARDEN1.md`
- Workplan ID/revision: `DOC-MVSEL2-HARDEN1` / `1`
- Workplan SHA-256 at handoff: `ab9eb69673f3d6ea255f9d71c9d4b4b1ce1f1e8560e232a8add9d42b0e13e9ee`
- Review protocol: `software-design-review` protocol `2.0.1`
- Reviewed implementation base: `feat/mvsel2-forward-lazy` at `e24d5168ce01bf2d773339e1a91d5ded4871a57f`
- Original implementation workplan: `workplans/archive/DOC-MVSEL2_forward_lazy_selector.md` revision 4
- Implementation branch: `feat/mvsel2-forward-lazy`
- Gate approval: `AUTO`
- Merge status: **DO NOT MERGE** until hardening H0-H6 pass.

## Review outcome

The post-implementation review accepted the core MVSEL2 Phase-A/Phase-B forward/lazy selector design but found merge-blocking conformance gaps in the surrounding G5/G7/G8 integration:

1. REPAIR2 defaults/policy and complete durable trace do not yet prove exact REPAIR1 semantic equivalence.
2. Campaign MVSEL2/REPAIR2 currently project an already materialized full MVIDX1 object instead of consuming the native forward-only reader end-to-end.
3. MVSTATE2 checkpoints are written, but interrupted campaign selection does not resume from them.
4. REPAIR2 replays selector prefixes instead of consuming MVSTATE2 at the selector-to-repair boundary.
5. REPAIR2 currently copies full forward state per proposal and has only 128/256 zero-swap production scaling evidence.
6. Final qualification is not yet bound cleanly to the corrected code-under-test SHA, and the prior full non-slow suite was blocked at collection.

These are narrow hardening/integration defects. The selector scientific policy, Phase-A algorithm, Phase-B certification design, target sizes, coverage threshold, and MVIDX1 scientific identity are frozen and must not be redesigned under this handoff.

## Implementation instruction

Codex continues on `feat/mvsel2-forward-lazy` and follows `DOC-MVSEL2-HARDEN1` starting at **H0 REVIEW-BASELINE**.

Hardening gates are:

```text
H0 REVIEW-BASELINE
 -> H1 REPAIR2-SEM1
 -> H2 MVIDX-FWD-RUNTIME1
 -> H3 MVSTATE2-RESUME1
 -> H4 REPAIR2-SCALE1
 -> H5 QUAL-HARDEN1
 -> H6 CLOSEOUT-HARDEN1
```

After objective PASS, record evidence and continue automatically. Stop on persistent FAIL, BLOCKED, `STALE_WORKPLAN`, `DESIGN_REVISION_REQUIRED`, an irreversible/external action requiring approval, or a genuinely unresolved user decision.

Do not rewrite the archived revision-4 workplan to conceal the failed review. The hardening workplan is the active transition authority; permanent architecture/specification edits occur only after the corresponding corrected implementation is accepted.
