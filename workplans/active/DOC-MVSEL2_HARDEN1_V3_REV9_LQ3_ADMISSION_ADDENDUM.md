---
kind: qualification-addendum
handoff: DOC-MVSEL2-HARDEN1-V3-REV9-NO-PREEXISTING-STATE
protocol_version: 3.1.0
plan_revision: 9
status: ACTIVE
---

# REV9 LQ3 optional-rung admission correction

## Evidence prompting this addendum

Target run `20260819-182539-22927` reached the real current-candidate qualification path and produced:

- G5 reused PASS;
- LQ1 PASS on the authenticated 36,408-candidate / 165-family / 9,505,021,522-edge production graph;
- LQ2 exact qualification-owned MVSTATE2 128->256 fallback/replay equivalence PASS;
- LQ3 measured REPAIR2 at 128, 256, and 512 with `proposal_full_state_copies=0`, `inverse_mutation=false`, and no accepted swaps;
- proposal counts were zero at all three measured rungs, so no proposal-cost normalization was available;
- peak owned RSS was 38,811,086,848 bytes (~36.15 GiB), below the run's hard RSS ceiling;
- production DB/config identity was unchanged.

The run stopped before optional 1024 even though the 512 REPAIR2 measurement itself cost only ~1.30 s.

## Root cause

The REV9 optional-rung admission code used a hard-coded `1.0 s/rank` floor in the Phase-B continuation estimate.  From 512 to 1024 this alone implied:

`1.5 * 512 * 1.0 s = 768 s`

which makes 1024 impossible to admit inside the frozen 585 s operating window regardless of actual measured current Phase-B speed.  This contradicted the reviewed rule that 1024 is allowed as the final bounded rung when proposal/timing evidence is still insufficient.

## Corrected admission rule

Qualification-only admission now uses:

`projected_optional = 2.0 * remaining_ranks * max(observed_current_phase_b_rank_seconds) + 45 s`

and admits the optional rung only when:

`elapsed + projected_optional <= operating_window`.

Properties:

- current measured Phase-B data only;
- 2x worst-observed-rank safety multiplier;
- 45 s explicit residual reserve;
- unchanged 585 s operating window;
- unchanged 900 s hard wall and RSS/scratch containment;
- unchanged selector/REPAIR2 science;
- unchanged maximum optional rung of 1024;
- unchanged fail-closed rule: if proposal cost is still unmeasured after 1024, LQ3 remains BLOCKED and no cost is guessed.

The correction is implemented as a qualification-only fail-closed source-pinned shim in `scripts/mvsel2_rev9_optional_admission.py`; if the expected REV9 source block is absent or duplicated, qualification aborts rather than applying an ambiguous transformation.
