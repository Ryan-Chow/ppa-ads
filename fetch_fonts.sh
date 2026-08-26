#!/usr/bin/env bash
# Fonts used by generate_cards.py, pulled from the google/fonts repo (OFL).
set -euo pipefail
mkdir -p fonts
base="https://raw.githubusercontent.com/google/fonts/main"
curl -sSLo "fonts/InstrumentSerif-Regular.ttf" "$base/ofl/instrumentserif/InstrumentSerif-Regular.ttf"
curl -sSLo "fonts/InstrumentSerif-Italic.ttf"  "$base/ofl/instrumentserif/InstrumentSerif-Italic.ttf"
curl -sSLo "fonts/Inter[opsz,wght].ttf"        "$base/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf"
echo "fonts ready"
