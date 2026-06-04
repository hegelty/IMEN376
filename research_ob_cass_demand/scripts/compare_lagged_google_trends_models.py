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
DATA_PATH = BASE / 'final_adjusted_target_model_outputs' / 'integrated_dataset_with_adjusted_target.csv'
OUT_DIR = BASE / 'final_lagged_google_trends_model_outputs'
OUT_DIR.mkdir(exist_ok=True)

TARGET = 'beer_domestic_volume_adjusted_leakage_safe'
TEST_START = pd.Timestamp('2024-01-01')

GOOGLE_TRENDS = [
    'google_trends_beer', 'google_trends_imported_beer', 'google_trends_nonalc_beer',
    'google_trends_cass_beer', 'google_trends_cass_light', 'google_trends_cass_zero_terms',
]

BASE_FEATURES = [
    'lag_1', 'lag_12', 'rolling_3_mean', 'rolling_6_mean',
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

LAGGED_GT_FEATURES = [f'{c}_lag1' for c in GOOGLE_TRENDS]
FEATURES = BASE_FEATURES + LAGGED_GT_FEATURES


def mase(actual, pred, train_series, seasonality=12):
    denom = np.mean(np.abs(train_series[seasonality:] - train_series[:-seasonality]))
    return float(np.mean(np.abs(np.asarray(actual) - np.asarray(pred))) / denom)


def wape(actual, pred):
    return float(np.sum(np.abs(np.asarray(actual)-np.asarray(pred))) / np.sum(np.abs(actual)))


def rmse(actual, pred):
    return float(np.sqrt(np.mean((np.asarray(actual)-np.asarray(pred))**2)))


def pipe(model):
    return Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('model', model),
    ])


def models():
    return {
        'ridge_lagged_gt': pipe(Ridge(alpha=0.1)),
        'lasso_lagged_gt': pipe(Lasso(alpha=10.0, max_iter=20000, random_state=42)),
        'elastic_net_lagged_gt': pipe(ElasticNet(alpha=10.0, l1_ratio=0.2, max_iter=20000, random_state=42)),
        'random_forest_lagged_gt': pipe(RandomForestRegressor(n_estimators=300, max_depth=3, min_samples_leaf=3, random_state=42)),
        'extra_trees_lagged_gt': pipe(ExtraTreesRegressor(n_estimators=300, max_depth=3, min_samples_leaf=3, random_state=42)),
        'gradient_boosting_lagged_gt': pipe(GradientBoostingRegressor(n_estimators=160, learning_rate=0.03, max_depth=2, min_samples_leaf=3, random_state=42)),
        'hist_gradient_boosting_lagged_gt': pipe(HistGradientBoostingRegressor(max_iter=160, learning_rate=0.03, max_leaf_nodes=8, l2_regularization=1.0, random_state=42)),
        'svr_rbf_lagged_gt': pipe(SVR(C=3.0, epsilon=200.0, gamma='scale')),
        'knn_lagged_gt': pipe(KNeighborsRegressor(n_neighbors=5, weights='distance')),
    }


def load_data():
    df = pd.read_csv(DATA_PATH)
    df['month'] = pd.to_datetime(df['month'])
    # The integrated dataset prefixes overlapping columns from user data as ours__*.
    # Create canonical Google Trends columns from either direct or prefixed names.
    for c in GOOGLE_TRENDS:
        if c not in df.columns and f'ours__{c}' in df.columns:
            df[c] = df[f'ours__{c}']
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors='coerce')
        df[f'{c}_lag1'] = df[c].shift(1)
    for c in FEATURES:
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


def seasonal_naive(df):
    rows=[]
    start=int((df['month']<TEST_START).sum())
    for i in range(start,len(df)):
        r=df.iloc[i]
        rows.append({'month':r['month'].strftime('%Y-%m'),'actual':float(r[TARGET]),'prediction':float(r['lag_12']),'model':'seasonal_naive'})
    return pd.DataFrame(rows)


def rolling_predict(df,name,model):
    rows=[]
    start=int((df['month']<TEST_START).sum())
    for i in range(start,len(df)):
        train=df.iloc[:i].dropna(subset=[TARGET])
        test=df.iloc[[i]]
        m=clone(model)
        m.fit(train[FEATURES], train[TARGET])
        pred=float(m.predict(test[FEATURES])[0])
        rows.append({'month':test['month'].dt.strftime('%Y-%m').iloc[0], 'actual':float(test[TARGET].iloc[0]), 'prediction':pred, 'model':name})
    return pd.DataFrame(rows)


def metric_table(pred_df, train_series):
    rows=[]
    for model,g in pred_df.groupby('model'):
        rows.append({'model':model,'split':'all_test','n_months':len(g),'MASE':mase(g['actual'],g['prediction'],train_series),'WAPE':wape(g['actual'],g['prediction']),'RMSE':rmse(g['actual'],g['prediction'])})
    return pd.DataFrame(rows).sort_values('MASE')


def main():
    df=load_data()
    pred_parts=[seasonal_naive(df)]
    for name,m in models().items():
        pred_parts.append(rolling_predict(df,name,m))
    pred=pd.concat(pred_parts, ignore_index=True)
    train_series=df.loc[df['month']<TEST_START,TARGET].to_numpy()
    metrics=metric_table(pred,train_series)
    pred.to_csv(OUT_DIR/'lagged_google_trends_backtest_predictions.csv', index=False)
    metrics.to_csv(OUT_DIR/'lagged_google_trends_model_metrics.csv', index=False)
    with open(OUT_DIR/'lagged_google_trends_summary.json','w',encoding='utf-8') as f:
        json.dump({
            'target': TARGET,
            'google_trends_policy': 'Use only t-1 Google Trends values for month t prediction; no contemporaneous GT.',
            'lagged_google_trends_features': LAGGED_GT_FEATURES,
            'models_compared': ['seasonal_naive']+list(models().keys()),
        }, f, ensure_ascii=False, indent=2)
    print(metrics.to_string(index=False))
    print('\nSaved to',OUT_DIR)

if __name__=='__main__':
    main()
