# Cass 수요예측 모델 담당자 전달용 요약

작성일: 2026-05-29  
대상: 실제 수요예측 모델 구현 담당자

## 1. 바로 써야 하는 파일

### 최종 모델 입력 데이터
- `data/final_cass_demand_model_dataset_with_exogenous_2020_2025.csv`
  - 월별 데이터, 2020-01 ~ 2025-12
  - 72행, 176컬럼
  - 타깃 후보 + 외생변수 포함

### 변수 설명
- `data/final_model_variable_dictionary.csv`
- `exogenous_variables_for_model.md`

### 수요 proxy 생성 방법(반드시 이해 필요)
- `monthly_demand_proxy_method.md`

### 검증 파일
- `data/final_exogenous_dataset_validation.csv`

---

## 2. 이 데이터의 핵심 전제

1. **Cass 제품별 실제 월별 판매량 데이터가 아니다.**  
   공개자료 기반으로 만든 **proxy dataset**이다.
2. **타깃 후보 일부는 생성값**이다.  
   특히 `cass_fresh_proxy_kl`, `cass_light_proxy_kl`, `cass_0_0_or_all_zero_proxy_kl`은 실제 내부 판매량이 아니라 시나리오/모델링용 proxy다.
3. **2025년 데이터는 forecast/scenario 구간으로 보는 것이 안전**하다.  
   학습 주력 구간은 2020~2024를 권장한다.
4. **일부 가격/경제 변수도 proxy 또는 generated value**다.
5. **뉴스/검색량 변수는 동시성(nowcasting) 성격**이 강하다. 예측 시점 정의에 따라 lag 처리 필요.

---

## 3. 추천 타깃

우선순위 기준 추천:

### 1순위: 전체/세그먼트 수요 예측
- `alcoholic_beer_total_proxy_kl`
- `regular_beer_excluding_low_calorie_proxy_kl`
- `low_calorie_light_beer_proxy_kl`
- `nonalcoholic_beer_proxy_kl`

### 2순위: Cass 제품군 proxy
- `cass_fresh_proxy_kl`
- `cass_light_proxy_kl`
- `cass_0_0_or_all_zero_proxy_kl`

**권장 해석:**
- 발표/보고서용 성능 비교는 1순위 타깃이 더 안정적이다.
- Cass SKU 수준은 proxy 생성 오차가 더 크므로 “정밀 예측”보다 “방향성/시나리오 분석”에 가깝다.

---

## 4. 추천 학습/평가 구간

- **Train:** 2020-01 ~ 2023-12
- **Validation/Test:** 2024-01 ~ 2024-12
- **Scenario/Forecast:** 2025-01 ~ 2025-12

72개월밖에 없어서 복잡한 딥러닝보다는 아래 접근이 현실적이다.

---

## 5. 먼저 돌려볼 모델

### Baseline
1. Seasonal Naive (전년 동월값)
2. 단순 이동평균/rolling baseline

### 추천 본모델
1. **SARIMAX**
   - 장점: 시계열 해석 용이, 발표 설명이 쉬움
2. **LightGBM / XGBoost**
   - 장점: lag + 외생변수 조합에 강함
3. **Ridge / Lasso 회귀**
   - 장점: 변수 과다 상황에서 안정적 baseline 가능

**비추천:**
- 관측치가 72개월뿐이라 복잡한 딥러닝은 과적합 위험이 큼.

---

## 6. 첫 실험에 바로 넣을 feature 세트

### 공통 lag feature
- 타깃의 `lag1`, `lag2`, `lag3`, `lag12`
- `rolling_mean_3`, `rolling_mean_6` 성격 변수

### 날씨
- `seoul_avg_temp_c`
- `seoul_avg_apparent_temp_c`
- `seoul_relative_humidity_mean_pct`
- `seoul_precipitation_mm`
- `seoul_hot_days_30c`
- `seoul_heatwave_warning_days_33c`
- `seoul_tropical_nights_25c`

### 캘린더/이벤트
- `public_holiday_count_kr`
- `longest_consecutive_nonwork_days`
- `weekend_days`
- `kbo_regular_games`
- `kbo_postseason_games`
- `regional_festival_offline_or_hybrid_count`
- `beer_festival_offline_or_hybrid_count_keyword`

### 뉴스/검색량
- `google_trends_beer`
- `google_trends_nonalc_beer`
- `google_trends_cass_light`
- `news_beer_general_count`
- `news_cass_ob_count`
- `news_nonalc_count`
- `news_weather_demand_count`
- `news_regulation_health_price_count`
- `news_sentiment_balance_proxy`

### 가격/경제
- `imported_beer_unit_value_usd_per_kg`
- `imported_beer_unit_value_yoy_pct`
- `price_pressure_search_index`
- `korea_cpi_generated_index_2020_01_100`
- `ob_major_price_increase_event_dummy`

---

## 7. 모델링 시 반드시 조심할 것

1. **계절성 중복**  
   기온, 여름 더미, KBO, 축제, 검색량이 동시에 움직일 가능성이 크다. Regularization 또는 feature importance 점검 필요.

2. **동시성 변수 누수 가능성**  
   뉴스량, 검색량은 당월 결과를 설명하는 데는 좋지만, 순수 사전예측 목적이라면 lag 처리해야 한다.

3. **proxy target의 한계**  
   성능 숫자를 절대적 정확도로 해석하면 안 된다. “공개자료 기반 수요 패턴 복원력” 정도로 표현하는 것이 안전하다.

4. **2025 구간 해석 주의**  
   2025 일부는 generated/provisional 성격이므로 holdout 성능 검증보다 scenario 용도가 더 적합하다.

5. **모델 성능보다 메시지가 중요**  
   이 프로젝트에서는 “외생변수가 단순 계절 예측보다 낫다”를 보여주는 것이 핵심이다.

---

## 8. 발표/보고서에서 추천하는 비교 그림

최소한 아래 3개는 만드는 것을 권장한다.

1. **Seasonal Naive vs SARIMAX/LightGBM 성능 비교**
   - MAE, RMSE, MAPE
2. **실제(proxy) vs 예측 시계열 plot**
   - 2024년 구간 중심
3. **Feature importance 또는 계수 해석**
   - 더위, 공휴일, KBO, 뉴스, 가격 변수의 영향 설명

---

## 9. 추가로 받으면 모델 품질이 크게 좋아지는 내부 데이터

만약 실제 실무자/회사 쪽에서 받을 수 있다면 우선순위는 아래와 같다.

1. Cass Fresh / Cass Light / Cass 0.0 **월별 실제 판매량 또는 출고량**
2. 채널별 판매량
   - 편의점 / 대형마트 / 음식점 / 유흥 / 온라인 등
3. 월별 실제 판가 / 할인 / 프로모션 정보
4. 품절 / 생산차질 / 설비 downtime 정보
5. 광고 집행비 / 캠페인 일정
6. 지역별 판매량

이 중 1번만 있어도 현재 proxy 모델보다 훨씬 설득력 있는 결과가 나온다.

---

## 10. 한 줄 전달 포인트

**이 데이터셋은 공개자료 기반 proxy이지만, 월별 맥주 수요를 설명하는 외생변수까지 포함된 형태라서, 2020~2024 학습 / 2024 검증 / 2025 시나리오 구조로 SARIMAX 또는 LightGBM 실험을 바로 시작할 수 있다.**
