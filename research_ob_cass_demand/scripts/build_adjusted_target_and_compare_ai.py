import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, Lasso, Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

BASE = Path('/home/hegelty/programming/IMEN343/research_ob_cass_demand')
INTEGRATED_PATH = BASE / 'final_integrated_model_outputs' / 'integrated_model_dataset.csv'
CHRONOS_BT_PATH = BASE / '0603 Cass Data Collect' / 'model_outputs' / 'chronos2_covariate_backtest.csv'
CHRONOS_FC_PATH = BASE / '0603 Cass Data Collect' / 'model_outputs' / 'chronos2_covariate_forecast.csv'
OUT_DIR = BASE / 'final_adjusted_target_model_outputs'
OUT_DIR.mkdir(exist_ok=True)

RAW_TARGET = 'beer_domestic_volume'
ADJ_TARGET = 'beer_domestic_volume_adjusted_leakage_safe'
TEST_START = pd.Timestamp('2024-01-01')

# Variables used to create adjusted monthly target. These are excluded from model features
# to avoid circularity. Google Trends is not used anywhere.
TARGET_ADJUSTMENT_SIGNALS = [
    'temp_avg',
    'heatwave_days',
    'tropical_night_days',
    'kbo_games',
    'holiday_days',
    'import_beer_price_yoy',
    'ob_price_hike_dummy',
]

BASE_FEATURES = [
    'lag_1', 'lag_12', 'rolling_3_mean', 'rolling_6_mean',
    'month_sin_annual', 'month_cos_annual', 'month_num', 'quarter',
    'is_summer_peak_jul_aug', 'is_year_end_nov_dec',
    'cass_fresh_share', 'cass_light_share',
    # Keep only features NOT used in target adjustment and NOT Google Trends.
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


def robust_z(s):
    s = pd.to_numeric(s, errors='coerce').astype(float)
    med = s.median()
    mad = (s - med).abs().median()
    if not np.isfinite(mad) or mad == 0:
        std = s.std()
        if not np.isfinite(std) or std == 0:
            return pd.Series(0.0, index=s.index)
        return (s - s.mean()) / std
    return (s - med) / (1.4826 * mad)


def build_adjusted_target(df):
    df = df.copy()
    df['year'] = df['month'].dt.year
    df['month_num'] = df['month'].dt.month

    # Start from existing month-of-year seasonality profile but damp it, then add non-Google signals.
    raw_month_weight = df[RAW_TARGET] / df.groupby('year')[RAW_TARGET].transform('sum')
    seasonal_profile = raw_month_weight.groupby(df['month_num']).transform('mean')

    # Conservative non-Google demand pressure index.
    pressure = (
        0.18 * robust_z(df['temp_avg'])
        + 0.10 * robust_z(df['heatwave_days'])
        + 0.08 * robust_z(df['tropical_night_days'])
        + 0.10 * robust_z(df['kbo_games'])
        + 0.04 * robust_z(df['holiday_days'])
        - 0.05 * robust_z(df['import_beer_price_yoy'])
        + 0.04 * robust_z(df['ob_price_hike_dummy'])
    )
    # Cap adjustment to avoid fabricating large swings.
    pressure = pressure.clip(-0.20, 0.20)

    # Dampen inherited seasonal profile and apply signal-driven adjustment.
    month_weight = seasonal_profile * (1.0 + pressure)
    month_weight = month_weight.clip(lower=0.001)
    month_weight = month_weight / month_weight.groupby(df['year']).transform('sum')

    annual_anchor = df.groupby('year')[RAW_TARGET].transform('sum')
    df[ADJ_TARGET] = annual_anchor * month_weight
    df['adjusted_target_pressure_index'] = pressure
    df['adjusted_target_month_weight'] = month_weight

    # Add lags based on adjusted target.
    df['lag_1'] = df[ADJ_TARGET].shift(1)
    df['lag_12'] = df[ADJ_TARGET].shift(12)
    df['rolling_3_mean'] = df[ADJ_TARGET].shift(1).rolling(3).mean()
    df['rolling_6_mean'] = df[ADJ_TARGET].shift(1).rolling(6).mean()
    return df


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


def model_pipeline(model):
    return Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('model', model),
    ])


def model_zoo():
    return {
        'ridge': model_pipeline(Ridge(alpha=0.1)),
        'lasso': model_pipeline(Lasso(alpha=10.0, max_iter=20000, random_state=42)),
        'elastic_net': model_pipeline(ElasticNet(alpha=10.0, l1_ratio=0.2, max_iter=20000, random_state=42)),
        'random_forest': model_pipeline(RandomForestRegressor(n_estimators=300, max_depth=3, min_samples_leaf=3, random_state=42)),
        'extra_trees': model_pipeline(ExtraTreesRegressor(n_estimators=300, max_depth=3, min_samples_leaf=3, random_state=42)),
        'gradient_boosting': model_pipeline(GradientBoostingRegressor(n_estimators=160, learning_rate=0.03, max_depth=2, min_samples_leaf=3, random_state=42)),
        'hist_gradient_boosting': model_pipeline(HistGradientBoostingRegressor(max_iter=160, learning_rate=0.03, max_leaf_nodes=8, l2_regularization=1.0, random_state=42)),
        'svr_rbf': model_pipeline(SVR(C=3.0, epsilon=200.0, gamma='scale')),
        'knn': model_pipeline(KNeighborsRegressor(n_neighbors=5, weights='distance')),
        'mlp': model_pipeline(MLPRegressor(hidden_layer_sizes=(16,), alpha=100.0, max_iter=4000, random_state=42)),
    }


def load_data():
    df = pd.read_csv(INTEGRATED_PATH)
    df['month'] = pd.to_datetime(df['month'])
    for c in TARGET_ADJUSTMENT_SIGNALS + BASE_FEATURES:
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = build_adjusted_target(df)
    for c in BASE_FEATURES:
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors='coerce')
    banned = [c for c in BASE_FEATURES if 'google_trends' in c or c == 'price_pressure_search_index' or c in TARGET_ADJUSTMENT_SIGNALS]
    if banned:
        raise RuntimeError(f'Leaky or target-construction features in model features: {banned}')
    return df


def rolling_predict(df, name, model):
    rows = []
    start_idx = int((df['month'] < TEST_START).sum())
    for i in range(start_idx, len(df)):
        train = df.iloc[:i].dropna(subset=[ADJ_TARGET])
        test = df.iloc[[i]]
        m = clone(model)
        m.fit(train[BASE_FEATURES], train[ADJ_TARGET])
        pred = float(m.predict(test[BASE_FEATURES])[0])
        rows.append({'month': test['month'].dt.strftime('%Y-%m').iloc[0], 'actual': float(test[ADJ_TARGET].iloc[0]), 'prediction': pred, 'model': name})
    return pd.DataFrame(rows)


def seasonal_naive(df):
    rows = []
    start_idx = int((df['month'] < TEST_START).sum())
    for i in range(start_idx, len(df)):
        r = df.iloc[i]
        rows.append({'month': r['month'].strftime('%Y-%m'), 'actual': float(r[ADJ_TARGET]), 'prediction': float(r['lag_12']), 'model': 'seasonal_naive'})
    return pd.DataFrame(rows)


def metrics(pred_df, train_series, event_months):
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


def main():
    df = load_data()
    df.to_csv(OUT_DIR / 'integrated_dataset_with_adjusted_target.csv', index=False)
    pred_parts = [seasonal_naive(df)]
    for name, model in model_zoo().items():
        try:
            pred_parts.append(rolling_predict(df, name, model))
        except Exception as e:
            print(f'[WARN] {name} failed: {e}')
    pred_df = pd.concat(pred_parts, ignore_index=True)

    event_mask = (
        (df['heatwave_days'] > 0)
        | (df['tropical_night_days'] > 0)
        | (df['kbo_games'] >= 100)
        | (df['world_cup_dummy'] > 0)
        | (df['ob_price_hike_dummy'] > 0)
    )
    event_months = set(df.loc[(df['month'] >= TEST_START) & event_mask, 'month'].dt.strftime('%Y-%m'))
    train_series = df.loc[df['month'] < TEST_START, ADJ_TARGET].to_numpy()
    metric_df = metrics(pred_df, train_series, event_months)

    pred_df.to_csv(OUT_DIR / 'adjusted_target_ai_backtest_predictions.csv', index=False)
    metric_df.to_csv(OUT_DIR / 'adjusted_target_ai_model_metrics.csv', index=False)
    with open(OUT_DIR / 'adjusted_target_summary.json', 'w', encoding='utf-8') as f:
        json.dump({
            'raw_target': RAW_TARGET,
            'adjusted_target': ADJ_TARGET,
            'target_adjustment_signals_excluded_from_features': TARGET_ADJUSTMENT_SIGNALS,
            'google_trends_policy': 'All Google Trends variables excluded from both target adjustment and model features.',
            'features_used': BASE_FEATURES,
            'event_months': sorted(event_months),
            'models_compared': ['seasonal_naive'] + list(model_zoo().keys()),
        }, f, ensure_ascii=False, indent=2)

    print(metric_df.to_string(index=False))
    print('\nSaved to', OUT_DIR)


if __name__ == '__main__':
    main()
