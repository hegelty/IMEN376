import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path('/home/hegelty/programming/IMEN343/research_ob_cass_demand')
OURS_PATH = BASE / 'data' / 'final_cass_demand_model_dataset_with_exogenous_2020_2025.csv'
COLLECT_PATH = BASE / '0603 Cass Data Collect' / 'cass_demand_v3_monthly.csv'
CHRONOS_BT_PATH = BASE / '0603 Cass Data Collect' / 'model_outputs' / 'chronos2_covariate_backtest.csv'
CHRONOS_FC_PATH = BASE / '0603 Cass Data Collect' / 'model_outputs' / 'chronos2_covariate_forecast.csv'
OUT_DIR = BASE / 'final_integrated_model_outputs'
OUT_DIR.mkdir(exist_ok=True)

TARGET = 'beer_domestic_volume'
ALPHAS = [0.1, 1, 10, 30, 100, 300, 1000]

FRIEND_FEATURES = [
    'temp_avg', 'heatwave_days', 'tropical_night_days', 'kbo_games',
    'world_cup_dummy', 'holiday_days', 'import_beer_price_yoy',
    'ob_price_hike_dummy', 'cass_fresh_share', 'cass_light_share',
]

# IMPORTANT: Google Trends variables are deliberately excluded from the final model.
# The earlier user-side proxy target used Google Trends to construct demand, so using
# Google Trends again as predictors would create circularity / target leakage.
OUR_FEATURES = [
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

MODEL_FEATURES = [
    'lag_1', 'lag_12', 'rolling_3_mean', 'rolling_6_mean',
    'month_sin_annual', 'month_cos_annual',
    'month_num', 'quarter',
    'is_summer_peak_jul_aug', 'is_year_end_nov_dec',
] + FRIEND_FEATURES + OUR_FEATURES


def mase(actual, pred, train_series, seasonality=12):
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    train_series = np.asarray(train_series, dtype=float)
    denom = np.mean(np.abs(train_series[seasonality:] - train_series[:-seasonality]))
    return float(np.mean(np.abs(actual - pred)) / denom)


def wape(actual, pred):
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    return float(np.sum(np.abs(actual - pred)) / np.sum(np.abs(actual)))


def rmse(actual, pred):
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    return float(np.sqrt(np.mean((actual - pred) ** 2)))


def fit_ridge(X, y, alpha):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    x_mean = X.mean(axis=0)
    x_std = X.std(axis=0)
    x_std[x_std == 0] = 1.0
    Xs = (X - x_mean) / x_std
    y_mean = y.mean()
    yc = y - y_mean
    I = np.eye(Xs.shape[1])
    beta = np.linalg.solve(Xs.T @ Xs + alpha * I, Xs.T @ yc)
    return {'x_mean': x_mean, 'x_std': x_std, 'y_mean': y_mean, 'beta': beta}


def predict_ridge(model, X):
    X = np.asarray(X, dtype=float)
    return ((X - model['x_mean']) / model['x_std']) @ model['beta'] + model['y_mean']


def load_integrated():
    ours = pd.read_csv(OURS_PATH)
    collect = pd.read_csv(COLLECT_PATH)
    ours['month'] = pd.to_datetime(ours['month'])
    collect['month'] = pd.to_datetime(collect['month'])

    # Prefix overlapping non-key columns from our richer dataset to avoid collisions.
    overlap = set(ours.columns).intersection(collect.columns) - {'month'}
    ours = ours.rename(columns={c: f'ours__{c}' for c in overlap})

    df = collect.merge(ours, on='month', how='left')
    df = df.sort_values('month').reset_index(drop=True)

    # Restore feature aliases if they were prefixed due to overlap.
    for c in ['month_num', 'quarter', 'month_sin_annual', 'month_cos_annual', 'is_summer_peak_jul_aug', 'is_year_end_nov_dec']:
        if c not in df.columns and f'ours__{c}' in df.columns:
            df[c] = df[f'ours__{c}']

    # Friend feature aliases are authoritative.
    alias_map = {
        'seoul_avg_temp_c': 'temp_avg',
        'seoul_heatwave_warning_days_33c': 'heatwave_days',
        'seoul_tropical_nights_25c': 'tropical_night_days',
        'kbo_regular_games': 'kbo_games',
        'public_holiday_count_kr': 'holiday_days',
        'ob_major_price_increase_event_dummy': 'ob_price_hike_dummy',
        'imported_beer_unit_value_yoy_pct': 'import_beer_price_yoy',
    }
    for ours_col, friend_col in alias_map.items():
        if friend_col not in df.columns and ours_col in df.columns:
            df[friend_col] = df[ours_col]

    df['lag_1'] = df[TARGET].shift(1)
    df['lag_12'] = df[TARGET].shift(12)
    df['rolling_3_mean'] = df[TARGET].shift(1).rolling(3).mean()
    df['rolling_6_mean'] = df[TARGET].shift(1).rolling(6).mean()

    # Ensure every feature exists and impute safe numeric values.
    for col in MODEL_FEATURES:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if col.startswith('lag_') or col.startswith('rolling_'):
            continue
        df[col] = df[col].fillna(df[col].median()).fillna(0.0)

    return df


def rolling_ridge_predictions(df, start_idx, alpha):
    rows = []
    for i in range(start_idx, len(df)):
        train = df.iloc[:i].dropna(subset=MODEL_FEATURES + [TARGET])
        test = df.iloc[[i]]
        model = fit_ridge(train[MODEL_FEATURES].to_numpy(), train[TARGET].to_numpy(), alpha)
        pred = float(predict_ridge(model, test[MODEL_FEATURES].to_numpy())[0])
        rows.append({
            'month': test['month'].dt.strftime('%Y-%m').iloc[0],
            'actual': float(test[TARGET].iloc[0]),
            'prediction': pred,
            'model': 'final_integrated_ridge',
        })
    return pd.DataFrame(rows)


def seasonal_naive_predictions(df, start_idx):
    rows = []
    for i in range(start_idx, len(df)):
        test = df.iloc[i]
        rows.append({
            'month': test['month'].strftime('%Y-%m'),
            'actual': float(test[TARGET]),
            'prediction': float(test['lag_12']),
            'model': 'seasonal_naive',
        })
    return pd.DataFrame(rows)


def select_alpha(df, train_end_idx):
    # Tune on the last 12 months before 2024.
    valid_start = train_end_idx - 12
    scale = df.iloc[:valid_start][TARGET].to_numpy()
    scores = []
    for a in ALPHAS:
        pred = rolling_ridge_predictions(df.iloc[:train_end_idx].copy(), valid_start, a)
        scores.append({'alpha': a, 'validation_MASE': mase(pred['actual'], pred['prediction'], scale)})
    scores = sorted(scores, key=lambda x: x['validation_MASE'])
    return scores[0]['alpha'], scores


def load_chronos_backtest():
    if not CHRONOS_BT_PATH.exists():
        return None
    c = pd.read_csv(CHRONOS_BT_PATH, encoding='utf-8-sig')
    if 'month' not in c.columns:
        c['month'] = pd.to_datetime(c['timestamp']).dt.strftime('%Y-%m')
    return c[['month', 'actual', 'prediction']].assign(model='chronos2_covariate_0603')


def metric_table(pred_df, train_series, event_months):
    rows = []
    for model, g in pred_df.groupby('model'):
        for split, mask in [
            ('all_test', np.ones(len(g), dtype=bool)),
            ('event_months', g['month'].isin(event_months).to_numpy()),
            ('normal_months', ~g['month'].isin(event_months).to_numpy()),
        ]:
            if mask.sum() == 0:
                continue
            rows.append({
                'model': model,
                'split': split,
                'n_months': int(mask.sum()),
                'MASE': mase(g.loc[mask, 'actual'], g.loc[mask, 'prediction'], train_series),
                'WAPE': wape(g.loc[mask, 'actual'], g.loc[mask, 'prediction']),
                'RMSE': rmse(g.loc[mask, 'actual'], g.loc[mask, 'prediction']),
            })
    return pd.DataFrame(rows).sort_values(['split', 'MASE'])


def make_2026_forecast(df, alpha):
    # Build a practical future feature frame using 0603 Chronos forecast months,
    # month-of-year averages for exogenous variables, and model-generated lag recursion.
    if not CHRONOS_FC_PATH.exists():
        return pd.DataFrame()
    fc = pd.read_csv(CHRONOS_FC_PATH, encoding='utf-8-sig')
    fc['month'] = pd.to_datetime(fc['month'])
    hist = df.copy()
    train = hist.dropna(subset=MODEL_FEATURES + [TARGET])
    model = fit_ridge(train[MODEL_FEATURES].to_numpy(), train[TARGET].to_numpy(), alpha)
    month_avg = hist.assign(month_num_future=hist['month'].dt.month).groupby('month_num_future').median(numeric_only=True)

    future_rows = []
    extended = hist[['month', TARGET] + MODEL_FEATURES].copy()
    for _, r in fc.iterrows():
        m = r['month']
        month_num = m.month
        row = {'month': m, TARGET: np.nan}
        for col in MODEL_FEATURES:
            if col == 'lag_1':
                row[col] = float(extended[TARGET].iloc[-1])
            elif col == 'lag_12':
                lag_month = m - pd.DateOffset(years=1)
                vals = extended.loc[extended['month'] == lag_month, TARGET]
                row[col] = float(vals.iloc[0]) if len(vals) else float(extended[TARGET].tail(12).mean())
            elif col == 'rolling_3_mean':
                row[col] = float(extended[TARGET].tail(3).mean())
            elif col == 'rolling_6_mean':
                row[col] = float(extended[TARGET].tail(6).mean())
            elif col in month_avg.columns:
                row[col] = float(month_avg.loc[month_num, col])
            else:
                row[col] = 0.0
        # Override known 0603 future forecast information when possible.
        row['month_num'] = month_num
        row['quarter'] = (month_num - 1) // 3 + 1
        row['month_sin_annual'] = np.sin(2 * np.pi * month_num / 12)
        row['month_cos_annual'] = np.cos(2 * np.pi * month_num / 12)
        row['world_cup_dummy'] = 1 if month_num in [6, 7] else 0
        row['ob_price_hike_dummy'] = 0
        pred = float(predict_ridge(model, pd.DataFrame([row])[MODEL_FEATURES].to_numpy())[0])
        row[TARGET] = pred
        future_rows.append({
            'month': m.strftime('%Y-%m'),
            'final_integrated_ridge_prediction': pred,
            'chronos2_0603_prediction': float(r.get('prediction', r.get('q500', np.nan))),
            'chronos2_q100': float(r.get('q100', np.nan)),
            'chronos2_q900': float(r.get('q900', np.nan)),
        })
        extended = pd.concat([extended, pd.DataFrame([row])[extended.columns]], ignore_index=True)
    out = pd.DataFrame(future_rows)
    out['final_recommended_prediction'] = 0.7 * out['final_integrated_ridge_prediction'] + 0.3 * out['chronos2_0603_prediction']
    return out


def main():
    df = load_integrated()
    df.to_csv(OUT_DIR / 'integrated_model_dataset.csv', index=False)

    train_end = int((df['month'] < pd.Timestamp('2024-01-01')).sum())
    test_start = train_end
    best_alpha, alpha_scores = select_alpha(df, train_end)

    ridge_pred = rolling_ridge_predictions(df, test_start, best_alpha)
    naive_pred = seasonal_naive_predictions(df, test_start)
    pred_parts = [ridge_pred, naive_pred]
    chronos = load_chronos_backtest()
    if chronos is not None:
        pred_parts.append(chronos)
    pred_df = pd.concat(pred_parts, ignore_index=True)

    event_mask = (
        (df['heatwave_days'] > 0)
        | (df['tropical_night_days'] > 0)
        | (df['kbo_games'] >= 100)
        | (df['world_cup_dummy'] > 0)
        | (df['ob_price_hike_dummy'] > 0)
    )
    event_months = set(df.loc[(df['month'] >= pd.Timestamp('2024-01-01')) & event_mask, 'month'].dt.strftime('%Y-%m'))
    train_series = df.loc[df['month'] < pd.Timestamp('2024-01-01'), TARGET].to_numpy()
    metrics = metric_table(pred_df, train_series, event_months)

    forecast_2026 = make_2026_forecast(df, best_alpha)

    pred_df.to_csv(OUT_DIR / 'final_backtest_predictions.csv', index=False)
    metrics.to_csv(OUT_DIR / 'final_model_metrics.csv', index=False)
    forecast_2026.to_csv(OUT_DIR / 'final_2026_forecast.csv', index=False)
    with open(OUT_DIR / 'final_model_summary.json', 'w', encoding='utf-8') as f:
        json.dump({
            'target': TARGET,
            'integrated_rows': int(len(df)),
            'train_months': train_end,
            'test_months': int(len(df) - test_start),
            'selected_alpha': best_alpha,
            'alpha_validation_scores': alpha_scores,
            'features_used': MODEL_FEATURES,
            'event_months_test': sorted(event_months),
            'source_friend_data': str(COLLECT_PATH),
            'source_our_data': str(OURS_PATH),
            'excluded_features_due_to_leakage': [
                'google_trends_beer', 'google_trends_imported_beer', 'google_trends_nonalc_beer',
                'google_trends_cass_beer', 'google_trends_cass_light', 'google_trends_cass_zero_terms',
                'price_pressure_search_index',
            ],
            'leakage_note': 'Google Trends variables are excluded because prior proxy target construction used Google Trends, so reusing them as predictors risks circularity.',
        }, f, ensure_ascii=False, indent=2)

    print('selected_alpha:', best_alpha)
    print(metrics.to_string(index=False))
    print('\nSaved outputs to', OUT_DIR)


if __name__ == '__main__':
    main()
