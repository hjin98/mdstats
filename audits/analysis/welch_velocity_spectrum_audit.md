# VS2 Direct Welch Velocity-Spectrum Audit

Release target: `mdstats 0.19.7a0`

## Scope

- direct trajectory-to-spectrum Welch estimator;
- shared VC0 input semantics;
- N3.1 atom blocking;
- self-only component, tensor, and per-atom periodograms;
- paired module specification and roadmap synchronization.

## Attribution audit

Segment averaging over short modified periodograms is attributed to P. D.
Welch (1967), DOI `10.1109/TAU.1967.1161901`. Window and FFT implementations
are supplied by SciPy and cited accordingly. Atom selection, physical drift
semantics, weighted equal-atom aggregation, atom blocking, tensor layout,
metadata, and result validation are mdstats-specific designs.

## Validation boundary

Only focused tests requested for VS2 and direct consumers of
`VelocitySpectrumResult` are executed. No full-suite claim is made.
