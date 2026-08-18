# Na-LTA corrected primitive-ring example

This example loads the uniform framework topology extracted from the 2,000-frame
300 K Na-LTA trajectory and compares the two Stage-4 ring families through size
eight:

- `SHORTEST_PATH_PAIRS -> PRIMITIVE_NO_SHORTCUT`;
- `REMOVED_EDGE_SHORTEST -> EDGE_SHORTEST_SUBSET`.

Run from an installed `mdstats 0.18.1a0` environment:

```bash
python generate_catalog.py
```

The generated directory contains the v2 primitive catalog, the explicitly
labeled compatibility subset catalog, ring and source-search tables, and a
compact report. The expected topological counts are:

```text
primitive/no-shortcut: 36 x 4R + 40 x 6R + 6 x 8R
edge-shortest subset:   36 x 4R + 16 x 6R
```

These counts are not yet conventional ring-site classifications. Geometry and
cage/portal inference remain downstream.
