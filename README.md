# Pi 5 E-Ink Weather Dashboard

Starter Python project for a Raspberry Pi 5 that:
- Fetches local weather from Open-Meteo (current + 7-day forecast).
- Reads local temperature and humidity from a GPIO sensor.
- Renders both data sources to a Waveshare-compatible SPI e-ink display.

## Hardware wiring (display)

Use this exact mapping for the DESPI-C02 e-ink board:

| Display Pin | Raspberry Pi 5 Pin |
|---|---|
| VCC (3.3V) | Pin 1 (3.3V) |
| GND | Pin 6 (or 9/14/etc.) |
| DIN / MOSI | Pin 19 (GPIO 10) |
| CLK / SCK | Pin 23 (GPIO 11) |
| CS | Pin 24 (GPIO 8) |
| DC | Pin 22 (GPIO 25) |
| RST | Pin 11 (GPIO 17) |
| BUSY | Pin 18 (GPIO 24) |

A consolidated visual wiring panel PNG is in `docs/wiring_panel.png`.

## Sensor hardware

The Amazon sensors you shared are DHT22/AM2302 modules.

Suggested Pi 5 wiring for two DHT22 modules:

| Sensor | DHT22 Module Pin | Raspberry Pi 5 Pin |
|---|---|
| Sensor #1 | VCC | Pin 17 (3.3V) |
| Sensor #1 | DATA | Pin 7 (GPIO 4) |
| Sensor #1 | GND | Pin 9 (GND) |
| Sensor #2 | VCC | Pin 17 (3.3V) |
| Sensor #2 | DATA | Pin 13 (GPIO 27) |
| Sensor #2 | GND | Pin 14 (GND) |

If your module has a board-level pull-up resistor (most do), no extra resistor is needed.
Keep DHT22 GPIO separate from e-ink SPI/control pins.

Runtime behavior for local sensor values:
- Reads both DHT22 sensors (GPIO4 and GPIO27) when `SENSOR_MODE=dht22`.
- Applies sanity filters before use (defaults: 20F to 95F, humidity 5% to 100%).
- Discards invalid readings and averages only valid sensors.
- If no valid DHT22 reading is available, it reuses the last known good real reading.

Runtime behavior for weather location lookup:
- If `ZIP_CODE` is set, resolves ZIP to coordinates first (using `COUNTRY_CODE`, default `US`).
- Else if `LOCATION_QUERY` is set, geocodes the neighborhood/city query.
- Else uses `LATITUDE` and `LONGITUDE` directly.
- Pulls both current conditions and 7-day daily forecast each refresh.

## Project layout

- `src/eink_weather/main.py`: app entrypoint
- `src/eink_weather/weather.py`: Open-Meteo client
- `src/eink_weather/sensors.py`: local temp/humidity sensor reader
- `src/eink_weather/display.py`: e-ink rendering and hardware bridge
- `src/eink_weather/config.py`: env-based settings
- `docs/wiring_panel.png`: pin map diagram image

## 1) Enable SPI on Raspberry Pi OS

```bash
sudo raspi-config
# Interface Options -> SPI -> Enable
sudo reboot
```

## 2) Install system dependencies

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv libopenjp2-7 libtiff6
```

## 3) Create venv and install Python packages

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4) Configure environment

```bash
cp .env.example .env
# edit .env with your latitude/longitude and sensor config
```

## 5) Run

```bash
PYTHONPATH=src python -m eink_weather.main
```

## Notes

- The display backend currently uses a generic Waveshare pattern and can be adapted to your exact panel class.
- Sensor support includes DHT22 and simulated mode for bench testing.
- For first bootstrapping, set `SENSOR_MODE=simulated` in `.env` to validate display and weather flow.
