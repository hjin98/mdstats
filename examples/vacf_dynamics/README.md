# VACF-derived VDOS and running diffusion example

`vasp_contcar_trajectory_vdos_diffusion.py` reads the custom watcher-generated
VASP `TRAJECTORY` format, verifies that its velocities are native, and writes
separate VDOS and running Green-Kubo diffusion figures.

For the supplied Na-LTA trajectory:

```bash
python examples/vacf_dynamics/vasp_contcar_trajectory_vdos_diffusion.py \
    TRAJECTORY \
    --timestep-fs 1.0 \
    --diffusion-species Na \
    --output-dir vacf_outputs
```

Outputs:

```text
vacf_outputs/vdos.png
vacf_outputs/vdos.pdf
vacf_outputs/vdos.csv
vacf_outputs/diffusion_running.png
vacf_outputs/diffusion_running.pdf
vacf_outputs/diffusion_running.csv
```

The VDOS branch uses a mass-weighted VACF, biased finite-record correlation
weighting, and a centered half-Hann lag taper. The diffusion branch uses an
equally weighted self VACF, because mass weighting is not a physical
self-diffusion integrand.

The plotted `D(t)` is a finite-time running integral. Its final sample is not
silently interpreted as a converged diffusion coefficient.
