import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, Lasso, Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

BASE = Path('/home/hegelty/programming/IMEN343/research_ob_cass_demand')
OURS_PATH = BASE / 'data' / 'final_cass_demand_model_dataset_with_exogenous_2020_2025.csv'
COLLECT_PATH = BASE / '0603 Cass Data Collect' / 'cass_demand_v3_monthly.csv'
OUT_DIR = BASE / 'final_user_method_target_outputs'
OUT_DIR.mkdir(exist_ok=True)

TARGET = 'beer_apparent_consumption_user_method_kl'
TEST_START = pd.Timestamp('2024-01-01')
KG_PER_KL_BEER_APPROX = 1000.0

TARGET_COMPONENTS = [
    'beer_domestic_volume',
    'hs2203_import_kl_approx',
    'hs2203_export_kl_approx',
]

NONALC_COLUMNS = [
    'nonalcoholic_beer_proxy_kl',
    'nonalcoholic_beer_market_value_proxy_million_krw',
    'cass_0_0_or_all_zero_proxy_kl',
]

# Google Trends: allowed only as one-month lag operational demand-sensing features.
GOOGLE_TRENDS = [
    'google_trends_beer', 'google_trends_imported_beer', 'google_trends_nonalc_beer',
    'google_trends_cass_beer', 'google_trends_cass_light', 'google_trends_cass_zero_terms',
]

BASE_FEATURES = [
    'lag_1', 'lag_12', 'rolling_3_mean', 'rolling_6_mean',
    'month_sin_annual', 'month_cos_annual', 'month_num', 'quarter',
    'is_summer_peak_jul_aug', 'is_year_end_nov_dec',
    'temp_avg', 'heatwave_days', 'tropical_night_days', 'kbo_games',
    'world_cup_dummy', 'holiday_days', 'import_beer_price_yoy', 'ob_price_hike_dummy',
    'cass_fresh_share', 'cass_light_share',
    'news_total_index', 'news_sentiment_balance_proxy',
    'news_beer_general_count', 'news_cass_ob_count', 'news_nonalc_count',
    'news_weather_demand_count', 'news_festival_beer_count',
    'regional_festival_count_planned', 'regional_festival_days_est',
    'beer_festival_count_keyword', 'beer_festival_days_est_keyword',
    'korea_cpi_generated_yoy_pct', 'imported_beer_unit_value_yoy_pct',
    'months_since_ob_price_event_cap6', 'seoul_precipitation_mm', 'seoul_rain_days',
    'seoul_pm10_ug_m3', 'seoul_pm25_ug_m3',
    'public_holiday_weekday_count_kr', 'nonworking_days_weekend_or_holiday',
    'long_weekend_3plus_days_in_month', 'kbo_postseason_games',
]

LAGGED_GT_FEATURES = [f'{c}_lag1' for c in GOOGLE_TRENDS]
FEATURES_SAFE = BASE_FEATURES
FEATURES_OPERATIONAL_GT = BASE_FEATURES + LAGGED_GT_FEATURES


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


def pipe(model):
    return Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('model', model),
    ])


def model_zoo(prefix=''):
    return {
        f'{prefix}ridge': pipe(Ridge(alpha=0.1)),
        f'{prefix}lasso': pipe(Lasso(alpha=10.0, max_iter=20000, random_state=42)),
        f'{prefix}elastic_net': pipe(ElasticNet(alpha=10.0, l1_ratio=0.2, max_iter=20000, random_state=42)),
        f'{prefix}random_forest': pipe(RandomForestRegressor(n_estimators=300, max_depth=3, min_samples_leaf=3, random_state=42)),
        f'{prefix}extra_trees': pipe(ExtraTreesRegressor(n_estimators=300, max_depth=3, min_samples_leaf=3, random_state=42)),
        f'{prefix}gradient_boosting': pipe(GradientBoostingRegressor(n_estimators=160, learning_rate=0.03, max_depth=2, min_samples_leaf=3, random_state=42)),
        f'{prefix}hist_gradient_boosting': pipe(HistGradientBoostingRegressor(max_iter=160, learning_rate=0.03, max_leaf_nodes=8, l2_regularization=1.0, random_state=42)),
        f'{prefix}svr_rbf': pipe(SVR(C=3.0, epsilon=200.0, gamma='scale')),
        f'{prefix}knn': pipe(KNeighborsRegressor(n_neighbors=5, weights='distance')),
    }


def load_integrated():
    ours = pd.read_csv(OURS_PATH)
    collect = pd.read_csv(COLLECT_PATH)
    ours['month'] = pd.to_datetime(ours['month'])
    collect['month'] = pd.to_datetime(collect['month'])

    overlap = set(ours.columns).intersection(collect.columns) - {'month'}
    ours = ours.rename(columns={c: f'ours__{c}' for c in overlap})
    df = collect.merge(ours, on='month', how='left').sort_values('month').reset_index(drop=True)

    # Canonical aliases from rich user-side data or 0603 data.
    alias_map = {
        'month_num': ['month_num', 'ours__month_num'],
        'quarter': ['quarter', 'ours__quarter'],
        'month_sin_annual': ['month_sin_annual', 'ours__month_sin_annual'],
        'month_cos_annual': ['month_cos_annual', 'ours__month_cos_annual'],
        'is_summer_peak_jul_aug': ['is_summer_peak_jul_aug', 'ours__is_summer_peak_jul_aug'],
        'is_year_end_nov_dec': ['is_year_end_nov_dec', 'ours__is_year_end_nov_dec'],
        'news_total_index': ['news_total_index'],
        'news_sentiment_balance_proxy': ['news_sentiment_balance_proxy'],
        'news_beer_general_count': ['news_beer_general_count'],
        'news_cass_ob_count': ['news_cass_ob_count'],
        'news_nonalc_count': ['news_nonalc_count'],
        'news_weather_demand_count': ['news_weather_demand_count'],
        'news_festival_beer_count': ['news_festival_beer_count'],
        'regional_festival_count_planned': ['regional_festival_count_planned'],
        'regional_festival_days_est': ['regional_festival_days_est'],
        'beer_festival_count_keyword': ['beer_festival_count_keyword'],
        'beer_festival_days_est_keyword': ['beer_festival_days_est_keyword'],
        'korea_cpi_generated_yoy_pct': ['korea_cpi_generated_yoy_pct'],
        'imported_beer_unit_value_yoy_pct': ['imported_beer_unit_value_yoy_pct'],
        'months_since_ob_price_event_cap6': ['months_since_ob_price_event_cap6'],
        'seoul_precipitation_mm': ['seoul_precipitation_mm', 'ours__seoul_precipitation_mm'],
        'seoul_rain_days': ['seoul_rain_days', 'ours__seoul_rain_days'],
        'seoul_pm10_ug_m3': ['seoul_pm10_ug_m3'],
        'seoul_pm25_ug_m3': ['seoul_pm25_ug_m3'],
        'public_holiday_weekday_count_kr': ['public_holiday_weekday_count_kr'],
        'nonworking_days_weekend_or_holiday': ['nonworking_days_weekend_or_holiday'],
        'long_weekend_3plus_days_in_month': ['long_weekend_3plus_days_in_month'],
        'kbo_postseason_games': ['kbo_postseason_games'],
    }
    for out, candidates in alias_map.items():
        if out in df.columns:
            continue
        for c in candidates:
            if c in df.columns:
                df[out] = df[c]
                break

    # Google Trends canonical columns may be prefixed due to overlap.
    for c in GOOGLE_TRENDS:
        if c not in df.columns and f'ours__{c}' in df.columns:
            df[c] = df[f'ours__{c}']
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors='coerce')
        df[f'{c}_lag1'] = df[c].shift(1)

    # User target method: domestic shipments + import kL approx - export kL approx.
    df['hs2203_import_kl_approx'] = pd.to_numeric(df.get('hs2203_import_kg_actual'), errors='coerce') / KG_PER_KL_BEER_APPROX
    df['hs2203_export_kl_approx'] = pd.to_numeric(df.get('hs2203_export_kg_actual'), errors='coerce') / KG_PER_KL_BEER_APPROX
    df[TARGET] = pd.to_numeric(df['beer_domestic_volume'], errors='coerce') + df['hs2203_import_kl_approx'] - df['hs2203_export_kl_approx']

    # Non-alcohol / zero-alcohol segment using user-side method.
    for c in NONALC_COLUMNS:
        if c not in df.columns and f'ours__{c}' in df.columns:
            df[c] = df[f'ours__{c}']
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['nonalc_segment_user_method_kl'] = df['nonalcoholic_beer_proxy_kl']
    df['cass_zero_user_method_kl'] = df['cass_0_0_or_all_zero_proxy_kl']

    # Target-derived lags only after target computation.
    df['lag_1'] = df[TARGET].shift(1)
    df['lag_12'] = df[TARGET].shift(12)
    df['rolling_3_mean'] = df[TARGET].shift(1).rolling(3).mean()
    df['rolling_6_mean'] = df[TARGET].shift(1).rolling(6).mean()

    for c in set(FEATURES_OPERATIONAL_GT + TARGET_COMPONENTS + [TARGET]):
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors='coerce')

    return df


def seasonal_naive(df):
    rows=[]
    start=int((df['month'] < TEST_START).sum())
    for i in range(start, len(df)):
        r=df.iloc[i]
        rows.append({'month':r['month'].strftime('%Y-%m'), 'actual':float(r[TARGET]), 'prediction':float(r['lag_12']), 'model':'seasonal_naive'})
    return pd.DataFrame(rows)


def rolling_predict(df, name, model, features):
    rows=[]
    start=int((df['month'] < TEST_START).sum())
    for i in range(start, len(df)):
        train=df.iloc[:i].dropna(subset=[TARGET])
        test=df.iloc[[i]]
        m=clone(model)
        m.fit(train[features], train[TARGET])
        pred=float(m.predict(test[features])[0])
        rows.append({'month':test['month'].dt.strftime('%Y-%m').iloc[0], 'actual':float(test[TARGET].iloc[0]), 'prediction':pred, 'model':name})
    return pd.DataFrame(rows)


def metrics(pred_df, train_series, event_months):
    rows=[]
    for model,g in pred_df.groupby('model'):
        for split, mask in [
            ('all_test', np.ones(len(g), dtype=bool)),
            ('event_months', g['month'].isin(event_months).to_numpy()),
            ('normal_months', ~g['month'].isin(event_months).to_numpy()),
        ]:
            if mask.sum()==0:
                continue
            rows.append({'model':model,'split':split,'n_months':int(mask.sum()),'MASE':mase(g.loc[mask,'actual'], g.loc[mask,'prediction'], train_series),'WAPE':wape(g.loc[mask,'actual'], g.loc[mask,'prediction']),'RMSE':rmse(g.loc[mask,'actual'], g.loc[mask,'prediction'])})
    return pd.DataFrame(rows).sort_values(['split','MASE'])


def main():
    df=load_integrated()
    df.to_csv(OUT_DIR/'user_method_integrated_dataset.csv', index=False)

    pred_parts=[seasonal_naive(df)]
    for name, model in model_zoo().items():
        pred_parts.append(rolling_predict(df, name, model, FEATURES_SAFE))
    for name, model in model_zoo(prefix='lagged_gt_').items():
        pred_parts.append(rolling_predict(df, name, model, FEATURES_OPERATIONAL_GT))
    pred=pd.concat(pred_parts, ignore_index=True)

    event_mask=(
        (pd.to_numeric(df['heatwave_days'], errors='coerce') > 0)
        | (pd.to_numeric(df['tropical_night_days'], errors='coerce') > 0)
        | (pd.to_numeric(df['kbo_games'], errors='coerce') >= 100)
        | (pd.to_numeric(df['world_cup_dummy'], errors='coerce') > 0)
        | (pd.to_numeric(df['ob_price_hike_dummy'], errors='coerce') > 0)
    )
    event_months=set(df.loc[(df['month']>=TEST_START) & event_mask, 'month'].dt.strftime('%Y-%m'))
    train_series=df.loc[df['month']<TEST_START, TARGET].to_numpy()
    metric=metrics(pred, train_series, event_months)

    pred.to_csv(OUT_DIR/'user_method_model_backtest_predictions.csv', index=False)
    metric.to_csv(OUT_DIR/'user_method_model_metrics.csv', index=False)
    with open(OUT_DIR/'user_method_model_summary.json','w',encoding='utf-8') as f:
        json.dump({
            'target': TARGET,
            'target_definition': 'domestic beer shipment proxy + HS2203 import kg/1000 - HS2203 export kg/1000',
            'kg_per_kl_assumption': KG_PER_KL_BEER_APPROX,
            'nonalc_segment_columns': ['nonalc_segment_user_method_kl', 'cass_zero_user_method_kl', 'nonalcoholic_beer_market_value_proxy_million_krw'],
            'google_trends_policy': 'Not used in target. Tested only as lagged t-1 operational features.',
            'safe_features': FEATURES_SAFE,
            'lagged_google_trends_features': LAGGED_GT_FEATURES,
            'event_months': sorted(event_months),
        }, f, ensure_ascii=False, indent=2)
    print(metric.to_string(index=False))
    print('\nSaved to', OUT_DIR)

if __name__ == '__main__':
    main()
