import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA_PATH = Path('/home/hegelty/programming/IMEN343/research_ob_cass_demand/data/final_cass_demand_model_dataset_with_exogenous_2020_2025.csv')
OUT_DIR = Path('/home/hegelty/.openclaw/workspace/model_test_outputs')
OUT_DIR.mkdir(exist_ok=True)

TARGET = 'alcoholic_beer_total_proxy_kl'
DATE_COL = 'month'

FEATURES = [
    'lag_1',
    'lag_12',
    'month_sin_annual',
    'month_cos_annual',
    'seoul_avg_temp_c',
    'seoul_heatwave_warning_days_33c',
    'seoul_tropical_nights_25c',
    'public_holiday_count_kr',
    'kbo_regular_games',
    'sports_major_event_days',
    'news_total_index',
    'news_sentiment_balance_proxy',
    'imported_beer_unit_value_yoy_pct',
    'ob_major_price_increase_event_dummy',
    'is_year_end_nov_dec',
    'is_summer_peak_jul_aug',
]

ALPHAS = [0.0, 0.1, 1.0, 10.0, 100.0]


def mase(actual, pred, train_series, seasonality=12):
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    train_series = np.asarray(train_series, dtype=float)
    denom = np.mean(np.abs(train_series[seasonality:] - train_series[:-seasonality]))
    if denom == 0:
        return np.nan
    return np.mean(np.abs(actual - pred)) / denom


def wape(actual, pred):
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    denom = np.sum(np.abs(actual))
    if denom == 0:
        return np.nan
    return np.sum(np.abs(actual - pred)) / denom


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
    if alpha == 0:
        beta = np.linalg.lstsq(Xs, yc, rcond=None)[0]
    else:
        I = np.eye(Xs.shape[1])
        beta = np.linalg.solve(Xs.T @ Xs + alpha * I, Xs.T @ yc)
    return {
        'x_mean': x_mean,
        'x_std': x_std,
        'y_mean': y_mean,
        'beta': beta,
    }


def predict_ridge(model, X):
    X = np.asarray(X, dtype=float)
    Xs = (X - model['x_mean']) / model['x_std']
    return Xs @ model['beta'] + model['y_mean']


def add_lags(df):
    df = df.copy()
    df['lag_1'] = df[TARGET].shift(1)
    df['lag_12'] = df[TARGET].shift(12)
    return df


def prepare_df():
    df = pd.read_csv(DATA_PATH)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df = df.sort_values(DATE_COL).reset_index(drop=True)
    df = add_lags(df)
    for col in FEATURES:
        if col not in df.columns:
            raise KeyError(f'Missing feature: {col}')
    df['imported_beer_unit_value_yoy_pct'] = df['imported_beer_unit_value_yoy_pct'].fillna(0.0)
    return df


def rolling_predict(df, start_idx, alpha):
    rows = []
    for i in range(start_idx, len(df)):
        train = df.iloc[:i].copy()
        test_row = df.iloc[[i]].copy()
        train_model = train.dropna(subset=FEATURES + [TARGET])
        X_train = train_model[FEATURES].to_numpy()
        y_train = train_model[TARGET].to_numpy()
        if alpha == 'seasonal_naive':
            pred = float(test_row['lag_12'].iloc[0])
            model_name = 'seasonal_naive'
        else:
            model = fit_ridge(X_train, y_train, alpha)
            pred = float(predict_ridge(model, test_row[FEATURES].to_numpy())[0])
            model_name = f'ridge_alpha_{alpha:g}'
        rows.append({
            'month': test_row[DATE_COL].dt.strftime('%Y-%m').iloc[0],
            'actual': float(test_row[TARGET].iloc[0]),
            'prediction': pred,
            'model': model_name,
        })
    return pd.DataFrame(rows)


def pick_alpha(df, train_end_idx, valid_start_idx):
    scores = []
    base_train = df.iloc[:train_end_idx].copy()
    scale_series = base_train[TARGET].dropna().to_numpy()
    for alpha in ALPHAS:
        preds = rolling_predict(df.iloc[:train_end_idx].copy(), start_idx=valid_start_idx, alpha=alpha)
        score = mase(preds['actual'], preds['prediction'], scale_series)
        scores.append((alpha, score))
    scores.sort(key=lambda x: x[1])
    return scores[0][0], scores


def main():
    df = prepare_df()
    # need enough history for lag_12 and a small validation window inside pre-2024 training
    train_mask = df[DATE_COL] < pd.Timestamp('2024-01-01')
    test_mask = df[DATE_COL] >= pd.Timestamp('2024-01-01')
    train_end_idx = int(train_mask.sum())
    test_start_idx = train_end_idx

    # validation: last 12 months of training period
    valid_start_idx = train_end_idx - 12
    best_alpha, alpha_scores = pick_alpha(df, train_end_idx=train_end_idx, valid_start_idx=valid_start_idx)

    results = []
    results.append(rolling_predict(df, start_idx=test_start_idx, alpha='seasonal_naive'))
    results.append(rolling_predict(df, start_idx=test_start_idx, alpha=best_alpha))
    pred_df = pd.concat(results, ignore_index=True)

    train_series = df.loc[train_mask, TARGET].dropna().to_numpy()
    event_mask = (
        (df['seoul_heatwave_warning_days_33c'] > 0)
        | (df['seoul_tropical_nights_25c'] > 0)
        | (df['kbo_regular_games'] >= 100)
        | (df['sports_major_event_days'] > 0)
    )
    event_months = set(df.loc[test_mask & event_mask, DATE_COL].dt.strftime('%Y-%m'))

    metrics_rows = []
    for model_name, g in pred_df.groupby('model'):
        for split_name, idx_mask in [
            ('all_test', np.ones(len(g), dtype=bool)),
            ('event_months', g['month'].isin(event_months).to_numpy()),
            ('normal_months', ~g['month'].isin(event_months).to_numpy()),
        ]:
            if idx_mask.sum() == 0:
                continue
            actual = g.loc[idx_mask, 'actual'].to_numpy()
            pred = g.loc[idx_mask, 'prediction'].to_numpy()
            metrics_rows.append({
                'model': model_name,
                'split': split_name,
                'n_months': int(idx_mask.sum()),
                'MASE': mase(actual, pred, train_series),
                'WAPE': wape(actual, pred),
                'RMSE': rmse(actual, pred),
            })
    metrics_df = pd.DataFrame(metrics_rows).sort_values(['split', 'MASE'])

    summary = {
        'data_path': str(DATA_PATH),
        'target': TARGET,
        'n_rows': int(len(df)),
        'train_months': int(train_mask.sum()),
        'test_months': int(test_mask.sum()),
        'features': FEATURES,
        'selected_alpha': best_alpha,
        'alpha_validation_scores': [{
            'alpha': a,
            'validation_MASE': s,
        } for a, s in alpha_scores],
        'event_months_in_test': sorted(event_months),
    }

    pred_df.to_csv(OUT_DIR / 'rolling_predictions.csv', index=False)
    metrics_df.to_csv(OUT_DIR / 'metrics.csv', index=False)
    with open(OUT_DIR / 'summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('\n=== metrics ===')
    print(metrics_df.to_string(index=False))


if __name__ == '__main__':
    main()
