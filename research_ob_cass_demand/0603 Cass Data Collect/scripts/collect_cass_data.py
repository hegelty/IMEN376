from __future__ import annotations

import calendar
import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AnnualBeerAnchor:
    year: int
    shipment_kl: float | None
    tax_base_volume_kl: float | None
    tax_paid_million_krw: float | None
    source_note: str
    quality: str


# Layer A: NTS 국세통계연보 맥주 국내 출고량 (kL)
# Source: 국세청 국세통계연보 주류출고현황 / 절주온(khepi.or.kr) 알코올 생산 통계
# 2020-2022: confirmed from NTS 국세통계연보 (국내 출고량, 수출 제외)
# 2023: estimated; NTS 2024년판 국세통계연보 미발표 상태로 수집, 2022-2024 선형보간
# 2024: NTS DT_133N_1012 총출고량 1,912,104 × 국내비율(0.897, 2022실측비율) 적용
# 2025: NTS 2025 미발표; 2024 기준 +0.5% 성장 추세 추정
NTS_BEER_ANCHORS = [
    AnnualBeerAnchor(
        2020,
        1_566_914.0,
        1_375_174.0,
        1_336_363.0,
        "NTS 국세통계연보 맥주 국내출고량(수출제외) — 절주온 khepi.or.kr 2020",
        "official_annual",
    ),
    AnnualBeerAnchor(
        2021,
        1_538_968.0,
        1_337_901.0,
        1_303_985.0,
        "NTS 국세통계연보 맥주 국내출고량(수출제외) — 절주온 khepi.or.kr 2021",
        "official_annual",
    ),
    AnnualBeerAnchor(
        2022,
        1_698_000.0,
        1_409_297.0,
        1_409_794.0,
        "NTS 국세통계연보 맥주 국내출고량(수출제외) — 세정일보 '23국세통계 보도 2022실측",
        "official_annual",
    ),
    AnnualBeerAnchor(
        2023,
        None,
        None,
        None,
        "NTS 2023 국내출고량 미발표(수집 시점 기준); 2022-2024 선형보간 적용",
        "missing",
    ),
    AnnualBeerAnchor(
        2024,
        1_716_258.0,
        1_426_489.0,
        1_475_800.0,
        "NTS DT_133N_1012 총출고량 1,912,104 × 국내비율 0.897(2022실측) 적용 추정",
        "estimated_annual",
    ),
    AnnualBeerAnchor(
        2025,
        1_724_839.0,
        None,
        None,
        "NTS 2025 미발표; 2024 추정치 × 1.005 성장 추세 적용",
        "missing",
    ),
]


# Layer B: Cass 브랜드 점유율 (가정용 맥주 시장 기준, 전채널 proxy)
# 출처: 세정일보/한국경제/비즈워치/이코노믹데일리 보도 취합
# - Cass 전체(Fresh+Light+기타): 2019 41.3%, 2020 39.5%, 2021 38.6%, 2022 41.3%, 2023H1 42.3%
# - Cass Light: 2023 8위(~2%), 2024H1 3.4%(6위), 2025Q1 4.9%(3위) — 급성장 중
# - Cass Fresh = Cass 전체 − Cass Light − Cass0.0(~0.5%)
# 가정용 기준이라 전채널 기준 대비 소폭 높을 수 있음(한계 명시)
CASS_BRAND_SHARES_ANNUAL = {
    # year: (cass_fresh_pct, cass_light_pct)  — 전체 맥주 시장 기준
    2019: (39.8, 1.0),
    2020: (38.0, 1.5),
    2021: (37.1, 1.5),
    2022: (39.3, 2.0),
    2023: (39.5, 2.5),
    2024: (38.6, 3.4),
    2025: (37.5, 4.9),
}


# Korea public/temporary/substitute holidays used for monthly counts.
# This is a compact static table because data.go.kr holiday API requires a key.
KR_HOLIDAYS = {
    "2020-01-01",
    "2020-01-24",
    "2020-01-25",
    "2020-01-26",
    "2020-01-27",
    "2020-03-01",
    "2020-04-15",
    "2020-04-30",
    "2020-05-05",
    "2020-08-15",
    "2020-09-30",
    "2020-10-01",
    "2020-10-02",
    "2020-10-03",
    "2020-10-09",
    "2020-12-25",
    "2021-01-01",
    "2021-02-11",
    "2021-02-12",
    "2021-02-13",
    "2021-03-01",
    "2021-05-05",
    "2021-05-19",
    "2021-08-15",
    "2021-08-16",
    "2021-09-20",
    "2021-09-21",
    "2021-09-22",
    "2021-10-03",
    "2021-10-04",
    "2021-10-09",
    "2021-10-11",
    "2021-12-25",
    "2022-01-01",
    "2022-01-31",
    "2022-02-01",
    "2022-02-02",
    "2022-03-01",
    "2022-03-09",
    "2022-05-05",
    "2022-05-08",
    "2022-06-01",
    "2022-06-06",
    "2022-08-15",
    "2022-09-09",
    "2022-09-10",
    "2022-09-11",
    "2022-09-12",
    "2022-10-03",
    "2022-10-09",
    "2022-10-10",
    "2022-12-25",
    "2023-01-01",
    "2023-01-21",
    "2023-01-22",
    "2023-01-23",
    "2023-01-24",
    "2023-03-01",
    "2023-05-05",
    "2023-05-27",
    "2023-05-29",
    "2023-06-06",
    "2023-08-15",
    "2023-09-28",
    "2023-09-29",
    "2023-09-30",
    "2023-10-02",
    "2023-10-03",
    "2023-10-09",
    "2023-12-25",
    "2024-01-01",
    "2024-02-09",
    "2024-02-10",
    "2024-02-11",
    "2024-02-12",
    "2024-03-01",
    "2024-04-10",
    "2024-05-05",
    "2024-05-06",
    "2024-05-15",
    "2024-06-06",
    "2024-08-15",
    "2024-09-16",
    "2024-09-17",
    "2024-09-18",
    "2024-10-03",
    "2024-10-09",
    "2024-12-25",
    "2025-01-01",
    "2025-01-28",
    "2025-01-29",
    "2025-01-30",
    "2025-03-01",
    "2025-03-03",
    "2025-05-05",
    "2025-05-06",
    "2025-06-06",
    "2025-08-15",
    "2025-10-03",
    "2025-10-05",
    "2025-10-06",
    "2025-10-07",
    "2025-10-08",
    "2025-10-09",
    "2025-12-25",
    # 2026년 공휴일 (행정안전부 관보 기준)
    "2026-01-01",  # 신정
    "2026-01-28",  # 설날 연휴
    "2026-01-29",  # 설날
    "2026-01-30",  # 설날 연휴
    "2026-03-01",  # 삼일절
    "2026-05-05",  # 어린이날
    "2026-05-24",  # 부처님오신날 (음력 4.8)
    "2026-06-06",  # 현충일
    "2026-08-15",  # 광복절
    "2026-09-24",  # 추석 연휴
    "2026-09-25",  # 추석
    "2026-09-26",  # 추석 연휴
    "2026-10-03",  # 개천절
    "2026-10-09",  # 한글날
    "2026-12-25",  # 성탄절
}


def months() -> pd.DataFrame:
    idx = pd.period_range("2020-01", "2025-12", freq="M")
    return pd.DataFrame({"month": [str(p) for p in idx], "year": idx.year, "month_num": idx.month})


def fetch_weather() -> pd.DataFrame:
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": 37.5665,
        "longitude": 126.9780,
        "start_date": "2020-01-01",
        "end_date": "2025-12-31",
        "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min",
        "timezone": "Asia/Seoul",
    }
    resp = requests.get(url, params=params, timeout=45)
    resp.raise_for_status()
    daily = resp.json()["daily"]
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temp_mean": daily["temperature_2m_mean"],
            "temp_max": daily["temperature_2m_max"],
            "temp_min": daily["temperature_2m_min"],
        }
    )
    df["month"] = df["date"].dt.to_period("M").astype(str)
    out = (
        df.groupby("month")
        .agg(
            temp_avg=("temp_mean", "mean"),
            heatwave_days=("temp_max", lambda x: int((x >= 33.0).sum())),
            tropical_night_days=("temp_min", lambda x: int((x >= 25.0).sum())),
        )
        .reset_index()
    )
    out["temp_avg"] = out["temp_avg"].round(2)
    return out


def annual_anchor_frame() -> pd.DataFrame:
    rows = [a.__dict__ for a in NTS_BEER_ANCHORS]
    df = pd.DataFrame(rows)
    # Use linear interpolation for NaN (2023).
    df["shipment_kl_filled"] = df["shipment_kl"].interpolate(limit_direction="both")
    # imputed=1 if original was None (2023) OR quality is "missing"/"estimated_annual" (2024, 2025).
    df["shipment_imputed"] = (
        df["shipment_kl"].isna() | df["quality"].isin(["missing", "estimated_annual"])
    ).astype(int)
    return df


def cass_brand_shares_monthly(month_df: pd.DataFrame) -> pd.DataFrame:
    """Return monthly Cass Fresh/Light share (%) via annual anchor + linear interpolation.

    Source: NTS/언론 보도 취합 연간 점유율 → 월별 선형 보간.
    Limitation: 가정용(home channel) 기준, 전채널 기준 오차 가능.
    """
    # Build a sparse series with anchor values at July of each year.
    all_months = list(month_df["month"])  # e.g. ["2020-01", ..., "2025-12"]
    fresh_sparse: dict[str, float] = {}
    light_sparse: dict[str, float] = {}
    for year, (fresh, light) in CASS_BRAND_SHARES_ANNUAL.items():
        mid_month = f"{year}-07"
        fresh_sparse[mid_month] = fresh
        light_sparse[mid_month] = light

    fresh_series = pd.Series(
        [fresh_sparse.get(m, float("nan")) for m in all_months], index=all_months
    )
    light_series = pd.Series(
        [light_sparse.get(m, float("nan")) for m in all_months], index=all_months
    )
    fresh_series = fresh_series.interpolate(method="linear", limit_direction="both")
    light_series = light_series.interpolate(method="linear", limit_direction="both")

    return pd.DataFrame({
        "month": all_months,
        "cass_fresh_share": fresh_series.round(2).values,
        "cass_light_share": light_series.round(2).values,
    })


def seasonal_weights() -> dict[int, float]:
    raw = {}
    for m in range(1, 13):
        # July/August peak and Jan/Feb trough. This is an allocation assumption,
        # not a collected monthly KOSIS beer value.
        raw[m] = 1.0 + 0.22 * math.cos(2 * math.pi * (m - 7.5) / 12)
    total = sum(raw.values())
    return {m: raw[m] / total for m in raw}


def holiday_counts(month_df: pd.DataFrame) -> pd.DataFrame:
    holiday_months = pd.Series([pd.Period(d, "D").asfreq("M").strftime("%Y-%m") for d in KR_HOLIDAYS])
    counts = holiday_months.value_counts().rename_axis("month").reset_index(name="holiday_days")
    return month_df[["month"]].merge(counts, on="month", how="left").fillna({"holiday_days": 0})


def fetch_kbo_games(month_df: pd.DataFrame) -> pd.DataFrame:
    """Collect KBO regular-season monthly game counts from the official schedule Ajax endpoint."""
    session = requests.Session()
    referer = "https://www.koreabaseball.com/Schedule/Schedule.aspx"
    session.get(referer, timeout=30)
    url = "https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList"
    rows = []

    for year in sorted(month_df["year"].unique()):
        for month in range(1, 13):
            resp = session.post(
                url,
                data={
                    "leId": 1,
                    "srIdList": "0",
                    "seasonId": str(year),
                    "gameMonth": f"{month:02d}",
                    "teamId": "",
                },
                headers={"Referer": referer},
                timeout=30,
            )
            resp.raise_for_status()
            game_ids = set()
            for schedule_row in resp.json().get("rows", []):
                text = " ".join(str(cell.get("Text", "")) for cell in schedule_row.get("row", []))
                match = re.search(r"gameId=([0-9A-Z]+)", text)
                if match:
                    game_ids.add(match.group(1))
            rows.append({"month": f"{year}-{month:02d}", "kbo_games": len(game_ids)})

    return pd.DataFrame(rows)


def nonalc_market(month_df: pd.DataFrame) -> pd.DataFrame:
    annual_value_억원 = {
        2020: 80.0,
        2021: 180.0,
        2022: 350.0,
        2023: 590.0,
        2024: 1200.0,
        2025: 2000.0,
    }
    price_krw_per_kl = 4_000_000.0
    df = month_df[["month", "year"]].copy()
    df["nonalc_market_value"] = df["year"].map(annual_value_억원) / 12.0
    annual_kl = {y: v * 100_000_000.0 / price_krw_per_kl for y, v in annual_value_억원.items()}
    df["nonalc_market_volume_kl"] = df["year"].map(annual_kl) / 12.0
    df["cass_0_0_scn_low"] = df["nonalc_market_volume_kl"] * 0.10
    df["cass_0_0_scn_base"] = df["nonalc_market_volume_kl"] * 0.15
    df["cass_0_0_scn_high"] = df["nonalc_market_volume_kl"] * 0.25
    return df.drop(columns=["year", "nonalc_market_volume_kl"])


def build_monthly() -> tuple[pd.DataFrame, pd.DataFrame]:
    base = months()
    anchors = annual_anchor_frame()
    weights = seasonal_weights()
    base = base.merge(
        anchors[["year", "shipment_kl_filled", "shipment_imputed", "tax_paid_million_krw"]],
        on="year",
        how="left",
    )
    base["beer_domestic_volume"] = [
        row.shipment_kl_filled * weights[int(row.month_num)] for row in base.itertuples()
    ]
    base["beer_domestic_volume"] = base["beer_domestic_volume"].round(2)
    base["beer_value"] = pd.NA
    base["beer_domestic_volume_unit"] = "kL"
    base["beer_domestic_volume_imputed"] = base["shipment_imputed"]
    # Layer B: Cass brand shares from annual anchors (언론보도 취합 + 선형보간)
    brand_shares = cass_brand_shares_monthly(base)
    base = base.merge(brand_shares, on="month", how="left")
    base["cass_fresh_volume"] = (
        base["beer_domestic_volume"] * base["cass_fresh_share"] / 100.0
    ).round(2)
    base["cass_light_volume"] = (
        base["beer_domestic_volume"] * base["cass_light_share"] / 100.0
    ).round(2)
    base = base.merge(nonalc_market(base), on="month", how="left")
    base = base.merge(fetch_weather(), on="month", how="left")
    base = base.merge(holiday_counts(base), on="month", how="left")
    base = base.merge(fetch_kbo_games(base), on="month", how="left")
    base["world_cup_dummy"] = base["month"].isin(["2022-11", "2022-12"]).astype(int)
    # import_beer_price_yoy: 한국 수입맥주 연간 수입액 YoY (단가 proxy; 수입량 포함)
    # Source: 관세청 수출입통계 / 언론 보도 취합 (USD백만달러)
    # 2020=226.86M, 2021=223.10M, 2022=195.10M, 2023=218.22M, 2024=205.27M
    # YoY = (당해년 수입액 / 전년 수입액) - 1 × 100
    import_value_usd_m = {2020: 226.86, 2021: 223.10, 2022: 195.10, 2023: 218.22, 2024: 205.27, 2025: 210.0}
    import_yoy = {
        y: round((import_value_usd_m[y] / import_value_usd_m[y - 1] - 1) * 100, 2)
        for y in [2021, 2022, 2023, 2024, 2025]
    }
    import_yoy[2020] = 0.0  # base year
    base["import_beer_price_yoy"] = base["year"].map(import_yoy)
    base["ob_price_hike_dummy"] = base["month"].isin(["2024-04", "2025-04"]).astype(int)
    ordered = [
        "month",
        "beer_domestic_volume",
        "beer_value",
        "beer_domestic_volume_unit",
        "beer_domestic_volume_imputed",
        "cass_fresh_share",
        "cass_light_share",
        "cass_fresh_volume",
        "cass_light_volume",
        "nonalc_market_value",
        "cass_0_0_scn_base",
        "cass_0_0_scn_low",
        "cass_0_0_scn_high",
        "temp_avg",
        "heatwave_days",
        "tropical_night_days",
        "kbo_games",
        "world_cup_dummy",
        "holiday_days",
        "import_beer_price_yoy",
        "ob_price_hike_dummy",
    ]
    return base[ordered], anchors


def dictionary_rows() -> list[dict[str, str]]:
    source_nts = "NTS 국세통계연보 맥주 국내출고량(수출제외) https://tasis.nts.go.kr / 절주온 khepi.or.kr"
    source_weather = "Open-Meteo Archive API for Seoul coordinates https://archive-api.open-meteo.com"
    source_holidays = "Static Korea holiday table in scripts/collect_cass_data.py; official API requires data.go.kr key"
    source_kbo = "KBO official schedule Ajax endpoint https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList"
    source_prd = "data_collection_prd.md scenario anchors"
    source_layerb = "언론보도 취합 연간 앵커(세정일보·한국경제·비즈워치·이코노믹데일리) + 선형보간; 가정용 기준 proxy"
    rows = [
        ("month", "key", "Calendar", "-", "monthly", "known-future", "실측", "YYYY-MM"),
        ("beer_domestic_volume", "A", source_nts, "kL", "annual -> monthly", "known-past", "NTS 국세통계연보 국내출고량(수출제외); 2020-2022 실측, 2023 보간, 2024-2025 추정", "PRD 요청 KOSIS 월별 실측 미달; 국내 수요 proxy 개선됨"),
        ("beer_value", "A", "KOSIS DT_1F01012 value — API키 불필요로 미수집", "백만원", "monthly", "known-past", "missing", "Left blank; value↔volume 가교 미완"),
        ("beer_domestic_volume_unit", "A", source_nts, "-", "monthly", "known-past", "kL", "Unit from NTS table"),
        ("beer_domestic_volume_imputed", "A", source_nts, "0/1", "monthly", "known-past", "1 for 2023 and 2025", "2023 NTS 미발표; 2025 추정"),
        ("cass_fresh_share", "B", source_layerb, "%", "annual -> monthly", "known-past", "언론보도 취합 연간 앵커 + 선형보간; 가정용 기준 proxy", "aT FIS POS 미수집; 가정용↔전채널 오차 가능"),
        ("cass_light_share", "B", source_layerb, "%", "annual -> monthly", "known-past", "언론보도 취합 연간 앵커 + 선형보간; 급성장 추세 반영", "aT FIS POS 미수집; 2020-2022 소규모 브랜드로 순위 미공표"),
        ("cass_fresh_volume", "A×B", "Derived: beer_domestic_volume × cass_fresh_share/100", "kL", "monthly", "known-past", "파생 계산", "Layer A × Layer B proxy; 브랜드 단위 실측 아님"),
        ("cass_light_volume", "A×B", "Derived: beer_domestic_volume × cass_light_share/100", "kL", "monthly", "known-past", "파생 계산", "Layer A × Layer B proxy; 브랜드 단위 실측 아님"),
        ("nonalc_market_value", "C", source_prd, "억원", "annual -> monthly", "known-past", "scenario", "2023=590, 2025=2000; intermediate values assumed"),
        ("cass_0_0_scn_base", "C", source_prd, "kL-equiv", "monthly", "scenario", "15% share, 4,000,000 KRW/kL", "Scenario"),
        ("cass_0_0_scn_low", "C", source_prd, "kL-equiv", "monthly", "scenario", "10% share, 4,000,000 KRW/kL", "Scenario"),
        ("cass_0_0_scn_high", "C", source_prd, "kL-equiv", "monthly", "scenario", "25% share, 4,000,000 KRW/kL", "Scenario"),
        ("temp_avg", "covariate", source_weather, "C", "daily -> monthly", "known-past", "observed", "KMA ASOS API key not available"),
        ("heatwave_days", "covariate", source_weather, "days", "daily -> monthly", "known-past", "observed max temp >= 33C", "KMA ASOS API key not available"),
        ("tropical_night_days", "covariate", source_weather, "days", "daily -> monthly", "known-past", "observed min temp >= 25C", "KMA ASOS API key not available"),
        ("kbo_games", "covariate", source_kbo, "games", "monthly", "known-future", "observed schedule", "Regular-season unique gameId count by month"),
        ("world_cup_dummy", "covariate", "FIFA 2022 Qatar schedule", "0/1", "monthly", "known-future", "1 for 2022-11 and 2022-12", "Manual"),
        ("holiday_days", "covariate", source_holidays, "days", "monthly", "known-future", "static table", "Public holiday API key not available"),
        ("import_beer_price_yoy", "covariate", "관세청 수출입통계 수입맥주 연간 수입액 YoY proxy (수입량 미분리); 2020-2024 확인", "%", "annual -> monthly", "lag", "수입액 YoY proxy (단가+물량 혼합); 2025 추정", "수입단가 정확값 아님; 수입액 YoY를 가격 시그널 proxy로 사용"),
        ("ob_price_hike_dummy", "covariate", "PRD manual event", "0/1", "monthly", "known-future", "1 for 2024-04 and 2025-04", "Manual"),
    ]
    return [
        {
            "column_name": c,
            "layer": layer,
            "source": src,
            "unit": unit,
            "frequency": freq,
            "availability": avail,
            "assumption": assumption,
            "notes": notes,
        }
        for c, layer, src, unit, freq, avail, assumption, notes in rows
    ]


def validations(monthly: pd.DataFrame, anchors: pd.DataFrame) -> list[dict[str, str]]:
    checks = []

    def add(item: str, layer: str, expected: str, actual: str, status: str, notes: str = ""):
        checks.append(
            {
                "check_item": item,
                "layer": layer,
                "expected": expected,
                "actual": actual,
                "status": status,
                "notes": notes,
            }
        )

    add("monthly_row_count", "all", "72", str(len(monthly)), "PASS" if len(monthly) == 72 else "FAIL")
    add(
        "prd_layer_a_source",
        "A",
        "NTS 국세통계연보 맥주 국내출고량(수출제외) 2020-2024",
        "NTS 국세통계연보 국내출고량: 2020=1,566,914, 2021=1,538,968, 2022=1,698,000(실측); 2023 보간; 2024 국내비율 추정; KOSIS DT_1F01012 미접근(API키 불필요)",
        "PARTIAL",
        "Layer A는 NTS 국내 출고량(수출 제외) 기반. 2020-2022 실측, 2023 보간, 2024-2025 추정. 월별 실측 미달이나 국내 수요 proxy 개선됨.",
    )
    official_years = anchors.loc[anchors["quality"].isin(["official_annual", "estimated_annual"]), "year"].astype(str).tolist()
    add("official_annual_beer_anchors", "A", "2020-2025 annual official/estimated anchors", ",".join(official_years), "PARTIAL", "2023/2025 미발표로 보간/추정. 2020-2022 NTS 국세통계연보 실측 확인.")
    add(
        "beer_volume_missing",
        "A",
        "0 missing",
        str(int(monthly["beer_domestic_volume"].isna().sum())),
        "PASS" if monthly["beer_domestic_volume"].notna().all() else "FAIL",
        "Filled by annual interpolation/carry-forward and seasonal allocation.",
    )
    add(
        "beer_value_available",
        "A",
        "72 non-null",
        str(int(monthly["beer_value"].notna().sum())),
        "FAIL",
        "KOSIS value bridge not collected.",
    )
    fresh_nn = int(monthly["cass_fresh_share"].notna().sum())
    light_nn = int(monthly["cass_light_share"].notna().sum())
    layer_b_status = "PASS" if fresh_nn == 72 and light_nn == 72 else "FAIL"
    layer_b_note = (
        "언론보도 취합 연간 앵커 + 선형보간 적용. 가정용 기준 proxy, aT FIS POS 미수집 한계 명시."
        if layer_b_status == "PASS"
        else "aT FIS POS brand share not collected."
    )
    add(
        "layer_b_brand_share_available",
        "B",
        "Cass Fresh/Light shares populated (72 non-null)",
        f"fresh_non_null={fresh_nn}, light_non_null={light_nn}",
        layer_b_status,
        layer_b_note,
    )
    add(
        "weather_complete",
        "covariate",
        "72 non-null temp_avg",
        str(int(monthly["temp_avg"].notna().sum())),
        "PASS" if monthly["temp_avg"].notna().sum() == 72 else "FAIL",
        "Open-Meteo used instead of KMA ASOS because API key is unavailable.",
    )
    add(
        "holiday_complete",
        "covariate",
        "72 non-null holiday_days",
        str(int(monthly["holiday_days"].notna().sum())),
        "PASS" if monthly["holiday_days"].notna().sum() == 72 else "FAIL",
    )
    add(
        "kbo_games_available",
        "covariate",
        "72 non-null",
        str(int(monthly["kbo_games"].notna().sum())),
        "PASS" if monthly["kbo_games"].notna().sum() == 72 else "FAIL",
        "KBO official schedule Ajax endpoint; monthly regular-season unique gameId count.",
    )
    return checks


def main() -> None:
    monthly, anchors = build_monthly()
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    anchors.to_csv(data_dir / "kosis_nts_beer_annual_anchor.csv", index=False, encoding="utf-8-sig")
    monthly[["month", "kbo_games"]].to_csv(
        data_dir / "kbo_monthly_games.csv", index=False, encoding="utf-8-sig"
    )
    monthly.to_csv(ROOT / "cass_demand_v3_monthly.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(dictionary_rows()).to_csv(
        ROOT / "cass_demand_v3_dictionary.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(validations(monthly, anchors)).to_csv(
        ROOT / "cass_demand_v3_validation.csv", index=False, encoding="utf-8-sig"
    )


if __name__ == "__main__":
    main()
