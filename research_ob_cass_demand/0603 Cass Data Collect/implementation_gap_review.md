# Implementation Gap Review

작성일: 2026-06-03

검토 대상:
- `ai_model_prd.md`
- `data_collection_prd.md`
- `scripts/collect_cass_data.py`
- `scripts/model_cass_demand.py`
- `cass_demand_v3_validation.csv`
- `model_outputs/model_run_summary.md`
- `model_outputs/evaluation_metrics.csv`

## 1. 결론

현재 구현은 **Phase 0 Data-readiness MVP는 충족**한다. 데이터 수집, 결측 진단, Seasonal Naive baseline, ETS robustness baseline, Chronos-2 univariate, Chronos-2 covariate-informed inference, rolling-origin diagnostic backtest, event/stress split, interval coverage, alert, monitoring/drift alert, tank allocation proxy, safety stock proxy, wholesaler advisory proxy, workflow action queue, phase acceptance gate, Phase 1 input checker, Phase 1 model-input builder, end-to-end runner, daily runner script가 동작한다.

하지만 **fallback/workaround code가 없지는 않다.** 특히 데이터 수집 쪽에는 PRD-grade 실측 데이터가 없어서 대체/가정/시나리오로 처리한 부분이 있고, 모델 쪽에는 Chronos 실행 실패 시 결과 파일을 계속 생성하는 graceful-failure code가 있다.

또한 **Phase 1 PRD-grade AI model은 아직 미충족**이다. 이유는 모델 코드 부족보다 데이터 부족이 더 크다. 실제 Cass SKU-level target, 월별 KOSIS 실측 Layer A, aT FIS Fresh/Light share, import beer price, tank/inventory/promotion/internal data가 없다.

---

## 2. Fallback / Workaround / Placeholder Code

| 구분 | 위치 | 상태 | 설명 | 리스크 |
|---|---|---|---|---|
| Annual anchor 대체 | `scripts/collect_cass_data.py:233-241`, `315-327` | 사용 중 | KOSIS `DT_1F01012` 월별 맥주 내수량 대신 KOSIS/NTS 연간 맥주 출고량을 사용 | 실제 월별 수요가 아니라 annual-to-month proxy |
| 2023/2025 imputation | `scripts/collect_cass_data.py:236-241` | 사용 중 | 2023은 보간, 2025는 2024 carry-forward | 24개 row가 imputed target에 포함됨 |
| 월별 seasonal allocation | `scripts/collect_cass_data.py:245-252` | 사용 중 | 연간 출고량을 cos 기반 계절 가중치로 월별 배분 | Seasonal Naive baseline이 인위적으로 유리해질 수 있음 |
| Layer B placeholder | `scripts/collect_cass_data.py:331-335` | 사용 중 | Cass Fresh/Light share 및 volume을 `pd.NA`로 둠 | SKU별 Cass Fresh/Light 예측 불가 |
| beer value placeholder | `scripts/collect_cass_data.py:328` | 사용 중 | KOSIS value bridge 미수집으로 `beer_value = pd.NA` | value-to-volume bridge 미구현 |
| import beer price placeholder | `scripts/collect_cass_data.py:341` | 사용 중 | 관세청/UNIPASS 미수집으로 `import_beer_price_yoy = pd.NA` | 가격 covariate 미사용 |
| Non-alcohol scenario | `scripts/collect_cass_data.py:295-312` | 사용 중 | Cass 0.0을 실측이 아닌 시장규모/점유율 scenario로 산출 | 성능 평가 target으로 사용 불가 |
| Open-Meteo 대체 | `scripts/collect_cass_data.py:389-391` | 사용 중 | KMA ASOS API key가 없어 Open-Meteo 사용 | 공식 KMA 기반 요구와 다름 |
| Static holiday table | `scripts/collect_cass_data.py:255-258`, `394` | 사용 중 | data.go.kr API 대신 코드 내 공휴일 테이블 사용 | 향후 연도 확장 시 수동 갱신 필요 |
| Future covariate projection | `scripts/model_cass_demand.py` / `projected_future_covariates()` | 사용 중 | 2026 forecast용 covariate를 월별 과거 평균으로 투영하고 event dummy는 0 처리 | 실제 미래 날씨/이벤트 예측이 아님 |
| Tank allocation proxy | `scripts/model_cass_demand.py` | 사용 중 | 월별 aggregate forecast를 M3 baseline capacity 수치에 연결 | 실제 SKU/tank executable plan 아님 |
| Chronos skip flag | `scripts/model_cass_demand.py` / `--skip-chronos` | 존재 | `--skip-chronos`로 Chronos 실행을 건너뛸 수 있음 | 현재 기본 실행에서는 사용하지 않음 |
| Chronos graceful failure | `scripts/model_cass_demand.py` / `run_chronos()` | 존재 | import/model load/inference 실패 시 script를 중단하지 않고 status 파일 생성 | 실패를 숨기지는 않지만, PASS로 오해하지 않도록 status 확인 필요 |
| Matplotlib silent skip | `scripts/model_cass_demand.py` / `write_plot()` | 존재 | matplotlib import 실패 시 plot 생성만 건너뜀 | plot 누락 가능, 핵심 모델 산출물은 유지 |
| HF cache workaround | `scripts/model_cass_demand.py` / `HF_HOME` | 사용 중 | 기본 Hugging Face cache 권한 문제를 피하려고 workspace `.hf_cache` 사용 | 환경 workaround, 모델 결과에는 직접 영향 없음 |

판정: fallback/workaround는 존재한다. 다만 대부분은 `validation`, `dictionary`, `model_run_summary`에서 명시되어 있어 숨겨진 조작은 아니다.

---

## 3. 구현 완료 항목

| PRD 항목 | 상태 | 근거 |
|---|---|---|
| 72개월 monthly CSV 생성 | 완료 | `cass_demand_v3_validation.csv` row count PASS |
| 날씨 covariate | 완료 | `temp_avg`, `heatwave_days`, `tropical_night_days` 72개 PASS |
| holiday covariate | 완료 | `holiday_days` 72개 PASS |
| KBO games covariate | 완료 | KBO official schedule Ajax에서 72개월 수집 PASS |
| data dictionary | 완료 | `cass_demand_v3_dictionary.csv` |
| data validation report | 완료 | `cass_demand_v3_validation.csv` |
| Seasonal Naive baseline | 완료 | `model_outputs/seasonal_naive_forecast.csv`, `seasonal_naive_backtest.csv` |
| ETS robustness baseline | 완료 | `model_outputs/ets_forecast.csv`, `ets_backtest.csv`, `ets_rolling_backtest.csv`, `ets_status.json` |
| Chronos-2 univariate | 완료 | `model_outputs/chronos2_forecast.csv`, `chronos2_backtest.csv` |
| Chronos-2 covariate-informed | 완료 | `model_outputs/chronos2_covariate_forecast.csv`, `chronos2_covariate_backtest.csv` |
| Chronos-2 rolling-origin diagnostic | 완료 | `model_outputs/chronos2_rolling_backtest.csv` |
| rolling-origin backtest | 완료 | `model_outputs/rolling_origin_backtest.csv` |
| 80/95 interval output | 완료 | Chronos forecast에 `q025`, `q100`, `q900`, `q975` 존재 |
| empirical interval coverage | 완료 | `model_outputs/interval_coverage_metrics.csv` |
| event/stress split evaluation | 완료 | `model_outputs/event_split_metrics.csv` |
| high-uncertainty alerts | 완료 | `model_outputs/forecast_alerts.csv` |
| tank allocation proxy | 부분 완료 | `model_outputs/tank_allocation_proxy.csv`; 실제 SKU/tank plan은 아님 |
| safety stock proxy | 부분 완료 | `model_outputs/safety_stock_proxy.csv`; 실제 DC/SKU 조정은 아님 |
| wholesaler advisory proxy | 부분 완료 | `model_outputs/wholesaler_advisory_proxy.csv`; 실제 account-level order는 아님 |
| workflow action queue | 부분 완료 | `model_outputs/workflow_action_queue.csv`; 실제 운영 시스템과 연결되지는 않음 |
| phase acceptance gate | 완료 | `model_outputs/phase_acceptance_check.csv` |
| Phase 1 data templates | 완료 | `data/phase1_*_template.csv`, `data/phase1_data_requirements.csv` |
| Phase 1 input checker | 완료 | `model_outputs/phase1_ingestion_status.csv`; 현재 모든 템플릿은 `EMPTY_TEMPLATE` |
| Phase 1 model-input builder | 완료 | `scripts/build_phase1_model_input.py`; 현재는 actual SKU target row가 없어 `BLOCKED` |
| End-to-end runner | 완료 | `scripts/run_pipeline.py`; 기본적으로 Phase 1 템플릿을 보존 |
| Monitoring/drift alert | 완료 | `model_outputs/monitoring_snapshot.csv`, `model_outputs/monitoring_alerts.csv` |
| Daily refresh runner | 부분 완료 | `scripts/run_daily_pipeline.ps1`, `scripts/install_daily_pipeline_task.ps1`; 스케줄 등록은 사용자가 실행해야 함 |
| WAPE/MASE/pinball metric | 완료 | `model_outputs/evaluation_metrics.csv` |
| diagnostic-only warning | 완료 | `model_outputs/model_run_summary.md` |
| reproducible script | 완료 | `scripts/collect_cass_data.py`, `scripts/model_cass_demand.py` |

---

## 4. 미구현 / 미충족 사항

### 4.1 데이터 미구현

| 항목 | 상태 | 영향 |
|---|---|---|
| KOSIS `DT_1F01012` 월별 맥주 내수량 실측 | 미구현/미확보 | Phase 1 actual target 평가 불가 |
| KOSIS beer value bridge | 미구현 | value-to-volume 보정 불가 |
| Cass Fresh share | 미구현 | Cass Fresh SKU forecast 불가 |
| Cass Light share | 미구현 | Cass Light SKU forecast 불가 |
| Cass Fresh/Light volume target | 미구현 | SKU-level metric 산출 불가 |
| Import beer price YoY | 미구현 | 가격/수입맥주 covariate 미사용 |
| Internal sales/shipments/inventory | 미구현 | 실제 운영 grain forecast 불가 |
| Fermentation tank state | 미구현 | tank allocation recommendation 불가 |
| Promotion calendar | 미구현 | 프로모션 uplift 반영 불가 |
| Stockout records | 미구현 | censored demand 보정 불가 |

### 4.2 모델/평가 미구현

| 항목 | 상태 | 영향 |
|---|---|---|
| actual Cass SKU-level target evaluation | 미구현 | SKU 수요예측 성능 주장 불가 |
| daily SKU x region/channel forecast | 미구현 | M4 production workflow 수준 미달 |
| rolling-origin backtest | 구현됨 | Seasonal Naive + Chronos-2 diagnostic rolling, 36개월 min train, 3개월 horizon, 6개월 step |
| event/stress period separate evaluation | 구현됨 | heatwave, tropical night, high KBO games, World Cup, price hike 기준 split |
| empirical interval coverage | 구현됨 | 80/95 coverage 및 interval width 계산 |
| ETS/SARIMA robustness baseline | 구현됨 | ETS additive baseline 구현, SARIMA는 별도 구현하지 않음 |
| multivariate SKU/region Chronos | 미구현 | SKU/region series가 없어 불가 |
| Chronos-2가 Seasonal Naive 개선 | 미충족 | proxy target backtest에서 Chronos가 baseline보다 낮음 |

### 4.3 운영 워크플로우 미구현

| 항목 | 상태 | 영향 |
|---|---|---|
| Tank allocation recommendation | 부분 구현 | 월별 proxy 기반 utilization/prebuild watch만 제공, SKU/tank executable 아님 |
| DC safety stock recommendation | 부분 구현 | interval 기반 aggregate proxy만 제공 |
| Wholesaler advisory order | 부분 구현 | national aggregate demand band만 제공, account-level 아님 |
| Human escalation rule engine | 부분 구현 | `forecast_alerts.csv`에 HIGH/WATCH/NORMAL 생성, 실제 workflow integration 없음 |
| Daily 06:00 refresh automation | 부분 구현 | runner와 Task Scheduler 등록 스크립트는 구현, 실제 등록은 미실행 |
| Monitoring dashboard/drift alert | 부분 구현 | CSV monitoring snapshot/alerts 구현, 대시보드는 없음 |
| Phase 1 data ingestion | 부분 구현 | builder는 구현됐지만 실제 내부 데이터 row가 없어 `data/phase1_model_input.csv`는 비어 있음 |

---

## 5. Phase 0 Acceptance Check

| ID | Criterion | Status |
|---|---|---|
| MVP-1 | Pipeline reads `cass_demand_v3_monthly.csv` without manual column edits | PASS |
| MVP-2 | Missing Cass Fresh/Light target columns are detected and reported | PASS |
| MVP-3 | Proxy/imputed target warning appears before model evaluation | PASS |
| MVP-4 | Seasonal Naive baseline forecast is generated | PASS |
| MVP-5 | Evaluation report labels metrics as diagnostic only | PASS |
| MVP-6 | No report claims validated SKU-level Cass Fresh/Light performance | PASS |
| MVP-7 | Output files are reproducible from a single script or notebook | PASS |

결론: Phase 0 MVP는 충족한다.

---

## 6. Phase 1 Acceptance Check

| ID | Criterion | Status | Reason |
|---|---|---|---|
| M-1 | Actual, non-synthetic demand target is available | FAIL | target이 annual-anchor proxy |
| M-2 | Cass Fresh/Light/Cass 0.0 or Cass family target grain defined | FAIL | Fresh/Light actual target 없음 |
| M-3 | Seasonal Naive baseline included | PASS | baseline 구현됨 |
| M-4 | Chronos-2 improves MASE or WAPE vs Seasonal Naive | FAIL | 현재 proxy backtest에서 Chronos-2가 더 나쁨 |
| M-5 | 80% and 95% intervals reported with empirical coverage | PARTIAL | coverage 계산은 구현, actual target이 proxy라 Phase 1 검증은 아님 |
| M-6 | Event/stress periods evaluated separately | PARTIAL | split metric은 구현, actual target이 proxy라 Phase 1 검증은 아님 |
| M-7 | High-uncertainty forecasts trigger human review | PARTIAL | alert CSV는 생성, 실제 workflow trigger는 없음 |
| M-8 | Tank allocation recommendations remain approval-based | PARTIAL | proxy recommendation은 생성, 실제 SKU/tank allocation은 없음 |

결론: Phase 1은 아직 충족하지 않는다.

---

## 7. 실행 결과상 중요한 해석

현재 metrics:

| model | WAPE | MASE |
|---|---:|---:|
| Seasonal Naive | 0.001035 | 0.036729 |
| Chronos-2 univariate | 0.009367 | 0.332362 |
| Chronos-2 covariate-informed | 0.012678 | 0.449849 |
| Seasonal Naive rolling | 0.001381 | 0.048971 |
| Chronos-2 rolling | 0.004369 | 0.154930 |

Chronos-2는 실행됐지만 baseline을 이기지 못했다. 이 결과는 현재 target이 연간 anchor를 월별 계절 가중치로 배분한 proxy라서 전년동월 반복 baseline이 유리한 구조이기 때문이다. 따라서 이 성능표는 **모델 파이프라인 진단 결과**이지, Cass SKU 수요예측 성능 검증이 아니다.

---

## 8. 다음 구현 우선순위

1. 실제 target 확보
   - KOSIS 월별 맥주 내수량 실측 또는 내부 Cass family/SKU sales-shipment data

2. Layer B 확보
   - Cass Fresh/Light share 또는 POS/내부 SKU별 volume

3. 운영 추천 기능 보강
   - 실제 workflow trigger integration
   - DC/SKU/account-level allocation logic
   - internal inventory/tank constraints 연결

4. 미수집 covariate 보강
   - import beer price YoY
   - promotion calendar
   - stockout/tank/internal inventory data

5. Phase 1 template ingestion 구현
   - `data/phase1_*_template.csv`에 실제 데이터가 채워졌을 때 모델 input으로 merge
   - SKU x region/channel grain forecast로 전환
