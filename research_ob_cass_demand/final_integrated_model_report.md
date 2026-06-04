# Final Integrated Demand Forecasting Model Report

## OB Cass Demand Forecasting — 0603 Cass Data Collect + User Dataset Integration

**작성일:** 2026-06-04  
**통합 대상:**  
1. `0603 Cass Data Collect/cass_demand_v3_monthly.csv`  
2. `data/final_cass_demand_model_dataset_with_exogenous_2020_2025.csv`  

**최종 산출 폴더:** `final_integrated_model_outputs/`

---

## 1. Executive Summary

본 보고서는 다른 팀원이 작성한 `0603 Cass Data Collect` 자료와 사용자 측 IMEN343 데이터셋을 통합하여 최종 수요예측 모델을 구축한 결과를 정리한다.

가장 중요한 수정사항은 **Google Trends 변수 제거**이다. 사용자 데이터의 일부 수요 proxy는 Google Trends를 활용해 생성되었기 때문에, Google Trends를 다시 모델 입력 변수로 사용하는 것은 **target leakage / circularity** 문제가 될 수 있다. 따라서 최종 통합 모델에서는 모든 Google Trends 계열 변수를 제외했다.

최종 결론은 다음과 같다.

1. **Leakage-safe 최종 평가에서는 Seasonal Naive가 가장 우수했다.**  
   테스트 기간 2024~2025년 24개월 기준 MASE는 Seasonal Naive 0.135로 가장 낮았다.

2. **통합 Ridge와 Chronos-2는 기준선보다 낮은 성능을 보였다.**  
   이는 `beer_domestic_volume` 타깃이 연간 출고량 앵커를 월별 계절 패턴으로 배분한 proxy이기 때문에, 전년 동월 반복 방식에 구조적으로 유리하기 때문이다.

3. **최종 운영 모델은 “Seasonal Naive core + Chronos-2 risk overlay”로 제안한다.**  
   성능평가상 중심 예측값은 Seasonal Naive를 사용하고, 발효탱크 운영에서는 Chronos-2의 Q90 상한을 안전계획값으로 참고한다.

4. **AI 모델은 보조 의사결정 도구로 유지하는 것이 가장 방어 가능하다.**  
   현재 공개/proxy 데이터만으로는 Chronos-2 또는 Ridge가 기준선을 안정적으로 이긴다고 주장하기 어렵다. 그러나 이벤트 월·수요 급등 리스크 판단에는 Chronos-2의 분위수 예측이 운영상 의미가 있다.

---

## 2. 통합 데이터 설계

### 2.1 0603 Cass Data Collect 자료

| 항목 | 내용 |
|---|---|
| 파일 | `0603 Cass Data Collect/cass_demand_v3_monthly.csv` |
| 기간 | 2020-01 ~ 2025-12 |
| 행 수 | 72개월 |
| 주요 타깃 | `beer_domestic_volume` |
| 핵심 변수 | Cass Fresh/Light share, 날씨, KBO, 월드컵, 공휴일, 가격인상 더미 |

0603 자료는 기존 최종 보고서의 Layer A/B/C 구조에 맞게 정리되어 있으며, Chronos-2 모델 산출물도 포함되어 있다. 따라서 최종 통합 모델의 target은 0603 자료의 `beer_domestic_volume`을 사용했다.

### 2.2 사용자 데이터

| 항목 | 내용 |
|---|---|
| 파일 | `data/final_cass_demand_model_dataset_with_exogenous_2020_2025.csv` |
| 기간 | 2020-01 ~ 2025-12 |
| 행 수 | 72개월 |
| 컬럼 수 | 176개 |
| 주요 내용 | 날씨, 뉴스, 축제, 가격, CPI, 공휴일, KBO 등 풍부한 외생변수 |

사용자 데이터는 훨씬 많은 외생변수를 포함한다. 다만 일부 수요 proxy가 Google Trends 기반으로 만들어졌기 때문에, Google Trends 변수는 최종 모델에서 제외했다.

---

## 3. Leakage 검토 및 변수 제외

### 3.1 문제 인식

사용자 데이터 중 일부 타깃 또는 수요 proxy는 Google Trends를 활용해 구성되었다. 이 경우 Google Trends를 다시 예측 변수로 넣으면 다음 문제가 발생한다.

```
Google Trends → target proxy 생성
Google Trends → model feature 입력
```

즉, 모델이 독립적인 외생변수를 학습하는 것이 아니라, 타깃 생성에 이미 들어간 정보를 다시 읽는 구조가 된다. 이는 평가자가 지적한 것처럼 **순환논리 / target leakage**에 해당한다.

### 3.2 최종 제외 변수

최종 모델에서는 다음 변수를 제외했다.

| 제외 변수 | 제외 이유 |
|---|---|
| `google_trends_beer` | target proxy 생성 정보와 중복 가능 |
| `google_trends_imported_beer` | 동일 |
| `google_trends_nonalc_beer` | 동일 |
| `google_trends_cass_beer` | 동일 |
| `google_trends_cass_light` | 동일 |
| `google_trends_cass_zero_terms` | 동일 |
| `price_pressure_search_index` | Google Trends 기반 검색지수 |

이 제거는 최종 모델의 성능을 낮출 수 있지만, 보고서의 신뢰성과 방어 가능성을 높인다.

---

## 4. 최종 모델 후보

최종 통합 데이터셋에서 다음 세 가지 모델을 비교했다.

| 모델 | 설명 | 역할 |
|---|---|---|
| Seasonal Naive | 전년 동월 수요 반복 | 필수 기준선 및 최종 core |
| Final Integrated Ridge | Google Trends 제외 후 lag + 날씨/이벤트/뉴스/가격 변수 사용 | leakage-safe ML 후보 |
| Chronos-2 Covariate | 0603 자료의 Chronos-2 covariate backtest | AI foundation model benchmark |

### 4.1 Final Integrated Ridge 입력 변수

Google Trends를 제외한 후 사용한 주요 변수는 다음과 같다.

- Lag / rolling 변수: `lag_1`, `lag_12`, `rolling_3_mean`, `rolling_6_mean`
- 계절성: `month_sin_annual`, `month_cos_annual`, `month_num`, `quarter`
- 0603 핵심 변수: `temp_avg`, `heatwave_days`, `tropical_night_days`, `kbo_games`, `world_cup_dummy`, `holiday_days`, `import_beer_price_yoy`, `ob_price_hike_dummy`
- Cass 구조: `cass_fresh_share`, `cass_light_share`
- 뉴스/이벤트: `news_total_index`, `news_cass_ob_count`, `news_weather_demand_count`, `regional_festival_count_planned`, `beer_festival_count_keyword`
- 경제/환경: CPI, 수입맥주 단가 YoY, 강수량, 미세먼지, 공휴일/연휴 변수

---

## 5. 백테스트 설계

| 항목 | 설정 |
|---|---|
| 학습 기간 | 2020-01 ~ 2023-12 |
| 테스트 기간 | 2024-01 ~ 2025-12 |
| 테스트 개월 | 24개월 |
| 타깃 | `beer_domestic_volume` |
| 평가 지표 | MASE, WAPE, RMSE |
| 이벤트 월 정의 | 폭염, 열대야, KBO 100경기 이상, 월드컵, 가격인상 월 |

---

## 6. 최종 성능 결과

### 6.1 전체 테스트 성능

| 모델 | n | MASE | WAPE | RMSE |
|---|---:|---:|---:|---:|
| **Seasonal Naive** | 24 | **0.135** | **0.00515** | **747** |
| Final Integrated Ridge | 24 | 0.489 | 0.01859 | 3,466 |
| Chronos-2 Covariate | 24 | 0.750 | 0.02849 | 4,659 |

전체 테스트에서는 Seasonal Naive가 압도적으로 가장 낮은 오차를 보였다. MASE 0.135는 매우 낮은 값으로, 현재 proxy target이 전년 동월 계절성에 강하게 맞춰져 있음을 보여준다.

### 6.2 이벤트 월 성능

| 모델 | n | MASE | WAPE | RMSE |
|---|---:|---:|---:|---:|
| **Seasonal Naive** | 10 | **0.151** | **0.00515** | **828** |
| Final Integrated Ridge | 10 | 0.341 | 0.01162 | 2,225 |
| Chronos-2 Covariate | 10 | 0.713 | 0.02427 | 4,479 |

이벤트 월에서도 Seasonal Naive가 가장 우수했다. 이는 현재 target이 실제 이벤트 수요 변동을 충분히 반영한 실측치라기보다, 연간 앵커 기반 월별 proxy에 가깝기 때문으로 해석된다.

### 6.3 일반 월 성능

| 모델 | n | MASE | WAPE | RMSE |
|---|---:|---:|---:|---:|
| **Seasonal Naive** | 14 | **0.124** | **0.00515** | **684** |
| Final Integrated Ridge | 14 | 0.595 | 0.02464 | 4,130 |
| Chronos-2 Covariate | 14 | 0.776 | 0.03215 | 4,783 |

---

## 7. 최종 모델 선택

### 7.1 성능평가용 최종 모델

성능평가 기준 최종 모델은 다음과 같이 선택한다.

> **Final Evaluation Model = Seasonal Naive**

선택 이유:

1. leakage-safe 통합 데이터에서 가장 낮은 MASE/WAPE/RMSE 기록
2. Google Trends circularity 문제 없음
3. 설명 가능성이 높고, 발표/보고서에서 방어하기 쉬움
4. 현재 target 구조가 전년 동월 기준선에 적합함

### 7.2 운영계획용 최종 모델

발효탱크 운영에서는 단순 평균 오차보다 품절 리스크가 중요하다. 따라서 운영계획용 모델은 다음과 같이 제안한다.

> **Final Operational Model = Seasonal Naive core + Chronos-2 Q90 risk overlay**

운영 규칙:

| 상황 | 계획값 |
|---|---|
| Routine 월 | Seasonal Naive 중심값 |
| 이벤트/고불확실 월 | Chronos-2 Q90 상한 참고 |
| Chronos-2 Q90이 Seasonal Naive보다 높음 | 안전계획값으로 Q90 사용 검토 |
| 발효탱크 용량 부족 | 계획팀 승인 기반 SKU 우선순위 조정 |

이 방식은 평가 지표상 가장 강한 Seasonal Naive를 core로 유지하면서, AI 모델의 장점인 분위수 기반 risk signal을 운영 의사결정에 반영한다.

---

## 8. 2026 최종 예측 / 운영 계획값

최종 산출 파일: `final_integrated_model_outputs/final_selected_2026_forecast.csv`

| 월 | Seasonal Naive | Chronos-2 중앙값 | Chronos-2 Q90 | 권장 계획값 |
|---|---:|---:|---:|---:|
| 2026-01 | 113,192 | 115,066 | 117,701 | 117,701 |
| 2026-02 | 113,192 | 115,164 | 117,752 | 117,752 |
| 2026-03 | 121,376 | 122,795 | 124,885 | 124,885 |
| 2026-04 | 135,552 | 135,821 | 137,805 | 137,805 |
| 2026-05 | 151,921 | 152,442 | 154,590 | 154,590 |
| 2026-06 | 166,097 | 165,912 | 168,430 | 168,430 |
| 2026-07 | 174,281 | 173,734 | 176,728 | 176,728 |
| 2026-08 | 174,281 | 174,322 | 177,382 | 177,382 |
| 2026-09 | 166,097 | 165,587 | 168,424 | 168,424 |
| 2026-10 | 151,921 | 151,564 | 153,803 | 153,803 |
| 2026-11 | 135,552 | 135,224 | 137,204 | 137,204 |
| 2026-12 | 121,376 | 121,620 | 124,264 | 124,264 |

해석:

- 중심 수요는 Seasonal Naive와 Chronos-2가 매우 비슷하다.
- 발효탱크 운영 관점에서는 Chronos-2 Q90을 안전계획값으로 사용하면 품절 리스크를 줄일 수 있다.
- 특히 2026년 6~8월은 여름 성수기 및 월드컵 가능성이 있어 보수적 계획값 적용이 타당하다.

---

## 9. 기존 0603 결과와의 관계

0603 자료에서는 rolling backtest 기준 Chronos-2가 Seasonal Naive를 근소하게 이긴 결과가 있었다.

| 모델 | Rolling MASE |
|---|---:|
| Chronos-2 Rolling | 0.133 |
| Seasonal Naive Rolling | 0.137 |

그러나 최종 통합 실험에서는 다음 조건을 반영했다.

1. 사용자 데이터와 0603 데이터를 통합
2. Google Trends leakage 가능 변수 제거
3. 통합 Ridge 모델 추가
4. 동일 2024~2025 holdout에서 후보 모델 비교

이 조건에서는 Seasonal Naive가 가장 우수했다. 따라서 최종 보고서에서는 다음처럼 표현하는 것이 가장 안전하다.

> “Chronos-2는 0603 rolling 실험에서 기준선을 근소하게 개선했으나, Google Trends leakage를 제거한 최종 통합 holdout에서는 Seasonal Naive가 가장 강한 기준선으로 확인되었다. 따라서 최종 운영안은 Seasonal Naive를 core forecast로 사용하고, Chronos-2 분위수 예측을 risk overlay로 활용한다.”

---

## 10. 한계 및 향후 개선

| 한계 | 설명 | 개선 방향 |
|---|---|---|
| Target이 proxy | 실제 OB 내부 SKU 판매량이 아님 | ERP/SAP 월별 SKU demand 확보 |
| 연간 앵커 월별 배분 | Seasonal Naive에 구조적으로 유리 | 실제 월별 출고량 확보 |
| Google Trends 제외 | leakage 방지를 위해 일부 설명력 포기 | 독립 POS/주문 데이터 확보 |
| 이벤트 효과 약함 | proxy target이 실제 이벤트 변동을 충분히 반영하지 못함 | 실측 주문/프로모션/채널 데이터 필요 |
| SKU 검증 불가 | Cass Fresh/Light 실제 성능 주장 불가 | SKU-level target 수집 |

---

## 11. 최종 결론

최종 통합 모델링 결과, 현재 공개/proxy 데이터 조건에서는 **Seasonal Naive가 가장 강한 예측 모델**로 확인되었다. 이는 AI 모델의 실패라기보다, 현재 target이 연간 앵커 기반 월별 proxy이므로 전년 동월 반복 기준선에 매우 유리하게 설계되어 있기 때문이다.

따라서 본 프로젝트의 최종 모델 제안은 다음과 같다.

1. **성능평가용 최종 모델:** Seasonal Naive  
2. **운영계획용 최종 모델:** Seasonal Naive core + Chronos-2 Q90 risk overlay  
3. **AI 역할:** 중심 예측값 단독 대체가 아니라, 이벤트/고불확실 월의 안전재고 및 발효탱크 검토 신호 제공  
4. **최종 메시지:** Google Trends leakage를 제거한 보수적 평가에서도 baseline을 명확히 설정했고, AI는 risk-aware planning layer로 통합 가능하다.

이 결론은 평가자가 지적할 수 있는 leakage 문제를 선제적으로 반영하므로, 기존 “AI가 무조건 이겼다”는 주장보다 훨씬 방어 가능하고 현실적인 최종안이다.

---

## Appendix. 산출 파일

| 파일 | 내용 |
|---|---|
| `scripts/build_final_integrated_model.py` | 최종 통합 데이터셋 및 모델 실행 스크립트 |
| `final_integrated_model_outputs/integrated_model_dataset.csv` | 0603 + 사용자 데이터 통합본 |
| `final_integrated_model_outputs/final_model_metrics.csv` | 최종 모델 성능 비교 |
| `final_integrated_model_outputs/final_backtest_predictions.csv` | 2024~2025 백테스트 예측값 |
| `final_integrated_model_outputs/final_2026_forecast.csv` | Ridge/Chronos blend 참고 예측 |
| `final_integrated_model_outputs/final_selected_2026_forecast.csv` | 최종 선택 운영 예측값 |
| `final_integrated_model_outputs/final_model_summary.json` | 모델 설정 및 leakage 제외 변수 기록 |
