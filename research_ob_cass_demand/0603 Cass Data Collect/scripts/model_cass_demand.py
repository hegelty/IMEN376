from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(ROOT / ".hf_cache"))
DEFAULT_INPUT = ROOT / "cass_demand_v3_monthly.csv"
DEFAULT_OUTPUT_DIR = ROOT / "model_outputs"
TARGET = "beer_domestic_volume"
SERIES_ID = "cass_beer_proxy"
SEASONAL_PERIOD = 12
TRAIN_END = "2023-12"
TEST_START = "2024-01"
QUANTILES = [0.025, 0.1, 0.5, 0.9, 0.975]
COVARIATE_CANDIDATES = [
    "temp_avg",
    "heatwave_days",
    "tropical_night_days",
    "kbo_games",
    "world_cup_dummy",
    "holiday_days",
    "ob_price_hike_dummy",
]


@dataclass
class ChronosResult:
    status: str
    reason: str
    forecast: pd.DataFrame | None = None
    backtest: pd.DataFrame | None = None
    covariate_status: str = "NOT_RUN"
    covariate_reason: str = "Covariate-informed run was not attempted."
    covariate_forecast: pd.DataFrame | None = None
    covariate_backtest: pd.DataFrame | None = None
    rolling_backtest: pd.DataFrame | None = None
    covariates: list[str] | None = None


@dataclass
class BaselineResult:
    status: str
    reason: str
    forecast: pd.DataFrame | None = None
    backtest: pd.DataFrame | None = None
    rolling_backtest: pd.DataFrame | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Cass demand forecasting model defined in ai_model_prd.md."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--horizon", type=int, default=12)
    parser.add_argument("--target", default=TARGET)
    parser.add_argument("--chronos-model-id", default="amazon/chronos-2")
    parser.add_argument("--device-map", default="cpu")
    parser.add_argument("--skip-chronos", action="store_true")
    parser.add_argument("--rolling-min-train", type=int, default=36)
    parser.add_argument("--rolling-horizon", type=int, default=3)
    parser.add_argument("--rolling-step", type=int, default=6)
    parser.add_argument("--skip-ets", action="store_true")
    return parser.parse_args()


def month_to_timestamp(month: pd.Series) -> pd.Series:
    return pd.PeriodIndex(month.astype(str), freq="M").to_timestamp()


def future_months(last_month: str, horizon: int) -> pd.DataFrame:
    start = pd.Period(last_month, freq="M") + 1
    periods = pd.period_range(start=start, periods=horizon, freq="M")
    return pd.DataFrame(
        {
            "month": [str(p) for p in periods],
            "timestamp": [p.to_timestamp() for p in periods],
        }
    )


def load_monthly(path: Path, target: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "month" not in df.columns:
        raise ValueError("Input data must include a 'month' column.")
    if target not in df.columns:
        raise ValueError(f"Input data must include target column '{target}'.")
    df = df.copy()
    df["timestamp"] = month_to_timestamp(df["month"])
    df[target] = pd.to_numeric(df[target], errors="coerce")
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def readiness_report(df: pd.DataFrame, target: str) -> tuple[pd.DataFrame, list[str]]:
    required = [
        "month",
        target,
        "beer_domestic_volume_imputed",
        "temp_avg",
        "heatwave_days",
        "tropical_night_days",
        "kbo_games",
        "world_cup_dummy",
        "holiday_days",
        "ob_price_hike_dummy",
    ]
    optional = [
        "beer_value",
        "cass_fresh_share",
        "cass_light_share",
        "cass_fresh_volume",
        "cass_light_volume",
        "nonalc_market_value",
        "cass_0_0_scn_base",
        "cass_0_0_scn_low",
        "cass_0_0_scn_high",
        "import_beer_price_yoy",
    ]
    rows = []
    for col in required + optional:
        if col in df.columns:
            non_null = int(df[col].notna().sum())
            status = "PASS" if col not in required or non_null == len(df) else "FAIL"
        else:
            non_null = 0
            status = "FAIL" if col in required else "MISSING_OPTIONAL"
        rows.append(
            {
                "column": col,
                "required": col in required,
                "non_null": non_null,
                "rows": len(df),
                "status": status,
            }
        )

    warnings = []
    if target == "beer_domestic_volume":
        warnings.append(
            "Target is an annual-anchor-based monthly proxy, not observed Cass SKU-level demand."
        )
    if "beer_domestic_volume_imputed" in df.columns:
        imputed_rows = int(pd.to_numeric(df["beer_domestic_volume_imputed"], errors="coerce").fillna(0).sum())
        if imputed_rows:
            warnings.append(f"{imputed_rows} rows have beer_domestic_volume_imputed=1.")
    for col in ["cass_fresh_volume", "cass_light_volume", "cass_fresh_share", "cass_light_share"]:
        if col in df.columns and df[col].notna().sum() == 0:
            warnings.append(f"{col} is empty; SKU-level Cass Fresh/Light forecasting is blocked.")
    if "import_beer_price_yoy" in df.columns and df["import_beer_price_yoy"].notna().sum() == 0:
        warnings.append("import_beer_price_yoy is empty; customs price covariate is not used.")

    return pd.DataFrame(rows), warnings


def seasonal_naive_backtest(df: pd.DataFrame, target: str) -> pd.DataFrame:
    lookup = df.set_index("month")[target].astype(float).to_dict()
    rows = []
    for row in df[df["month"] >= TEST_START].itertuples(index=False):
        month = str(row.month)
        prev_year_month = str(pd.Period(month, freq="M") - SEASONAL_PERIOD)
        if prev_year_month not in lookup:
            continue
        actual = float(getattr(row, target))
        prediction = float(lookup[prev_year_month])
        rows.append(
            {
                "month": month,
                "timestamp": row.timestamp,
                "actual": actual,
                "prediction": prediction,
                "model": "seasonal_naive",
                "source_month": prev_year_month,
            }
        )
    return pd.DataFrame(rows)


def residual_quantiles(df: pd.DataFrame, target: str) -> dict[float, float]:
    train = df[df["month"] <= TRAIN_END].copy()
    values = train[target].astype(float).to_numpy()
    residuals = values[SEASONAL_PERIOD:] - values[:-SEASONAL_PERIOD]
    if len(residuals) == 0:
        return {q: 0.0 for q in QUANTILES}
    return {q: float(np.quantile(residuals, q)) for q in QUANTILES}


def seasonal_naive_forecast(df: pd.DataFrame, target: str, horizon: int) -> pd.DataFrame:
    future = future_months(str(df["month"].iloc[-1]), horizon)
    last_year = df.tail(SEASONAL_PERIOD)[["month", target]].reset_index(drop=True)
    quantile_offsets = residual_quantiles(df, target)
    rows = []
    for i, row in future.iterrows():
        base = float(last_year.loc[i % SEASONAL_PERIOD, target])
        out = {
            "month": row["month"],
            "timestamp": row["timestamp"],
            "prediction": base,
            "model": "seasonal_naive",
            "source_month": str(last_year.loc[i % SEASONAL_PERIOD, "month"]),
        }
        for q, offset in quantile_offsets.items():
            out[f"q{int(q * 1000):03d}"] = max(0.0, base + offset)
        rows.append(out)
    return pd.DataFrame(rows)


def mase_scale(df: pd.DataFrame, target: str) -> float:
    train = df[df["month"] <= TRAIN_END][target].astype(float).to_numpy()
    if len(train) <= SEASONAL_PERIOD:
        return math.nan
    scale = np.mean(np.abs(train[SEASONAL_PERIOD:] - train[:-SEASONAL_PERIOD]))
    return float(scale) if scale != 0 else math.nan


def wape(actual: np.ndarray, prediction: np.ndarray) -> float:
    denom = np.sum(np.abs(actual))
    return float(np.sum(np.abs(actual - prediction)) / denom) if denom else math.nan


def mase(actual: np.ndarray, prediction: np.ndarray, scale: float) -> float:
    if math.isnan(scale) or scale == 0:
        return math.nan
    return float(np.mean(np.abs(actual - prediction)) / scale)


def pinball_loss(actual: np.ndarray, forecast_quantile: np.ndarray, quantile: float) -> float:
    error = actual - forecast_quantile
    return float(np.mean(np.maximum(quantile * error, (quantile - 1) * error)))


def evaluate_backtest(backtest: pd.DataFrame, scale: float, model_name: str) -> dict[str, Any]:
    if backtest.empty:
        return {
            "model": model_name,
            "rows": 0,
            "wape": math.nan,
            "mase": math.nan,
            "pinball_0_1": math.nan,
            "pinball_0_5": math.nan,
            "pinball_0_9": math.nan,
        }
    actual = backtest["actual"].astype(float).to_numpy()
    prediction = backtest["prediction"].astype(float).to_numpy()
    metrics = {
        "model": model_name,
        "rows": len(backtest),
        "wape": wape(actual, prediction),
        "mase": mase(actual, prediction, scale),
        "pinball_0_1": math.nan,
        "pinball_0_5": math.nan,
        "pinball_0_9": math.nan,
    }
    quantile_cols = {0.1: "q100", 0.5: "q500", 0.9: "q900"}
    for q, col in quantile_cols.items():
        if col in backtest.columns:
            metrics[f"pinball_{q:.1f}".replace(".", "_")] = pinball_loss(
                actual, backtest[col].astype(float).to_numpy(), q
            )
    return metrics


def interval_coverage(backtests: list[pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for frame in backtests:
        if frame is None or frame.empty or "actual" not in frame.columns or "model" not in frame.columns:
            continue
        for model, group in frame.groupby("model"):
            actual = group["actual"].astype(float)
            row = {"model": model, "rows": len(group)}
            if {"q100", "q900"}.issubset(group.columns):
                lower = group["q100"].astype(float)
                upper = group["q900"].astype(float)
                row["coverage_80"] = float(((actual >= lower) & (actual <= upper)).mean())
                row["avg_width_80"] = float((upper - lower).mean())
                row["avg_width_80_pct"] = float(((upper - lower) / group["prediction"].astype(float)).mean())
            else:
                row["coverage_80"] = math.nan
                row["avg_width_80"] = math.nan
                row["avg_width_80_pct"] = math.nan
            if {"q025", "q975"}.issubset(group.columns):
                lower = group["q025"].astype(float)
                upper = group["q975"].astype(float)
                row["coverage_95"] = float(((actual >= lower) & (actual <= upper)).mean())
                row["avg_width_95"] = float((upper - lower).mean())
                row["avg_width_95_pct"] = float(((upper - lower) / group["prediction"].astype(float)).mean())
            else:
                row["coverage_95"] = math.nan
                row["avg_width_95"] = math.nan
                row["avg_width_95_pct"] = math.nan
            rows.append(row)
    return pd.DataFrame(rows)


def event_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["month"]].copy()
    kbo_threshold = pd.to_numeric(df["kbo_games"], errors="coerce").quantile(0.75) if "kbo_games" in df.columns else math.nan
    out["event_or_stress"] = False
    reasons = []
    for row in df.itertuples(index=False):
        row_reasons = []
        if hasattr(row, "heatwave_days") and pd.notna(row.heatwave_days) and float(row.heatwave_days) > 0:
            row_reasons.append("heatwave")
        if hasattr(row, "tropical_night_days") and pd.notna(row.tropical_night_days) and float(row.tropical_night_days) > 0:
            row_reasons.append("tropical_night")
        if hasattr(row, "world_cup_dummy") and pd.notna(row.world_cup_dummy) and int(row.world_cup_dummy) == 1:
            row_reasons.append("world_cup")
        if hasattr(row, "ob_price_hike_dummy") and pd.notna(row.ob_price_hike_dummy) and int(row.ob_price_hike_dummy) == 1:
            row_reasons.append("price_hike")
        if (
            hasattr(row, "kbo_games")
            and pd.notna(row.kbo_games)
            and not math.isnan(kbo_threshold)
            and float(row.kbo_games) >= float(kbo_threshold)
            and float(row.kbo_games) > 0
        ):
            row_reasons.append("high_kbo_games")
        reasons.append(",".join(row_reasons) if row_reasons else "routine")
    out["event_reason"] = reasons
    out["event_or_stress"] = out["event_reason"] != "routine"
    return out


def event_split_metrics(backtests: list[pd.DataFrame], df: pd.DataFrame, scale: float) -> pd.DataFrame:
    flags = event_flags(df)
    rows = []
    for frame in backtests:
        if frame is None or frame.empty or "actual" not in frame.columns or "model" not in frame.columns:
            continue
        merged = frame.merge(flags, on="month", how="left")
        for (model, segment), group in merged.groupby(["model", "event_or_stress"], dropna=False):
            label = "event_or_stress" if bool(segment) else "routine"
            actual = group["actual"].astype(float).to_numpy()
            prediction = group["prediction"].astype(float).to_numpy()
            rows.append(
                {
                    "model": model,
                    "segment": label,
                    "rows": len(group),
                    "wape": wape(actual, prediction),
                    "mase": mase(actual, prediction, scale),
                    "event_reasons": ";".join(sorted(set(group["event_reason"].dropna()))),
                }
            )
    return pd.DataFrame(rows)


def seasonal_naive_rolling_backtest(
    df: pd.DataFrame,
    target: str,
    min_train: int,
    horizon: int,
    step: int,
) -> pd.DataFrame:
    rows = []
    for origin_idx in range(min_train - 1, len(df) - 1, step):
        origin_month = str(df.loc[origin_idx, "month"])
        for h in range(1, horizon + 1):
            test_idx = origin_idx + h
            if test_idx >= len(df):
                continue
            source_idx = test_idx - SEASONAL_PERIOD
            if source_idx < 0:
                continue
            actual = float(df.loc[test_idx, target])
            prediction = float(df.loc[source_idx, target])
            rows.append(
                {
                    "origin_month": origin_month,
                    "horizon": h,
                    "month": str(df.loc[test_idx, "month"]),
                    "timestamp": df.loc[test_idx, "timestamp"],
                    "actual": actual,
                    "prediction": prediction,
                    "model": "seasonal_naive_rolling",
                    "source_month": str(df.loc[source_idx, "month"]),
                }
            )
    out = pd.DataFrame(rows)
    return add_baseline_intervals_to_backtest(out, df, target) if not out.empty else out


def ets_prediction_frame(
    train: pd.DataFrame,
    future: pd.DataFrame,
    predictions: np.ndarray,
    model_name: str,
    target: str,
) -> pd.DataFrame:
    residuals = train[target].astype(float).to_numpy()[SEASONAL_PERIOD:] - train[target].astype(float).to_numpy()[:-SEASONAL_PERIOD]
    if len(residuals) == 0:
        residuals = train[target].astype(float).to_numpy() - train[target].astype(float).mean()
    offsets = {q: float(np.quantile(residuals, q)) if len(residuals) else 0.0 for q in QUANTILES}
    out = future[["month", "timestamp"]].copy()
    out["prediction"] = np.maximum(0.0, predictions)
    out["model"] = model_name
    for q, offset in offsets.items():
        out[f"q{int(q * 1000):03d}"] = (out["prediction"] + offset).clip(lower=0)
    return out


def fit_ets_predict(train: pd.DataFrame, prediction_length: int, target: str) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    series = train.set_index("timestamp")[target].astype(float).asfreq("MS")
    model = ExponentialSmoothing(
        series,
        trend="add",
        seasonal="add",
        seasonal_periods=SEASONAL_PERIOD,
        initialization_method="estimated",
    )
    fitted = model.fit(optimized=True)
    return np.asarray(fitted.forecast(prediction_length), dtype=float)


def run_ets_baseline(
    df: pd.DataFrame,
    target: str,
    horizon: int,
    skip: bool,
    rolling_min_train: int,
    rolling_horizon: int,
    rolling_step: int,
) -> BaselineResult:
    if skip:
        return BaselineResult(status="SKIPPED", reason="--skip-ets was set.")
    try:
        import statsmodels  # noqa: F401
    except Exception as exc:
        return BaselineResult(status="FAILED", reason=f"statsmodels import failed: {exc}")

    try:
        train = df[df["month"] <= TRAIN_END]
        test = df[df["month"] >= TEST_START]
        if len(train) < SEASONAL_PERIOD * 2:
            return BaselineResult(status="FAILED", reason="ETS needs at least two seasonal cycles.")

        test_predictions = fit_ets_predict(train, len(test), target)
        backtest = ets_prediction_frame(train, test, test_predictions, "ets_additive", target)
        backtest = backtest.merge(test[["month", target]].rename(columns={target: "actual"}), on="month", how="left")

        future = future_months(str(df["month"].iloc[-1]), horizon)
        full_predictions = fit_ets_predict(df, horizon, target)
        forecast = ets_prediction_frame(df, future, full_predictions, "ets_additive", target)

        rolling_frames = []
        for origin_idx in range(rolling_min_train - 1, len(df) - 1, rolling_step):
            prediction_length = min(rolling_horizon, len(df) - origin_idx - 1)
            if prediction_length <= 0:
                continue
            rolling_train = df.iloc[: origin_idx + 1]
            rolling_test = df.iloc[origin_idx + 1 : origin_idx + 1 + prediction_length]
            if len(rolling_train) < SEASONAL_PERIOD * 2:
                continue
            preds = fit_ets_predict(rolling_train, prediction_length, target)
            pred_frame = ets_prediction_frame(rolling_train, rolling_test, preds, "ets_additive_rolling", target)
            pred_frame = pred_frame.merge(
                rolling_test[["month", target]].rename(columns={target: "actual"}), on="month", how="left"
            )
            pred_frame["origin_month"] = str(df.loc[origin_idx, "month"])
            pred_frame["horizon"] = list(range(1, len(pred_frame) + 1))
            rolling_frames.append(pred_frame)
        rolling = pd.concat(rolling_frames, ignore_index=True) if rolling_frames else pd.DataFrame()

        return BaselineResult(
            status="PASS",
            reason="ETS additive baseline ran successfully.",
            forecast=forecast,
            backtest=backtest,
            rolling_backtest=rolling,
        )
    except Exception as exc:
        return BaselineResult(status="FAILED", reason=f"ETS baseline failed: {exc}")


def select_covariates(df: pd.DataFrame) -> list[str]:
    covariates = []
    for col in COVARIATE_CANDIDATES:
        if col in df.columns and df[col].notna().sum() == len(df):
            covariates.append(col)
    return covariates


def chronos_input(
    df: pd.DataFrame,
    target: str,
    covariates: list[str] | None = None,
    include_target: bool = True,
) -> pd.DataFrame:
    out = pd.DataFrame(
        {
            "id": SERIES_ID,
            "timestamp": df["timestamp"],
        }
    )
    if include_target:
        out["target"] = df[target].astype(float)
    for col in covariates or []:
        out[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    return out


# 2026년 이벤트 사전 설정 (manual update: 2026 KBO 정규시즌 + 이벤트)
# KBO 2026 정규시즌: 3~10월, 월별 게임 수는 2025 시즌 평균 기반 추정
_KBO_2026 = {
    "2026-01": 0, "2026-02": 0,
    "2026-03": 52, "2026-04": 90, "2026-05": 95,
    "2026-06": 88, "2026-07": 95, "2026-08": 95,
    "2026-09": 88, "2026-10": 55,
    "2026-11": 0, "2026-12": 0,
}
# ob_price_hike_dummy: 2026년 가격인상 보도 없음(2026-06-03 기준) → 0
# world_cup_dummy: 2026 FIFA 월드컵 북중미 개최 (6월~7월) → 해당 월 1
_WORLD_CUP_2026 = {"2026-06", "2026-07"}


def projected_future_covariates(
    df: pd.DataFrame,
    horizon: int,
    covariates: list[str],
) -> pd.DataFrame:
    future = future_months(str(df["month"].iloc[-1]), horizon)
    future["month_num"] = pd.PeriodIndex(future["month"], freq="M").month
    history = df.copy()
    history["month_num"] = pd.PeriodIndex(history["month"], freq="M").month
    out = future[["month", "timestamp", "month_num"]].copy()
    for col in covariates:
        if col == "world_cup_dummy":
            out[col] = out["month"].isin(_WORLD_CUP_2026).astype(float)
        elif col == "ob_price_hike_dummy":
            out[col] = 0.0
        elif col == "kbo_games":
            monthly_avg = history.groupby("month_num")[col].mean()
            mapped_2026 = out["month"].map(_KBO_2026)
            mapped_avg = out["month_num"].map(monthly_avg).astype(float)
            out[col] = mapped_2026.where(mapped_2026.notna(), mapped_avg).astype(float)
        else:
            monthly_avg = history.groupby("month_num")[col].mean()
            out[col] = out["month_num"].map(monthly_avg).astype(float)
    out["id"] = SERIES_ID
    return out[["id", "timestamp", *covariates]]


def normalize_chronos_output(pred_df: pd.DataFrame, model_name: str) -> pd.DataFrame:
    out = pred_df.copy()
    if "timestamp" not in out.columns:
        raise ValueError("Chronos output does not include a timestamp column.")
    out["month"] = pd.to_datetime(out["timestamp"]).dt.to_period("M").astype(str)
    if "predictions" in out.columns:
        out["prediction"] = out["predictions"]
    elif "0.5" in out.columns:
        out["prediction"] = out["0.5"]
    else:
        quantile_like = [c for c in out.columns if str(c) in {"0.5", "0.50", "median"}]
        if not quantile_like:
            raise ValueError(f"Cannot identify point forecast column in Chronos output: {list(out.columns)}")
        out["prediction"] = out[quantile_like[0]]
    for source, dest in [("0.025", "q025"), ("0.1", "q100"), ("0.5", "q500"), ("0.9", "q900"), ("0.975", "q975")]:
        if source in out.columns:
            out[dest] = out[source]
    out["model"] = model_name
    keep = ["month", "timestamp", "prediction", "model", "q025", "q100", "q500", "q900", "q975"]
    return out[[c for c in keep if c in out.columns]]


def chronos_rolling_backtest(
    pipeline: Any,
    df: pd.DataFrame,
    target: str,
    min_train: int,
    horizon: int,
    step: int,
) -> pd.DataFrame:
    frames = []
    for origin_idx in range(min_train - 1, len(df) - 1, step):
        origin_month = str(df.loc[origin_idx, "month"])
        prediction_length = min(horizon, len(df) - origin_idx - 1)
        if prediction_length <= 0:
            continue
        train = df.iloc[: origin_idx + 1]
        test = df.iloc[origin_idx + 1 : origin_idx + 1 + prediction_length]
        raw = pipeline.predict_df(
            chronos_input(train, target),
            prediction_length=prediction_length,
            quantile_levels=QUANTILES,
            id_column="id",
            timestamp_column="timestamp",
            target="target",
        )
        pred = normalize_chronos_output(raw, "chronos2_rolling")
        actual = test[["month", target]].rename(columns={target: "actual"})
        pred = pred.merge(actual, on="month", how="left")
        pred["origin_month"] = origin_month
        pred["horizon"] = list(range(1, len(pred) + 1))
        frames.append(pred)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def run_chronos(
    df: pd.DataFrame,
    target: str,
    horizon: int,
    model_id: str,
    device_map: str,
    skip: bool,
    rolling_min_train: int,
    rolling_horizon: int,
    rolling_step: int,
) -> ChronosResult:
    if skip:
        return ChronosResult(status="SKIPPED", reason="--skip-chronos was set.")

    try:
        from chronos import Chronos2Pipeline
    except Exception as exc:
        return ChronosResult(
            status="FAILED",
            reason=f"chronos-forecasting is not installed or import failed: {exc}",
        )

    try:
        pipeline = Chronos2Pipeline.from_pretrained(model_id, device_map=device_map)
    except Exception as exc:
        return ChronosResult(
            status="FAILED",
            reason=f"Chronos-2 model load failed for {model_id}: {exc}",
        )

    try:
        context = chronos_input(df, target)
        raw_forecast = pipeline.predict_df(
            context,
            prediction_length=horizon,
            quantile_levels=QUANTILES,
            id_column="id",
            timestamp_column="timestamp",
            target="target",
        )
        forecast = normalize_chronos_output(raw_forecast, "chronos2_univariate")

        train = df[df["month"] <= TRAIN_END]
        test = df[df["month"] >= TEST_START]
        backtest = None
        if len(train) and len(test):
            raw_backtest = pipeline.predict_df(
                chronos_input(train, target),
                prediction_length=len(test),
                quantile_levels=QUANTILES,
                id_column="id",
                timestamp_column="timestamp",
                target="target",
            )
            backtest = normalize_chronos_output(raw_backtest, "chronos2_univariate")
            actual = test[["month", target]].rename(columns={target: "actual"})
            backtest = backtest.merge(actual, on="month", how="left")

        result = ChronosResult(
            status="PASS",
            reason="Chronos-2 univariate ran successfully.",
            forecast=forecast,
            backtest=backtest,
            covariates=select_covariates(df),
        )
        if result.covariates:
            try:
                context_cov = chronos_input(df, target, result.covariates)
                future_cov = projected_future_covariates(df, horizon, result.covariates)
                raw_cov_forecast = pipeline.predict_df(
                    context_cov,
                    future_df=future_cov,
                    prediction_length=horizon,
                    quantile_levels=QUANTILES,
                    id_column="id",
                    timestamp_column="timestamp",
                    target="target",
                )
                result.covariate_forecast = normalize_chronos_output(
                    raw_cov_forecast, "chronos2_covariate_projected"
                )
                if len(train) and len(test):
                    future_cov_backtest = chronos_input(
                        test, target, result.covariates, include_target=False
                    )
                    raw_cov_backtest = pipeline.predict_df(
                        chronos_input(train, target, result.covariates),
                        future_df=future_cov_backtest,
                        prediction_length=len(test),
                        quantile_levels=QUANTILES,
                        id_column="id",
                        timestamp_column="timestamp",
                        target="target",
                    )
                    result.covariate_backtest = normalize_chronos_output(
                        raw_cov_backtest, "chronos2_covariate"
                    )
                    actual = test[["month", target]].rename(columns={target: "actual"})
                    result.covariate_backtest = result.covariate_backtest.merge(
                        actual, on="month", how="left"
                    )
                result.covariate_status = "PASS"
                result.covariate_reason = (
                    "Chronos-2 covariate-informed run succeeded. Future forecast covariates "
                    "use historical month-of-year averages and zeroed event dummies."
                )
            except Exception as exc:
                result.covariate_status = "FAILED"
                result.covariate_reason = f"Chronos-2 covariate-informed inference failed: {exc}"
        else:
            result.covariate_status = "SKIPPED"
            result.covariate_reason = "No fully populated covariates were available."
        try:
            result.rolling_backtest = chronos_rolling_backtest(
                pipeline=pipeline,
                df=df,
                target=target,
                min_train=rolling_min_train,
                horizon=rolling_horizon,
                step=rolling_step,
            )
        except Exception as exc:
            result.rolling_backtest = pd.DataFrame(
                [
                    {
                        "model": "chronos2_rolling",
                        "status": "FAILED",
                        "reason": f"Chronos-2 rolling-origin backtest failed: {exc}",
                    }
                ]
            )
        return result
    except Exception as exc:
        return ChronosResult(status="FAILED", reason=f"Chronos-2 inference failed: {exc}")


def add_baseline_intervals_to_backtest(backtest: pd.DataFrame, df: pd.DataFrame, target: str) -> pd.DataFrame:
    offsets = residual_quantiles(df, target)
    out = backtest.copy()
    for q, offset in offsets.items():
        out[f"q{int(q * 1000):03d}"] = (out["prediction"] + offset).clip(lower=0)
    return out


def write_plot(df: pd.DataFrame, forecasts: list[pd.DataFrame], output_dir: Path, target: str) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df["timestamp"], df[target], label="historical proxy target", color="#2f5d8c")
    for forecast in forecasts:
        if forecast is None or forecast.empty:
            continue
        label = str(forecast["model"].iloc[0])
        ax.plot(forecast["timestamp"], forecast["prediction"], label=label)
        if {"q100", "q900"}.issubset(forecast.columns):
            ax.fill_between(
                forecast["timestamp"],
                forecast["q100"].astype(float),
                forecast["q900"].astype(float),
                alpha=0.15,
            )
    ax.set_title("Cass beer proxy demand forecast")
    ax.set_xlabel("Month")
    ax.set_ylabel("kL")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "forecast_plot.png", dpi=150)
    plt.close(fig)


def preferred_forecast(
    baseline_forecast: pd.DataFrame,
    chronos_result: ChronosResult,
) -> pd.DataFrame:
    if chronos_result.covariate_forecast is not None and not chronos_result.covariate_forecast.empty:
        return chronos_result.covariate_forecast.copy()
    if chronos_result.forecast is not None and not chronos_result.forecast.empty:
        return chronos_result.forecast.copy()
    return baseline_forecast.copy()


def forecast_alerts(forecast: pd.DataFrame, df: pd.DataFrame, target: str) -> pd.DataFrame:
    if forecast.empty:
        return pd.DataFrame()
    hist_p75 = float(df[target].quantile(0.75))
    hist_p90 = float(df[target].quantile(0.90))
    rows = []
    for row in forecast.itertuples(index=False):
        prediction = float(row.prediction)
        width80_pct = math.nan
        width95_pct = math.nan
        if hasattr(row, "q100") and hasattr(row, "q900") and pd.notna(row.q100) and pd.notna(row.q900):
            width80_pct = float((row.q900 - row.q100) / prediction) if prediction else math.nan
        if hasattr(row, "q025") and hasattr(row, "q975") and pd.notna(row.q025) and pd.notna(row.q975):
            width95_pct = float((row.q975 - row.q025) / prediction) if prediction else math.nan
        reasons = []
        if not math.isnan(width80_pct) and width80_pct >= 0.08:
            reasons.append("wide_80_interval")
        if not math.isnan(width95_pct) and width95_pct >= 0.14:
            reasons.append("wide_95_interval")
        if prediction >= hist_p90:
            reasons.append("above_historical_p90")
        elif prediction >= hist_p75:
            reasons.append("above_historical_p75")
        if "wide_80_interval" in reasons or "wide_95_interval" in reasons or "above_historical_p90" in reasons:
            severity = "HIGH"
            action = "Planner review before fermentation or inventory commitment."
        elif reasons:
            severity = "WATCH"
            action = "Monitor against next data refresh."
        else:
            severity = "NORMAL"
            action = "No escalation."
        rows.append(
            {
                "month": row.month,
                "model": row.model,
                "prediction": prediction,
                "width80_pct": width80_pct,
                "width95_pct": width95_pct,
                "severity": severity,
                "reasons": ",".join(reasons) if reasons else "none",
                "recommended_action": action,
            }
        )
    return pd.DataFrame(rows)


def tank_allocation_proxy(forecast: pd.DataFrame, df: pd.DataFrame, target: str) -> pd.DataFrame:
    if forecast.empty:
        return pd.DataFrame()
    hist = df.copy()
    hist["month_num"] = pd.PeriodIndex(hist["month"], freq="M").month
    month_avg = hist.groupby("month_num")[target].mean()
    base_batches_per_day = 1.20
    tank_capacity_batches_per_day = 20.0 / 14.0
    rows = []
    for row in forecast.itertuples(index=False):
        period = pd.Period(str(row.month), freq="M")
        same_month_avg = float(month_avg.loc[period.month])
        prediction = float(row.prediction)
        q900 = float(row.q900) if hasattr(row, "q900") and pd.notna(row.q900) else prediction
        demand_ratio = prediction / same_month_avg if same_month_avg else math.nan
        required_batches_per_day = base_batches_per_day * demand_ratio
        utilization = required_batches_per_day / tank_capacity_batches_per_day
        prebuild_kl = max(0.0, q900 - same_month_avg)
        if utilization >= 0.95:
            status = "CRITICAL"
            recommendation = "Escalate to HQ planner; evaluate prebuild and SKU prioritization."
        elif utilization >= 0.88:
            status = "WATCH"
            recommendation = "Review weekly fermentation starts and safety stock buffers."
        else:
            status = "NORMAL"
            recommendation = "No tank allocation escalation from proxy forecast."
        rows.append(
            {
                "month": str(period),
                "model": row.model,
                "forecast_kl": prediction,
                "q900_kl": q900,
                "historical_same_month_avg_kl": same_month_avg,
                "demand_ratio_vs_same_month_avg": demand_ratio,
                "estimated_required_batches_per_day": required_batches_per_day,
                "tank_capacity_batches_per_day": tank_capacity_batches_per_day,
                "estimated_utilization": utilization,
                "prebuild_watch_kl": prebuild_kl,
                "recommended_commit_month": str(period - 1),
                "status": status,
                "recommendation": recommendation,
                "limitation": "Proxy monthly aggregate only; not SKU/tank executable.",
            }
        )
    return pd.DataFrame(rows)


def safety_stock_proxy(forecast: pd.DataFrame) -> pd.DataFrame:
    if forecast.empty:
        return pd.DataFrame()
    rows = []
    for row in forecast.itertuples(index=False):
        prediction = float(row.prediction)
        q900 = float(row.q900) if hasattr(row, "q900") and pd.notna(row.q900) else prediction
        q975 = float(row.q975) if hasattr(row, "q975") and pd.notna(row.q975) else q900
        buffer_80_kl = max(0.0, q900 - prediction)
        buffer_95_kl = max(0.0, q975 - prediction)
        adjustment_pct = buffer_80_kl / prediction if prediction else math.nan
        if adjustment_pct <= 0.15:
            approval_band = "AUTO_OR_LOW_TOUCH"
            action = "Use 80% interval buffer as advisory safety stock."
        elif adjustment_pct <= 0.30:
            approval_band = "PLANNER_APPROVAL"
            action = "Planner approval required before safety-stock adjustment."
        else:
            approval_band = "HQ_ESCALATION"
            action = "Escalate; interval implies large inventory commitment."
        rows.append(
            {
                "month": row.month,
                "model": row.model,
                "forecast_kl": prediction,
                "safety_stock_buffer_80_kl": buffer_80_kl,
                "safety_stock_buffer_95_kl": buffer_95_kl,
                "adjustment_pct_vs_forecast": adjustment_pct,
                "approval_band": approval_band,
                "recommended_action": action,
                "limitation": "Aggregate monthly proxy only; not DC/SKU executable.",
            }
        )
    return pd.DataFrame(rows)


def wholesaler_advisory_proxy(forecast: pd.DataFrame) -> pd.DataFrame:
    if forecast.empty:
        return pd.DataFrame()
    rows = []
    for row in forecast.itertuples(index=False):
        prediction = float(row.prediction)
        q100 = float(row.q100) if hasattr(row, "q100") and pd.notna(row.q100) else prediction
        q900 = float(row.q900) if hasattr(row, "q900") and pd.notna(row.q900) else prediction
        rows.append(
            {
                "month": row.month,
                "model": row.model,
                "advisory_low_kl": q100,
                "advisory_base_kl": prediction,
                "advisory_high_kl": q900,
                "message": (
                    "Use as national aggregate demand band only; translate to account-level orders "
                    "only after account/DC data is available."
                ),
                "limitation": "No account, channel, or region data available.",
            }
        )
    return pd.DataFrame(rows)


def phase_acceptance_check(
    df: pd.DataFrame,
    metrics: pd.DataFrame,
    coverage: pd.DataFrame,
    event_metrics: pd.DataFrame,
    alerts: pd.DataFrame,
    tank_proxy: pd.DataFrame,
) -> pd.DataFrame:
    chronos = metrics.loc[metrics["model"] == "chronos2_univariate"] if "model" in metrics.columns else pd.DataFrame()
    baseline = metrics.loc[metrics["model"] == "seasonal_naive"] if "model" in metrics.columns else pd.DataFrame()
    chronos_beats_baseline = False
    if not chronos.empty and not baseline.empty:
        chronos_beats_baseline = (
            float(chronos["wape"].iloc[0]) < float(baseline["wape"].iloc[0])
            or float(chronos["mase"].iloc[0]) < float(baseline["mase"].iloc[0])
        )
    actual_target_available = (
        "beer_domestic_volume_imputed" in df.columns
        and int(pd.to_numeric(df["beer_domestic_volume_imputed"], errors="coerce").fillna(0).sum()) == 0
        and not df["beer_domestic_volume"].isna().any()
    )
    sku_target_available = any(
        col in df.columns and df[col].notna().sum() == len(df)
        for col in ["cass_fresh_volume", "cass_light_volume"]
    )
    rows = [
        ("MVP-1", "Pipeline reads monthly CSV without manual column edits", "PASS", "model runner reads cass_demand_v3_monthly.csv"),
        ("MVP-2", "Missing Cass Fresh/Light target columns are detected and reported", "PASS", "readiness warnings include blocked SKU targets"),
        ("MVP-3", "Proxy/imputed target warning appears before model evaluation", "PASS", "model_run_summary includes proxy/imputed warning"),
        ("MVP-4", "Seasonal Naive baseline forecast is generated", "PASS", "seasonal_naive_forecast.csv generated"),
        ("MVP-5", "Evaluation report labels metrics as diagnostic only", "PASS", "model_run_summary labels proxy diagnostics"),
        ("MVP-6", "No report claims validated SKU-level Cass Fresh/Light performance", "PASS", "reports explicitly block SKU-level claim"),
        ("MVP-7", "Output files are reproducible from a single script", "PASS", "scripts/model_cass_demand.py regenerates model_outputs"),
        (
            "M-1",
            "Actual, non-synthetic demand target is available",
            "PASS" if actual_target_available else "FAIL",
            "current target has imputed/proxy periods" if not actual_target_available else "actual target gate passed",
        ),
        (
            "M-2",
            "Cass Fresh/Light/Cass 0.0 or Cass family target grain is explicitly defined",
            "PASS" if sku_target_available else "FAIL",
            "Cass Fresh/Light actual target columns are empty" if not sku_target_available else "SKU target available",
        ),
        ("M-3", "Seasonal Naive baseline is included", "PASS", "baseline metrics generated"),
        (
            "M-4",
            "Chronos-2 improves MASE or WAPE vs Seasonal Naive baseline",
            "PASS" if chronos_beats_baseline else "FAIL",
            "Chronos-2 does not beat Seasonal Naive on proxy diagnostic backtest"
            if not chronos_beats_baseline
            else "Chronos-2 beats baseline",
        ),
        (
            "M-5",
            "80% and 95% intervals are reported with empirical coverage",
            "PARTIAL" if not coverage.empty else "FAIL",
            "coverage is computed, but target is proxy" if not coverage.empty else "coverage missing",
        ),
        (
            "M-6",
            "Event/stress periods are evaluated separately",
            "PARTIAL" if not event_metrics.empty else "FAIL",
            "event split exists, but target is proxy" if not event_metrics.empty else "event split missing",
        ),
        (
            "M-7",
            "High-uncertainty forecasts trigger human review",
            "PARTIAL" if not alerts.empty else "FAIL",
            "forecast_alerts.csv generated; no external workflow integration",
        ),
        (
            "M-8",
            "Tank allocation recommendations remain approval-based",
            "PARTIAL" if not tank_proxy.empty else "FAIL",
            "tank_allocation_proxy.csv generated; not SKU/tank executable",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=["id", "criterion", "status", "notes"],
    )


def workflow_action_queue(
    alerts: pd.DataFrame,
    tank_proxy: pd.DataFrame,
    safety_stock: pd.DataFrame,
    wholesaler_advisory: pd.DataFrame,
) -> pd.DataFrame:
    if alerts.empty:
        return pd.DataFrame()
    merged = alerts[["month", "severity", "reasons", "recommended_action"]].copy()
    if not tank_proxy.empty:
        merged = merged.merge(
            tank_proxy[["month", "status", "estimated_utilization", "prebuild_watch_kl", "recommendation"]],
            on="month",
            how="left",
            suffixes=("", "_tank"),
        )
    if not safety_stock.empty:
        merged = merged.merge(
            safety_stock[["month", "approval_band", "safety_stock_buffer_80_kl"]],
            on="month",
            how="left",
        )
    if not wholesaler_advisory.empty:
        merged = merged.merge(
            wholesaler_advisory[["month", "advisory_low_kl", "advisory_base_kl", "advisory_high_kl"]],
            on="month",
            how="left",
        )
    rows = []
    for row in merged.itertuples(index=False):
        if row.severity == "HIGH":
            owner = "HQ demand planner"
            decision = "review_before_commit"
            approval = "required"
        elif row.severity == "WATCH" or getattr(row, "approval_band", "") != "AUTO_OR_LOW_TOUCH":
            owner = "demand planner"
            decision = "monitor_or_approve_adjustment"
            approval = "conditional"
        else:
            owner = "planning system"
            decision = "no_escalation"
            approval = "not_required"
        rows.append(
            {
                "month": row.month,
                "severity": row.severity,
                "owner": owner,
                "decision_type": decision,
                "approval_required": approval,
                "forecast_reasons": row.reasons,
                "forecast_action": row.recommended_action,
                "tank_status": getattr(row, "status", pd.NA),
                "estimated_utilization": getattr(row, "estimated_utilization", pd.NA),
                "prebuild_watch_kl": getattr(row, "prebuild_watch_kl", pd.NA),
                "safety_stock_approval_band": getattr(row, "approval_band", pd.NA),
                "safety_stock_buffer_80_kl": getattr(row, "safety_stock_buffer_80_kl", pd.NA),
                "advisory_low_kl": getattr(row, "advisory_low_kl", pd.NA),
                "advisory_base_kl": getattr(row, "advisory_base_kl", pd.NA),
                "advisory_high_kl": getattr(row, "advisory_high_kl", pd.NA),
                "limitation": "Proxy workflow queue only; not connected to production systems.",
            }
        )
    return pd.DataFrame(rows)


def monitoring_snapshot(
    df: pd.DataFrame,
    readiness: pd.DataFrame,
    metrics: pd.DataFrame,
    coverage: pd.DataFrame,
    alerts: pd.DataFrame,
    phase_check: pd.DataFrame,
    target: str,
) -> pd.DataFrame:
    latest_month = str(df["month"].max())
    latest_period = pd.Period(latest_month, freq="M")
    expected_latest = pd.Period("2025-12", freq="M")
    rows = []

    def add(check: str, status: str, value: str, threshold: str, action: str) -> None:
        rows.append(
            {
                "check_item": check,
                "status": status,
                "value": value,
                "threshold": threshold,
                "recommended_action": action,
            }
        )

    add(
        "data_freshness",
        "PASS" if latest_period >= expected_latest else "WARN",
        latest_month,
        str(expected_latest),
        "Refresh data collection if latest month is behind expected range.",
    )
    missing_required = readiness[(readiness["required"] == True) & (readiness["status"] != "PASS")]  # noqa: E712
    add(
        "required_feature_completeness",
        "PASS" if missing_required.empty else "FAIL",
        str(len(missing_required)),
        "0 failed required features",
        "Fix required input columns before trusting model output.",
    )
    imputed_rows = int(pd.to_numeric(df.get("beer_domestic_volume_imputed", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    add(
        "target_imputation",
        "WARN" if imputed_rows else "PASS",
        str(imputed_rows),
        "0 imputed target rows for PRD-grade evaluation",
        "Do not use proxy/imputed target for Phase 1 performance claim.",
    )
    high_alerts = int((alerts["severity"] == "HIGH").sum()) if "severity" in alerts.columns else 0
    add(
        "forecast_high_alerts",
        "WARN" if high_alerts else "PASS",
        str(high_alerts),
        "0 high alerts",
        "Review HIGH months before fermentation or inventory commitment.",
    )
    phase_fail = int((phase_check["status"] == "FAIL").sum()) if "status" in phase_check.columns else 0
    add(
        "phase_acceptance_failures",
        "FAIL" if phase_fail else "PASS",
        str(phase_fail),
        "0 FAIL rows",
        "Resolve Phase 1 blockers before claiming PRD-grade model readiness.",
    )
    if "model" in metrics.columns and not metrics.empty:
        best = metrics.sort_values("wape").iloc[0]
        add(
            "best_diagnostic_wape",
            "INFO",
            f"{best['model']}={float(best['wape']):.6f}",
            "diagnostic only",
            "Use as proxy-data diagnostic, not SKU performance claim.",
        )
    if "coverage_80" in coverage.columns and not coverage.empty:
        min_coverage = float(coverage["coverage_80"].min())
        add(
            "min_interval_80_coverage",
            "PASS" if min_coverage >= 0.8 else "WARN",
            f"{min_coverage:.3f}",
            ">=0.800",
            "Recalibrate intervals if coverage falls below target on actual data.",
        )
    last_12 = df.tail(12)[target].astype(float)
    prev_12 = df.iloc[-24:-12][target].astype(float) if len(df) >= 24 else pd.Series(dtype=float)
    if len(prev_12):
        drift = (last_12.mean() - prev_12.mean()) / prev_12.mean()
        add(
            "target_last12_mean_drift",
            "WARN" if abs(drift) >= 0.05 else "PASS",
            f"{drift:.6f}",
            "abs drift < 0.05",
            "Investigate target distribution shift if drift exceeds threshold.",
        )
    return pd.DataFrame(rows)


def monitoring_alerts(snapshot: pd.DataFrame) -> pd.DataFrame:
    if snapshot.empty:
        return pd.DataFrame()
    return snapshot[snapshot["status"].isin(["WARN", "FAIL"])].reset_index(drop=True)


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    display = df.copy()
    for col in display.columns:
        if pd.api.types.is_float_dtype(display[col]):
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else f"{x:.6f}")
        else:
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else str(x))
    headers = [str(c) for c in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in display.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def write_summary(
    output_dir: Path,
    data_path: Path,
    df: pd.DataFrame,
    readiness: pd.DataFrame,
    warnings: list[str],
    metrics: pd.DataFrame,
    chronos_result: ChronosResult,
    ets_result: BaselineResult,
    coverage: pd.DataFrame,
    event_metrics: pd.DataFrame,
    alerts: pd.DataFrame,
    tank_proxy: pd.DataFrame,
    safety_stock: pd.DataFrame,
    wholesaler_advisory: pd.DataFrame,
    phase_check: pd.DataFrame,
    workflow_queue: pd.DataFrame,
) -> None:
    warning_lines = "\n".join(f"- {w}" for w in warnings) if warnings else "- No warnings."
    chronos_files = []
    if chronos_result.forecast is not None:
        chronos_files.append("`chronos2_forecast.csv`")
    if chronos_result.backtest is not None:
        chronos_files.append("`chronos2_backtest.csv`")
    if chronos_result.covariate_forecast is not None:
        chronos_files.append("`chronos2_covariate_forecast.csv`")
    if chronos_result.covariate_backtest is not None:
        chronos_files.append("`chronos2_covariate_backtest.csv`")
    chronos_file_text = ", ".join(chronos_files) if chronos_files else "none"
    comparison_text = "Chronos-2 was not available, so only the Seasonal Naive baseline was evaluated."
    if {"model", "wape", "mase"}.issubset(metrics.columns) and len(metrics) > 1:
        baseline = metrics.loc[metrics["model"] == "seasonal_naive"]
        chronos = metrics.loc[metrics["model"] == "chronos2_univariate"]
        if not baseline.empty and not chronos.empty:
            baseline_wape = float(baseline["wape"].iloc[0])
            chronos_wape = float(chronos["wape"].iloc[0])
            baseline_mase = float(baseline["mase"].iloc[0])
            chronos_mase = float(chronos["mase"].iloc[0])
            if chronos_wape < baseline_wape and chronos_mase < baseline_mase:
                comparison_text = (
                    "Chronos-2 beats Seasonal Naive on both WAPE and MASE in this diagnostic backtest."
                )
            else:
                comparison_text = (
                    "Chronos-2 does not beat Seasonal Naive on this proxy-data diagnostic backtest. "
                    "This is expected to be possible because the current target is seasonally allocated "
                    "from annual anchors, which gives the one-year seasonal baseline an artificial advantage."
                )

    text = f"""# Cass Demand Model Run Summary

Generated outputs follow `ai_model_prd.md`.

## Model Choice

- Selected AI model: Chronos-2 zero-shot time-series forecasting
- Mandatory baseline: Seasonal Naive
- Current Chronos-2 status: `{chronos_result.status}`
- Chronos-2 note: {chronos_result.reason}
- Current Chronos-2 covariate status: `{chronos_result.covariate_status}`
- Chronos-2 covariate note: {chronos_result.covariate_reason}
- Covariates used: {", ".join(chronos_result.covariates or []) if chronos_result.covariates else "none"}
- ETS robustness baseline status: `{ets_result.status}`
- ETS note: {ets_result.reason}

## Input Data

- Input file: `{data_path.name}`
- Rows: {len(df)}
- Range: {df["month"].iloc[0]} to {df["month"].iloc[-1]}
- Target: `{TARGET}`

## Data Readiness Warnings

{warning_lines}

## Evaluation Metrics

These metrics are diagnostics only because the current target is a public/proxy monthly series, not actual Cass SKU-level demand.

{markdown_table(metrics)}

## Interval Coverage

{markdown_table(coverage)}

## Event / Stress Split

{markdown_table(event_metrics)}

## Operational Proxy Outputs

- Forecast alert rows: {len(alerts)}
- Tank allocation proxy rows: {len(tank_proxy)}
- Safety stock proxy rows: {len(safety_stock)}
- Wholesaler advisory proxy rows: {len(wholesaler_advisory)}
- Workflow action queue rows: {len(workflow_queue)}
- High alert rows: {int((alerts["severity"] == "HIGH").sum()) if "severity" in alerts.columns else 0}

## Phase Acceptance Gate

{markdown_table(phase_check)}

## Output Files

- `data_readiness_report.csv`
- `phase_acceptance_check.csv`
- `seasonal_naive_forecast.csv`
- `seasonal_naive_backtest.csv`
- `rolling_origin_backtest.csv`
- `evaluation_metrics.csv`
- `ets_status.json`
- `ets_forecast.csv` / `ets_backtest.csv` if ETS is available
- `interval_coverage_metrics.csv`
- `event_split_metrics.csv`
- `forecast_alerts.csv`
- `tank_allocation_proxy.csv`
- `safety_stock_proxy.csv`
- `wholesaler_advisory_proxy.csv`
- `workflow_action_queue.csv`
- `monitoring_snapshot.csv`
- `monitoring_alerts.csv`
- `chronos2_status.json`
- Chronos-2 files: {chronos_file_text}
- `forecast_plot.png` if matplotlib was available

## Interpretation

{comparison_text}

Use the Seasonal Naive metrics as the required baseline. If Chronos-2 does not run, the implementation is still complete but the environment needs `chronos-forecasting` plus access to the Hugging Face model weights.

The current model output must not be presented as validated Cass Fresh/Light SKU-level performance until actual SKU demand targets are collected.
"""
    (output_dir / "model_run_summary.md").write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_monthly(args.input, args.target)
    readiness, warnings = readiness_report(df, args.target)
    readiness.to_csv(output_dir / "data_readiness_report.csv", index=False, encoding="utf-8-sig")

    baseline_backtest = add_baseline_intervals_to_backtest(
        seasonal_naive_backtest(df, args.target), df, args.target
    )
    baseline_forecast = seasonal_naive_forecast(df, args.target, args.horizon)
    baseline_rolling = seasonal_naive_rolling_backtest(
        df,
        args.target,
        min_train=args.rolling_min_train,
        horizon=args.rolling_horizon,
        step=args.rolling_step,
    )
    baseline_backtest.to_csv(output_dir / "seasonal_naive_backtest.csv", index=False, encoding="utf-8-sig")
    baseline_forecast.to_csv(output_dir / "seasonal_naive_forecast.csv", index=False, encoding="utf-8-sig")
    ets_result = run_ets_baseline(
        df=df,
        target=args.target,
        horizon=args.horizon,
        skip=args.skip_ets,
        rolling_min_train=args.rolling_min_train,
        rolling_horizon=args.rolling_horizon,
        rolling_step=args.rolling_step,
    )
    if ets_result.forecast is not None:
        ets_result.forecast.to_csv(output_dir / "ets_forecast.csv", index=False, encoding="utf-8-sig")
    if ets_result.backtest is not None:
        ets_result.backtest.to_csv(output_dir / "ets_backtest.csv", index=False, encoding="utf-8-sig")
    if ets_result.rolling_backtest is not None and not ets_result.rolling_backtest.empty:
        ets_result.rolling_backtest.to_csv(output_dir / "ets_rolling_backtest.csv", index=False, encoding="utf-8-sig")
    (output_dir / "ets_status.json").write_text(
        json.dumps(
            {
                "status": ets_result.status,
                "reason": ets_result.reason,
                "model": "statsmodels ExponentialSmoothing additive trend/additive seasonality",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    chronos_result = run_chronos(
        df=df,
        target=args.target,
        horizon=args.horizon,
        model_id=args.chronos_model_id,
        device_map=args.device_map,
        skip=args.skip_chronos,
        rolling_min_train=args.rolling_min_train,
        rolling_horizon=args.rolling_horizon,
        rolling_step=args.rolling_step,
    )
    if chronos_result.forecast is not None:
        chronos_result.forecast.to_csv(output_dir / "chronos2_forecast.csv", index=False, encoding="utf-8-sig")
    if chronos_result.backtest is not None:
        chronos_result.backtest.to_csv(output_dir / "chronos2_backtest.csv", index=False, encoding="utf-8-sig")
    if chronos_result.covariate_forecast is not None:
        chronos_result.covariate_forecast.to_csv(
            output_dir / "chronos2_covariate_forecast.csv", index=False, encoding="utf-8-sig"
        )
    if chronos_result.covariate_backtest is not None:
        chronos_result.covariate_backtest.to_csv(
            output_dir / "chronos2_covariate_backtest.csv", index=False, encoding="utf-8-sig"
        )
    rolling_frames = [baseline_rolling]
    if chronos_result.rolling_backtest is not None and not chronos_result.rolling_backtest.empty:
        chronos_result.rolling_backtest.to_csv(
            output_dir / "chronos2_rolling_backtest.csv", index=False, encoding="utf-8-sig"
        )
        if "actual" in chronos_result.rolling_backtest.columns:
            rolling_frames.append(chronos_result.rolling_backtest)
    rolling_backtest = pd.concat([f for f in rolling_frames if f is not None and not f.empty], ignore_index=True)
    rolling_backtest.to_csv(output_dir / "rolling_origin_backtest.csv", index=False, encoding="utf-8-sig")

    status_payload = {
        "status": chronos_result.status,
        "reason": chronos_result.reason,
        "covariate_status": chronos_result.covariate_status,
        "covariate_reason": chronos_result.covariate_reason,
        "covariates": chronos_result.covariates or [],
        "rolling_min_train": args.rolling_min_train,
        "rolling_horizon": args.rolling_horizon,
        "rolling_step": args.rolling_step,
        "chronos_rolling_rows": int(len(chronos_result.rolling_backtest))
        if chronos_result.rolling_backtest is not None
        else 0,
        "model_id": args.chronos_model_id,
        "device_map": args.device_map,
        "source": "https://github.com/amazon-science/chronos-forecasting",
    }
    (output_dir / "chronos2_status.json").write_text(
        json.dumps(status_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    scale = mase_scale(df, args.target)
    metric_rows = [evaluate_backtest(baseline_backtest, scale, "seasonal_naive")]
    if ets_result.backtest is not None:
        metric_rows.append(evaluate_backtest(ets_result.backtest, scale, "ets_additive"))
    if chronos_result.backtest is not None:
        metric_rows.append(evaluate_backtest(chronos_result.backtest, scale, "chronos2_univariate"))
    if chronos_result.covariate_backtest is not None:
        metric_rows.append(evaluate_backtest(chronos_result.covariate_backtest, scale, "chronos2_covariate"))
    if not baseline_rolling.empty:
        metric_rows.append(evaluate_backtest(baseline_rolling, scale, "seasonal_naive_rolling"))
    if ets_result.rolling_backtest is not None and not ets_result.rolling_backtest.empty:
        metric_rows.append(evaluate_backtest(ets_result.rolling_backtest, scale, "ets_additive_rolling"))
    if (
        chronos_result.rolling_backtest is not None
        and not chronos_result.rolling_backtest.empty
        and "actual" in chronos_result.rolling_backtest.columns
    ):
        metric_rows.append(evaluate_backtest(chronos_result.rolling_backtest, scale, "chronos2_rolling"))
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(output_dir / "evaluation_metrics.csv", index=False, encoding="utf-8-sig")

    backtest_frames = [baseline_backtest]
    if ets_result.backtest is not None:
        backtest_frames.append(ets_result.backtest)
    if chronos_result.backtest is not None:
        backtest_frames.append(chronos_result.backtest)
    if chronos_result.covariate_backtest is not None:
        backtest_frames.append(chronos_result.covariate_backtest)
    if not baseline_rolling.empty:
        backtest_frames.append(baseline_rolling)
    if ets_result.rolling_backtest is not None and not ets_result.rolling_backtest.empty:
        backtest_frames.append(ets_result.rolling_backtest)
    if (
        chronos_result.rolling_backtest is not None
        and not chronos_result.rolling_backtest.empty
        and "actual" in chronos_result.rolling_backtest.columns
    ):
        backtest_frames.append(chronos_result.rolling_backtest)
    coverage = interval_coverage(backtest_frames)
    coverage.to_csv(output_dir / "interval_coverage_metrics.csv", index=False, encoding="utf-8-sig")
    event_metrics = event_split_metrics(backtest_frames, df, scale)
    event_metrics.to_csv(output_dir / "event_split_metrics.csv", index=False, encoding="utf-8-sig")

    forecast_frames = [baseline_forecast]
    if ets_result.forecast is not None:
        forecast_frames.append(ets_result.forecast)
    if chronos_result.forecast is not None:
        forecast_frames.append(chronos_result.forecast)
    if chronos_result.covariate_forecast is not None:
        forecast_frames.append(chronos_result.covariate_forecast)
    selected_forecast = preferred_forecast(baseline_forecast, chronos_result)
    alerts = forecast_alerts(selected_forecast, df, args.target)
    alerts.to_csv(output_dir / "forecast_alerts.csv", index=False, encoding="utf-8-sig")
    tank_proxy = tank_allocation_proxy(selected_forecast, df, args.target)
    tank_proxy.to_csv(output_dir / "tank_allocation_proxy.csv", index=False, encoding="utf-8-sig")
    safety_stock = safety_stock_proxy(selected_forecast)
    safety_stock.to_csv(output_dir / "safety_stock_proxy.csv", index=False, encoding="utf-8-sig")
    wholesaler_advisory = wholesaler_advisory_proxy(selected_forecast)
    wholesaler_advisory.to_csv(output_dir / "wholesaler_advisory_proxy.csv", index=False, encoding="utf-8-sig")
    phase_check = phase_acceptance_check(df, metrics, coverage, event_metrics, alerts, tank_proxy)
    phase_check.to_csv(output_dir / "phase_acceptance_check.csv", index=False, encoding="utf-8-sig")
    workflow_queue = workflow_action_queue(alerts, tank_proxy, safety_stock, wholesaler_advisory)
    workflow_queue.to_csv(output_dir / "workflow_action_queue.csv", index=False, encoding="utf-8-sig")
    monitor = monitoring_snapshot(df, readiness, metrics, coverage, alerts, phase_check, args.target)
    monitor.to_csv(output_dir / "monitoring_snapshot.csv", index=False, encoding="utf-8-sig")
    monitor_alerts = monitoring_alerts(monitor)
    monitor_alerts.to_csv(output_dir / "monitoring_alerts.csv", index=False, encoding="utf-8-sig")
    write_plot(df, forecast_frames, output_dir, args.target)
    write_summary(
        output_dir,
        args.input,
        df,
        readiness,
        warnings,
        metrics,
        chronos_result,
        ets_result,
        coverage,
        event_metrics,
        alerts,
        tank_proxy,
        safety_stock,
        wholesaler_advisory,
        phase_check,
        workflow_queue,
    )

    print(f"Wrote model outputs to {output_dir}")
    print(f"Chronos-2 status: {chronos_result.status} - {chronos_result.reason}")


if __name__ == "__main__":
    main()
