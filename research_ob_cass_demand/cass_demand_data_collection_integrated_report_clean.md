# Cass 수요예측 데이터 통합 정리 보고서

작성일: 2026-05-29

프로젝트: IMEN343 생산운영관리 — OB맥주 Cass 제품군 AI 수요예측 및 생산운영 최적화

작성 범위: data_collection_report.md와 exogenous_data_collection_report.md의 내용을 통합하되, 실제 모델 학습에 투입되지 않는 참고용·원천·샘플 데이터는 제외하고 최종 학습 데이터 기준으로 재정리하였다.

## 1. Executive Summary

본 프로젝트의 핵심 목적은 Cass Fresh, Cass Light, Cass 0.0/All Zero의 월별 수요예측 모델을 만들 수 있는 공개자료 기반 데이터셋을 구축하는 것이다. 공개자료 조사 결과 Cass SKU별 실제 월별 판매량·출고량은 공개되어 있지 않았으므로, 공식 연간 맥주 시장 규모와 월별 수요 proxy, 세그먼트별 시장 anchor, 날씨·이벤트·뉴스·가격경제 외생변수를 결합해 모델링용 월별 proxy 데이터셋을 구성했다.

최종 학습 입력 파일은 final_cass_demand_model_dataset_with_exogenous_2020_2025.csv 하나로 정리했다. 이 파일은 2020년 1월부터 2025년 12월까지 72개월, 176개 컬럼으로 구성되며, 수요 proxy와 외생변수를 모두 포함한다.

| 항목 | 정리 결과 |
| --- | --- |
| 최종 학습 입력 파일 | data/final_cass_demand_model_dataset_with_exogenous_2020_2025.csv |
| 기간 | 2020-01 ~ 2025-12 |
| 주기 | 월별 |
| 규모 | 72행 × 176컬럼 |
| 조인 키 | month |
| 타깃 성격 | 공개자료 기반 월별 수요 proxy |
| 외생변수 범위 | 날씨·환경, 이벤트·캘린더, 뉴스·비정형, 가격·경제 |
| 학습용 전달 폴더 | model_training_data_only |

## 2. 최종 전달 파일 구성

모델 담당자에게 전달할 파일은 실제 학습 또는 학습 전 검증에 필요한 최소 파일로 제한했다. 중간 원천 데이터, 참고용 데이터, 기사 sample, 스크립트는 제외했다.

| 파일 | 용도 | 학습 투입 여부 |
| --- | --- | --- |
| final_cass_demand_model_dataset_with_exogenous_2020_2025.csv | 수요 proxy와 외생변수가 모두 병합된 최종 월별 모델 입력 데이터 | 예 |
| final_model_variable_dictionary.csv | 176개 변수의 그룹, 설명, 모델링 용도, 주의사항 확인 | 아니오 — 메타데이터 |
| final_exogenous_dataset_validation.csv | 병합 결과, 기간, 행 수, 결측 여부 등 검증 요약 | 아니오 — 검증용 |

## 3. 제외한 데이터와 제외 이유

아래 데이터는 최종 데이터셋 생성 과정에서 사용되었거나 검증·추적 목적으로 남아 있지만, 실제 모델 학습 입력으로 직접 사용할 필요가 없으므로 전달 대상에서 제외했다. 같은 정보가 최종 병합 파일에 이미 반영되어 있어 중복 학습 또는 데이터 누수 위험을 줄이기 위한 조치다.

| 제외 데이터 유형 | 예시 파일 | 제외 이유 |
| --- | --- | --- |
| 원천/중간 Google Trends 데이터 | monthly_google_trends_beer_segments_2020_2026.csv, monthly_google_trends_cass_products_2020_2026.csv | 최종 데이터셋에 필요한 검색량 변수가 이미 병합되어 있음 |
| 원천/중간 UN Comtrade 데이터 | monthly_hs2203_comtrade_korea_2020_2025.csv | 수입·수출량과 단가 변수가 최종 데이터셋에 반영되어 있음 |
| 단독 날씨 중간 데이터 | monthly_weather_seoul_open_meteo_2020_2025.csv, exog_weather_environment_monthly.csv | 최종 데이터셋에 학습용 날씨·환경 변수가 병합되어 있음 |
| 외생변수별 중간 병합 파일 | exog_events_calendar_monthly.csv, exog_news_unstructured_monthly.csv, exog_economic_price_monthly.csv | 최종 병합 파일과 중복되므로 직접 학습 입력에서는 제외 |
| 뉴스 기사 sample | exog_news_unstructured_articles_sample.csv | 월별 집계값만 학습에 사용하며 기사 원문 목록은 참고용임 |
| 조사 메모·스크립트·원문 PDF/TXT | subagent_*.md, scripts/*, sources/* | 재현·근거 확인용이며 모델 학습 입력이 아님 |

## 4. 데이터 생성의 핵심 전제

- Cass Fresh, Cass Light, Cass 0.0/All Zero의 실제 SKU별 월별 판매량·출고량은 공개되어 있지 않다.
- 따라서 타깃 변수는 실제 내부 판매량이 아니라 공개자료 기반 proxy이다.
- 2020~2024년 전체 알코올 맥주 수요 proxy는 공식 연간 anchor에 맞춰 월별로 분해했다.
- 2025년은 공식 연간 출고량이 확정되지 않았으므로 generated/provisional 구간으로 처리한다.
- Google Trends, 뉴스량, 가격 검색량은 절대 수요가 아니라 관심도·이슈 강도 proxy이다.

## 5. 최종 데이터셋 구조

| 변수 그룹 | 변수 수 | 내용 |
| --- | --- | --- |
| 수요 proxy 및 기존 월별 변수 | 38 | 전체 알코올 맥주, 일반 맥주, 저칼로리/라이트, 논알콜/무알콜, Cass 제품군 proxy 및 기본 월별 변수 |
| 날씨·환경 | 67 | 기온, 체감온도, 습도, 강수, 일사, 풍속, 폭염, 열대야, 한파, 대기질, 계절 더미 |
| 이벤트·캘린더 | 32 | 주말, 공휴일, 연휴, KBO, 대형 스포츠, 지역축제, 맥주축제 |
| 뉴스·비정형 | 25 | 맥주/Cass/무알콜/날씨/축제/규제·가격 뉴스량 및 제목 기반 키워드 감성 proxy |
| 가격·경제 | 14 | 수입맥주 단가, 단가 YoY, 가격 검색량, CPI proxy, 가격 인상 이벤트 더미 |

## 6. 예측 타깃 변수

| 타깃 변수 | 의미 | 권장 활용 |
| --- | --- | --- |
| alcoholic_beer_total_proxy_kl | 전체 알코올 맥주 월별 수요 proxy | 가장 안정적인 1차 모델 타깃 |
| regular_beer_excluding_low_calorie_proxy_kl | 저칼로리/라이트를 제외한 일반 맥주 proxy | 일반 맥주 세그먼트 예측 |
| low_calorie_light_beer_proxy_kl | 저칼로리/라이트 맥주 proxy | Cass Light와 라이트 세그먼트 성장 분석 |
| nonalcoholic_beer_proxy_kl | 논알콜/무알콜 맥주 volume proxy | 무알콜 세그먼트 수요 분석 |
| cass_fresh_proxy_kl | Cass Fresh 월별 수요 proxy | 제품군 생산계획 시나리오 |
| cass_light_proxy_kl | Cass Light 월별 수요 proxy | 라이트 제품 생산계획 시나리오 |
| cass_0_0_or_all_zero_proxy_kl | Cass 0.0/All Zero 월별 수요 proxy | 무알콜 제품 생산계획 시나리오 |

## 7. 수요 proxy 생성 방식

### 7.1 전체 알코올 맥주 시장

연간 맥주 apparent market은 국내 맥주 출고량에 HS2203 맥주 수입량을 더하고 수출량을 차감해 계산했다. 연간 총량은 공식 통계 기반 anchor로 고정하고, 월별 분포는 HS2203 월별 수입량과 Google Trends 맥주 검색 관심도를 결합한 월별 weight로 분해했다.

월별 알코올 맥주 수요 proxy = 연간 맥주 apparent market × normalize(0.45 × 월별 HS2203 수입량 + 0.55 × Google Trends 맥주)

### 7.2 일반 맥주와 저칼로리/라이트 맥주

저칼로리/라이트 맥주는 Cass Light 공개 점유율과 light beer 성장 보도를 anchor로 사용했다. 일반 맥주는 전체 알코올 맥주 수요에서 저칼로리/라이트 맥주 proxy를 차감해 계산했다.

연간 light/low-calorie share는 2020년 2.4%에서 2025년 4.7%로 증가하는 구조로 설정했다.

### 7.3 논알콜/무알콜 맥주

논알콜/무알콜은 알코올 맥주 출고량 통계와 시장 정의가 다를 수 있으므로 별도 시장규모 금액 anchor를 사용했다. 월별 가중치는 무알콜 맥주와 논알콜 맥주 Google Trends를 결합해 만들었고, volume proxy는 시장가치 proxy를 4.0백만원/kL 가정으로 환산했다.

### 7.4 Cass 제품군 배분

Cass Fresh와 Cass Light는 공개된 가정시장 점유율을 기반으로 시나리오용 proxy를 생성했다. Cass 0.0/All Zero는 정확한 공개 점유율이 없어 무·비알코올 시장 내 Cass 계열 가정 점유율을 적용했다. 이 값들은 실제 판매량이 아니라 생산계획 시나리오 입력값으로 해석해야 한다.

## 8. 외생변수 정리

### 8.1 날씨·환경

서울 기준 월별 날씨와 대기질을 수치화했다. 맥주 수요의 계절성, 더위, 야외활동 영향을 설명하기 위한 변수군이다.

| 대표 변수 | 의미 |
| --- | --- |
| seoul_avg_temp_c | 월평균기온 |
| seoul_avg_apparent_temp_c | 월평균 체감온도 |
| seoul_relative_humidity_mean_pct | 평균 습도 |
| seoul_precipitation_mm | 월강수량 |
| seoul_hot_days_30c | 30℃ 이상 일수 |
| seoul_heatwave_warning_days_33c | 33℃ 이상 일수 |
| seoul_tropical_nights_25c | 열대야 proxy |
| seoul_pm25_ug_m3 | 초미세먼지 |

### 8.2 이벤트·캘린더

공휴일, 연휴, KBO, 대형 스포츠, 지역축제, 맥주축제 변수를 월별로 집계했다. 모임, 외식, 관람, 관광 수요를 설명하기 위한 변수군이다.

| 대표 변수 | 의미 |
| --- | --- |
| public_holiday_count_kr | 월별 공휴일 수 |
| longest_consecutive_nonwork_days | 최장 연휴 길이 |
| kbo_regular_games | KBO 정규시즌 경기 수 |
| kbo_postseason_games | KBO 포스트시즌 경기 수 |
| sports_major_event_days | 월드컵/올림픽/아시안게임 등 대형 스포츠 이벤트 일수 |
| regional_festival_offline_or_hybrid_count | 오프라인/혼합 지역축제 수 |
| beer_festival_offline_or_hybrid_count_keyword | 맥주/비어/치맥 키워드 축제 수 |

### 8.3 뉴스·비정형

Google News RSS 검색 결과를 월별·카테고리별 기사 수와 제목 기반 키워드 감성 proxy로 변환했다. 절대 보도량이 아니라 월별 이슈 강도 proxy로 사용한다.

| 대표 변수 | 의미 |
| --- | --- |
| news_beer_general_count | 맥주 일반 뉴스 수 |
| news_cass_ob_count | Cass/OB맥주 관련 뉴스 수 |
| news_nonalc_count | 무알콜/논알콜 맥주 뉴스 수 |
| news_weather_demand_count | 폭염·날씨·맥주/음료 관련 뉴스 수 |
| news_festival_beer_count | 축제·페스티벌·맥주축제 뉴스 수 |
| news_regulation_health_price_count | 규제·주세·가격·건강·절주 뉴스 수 |
| news_sentiment_balance_proxy | 제목 내 긍정 키워드 count - 부정 키워드 count |

### 8.4 가격·경제

수입맥주 단가, 가격 관련 검색량, CPI proxy, OB맥주 가격 인상 이벤트를 월별 변수로 정리했다. 가격 민감도와 비용 압력을 설명하기 위한 변수군이다.

| 대표 변수 | 의미 |
| --- | --- |
| imported_beer_unit_value_usd_per_kg | UN Comtrade HS2203 수입액 / 수입중량 |
| imported_beer_unit_value_yoy_pct | 수입맥주 단가 전년동월비 |
| google_trends_beer_price | 맥주 가격 검색 관심도 |
| google_trends_alcohol_price | 주류 가격 검색 관심도 |
| price_pressure_search_index | 가격 관련 검색량 합계 |
| korea_cpi_generated_index_2020_01_100 | 연간 CPI 상승률 anchor 기반 월별 CPI proxy |
| ob_major_price_increase_event_dummy | 2024-04, 2025-04 가격 인상 이벤트 더미 |

## 9. 검증 결과

최종 병합 데이터셋은 2020-01부터 2025-12까지 72개월을 포함하며, 주요 외생변수 원천의 월별 범위가 일치하도록 병합했다. 변수 사전은 최종 데이터셋의 176개 컬럼 전체를 설명한다.

| 검증 항목 | 값 |
| --- | --- |
| rows | 72 |
| columns | 176 |
| start_month | 2020-01 |
| end_month | 2025-12 |
| weather_source_months | 72 |
| weather_source_columns | 68 |
| events_source_months | 72 |
| events_source_columns | 33 |
| news_source_months | 72 |
| news_source_columns | 26 |
| econ_source_months | 72 |
| econ_source_columns | 15 |

## 10. 모델링 권장 구조

- Train: 2020-01 ~ 2023-12
- Validation/Test: 2024-01 ~ 2024-12
- Scenario/Forecast: 2025-01 ~ 2025-12
- Baseline: Seasonal Naive 또는 전년 동월값
- 추천 모델: SARIMAX, LightGBM/XGBoost, Ridge/Lasso
- 발표 핵심: 외생변수를 넣은 모델이 단순 계절 기준선 대비 예측오차를 얼마나 줄이는지 제시

## 11. 주의사항

- 타깃 자체가 proxy이므로 실제 내부 판매량 예측 정확도로 해석하면 안 된다.
- 날씨, 여름 더미, KBO, 축제, 검색량은 계절성이 겹칠 수 있으므로 feature selection 또는 regularization이 필요하다.
- 뉴스량과 검색량은 당월 수요와 동시에 움직이는 nowcasting 변수일 수 있어 순수 사전예측에서는 lag 처리를 권장한다.
- 2025년은 generated/provisional 구간이므로 검증용보다 시나리오/forecast 구간으로 사용하는 것이 안전하다.
- Cass 제품군 proxy는 제품별 실제 출하량이 아니라 생산 믹스와 병목 공정 논의를 위한 시나리오 입력값이다.

## 12. 결론

최종적으로 공개자료 기반 수요 proxy와 외생변수를 하나의 월별 학습 입력 데이터셋으로 통합했다. 실제 모델 담당자는 원천/중간 파일을 별도로 사용할 필요 없이 final_cass_demand_model_dataset_with_exogenous_2020_2025.csv를 기준으로 학습을 시작하면 된다. 변수 의미와 주의사항은 final_model_variable_dictionary.csv에서 확인하고, 병합 및 범위 검증은 final_exogenous_dataset_validation.csv를 참고하면 된다.
