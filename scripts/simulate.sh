#!/usr/bin/env bash
# Launch the Tkinter e-ink simulator.
# Run this on any machine that has a display (Pi with monitor, or your laptop).
# It polls last_frame.png (written by the main loop) and refreshes every 2 s.
#
# Usage:  bash scripts/simulate.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

VENV_PY=".venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
    echo "ERROR: venv not found. Run scripts/run.sh first to create it." >&2
    exit 1
fi

echo "Starting e-ink simulator — watching last_frame.png …"
PYTHONPATH=src "$VENV_PY" -c "from eink_weather.simulator import main; main()"
