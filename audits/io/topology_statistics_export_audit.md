# Topology Statistics Export Audit

Release: `mdstats 0.17.0a5`

Scope:

- `mdstats/io/topology_statistics.py`;
- `docs/specs/io/topology_statistics_spec.{md,pdf}`;
- public exports through `mdstats.io` and `mdstats`.

Validated behavior:

- deterministic table names and column order;
- exact JSON output from the authoritative TS1, TS2, or TS4 `to_dict()` payload;
- JSON restoration preserves the source result digest;
- long-form CSV tables contain exact PMF frequencies/probabilities and frame series;
- framework edge keys remain lossless canonical JSON cells;
- combined exports include atomic, framework, contingency, and boundary tables;
- optional temporal tables appear only when TS3 results are present;
- UTF-8 CSV uses standard-library `csv` and deterministic line endings;
- existing files are protected unless `overwrite=True`;
- no pandas dependency and no graph/statistics recomputation.

The Na-LTA example produced one canonical JSON payload and 23 deterministic CSV tables.

Validation:

- focused table/export tests passed;
- JSON digest round trip passed;
- overwrite guard and explicit overwrite passed;
- export specification PDF preflight and rendered-page inspection passed.
