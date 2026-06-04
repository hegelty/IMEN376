# Final Presentation AI Package

발표자료 AI 예측 파트에 넣을 최종 자료 모음입니다.

## 1. 보고서

- `AI_forecasting_report_section.md`  
  발표 보고서에 바로 넣을 수 있는 AI 예측 파트 최종 서술본입니다.

## 2. 발표용 그래프

폴더: `figures/`

권장 사용 순서:

1. `01_target_construction_apparent_consumption.png`  
   최종 target 구성: 국내 출고량 + HS2203 수입 - HS2203 수출

2. `02_backtest_actual_vs_chronos2_seasonal.png`  
   Chronos-2와 Seasonal Naive의 백테스트 예측 비교

3. `03_model_comparison_mase.png`  
   다양한 모델의 MASE 비교

4. `04_model_comparison_wape.png`  
   다양한 모델의 WAPE 비교

5. `05_absolute_error_over_time.png`  
   Chronos-2와 Seasonal Naive의 월별 절대오차 비교

6. `06_nonalc_zero_segment_proxy.png`  
   논알콜/무알콜 및 Cass 0.0 proxy 세그먼트

7. `07_event_stress_months_on_target.png`  
   이벤트/스트레스 월 표시

8. `08_final_model_summary_table.png`  
   최종 모델 결과 요약표

## 3. 데이터

폴더: `data/`

- `user_method_integrated_dataset.csv`  
  최종 target과 세그먼트가 포함된 통합 데이터셋입니다.

## 4. 모델 결과

폴더: `model_outputs/`

- `user_method_all_model_metrics.csv`  
  Chronos-2, Seasonal Naive, ML 모델 전체 성능 비교

- `chronos2_user_method_predictions.csv`  
  Chronos-2 예측 결과

- `user_method_model_backtest_predictions.csv`  
  다양한 ML 모델 백테스트 예측 결과

## 5. 스크립트

폴더: `scripts/`

- `build_user_method_target_and_models.py`  
  최종 target 생성 및 ML 모델 비교

- `run_chronos2_user_method_target.py`  
  Chronos-2 실행

- `make_presentation_figures.py`  
  발표용 그래프 생성

## 핵심 결과

| 모델 | MASE | WAPE |
|---|---:|---:|
| Chronos-2 | 0.387 | 0.0168 |
| Seasonal Naive | 0.445 | 0.0193 |
| GradientBoosting + lagged Google Trends | 0.615 | 0.0267 |

최종 발표 메시지:

> 국내 맥주 apparent consumption을 target으로 사용한 최종 비교에서 Chronos-2가 가장 낮은 예측오차를 기록했다. 따라서 Chronos-2를 최종 AI forecast model로 채택하고, Seasonal Naive를 sanity-check baseline으로 병행하며, 전달 Google Trends 기반 모델은 운영 보조 신호로 활용한다.
