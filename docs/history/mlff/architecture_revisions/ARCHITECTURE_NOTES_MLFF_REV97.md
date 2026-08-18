# MLFF architecture revision 97 - MVKERNEL1

Revision 97 completes the exact-equivalence `MVKERNEL1` performance gate.

- Introduces shared canonical ragged-CSR gather kernels for MVSEL/MVQUAL/MVIDX telemetry.
- Fuses duplicate MVSEL family/domain edge gathering while preserving independent ordered FP64 scatter operations.
- Vectorizes witness arithmetic and selected-subset `bincount` telemetry.
- Maintains required hard-obligation pending state incrementally without changing sequential rank authority.
- Retains scalar MVSEL and MVQUAL telemetry references for exact qualification.
- Leaves independent TARGET-DATA2B MVQUAL rescoring unchanged.
- Advances the optimization program to `REPAIR-PAR1`.
