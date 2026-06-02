"""PIL-based weather icon primitives for e-ink rendering.

Icons are drawn using basic geometric shapes so they render cleanly
in both 1-bit (hardware) and grayscale (simulator) modes.
"""
from __future__ import annotations

import math
import random
from datetime import date as _date

from PIL import ImageDraw

# ── WMO code → icon key ───────────────────────────────────────────────────────
_ICON: dict[int, str] = {
    0: "sun",
    1: "sun",
    2: "partly_cloudy",
    3: "cloudy",
    45: "fog",
    48: "fog",
    51: "drizzle",
    53: "drizzle",
    55: "drizzle",
    56: "drizzle",
    57: "drizzle",
    61: "rain",
    63: "rain",
    65: "rain",
    66: "rain",
    67: "rain",
    71: "snow",
    73: "snow",
    75: "snow",
    77: "snow",
    80: "rain",
    81: "rain",
    82: "rain",
    85: "snow",
    86: "snow",
    95: "storm",
    96: "storm",
    97: "storm",
    98: "storm",
    99: "storm",
}

# ── WMO code → human label ────────────────────────────────────────────────────
_LABEL: dict[int, str] = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Freezing Fog",
    51: "Light Drizzle",
    53: "Drizzle",
    55: "Heavy Drizzle",
    56: "Light Freezing Drizzle",
    57: "Freezing Drizzle",
    61: "Light Rain",
    63: "Rain",
    65: "Heavy Rain",
    66: "Light Freezing Rain",
    67: "Freezing Rain",
    71: "Light Snow",
    73: "Snow",
    75: "Heavy Snow",
    77: "Snow Grains",
    80: "Light Showers",
    81: "Showers",
    82: "Heavy Showers",
    85: "Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm w/ Hail",
    97: "Heavy Thunderstorm",
    98: "Thunderstorm w/ Hail",
    99: "Heavy Thunderstorm w/ Hail",
}


def icon_type(code: int) -> str:
    """Return the icon key for a WMO weather code."""
    return _ICON.get(code, "cloudy")


def label(code: int) -> str:
    """Return a human-readable description for a WMO weather code."""
    return _LABEL.get(code, f"Code {code}")


# ── Primitive shapes ──────────────────────────────────────────────────────────

def _sun(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, col: int
) -> None:
    r = max(4, size // 4)
    lw = max(1, size // 16)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    for i in range(8):
        a = math.radians(i * 45)
        x1 = cx + int((r + 2) * math.cos(a))
        y1 = cy + int((r + 2) * math.sin(a))
        x2 = cx + int((r + 2 + lw + size // 5) * math.cos(a))
        y2 = cy + int((r + 2 + lw + size // 5) * math.sin(a))
        draw.line((x1, y1, x2, y2), fill=col, width=lw)


def _cloud(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, col: int
) -> None:
    """Three overlapping circles + lumpy bottom give a fluffy cloud silhouette."""
    r = max(4, size // 4)
    # top bumps — left, centre (tallest), right
    draw.ellipse((cx - r * 2, cy - r // 2, cx,         cy + r), fill=col)
    draw.ellipse((cx - r,     cy - r,      cx + r,     cy + r), fill=col)
    draw.ellipse((cx,         cy - r // 2, cx + r * 2, cy + r), fill=col)
    # solid body fill
    draw.rectangle((cx - r * 2, cy, cx + r * 2, cy + r), fill=col)
    # bottom bumps — four small ellipses protruding below the base line
    br = max(2, r * 2 // 5)
    for bx in (cx - r * 3 // 2, cx - r // 2, cx + r // 2, cx + r * 3 // 2):
        draw.ellipse((bx - br, cy + r - br, bx + br, cy + r + br), fill=col)


def _rain_drops(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, col: int, count: int = 3
) -> None:
    lw = max(1, size // 20)
    spacing = max(size // (count + 1), 4)
    x_start = cx - (count - 1) * spacing // 2
    for i in range(count):
        x = x_start + i * spacing
        draw.line((x, cy, x - 2, cy + max(4, size // 6)), fill=col, width=lw)


def _snow_dots(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, col: int, count: int = 3
) -> None:
    dr = max(2, size // 14)
    spacing = max(size // (count + 1), 4)
    x_start = cx - (count - 1) * spacing // 2
    for i in range(count):
        x = x_start + i * spacing
        draw.ellipse((x - dr, cy - dr, x + dr, cy + dr), fill=col)


def _lightning(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, col: int
) -> None:
    """Classic ⚡ lightning-bolt — 6-point Z-shaped polygon.

    Two outward wings (upper-right and lower-left) connected by a diagonal
    band through the middle, matching the traditional bolt silhouette.
    """
    w = max(8, int(size * 0.55))   # total width
    h = max(10, int(size * 0.72))  # total height
    mu = cy + h * 2 // 5           # y of upper kink
    ml = cy + h * 3 // 5           # y of lower kink
    pts = [
        (cx + w // 3,  cy),    # top tip    (right of centre)
        (cx + w // 2,  mu),    # right outer wing
        (cx - w // 6,  mu),    # right inner notch  (kink cuts left)
        (cx - w // 3,  cy + h),# bottom tip (left of centre)
        (cx - w // 2,  ml),    # left outer wing
        (cx + w // 6,  ml),    # left inner notch   (kink cuts right)
    ]
    draw.polygon(pts, fill=col)


# ── Public API ────────────────────────────────────────────────────────────────

def draw_icon(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    size: int,
    weather_code: int,
    color: int = 0,
    bg: int = 255,
) -> None:
    """Draw a weather icon centered at (cx, cy) within a bounding box of `size` px.

    Args:
        draw: PIL ImageDraw instance.
        cx, cy: Center pixel coordinates.
        size: Bounding-box side length in pixels (icon scales to ~80% of this).
        weather_code: WMO weather interpretation code.
        color: Foreground fill value (0 = black in "L" / "1" modes).
        bg: Background fill used for erasing overlap (255 = white).
    """
    itype = icon_type(weather_code)
    lw = max(1, size // 18)

    if itype == "sun":
        _sun(draw, cx, cy, size, color)

    elif itype == "partly_cloudy":
        # Smaller sun peeking from top-left, cloud overlapping bottom-right.
        _sun(draw, cx - size // 8, cy - size // 8, int(size * 0.70), color)
        # Erase the part of the sun where the cloud will sit (bg-colored cloud first).
        _cloud(draw, cx + size // 10, cy + size // 10, int(size * 0.65), bg)
        # Then draw the cloud outline on top.
        _cloud(draw, cx + size // 10, cy + size // 10, int(size * 0.65), color)

    elif itype == "cloudy":
        _cloud(draw, cx, cy, size, color)

    elif itype == "fog":
        lw2 = max(2, size // 10)
        for i in range(4):
            y = cy - size // 3 + i * (size // 3)
            offset = (i % 2) * (size // 8)
            x0 = cx - size // 3 + offset
            x1 = cx + size // 3
            draw.line((x0, y, x1, y), fill=color, width=lw2)

    elif itype in ("drizzle", "rain"):
        # Cloud in upper portion, drops below.
        _cloud(draw, cx, cy - size // 8, int(size * 0.72), color)
        drop_count = 2 if itype == "drizzle" else 3
        _rain_drops(draw, cx, cy + size // 5, size, color, count=drop_count)

    elif itype == "snow":
        _cloud(draw, cx, cy - size // 8, int(size * 0.72), color)
        _snow_dots(draw, cx, cy + size // 5, size, color, count=3)

    elif itype == "storm":
        _cloud(draw, cx, cy - size // 5, int(size * 0.68), color)
        _lightning(draw, cx - size // 8, cy + size // 8, int(size * 0.52), color)

    else:
        # Fallback: plain cloud.
        _cloud(draw, cx, cy, size, color)


# ── Moon phase ───────────────────────────────────────────────────────────────

def moon_phase(d: _date | None = None) -> float:
    """Return the lunar phase as a value in [0, 1).

    0.0 = new moon, 0.25 = first quarter, 0.5 = full moon, 0.75 = last quarter.
    Uses a simple Julian-day calculation accurate to within a few hours.
    """
    if d is None:
        from datetime import date as _today
        d = _today.today()
    # Julian Day Number for the given date
    y, m, day = d.year, d.month, d.day
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    jdn = day + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
    # Known new moon: 6 Jan 2000 = JDN 2451549.5  cycle = 29.53058867 days
    cycle = 29.53058867
    phase = ((jdn - 2451549.5) % cycle) / cycle
    return phase % 1.0


# ── Scenic landscape ──────────────────────────────────────────────────────────

def draw_scene(
    draw: ImageDraw.ImageDraw,
    x0: int,
    y0: int,
    w: int,
    h: int,
    weather_code: int,
    hour: int | float = 12,
    today: _date | None = None,
    sunrise_hour: float = 6.0,
    sunset_hour: float = 20.0,
    moonrise_hour: float | None = None,
    moonset_hour: float | None = None,
) -> None:
    """Draw a scenic landscape illustration filling the rect (x0,y0,w,h).

    Sky (sun/moon/stars/clouds) occupies the top ~55 %; layered hills fill
    the bottom ~45 %.  Weather effects (rain, snow, lightning, fog) are
    rendered on top.  All shapes are PIL primitives so they work in both
    grayscale-L (simulator) and 1-bit (hardware) modes.
    """
    itype    = icon_type(weather_code)
    fhour    = float(hour)
    is_night = not (sunrise_hour <= fhour < sunset_hour)
    sky_frac = 0.55                            # fraction of h dedicated to sky
    sky_h    = int(h * sky_frac)

    # ── Sky color: red dawn/dusk → white midday → black night ─────────────────
    # On BWR hardware the gradient auto-quantises: near-transition red shows as
    # red ink, midday shows as white paper, night shows as black ink.
    _GOLDEN = 1.5   # hours either side of sunrise/sunset that blush red
    if is_night:
        sky_fill = (0,   0,   0)       # black night sky
        _ink     = (255, 255, 255)     # white — stars, moon, night effects
    else:
        dist = min(abs(fhour - sunrise_hour), abs(fhour - sunset_hour))
        if dist < _GOLDEN:
            blend    = dist / _GOLDEN  # 0 = at horizon, 1 = golden edge
            sky_fill = (255, int(200 * blend), int(180 * blend))
        else:
            sky_fill = (255, 255, 255)  # white midday sky
        _ink = (0, 0, 0)               # black — standard daytime ink

    # ── Sky background ────────────────────────────────────────────────────────
    draw.rectangle((x0, y0, x0 + w, y0 + h), fill=sky_fill)

    # ── Stars (night only) ────────────────────────────────────────────────────
    if is_night:
        random.seed(42)
        for _ in range(20):
            sx = x0 + random.randint(8, w - 8)
            sy = y0 + random.randint(4, sky_h - 8)
            draw.ellipse((sx - 1, sy - 1, sx + 1, sy + 1), fill=_ink)

    # ── Sun (day, not fully overcast/foggy) ───────────────────────────────────
    if not is_night and itype not in ("cloudy", "fog"):
        day_len = max(0.5, sunset_hour - sunrise_hour)
        t      = max(0.0, min(1.0, (hour - sunrise_hour) / day_len))
        arc    = 1.0 - 4.0 * (t - 0.5) ** 2              # parabolic, 1=noon
        sun_x  = x0 + int(w * (0.10 + t * 0.80))
        sun_y  = y0 + int(sky_h * (0.88 - arc * 0.72))
        sun_r  = max(10, min(w // 10, 22))
        draw.ellipse(
            (sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r),
            fill=_ink,
        )
        if itype in ("sun", "partly_cloudy"):
            ray_len = max(5, sun_r // 2)
            lw      = max(1, sun_r // 7)
            for i in range(8):
                a  = math.radians(i * 45)
                x1 = sun_x + int((sun_r + 3) * math.cos(a))
                y1 = sun_y + int((sun_r + 3) * math.sin(a))
                x2 = sun_x + int((sun_r + 3 + ray_len) * math.cos(a))
                y2 = sun_y + int((sun_r + 3 + ray_len) * math.sin(a))
                draw.line((x1, y1, x2, y2), fill=_ink, width=lw)

            # Smiling face — features cut out of the solid disc in sky_fill color
            face_col = sky_fill
            eye_r    = max(1, sun_r // 7)
            eye_y    = sun_y - sun_r // 5
            eye_dx   = sun_r // 3
            draw.ellipse(
                (sun_x - eye_dx - eye_r, eye_y - eye_r,
                 sun_x - eye_dx + eye_r, eye_y + eye_r), fill=face_col)
            draw.ellipse(
                (sun_x + eye_dx - eye_r, eye_y - eye_r,
                 sun_x + eye_dx + eye_r, eye_y + eye_r), fill=face_col)
            smile_box = [
                sun_x - sun_r // 3, sun_y - sun_r // 8,
                sun_x + sun_r // 3, sun_y + sun_r // 3,
            ]
            draw.arc(smile_box, start=0, end=180,
                     fill=face_col, width=max(1, sun_r // 8))

            # Sunglasses — random ~1-in-3 chance, stable within the hour
            random.seed(int(fhour) * 17 + 99)
            if random.random() < 0.33:
                lg_w = max(4, sun_r // 2)
                lg_h = max(2, sun_r // 4)
                for ex in (sun_x - eye_dx, sun_x + eye_dx):
                    draw.rounded_rectangle(
                        (ex - lg_w, eye_y - lg_h, ex + lg_w, eye_y + lg_h),
                        radius=max(1, lg_h // 2), fill=face_col,
                    )
                draw.line(
                    (sun_x - eye_dx + lg_w, eye_y,
                     sun_x + eye_dx - lg_w, eye_y),
                    fill=face_col, width=max(1, sun_r // 10),
                )

    # ── Moon (night) — phase-accurate, arc-tracked ───────────────────────────
    if is_night:
        # Determine moon arc from actual moonrise/moonset if available,
        # otherwise fall back to a generic 20:00–06:00 window.
        if moonrise_hour is not None and moonset_hour is not None:
            # Handle moon arc that may cross midnight
            if moonset_hour > moonrise_hour:
                # Simple same-night case
                moon_up = moonrise_hour <= hour <= moonset_hour
                moon_dur = moonset_hour - moonrise_hour
                t_moon = (hour - moonrise_hour) / max(0.5, moon_dur)
            else:
                # Crosses midnight: moonrise PM, moonset AM next day
                moon_dur = (24.0 - moonrise_hour) + moonset_hour
                if hour >= moonrise_hour:
                    t_moon = (hour - moonrise_hour) / max(0.5, moon_dur)
                else:
                    t_moon = (24.0 - moonrise_hour + hour) / max(0.5, moon_dur)
                moon_up = hour >= moonrise_hour or hour <= moonset_hour
            t_moon = max(0.0, min(1.0, t_moon))
        else:
            # Fallback: 20:00 rise, 06:00 set
            night_hour = (hour - 20) % 24
            t_moon = max(0.0, min(1.0, night_hour / 10.0))
            moon_up = True

        if moon_up:
            arc_moon = 1.0 - 4.0 * (t_moon - 0.5) ** 2
            mx  = x0 + int(w * (0.10 + t_moon * 0.80))
            my  = y0 + int(sky_h * (0.88 - arc_moon * 0.72))
            mr  = max(8, w // 18)
            phase = moon_phase(today)

            if phase < 0.03 or phase > 0.97:
                # New moon — faint ring only
                draw.ellipse((mx - mr, my - mr, mx + mr, my + mr), outline=_ink, width=1)
            elif phase <= 0.50:
                # Waxing: lit right, shadow bite shrinks left→nothing
                draw.ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=_ink)
                bite_frac = 1.0 - phase * 2
                bite_r    = int(mr * bite_frac)
                draw.ellipse(
                    (mx - mr - bite_r // 2, my - mr, mx + mr - bite_r // 2, my + mr),
                    fill=sky_fill,
                )
            else:
                # Waning: lit left, shadow bite grows from right
                draw.ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=_ink)
                bite_frac = (phase - 0.5) * 2
                bite_r    = int(mr * bite_frac)
                draw.ellipse(
                    (mx - mr + bite_r // 2, my - mr, mx + mr + bite_r // 2, my + mr),
                    fill=sky_fill,
                )

    # ── Clouds ────────────────────────────────────────────────────────────────
    cloud_itypes = ("cloudy", "partly_cloudy", "rain", "drizzle", "snow", "storm", "fog")
    if itype in cloud_itypes:
        dark  = itype in ("rain", "drizzle", "storm")
        if is_night:
            cfill = 200 if dark else 230   # lighter so clouds show on black sky
        else:
            cfill = 40 if dark else 155
        csize   = max(w // 5, 30)
        cloud_positions = [
            (x0 + w // 5,      y0 + int(sky_h * 0.25)),
            (x0 + w * 3 // 5,  y0 + int(sky_h * 0.15)),
        ]
        if itype in ("cloudy", "fog"):
            cloud_positions.append((x0 + w * 2 // 5, y0 + int(sky_h * 0.42)))
        for (cx, cy) in cloud_positions:
            _cloud(draw, cx, cy, csize, cfill)
            # Highlight: lighter ellipse on upper-left quadrant for 3-D depth
            h_r    = max(3, csize // 7)
            h_fill = min(255, cfill + 75) if not is_night else min(255, cfill + 35)
            draw.ellipse(
                (cx - csize // 3 - h_r, cy - csize // 6 - h_r,
                 cx - csize // 3 + h_r, cy - csize // 6 + h_r),
                fill=h_fill,
            )

    # ── Weather effects ───────────────────────────────────────────────────────
    random.seed(weather_code * 7 + hour)

    if itype in ("rain", "drizzle"):
        count = 22 if itype == "rain" else 11
        lw    =  2 if itype == "rain" else 1
        for _ in range(count):
            rx = x0 + random.randint(0, w - 1)
            ry = y0 + int(sky_h * 0.50) + random.randint(0, int(sky_h * 0.45))
            draw.line((rx, ry, rx - 3, ry + 10), fill=_ink, width=lw)

    elif itype == "snow":
        for _ in range(28):
            sx = x0 + random.randint(0, w - 1)
            sy = y0 + int(sky_h * 0.40) + random.randint(0, int(sky_h * 0.55))
            sr = random.randint(1, 3)
            draw.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=_ink)

    elif itype == "storm":
        _lightning(
            draw,
            x0 + w // 2,
            y0 + int(sky_h * 0.52),
            int(min(w, h) * 0.28),
            _ink,
        )

    elif itype == "fog":
        # Bayer-style ordered dither: scatter semi-transparent dots across the
        # sky area to give a hazy/misty feel without heavy horizontal banding.
        cell = max(4, min(w, sky_h) // 22)
        # 4×4 Bayer threshold matrix (0–15)
        bayer = [
            [ 0,  8,  2, 10],
            [12,  4, 14,  6],
            [ 3, 11,  1,  9],
            [15,  7, 13,  5],
        ]
        fog_top    = y0 + int(sky_h * 0.10)
        fog_bottom = y0 + sky_h
        # Density ramp: denser near the ground, lighter near the top.
        for row_y in range(fog_top, fog_bottom, cell):
            depth = (row_y - fog_top) / max(1, fog_bottom - fog_top)  # 0→1
            threshold = int(14 - depth * 10)   # 14 (sparse) → 4 (dense)
            for col_x in range(x0, x0 + w, cell):
                bi = ((row_y - fog_top) // cell) % 4
                bj = ((col_x - x0)     // cell) % 4
                if bayer[bi][bj] >= threshold:
                    r = max(1, cell // 3)
                    cx2 = col_x + cell // 2
                    cy2 = row_y + cell // 2
                    draw.ellipse((cx2 - r, cy2 - r, cx2 + r, cy2 + r), fill=170)

    # ── Layered hills (back → front, darkening) ───────────────────────────────
    def _hill(pts_frac: list[tuple[float, float]], fill: int) -> None:
        pts = [(x0 + int(fx * w), y0 + int(fy * h)) for fx, fy in pts_frac]
        draw.polygon(pts, fill=fill)

    # Hills: moonlit (lighter) at night so they show against the black sky.
    hfar  = 210 if is_night else 190
    hmid  = 160 if is_night else 115
    hnear =  90 if is_night else  50

    # Far hill — lightest
    _hill([
        (0.00, 1.00), (0.00, 0.68),
        (0.18, 0.59), (0.38, 0.64), (0.58, 0.57),
        (0.80, 0.62), (1.00, 0.60), (1.00, 1.00),
    ], fill=hfar)

    # Mid hill
    _hill([
        (0.00, 1.00), (0.00, 0.77),
        (0.14, 0.71), (0.33, 0.66), (0.52, 0.69),
        (0.72, 0.64), (1.00, 0.70), (1.00, 1.00),
    ], fill=hmid)

    # Near hill — darkest / foreground
    _hill([
        (0.00, 1.00), (0.00, 0.85),
        (0.11, 0.82), (0.28, 0.75), (0.48, 0.78),
        (0.68, 0.73), (0.86, 0.80), (1.00, 0.83),
        (1.00, 1.00),
    ], fill=hnear)

    # Snow ground cover (over hills)
    if itype == "snow":
        _hill([
            (0.00, 1.00), (0.00, 0.90),
            (0.20, 0.87), (0.50, 0.88), (0.80, 0.86),
            (1.00, 0.89), (1.00, 1.00),
        ], fill=245)
