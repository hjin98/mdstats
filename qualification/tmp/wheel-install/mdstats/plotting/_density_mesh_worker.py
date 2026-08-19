"""Private fresh-process worker for one large sparse density shell."""
from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("error", type=Path)
    args = parser.parse_args()
    try:
        import cloudpickle

        from .density_sparse_mesh import prepare_sparse_density_mesh

        with args.input.open("rb") as handle:
            request = cloudpickle.load(handle)
        surface = prepare_sparse_density_mesh(
            request["field"],
            float(request["mass_fraction"]),
            **dict(request["keyword_arguments"]),
        )
        with args.output.open("wb") as handle:
            cloudpickle.dump(surface, handle, protocol=5)
        return 0
    except BaseException as error:  # pragma: no cover - executed in child
        args.error.write_text(
            json.dumps(
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "traceback": traceback.format_exc(),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
