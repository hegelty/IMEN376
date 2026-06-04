# Cass 수요예측 외생변수 데이터 수집 보고서

작성일: 2026-05-28  
프로젝트: IMEN343 생산운영관리 — OB맥주 Cass 제품군 AI 수요예측 및 생산운영 최적화

---

## 1. 목적

기존 수요 데이터셋은 월별 맥주/저칼로리 맥주/논알콜 맥주 수요 proxy를 제공하지만, 수요예측 모델의 성능을 높이기 위해서는 수요를 설명하는 외생변수가 필요하다. 본 단계에서는 맥주 수요에 영향을 줄 수 있는 날씨, 이벤트, 뉴스, 가격·경제 데이터를 최대한 수집하고, 모델에 투입 가능한 월별 수치형 변수로 변환했다.

최종 산출물은 다음 파일이다.

```text
data/final_cass_demand_model_dataset_with_exogenous_2020_2025.csv
```

- 기간: 2020-01 ~ 2025-12
- 주기: 월별
- 행 수: 72개월
- 컬럼 수: 176개
- 포함 범위: 수요 proxy + 날씨/환경 + 축제/스포츠/공휴일 + 뉴스/비정형 + 가격/경제

---

## 2. 수집 전략

외생변수는 다음 네 축으로 나누어 수집했다.

| 축 | 수집 내용 | 수요예측상 의미 |
|---|---|---|
| 날씨·환경 | 기온, 습도, 체감온도, 강수, 풍속, 일사, 폭염, 열대야, 한파, 대기질 | 맥주 소비의 계절성, 더위 수요, 야외활동 영향 |
| 이벤트·캘린더 | 공휴일, 연휴, KBO 경기, 올림픽/월드컵/아시안게임, 지역축제, 맥주축제 | 모임, 관람, 관광, 외식 수요 proxy |
| 뉴스·비정형 | 맥주, Cass/OB, 무알콜, 폭염/맥주, 축제/맥주, 규제/가격/건강 뉴스 수 | 이슈 강도, 브랜드 노출, 소비 트렌드 proxy |
| 가격·경제 | 수입맥주 단가, 가격 검색량, CPI proxy, 가격 인상 이벤트 | 가격 민감도, 비용 압력, 소비심리 proxy |

---

## 3. 날씨·환경 데이터

### 3.1 산출 파일

```text
data/exog_weather_environment_monthly.csv
```

- 72행, 68컬럼
- 결측 없음
- 서울 기준 월별 데이터

### 3.2 원천

- Open-Meteo Historical Weather API
  - 서울 중심 좌표: 37.5665, 126.9780
  - 기온, 습도, 체감온도, 강수, 풍속, 일사 등
- 서울 열린데이터광장 MonthlyAverageAirQuality
  - 중구 측정소 월평균 PM10, PM2.5, NO2, O3, CO, SO2

### 3.3 수치화 변수 예시

| 변수 | 의미 | 모델링 해석 |
|---|---|---|
| `seoul_avg_temp_c` | 월평균기온 | 기본 더위 수요 |
| `seoul_avg_apparent_temp_c` | 월평균 체감온도 | 습도·풍속을 반영한 실제 더위 |
| `seoul_relative_humidity_mean_pct` | 평균 습도 | 불쾌지수/체감더위 보완 |
| `seoul_precipitation_mm` | 월강수량 | 야외활동 감소 또는 채널 변화 |
| `seoul_hot_days_30c` | 30℃ 이상 일수 | 맥주 피크 수요 proxy |
| `seoul_heatwave_warning_days_33c` | 33℃ 이상 일수 | 폭염 proxy |
| `seoul_tropical_nights_25c` | 열대야 proxy | 야간 음주/야식 수요 가능성 |
| `seoul_pm25_ug_m3` | 초미세먼지 | 야외활동 위축 가능성 |

### 3.4 Caveat

- Open-Meteo는 공식 ASOS 원관측이 아니라 격자형 archive다.
- 폭염/열대야/한파는 공식 특보가 아니라 threshold 기반 proxy다.
- 대기질은 서울 전체 평균이 아니라 중구 측정소를 서울 도심 proxy로 사용했다.

---

## 4. 이벤트·캘린더 데이터

### 4.1 산출 파일

```text
data/exog_events_calendar_monthly.csv
```

- 72행, 33컬럼
- 결측 없음

### 4.2 원천

- 문화체육관광부 지역축제 정보 2020~2025 ZIP/XLSX
- KBO 공식 Schedule.asmx API
- 한국 공휴일 규칙 `holidays.KR(observed=True)`
- 올림픽, 월드컵, 아시안게임 공식 개최기간 수동 규칙화

### 4.3 수치화 변수 예시

| 변수 | 의미 | 모델링 해석 |
|---|---|---|
| `public_holiday_count_kr` | 월별 공휴일 수 | 여행·모임·외식 수요 |
| `longest_consecutive_nonwork_days` | 최장 연휴 길이 | 설/추석/대체휴일 효과 |
| `kbo_regular_games` | KBO 정규시즌 경기 수 | 치맥·야식·관람 수요 proxy |
| `kbo_postseason_games` | KBO 포스트시즌 경기 수 | 가을야구 이벤트 효과 |
| `sports_major_event_days` | 대형 스포츠 이벤트 일수 | 월드컵/올림픽 관람 수요 |
| `regional_festival_offline_or_hybrid_count` | 오프라인/혼합 지역축제 수 | 야외 행사·관광 수요 |
| `beer_festival_offline_or_hybrid_count_keyword` | 맥주/비어/치맥 키워드 축제 수 | 맥주 직접 이벤트 proxy |

### 4.4 검증

- CSV 범위: 2020-01 ~ 2025-12
- KBO 정규시즌 합계는 2020~2025 각 연도 720경기로 검증됨

### 4.5 Caveat

- 지역축제는 계획 자료 기준이므로 실제 취소/변경 가능성이 있다.
- 2020~2021년은 COVID-19로 온라인/취소 축제가 많아 오프라인/혼합 변수를 함께 보는 것이 안전하다.

---

## 5. 뉴스·비정형 데이터

### 5.1 산출 파일

```text
data/exog_news_unstructured_monthly.csv
data/exog_news_unstructured_articles_sample.csv
```

- 월별 집계: 72행, 26컬럼
- 원천 기사 sample: 최대 5,000개 행
- Google News RSS 캐시 기반 총 21,144건의 기사 항목을 월별·카테고리별로 집계

### 5.2 검색 카테고리

| 변수 | 검색 주제 | 모델링 해석 |
|---|---|---|
| `news_beer_general_count` | 맥주 일반 | 시장 전반 이슈량 |
| `news_cass_ob_count` | Cass/OB맥주 | 브랜드 노출/캠페인/기업 이슈 |
| `news_nonalc_count` | 무알콜/논알콜 맥주 | 건강·절주 트렌드 |
| `news_weather_demand_count` | 폭염/날씨/맥주/음료 | 날씨 기반 음료 수요 이슈 |
| `news_festival_beer_count` | 축제/맥주축제/페스티벌 | 행사 기반 소비 이슈 |
| `news_regulation_health_price_count` | 규제/주세/가격/건강/절주 | 수요 억제 또는 대체소비 이슈 |

### 5.3 감성/키워드 수치화

뉴스 제목에서 단순 키워드 count를 사용했다.

- 긍정 키워드 예: 인기, 성장, 증가, 급증, 호조, 흥행, 출시, 1위, 확대
- 부정 키워드 예: 감소, 하락, 부진, 위축, 침체, 논란, 규제, 가격인상, 불매, 관세
- `news_sentiment_balance_proxy = 긍정 키워드 count - 부정 키워드 count`

### 5.4 Caveat

- 기사 수는 Google News RSS 검색 결과 기준이며 전체 언론 보도량이 아니다.
- 감성은 제목 기반 단순 키워드 방식이므로 정교한 NLP 감성분석이 아니다.
- 그래도 월별 이슈 강도와 브랜드/세그먼트 관심도를 수치화하는 데 유용하다.

---

## 6. 가격·경제 데이터

### 6.1 산출 파일

```text
data/exog_economic_price_monthly.csv
```

- 72행, 15컬럼

### 6.2 원천 및 수치화

| 변수 | 원천/생성 방식 | 모델링 해석 |
|---|---|---|
| `imported_beer_unit_value_usd_per_kg` | UN Comtrade HS2203 수입액 / 수입중량 | 수입맥주 단가, 프리미엄화, 비용 압력 |
| `imported_beer_unit_value_yoy_pct` | 위 값의 전년동월비 | 가격/비용 변화율 |
| `google_trends_inflation_m物가` | Google Trends `물가` | 소비자 물가 관심도 |
| `google_trends_beer_price` | Google Trends `맥주 가격` | 맥주 가격 관심도 |
| `google_trends_alcohol_price` | Google Trends `주류 가격` | 주류 가격 관심도 |
| `price_pressure_search_index` | 가격 관련 검색량 합계 | 가격 민감도 proxy |
| `korea_cpi_generated_index_2020_01_100` | 연간 CPI 상승률 anchor를 월별 평활 분해 | 일반 물가 proxy |
| `ob_major_price_increase_event_dummy` | 2024-04, 2025-04 가격 인상 보도 기반 | 가격 인상 충격 더미 |

### 6.3 Caveat

- KOSIS 주류/맥주 전용 CPI는 동적 표 접근이 불안정해 자동 수집하지 못했다.
- CPI는 실제 월별 CPI가 아니라 연간 CPI 상승률을 월별로 평활화한 proxy다.
- 가격 인상 더미는 보도 기반 이벤트 변수로만 해석한다.

---

## 7. 최종 병합 데이터셋

최종 병합 파일:

```text
data/final_cass_demand_model_dataset_with_exogenous_2020_2025.csv
```

검증:

| 항목 | 값 |
|---|---:|
| 기간 | 2020-01 ~ 2025-12 |
| 행 수 | 72 |
| 컬럼 수 | 176 |
| 날씨 원천 파일 | 72개월 |
| 이벤트 원천 파일 | 72개월 |
| 뉴스 원천 파일 | 72개월 |
| 가격·경제 원천 파일 | 72개월 |

변수 설명 파일:

```text
data/final_model_variable_dictionary.csv
exogenous_variables_for_model.md
```

---

## 8. 모델링 활용 방안

### 8.1 추천 타깃

- 전체 맥주: `alcoholic_beer_total_proxy_kl`
- 일반 맥주: `regular_beer_excluding_low_calorie_proxy_kl`
- 저칼로리/라이트: `low_calorie_light_beer_proxy_kl`, `cass_light_proxy_kl`
- 논알콜/무알콜: `nonalcoholic_beer_proxy_kl`, `cass_0_0_or_all_zero_proxy_kl`
- Cass Fresh: `cass_fresh_proxy_kl`

### 8.2 추천 feature set

기본 feature:

- 날씨: 평균기온, 체감온도, 습도, 폭염일수, 강수량
- 캘린더: 주말 수, 공휴일 수, 최장 연휴, 여름 더미
- 이벤트: KBO 경기 수, 지역축제 수, 맥주축제 수
- 뉴스: 맥주 뉴스 수, Cass/OB 뉴스 수, 무알콜 뉴스 수, 가격/규제 뉴스 수
- 가격: 수입맥주 단가, 가격 검색량, 가격 인상 더미

### 8.3 추천 실험 설계

- Train: 2020-01 ~ 2023-12
- Test: 2024-01 ~ 2024-12
- Scenario/Forecast: 2025-01 ~ 2025-12

비교 모델:

1. Seasonal Naive: 전년 동월값
2. SARIMAX: 시계열 + 외생변수
3. LightGBM/XGBoost: lag + 날씨/이벤트/뉴스/가격 변수

발표에서는 “외생변수를 넣었을 때 단순 계절 모델 대비 예측오차가 얼마나 줄어드는가”를 보여주면 AI 수요예측 기회가 가장 명확하게 드러난다.

---

## 9. 결론

본 단계에서는 단순 월별 수요 proxy를 넘어, 맥주 수요를 설명할 수 있는 외생변수 4개 축을 구축했다. 특히 날씨·환경과 이벤트 데이터는 실제 공개자료 기반의 정량 변수이며, 뉴스 데이터는 비정형 정보를 월별 기사 수와 키워드 감성으로 변환했다. 가격·경제 데이터는 일부 생성값을 포함하지만, 수입맥주 단가와 가격 검색량을 함께 사용하여 가격 민감도 proxy로 활용 가능하다.

최종적으로 생성된 `final_cass_demand_model_dataset_with_exogenous_2020_2025.csv`는 IMEN343 프로젝트에서 AI 수요예측 모델을 실제로 구현하고, Cass Fresh / Cass Light / Cass 0.0의 생산 믹스 및 병목 공정 운영 의사결정으로 연결하기에 충분한 형태의 모델 입력 데이터셋이다.
