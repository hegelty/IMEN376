# Modeling Handoff Data

모델 담당자가 바로 볼 핵심 데이터만 따로 모아둔 폴더입니다.

## 가장 먼저 볼 파일
- `final_cass_demand_model_dataset_with_exogenous_2020_2025.csv`
  - 최종 모델 입력 파일
- `final_model_variable_dictionary.csv`
  - 변수 설명
- `final_exogenous_dataset_validation.csv`
  - 병합/결측 검증

## 타깃/기초 수요 proxy
- `monthly_beer_segment_modeling_dataset_2020_2025.csv`

## 외생변수 원천(월별 가공 완료본)
- `exog_weather_environment_monthly.csv`
- `exog_events_calendar_monthly.csv`
- `exog_news_unstructured_monthly.csv`
- `exog_economic_price_monthly.csv`

## 참고용 세부 월별 입력
- `monthly_google_trends_beer_segments_2020_2026.csv`
- `monthly_google_trends_cass_products_2020_2026.csv`
- `monthly_hs2203_comtrade_korea_2020_2025.csv`
- `monthly_weather_seoul_open_meteo_2020_2025.csv`

## 제외한 것
- 원문 기사 sample
- 스크립트
- 소스 PDF/TXT
- 중간 조사 메모

즉, **모델링에 바로 쓰거나 검증에 직접 필요한 것만 남겼습니다.**
