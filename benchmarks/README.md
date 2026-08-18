# Benchmarks

Each benchmark family uses one semantic stem across its script, raw data, and narrative output:

```text
<topic>_benchmark.py
<topic>_benchmark.json
<topic>_benchmark.md
```

Timings are machine-specific. Correctness comparisons and validation conclusions are documented separately under `audits/`.

Density architecture evidence additionally uses:

```text
density_ld8_p0_benchmark.py          # production-cutoff planning and optional LD7 baseline
density_ld8_s2_direct_benchmark.py   # bounded exact S2 oracle versus LD1-A
density_browser_validation.py        # Chromium/WebGL smoke evidence
density_ld9_v0_calibration.py        # raw-scene hard-budget calibration
```

The browser and calibration scripts record failed environment or budget gates as structured JSON evidence; a generated report must not be interpreted as a passing result without checking its `status` or `passed` field.
