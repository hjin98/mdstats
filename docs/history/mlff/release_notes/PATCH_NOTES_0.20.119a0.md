# mdstats 0.20.119a0 patch notes

## PAR-DENS architecture plan

This release records the next long-trajectory density implementation sequence in the normative dynamical-framework/density architecture manual. It does **not** implement the new runtime behavior yet.

Ordered gates:

1. `PAR-DENS0` - basin-aware, convergence-qualified vibrational spread estimation;
2. `PAR-DENS1` - execution-faithful direct/FFT cost calibration;
3. `PAR-DENS2` - one global 90%-CPU / 80%-host-memory density scheduler;
4. `PAR-DENS3` - parallel density planning and realization;
5. `PAR-DENS4` - parallel trajectory preprocessing and geometry reuse;
6. `PAR-DENS5` - optional GPU density execution under an 80%-available-VRAM safeguard;
7. `PAR-DENS6` - end-to-end qualification and auto-tuning.

The plan reuses existing Stage-11E and explicit site-assignment basin/transition semantics, excludes passage motion from adaptive vibrational SD, and records the 10,001-frame Na-LTA convergence evidence discussed during design. It explicitly forbids speedups obtained by silently coarsening the scientific grid, broadening the Gaussian, weakening precision, or reinstating wall-time as a hard density feasibility bound.
