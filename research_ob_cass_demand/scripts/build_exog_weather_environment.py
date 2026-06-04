#!/usr/bin/env python3
"""Build monthly Seoul weather/environment exogenous variables for IMEN343 Cass demand project.

Sources:
- Open-Meteo Historical Weather API for Seoul City Hall coordinates (hourly + daily reanalysis/model archive)
- Seoul Open Data MonthlyAverageAirQuality service for station '중구' (monthly official air-quality station data)

Output: data/exog_weather_environment_monthly.csv
"""
from __future__ import annotations

import calendar
import math
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

BASE_DIR = Path(__file__).resolve().parents[1]
OUT = BASE_DIR / "data" / "exog_weather_environment_monthly.csv"

LAT = 37.5665
LON = 126.9780
TIMEZONE = "Asia/Seoul"
START_YEAR = 2020
END_YEAR = 2025
AIR_STATION = "중구"  # central Seoul station; one-row station query works with Seoul sample API key

WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_URL_TMPL = "http://openapi.seoul.go.kr:8088/sample/json/MonthlyAverageAirQuality/1/5/{ym}/{station}"

DAILY_VARS = [
    "temperature_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_mean",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "precipitation_hours",
    "wind_speed_10m_mean",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "shortwave_radiation_sum",
    "daylight_duration",
    "sunshine_duration",
]

HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "wind_speed_10m",
]

DISTRICT_NAMES = {
    "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구", "강북구", "도봉구",
    "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구", "구로구", "금천구", "영등포구", "동작구",
    "관악구", "서초구", "강남구", "송파구", "강동구",
}


def get_json(url: str, params: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "IMEN343-data-collection/1.0"})
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # network or occasional Open API transient errors
            last_exc = exc
            if attempt == 3:
                break
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed JSON request: {url} params={params!r} error={last_exc}")


def fetch_weather_year(year: int) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "timezone": TIMEZONE,
        "daily": ",".join(DAILY_VARS),
        "hourly": ",".join(HOURLY_VARS),
    }
    js = get_json(WEATHER_URL, params=params, timeout=90)
    if "daily" not in js or "hourly" not in js:
        raise RuntimeError(f"Unexpected Open-Meteo response for {year}: {js}")

    daily = pd.DataFrame(js["daily"])
    daily["date"] = pd.to_datetime(daily.pop("time"))
    daily["month"] = daily["date"].dt.strftime("%Y-%m")

    hourly = pd.DataFrame(js["hourly"])
    hourly["time"] = pd.to_datetime(hourly["time"])
    hourly["date"] = hourly["time"].dt.date
    hourly["month"] = hourly["time"].dt.strftime("%Y-%m")
    meta = {k: js.get(k) for k in ["latitude", "longitude", "elevation", "timezone"]}
    return daily, hourly, meta


def aggregate_weather() -> tuple[pd.DataFrame, dict[str, Any]]:
    daily_parts: list[pd.DataFrame] = []
    hourly_parts: list[pd.DataFrame] = []
    metas: list[dict[str, Any]] = []
    for y in range(START_YEAR, END_YEAR + 1):
        d, h, meta = fetch_weather_year(y)
        daily_parts.append(d)
        hourly_parts.append(h)
        metas.append(meta)
        time.sleep(0.2)

    daily = pd.concat(daily_parts, ignore_index=True)
    hourly = pd.concat(hourly_parts, ignore_index=True)

    # Daily-derived monthly features
    def cdd(x: pd.Series, base: float) -> float:
        return float(np.maximum(x - base, 0).sum())

    def hdd(x: pd.Series, base: float) -> float:
        return float(np.maximum(base - x, 0).sum())

    rows = []
    for month, g in daily.groupby("month"):
        rows.append({
            "month": month,
            "days_in_month": int(len(g)),
            "seoul_avg_temp_c": g["temperature_2m_mean"].mean(),
            "seoul_avg_max_temp_c": g["temperature_2m_max"].mean(),
            "seoul_avg_min_temp_c": g["temperature_2m_min"].mean(),
            "seoul_month_max_temp_c": g["temperature_2m_max"].max(),
            "seoul_month_min_temp_c": g["temperature_2m_min"].min(),
            "seoul_avg_apparent_temp_c": g["apparent_temperature_mean"].mean(),
            "seoul_avg_max_apparent_temp_c": g["apparent_temperature_max"].mean(),
            "seoul_avg_min_apparent_temp_c": g["apparent_temperature_min"].mean(),
            "seoul_month_max_apparent_temp_c": g["apparent_temperature_max"].max(),
            "seoul_precipitation_mm": g["precipitation_sum"].sum(),
            "seoul_rain_mm": g["rain_sum"].sum(),
            "seoul_snowfall_cm": g["snowfall_sum"].sum(),
            "seoul_precipitation_hours": g["precipitation_hours"].sum(),
            "seoul_wet_days_0_1mm": int((g["precipitation_sum"] >= 0.1).sum()),
            "seoul_rain_days_1mm": int((g["precipitation_sum"] >= 1.0).sum()),
            "seoul_heavy_rain_days_30mm": int((g["precipitation_sum"] >= 30.0).sum()),
            "seoul_very_heavy_rain_days_80mm": int((g["precipitation_sum"] >= 80.0).sum()),
            "seoul_dry_days_lt1mm": int((g["precipitation_sum"] < 1.0).sum()),
            "seoul_hot_days_30c": int((g["temperature_2m_max"] >= 30.0).sum()),
            "seoul_heatwave_warning_days_33c": int((g["temperature_2m_max"] >= 33.0).sum()),
            "seoul_tropical_nights_25c": int((g["temperature_2m_min"] >= 25.0).sum()),
            "seoul_freezing_days_min_lt0c": int((g["temperature_2m_min"] < 0.0).sum()),
            "seoul_ice_days_max_lt0c": int((g["temperature_2m_max"] < 0.0).sum()),
            "seoul_cold_wave_days_min_le_minus12c": int((g["temperature_2m_min"] <= -12.0).sum()),
            "seoul_apparent_heat_days_32c": int((g["apparent_temperature_max"] >= 32.0).sum()),
            "seoul_cooling_degree_days_18c": cdd(g["temperature_2m_mean"], 18.0),
            "seoul_heating_degree_days_18c": hdd(g["temperature_2m_mean"], 18.0),
            "seoul_cooling_degree_days_26c": cdd(g["temperature_2m_mean"], 26.0),
            "seoul_wind_speed_mean_kmh_daily": g["wind_speed_10m_mean"].mean(),
            "seoul_wind_speed_max_kmh_daily": g["wind_speed_10m_max"].max(),
            "seoul_wind_gust_max_kmh": g["wind_gusts_10m_max"].max(),
            "seoul_shortwave_radiation_mj_m2_sum": g["shortwave_radiation_sum"].sum(),
            "seoul_shortwave_radiation_mj_m2_daily_mean": g["shortwave_radiation_sum"].mean(),
            "seoul_daylight_hours_sum": (g["daylight_duration"].sum() / 3600.0),
            "seoul_sunshine_hours_sum": (g["sunshine_duration"].sum() / 3600.0),
        })
    weather_m = pd.DataFrame(rows)

    # Hourly-derived humidity and intra-day feel variables
    hourly_m = hourly.groupby("month").agg(
        seoul_relative_humidity_mean_pct=("relative_humidity_2m", "mean"),
        seoul_relative_humidity_min_pct=("relative_humidity_2m", "min"),
        seoul_relative_humidity_max_pct=("relative_humidity_2m", "max"),
        seoul_hourly_temp_p95_c=("temperature_2m", lambda s: float(np.nanpercentile(s, 95))),
        seoul_hourly_apparent_temp_p95_c=("apparent_temperature", lambda s: float(np.nanpercentile(s, 95))),
        seoul_hourly_wind_speed_mean_kmh=("wind_speed_10m", "mean"),
        seoul_hourly_wind_speed_p95_kmh=("wind_speed_10m", lambda s: float(np.nanpercentile(s, 95))),
    ).reset_index()

    out = weather_m.merge(hourly_m, on="month", how="left")
    return out, metas[0]


def fetch_air_month(ym: str, station: str = AIR_STATION) -> dict[str, Any] | None:
    url = AIR_URL_TMPL.format(ym=ym, station=quote(station))
    js = get_json(url, timeout=30)
    block = js.get("MonthlyAverageAirQuality")
    if not block or block.get("RESULT", {}).get("CODE") != "INFO-000":
        return None
    rows = block.get("row") or []
    return rows[0] if rows else None


def aggregate_air(months: list[str]) -> pd.DataFrame:
    rows = []
    for m in months:
        ym = m.replace("-", "")
        row = fetch_air_month(ym)
        if row is None:
            rows.append({"month": m, "air_quality_station_nm": AIR_STATION, "air_quality_missing_flag": 1})
        else:
            # Seoul Open Data field names: NTDX NO2, OZON O3, CBMX CO, SPDX SO2, PM PM10, FPM PM2.5
            rows.append({
                "month": m,
                "air_quality_station_nm": row.get("MSRSTN_NM", AIR_STATION),
                "air_quality_missing_flag": 0,
                "seoul_air_no2_ppm": row.get("NTDX"),
                "seoul_air_o3_ppm": row.get("OZON"),
                "seoul_air_co_ppm": row.get("CBMX"),
                "seoul_air_so2_ppm": row.get("SPDX"),
                "seoul_pm10_ug_m3": row.get("PM"),
                "seoul_pm25_ug_m3": row.get("FPM"),
            })
        time.sleep(0.05)
    air = pd.DataFrame(rows)
    # Monthly average bad flags based on Korean daily average grade breakpoints; not counts of bad days.
    air["seoul_pm10_month_avg_bad_flag_gt80"] = (pd.to_numeric(air["seoul_pm10_ug_m3"], errors="coerce") > 80).astype("Int64")
    air["seoul_pm25_month_avg_bad_flag_gt35"] = (pd.to_numeric(air["seoul_pm25_ug_m3"], errors="coerce") > 35).astype("Int64")
    return air


def add_seasonality(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    dt = pd.to_datetime(out["month"] + "-01")
    out.insert(1, "year", dt.dt.year)
    out.insert(2, "month_num", dt.dt.month)
    out.insert(3, "quarter", dt.dt.quarter)
    out["month_sin_annual"] = np.sin(2 * math.pi * out["month_num"] / 12)
    out["month_cos_annual"] = np.cos(2 * math.pi * out["month_num"] / 12)
    out["is_winter_dec_feb"] = out["month_num"].isin([12, 1, 2]).astype(int)
    out["is_spring_mar_may"] = out["month_num"].isin([3, 4, 5]).astype(int)
    out["is_summer_jun_aug"] = out["month_num"].isin([6, 7, 8]).astype(int)
    out["is_autumn_sep_nov"] = out["month_num"].isin([9, 10, 11]).astype(int)
    out["is_summer_peak_jul_aug"] = out["month_num"].isin([7, 8]).astype(int)
    out["is_year_end_nov_dec"] = out["month_num"].isin([11, 12]).astype(int)
    out["is_school_vacation_approx_jan_feb_jul_aug"] = out["month_num"].isin([1, 2, 7, 8]).astype(int)
    out["data_source_weather"] = "Open-Meteo Historical Weather API; Seoul City Hall coordinates; ERA5/ECMWF reanalysis/model archive"
    out["data_source_air_quality"] = "Seoul Open Data MonthlyAverageAirQuality API; station=중구; sample-key one-station query"
    return out


def main() -> None:
    weather, meta = aggregate_weather()
    months = pd.period_range(f"{START_YEAR}-01", f"{END_YEAR}-12", freq="M").strftime("%Y-%m").tolist()
    # Ensure full month frame even if any API call returns sparse data.
    base = pd.DataFrame({"month": months})
    air = aggregate_air(months)
    final = base.merge(weather, on="month", how="left").merge(air, on="month", how="left")
    final = add_seasonality(final)

    # Stable, modeling-friendly ordering: IDs/seasonality first, then weather, then air/source.
    id_cols = [
        "month", "year", "month_num", "quarter", "days_in_month",
        "month_sin_annual", "month_cos_annual", "is_winter_dec_feb", "is_spring_mar_may",
        "is_summer_jun_aug", "is_autumn_sep_nov", "is_summer_peak_jul_aug",
        "is_year_end_nov_dec", "is_school_vacation_approx_jan_feb_jul_aug",
    ]
    source_cols = ["air_quality_station_nm", "air_quality_missing_flag", "data_source_weather", "data_source_air_quality"]
    other_cols = [c for c in final.columns if c not in id_cols + source_cols]
    final = final[id_cols + other_cols + source_cols]

    # Rounded enough for monthly modeling, no needless binary float noise.
    for col in final.select_dtypes(include=["float64", "float32"]).columns:
        final[col] = final[col].round(4)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Wrote {OUT} rows={len(final)} cols={len(final.columns)}")
    print(f"Open-Meteo grid metadata: {meta}")
    missing = final.isna().sum()
    missing = missing[missing > 0]
    if len(missing):
        print("Missing values:")
        print(missing.to_string())
    else:
        print("No missing values.")


if __name__ == "__main__":
    main()
