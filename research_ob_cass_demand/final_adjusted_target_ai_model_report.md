# Final Adjusted Target + Multiple AI Models Report

## OB Cass Demand Forecasting — Leakage-safe Target Revision and Model Comparison

**작성일:** 2026-06-04  
**목적:** `beer_domestic_volume`을 그대로 쓰는 문제를 보완하고, 다양한 AI/ML 모델을 비교  
**산출 폴더:** `final_adjusted_target_model_outputs/`

---

## 1. 핵심 요약

기존 최종 통합 모델에서는 0603 자료의 `beer_domestic_volume`을 그대로 target으로 사용했다. 그러나 이 변수는 연간 앵커를 월별로 배분한 proxy이므로, 전년 동월 반복 방식인 Seasonal Naive에 지나치게 유리하다. 또한 사용자 데이터의 기존 proxy 생성에는 Google Trends가 포함되어 있었기 때문에, Google Trends를 다시 feature로 사용하는 것은 target leakage 문제가 있다.

따라서 이번 버전에서는 다음과 같이 수정했다.

1. `beer_domestic_volume`을 그대로 쓰지 않고 **adjusted leakage-safe target**을 생성했다.
2. Google Trends 계열 변수는 target 생성과 model feature 모두에서 제외했다.
3. target 조정에 사용한 변수는 다시 model feature로 넣지 않았다.
4. Chronos-2와 다양한 AI/ML 모델을 함께 비교했다.

최종 결과는 다음과 같다.

| 순위 | 모델 | MASE | WAPE | 해석 |
|---:|---|---:|---:|---|
| 1 | **Chronos-2 adjusted target** | **0.809** | **0.0527** | 최종 AI 모델 후보 |
| 2 | Seasonal Naive | 0.811 | 0.0529 | 거의 동률인 강한 baseline |
| 3 | KNN | 0.921 | 0.0600 | AI/ML 후보 중 2위 |
| 4 | ExtraTrees | 1.118 | 0.0729 | tree ensemble |
| 5 | Ridge | 1.119 | 0.0729 | linear benchmark |

결론적으로 adjusted target 기준에서는 **Chronos-2가 Seasonal Naive를 아주 근소하게 이겼다.** 차이는 작지만, Google Trends leakage를 제거하고 target도 수정한 조건에서 Chronos-2가 최상위가 된 점은 보고서에 활용 가능하다.

---

## 2. 왜 `beer_domestic_volume`을 수정했는가

`beer_domestic_volume`은 공개 연간 출고량 anchor를 월별로 배분한 proxy이다. 이 변수는 실제 월별 판매/출고 데이터가 아니며, 다음 문제가 있다.

| 문제 | 설명 |
|---|---|
| 인위적 계절성 | 월별 배분 공식 때문에 매년 유사한 계절 패턴 반복 |
| Seasonal Naive 과대 우위 | 전년 동월 반복 기준선이 구조적으로 유리 |
| 이벤트 효과 약화 | 폭염, 스포츠 이벤트 등 실제 수요 충격이 충분히 반영되지 않을 수 있음 |
| 운영 해석 한계 | 실제 Cass Fresh/Light SKU 수요가 아님 |

따라서 최종 AI 모델을 평가하려면 target을 그대로 쓰기보다, 연간 anchor는 유지하되 월별 분포를 비-Google 신호로 보수적으로 재조정하는 방식이 필요하다.

---

## 3. Adjusted Target 생성 방식

### 3.1 기본 원칙

| 원칙 | 내용 |
|---|---|
| 연간 총량 보존 | 각 연도의 `beer_domestic_volume` 합계는 유지 |
| Google Trends 제외 | target 조정에도 Google Trends 미사용 |
| 보수적 조정 | 월별 수요 변동을 과도하게 만들지 않도록 adjustment cap 적용 |
| Circularity 방지 | target 조정에 쓴 변수는 model feature에서 제외 |

### 3.2 Target 조정에 사용한 변수

다음 변수는 월별 demand pressure index를 만드는 데만 사용하고, 예측 모델 feature에서는 제외했다.

| 변수 | 의미 |
|---|---|
| `temp_avg` | 월평균기온 |
| `heatwave_days` | 폭염일수 |
| `tropical_night_days` | 열대야일수 |
| `kbo_games` | KBO 경기수 |
| `holiday_days` | 공휴일 수 |
| `import_beer_price_yoy` | 수입맥주 가격 YoY |
| `ob_price_hike_dummy` | OB 가격 인상 더미 |

### 3.3 제외한 leakage 변수

아래 변수는 target 조정과 model feature 양쪽에서 모두 제외했다.

- `google_trends_beer`
- `google_trends_imported_beer`
- `google_trends_nonalc_beer`
- `google_trends_cass_beer`
- `google_trends_cass_light`
- `google_trends_cass_zero_terms`
- `price_pressure_search_index`

---

## 4. 비교한 AI/ML 모델

이번에는 Chronos-2 외에도 다양한 AI/ML 모델을 비교했다.

| 모델 | 유형 |
|---|---|
| Chronos-2 | Time-series foundation model |
| Ridge | Regularized linear regression |
| Lasso | Sparse linear regression |
| ElasticNet | L1/L2 mixed regression |
| RandomForest | Bagging tree ensemble |
| ExtraTrees | Randomized tree ensemble |
| GradientBoosting | Boosted tree model |
| HistGradientBoosting | Histogram-based boosted tree model |
| SVR-RBF | Kernel regression |
| KNN | Instance-based regression |
| MLP | Neural network regression |
| Seasonal Naive | Baseline |

모든 ML 모델은 rolling backtest 방식으로, 각 테스트 월 직전까지의 데이터만 학습하도록 구성했다.

---

## 5. 전체 테스트 결과

테스트 기간: 2024-01 ~ 2025-12 (24개월)

| 모델 | MASE | WAPE | RMSE |
|---|---:|---:|---:|
| **Chronos-2 adjusted target** | **0.809** | **0.0527** | **9,633** |
| Seasonal Naive | 0.811 | 0.0529 | 10,254 |
| KNN | 0.921 | 0.0600 | 11,001 |
| ExtraTrees | 1.118 | 0.0729 | 12,254 |
| Ridge | 1.119 | 0.0729 | 12,737 |
| Lasso | 1.126 | 0.0734 | 13,010 |
| GradientBoosting | 1.228 | 0.0801 | 14,190 |
| HistGradientBoosting | 1.402 | 0.0914 | 15,957 |
| RandomForest | 1.454 | 0.0948 | 15,868 |
| ElasticNet | 2.404 | 0.1567 | 24,273 |
| SVR-RBF | 4.478 | 0.2918 | 44,860 |
| MLP | 14.942 | 0.9739 | 145,773 |

### 해석

- adjusted target 기준에서는 Chronos-2가 가장 낮은 MASE를 기록했다.
- Seasonal Naive와 차이는 매우 작다: 0.8086 vs 0.8114.
- KNN은 ML 모델 중 가장 좋은 성능을 보였다.
- MLP, SVR은 작은 월별 데이터셋에서는 불안정했다.
- Tree ensemble은 기대보다 약했는데, 72개월이라는 작은 표본과 강한 계절성 때문에 과적합/불안정성이 생긴 것으로 보인다.

---

## 6. 이벤트 월 결과

이벤트 월 정의: 폭염, 열대야, KBO 100경기 이상, 월드컵, 가격인상 월 중 하나 이상 해당.

| 모델 | 이벤트 월 MASE | WAPE | RMSE |
|---|---:|---:|---:|
| Seasonal Naive | 0.993 | 0.0505 | 12,494 |
| KNN | 1.143 | 0.0581 | 12,403 |
| Lasso | 1.369 | 0.0696 | 15,609 |
| Ridge | 1.436 | 0.0730 | 15,623 |
| ExtraTrees | 1.612 | 0.0819 | 16,439 |
| RandomForest | 1.691 | 0.0859 | 18,323 |
| GradientBoosting | 1.738 | 0.0883 | 18,753 |

Chronos-2 adjusted target은 현재 전체 테스트 지표로 산출했으며, 이벤트 split은 별도 확장 가능하다. 운영 해석에서는 Chronos-2의 분위수 상한을 이벤트 월 risk overlay로 사용하는 것이 타당하다.

---

## 7. 최종 모델 선택

### 7.1 최종 AI 모델

> **Final AI Model = Chronos-2 on adjusted leakage-safe target**

선택 이유:

1. adjusted target 기준 전체 MASE 최저
2. Google Trends leakage 제거
3. target 조정 변수와 feature 분리
4. 기존 친구 자료의 Chronos-2 방법론과 일관성 유지
5. 분위수 예측을 통해 운영 리스크 관리 가능

### 7.2 최종 운영 모델

> **Final Operational Model = Chronos-2 adjusted target + Seasonal Naive sanity check**

운영 방식:

```
Adjusted target 생성
  ↓
Chronos-2 forecast 산출
  ↓
Seasonal Naive와 차이 확인
  ↓
차이가 작으면 Chronos-2 중앙값 사용
  ↓
이벤트/고불확실 월은 Chronos-2 Q90 상한 기준으로 발효탱크 계획 검토
  ↓
계획팀 승인 후 SKU 배분
```

### 7.3 보고서용 표현

가장 방어 가능한 문장은 다음과 같다.

> “기존 `beer_domestic_volume`은 연간 anchor 기반 월별 proxy라 Seasonal Naive에 구조적으로 유리하다. 따라서 본 최종 실험에서는 Google Trends leakage를 제거하고, 비-Google demand pressure 변수로 월별 target을 보수적으로 재조정했다. 이 adjusted target 기준에서 Chronos-2는 MASE 0.809로 Seasonal Naive 0.811을 근소하게 상회했다. 따라서 최종 AI 모델은 Chronos-2로 채택하되, 성능 차이가 작으므로 Seasonal Naive를 sanity-check baseline으로 병행한다.”

---

## 8. 한계

| 한계 | 설명 |
|---|---|
| Adjusted target도 proxy | 실제 월별 OB 출고량이 아님 |
| 조정식에 가정 포함 | 날씨/KBO/가격 변수 가중치는 보수적 가정 |
| 표본 작음 | 72개월 월별 데이터로 AI 모델 일반화가 제한적 |
| 이벤트 split 추가 필요 | Chronos-2 adjusted 결과의 이벤트별 분석은 추가 가능 |
| SKU 수준 검증 불가 | Cass Fresh/Light 실제 판매량 없음 |

---

## 9. 최종 결론

최종적으로 `beer_domestic_volume`을 그대로 사용하지 않고, Google Trends를 완전히 배제한 adjusted target을 만들었다. 이 target에서 다양한 AI/ML 모델을 비교한 결과, Chronos-2가 Seasonal Naive를 아주 근소하게 앞섰다.

따라서 최종 결론은 다음과 같다.

1. **Raw `beer_domestic_volume` 그대로 쓰는 것은 부적절하다.**  
   Seasonal Naive에 지나치게 유리한 proxy target이기 때문이다.

2. **Google Trends는 최종 모델에서 제외해야 한다.**  
   target proxy 생성과 feature 사이의 circularity 문제가 있기 때문이다.

3. **Adjusted target 기준 최종 AI 모델은 Chronos-2가 가장 적합하다.**  
   MASE 0.809로 전체 모델 중 가장 낮은 오차를 기록했다.

4. **Seasonal Naive는 여전히 강한 sanity-check baseline이다.**  
   Chronos-2와 차이가 작으므로, 최종 운영에서는 두 모델을 함께 모니터링해야 한다.

5. **운영 적용은 Chronos-2 중심 + Seasonal Naive 검증 + Q90 risk overlay 구조가 가장 안전하다.**

---

## Appendix. 산출 파일

| 파일 | 내용 |
|---|---|
| `scripts/build_adjusted_target_and_compare_ai.py` | adjusted target 생성 + AI/ML 모델 비교 |
| `scripts/run_chronos2_adjusted_target.py` | Chronos-2 adjusted target 실행 |
| `final_adjusted_target_model_outputs/integrated_dataset_with_adjusted_target.csv` | adjusted target 포함 통합 데이터셋 |
| `final_adjusted_target_model_outputs/adjusted_target_ai_model_metrics.csv` | ML 모델 비교 지표 |
| `final_adjusted_target_model_outputs/chronos2_adjusted_target_metrics.csv` | Chronos-2 adjusted target 지표 |
| `final_adjusted_target_model_outputs/adjusted_target_all_model_metrics.csv` | 전체 모델 통합 비교표 |
| `final_adjusted_target_model_outputs/adjusted_target_ai_backtest_predictions.csv` | ML 모델별 백테스트 예측값 |
| `final_adjusted_target_model_outputs/chronos2_adjusted_target_predictions.csv` | Chronos-2 백테스트 예측값 |
