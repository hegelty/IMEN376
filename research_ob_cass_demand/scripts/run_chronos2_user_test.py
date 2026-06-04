import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from chronos import BaseChronosPipeline

BASE = Path('/home/hegelty/programming/IMEN343/research_ob_cass_demand')
DATA_PATH = BASE / 'data' / 'final_cass_demand_model_dataset_with_exogenous_2020_2025.csv'
OUT_DIR = BASE / 'model_outputs_chronos2_user_test'
OUT_DIR.mkdir(exist_ok=True)

TARGET = 'alcoholic_beer_total_proxy_kl'
ID_COL = 'item_id'
TS_COL = 'timestamp'
ITEM_ID = 'cass_total'

COVARIATES = [
    'seoul_avg_temp_c',
    'seoul_heatwave_warning_days_33c',
    'seoul_tropical_nights_25c',
    'kbo_regular_games',
    'sports_major_event_days',
    'public_holiday_count_kr',
    'ob_major_price_increase_event_dummy',
]

QUANTILES = [0.1, 0.5, 0.9]


def mase(actual, pred, train_series, seasonality=12):
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    train_series = np.asarray(train_series, dtype=float)
    denom = np.mean(np.abs(train_series[seasonality:] - train_series[:-seasonality]))
    return np.mean(np.abs(actual - pred)) / denom


def wape(actual, pred):
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    return np.sum(np.abs(actual - pred)) / np.sum(np.abs(actual))


def rmse(actual, pred):
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    return float(np.sqrt(np.mean((actual - pred) ** 2)))


def prepare_data():
    df = pd.read_csv(DATA_PATH)
    df['month'] = pd.to_datetime(df['month'])
    cols = ['month', TARGET] + COVARIATES
    df = df[cols].copy()
    df[ID_COL] = ITEM_ID
    df = df.rename(columns={'month': TS_COL, TARGET: 'target'})
    return df


def seasonal_naive(test_df, context_df):
    hist = context_df.set_index(TS_COL)['target']
    preds = []
    for ts in test_df[TS_COL]:
        prev = ts - pd.DateOffset(years=1)
        preds.append(float(hist.loc[prev]))
        hist.loc[ts] = float(test_df.loc[test_df[TS_COL] == ts, 'target'].iloc[0])
    return np.array(preds, dtype=float)


def main():
    df = prepare_data()
    train_df = df[df[TS_COL] < pd.Timestamp('2024-01-01')].copy()
    test_df = df[df[TS_COL] >= pd.Timestamp('2024-01-01')].copy()

    context_df = train_df[[ID_COL, TS_COL, 'target'] + COVARIATES].copy()
    future_df = test_df[[ID_COL, TS_COL] + COVARIATES].copy()

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'Using device: {device}')
    if device == 'cuda':
        print(f'GPU: {torch.cuda.get_device_name(0)}')
    pipeline = BaseChronosPipeline.from_pretrained('amazon/chronos-2', device_map=device)

    pred_df = pipeline.predict_df(
        context_df,
        future_df=future_df,
        prediction_length=len(test_df),
        quantile_levels=QUANTILES,
        id_column=ID_COL,
        timestamp_column=TS_COL,
        target='target',
    )

    merged = pred_df.merge(
        test_df[[ID_COL, TS_COL, 'target']],
        on=[ID_COL, TS_COL],
        how='left',
        suffixes=('', '_actual')
    )
    merged = merged.rename(columns={'target': 'actual', 'predictions': 'prediction'})

    naive_pred = seasonal_naive(test_df[[TS_COL, 'target']].copy(), train_df[[TS_COL, 'target']].copy())
    naive_df = test_df[[TS_COL, 'target']].copy()
    naive_df['prediction'] = naive_pred
    naive_df['model'] = 'seasonal_naive'

    chronos_eval = merged[[TS_COL, 'actual', 'prediction']].copy()
    chronos_eval['model'] = 'chronos2_covariate'
    chronos_eval['month'] = chronos_eval[TS_COL].dt.strftime('%Y-%m')
    naive_df['month'] = naive_df[TS_COL].dt.strftime('%Y-%m')
    naive_df = naive_df.rename(columns={'target': 'actual'})

    event_mask = (
        (test_df['seoul_heatwave_warning_days_33c'] > 0)
        | (test_df['seoul_tropical_nights_25c'] > 0)
        | (test_df['kbo_regular_games'] >= 100)
        | (test_df['sports_major_event_days'] > 0)
    ).to_numpy()

    train_series = train_df['target'].to_numpy()
    rows = []
    for name, g in [('chronos2_covariate', chronos_eval), ('seasonal_naive', naive_df)]:
        for split, mask in [
            ('all_test', np.ones(len(g), dtype=bool)),
            ('event_months', event_mask),
            ('normal_months', ~event_mask),
        ]:
            actual = g.loc[mask, 'actual'].to_numpy()
            pred = g.loc[mask, 'prediction'].to_numpy()
            rows.append({
                'model': name,
                'split': split,
                'n_months': int(mask.sum()),
                'MASE': mase(actual, pred, train_series),
                'WAPE': wape(actual, pred),
                'RMSE': rmse(actual, pred),
            })

    metrics = pd.DataFrame(rows)
    merged['month'] = merged[TS_COL].dt.strftime('%Y-%m')

    merged.to_csv(OUT_DIR / 'chronos2_predictions_vs_actual.csv', index=False)
    metrics.to_csv(OUT_DIR / 'chronos2_metrics.csv', index=False)
    with open(OUT_DIR / 'chronos2_summary.json', 'w', encoding='utf-8') as f:
        json.dump({
            'data_path': str(DATA_PATH),
            'target': TARGET,
            'covariates': COVARIATES,
            'train_months': int(len(train_df)),
            'test_months': int(len(test_df)),
            'quantiles': QUANTILES,
        }, f, ensure_ascii=False, indent=2)

    print(metrics.to_string(index=False))
    print('\nSaved to', OUT_DIR)


if __name__ == '__main__':
    main()
