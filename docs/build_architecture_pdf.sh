#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/build/docs"
mkdir -p "${OUT}"
python3 "${ROOT}/docs/build_pdfs.py" build \
  --target docs/arch_manuals/mlff_training_data_architecture.pdf \
  --report "${OUT}/mlff_training_data_architecture.build.json"
cp "${ROOT}/docs/arch_manuals/mlff_training_data_architecture.pdf" \
   "${OUT}/mlff_training_data_architecture.pdf"
sha256sum "${OUT}/mlff_training_data_architecture.pdf" > \
  "${OUT}/mlff_training_data_architecture.pdf.sha256"
