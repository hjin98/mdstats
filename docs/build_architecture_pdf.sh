#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/build/docs"
mkdir -p "${OUT}"

# Canonical architecture source assembly is generated from the chapter set
# under docs/arch_manuals/mlff_training_data/ by the architecture assembler.
# The assembled Markdown is a derived publication input and must not be
# edited independently.
SOURCE="${ROOT}/docs/arch_manuals/mlff_training_data_architecture.md"

if [[ ! -f "${SOURCE}" ]]; then
  echo "Missing canonical architecture source: ${SOURCE}" >&2
  exit 1
fi

pandoc "${SOURCE}" \
  -o "${OUT}/mlff_training_data_architecture.pdf" \
  --pdf-engine=typst

sha256sum "${OUT}/mlff_training_data_architecture.pdf" > "${OUT}/mlff_training_data_architecture.pdf.sha256"
