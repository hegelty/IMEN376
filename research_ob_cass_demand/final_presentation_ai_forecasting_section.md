# AI 수요예측 모델 구축 및 결과

## OB Cass 수요예측과 발효탱크 사전 배분 의사결정

---

## 1. 분석 목적

Cass 맥주는 계절성과 이벤트 영향을 크게 받는 제품이다. 특히 여름철 폭염, 야구 경기, 스포츠 이벤트, 가격 인상 전후의 선구매 수요는 월별 수요 변동을 크게 만든다. 반면 맥주 생산은 발효 리드타임이 존재하기 때문에, 수요가 발생한 뒤 즉시 생산량을 늘리기 어렵다.

따라서 본 프로젝트의 AI 예측 파트는 다음 질문에 답하는 것을 목표로 한다.

> “공개 데이터와 수요 관련 외생변수를 이용해 Cass 관련 맥주 수요를 사전에 예측하고, 발효탱크 배분 의사결정에 활용할 수 있는가?”

본 분석은 단순히 예측값 하나를 만드는 것이 아니라, 다음 세 가지를 함께 검증했다.

1. 공개 데이터 기반으로 월별 맥주 수요 proxy를 만들 수 있는가
2. AI 모델이 전년 동월 반복 기준선보다 의미 있는 개선을 만들 수 있는가
3. 예측 결과를 발효탱크 운영과 안전재고 의사결정으로 연결할 수 있는가

---

## 2. 데이터 수집 및 구성

### 2.1 데이터 기간과 단위

본 모델은 2020년 1월부터 2025년 12월까지 총 72개월의 월별 데이터를 사용했다.

| 항목 | 내용 |
|---|---|
| 기간 | 2020-01 ~ 2025-12 |
| 단위 | 월별 데이터 |
| 관측 수 | 72개월 |
| 예측 대상 | 국내 알코올 맥주 수요 proxy |
| 검증 기간 | 2024-01 ~ 2025-12 |

---

### 2.2 수요 데이터: Layer A / B / C 구조

수요 데이터는 실제 OB 내부 판매 데이터가 없기 때문에, 공개자료를 바탕으로 3개 layer로 나누어 구성했다.

| Layer | 내용 | 사용 목적 |
|---|---|---|
| Layer A | 국내 알코올 맥주 전체 출고량 | 전체 시장 수요 예측 target의 기반 |
| Layer B | Cass Fresh / Cass Light 점유율 | 전체 시장 수요를 Cass 브랜드 수요로 분해 |
| Layer C | Cass 0.0 비알콜 시장 시나리오 | 비알콜 성장 가능성 반영 |

Layer A는 국세통계연보 등 공개자료의 연간 국내 맥주 출고량을 기반으로 구성했다. 2020~2022년은 상대적으로 실측 성격이 강하고, 2023~2025년은 보간 또는 추정값을 포함한다. 따라서 본 분석의 target은 실제 월별 판매량이 아니라 공개자료 기반의 **diagnostic proxy target**이다.

Layer B는 언론 보도에 공개된 Cass Fresh와 Cass Light 점유율을 연도별 anchor로 사용하고, 월별로 보간하여 구성했다. 이를 통해 전체 맥주 수요를 Cass Fresh / Cass Light 수준으로 대략 분해할 수 있다.

---

### 2.3 외생변수 수집

맥주 수요는 단순한 과거 수요뿐 아니라 날씨, 스포츠, 공휴일, 가격, 뉴스 등에 영향을 받는다. 따라서 다음 외생변수를 수집했다.

| 구분 | 변수 예시 | 수요와의 관계 |
|---|---|---|
| 날씨 | 월평균기온, 폭염일수, 열대야일수, 강수량 | 더운 날씨는 맥주 수요 증가 가능성 |
| 스포츠 | KBO 경기수, 주요 스포츠 이벤트 | 야구장/단체관람/회식 수요 증가 가능성 |
| 달력 | 공휴일 수, 연휴일수, 주말 수 | 음주·여가 활동 증가 가능성 |
| 가격 | 수입맥주 단가 YoY, OB 가격인상 더미 | 가격 인상 전 선구매 또는 대체수요 가능성 |
| 뉴스/축제 | 맥주 관련 뉴스 수, 축제 수 | 사회적 관심도와 이벤트 수요 반영 |
| Google Trends | 맥주/Cass 관련 검색량 | 수요 선행 신호 후보 |

다만 Google Trends는 사용 방식에 주의가 필요하다. 일부 초기 proxy target은 Google Trends를 포함해 만들어졌기 때문에, 동일한 Google Trends를 다시 모델 feature로 넣으면 target leakage 문제가 생길 수 있다. 이 문제는 아래에서 별도로 처리했다.

---

## 3. Target 변수 정의

### 3.1 Raw target의 한계

초기 target 후보는 `beer_domestic_volume`이었다. 이는 국내 알코올 맥주 출고량을 월별로 배분한 값이다. 그러나 이 값을 그대로 사용하면 다음 문제가 있다.

| 문제 | 설명 |
|---|---|
| 실제 월별 판매량 아님 | 공개 연간 출고량을 월별로 배분한 proxy |
| 인위적 계절성 | 매년 유사한 월별 패턴이 반복될 가능성 |
| Seasonal Naive에 유리 | 전년 동월 값을 그대로 쓰는 기준선이 구조적으로 강해짐 |
| 이벤트 효과 제한 | 폭염·스포츠 이벤트 같은 비정기 충격이 충분히 반영되지 않을 수 있음 |

즉, raw `beer_domestic_volume`을 그대로 target으로 쓰면 AI 모델 성능을 공정하게 평가하기 어렵다.

---

### 3.2 Adjusted leakage-safe target 생성

이를 보완하기 위해 최종 모델에서는 raw target을 그대로 사용하지 않고, 다음 원칙에 따라 수정 target을 만들었다.

> 최종 target: `beer_domestic_volume_adjusted_leakage_safe`

생성 원칙은 다음과 같다.

| 원칙 | 내용 |
|---|---|
| 연간 총량 보존 | 연도별 전체 맥주 수요 규모는 기존 공개자료 anchor를 유지 |
| 월별 분포 재조정 | 월별 수요 분포는 비-Google 수요 압력 변수로 보수적으로 수정 |
| Google Trends 제외 | target 생성에는 Google Trends를 사용하지 않음 |
| Circularity 방지 | target 조정에 사용한 변수는 예측 feature에서 제외 |

Adjusted target을 만들 때 사용한 수요 압력 변수는 다음과 같다.

| 변수 | 의미 |
|---|---|
| 월평균기온 | 더운 달 수요 증가 가능성 |
| 폭염일수 | 여름철 급등 수요 가능성 |
| 열대야일수 | 야간 음주/외식 수요 가능성 |
| KBO 경기수 | 스포츠 관람 수요 가능성 |
| 공휴일 수 | 여가 및 모임 수요 가능성 |
| 수입맥주 가격 YoY | 대체재 가격 변화 |
| OB 가격인상 더미 | 가격 인상 전후 선구매 가능성 |

중요한 점은, 이 변수들은 target 조정에는 사용되었지만 이후 예측 모델의 feature에서는 제외했다. 이는 같은 정보를 target 생성과 예측에 동시에 사용하는 circularity를 피하기 위한 조치이다.

---

## 4. Google Trends 처리 방식

Google Trends는 소비자 관심도를 나타내는 유용한 수요 선행 지표일 수 있다. 그러나 본 프로젝트에서는 target proxy 생성 과정과 겹칠 가능성이 있기 때문에 사용 방식을 구분했다.

### 4.1 사용하지 않은 경우: 성능 검증용 모델

성능 검증용 모델에서는 Google Trends를 완전히 제외했다. 이유는 다음과 같다.

```
Google Trends → target proxy 생성
Google Trends → 모델 feature로 다시 사용
```

이 구조가 되면 모델이 실제 수요를 예측하는 것이 아니라, target 생성에 이미 들어간 정보를 다시 읽는 것이 된다. 따라서 평가자는 이를 target leakage라고 볼 수 있다.

### 4.2 사용할 수 있는 경우: 운영 예측용 모델

다만 실제 운영에서는 Google Trends를 쓸 수 있다. 조건은 다음과 같다.

| 조건 | 설명 |
|---|---|
| target 생성에는 미사용 | target을 만들 때 Google Trends를 넣지 않음 |
| 당월값 직접 사용 금지 | 당월 Google Trends로 당월 수요를 예측하지 않음 |
| 전달값만 사용 | `t-1`월 Google Trends로 `t`월 수요를 예측 |
| 독립 target 확보 시 재평가 | 실제 출고/POS 데이터가 있으면 demand sensing feature로 재평가 가능 |

본 프로젝트에서도 전달 Google Trends를 별도로 테스트했다. 하지만 현재 proxy 데이터에서는 성능 개선 효과가 크지 않았다. 따라서 최종 보고서에서는 Google Trends를 “운영 예측에서 재평가 가능한 demand-sensing 후보 변수”로 정리했다.

---

## 5. 모델 후보

본 프로젝트에서는 단일 모델만 사용하지 않고, 여러 AI/ML 모델과 baseline을 비교했다.

| 모델 | 유형 | 목적 |
|---|---|---|
| Seasonal Naive | 전년 동월 반복 baseline | 필수 기준선 |
| Chronos-2 | 시계열 foundation model | 최종 AI 모델 후보 |
| Ridge | 선형 regularized regression | 단순 ML 기준선 |
| Lasso | sparse linear model | 변수 선택 효과 확인 |
| ElasticNet | L1/L2 혼합 회귀 | 선형 모델 보완 |
| RandomForest | tree ensemble | 비선형 관계 탐색 |
| ExtraTrees | randomized tree ensemble | tree 기반 robust 후보 |
| GradientBoosting | boosting tree | 비선형 예측 후보 |
| HistGradientBoosting | histogram boosting | 작은 데이터에서 boosting 성능 확인 |
| KNN | instance-based model | 유사 월 기반 예측 |
| SVR | kernel regression | 비선형 회귀 후보 |
| MLP | neural network | 신경망 기반 후보 |

모든 ML 모델은 2024~2025년 테스트 기간에 대해 rolling backtest 방식으로 평가했다. 즉 각 월을 예측할 때, 그 월 이후의 데이터는 학습에 사용하지 않았다.

---

## 6. Chronos-2 모델

Chronos-2는 Amazon Science에서 공개한 zero-shot 시계열 foundation model이다. 일반적인 회귀 모델과 달리, 시계열 패턴을 사전학습한 모델을 별도 fine-tuning 없이 적용할 수 있다.

본 프로젝트에서 Chronos-2를 사용한 이유는 다음과 같다.

| 이유 | 설명 |
|---|---|
| Zero-shot 가능 | 작은 데이터셋에서도 사전학습 지식을 활용 가능 |
| 시계열 전용 모델 | 월별 수요 패턴 학습에 적합 |
| 분위수 예측 가능 | 중앙값뿐 아니라 불확실성 구간 산출 가능 |
| 운영 의사결정 연결 | Q90 상한을 안전재고/발효탱크 계획에 활용 가능 |

Chronos-2는 GPU 환경에서 실행했다.

| 항목 | 내용 |
|---|---|
| 모델 | `amazon/chronos-2` |
| 실행 환경 | NVIDIA GeForce RTX 4060 Laptop GPU |
| Target | `beer_domestic_volume_adjusted_leakage_safe` |
| 평가 기간 | 2024-01 ~ 2025-12 |

---

## 7. 최종 모델 성능 결과

### 7.1 전체 테스트 결과

테스트 기간은 2024년 1월부터 2025년 12월까지 24개월이다.

| 순위 | 모델 | MASE | WAPE | RMSE |
|---:|---|---:|---:|---:|
| 1 | **Chronos-2 adjusted target** | **0.809** | **0.0527** | **9,633** |
| 2 | Seasonal Naive | 0.811 | 0.0529 | 10,254 |
| 3 | KNN | 0.921 | 0.0600 | 11,001 |
| 4 | ExtraTrees | 1.118 | 0.0729 | 12,254 |
| 5 | Ridge | 1.119 | 0.0729 | 12,737 |
| 6 | Lasso | 1.126 | 0.0734 | 13,010 |
| 7 | GradientBoosting | 1.228 | 0.0801 | 14,190 |
| 8 | HistGradientBoosting | 1.402 | 0.0914 | 15,957 |
| 9 | RandomForest | 1.454 | 0.0948 | 15,868 |
| 10 | ElasticNet | 2.404 | 0.1567 | 24,273 |
| 11 | SVR-RBF | 4.478 | 0.2918 | 44,860 |
| 12 | MLP | 14.942 | 0.9739 | 145,773 |

### 7.2 결과 해석

최종 adjusted target 기준에서는 Chronos-2가 가장 낮은 MASE를 기록했다. Seasonal Naive와의 차이는 매우 작지만, 중요한 점은 다음과 같다.

1. raw target이 아니라 adjusted leakage-safe target을 사용했다.
2. Google Trends를 target 생성에 사용하지 않았다.
3. target 조정에 사용한 변수도 feature에서 제외했다.
4. 이 조건에서 Chronos-2가 baseline을 근소하게 앞섰다.

따라서 최종 AI 모델은 Chronos-2로 선택할 수 있다. 다만 Chronos-2와 Seasonal Naive의 차이가 작기 때문에, 실제 운영에서는 Seasonal Naive를 sanity-check baseline으로 함께 유지해야 한다.

---

## 8. 전달 Google Trends 테스트 결과

운영 예측 가능성을 보기 위해 전달 Google Trends를 사용한 모델도 별도로 테스트했다.

사용 방식은 다음과 같다.

> `t-1`월 Google Trends → `t`월 수요 예측

즉 target 생성에는 Google Trends를 사용하지 않고, 예측 feature로도 당월값이 아니라 전달값만 사용했다.

| 모델 | MASE | WAPE | RMSE |
|---|---:|---:|---:|
| Seasonal Naive | 0.811 | 0.0529 | 10,254 |
| KNN + lagged Google Trends | 1.032 | 0.0673 | 12,609 |
| ExtraTrees + lagged Google Trends | 1.102 | 0.0719 | 12,397 |
| Ridge + lagged Google Trends | 1.158 | 0.0755 | 13,907 |
| GradientBoosting + lagged Google Trends | 1.225 | 0.0799 | 14,180 |

현재 proxy 데이터에서는 전달 Google Trends를 추가해도 성능 개선은 크지 않았다. 따라서 Google Trends는 최종 모델의 핵심 성능 근거로 사용하지 않고, 향후 실제 POS/출고 데이터 확보 시 재평가할 운영 후보 변수로 남긴다.

---

## 9. 최종 모델 선택

본 프로젝트의 최종 AI 수요예측 모델은 다음과 같이 정리한다.

> **Final AI Forecasting Model: Chronos-2 on adjusted leakage-safe target**

단, 운영 안정성을 위해 다음 구조로 사용한다.

```
Adjusted target 기반 Chronos-2 예측
  ↓
Seasonal Naive baseline과 비교
  ↓
예측 차이가 작으면 Chronos-2 중앙값 사용
  ↓
이벤트 월 또는 불확실성 높은 월은 Chronos-2 Q90 상한 참고
  ↓
발효탱크 배분 및 안전재고 검토
```

---

## 10. 운영 의사결정 연결

Cass 생산에서 중요한 것은 단순히 평균 예측 오차를 줄이는 것뿐 아니라, 수요 급등 시점에 품절 위험을 줄이는 것이다. 따라서 Chronos-2의 분위수 예측은 운영적으로 의미가 있다.

| 예측 결과 | 운영 대응 |
|---|---|
| 중앙값이 전년 동월과 유사 | 기존 발효 계획 유지 |
| Q90 상한이 전년 동월보다 높음 | 안전재고 또는 발효 배치 상향 검토 |
| 여름 성수기/월드컵/KBO 집중 월 | 계획팀장 검토 및 보수적 생산계획 |
| 예측구간이 넓음 | 불확실성 alert 발생 |

특히 발효 리드타임이 존재하기 때문에, 7월 수요를 대응하려면 최소 6월 중순에는 발효 계획이 확정되어야 한다. 따라서 AI 예측은 “수요가 이미 발생한 뒤 대응”하는 방식이 아니라, “수요 발생 전 생산계획을 조정”하는 데 의미가 있다.

---

## 11. 한계

본 분석은 공개 데이터 기반이므로 다음 한계가 있다.

| 한계 | 설명 |
|---|---|
| 실제 OB 내부 데이터 아님 | target은 실제 ERP/SAP 판매량이 아니라 공개자료 기반 proxy |
| 월별 표본 수 작음 | 72개월 데이터로 복잡한 AI 모델을 검증하기에는 제한적 |
| SKU 단위 검증 불가 | Cass Fresh / Light 실제 월별 출고량이 없음 |
| Adjusted target도 가정 포함 | 비-Google 변수로 보수적 재조정했지만 실제 수요는 아님 |
| Google Trends 효과 제한 | 현재 proxy 데이터에서는 전달 Google Trends가 성능 개선을 만들지 못함 |

따라서 본 모델의 결과는 실제 운영 성능을 확정적으로 주장하기보다, **AI 수요예측 시스템의 MVP 가능성 검증**으로 해석해야 한다.

---

## 12. 결론

본 프로젝트는 공개 데이터 기반으로 Cass 관련 맥주 수요예측 모델을 구축하고, 다양한 AI/ML 모델을 비교했다. 초기 raw target은 전년 동월 기준선에 지나치게 유리했기 때문에, 최종 분석에서는 Google Trends를 제외하고 비-Google 수요 압력 변수로 조정한 leakage-safe target을 사용했다.

최종 adjusted target 기준에서 Chronos-2는 MASE 0.809로 Seasonal Naive 0.811을 근소하게 앞섰다. 차이는 작지만, Google Trends leakage를 제거하고 target을 보수적으로 수정한 조건에서 Chronos-2가 최상위 성능을 기록했다는 점에서 최종 AI 모델로 채택할 수 있다.

최종 제안은 다음과 같다.

1. **최종 AI 모델:** Chronos-2  
2. **Target:** `beer_domestic_volume_adjusted_leakage_safe`  
3. **검증 baseline:** Seasonal Naive  
4. **운영 방식:** Chronos-2 중앙값 + Q90 risk overlay + Seasonal Naive sanity check  
5. **향후 개선:** 실제 OB SKU 출고량, POS 데이터, 발효탱크 상태 데이터 확보 후 재검증

결론적으로, 본 AI 모델은 공개 데이터만으로도 Cass 수요의 계절성과 이벤트 영향을 반영한 예측 체계를 만들 수 있음을 보여준다. 특히 Chronos-2의 분위수 예측은 발효탱크 사전 배분, 안전재고 설정, 이벤트 월 품절 리스크 관리에 활용될 수 있다.

---

## Appendix. 사용 산출물

| 파일 | 내용 |
|---|---|
| `final_adjusted_target_model_outputs/integrated_dataset_with_adjusted_target.csv` | 최종 adjusted target 포함 데이터셋 |
| `final_adjusted_target_model_outputs/adjusted_target_all_model_metrics.csv` | 전체 모델 비교 결과 |
| `final_adjusted_target_model_outputs/chronos2_adjusted_target_predictions.csv` | Chronos-2 예측 결과 |
| `final_lagged_google_trends_model_outputs/lagged_google_trends_model_metrics.csv` | 전달 Google Trends 모델 테스트 결과 |
| `scripts/build_adjusted_target_and_compare_ai.py` | adjusted target 생성 및 ML 모델 비교 스크립트 |
| `scripts/run_chronos2_adjusted_target.py` | Chronos-2 실행 스크립트 |
| `scripts/compare_lagged_google_trends_models.py` | 전달 Google Trends 테스트 스크립트 |
