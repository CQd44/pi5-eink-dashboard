from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv(override=True)


@dataclass(frozen=True)
class AppConfig:
    latitude: float
    longitude: float
    zip_code: str
    country_code: str
    location_query: str
    timezone: str
    refresh_seconds: int
    sensor_mode: str
    dht22_gpio_pins: tuple[int, ...]
    min_temp_f: float
    max_temp_f: float
    min_humidity_pct: float
    max_humidity_pct: float
    display_rotation: int
    display_width: int
    display_height: int
    hot_temp_threshold_f: float


def _parse_gpio_pins() -> tuple[int, ...]:
    raw_list = os.getenv("DHT22_GPIO_PINS", "").strip()
    if raw_list:
        pins: list[int] = []
        for part in raw_list.split(","):
            token = part.strip()
            if not token:
                continue
            value = int(token)
            if value not in pins:
                pins.append(value)
        if pins:
            return tuple(pins)

    # Backward-compatible fallback.
    primary = int(os.getenv("DHT22_GPIO_PIN", "4"))
    secondary = int(os.getenv("DHT22_GPIO_PIN_2", "27"))
    if primary == secondary:
        return (primary,)
    return (primary, secondary)


def load_config() -> AppConfig:
    return AppConfig(
        latitude=float(os.getenv("LATITUDE", "40.7128")),
        longitude=float(os.getenv("LONGITUDE", "-74.0060")),
        zip_code=os.getenv("ZIP_CODE", ""),
        country_code=os.getenv("COUNTRY_CODE", "US"),
        location_query=os.getenv("LOCATION_QUERY", ""),
        timezone=os.getenv("TIMEZONE", "auto"),
        refresh_seconds=int(os.getenv("REFRESH_SECONDS", "600")),
        sensor_mode=os.getenv("SENSOR_MODE", "simulated").lower(),
        dht22_gpio_pins=_parse_gpio_pins(),
        min_temp_f=float(os.getenv("MIN_VALID_TEMP_F", "20")),
        max_temp_f=float(os.getenv("MAX_VALID_TEMP_F", "95")),
        min_humidity_pct=float(os.getenv("MIN_VALID_HUMIDITY_PCT", "5")),
        max_humidity_pct=float(os.getenv("MAX_VALID_HUMIDITY_PCT", "100")),
        display_rotation=int(os.getenv("DISPLAY_ROTATION", "0")),
        display_width=int(os.getenv("DISPLAY_WIDTH", "800")),
        display_height=int(os.getenv("DISPLAY_HEIGHT", "480")),
        hot_temp_threshold_f=float(os.getenv("HOT_TEMP_THRESHOLD_F", "100")),
    )
