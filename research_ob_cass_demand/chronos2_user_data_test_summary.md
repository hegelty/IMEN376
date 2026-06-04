# Chronos-2 사용자 데이터 테스트 요약

## 실행 환경
- 모델: Amazon Chronos-2 (`amazon/chronos-2`)
- 실행 장치: GPU (`NVIDIA GeForce RTX 4060 Laptop GPU`)
- venv: `.venv_chronos_test`
- 스크립트: `scripts/run_chronos2_user_test.py`

## 데이터 / 설정
- 데이터: `data/final_cass_demand_model_dataset_with_exogenous_2020_2025.csv`
- 타깃: `alcoholic_beer_total_proxy_kl`
- 학습: 2020-01 ~ 2023-12 (48개월)
- 테스트: 2024-01 ~ 2025-12 (24개월)
- 모델 방식: Chronos-2 covariate-informed zero-shot
- Covariates:
  - `seoul_avg_temp_c`
  - `seoul_heatwave_warning_days_33c`
  - `seoul_tropical_nights_25c`
  - `kbo_regular_games`
  - `sports_major_event_days`
  - `public_holiday_count_kr`
  - `ob_major_price_increase_event_dummy`

## 결과
| 모델 | split | n | MASE | WAPE | RMSE |
|---|---|---:|---:|---:|---:|
| Chronos-2 Covariate | 전체 | 24 | 0.800 | 0.0785 | 14,711 |
| Seasonal Naive | 전체 | 24 | 1.137 | 0.1115 | 19,960 |
| Chronos-2 Covariate | 이벤트 월 | 10 | 1.051 | 0.0946 | 19,003 |
| Seasonal Naive | 이벤트 월 | 10 | 1.123 | 0.1010 | 19,640 |
| Chronos-2 Covariate | 일반 월 | 14 | 0.622 | 0.0652 | 10,632 |
| Seasonal Naive | 일반 월 | 14 | 1.147 | 0.1203 | 20,185 |

## 해석
- 같은 Chronos-2 모델을 사용자 데이터에 적용하면, 전체 테스트에서 Seasonal Naive보다 성능이 좋다.
- 전체 MASE는 `1.137 → 0.800`으로 개선됐다.
- 이벤트 월에서도 Chronos-2가 근소하게 우위다 (`1.123 → 1.051`).
- 일반 월에서는 개선 폭이 더 크다 (`1.147 → 0.622`).
- 다만 이전 Ridge 테스트(MASE 0.675)보다는 Chronos-2가 약간 낮은 성능이다. 데이터가 72개월로 작고 proxy 타깃이라, zero-shot foundation model보다 단순 regularized regression이 더 잘 맞은 것으로 보인다.

## 산출물
- `model_outputs_chronos2_user_test/chronos2_predictions_vs_actual.csv`
- `model_outputs_chronos2_user_test/chronos2_metrics.csv`
- `model_outputs_chronos2_user_test/chronos2_summary.json`
