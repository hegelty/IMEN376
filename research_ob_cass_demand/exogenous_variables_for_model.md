# Cass 수요예측 모델용 외생변수 설명서

작성일: 2026-05-28  
최종 데이터셋: `data/final_cass_demand_model_dataset_with_exogenous_2020_2025.csv`  
변수 사전 CSV: `data/final_model_variable_dictionary.csv`

## 1. 데이터셋 구조

- 기간: 2020-01 ~ 2025-12
- 주기: 월별
- 행 수: 72개월
- 컬럼 수: 176개
- 조인 키: `month`
- 타깃 후보:
  - `alcoholic_beer_total_proxy_kl`
  - `regular_beer_excluding_low_calorie_proxy_kl`
  - `low_calorie_light_beer_proxy_kl`
  - `nonalcoholic_beer_proxy_kl`
  - `cass_fresh_proxy_kl`
  - `cass_light_proxy_kl`
  - `cass_0_0_or_all_zero_proxy_kl`

## 2. 변수 그룹 요약

| 그룹 | 파일 | 변수 수/성격 | 모델링 의미 |
|---|---|---|---|
| 수요 proxy | `monthly_beer_segment_modeling_dataset_2020_2025.csv` | 세그먼트/제품군 월별 수요 proxy | 예측 타깃 또는 lag feature |
| 날씨·환경 | `exog_weather_environment_monthly.csv` | 기온, 습도, 체감온도, 강수, 풍속, 일사, 폭염/열대야/한파, 대기질 | 맥주 수요의 계절성·더위·야외활동 영향 |
| 이벤트·캘린더 | `exog_events_calendar_monthly.csv` | 공휴일, 연휴, KBO, 대형 스포츠, 지역축제, 맥주축제 | 모임/외식/관람/관광 수요 proxy |
| 뉴스·비정형 | `exog_news_unstructured_monthly.csv` | Google News RSS 기사 수, 카테고리별 뉴스량, 제목 키워드 감성 | 이슈·브랜드 노출·트렌드 강도 proxy |
| 가격·경제 | `exog_economic_price_monthly.csv` | 수입맥주 단가, 가격 검색량, CPI 생성 index, 가격 인상 더미 | 가격 민감도·구매심리·비용 압력 proxy |

## 3. 추천 타깃별 feature set

### 3.1 전체 알코올 맥주 수요

권장 y:

```text
alcoholic_beer_total_proxy_kl
```

권장 X:

- 날씨: `seoul_avg_temp_c`, `seoul_hot_days_30c`, `seoul_tropical_nights_25c`, `seoul_precipitation_mm`, `seoul_relative_humidity_mean_pct`
- 이벤트: `public_holiday_weekday_count_kr`, `longest_consecutive_nonwork_days`, `kbo_regular_games`, `regional_festival_offline_or_hybrid_count`
- 검색/뉴스: `google_trends_beer`, `news_beer_general_count`, `news_weather_demand_count`
- 가격: `imported_beer_unit_value_usd_per_kg`, `price_pressure_search_index`, `ob_major_price_increase_event_dummy`

### 3.2 일반 맥주 수요

권장 y:

```text
regular_beer_excluding_low_calorie_proxy_kl
```

권장 X:

- 전체 맥주와 동일한 기본 feature
- `news_regulation_health_price_count`: 건강/절주/규제 뉴스가 일반 맥주 수요를 낮출 수 있음
- `google_trends_nonalc_beer`: 대체재 관심도 proxy로 추가 가능

### 3.3 저칼로리/라이트 맥주 수요

권장 y:

```text
low_calorie_light_beer_proxy_kl
cass_light_proxy_kl
```

권장 X:

- `google_trends_cass_light`
- `news_health_trend_title_count`
- `news_nonalc_count`
- `seoul_avg_temp_c`, `is_summer_peak_jun_aug`
- `price_pressure_search_index`

해석: 저칼로리/라이트 맥주는 건강·다이어트 트렌드와 더위 수요가 동시에 작용할 가능성이 크다.

### 3.4 논알콜/무알콜 맥주 수요

권장 y:

```text
nonalcoholic_beer_proxy_kl
cass_0_0_or_all_zero_proxy_kl
```

권장 X:

- `google_trends_nonalc_beer`
- `google_trends_cass_zero_terms`
- `news_nonalc_count`
- `news_health_trend_title_count`
- `korea_cpi_generated_yoy_pct`, `price_pressure_search_index`
- `public_holiday_count_kr`, `weekend_days`

해석: 논알콜/무알콜은 음주 절제, 건강, 운전/운동 전후 소비, 가격 부담 시 대체 소비와 연결될 수 있다.

## 4. 뉴스/비정형 데이터 수치화

뉴스 데이터는 Google News RSS 검색 결과를 월별로 집계했다.

카테고리:

- `news_beer_general_count`: 맥주 일반 뉴스 수
- `news_cass_ob_count`: Cass/OB맥주 관련 뉴스 수
- `news_nonalc_count`: 무알콜/논알콜 맥주 뉴스 수
- `news_weather_demand_count`: 폭염·무더위·날씨와 맥주/음료 관련 뉴스 수
- `news_festival_beer_count`: 축제/페스티벌/맥주축제 뉴스 수
- `news_regulation_health_price_count`: 규제, 주세, 가격인상, 건강, 절주 관련 뉴스 수
- `news_sentiment_balance_proxy`: 제목 내 긍정 키워드 count - 부정 키워드 count

주의: 뉴스 변수는 전체 언론 보도량이 아니라 특정 Google News RSS 쿼리 결과의 count다. 따라서 절대 뉴스 수가 아니라 월별 이슈 강도 proxy로 사용한다.

## 5. 모델링 시 주의사항

1. **타깃 자체가 proxy다.** Cass 제품별 실제 판매량이 아니라 공개자료 기반 생성값이다.
2. **계절성 중복이 강하다.** 기온, 여름 더미, 축제, KBO, 검색량이 모두 여름에 높을 수 있다. LightGBM/XGBoost 또는 Lasso/Ridge처럼 feature selection/regularization이 가능한 모델을 추천한다.
3. **뉴스/검색량은 동시성 변수다.** 실제 예측 시점에서 사용할 수 있는지에 따라 lag 처리해야 한다. 발표용 데모에서는 당월 nowcasting 변수로 설명 가능하다.
4. **2025년 수요는 provisional generated다.** 훈련은 2020~2024, 2025는 예측/시나리오 구간으로 쓰는 것이 안전하다.
5. **경제/CPI 일부는 생성값이다.** 실제 월별 주류 CPI가 아니라 연간 CPI anchor 기반 proxy와 가격 검색량을 결합했다.

## 6. 추천 모델 실험 설계

- Train: 2020-01 ~ 2023-12
- Validation/Test: 2024-01 ~ 2024-12
- Scenario/Forecast: 2025-01 ~ 2025-12

Baseline:

- Seasonal Naive: 전년 동월 수요 사용

ML 모델:

- LightGBM/XGBoost/RandomForest
- Features: lag1, lag12, rolling3, 날씨, 이벤트, 뉴스, 가격 변수

설명 가능한 모델:

- SARIMAX with exogenous variables
- Ridge/Lasso regression with lag features

발표에서는 “날씨+이벤트+뉴스+가격 변수를 넣은 모델이 단순 계절 naive보다 얼마나 개선되는지”를 보여주는 구성이 가장 설득력 있다.
