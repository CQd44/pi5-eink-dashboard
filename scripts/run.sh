#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi

VENV_PY=".venv/bin/python"
"$VENV_PY" -m pip install --upgrade pip >/dev/null
"$VENV_PY" -m pip install -r requirements.txt

# Launch the simulator in the background so the display is always visible,
# even if the e-ink hardware isn't connected or isn't working.
if [[ -n "${DISPLAY:-}" ]]; then
    PYTHONPATH=src "$VENV_PY" -c \
        "from eink_weather.simulator import main; main()" &
    SIM_PID=$!
    trap 'kill "$SIM_PID" 2>/dev/null' EXIT
    echo "Simulator started (PID $SIM_PID) — watching last_frame.png"
fi

PYTHONPATH=src "$VENV_PY" -m eink_weather.main
