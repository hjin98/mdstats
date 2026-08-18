# mdstats 0.20.230a0 patch notes

- Implement MVKERNEL1 / architecture revision 97 as exact sparse-vector performance hardening.
- Add canonical vectorized ragged-CSR gathers and reuse one gathered stream for paired MVSEL family/domain gain updates.
- Vectorize coverage/representative witness arithmetic while preserving scalar-reference state after every qualified rank.
- Convert selected-subset coverage, hard-obligation counts, and MVQUAL multiplicity/unique-owner telemetry to CSR gather plus `bincount` kernels.
- Build DATA2A run/condition provenance codes once per MVQUAL domain.
- Preserve representative and 16,384-selection stress digests and full MVQUAL plan authority.
- Keep MACE-MPA-0 as the active qualification checkpoint while retaining model-generic MACE-MH-1 compatibility.
- Next optimization gate is REPAIR-PAR1.
