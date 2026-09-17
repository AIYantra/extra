#!/usr/bin/env bash
# Helper script to prepare and release the Homebrew Tap formula for Extra

set -euo pipefail

VERSION="${1:-0.2.4}"
TARBALL_URL="https://github.com/AIYantra/extra/archive/refs/tags/v${VERSION}.tar.gz"
FORMULA_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/Formula/extra.rb"

echo "==> Preparing Homebrew formula for Extra v${VERSION}"

# Download tarball to compute SHA256 if curl is available
TEMP_FILE="$(mktemp)"
if curl -sSL -f "${TARBALL_URL}" -o "${TEMP_FILE}" 2>/dev/null; then
    SHA256=$(shasum -a 256 "${TEMP_FILE}" | awk '{print $1}')
    echo "==> Computed SHA256: ${SHA256}"
    sed -i.bak "s/REPLACE_WITH_ACTUAL_SHA256/${SHA256}/g" "${FORMULA_PATH}"
    rm -f "${FORMULA_PATH}.bak"
else
    echo "==> Note: Release tarball not yet published online at ${TARBALL_URL}."
    echo "    Replace REPLACE_WITH_ACTUAL_SHA256 once release tag is created."
fi
rm -f "${TEMP_FILE}"

echo "==> Formula ready at: ${FORMULA_PATH}"
echo "==> To test locally on macOS:"
echo "    brew install --build-from-source ${FORMULA_PATH}"
