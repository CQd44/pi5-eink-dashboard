"""E-ink display rendering.

Layout (800 × 480 default — 7.5" Waveshare e-ink):

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  HEADER  (inverted, black bg)   location  ···  date/time               │  45 px
  ├────────────────────────────┬────────────────────────────────────────────┤
  │  INDOOR                    │  OUTDOOR                   [icon]          │
  │  72.5 °F                   │  74.3 °F                                   │  ~258 px
  │  48 %  Humidity            │  Partly Cloudy                             │
  │  DHT22  2/2 sensors        │  Wind  8 mph                               │
  ├────────────────────────────┴────────────────────────────────────────────┤
  │  MON   TUE   WED   THU   FRI   SAT   SUN   (7-day forecast strip)      │  ~175 px
  └─────────────────────────────────────────────────────────────────────────┘
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

from .icons import draw_icon, draw_scene, label as weather_label
from .sensors import SensorSnapshot
from .weather import ForecastBundle

# ── Font paths ────────────────────────────────────────────────────────────────
_F  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    path = _FB if bold else _F
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _c_to_f(c: float) -> float:
    return c * 9.0 / 5.0 + 32.0


def _parse_sky_hour(iso: str, default: float) -> float:
    """Parse 'YYYY-MM-DDTHH:MM' → fractional hour (e.g. 6.2 for 06:12)."""
    try:
        time_part = iso.split("T")[1]
        h, m = time_part.split(":")[:2]
        return int(h) + int(m) / 60.0
    except Exception:
        return default


# ── Display color palette (RGB) ──────────────────────────────────────────────────
BLACK = (  0,   0,   0)
WHITE = (255, 255, 255)
RED   = (200,   0,   0)
GRAY  = (110, 110, 110)
LGRAY = (175, 175, 175)


def _split_bwr_planes(
    img: Image.Image,
) -> tuple[Image.Image, Image.Image]:
    """Split an RGB image into 1-bit black and 1-bit red planes.

    Waveshare BWR display: getbuffer() expects 1-bit images where
    0 = print ink, 1 = leave white.
    """
    r_ch, g_ch, b_ch = img.split()
    # Black: all channels dark
    black_mask = ImageChops.darker(
        ImageChops.darker(
            r_ch.point(lambda v: 255 if v < 64 else 0),
            g_ch.point(lambda v: 255 if v < 64 else 0),
        ),
        b_ch.point(lambda v: 255 if v < 64 else 0),
    )
    black_1bit = ImageOps.invert(black_mask).convert("1")
    # Red: R high, G and B low
    red_mask = ImageChops.darker(
        ImageChops.darker(
            r_ch.point(lambda v: 255 if v > 160 else 0),
            g_ch.point(lambda v: 255 if v < 80 else 0),
        ),
        b_ch.point(lambda v: 255 if v < 80 else 0),
    )
    red_1bit = ImageOps.invert(red_mask).convert("1")
    return black_1bit, red_1bit


class EInkDisplay:
    """Renders weather + sensor data to a Pillow image and optionally pushes
    to a Waveshare 7.5" V2 e-ink panel."""

    def __init__(
        self,
        rotation: int = 0,
        width: int = 800,
        height: int = 480,
        hot_temp_threshold_f: float = 90.0,
    ) -> None:
        self.rotation = rotation
        self.width = width
        self.height = height
        self._hot_temp_threshold_f = hot_temp_threshold_f
        self._is_bwr = False          # set True by _init_hardware if BWR driver found
        self._epd = self._init_hardware()

    def _init_hardware(self):
        # Try tri-color (BWR) driver first — needed for panels with a red layer.
        # Fall back to monochrome V2 if not available.
        for module_name, is_bwr in [("epd7in5b_V2", True), ("epd7in5_V2", False)]:
            try:
                from importlib import import_module
                mod = import_module(f"waveshare_epd.{module_name}")
                epd = mod.EPD()
                epd.init()
                epd.Clear()
                self._is_bwr = is_bwr
                return epd
            except Exception:
                continue
        return None

    def render(self, forecast: ForecastBundle, sensor: SensorSnapshot) -> Path:
        W, H = self.width, self.height

        # ── Layout constants (scale with resolution) ──────────────────────────
        HDR_H      = 45
        MID_X      = W // 2
        TOP_BOT    = HDR_H + int((H - HDR_H) * 0.56)   # ~302 @ 480 px
        WEEKLY_TOP = TOP_BOT + 8
        PAD        = 18

        # ── Canvas ────────────────────────────────────────────────────────────
        img = Image.new("RGB", (W, H), WHITE)
        d   = ImageDraw.Draw(img)

        # ── Fonts ─────────────────────────────────────────────────────────────
        f12  = _font(False, 12)
        f14  = _font(False, 14)
        f16b = _font(True,  16)
        f18  = _font(False, 18)
        f22b = _font(True,  22)
        f40b = _font(True,  40)
        f54b = _font(True,  54)

        current    = forecast.current
        temp_f_out = _c_to_f(current.temperature_c)
        temp_f_in  = _c_to_f(sensor.temperature_c)

        # ── Alert flags ───────────────────────────────────────────────────────
        # Severe = only hail-producing storms; plain thunderstorms (95, 97) are
        # common summer events and don't warrant a full red-header alert.
        is_severe    = current.weather_code in (96, 98, 99)
        is_hot       = temp_f_out >= self._hot_temp_threshold_f
        alert        = is_severe or is_hot
        out_temp_col = RED if is_hot else BLACK
        hdr_col      = RED if alert else BLACK

        # ════════════════════════════════════════════════════════════════════
        # DIVIDERS
        # ════════════════════════════════════════════════════════════════════
        d.line((MID_X, HDR_H + 2, MID_X, TOP_BOT - 2), fill=LGRAY, width=1)
        d.line((0, TOP_BOT, W, TOP_BOT), fill=BLACK, width=2)

        # ════════════════════════════════════════════════════════════════════
        # LEFT PANEL — INDOOR
        # ════════════════════════════════════════════════════════════════════
        y = HDR_H + 10
        d.text((PAD, y), "INDOOR", fill=BLACK, font=f16b, anchor="lt")
        y += 26
        d.text((PAD, y), f"{temp_f_in:.0f}\u00b0F", fill=BLACK, font=f40b, anchor="lt")
        y += 52
        d.text((PAD, y), f"{sensor.humidity_pct:.0f}%  Humidity", fill=BLACK, font=f22b, anchor="lt")
        y += 32

        if sensor.source == "simulated":
            note, note_col = "Simulated sensor data", GRAY
        elif sensor.source == "dht22-last-good":
            note, note_col = f"DHT22  last-good  ({sensor.sensors_seen} sensors)", RED
        elif sensor.sensors_used == 0:
            note, note_col = f"DHT22  no data  ({sensor.sensors_seen} sensors)", RED
        else:
            note, note_col = f"DHT22  {sensor.sensors_used}/{sensor.sensors_seen} sensors", GRAY
        d.text((PAD, y), note, fill=note_col, font=f14, anchor="lt")

        # ════════════════════════════════════════════════════════════════════
        # RIGHT PANEL — OUTDOOR  (scenic background + data strip)
        # ════════════════════════════════════════════════════════════════════
        out_panel_h = TOP_BOT - HDR_H
        scene_h     = int(out_panel_h * 0.50)   # top 50 % landscape, 50 % data strip
        text_y0     = HDR_H + scene_h

        # Scenic landscape
        _now = datetime.now()
        # Pull today's sky times from the first daily forecast entry (today)
        _today_fc = forecast.weekly[0] if forecast.weekly else None
        _sunrise_h  = _parse_sky_hour(_today_fc.sunrise,  6.0)  if _today_fc else 6.0
        _sunset_h   = _parse_sky_hour(_today_fc.sunset,  20.0)  if _today_fc else 20.0
        _moonrise_h = _parse_sky_hour(_today_fc.moonrise, -1.0) if _today_fc else None
        _moonset_h  = _parse_sky_hour(_today_fc.moonset,  -1.0) if _today_fc else None
        draw_scene(
            d, MID_X, HDR_H, W - MID_X, scene_h,
            current.weather_code,
            hour=_now.hour + _now.minute / 60.0,
            today=_now.date(),
            sunrise_hour=_sunrise_h,
            sunset_hour=_sunset_h,
            moonrise_hour=_moonrise_h if _moonrise_h is not None and _moonrise_h >= 0 else None,
            moonset_hour=_moonset_h  if _moonset_h  is not None and _moonset_h  >= 0 else None,
        )

        # White data strip below scene
        d.rectangle((MID_X, text_y0, W, TOP_BOT), fill=WHITE)
        d.line((MID_X, text_y0, W, text_y0), fill=LGRAY, width=1)

        x1       = MID_X + PAD
        wind_mph = current.windspeed_kmh * 0.621371
        y        = text_y0 + 6
        d.text((x1, y), "OUTDOOR", fill=BLACK, font=f16b, anchor="lt")
        y += 22
        # Temp (large, red if above threshold) + condition label right-aligned
        d.text((x1, y), f"{temp_f_out:.0f}\u00b0", fill=out_temp_col, font=f40b, anchor="lt")
        d.text((W - PAD, y), weather_label(current.weather_code), fill=BLACK, font=f18, anchor="rt")
        y += 52
        d.text((x1, y), f"Humidity: {current.humidity_pct:.0f}%", fill=BLACK, font=f16b, anchor="lt")
        y += 22
        d.text(
            (x1, y),
            f"Wind: {wind_mph:.0f} mph  |  Rain: {current.precipitation_probability:.0f}%",
            fill=BLACK, font=f16b, anchor="lt",
        )

        # ════════════════════════════════════════════════════════════════════
        # BOTTOM — 7-DAY WEEKLY FORECAST STRIP
        # ════════════════════════════════════════════════════════════════════
        days = forecast.weekly[:7]
        if days:
            col_w = W // len(days)
            for i, day in enumerate(days):
                cx  = i * col_w + col_w // 2
                yw  = WEEKLY_TOP

                # Day abbreviation
                try:
                    from datetime import date as _date
                    day_name = _date.fromisoformat(day.date).strftime("%a").upper()
                except Exception:
                    day_name = day.date[-5:]
                d.text((cx, yw), day_name, fill=BLACK, font=f16b, anchor="mt")
                yw += 20

                # Small icon — hail storms (96, 98, 99) drawn in red; plain
                # thunderstorms (95, 97) use black — common in summer, not an alert
                icon_col = RED if day.weather_code in (96, 98, 99) else BLACK
                draw_icon(d, cx, yw + 20, 40, day.weather_code, color=icon_col, bg=WHITE)
                yw += 46

                # High / Low in °F — HIGH bold red, LOW smaller light gray
                hi_f = _c_to_f(day.temp_max_c)
                lo_f = _c_to_f(day.temp_min_c)
                d.text((cx, yw), f"{hi_f:.0f}\u00b0", fill=RED,   font=f22b, anchor="mt")
                yw += 28
                d.text((cx, yw), f"{lo_f:.0f}\u00b0", fill=LGRAY, font=f16b, anchor="mt")
                yw += 22

                # Rain probability — always shown; red if ≥50 %
                rain_pct = day.precipitation_probability_max
                rain_col = RED if rain_pct >= 50 else BLACK
                d.text(
                    (cx, yw),
                    f"{rain_pct:.0f}% rain",
                    fill=rain_col, font=f12, anchor="mt",
                )

                # Thin column divider (skip last column)
                if i < len(days) - 1:
                    d.line(
                        (cx + col_w // 2, TOP_BOT + 4, cx + col_w // 2, H - 4),
                        fill=LGRAY, width=1,
                    )

        # ════════════════════════════════════════════════════════════════════
        # HEADER — drawn last so it always overpaints any scene bleed
        # ════════════════════════════════════════════════════════════════════
        d.rectangle((0, 0, W, HDR_H), fill=hdr_col)   # RED on severe weather / heat
        now = datetime.now().strftime("%a, %b %-d  %-I:%M %p")
        d.text((PAD, HDR_H // 2), forecast.location_label, fill=WHITE, font=f18, anchor="lm")
        d.text((W - PAD, HDR_H // 2), now, fill=WHITE, font=f18, anchor="rm")

        # ── Rotation ─────────────────────────────────────────────────────────
        if self.rotation in (90, 180, 270):
            img = img.rotate(self.rotation, expand=True)

        # ── Save PNG for simulator / debug ────────────────────────────────────
        out = Path("last_frame.png")
        img.save(out, "PNG")

        # ── Push to hardware ───────────────────────────────────────────────────────
        if self._epd is not None:
            try:
                if self._is_bwr:
                    bk, rd = _split_bwr_planes(img)
                    self._epd.display(
                        self._epd.getbuffer(bk),
                        self._epd.getbuffer(rd),
                    )
                else:
                    # Mono display: convert RGB → grayscale → 1-bit
                    self._epd.display(self._epd.getbuffer(img.convert("L").convert("1")))
            except Exception:
                pass

        return out
