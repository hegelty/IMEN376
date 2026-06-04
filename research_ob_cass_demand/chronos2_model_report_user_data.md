# Chronos-2 기반 OB Cass 수요예측 모델 테스트 보고서

## AI-Driven Demand Forecasting for Fermentation Capacity Allocation  
### 사용자 데이터 적용 실험 — OB Brewery / Cass Beer Supply Chain

**작성일:** 2026-06-04  
**데이터 기간:** 2020-01 ~ 2025-12 (72개월)  
**테스트 기간:** 2024-01 ~ 2025-12 (24개월)  
**모델:** Amazon Chronos-2 (`amazon/chronos-2`)  
**실행 환경:** NVIDIA GeForce RTX 4060 Laptop GPU

---

## 1. Executive Summary

본 보고서는 기존 `final_report.md`, `ai_model_io_summary.md`에서 사용한 AI 수요예측 접근법을 사용자 데이터셋에 동일하게 적용하여 검증한 결과를 정리한다. 기존 자료의 핵심 모델은 Amazon Chronos-2 zero-shot 시계열 파운데이션 모델이며, 본 실험 역시 같은 모델을 사용했다.

핵심 결과는 다음과 같다.

1. **Chronos-2 GPU 실행 성공:** 사용자 환경의 RTX 4060 Laptop GPU에서 `amazon/chronos-2` 모델을 실행했다.
2. **기준선 대비 성능 개선:** 2024~2025년 24개월 백테스트에서 Chronos-2 Covariate 모델은 Seasonal Naive보다 낮은 오차를 기록했다.
   - Chronos-2 MASE: **0.800**
   - Seasonal Naive MASE: **1.137**
3. **이벤트 월에서도 개선 확인:** 폭염·열대야·KBO 경기 집중 월 등 이벤트 월에서 Chronos-2는 Seasonal Naive보다 근소하게 우세했다.
   - Chronos-2 이벤트 월 MASE: **1.051**
   - Seasonal Naive 이벤트 월 MASE: **1.123**
4. **추가 benchmark:** 같은 데이터에 Ridge 회귀 모델을 적용한 결과 MASE 0.675로 Chronos-2보다 더 낮은 오차가 관찰되었다. 이는 72개월의 짧은 proxy 데이터에서는 단순한 regularized regression이 더 잘 맞을 수 있음을 시사한다.

종합하면, **보고서의 핵심 주장인 “AI 기반 수요예측이 전년 동월 단순 기준선보다 개선될 수 있다”는 사용자 데이터에서도 확인되었다.** 다만 운영 모델 선택에서는 Chronos-2와 Ridge를 함께 비교하는 하이브리드 접근이 더 안전하다.

---

## 2. 분석 목적

Cass 맥주 생산은 발효 리드타임과 탱크 용량 제약 때문에 수요를 사전에 예측하는 것이 중요하다. 기존 보고서는 Chronos-2 모델을 사용하여 수요 급등 가능성이 있는 월을 미리 예측하고, 이를 발효탱크 배분 의사결정으로 연결하는 구조를 제안했다.

본 실험의 목적은 다음과 같다.

| 목적 | 내용 |
|---|---|
| 동일 모델 검증 | 기존 자료와 같은 Amazon Chronos-2 모델을 사용자 데이터에 적용 |
| 기준선 비교 | Seasonal Naive 대비 성능 개선 여부 확인 |
| 이벤트 월 분석 | 폭염·열대야·스포츠 이벤트 월에서 예측 성능 확인 |
| 운영 가능성 평가 | 실제 발효 배분 의사결정에 활용 가능한지 판단 |

---

## 3. 데이터 구성

### 3.1 사용 데이터

본 실험에는 다음 파일을 사용했다.

`data/final_cass_demand_model_dataset_with_exogenous_2020_2025.csv`

데이터는 2020년 1월부터 2025년 12월까지 총 72개월의 월별 수요 proxy와 외생변수로 구성되어 있다.

### 3.2 타깃 변수

| 변수명 | 내용 | 단위 |
|---|---|---|
| `alcoholic_beer_total_proxy_kl` | 국내 알코올 맥주 총수요 proxy | kL / 월 |

본 타깃은 실제 OB 내부 ERP 출고량이 아니라 공개자료와 proxy 구성으로 생성된 수요 변수이다. 따라서 결과는 운영 확정용이라기보다 **진단적 모델 검증 결과**로 해석해야 한다.

### 3.3 Chronos-2 입력 Covariates

기존 보고서의 입력 구조에 맞춰 다음 7개 외생변수를 사용했다.

| 변수명 | 의미 |
|---|---|
| `seoul_avg_temp_c` | 서울 월평균기온 |
| `seoul_heatwave_warning_days_33c` | 33°C 이상 폭염일수 |
| `seoul_tropical_nights_25c` | 열대야일수 |
| `kbo_regular_games` | KBO 정규시즌 경기수 |
| `sports_major_event_days` | 주요 스포츠 이벤트 일수 |
| `public_holiday_count_kr` | 월별 공휴일 수 |
| `ob_major_price_increase_event_dummy` | OB맥주 가격 인상 이벤트 더미 |

---

## 4. 모델 설계

### 4.1 모델: Amazon Chronos-2

Chronos-2는 Amazon Science에서 공개한 zero-shot 시계열 파운데이션 모델이다. 기존 Chronos/Chronos-Bolt와 달리 Chronos-2는 미래 외생변수와 covariate-informed forecasting을 직접 지원한다.

본 실험에서는 다음 방식으로 모델을 구성했다.

| 항목 | 설정 |
|---|---|
| 모델 ID | `amazon/chronos-2` |
| 방식 | Zero-shot inference |
| Target | `alcoholic_beer_total_proxy_kl` |
| Covariates | 날씨, KBO, 스포츠 이벤트, 공휴일, 가격 인상 더미 |
| 예측 분위수 | 10%, 50%, 90% |
| 학습 구간 | 2020-01 ~ 2023-12 |
| 테스트 구간 | 2024-01 ~ 2025-12 |
| 실행 장치 | CUDA GPU |

### 4.2 기준선: Seasonal Naive

기준선은 시계열 수요예측에서 가장 기본적인 전년 동월 반복 방식이다.

\[
\hat{y}_t = y_{t-12}
\]

맥주 수요처럼 월별 계절성이 강한 데이터에서는 Seasonal Naive가 매우 강한 기준선이 된다. 따라서 Chronos-2가 이 기준선을 이기는지 확인하는 것이 모델 도입 타당성의 핵심이다.

### 4.3 추가 Benchmark: Ridge Regression

Chronos-2와 별도로 Ridge 회귀 모델도 비교했다. Ridge는 다음 변수를 사용했다.

- `lag_1`, `lag_12`
- 연간 계절성: `month_sin_annual`, `month_cos_annual`
- 날씨·이벤트·뉴스·가격 변수

Ridge 모델은 최종 채택 모델이라기보다, 작은 표본에서 단순 ML 모델이 얼마나 강한지 확인하기 위한 benchmark로 사용했다.

---

## 5. 평가 방식

### 5.1 Backtest 설계

| 구분 | 기간 | 개월 수 |
|---|---|---:|
| 학습 데이터 | 2020-01 ~ 2023-12 | 48개월 |
| 테스트 데이터 | 2024-01 ~ 2025-12 | 24개월 |

### 5.2 평가 지표

| 지표 | 의미 |
|---|---|
| MASE | Seasonal Naive scale 기준 평균절대오차. 1보다 작으면 기준선보다 우수 |
| WAPE | 전체 실제 수요 대비 절대오차 비율 |
| RMSE | 큰 오차에 민감한 제곱근 평균제곱오차 |

### 5.3 이벤트 월 정의

이벤트 월은 다음 조건 중 하나 이상을 만족하는 월로 정의했다.

- 폭염일수 존재
- 열대야일수 존재
- KBO 정규시즌 경기수 100경기 이상
- 주요 스포츠 이벤트 일수 존재

테스트 기간 중 이벤트 월은 총 10개월이다.

---

## 6. 모델 성능 결과

### 6.1 전체 테스트 성능

| 모델 | 테스트 월 수 | MASE | WAPE | RMSE |
|---|---:|---:|---:|---:|
| **Chronos-2 Covariate** | 24 | **0.800** | **0.0785** | **14,711** |
| Seasonal Naive | 24 | 1.137 | 0.1115 | 19,960 |

Chronos-2는 전체 테스트에서 Seasonal Naive 대비 모든 주요 지표에서 우수했다. 특히 MASE가 1보다 낮아, 전년 동월 반복 기준선보다 의미 있는 개선을 보였다.

**개선 폭:**

| 지표 | Seasonal Naive | Chronos-2 | 개선 |
|---|---:|---:|---:|
| MASE | 1.137 | 0.800 | 약 29.7% 감소 |
| WAPE | 0.1115 | 0.0785 | 약 29.6% 감소 |
| RMSE | 19,960 | 14,711 | 약 26.3% 감소 |

---

### 6.2 이벤트 월 성능

| 모델 | 이벤트 월 수 | MASE | WAPE | RMSE |
|---|---:|---:|---:|---:|
| **Chronos-2 Covariate** | 10 | **1.051** | **0.0946** | **19,003** |
| Seasonal Naive | 10 | 1.123 | 0.1010 | 19,640 |

이벤트 월에서는 개선 폭이 크지는 않지만 Chronos-2가 기준선보다 우세했다. 이는 폭염·스포츠 이벤트 등 외생변수를 반영하는 Chronos-2 구조가 수요 급등 구간에서도 일정 수준의 장점을 가진다는 것을 보여준다.

다만 이벤트 월 MASE가 1에 가깝기 때문에, 이벤트 월 예측은 여전히 가장 어려운 구간이다. 실제 운영에서는 이벤트 월에 80% 또는 90% 분위수 상한을 함께 사용하는 보수적 배분 전략이 필요하다.

---

### 6.3 일반 월 성능

| 모델 | 일반 월 수 | MASE | WAPE | RMSE |
|---|---:|---:|---:|---:|
| **Chronos-2 Covariate** | 14 | **0.622** | **0.0652** | **10,632** |
| Seasonal Naive | 14 | 1.147 | 0.1203 | 20,185 |

일반 월에서는 Chronos-2의 개선 폭이 매우 컸다. 이는 Chronos-2가 전체적인 수요 추세와 계절 패턴을 전년 동월 반복보다 안정적으로 포착했음을 의미한다.

---

## 7. Benchmark 모델과의 비교

추가로 Ridge 회귀 모델을 같은 데이터에 적용했다.

| 모델 | 전체 MASE | 전체 WAPE | 전체 RMSE |
|---|---:|---:|---:|
| **Ridge Regression** | **0.675** | **0.0662** | **12,057** |
| Chronos-2 Covariate | 0.800 | 0.0785 | 14,711 |
| Seasonal Naive | 1.137 | 0.1115 | 19,960 |

Ridge 모델은 Chronos-2보다 더 낮은 오차를 기록했다. 이는 다음과 같이 해석할 수 있다.

1. 데이터가 72개월로 작아 복잡한 foundation model보다 단순한 regularized model이 더 잘 맞을 수 있다.
2. 타깃이 실제 판매량이 아니라 proxy 변수이므로, lag와 계절성만으로도 상당 부분 설명된다.
3. Chronos-2는 zero-shot 모델이므로 별도 fine-tuning 없이 적용되었고, 데이터셋 특화 학습은 하지 않았다.

따라서 보고서의 주 모델은 기존 자료와 동일하게 Chronos-2로 두되, **실무 적용 시 Ridge와 Chronos-2를 ensemble 또는 model selection 방식으로 함께 운영하는 전략**이 합리적이다.

---

## 8. 운영 적용 해석

### 8.1 발효탱크 배분 관점

Cass 생산은 발효 리드타임이 길기 때문에 수요 급등을 사전에 탐지해야 한다. Chronos-2 모델은 단순 전년 동월 반복보다 낮은 오차를 보여, 월별 발효량 초안 생성에 사용할 수 있다.

운영 방식은 다음과 같이 설계할 수 있다.

```
월별 데이터 업데이트
  ↓
Chronos-2 수요예측 + 분위수 구간 산출
  ↓
Seasonal Naive / Ridge benchmark와 비교
  ↓
정상 월: 중앙값 기준 발효 계획
  ↓
이벤트 월: 80% 또는 90% 분위수 상한 기준 보수적 배분
  ↓
계획팀 검토 후 발효탱크 스케줄 확정
```

### 8.2 이벤트 월 대응

이벤트 월에서는 Chronos-2가 Seasonal Naive보다 약간 우수했지만, 오차가 여전히 높았다. 따라서 다음과 같은 보완이 필요하다.

| 상황 | 권장 대응 |
|---|---|
| 폭염·열대야 예상 | Chronos-2 상한 분위수 기준 안전재고 확대 |
| KBO 경기 집중 월 | 도매상 주문 조기 확정 유도 |
| 가격 인상 전후 | 선구매 수요 가능성 반영 |
| 예측구간이 넓은 월 | 계획팀장 검토 필수 |

---

## 9. 한계

본 실험에는 다음 한계가 있다.

| 한계 | 영향 |
|---|---|
| 타깃이 실제 OB 내부 판매량이 아닌 proxy | 운영 성능으로 직접 일반화하기 어려움 |
| 데이터 기간 72개월 | foundation model 및 covariate 효과 검증에 표본이 작음 |
| 월별 aggregate 데이터 | SKU별 Cass Fresh / Light 직접 검증 불가 |
| 미래 covariate 미사용 | 2026년 실제 운영 예측에는 미래 날씨·이벤트 입력 생성 필요 |
| zero-shot 적용 | 데이터셋 특화 fine-tuning 효과는 검증하지 않음 |

---

## 10. 결론

본 실험은 기존 친구 자료에서 사용한 Amazon Chronos-2 모델을 사용자 데이터에 동일하게 적용한 검증이다. 결과적으로 Chronos-2는 Seasonal Naive 기준선을 유의미하게 개선했다.

핵심 결론은 다음과 같다.

1. **Chronos-2는 사용자 데이터에서도 정상 작동했다.**  
   GPU 환경에서 `amazon/chronos-2` 모델을 실행하고 2024~2025년 백테스트를 완료했다.

2. **Seasonal Naive보다 우수했다.**  
   전체 MASE가 1.137에서 0.800으로 감소하여, 전년 동월 반복보다 약 30% 개선되었다.

3. **이벤트 월에서도 근소한 개선을 보였다.**  
   이벤트 월 MASE는 1.123에서 1.051로 낮아졌다. 다만 이벤트 월은 여전히 난도가 높기 때문에 예측 상한 기반 운영 전략이 필요하다.

4. **Ridge benchmark가 더 낮은 오차를 보였다.**  
   작은 proxy 데이터에서는 Ridge가 MASE 0.675로 가장 우수했다. 따라서 실제 운영에서는 Chronos-2 단독보다 Ridge/Chronos-2 병행 검증 또는 ensemble 방식이 더 안전하다.

최종적으로, **Chronos-2 기반 AI 수요예측은 Cass 발효탱크 사전 배분 의사결정에 적용 가능한 수준의 개선 효과를 보였으며, 향후 실제 OB 내부 월별 판매량 데이터를 확보하면 운영 등급 모델로 확장할 수 있다.**

---

## Appendix. 산출 파일

| 파일 | 내용 |
|---|---|
| `scripts/run_chronos2_user_test.py` | Chronos-2 실행 스크립트 |
| `model_outputs_chronos2_user_test/chronos2_predictions_vs_actual.csv` | 월별 실제값 vs 예측값 |
| `model_outputs_chronos2_user_test/chronos2_metrics.csv` | Chronos-2 / Seasonal Naive 성능 지표 |
| `model_outputs_chronos2_user_test/chronos2_summary.json` | 실행 설정 요약 |
| `model_outputs_user_data_test/metrics.csv` | Ridge benchmark 성능 지표 |
| `chronos2_user_data_test_summary.md` | 간단 요약 |

---

*본 보고서는 `/home/hegelty/programming/IMEN343/research_ob_cass_demand` 프로젝트 폴더의 사용자 데이터와 실행 결과를 기반으로 작성되었다.*
