"""Shared bounded real-MACE model factory for focused MLFF tests.

The factory builds a genuinely small MACE 0.3.x model rather than a mock, so
tests that need real model/graph/execution semantics can run in bounded CPU
time. It was extracted from the retired G6/G7/G9 requalification suite when P6
removed that suite's retired-topology contract; the factory itself is neutral
current test machinery.
"""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("e3nn")
pytest.importorskip("mace")

from e3nn import o3
from mace import modules, tools


def _tiny_mace(
    *,
    r_max: float = 4.0,
    num_bessel: int = 4,
    num_polynomial_cutoff: int = 3,
    interaction_cls_name: str = "RealAgnosticResidualInteractionBlock",
    num_interactions: int = 2,
    correlation: int = 2,
    atomic_numbers: tuple[int, ...] = (1, 8),
    heads: list[str] | None = None,
    seed: int = 0,
    scale: float = 1.0,
    shift: float = 0.0,
    atomic_energies: tuple[float, ...] | None = None,
    dtype: torch.dtype = torch.float64,
):
    previous = torch.get_default_dtype()
    torch.set_default_dtype(dtype)
    torch.manual_seed(seed)
    try:
        table = tools.AtomicNumberTable(list(atomic_numbers))
        kwargs = dict(
            r_max=r_max,
            num_bessel=num_bessel,
            num_polynomial_cutoff=num_polynomial_cutoff,
            max_ell=1,
            interaction_cls=modules.interaction_classes[interaction_cls_name],
            interaction_cls_first=modules.interaction_classes[interaction_cls_name],
            num_interactions=num_interactions,
            num_elements=len(atomic_numbers),
            hidden_irreps=o3.Irreps("8x0e + 8x1o"),
            MLP_irreps=o3.Irreps("4x0e"),
            gate=torch.nn.functional.silu,
            atomic_energies=np.array(
                atomic_energies if atomic_energies is not None else [0.0] * len(atomic_numbers)
            ),
            avg_num_neighbors=2.0,
            atomic_numbers=table.zs,
            correlation=correlation,
            atomic_inter_scale=scale,
            atomic_inter_shift=shift,
        )
        if heads is not None:
            kwargs["heads"] = heads
        model = modules.ScaleShiftMACE(**kwargs)
    finally:
        torch.set_default_dtype(previous)
    return model.to(dtype=dtype)

