from dataclasses import dataclass
import random
from typing import Optional


@dataclass(frozen=True)
class SensorSnapshot:
    temperature_c: float
    humidity_pct: float
    sensors_seen: int
    sensors_used: int
    source: str


class SensorReader:
    def __init__(
        self,
        mode: str = "simulated",
        dht22_gpio_pins: Optional[list[int]] = None,
        min_temp_f: float = 20.0,
        max_temp_f: float = 95.0,
        min_humidity_pct: float = 5.0,
        max_humidity_pct: float = 100.0,
    ):
        self.mode = mode
        self.dht22_gpio_pins = dht22_gpio_pins or [4, 27]
        self.min_temp_f = min_temp_f
        self.max_temp_f = max_temp_f
        self.min_humidity_pct = min_humidity_pct
        self.max_humidity_pct = max_humidity_pct
        self._last_good_snapshot: Optional[SensorSnapshot] = None

    def read(self) -> SensorSnapshot:
        if self.mode == "dht22":
            samples = [self._read_dht22(pin) for pin in self.dht22_gpio_pins]
            valid_samples = [s for s in samples if s is not None and self._is_sane(s)]
            if valid_samples:
                avg_temp = sum(s.temperature_c for s in valid_samples) / len(valid_samples)
                avg_humidity = sum(s.humidity_pct for s in valid_samples) / len(valid_samples)
                snapshot = SensorSnapshot(
                    temperature_c=round(avg_temp, 1),
                    humidity_pct=round(avg_humidity, 1),
                    sensors_seen=len(self.dht22_gpio_pins),
                    sensors_used=len(valid_samples),
                    source="dht22",
                )
                self._last_good_snapshot = snapshot
                return snapshot

            if self._last_good_snapshot is not None:
                return SensorSnapshot(
                    temperature_c=self._last_good_snapshot.temperature_c,
                    humidity_pct=self._last_good_snapshot.humidity_pct,
                    sensors_seen=len(self.dht22_gpio_pins),
                    sensors_used=0,
                    source="dht22-last-good",
                )

            raise RuntimeError(
                "No valid DHT22 readings yet (all unavailable or out of sanity bounds)."
            )
        return self._read_simulated()

    def _read_simulated(
        self,
        sensors_seen: int = 1,
        sensors_used: int = 1,
        source: str = "simulated",
    ) -> SensorSnapshot:
        return SensorSnapshot(
            temperature_c=round(random.uniform(20.0, 28.0), 1),
            humidity_pct=round(random.uniform(35.0, 65.0), 1),
            sensors_seen=sensors_seen,
            sensors_used=sensors_used,
            source=source,
        )

    def _is_sane(self, sample: SensorSnapshot) -> bool:
        temp_f = (sample.temperature_c * 9.0 / 5.0) + 32.0
        return (
            self.min_temp_f <= temp_f <= self.max_temp_f
            and self.min_humidity_pct <= sample.humidity_pct <= self.max_humidity_pct
        )

    def _read_dht22(self, gpio_pin: int) -> Optional[SensorSnapshot]:
        try:
            import adafruit_dht
            import board
        except Exception:
            return None

        pin_name = f"D{gpio_pin}"
        board_pin = getattr(board, pin_name, None)
        if board_pin is None:
            return None

        dht = adafruit_dht.DHT22(board_pin)
        try:
            temperature = dht.temperature
            humidity = dht.humidity
            if temperature is None or humidity is None:
                return None
            return SensorSnapshot(
                temperature_c=round(float(temperature), 1),
                humidity_pct=round(float(humidity), 1),
                sensors_seen=1,
                sensors_used=1,
                source="dht22",
            )
        except Exception:
            return None
        finally:
            dht.exit()
