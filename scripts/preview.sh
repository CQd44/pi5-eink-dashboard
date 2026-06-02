#!/usr/bin/env bash
# Generate eink_preview.png — a hardware-accurate 3-color (black/white/red)
# composite that shows exactly what will appear on the Waveshare BWR panel.
#
# Run this after the dashboard has written last_frame.png at least once.
# Usage:  bash scripts/preview.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

VENV_PY=".venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
    echo "ERROR: venv not found. Run scripts/run.sh first to create it." >&2
    exit 1
fi

if [[ ! -f last_frame.png ]]; then
    echo "ERROR: last_frame.png not found. Run the dashboard (or simulate.sh) first." >&2
    exit 1
fi

PYTHONPATH=src "$VENV_PY" - <<'PY'
from PIL import Image, ImageOps
from eink_weather.display import _split_bwr_planes

raw = Image.open("last_frame.png").convert("RGB")
black_p, red_p = _split_bwr_planes(raw)

# _split_bwr_planes uses hardware convention: 0=ink, 1=white.
# Invert so non-zero = apply color (PIL paste mask convention).
black_mask = ImageOps.invert(black_p.convert("L"))
red_mask   = ImageOps.invert(red_p.convert("L"))

preview = Image.new("RGB", raw.size, (255, 255, 255))
preview.paste((0, 0, 0),   mask=black_mask)
preview.paste((200, 0, 0), mask=red_mask)
preview.save("eink_preview.png")
print("Saved eink_preview.png")
PY
