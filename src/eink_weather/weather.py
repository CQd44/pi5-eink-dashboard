from dataclasses import dataclass
from typing import Optional

import requests


@dataclass(frozen=True)
class WeatherSnapshot:
    temperature_c: float
    windspeed_kmh: float
    weather_code: int
    humidity_pct: float = 0.0
    precipitation_probability: float = 0.0


@dataclass(frozen=True)
class DailyForecast:
    date: str
    temp_max_c: float
    temp_min_c: float
    precipitation_probability_max: float
    weather_code: int
    sunrise: str = ""    # ISO datetime e.g. "2026-06-01T06:12"
    sunset: str = ""     # ISO datetime e.g. "2026-06-01T20:14"
    moonrise: str = ""   # ISO datetime e.g. "2026-06-01T21:05"
    moonset: str = ""    # ISO datetime e.g. "2026-06-02T07:33"


@dataclass(frozen=True)
class ForecastBundle:
    location_label: str
    current: WeatherSnapshot
    weekly: list[DailyForecast]


class WeatherClient:
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    ZIP_URL_TEMPLATE = "https://api.zippopotam.us/{country}/{zip_code}"

    def __init__(
        self,
        latitude: float,
        longitude: float,
        timezone: str = "auto",
        location_label: str = "configured coordinates",
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
        self.location_label = location_label

    @classmethod
    def from_location(
        cls,
        *,
        latitude: float,
        longitude: float,
        timezone: str,
        zip_code: str = "",
        country_code: str = "US",
        location_query: str = "",
    ) -> "WeatherClient":
        zip_value = zip_code.strip()
        query_value = location_query.strip()
        country_value = (country_code.strip() or "US").lower()

        if zip_value:
            resolved = cls._resolve_zip(zip_value, country_value)
            if resolved is not None:
                lat, lon, label = resolved
                return cls(lat, lon, timezone=timezone, location_label=label)

        if query_value:
            resolved = cls._resolve_name(query_value)
            if resolved is not None:
                lat, lon, label = resolved
                return cls(lat, lon, timezone=timezone, location_label=label)

        label = f"coords ({latitude:.4f}, {longitude:.4f})"
        return cls(latitude, longitude, timezone=timezone, location_label=label)

    @classmethod
    def _resolve_zip(cls, zip_code: str, country_code: str) -> Optional[tuple[float, float, str]]:
        url = cls.ZIP_URL_TEMPLATE.format(country=country_code, zip_code=zip_code)
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return None
            payload = response.json()
            places = payload.get("places") or []
            if not places:
                return None
            first = places[0]
            lat = float(first.get("latitude"))
            lon = float(first.get("longitude"))
            place_name = first.get("place name", "")
            state = first.get("state abbreviation") or first.get("state") or ""
            label_parts = [part for part in [place_name, state] if part]
            label = ", ".join(label_parts) if label_parts else zip_code.upper()
            return lat, lon, label
        except Exception:
            return None

    @classmethod
    def _resolve_name(cls, query: str) -> Optional[tuple[float, float, str]]:
        params = {
            "name": query,
            "count": 1,
            "language": "en",
            "format": "json",
        }
        try:
            response = requests.get(cls.GEOCODE_URL, params=params, timeout=10)
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results") or []
            if not results:
                return None
            first = results[0]
            lat = float(first["latitude"])
            lon = float(first["longitude"])
            name = first.get("name", query)
            country = first.get("country_code", "")
            label = f"{name}, {country}".strip(", ")
            return lat, lon, label
        except Exception:
            return None

    def fetch_current(self) -> WeatherSnapshot:
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current": "temperature_2m,windspeed_10m,weathercode,relativehumidity_2m,precipitation_probability",
            "timezone": self.timezone,
        }
        response = requests.get(self.FORECAST_URL, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()

        current = payload.get("current", {})
        return WeatherSnapshot(
            temperature_c=float(current.get("temperature_2m", 0.0)),
            windspeed_kmh=float(current.get("windspeed_10m", 0.0)),
            weather_code=int(current.get("weathercode", -1)),
            humidity_pct=float(current.get("relativehumidity_2m", 0.0)),
            precipitation_probability=float(current.get("precipitation_probability", 0.0)),
        )

    def fetch_weekly(self) -> list[DailyForecast]:
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "daily": (
                "temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max,weathercode,"
                "sunrise,sunset"
            ),
            "forecast_days": 7,
            "timezone": self.timezone,
        }
        response = requests.get(self.FORECAST_URL, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        daily = payload.get("daily", {})

        dates    = daily.get("time", [])
        tmax     = daily.get("temperature_2m_max", [])
        tmin     = daily.get("temperature_2m_min", [])
        pmax     = daily.get("precipitation_probability_max", [])
        wcode    = daily.get("weathercode", [])
        sunrises = daily.get("sunrise", [])
        sunsets  = daily.get("sunset", [])
        moonrises= daily.get("moonrise", [])
        moonsets = daily.get("moonset", [])

        forecasts: list[DailyForecast] = []
        for i, date in enumerate(dates):
            forecasts.append(
                DailyForecast(
                    date=str(date),
                    temp_max_c=float(tmax[i]) if i < len(tmax) else 0.0,
                    temp_min_c=float(tmin[i]) if i < len(tmin) else 0.0,
                    precipitation_probability_max=float(pmax[i]) if i < len(pmax) else 0.0,
                    weather_code=int(wcode[i]) if i < len(wcode) else -1,
                    sunrise=str(sunrises[i]) if i < len(sunrises) else "",
                    sunset=str(sunsets[i]) if i < len(sunsets) else "",
                    moonrise=str(moonrises[i]) if i < len(moonrises) else "",
                    moonset=str(moonsets[i]) if i < len(moonsets) else "",
                )
            )
        return forecasts

    def fetch_bundle(self) -> ForecastBundle:
        return ForecastBundle(
            location_label=self.location_label,
            current=self.fetch_current(),
            weekly=self.fetch_weekly(),
        )
