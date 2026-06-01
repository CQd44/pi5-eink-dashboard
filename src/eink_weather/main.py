import logging
import time

from .config import load_config
from .display import EInkDisplay
from .sensors import SensorReader
from .weather import WeatherClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def run_once() -> None:
    config = load_config()
    weather_client = WeatherClient.from_location(
        latitude=config.latitude,
        longitude=config.longitude,
        timezone=config.timezone,
        zip_code=config.zip_code,
        country_code=config.country_code,
        location_query=config.location_query,
    )
    sensor_reader = SensorReader(
        mode=config.sensor_mode,
        dht22_gpio_pins=list(config.dht22_gpio_pins),
        min_temp_f=config.min_temp_f,
        max_temp_f=config.max_temp_f,
        min_humidity_pct=config.min_humidity_pct,
        max_humidity_pct=config.max_humidity_pct,
    )
    display = EInkDisplay(
        rotation=config.display_rotation,
        width=config.display_width,
        height=config.display_height,
        hot_temp_threshold_f=config.hot_temp_threshold_f,
    )

    forecast = weather_client.fetch_bundle()
    sensor = sensor_reader.read()
    output_file = display.render(forecast=forecast, sensor=sensor)

    logging.info(
        "Display refreshed. location=%s outside=%.1fC local_avg=%.1fC humidity_avg=%.1f%% used=%s/%s source=%s weekly_days=%s frame=%s",
        forecast.location_label,
        forecast.current.temperature_c,
        sensor.temperature_c,
        sensor.humidity_pct,
        sensor.sensors_used,
        sensor.sensors_seen,
        sensor.source,
        len(forecast.weekly),
        output_file,
    )


def main() -> None:
    config = load_config()
    logging.info("Starting loop with refresh every %s seconds", config.refresh_seconds)

    while True:
        try:
            run_once()
        except Exception as exc:
            logging.exception("Refresh failed: %s", exc)
        time.sleep(config.refresh_seconds)


if __name__ == "__main__":
    main()
