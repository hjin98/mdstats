# VC0 and N3.1 Implementation Audit

Release target: `mdstats 0.19.6a0`

## Scope

- private shared velocity-input preparation;
- VACF behavioral refactor;
- atom-block direct-spectrum memory planning;
- paired specifications and roadmap synchronization.

## Attribution audit

No new externally borrowed mathematical algorithm is implemented in this stage. VC0 is a refactor of existing mdstats VACF semantics. N3.1 adapts `mdstats.analysis._fft.make_atom_fft_plan` and uses explicit `float64`/`complex128` byte counts plus the standard real-FFT output shape. The future Welch estimator remains separately attributable to Welch (1967).

## Validation boundary

Only focused tests requested for this stage were run. No claim is made that the complete package regression tree was executed.
