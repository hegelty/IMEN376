# Operational Google Trends Lag Model Report

## Target 생성에는 미사용, 예측에는 전달 Google Trends 사용

**작성일:** 2026-06-04  
**목적:** Google Trends를 target 생성에 쓰지 않고, `t-1` 전달 신호로만 예측 feature에 사용하는 방식 검증  
**산출 폴더:** `final_lagged_google_trends_model_outputs/`

---

## 1. 핵심 결론

Google Trends는 target 생성에 사용하면 circularity / leakage 문제가 생길 수 있다. 그러나 실제 운영 예측에서는 **전달(t-1) Google Trends를 당월(t) 수요 예측 feature로 사용하는 것**은 방어 가능하다.

이번 실험은 다음 원칙으로 수행했다.

| 원칙 | 내용 |
|---|---|
| Target 생성 | Google Trends 미사용 |
| 예측 feature | `t-1` Google Trends만 사용 |
| 금지 | 당월 Google Trends로 당월 수요 예측 |
| 금지 | Google Trends를 target adjustment에 사용 |

결과적으로 전달 Google Trends를 추가한 ML 모델들은 Seasonal Naive 또는 Chronos-2보다 낮은 성능을 보이지 못했다. 따라서 최종 모델에서는 Google Trends lag를 **운영 가능 feature 후보**로 열어두되, 현재 proxy 데이터에서는 성능 개선 근거가 약하다고 정리하는 것이 타당하다.

---

## 2. 사용한 Google Trends lag 변수

다음 변수들을 1개월 lag 처리하여 feature로 사용했다.

| 원 변수 | 사용 feature |
|---|---|
| `google_trends_beer` | `google_trends_beer_lag1` |
| `google_trends_imported_beer` | `google_trends_imported_beer_lag1` |
| `google_trends_nonalc_beer` | `google_trends_nonalc_beer_lag1` |
| `google_trends_cass_beer` | `google_trends_cass_beer_lag1` |
| `google_trends_cass_light` | `google_trends_cass_light_lag1` |
| `google_trends_cass_zero_terms` | `google_trends_cass_zero_terms_lag1` |

---

## 3. 모델 비교 결과

Target: `beer_domestic_volume_adjusted_leakage_safe`  
Test: 2024-01 ~ 2025-12

| 모델 | MASE | WAPE | RMSE |
|---|---:|---:|---:|
| Seasonal Naive | 0.811 | 0.0529 | 10,254 |
| KNN + lagged GT | 1.032 | 0.0673 | 12,609 |
| ExtraTrees + lagged GT | 1.102 | 0.0719 | 12,397 |
| Ridge + lagged GT | 1.158 | 0.0755 | 13,907 |
| Lasso + lagged GT | 1.178 | 0.0768 | 14,600 |
| GradientBoosting + lagged GT | 1.225 | 0.0799 | 14,180 |
| HistGradientBoosting + lagged GT | 1.331 | 0.0867 | 15,427 |
| RandomForest + lagged GT | 1.483 | 0.0967 | 16,097 |
| ElasticNet + lagged GT | 2.370 | 0.1545 | 23,763 |
| SVR-RBF + lagged GT | 4.478 | 0.2919 | 44,862 |

비교를 위해 adjusted target 기준 Chronos-2 결과는 다음과 같다.

| 모델 | MASE | WAPE | RMSE |
|---|---:|---:|---:|
| **Chronos-2 adjusted target** | **0.809** | **0.0527** | **9,633** |
| Seasonal Naive | 0.811 | 0.0529 | 10,254 |

---

## 4. 해석

1. **전달 Google Trends 사용은 방법론적으로 가능하다.**  
   `t-1` 검색량으로 `t` 수요를 예측하면 당월 정보 누수 문제를 피할 수 있다.

2. **하지만 현재 proxy 데이터에서는 성능 개선이 크지 않다.**  
   lagged GT를 넣은 ML 모델 중 가장 좋은 KNN도 MASE 1.032로 Seasonal Naive보다 낮았다.

3. **Chronos-2 adjusted target이 여전히 최종 1위다.**  
   MASE 0.809로 Seasonal Naive 0.811을 근소하게 앞섰다.

4. **Google Trends는 운영 nowcasting 후보로 유지한다.**  
   실제 월별 POS/출고 target이 확보되면 lagged Google Trends의 효과를 다시 평가할 가치가 있다.

---

## 5. 최종 보고서용 문장

> “Google Trends는 proxy target 생성에는 사용하지 않았다. 다만 실제 운영 예측에서는 수요 선행 신호로 활용 가능하므로, contemporaneous value가 아닌 전달(t-1) Google Trends만 별도 operational feature로 테스트했다. 현재 proxy 데이터에서는 lagged Google Trends가 성능 개선을 만들지는 못했으나, 독립적인 실제 출고/POS target이 확보될 경우 demand-sensing feature로 재평가할 수 있다.”

---

## Appendix. 산출 파일

| 파일 | 내용 |
|---|---|
| `scripts/compare_lagged_google_trends_models.py` | 전달 Google Trends 모델 비교 스크립트 |
| `final_lagged_google_trends_model_outputs/lagged_google_trends_model_metrics.csv` | 성능 지표 |
| `final_lagged_google_trends_model_outputs/lagged_google_trends_backtest_predictions.csv` | 백테스트 예측값 |
| `final_lagged_google_trends_model_outputs/lagged_google_trends_summary.json` | 실험 설정 요약 |
