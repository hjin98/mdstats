#!/usr/bin/env python3
"""Compute and plot a VACF-derived VDOS and running diffusion coefficient.

This example is designed for the custom watcher-generated VASP ``TRAJECTORY``
format documented by mdstats.  It deliberately uses the native Cartesian
velocities stored in every concatenated CONTCAR record; no finite-difference
velocity reconstruction is allowed by this reader.

The two outputs use different physically appropriate VACFs:

* VDOS: mass-weighted VACF, biased finite-record weighting, and a centered
  half-Hann lag taper before the Fourier transform.
* D(t): uniformly weighted self VACF integrated with the Green-Kubo relation.

The final sample of D(t) is a finite-time running integral, not automatically a
converged diffusion coefficient.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from mdstats import (
    compute_vacf,
    compute_vacf_spectrum,
    compute_vdos,
    integrate_vacf_to_diffusion,
    plot_vacf_diffusion,
    plot_velocity_spectrum,
    read_vasp_frames,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read a watcher-generated VASP TRAJECTORY, compute a VACF-derived "
            "VDOS and running Green-Kubo diffusion curve, and save separate figures."
        )
    )
    parser.add_argument("trajectory", type=Path, help="Path to the TRAJECTORY file.")
    parser.add_argument(
        "--timestep-fs",
        type=float,
        required=True,
        help="Physical time between adjacent concatenated CONTCAR records, in fs.",
    )
    parser.add_argument(
        "--vdos-species",
        nargs="+",
        default=None,
        help="Species included in the VDOS. Omit to include all atoms.",
    )
    parser.add_argument(
        "--diffusion-species",
        nargs="+",
        default=["Na"],
        help="Species used for D(t). Default: Na.",
    )
    parser.add_argument(
        "--max-lag",
        type=int,
        default=None,
        help="Largest saved-frame VACF lag. Default: half the trajectory length.",
    )
    parser.add_argument(
        "--drift-mode",
        choices=["center_of_mass", "center_of_geometry", "none"],
        default="center_of_mass",
        help="Framewise translational-drift correction. Default: center_of_mass.",
    )
    parser.add_argument(
        "--vdos-x-axis",
        choices=["thz", "cm^-1", "mev"],
        default="thz",
        help="Horizontal axis for the VDOS figure. Default: thz.",
    )
    parser.add_argument(
        "--vdos-components",
        action="store_true",
        help="Plot x/y/z VDOS components instead of the total VDOS.",
    )
    parser.add_argument(
        "--vdos-xmax",
        type=float,
        default=None,
        help=(
            "Optional upper VDOS-axis limit in the selected x-axis unit. "
            "By default the example displays the region containing 99.5%% "
            "of the integrated VDOS weight."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("vacf_outputs"),
        help="Output directory. Default: vacf_outputs.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=220,
        help="PNG resolution. Default: 220 dpi.",
    )
    return parser.parse_args()


def _selection_label(species: list[str] | None) -> str:
    return "all atoms" if species is None else "+".join(species)


def main() -> None:
    args = _parse_args()
    if not np.isfinite(args.timestep_fs) or args.timestep_fs <= 0.0:
        raise ValueError("--timestep-fs must be finite and strictly positive.")
    if args.max_lag is not None and args.max_lag < 0:
        raise ValueError("--max-lag must be nonnegative.")
    if args.dpi <= 0:
        raise ValueError("--dpi must be positive.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    drift_mode = None if args.drift_mode == "none" else args.drift_mode

    started = time.perf_counter()
    trajectory = read_vasp_frames(
        args.trajectory,
        format="vasp-contcar-trajectory",
        timestep_fs=args.timestep_fs,
    )
    print(
        f"Read {trajectory.n_frames} frames and {trajectory.n_atoms} atoms "
        f"in {time.perf_counter() - started:.2f} s."
    )
    print(f"Velocity source: {trajectory.provenance.velocity_source}")
    if trajectory.provenance.velocity_source != "native":
        raise RuntimeError("This example requires native per-frame velocities.")

    # VDOS branch.  Mass weighting is useful for a vibrational interpretation.
    started = time.perf_counter()
    vdos_vacf = compute_vacf(
        trajectory,
        species=args.vdos_species,
        max_lag=args.max_lag,
        weights="mass",
        drift_mode=drift_mode,
        compute_tensor=False,
        backend="fft",
    )
    vdos_spectrum = compute_vacf_spectrum(
        vdos_vacf,
        normalization="per_weight",
        correlation_weighting="biased",
        window="half_hann",
        negative_policy="preserve",
    )
    vdos = compute_vdos(
        vdos_spectrum,
        normalization="unit_area",
        negative_policy="clip_roundoff",
    )
    print(f"Computed VDOS in {time.perf_counter() - started:.2f} s.")

    vdos_projection = "components" if args.vdos_components else "total"
    fig_vdos, ax_vdos = plot_velocity_spectrum(
        vdos,
        x_axis=args.vdos_x_axis,
        projection=vdos_projection,
    )
    ax_vdos.set_title(
        f"VACF-derived VDOS ({_selection_label(args.vdos_species)})"
    )
    if args.vdos_xmax is not None:
        if not np.isfinite(args.vdos_xmax) or args.vdos_xmax <= 0.0:
            raise ValueError("--vdos-xmax must be finite and strictly positive.")
        displayed_xmax = float(args.vdos_xmax)
    else:
        cumulative_weight = np.cumsum(vdos.total, dtype=np.float64)
        threshold = 0.995 * float(cumulative_weight[-1])
        retained_index = int(np.searchsorted(cumulative_weight, threshold, side="left"))
        if args.vdos_x_axis == "thz":
            selected_axis = vdos.frequencies_thz
        elif args.vdos_x_axis == "cm^-1":
            selected_axis = vdos.wavenumbers_cm_inv
        else:
            selected_axis = vdos.energies_mev
        displayed_xmax = 1.10 * float(selected_axis[min(retained_index, selected_axis.size - 1)])
    ax_vdos.set_xlim(left=0.0, right=displayed_xmax)
    fig_vdos.tight_layout()
    vdos_png = args.output_dir / "vdos.png"
    vdos_pdf = args.output_dir / "vdos.pdf"
    fig_vdos.savefig(vdos_png, dpi=args.dpi, bbox_inches="tight")
    fig_vdos.savefig(vdos_pdf, bbox_inches="tight")
    plt.close(fig_vdos)

    np.savetxt(
        args.output_dir / "vdos.csv",
        np.column_stack(
            [
                vdos.frequencies_thz,
                vdos.wavenumbers_cm_inv,
                vdos.energies_mev,
                vdos.total,
                vdos.components,
            ]
        ),
        delimiter=",",
        header=(
            "frequency_THz,wavenumber_cm^-1,energy_meV,"
            "vdos_total_per_THz,vdos_x_per_THz,vdos_y_per_THz,vdos_z_per_THz"
        ),
        comments="",
    )

    # Diffusion branch.  Self diffusion requires equal per-particle weights.
    started = time.perf_counter()
    diffusion_vacf = compute_vacf(
        trajectory,
        species=args.diffusion_species,
        max_lag=args.max_lag,
        weights="uniform",
        drift_mode=drift_mode,
        compute_tensor=False,
        backend="fft",
    )
    running_diffusion = integrate_vacf_to_diffusion(
        diffusion_vacf,
        dimensions=3,
        component="scalar",
    )
    print(f"Computed D(t) in {time.perf_counter() - started:.2f} s.")

    diffusion_label = _selection_label(args.diffusion_species)
    fig_diffusion, ax_diffusion = plot_vacf_diffusion(
        running_diffusion,
        time_unit="ps",
        diffusion_unit="cm2/s",
        label=diffusion_label,
        title=f"Running Green-Kubo self diffusion ({diffusion_label})",
        show_zero_line=True,
    )
    fig_diffusion.tight_layout()
    diffusion_png = args.output_dir / "diffusion_running.png"
    diffusion_pdf = args.output_dir / "diffusion_running.pdf"
    fig_diffusion.savefig(diffusion_png, dpi=args.dpi, bbox_inches="tight")
    fig_diffusion.savefig(diffusion_pdf, bbox_inches="tight")
    plt.close(fig_diffusion)

    np.savetxt(
        args.output_dir / "diffusion_running.csv",
        np.column_stack(
            [
                running_diffusion.lag_times,
                running_diffusion.running_diffusion_a2_per_ps,
                running_diffusion.running_diffusion_cm2_per_s,
            ]
        ),
        delimiter=",",
        header="time_ps,D_A2_per_ps,D_cm2_per_s",
        comments="",
    )

    print(f"Saved {vdos_png}")
    print(f"Saved {vdos_pdf}")
    print(f"Saved {diffusion_png}")
    print(f"Saved {diffusion_pdf}")
    print(
        "Final sampled D(t): "
        f"{running_diffusion.running_diffusion_cm2_per_s[-1]:.8e} cm^2/s"
    )
    print(
        "Interpretation warning: the final sampled value is not automatically "
        "a converged diffusion coefficient; inspect the full D(t) curve and "
        "use an explicit plateau interval when one exists."
    )


if __name__ == "__main__":
    main()
