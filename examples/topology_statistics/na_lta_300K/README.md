# 300 K Na-LTA Topology Statistics

This directory contains figures generated from the previously serialized 2,000-frame atomic-connectivity and framework-topology catalogs.

Expected behavior:

- Si-O and Al-O contact counts remain exactly 96;
- Na-O contact counts fluctuate between 110 and 121;
- the atomic catalog contains 72 states and 71 changed boundaries;
- the framework catalog contains one class and no transitions;
- all 96 projected framework edges have unit occupancy.

Run `generate_figures.py` with paths to the two serialized catalog JSON files.
