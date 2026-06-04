# 사용자 데이터 예측 모델 테스트 요약

기준 자료:
- `/home/hegelty/POM/final_report.md`
- `/home/hegelty/POM/ai_model_io_summary.md`

실제 테스트에 사용한 데이터:
- `/home/hegelty/programming/IMEN343/research_ob_cass_demand/data/final_cass_demand_model_dataset_with_exogenous_2020_2025.csv`

## 1) 테스트 설정
- 타깃 변수: `alcoholic_beer_total_proxy_kl`
- 학습 구간: 2020-01 ~ 2023-12 (48개월)
- 테스트 구간: 2024-01 ~ 2025-12 (24개월)
- 비교 모델:
  - Seasonal Naive (`t-12`)
  - Ridge 회귀 (lag + 계절성 + 날씨/이벤트/뉴스/가격 변수)
- 검증 방식: expanding-window rolling backtest

## 2) 사용한 주요 입력 변수
- `lag_1`, `lag_12`
- `month_sin_annual`, `month_cos_annual`
- `seoul_avg_temp_c`
- `seoul_heatwave_warning_days_33c`
- `seoul_tropical_nights_25c`
- `public_holiday_count_kr`
- `kbo_regular_games`
- `sports_major_event_days`
- `news_total_index`
- `news_sentiment_balance_proxy`
- `imported_beer_unit_value_yoy_pct`
- `ob_major_price_increase_event_dummy`
- `is_year_end_nov_dec`
- `is_summer_peak_jul_aug`

## 3) 결과
### 전체 테스트 (24개월)
| 모델 | MASE | WAPE | RMSE |
|---|---:|---:|---:|
| Ridge (alpha=100) | 0.675 | 0.066 | 12,057 |
| Seasonal Naive | 1.137 | 0.112 | 19,960 |

### 이벤트 월 테스트
이벤트 월 정의: 폭염/열대야/KBO 경기 많음/주요 스포츠 이벤트 존재

| 모델 | MASE | WAPE | RMSE |
|---|---:|---:|---:|
| Ridge (alpha=100) | 0.725 | 0.065 | 12,988 |
| Seasonal Naive | 1.123 | 0.101 | 19,640 |

## 4) 해석
- 이번 사용자 데이터에서는 **Ridge 기반 모델이 Seasonal Naive보다 명확히 우세**했습니다.
- 특히 이벤트 월에서도 오차가 더 낮아, 보고서의 핵심 가설(이벤트/외생변수가 중요함)과 방향성이 맞습니다.
- 다만 현재 타깃은 실제 ERP 출고량이 아니라 **proxy 수요 변수**라서, 결과는 운영용 최종 성능이라기보다 **진단용 검증 결과**로 보는 게 안전합니다.

## 5) 산출물
- 스크립트: `/home/hegelty/.openclaw/workspace/model_test_on_user_data.py`
- 예측 결과: `/home/hegelty/.openclaw/workspace/model_test_outputs/rolling_predictions.csv`
- 평가 지표: `/home/hegelty/.openclaw/workspace/model_test_outputs/metrics.csv`
- 실행 요약: `/home/hegelty/.openclaw/workspace/model_test_outputs/summary.json`

## 6) 다음 추천
1. 같은 방식으로 `cass_fresh_proxy_kl` 타깃도 별도 모델링
2. 2026 예측용 future feature 생성 후 월별 forecast 출력
3. 실제 발표용으로 그래프 1장(실제 vs 예측) 추가
