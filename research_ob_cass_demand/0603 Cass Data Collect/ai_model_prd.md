# Cass Demand Forecasting AI Model PRD

작성일: 2026-06-03  
대상 프로젝트: OB Brewery Cass 계열 수요예측 및 발효 탱크 의사결정 지원  
작성 기준 파일:
- `POM_M3_Risk_AI_Analysis.docx`
- `POM_M4_AI_Integration_Design.docx`
- `POM Term Project Guideline (2026) Revised.docx`
- `Cass 수요예측 데이터 수집 및 AI 모델 방법론 (v2).md`
- `data_collection_prd.md`
- `data_collection_report.md`
- `cass_demand_v3_monthly.csv`
- `cass_demand_v3_dictionary.csv`
- `cass_demand_v3_validation.csv`
- `data/kosis_nts_beer_annual_anchor.csv`

---

## 1. Executive Summary

본 PRD는 Cass Fresh, Cass Light, Cass 0.0 수요 변동을 예측하고, 이를 발효 탱크 배분과 재고 보충 의사결정에 연결하기 위한 AI 모델 요구사항을 정의한다.

**선정 AI 모델은 Chronos-2 zero-shot time-series forecasting model이다.**  
Seasonal Naive는 AI 모델 후보가 아니라 성능 비교를 위한 mandatory baseline으로만 사용한다.

다만 현재 폴더에 수집된 데이터 기준으로는 **정식 SKU별 수요예측 성능을 주장할 수 없다.** 핵심 타깃인 `beer_domestic_volume`은 월별 실측이 아니라 국세청/KOSIS 연간 맥주 출고량을 월별 계절 패턴으로 배분한 proxy이며, Cass Fresh/Light 브랜드별 월간 실측 수요와 점유율은 결측이다. 따라서 본 PRD는 다음 2단계로 나눈다.

1. **Phase 0: Data-readiness MVP**
   - 현재 수집 데이터로 파이프라인, baseline forecast, 결측/품질 진단, 모델 사용 가능성 검증
   - 예측 성능은 "실제 Cass SKU 수요예측 성능"으로 주장하지 않음

2. **Phase 1: PRD-grade AI model**
   - 내부 SKU별 출고/판매/재고 데이터 또는 신뢰 가능한 월별 실측 타깃 확보 후 Chronos-2 기반 zero-shot/covariate-aware forecasting 적용
   - Seasonal Naive baseline 대비 MASE, WAPE, pinball loss 개선 여부를 검증

---

## 2. Problem Statement

Cass 생산 운영의 핵심 제약은 발효 공정이다. 기존 M3/M4 문서에 따르면 발효 탱크는 20개, 발효 기간은 약 14일이며, baseline load는 약 1.20 batches/day, capacity는 약 1.43 batches/day로 utilization이 약 84%에 달한다. 따라서 수요 급증 또는 탱크 손실이 발생하면 단기적으로 생산량을 즉시 늘리기 어렵다.

특히 폭염, 스포츠 이벤트, 프로모션, 월드컵 등으로 단기 수요가 증가할 경우 실제 생산 대응은 4-8주 전에 선제적으로 이루어져야 한다. 이 프로젝트의 AI 모델은 단순 예측 도구가 아니라, 다음 운영 의사결정을 지원해야 한다.

- 어떤 SKU를 어느 정도 선제 생산할지
- 발효 탱크 시작 batch를 어떤 제품군에 배정할지
- DC/wholesaler 안전재고를 얼마나 조정할지
- 수요 급증 가능성이 높지만 불확실성이 큰 기간에 human escalation이 필요한지

---

## 3. Goals

### 3.1 Business Goals

- 발효 탱크 병목 상황에서 Cass 계열 SKU의 service level 저하를 줄인다.
- 이벤트성 수요 급증에 대해 1-3개월 전 생산 계획 조정을 가능하게 한다.
- 수요예측 결과를 tank allocation, DC safety stock, wholesaler recommendation workflow에 연결한다.
- 예측 불확실성을 point forecast가 아니라 prediction interval로 제시하여 과신을 줄인다.

### 3.2 Model Goals

- 월별 또는 일별 수요 타깃에 대해 point forecast와 80%/95% prediction interval을 산출한다.
- Seasonal Naive baseline 대비 통계적으로 의미 있는 개선을 검증한다.
- routine month와 event/stress month를 분리해 모델 성능을 평가한다.
- 데이터 결측, proxy target, imputation 여부를 모델 산출물에 명시한다.

### 3.3 Phase 0 MVP Goals

- 현재 수집된 `cass_demand_v3_monthly.csv`를 읽고 데이터 품질을 자동 진단한다.
- target/covariate의 결측, imputation, proxy 여부를 모델 실행 전 flag 처리한다.
- Seasonal Naive baseline과 선택적 ETS/SARIMA/Chronos demo forecast를 생성한다.
- 현재 데이터로는 Cass Fresh/Light SKU별 성능 검증이 불가능하다는 제한을 리포트에 포함한다.

---

## 4. Non-goals

- 현재 public-only monthly dataset만으로 Cass Fresh/Light SKU별 실측 수요예측 성능을 주장하지 않는다.
- 월별 proxy 데이터를 사용해 일별 SKU x region x channel 예측 모델이 검증되었다고 주장하지 않는다.
- 사람이 승인해야 하는 발효 탱크 배정을 AI가 자동 확정하지 않는다.
- Phase 0에서 Chronos-2 fine-tuning을 수행하지 않는다.
- 결측인 Cass Fresh/Light share, KBO games, import beer price를 임의 생성해 모델 성능 평가에 사용하지 않는다.

---

## 5. Users and Stakeholders

| Stakeholder | Role | Needs |
|---|---|---|
| HQ demand planner | 예측 결과 검토 및 주간 생산계획 조정 | SKU별 수요 forecast, interval, event rationale |
| Brewery production planner | 발효 탱크 allocation 실행 | 다음 7개 fermentation starts에 대한 제품군 배정 제안 |
| DC inventory manager | 안전재고 및 replenishment 조정 | DC별 expected demand, stock risk, adjustment band |
| Sales/wholesaler manager | 계정별 권장 발주량 전달 | advisory recommendation, high-risk alert |
| Course evaluator | AI opportunity 평가 | 실제 supply chain 문제와 데이터 readiness의 정직한 연결 |

---

## 6. Current Data Readiness

### 6.1 Available Dataset

주요 데이터 파일은 `cass_demand_v3_monthly.csv`이며 2020-01부터 2025-12까지 72개월, 21개 컬럼으로 구성되어 있다.

주요 컬럼:

| Category | Columns | Current Status |
|---|---|---|
| National beer volume proxy | `beer_domestic_volume`, `beer_domestic_volume_unit`, `beer_domestic_volume_imputed` | 값 존재, 단 월별 실측이 아니라 연간 anchor 기반 월별 배분 |
| Brand/SKU target | `cass_fresh_share`, `cass_light_share`, `cass_fresh_volume`, `cass_light_volume` | 전부 결측 |
| Non-alcohol segment | `nonalc_market_value`, `cass_0_0_scn_base`, `cass_0_0_scn_low`, `cass_0_0_scn_high` | 값 존재, scenario/proxy 성격 |
| Weather | `temp_avg`, `heatwave_days`, `tropical_night_days` | 값 존재 |
| Events | `world_cup_dummy`, `holiday_days`, `ob_price_hike_dummy` | 값 존재 |
| Missing covariates | `kbo_games`, `import_beer_price_yoy`, `beer_value` | 결측 |

### 6.2 Validation Result

`cass_demand_v3_validation.csv` 기준 주요 검증 결과:

| Item | Result | Model Impact |
|---|---|---|
| 72 monthly rows | PASS | 월별 pipeline 테스트 가능 |
| Layer A official monthly beer volume | FAIL | 핵심 타깃이 월별 실측이 아니므로 성능평가 제한 |
| Annual beer anchors | FLAG | 2020, 2021, 2022, 2024는 official, 2023/2025는 unavailable/imputed |
| Beer value | FAIL | value-based target 사용 불가 |
| Cass Fresh/Light shares | FAIL | SKU별 Cass Fresh/Light 예측 불가 |
| Weather | PASS | covariate 후보로 사용 가능 |
| Holiday calendar | PASS | covariate 후보로 사용 가능 |
| KBO games | FAIL | 스포츠 이벤트 feature 보강 필요 |

### 6.3 Data Readiness Decision

현재 데이터는 **Phase 0 MVP에는 사용 가능**하지만, **Phase 1 정식 모델 성능 검증에는 부족**하다.

사용 가능:
- 데이터 ingestion pipeline
- feature schema 정의
- baseline forecast demo
- Chronos-2 inference demo
- uncertainty/reporting UI 설계
- 결측 및 proxy target 진단

사용 불가:
- Cass Fresh/Light SKU별 monthly actual 성능 검증
- 일별 SKU x region x channel forecast 성능 주장
- 2024-2025 holdout accuracy claim
- covariate가 실제로 성능을 개선했다는 강한 결론

---

## 7. Required Data for Phase 1

정식 AI 모델 평가를 위해 다음 데이터가 필요하다.

### 7.1 Minimum Required Target Data

| Requirement | Minimum Standard |
|---|---|
| Monthly actual demand | 최소 2020-01부터 2025-12까지 72개월 |
| SKU coverage | Cass Fresh, Cass Light, Cass 0.0 또는 최소 Cass family aggregate |
| Unit | kL, cases, shipments, or sell-out 중 하나로 일관 |
| Imputation | evaluation target에는 synthetic allocation 사용 금지 |
| Granularity | 최소 monthly, 이상적으로 daily SKU x region/channel |

### 7.2 Recommended Internal Data

| Data | Purpose |
|---|---|
| Historical sales/shipments by SKU/channel/day | 직접 수요 타깃 |
| Current SKU inventory at DC/wholesaler | replenishment decision |
| Fermentation tank state | tank allocation feasibility |
| Promotion calendar | demand uplift covariate |
| Historical forecast errors | uncertainty calibration |
| Stockout records | censored demand 보정 |

### 7.3 Recommended External Data

| Data | Purpose |
|---|---|
| Weather forecast and historical weather | heatwave/tropical night uplift |
| Sports/event calendar | event-month classification |
| Holidays and long weekends | seasonality and travel demand |
| Import beer price / competitor signal | market substitution proxy |
| World Cup or major event dummy | rare-event stress flag |

---

## 8. Model Scope

### 8.0 Selected AI Model

최종 선정 모델은 **Chronos-2 zero-shot time-series forecasting model**이다.

선정 이유:
- 현재 프로젝트는 수요예측 문제이므로 sequence/time-series foundation model이 가장 직접적으로 맞다.
- Cass 관련 데이터는 길이가 짧고 SKU별 실측이 제한적이므로, 대규모 fine-tuning이 필요한 모델보다 zero-shot forecasting이 현실적이다.
- 단순 point forecast가 아니라 80%/95% prediction interval을 산출할 수 있어 M4 문서의 human escalation 및 tank allocation workflow와 잘 맞는다.
- 날씨, 휴일, 이벤트, 프로모션 같은 external covariate를 포함한 forecast 설계로 확장할 수 있다.
- 수업 프로젝트 범위에서 "구현 가능성", "설명 가능성", "운영 의사결정 연결성"의 균형이 가장 좋다.

따라서 PRD의 AI 모델 구조는 다음과 같이 고정한다.

| Role | Model |
|---|---|
| Selected AI model | Chronos-2 zero-shot forecasting |
| Mandatory comparison baseline | Seasonal Naive |
| Optional robustness baseline | ETS/SARIMA |
| Not selected | LSTM, XGBoost, Prophet, generic LLM |

비선정 이유:
- LSTM/Transformer from scratch: 현재 72개월 수준의 짧은 데이터로 학습하기 부적절하다.
- XGBoost/Random Forest: tabular regressor로 쓸 수는 있지만 forecast interval과 time-series uncertainty 설계가 Chronos-2보다 덜 직접적이다.
- Prophet: 빠른 baseline으로는 가능하지만 AI 모델로 내세우기에는 M4의 covariate-aware interval forecasting 요구와 차별성이 약하다.
- Generic LLM: 수요예측 numerical forecasting의 primary model로는 부적절하며, 설명문 생성 보조 역할에 한정해야 한다.

### 8.1 Phase 0 MVP Model

Phase 0 모델은 "성능 최적화"보다 "데이터와 workflow 검증"을 목표로 한다.

Required:
- Seasonal Naive baseline
- Data readiness validator
- Forecast artifact generator
- Backtest runner with warning labels
- Markdown evaluation report

Optional:
- ETS or SARIMA baseline
- Chronos-2 zero-shot demo
- Covariate ablation demo

Phase 0 산출물에는 반드시 다음 disclaimer를 포함한다.

> Current target is annual-anchor-based monthly proxy, not observed Cass SKU-level monthly demand. Forecast metrics are pipeline diagnostics only and must not be interpreted as validated SKU demand forecasting performance.

### 8.2 Phase 1 Production Model

Phase 1의 production model은 Chronos-2 기반 zero-shot forecasting이다. 선택 이유는 다음과 같다.

- short time series에서도 zero-shot inference 가능
- covariate-aware forecasting 지원
- prediction interval/quantile forecast 산출 가능
- fine-tuning 없이 baseline 대비 비교 실험 가능
- POM 프로젝트 범위에서 구현 복잡도와 설명 가능성의 균형이 좋음

Chronos-2는 다음 방식으로 실험한다.

| Experiment | Description | Acceptance Use |
|---|---|---|
| Seasonal Naive | 전년 동일월 또는 동일요일 반복 | mandatory baseline |
| Chronos-2 univariate | target series only | selected AI model base run |
| Chronos-2 covariate-informed | weather, holiday, event, promotion features | uplift 검증 |
| Optional multivariate | SKU 또는 region series 동시 입력 | 데이터 충분 시 |
| Optional ETS/SARIMA | classical baseline | robustness comparison |

---

## 9. Inputs and Features

### 9.1 Phase 0 Input Schema

File: `cass_demand_v3_monthly.csv`

Required columns:
- `month`
- `beer_domestic_volume`
- `beer_domestic_volume_imputed`
- `temp_avg`
- `heatwave_days`
- `tropical_night_days`
- `world_cup_dummy`
- `holiday_days`
- `ob_price_hike_dummy`

Optional columns:
- `nonalc_market_value`
- `cass_0_0_scn_base`
- `cass_0_0_scn_low`
- `cass_0_0_scn_high`
- `kbo_games`
- `import_beer_price_yoy`

Blocked target columns until filled:
- `cass_fresh_share`
- `cass_light_share`
- `cass_fresh_volume`
- `cass_light_volume`

### 9.2 Phase 1 Input Schema

Recommended grain:
- Daily SKU x region/channel

Required fields:
- `date`
- `sku`
- `region` or `channel`
- `actual_demand`
- `shipments`
- `inventory_on_hand`
- `stockout_flag`
- `promotion_flag`
- `temperature`
- `heatwave_flag`
- `holiday_flag`
- `event_flag`

Optional operations fields:
- `fermentation_tank_id`
- `fermentation_start_date`
- `fermentation_available_date`
- `batch_size`
- `tank_capacity`
- `line_capacity`

---

## 10. Outputs

### 10.1 Phase 0 Outputs

| Output | Format | Description |
|---|---|---|
| Data readiness report | Markdown/CSV | 결측, proxy, imputation, blocked target 진단 |
| Baseline forecast | CSV | monthly proxy target forecast |
| Forecast intervals | CSV | 가능 시 80%/95% interval |
| Evaluation report | Markdown | MASE/WAPE 등 pipeline diagnostic metric |
| Model limitation note | Markdown | 현재 성능 주장의 제한 |

### 10.2 Phase 1 Outputs

| Output | Grain | Description |
|---|---|---|
| Demand forecast | SKU x region x day | 28-day point forecast |
| Prediction intervals | SKU x region x day | 80% and 95% intervals |
| Tank allocation recommendation | SKU x next 7 starts | 발효 시작 batch 추천 |
| DC safety stock recommendation | DC x SKU x day | safety stock adjustment |
| Wholesaler advisory order | account x SKU | sales team 전달용 권장량 |
| Escalation alert | workflow event | high uncertainty, drift, rare event alert |

---

## 11. Workflow Integration

### 11.1 Forecast Cadence

Phase 1 target cadence:
- Daily refresh: 06:00 KST
- Weekly tank allocation commit: Wednesday planning cycle
- Daily safety stock review
- Alert when forecast moves outside previous-day 80% interval

Phase 0 cadence:
- Manual batch run on collected monthly CSV
- Used for report/demo, not operational planning

### 11.2 Human Decision Authority

| Decision Area | AI Role | Human Role |
|---|---|---|
| Fermentation tank allocation | Recommendation with interval/rationale | Full approval required |
| DC safety stock adjustment within +/-15% | Auto suggestion or low-touch approval | Monitor exceptions |
| DC adjustment +/-15% to +/-30% | Recommendation | Planner approval |
| DC adjustment above +/-30% | Escalation | HQ approval |
| Wholesaler replenishment | Advisory | Sales team communicates/negotiates |

AI는 irreversible fermentation commitment를 자동 확정하지 않는다.

---

## 12. Evaluation Plan

### 12.1 Phase 0 Evaluation

Phase 0에서는 모델 성능을 business KPI로 주장하지 않고, pipeline diagnostic으로만 평가한다.

Metrics:
- MASE
- WAPE
- sMAPE if useful
- Pinball loss if interval forecast is available

Rules:
- `beer_domestic_volume_imputed = TRUE`인 기간은 별도 표기한다.
- 월별 proxy target 기반 score는 "actual SKU demand accuracy"로 표현하지 않는다.
- Cass Fresh/Light 결측 target에 대한 metric은 산출하지 않는다.
- Chronos-2 결과가 baseline보다 좋더라도 "proxy data에서의 diagnostic result"로만 해석한다.

### 12.2 Phase 1 Evaluation

정식 평가는 actual target 확보 후 수행한다.

Recommended split:
- Train: 2020-01 to 2023-12
- Validation/Test: 2024-01 to 2025-12

If daily data is available:
- Rolling-origin backtest
- Horizon buckets: 1-7 days, 8-14 days, 15-28 days
- Event vs routine day/month split

Required baseline comparison:
- Seasonal Naive is mandatory
- Chronos-2 must beat Seasonal Naive on at least one primary metric without materially worsening interval calibration

Primary metrics:
- MASE
- WAPE
- Pinball loss for quantiles
- Prediction interval coverage

Operational metrics:
- Stockout risk reduction
- Excess inventory risk
- Forecast-driven tank allocation feasibility
- Number of high-uncertainty escalations

---

## 13. Acceptance Criteria

### 13.1 Phase 0 MVP Acceptance

Phase 0 is accepted when all conditions below are met.

| ID | Criterion |
|---|---|
| MVP-1 | Pipeline reads `cass_demand_v3_monthly.csv` without manual column edits |
| MVP-2 | Missing Cass Fresh/Light target columns are detected and reported |
| MVP-3 | Proxy/imputed target warning appears before model evaluation |
| MVP-4 | Seasonal Naive baseline forecast is generated |
| MVP-5 | Evaluation report labels metrics as diagnostic only |
| MVP-6 | No report claims validated SKU-level Cass Fresh/Light performance |
| MVP-7 | Output files are reproducible from a single script or notebook |

### 13.2 Phase 1 Model Acceptance

Phase 1 model is accepted only when all conditions below are met.

| ID | Criterion |
|---|---|
| M-1 | Actual, non-synthetic demand target is available for the evaluation period |
| M-2 | Cass Fresh/Light/Cass 0.0 or Cass family target grain is explicitly defined |
| M-3 | Seasonal Naive baseline is included |
| M-4 | Chronos-2 improves MASE or WAPE vs Seasonal Naive baseline |
| M-5 | 80% and 95% intervals are reported with empirical coverage |
| M-6 | Event/stress periods are evaluated separately from routine periods |
| M-7 | High-uncertainty forecasts trigger human review |
| M-8 | Tank allocation recommendations remain approval-based |

---

## 14. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Proxy target mistaken for actual demand | False performance claim | Hard warning in validator/report |
| Cass SKU actuals unavailable | Cannot validate SKU model | Limit output to aggregate/proxy demo |
| Short time series | Overfitting or unstable covariate effects | Seasonal Naive baseline, rolling backtest, conservative interpretation |
| Rare event undertraining | World Cup/heatwave surge missed | Event flags, wider intervals, human escalation |
| Data leakage | Inflated performance | Strict date-based split and future-only covariates |
| Overtrust in point forecast | Bad tank commitment | Always show interval and rationale |
| External data missing | Feature gaps | Fail gracefully and mark covariate unavailable |
| Partner/internal data dependency | Delayed production use | Phase 0 public-data MVP separated from Phase 1 model |

---

## 15. Implementation Plan

### Phase 0: Current Folder MVP

1. Build data validator
   - Read data dictionary and monthly CSV
   - Detect missing target/covariate columns
   - Mark imputed/proxy target periods

2. Build baseline forecast
   - Seasonal Naive for monthly target
   - Optional ETS/SARIMA if stable

3. Add Chronos-2 demo path
   - Run only if dependency is installed
   - Label result as proxy-data demo

4. Generate report
   - Data readiness
   - Baseline metrics
   - Forecast plot/table
   - Explicit limitations

### Phase 1: PRD-grade AI Model

1. Acquire actual SKU or Cass family target data
2. Build daily/monthly feature store
3. Implement rolling-origin backtest
4. Compare Seasonal Naive, classical baseline, Chronos-2
5. Calibrate prediction intervals
6. Integrate forecast with tank allocation and safety stock workflow
7. Add monitoring for drift, interval breach, and data freshness

---

## 16. Model Monitoring Requirements

Production monitoring should include:

- Daily data freshness check
- Missing feature rate
- Target distribution drift
- Forecast error by SKU/region/channel
- Interval coverage by horizon
- Event-month error
- Forecast movement outside prior 80% interval
- Human override rate
- Tank allocation recommendation acceptance rate

Alert triggers:
- Required target/covariate missing
- Forecast movement exceeds threshold
- 80% interval coverage falls below acceptable range over recent window
- Event/stress period detected with high uncertainty
- Data distribution materially differs from training/backtest period

---

## 17. Open Questions

1. Internal SKU-level data availability
   - Cass Fresh, Cass Light, Cass 0.0의 실제 월별 또는 일별 sales/shipments를 확보할 수 있는가?

2. Target definition
   - 수요 타깃을 shipment, sell-in, sell-out, production request 중 무엇으로 정의할 것인가?

3. Operational grain
   - 최종 의사결정 단위는 national monthly, SKU monthly, SKU x region daily 중 무엇인가?

4. Evaluation standard
   - 수업 제출용으로는 proxy-data MVP를 허용할 것인가, 아니면 실측 데이터 확보 전까지 모델 성능 주장을 제외할 것인가?

5. Chronos-2 execution environment
   - 프로젝트 환경에서 `chronos-forecasting` 설치 및 실행 계획을 어떻게 잡을 것인가?

---

## 18. Final Recommendation

현재 폴더의 데이터와 문서를 기준으로 가장 안전한 구현 방향은 다음과 같다.

1. **Phase 0 MVP를 먼저 구현한다.**
   - 데이터 품질 진단
   - Seasonal Naive baseline
   - Chronos-2 demo option
   - 명확한 limitation report

2. **M4 문서의 AI-2 integration design은 유지한다.**
   - tank allocation, DC safety stock, wholesaler advisory workflow는 PRD-grade 목표로 둔다.

3. **성과 주장은 보수적으로 작성한다.**
   - 현재 데이터로는 "Cass SKU별 AI 수요예측 성능 검증"이 아니라 "public/proxy data 기반 모델 방법론 및 통합 설계"로 표현한다.

4. **추가 데이터 확보 시 Phase 1로 전환한다.**
   - actual SKU-level target 확보 후 Chronos-2와 baseline을 정식 비교한다.
