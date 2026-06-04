import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from chronos import BaseChronosPipeline

BASE = Path('/home/hegelty/programming/IMEN343/research_ob_cass_demand')
DATA_PATH = BASE / 'final_adjusted_target_model_outputs' / 'integrated_dataset_with_adjusted_target.csv'
OUT_DIR = BASE / 'final_adjusted_target_model_outputs'
TARGET = 'beer_domestic_volume_adjusted_leakage_safe'
TEST_START = pd.Timestamp('2024-01-01')

# Chronos covariates: no Google Trends, no target-adjustment signals, no lag/rolling target-derived vars.
COVARIATES = [
    'month_sin_annual', 'month_cos_annual', 'month_num', 'quarter',
    'is_summer_peak_jul_aug', 'is_year_end_nov_dec',
    'cass_fresh_share', 'cass_light_share',
    'news_total_index', 'news_sentiment_balance_proxy',
    'news_beer_general_count', 'news_cass_ob_count', 'news_nonalc_count',
    'news_weather_demand_count', 'news_festival_beer_count',
    'regional_festival_count_planned', 'regional_festival_days_est',
    'beer_festival_count_keyword', 'beer_festival_days_est_keyword',
    'korea_cpi_generated_yoy_pct', 'imported_beer_unit_value_yoy_pct',
    'months_since_ob_price_event_cap6',
    'seoul_precipitation_mm', 'seoul_rain_days', 'seoul_pm10_ug_m3', 'seoul_pm25_ug_m3',
    'public_holiday_weekday_count_kr', 'nonworking_days_weekend_or_holiday',
    'long_weekend_3plus_days_in_month', 'kbo_postseason_games',
]


def mase(actual, pred, train_series, seasonality=12):
    denom = np.mean(np.abs(train_series[seasonality:] - train_series[:-seasonality]))
    return float(np.mean(np.abs(np.asarray(actual)-np.asarray(pred))) / denom)


def wape(actual, pred):
    return float(np.sum(np.abs(np.asarray(actual)-np.asarray(pred))) / np.sum(np.abs(actual)))


def rmse(actual, pred):
    return float(np.sqrt(np.mean((np.asarray(actual)-np.asarray(pred))**2)))


def main():
    df = pd.read_csv(DATA_PATH)
    df['month'] = pd.to_datetime(df['month'])
    for c in COVARIATES:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

    work = df[['month', TARGET] + COVARIATES].rename(columns={'month': 'timestamp', TARGET: 'target'}).copy()
    work['item_id'] = 'cass_total_adjusted'
    train = work[work['timestamp'] < TEST_START].copy()
    test = work[work['timestamp'] >= TEST_START].copy()
    context_df = train[['item_id', 'timestamp', 'target'] + COVARIATES]
    future_df = test[['item_id', 'timestamp'] + COVARIATES]

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print('Using device:', device)
    pipe = BaseChronosPipeline.from_pretrained('amazon/chronos-2', device_map=device)
    pred = pipe.predict_df(
        context_df,
        future_df=future_df,
        prediction_length=len(test),
        quantile_levels=[0.1, 0.5, 0.9],
        id_column='item_id',
        timestamp_column='timestamp',
        target='target',
    )
    merged = pred.merge(test[['item_id','timestamp','target']], on=['item_id','timestamp'], how='left')
    merged = merged.rename(columns={'target':'actual','predictions':'prediction'})
    merged['month'] = merged['timestamp'].dt.strftime('%Y-%m')
    merged.to_csv(OUT_DIR / 'chronos2_adjusted_target_predictions.csv', index=False)

    train_series = train['target'].to_numpy()
    metrics = pd.DataFrame([{
        'model': 'chronos2_adjusted_target',
        'split': 'all_test',
        'n_months': len(merged),
        'MASE': mase(merged['actual'], merged['prediction'], train_series),
        'WAPE': wape(merged['actual'], merged['prediction']),
        'RMSE': rmse(merged['actual'], merged['prediction']),
    }])
    metrics.to_csv(OUT_DIR / 'chronos2_adjusted_target_metrics.csv', index=False)
    print(metrics.to_string(index=False))


if __name__ == '__main__':
    main()
