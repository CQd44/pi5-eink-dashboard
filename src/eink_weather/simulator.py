"""Tkinter window that previews last_frame.png — the same image sent to the
e-ink hardware.  Run this on a desktop machine (or a Pi with a display) while
the main loop is running; it polls and refreshes automatically.

Usage:
    PYTHONPATH=src .venv/bin/python -c \
        "from eink_weather.simulator import main; main()"

  or via the helper script:
    bash scripts/simulate.sh
"""
from __future__ import annotations

from pathlib import Path

_FRAME_FILE = Path("last_frame.png")
_POLL_MS    = 2000   # milliseconds between file-reload checks


def main() -> None:
    try:
        import tkinter as tk
        from PIL import Image, ImageTk
    except ImportError as exc:
        raise SystemExit(
            f"Simulator needs tkinter and Pillow: {exc}\n"
            "  pip install pillow   (tkinter ships with Python on most systems)"
        ) from exc

    from .config import load_config

    cfg = load_config()
    W, H = cfg.display_width, cfg.display_height

    BEZEL = 20
    BG = "#3a3a3a"

    root = tk.Tk()
    root.title("E-Ink Simulator")
    root.resizable(False, False)
    root.configure(bg=BG)

    # Simulated display bezel
    canvas = tk.Canvas(
        root,
        width=W + BEZEL * 2,
        height=H + BEZEL * 2,
        bg=BG,
        highlightthickness=0,
    )
    canvas.pack(padx=8, pady=8)
    canvas.create_rectangle(
        BEZEL - 3, BEZEL - 3, W + BEZEL + 3, H + BEZEL + 3,
        fill="#111111", outline="#111111",
    )

    # Keep reference to avoid garbage collection
    _ref: dict = {"img": None}

    def _reload() -> None:
        if _FRAME_FILE.exists():
            try:
                from PIL import ImageOps
                from .display import _split_bwr_planes
                raw = Image.open(_FRAME_FILE).convert("RGB")
                if raw.size != (W, H):
                    raw = raw.resize((W, H), Image.LANCZOS)
                # Convert to hardware-accurate 3-color (black / red / white)
                black_p, red_p = _split_bwr_planes(raw)
                black_mask = ImageOps.invert(black_p.convert("L"))
                red_mask   = ImageOps.invert(red_p.convert("L"))
                pil = Image.new("RGB", raw.size, (255, 255, 255))
                pil.paste((0, 0, 0),   mask=black_mask)
                pil.paste((200, 0, 0), mask=red_mask)
                tk_img = ImageTk.PhotoImage(pil)
                canvas.delete("frame")
                canvas.create_image(BEZEL, BEZEL, anchor="nw", image=tk_img, tags="frame")
                _ref["img"] = tk_img
            except Exception:
                pass
        root.after(_POLL_MS, _reload)

    _reload()
    root.mainloop()
