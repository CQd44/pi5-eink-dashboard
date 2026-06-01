# DESPI-C02 to Raspberry Pi 5 Wiring

Primary wiring image: `docs/wiring_panel.png`

The panel includes:
- DESPI-C02 e-ink breakout connections
- DHT22 sensor #1 on GPIO4 (physical pin 7)
- DHT22 sensor #2 on GPIO27 (physical pin 13)

## Pin map

| DESPI-C02 Signal | Raspberry Pi 5 Physical Pin | BCM GPIO |
|---|---:|---:|
| 3.3V / VCC | 1 | - |
| GND | 6 (or 9/14/etc.) | - |
| DIN / MOSI | 19 | 10 |
| CLK / SCK | 23 | 11 |
| CS | 24 | 8 |
| DC | 22 | 25 |
| RST | 11 | 17 |
| BUSY | 18 | 24 |

## Sensor pin reminder

For your DHT22/AM2302 sensors, use separate GPIO data lines.
Current consolidated plan uses BCM GPIO4 (pin 7) and BCM GPIO27 (pin 13).
