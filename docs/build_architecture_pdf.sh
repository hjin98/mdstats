#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/build/docs"
mkdir -p "${OUT}"

# Canonical architecture source assembly is repository-specific.
# Keep this wrapper stable; update only the source assembly command when
# architecture chapters change.
SOURCE="${ROOT}/docs/arch_manuals/mlff_training_data_architecture.md"

if [[ ! -f "${SOURCE}" ]]; then
  echo "Missing canonical architecture source: ${SOURCE}" >&2
  exit 1
fi

pandoc "${SOURCE}" \
  -o "${OUT}/mlff_training_data_architecture.pdf" \
  --pdf-engine=typst

sha256sum "${OUT}/mlff_training_data_architecture.pdf" > "${OUT}/mlff_training_data_architecture.pdf.sha256"
