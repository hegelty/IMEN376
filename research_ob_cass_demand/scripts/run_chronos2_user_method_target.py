import numpy as np
import pandas as pd
import torch
from pathlib import Path
from chronos import BaseChronosPipeline

BASE=Path('/home/hegelty/programming/IMEN343/research_ob_cass_demand')
DATA=BASE/'final_user_method_target_outputs/user_method_integrated_dataset.csv'
OUT=BASE/'final_user_method_target_outputs'
TARGET='beer_apparent_consumption_user_method_kl'
TEST_START=pd.Timestamp('2024-01-01')
COVARIATES=[
 'month_sin_annual','month_cos_annual','month_num','quarter','is_summer_peak_jul_aug','is_year_end_nov_dec',
 'temp_avg','heatwave_days','tropical_night_days','kbo_games','world_cup_dummy','holiday_days','import_beer_price_yoy','ob_price_hike_dummy',
 'cass_fresh_share','cass_light_share','news_total_index','news_sentiment_balance_proxy','news_beer_general_count','news_cass_ob_count','news_nonalc_count',
 'news_weather_demand_count','news_festival_beer_count','regional_festival_count_planned','regional_festival_days_est','beer_festival_count_keyword','beer_festival_days_est_keyword',
 'korea_cpi_generated_yoy_pct','imported_beer_unit_value_yoy_pct','seoul_precipitation_mm','seoul_rain_days','seoul_pm10_ug_m3','seoul_pm25_ug_m3',
 'public_holiday_weekday_count_kr','nonworking_days_weekend_or_holiday','long_weekend_3plus_days_in_month','kbo_postseason_games',
]

def mase(a,p,train,s=12):
    return float(np.mean(np.abs(np.asarray(a)-np.asarray(p))) / np.mean(np.abs(train[s:]-train[:-s])))
def wape(a,p):
    return float(np.sum(np.abs(np.asarray(a)-np.asarray(p))) / np.sum(np.abs(a)))
def rmse(a,p):
    return float(np.sqrt(np.mean((np.asarray(a)-np.asarray(p))**2)))

def main():
    df=pd.read_csv(DATA)
    df['month']=pd.to_datetime(df['month'])
    for c in COVARIATES:
        if c not in df.columns: df[c]=0.0
        df[c]=pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    work=df[['month',TARGET]+COVARIATES].rename(columns={'month':'timestamp',TARGET:'target'}).copy()
    work['item_id']='cass_apparent_consumption'
    train=work[work.timestamp<TEST_START]
    test=work[work.timestamp>=TEST_START]
    device='cuda' if torch.cuda.is_available() else 'cpu'
    print('Using device:',device)
    pipe=BaseChronosPipeline.from_pretrained('amazon/chronos-2', device_map=device)
    pred=pipe.predict_df(train[['item_id','timestamp','target']+COVARIATES], future_df=test[['item_id','timestamp']+COVARIATES], prediction_length=len(test), quantile_levels=[0.1,0.5,0.9], id_column='item_id', timestamp_column='timestamp', target='target')
    merged=pred.merge(test[['item_id','timestamp','target']], on=['item_id','timestamp'], how='left').rename(columns={'target':'actual','predictions':'prediction'})
    merged['month']=merged.timestamp.dt.strftime('%Y-%m')
    merged.to_csv(OUT/'chronos2_user_method_predictions.csv', index=False)
    tr=train.target.to_numpy()
    metrics=pd.DataFrame([{'model':'chronos2_user_method','split':'all_test','n_months':len(merged),'MASE':mase(merged.actual,merged.prediction,tr),'WAPE':wape(merged.actual,merged.prediction),'RMSE':rmse(merged.actual,merged.prediction)}])
    metrics.to_csv(OUT/'chronos2_user_method_metrics.csv', index=False)
    print(metrics.to_string(index=False))
if __name__=='__main__': main()
