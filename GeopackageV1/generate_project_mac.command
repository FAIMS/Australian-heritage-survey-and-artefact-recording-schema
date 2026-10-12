#!/bin/bash
# ==============================================================================
# Australian Heritage Survey - Project Generator (macOS Launcher)
# Double-click this file in Finder to generate your GeoPackage and QGIS project
# ==============================================================================

cd "$(dirname "$0")"

echo "============================================================================"
echo "  AUSTRALIAN HERITAGE SURVEY & ARTEFACT RECORDING (GeoPackage V0.2)"
echo "  Project Setup Generator for macOS"
echo "============================================================================"
echo ""

if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "[ERROR] Python 3 was not found on your system."
    echo "macOS usually includes Python 3 via Xcode Command Line Tools."
    echo "To install, open Terminal and type: xcode-select --install"
    echo ""
    read -n 1 -s -r -p "Press any key to close this window..."
    exit 1
fi

"$PY_CMD" generate_geopackage.py

echo ""
echo "============================================================================"
echo "Setup process finished. Press any key to close this window."
echo "============================================================================"
read -n 1 -s -r -p ""
