# **Cass 수요예측 — 데이터 및 AI 모델 방법론 (v2)**

---

## **1\. Executive Summary**

공개 데이터를 정밀 조사한 결과, **브랜드 단위 월별 실측은 존재하지 않지만, 데이터가 실제로 지지하는 "수요 스트림" 3개로 나누면 논리에 빈틈이 사라진다.** v3은 데이터를 다음 3계층으로 분리한다.

* **Layer A — 전체 알코올 맥주 (정확도 백본, VOLUME).** KOSIS 「품목별 광공업 생산·출하·재고·내수·수출량」의 맥주 **내수량(실측, 월별)**. 예측 정확도 결과는 오직 여기서 시연한다. 주세법상 맥주라 **발포주(기타주류)와 비알콜(음료)은 제외** → Cass Fresh·Light(+경쟁 라거)를 깨끗이 포괄.  
* **Layer B — Cass Fresh / Cass Light 분해 (VALUE 점유율, 앵커).** aT FIS 소매점 POS의 브랜드 매출(카스 후레쉬·카스 라이트, 분기 실측)로 Layer A를 두 라거 브랜드로 분해. 가정이 아니라 **실측 앵커**(가격대가 유사한 두 주류 라거라 value 점유율 ≈ volume 점유율).  
* **Layer C — Cass 0.0 (비알콜, 별도 앵커·시나리오).** 비알콜은 주세법상 음료라 Layer A에 없다. 별도 시장 앵커(국내 비알콜 맥주 시장 규모)로 처리. **비알콜은 발효 공정을 거쳐 탱크를 점유**하므로 배분 문제에는 포함되지만, Cass 0.0 단위 점유율은 시나리오 입력으로 명시.

핵심 원칙 한 줄: **정확도 주장은 실측이 있는 Layer A에서만 하고, 배분은 앵커(B)·시나리오(C)로 분리하며, 운영 단위는 VOLUME, 점유율 산출만 VALUE를 쓰되 그 가교와 경계를 명시한다.**

|  | Layer A | Layer B | Layer C |
| ----- | ----- | ----- | ----- |
| 대상 | 전체 알코올 맥주 | Cass Fresh / Cass Light | Cass 0.0 (비알콜) |
| 소스 | KOSIS 맥주 내수량(실측) | aT FIS POS 브랜드 매출(실측) | 비알콜 맥주 시장규모(업계·보고서) |
| 단위 | **VOLUME** (kL/톤) | VALUE 점유율 → volume 근사 | VALUE 시장규모 → volume 환산 |
| 주기 | 월별 2020–2025 | 분기(점유율 보간) | 연간(추세) |
| 성격 | **실측 (정확도 백본)** | **실측 앵커** | 시나리오(앵커된 추세) |
| 모델 역할 | Chronos-2 예측 대상 | 분해 비율 | 성장 추세 레이어 |

v2 대비 변경: ① SKU를 "브랜드 시계열 가정"에서 "데이터가 지지하는 3 수요 스트림"으로 재정의, ② 비알콜을 별도 계층으로 분리(주세법 근거), ③ value/volume 층 분리와 가교 명시, ④ 발효 점유 관점에서 비알콜 포함 정당화.

---

## **2\. 설계 원칙**

* **방어 가능성 우선(가이드라인 5.2).** 모든 타깃·점유율·단위 변환을 TA 질문에 설명할 수 있어야 한다.  
* **순환참조 금지.** 타깃 생성에 쓴 신호를 그 타깃의 covariate 검증에 쓰지 않는다(Layer A 타깃은 실측, covariate는 별개의 실측 날씨·이벤트).  
* **실측 우선, 가정은 명시(5.3).** 계층별로 실측/앵커/시나리오를 라벨링한다.  
* **단위 일관성.** 발효·배분은 물량(VOLUME), 점유율은 매출액(VALUE) 기반 근사임을 분리하고 가교를 명시한다.  
* **zero-shot 제약.** 모델 가중치를 학습/파인튜닝하지 않는다.

---

## **3\. 3계층 데이터 아키텍처 (핵심)**

### **3.1 Layer A — 전체 알코올 맥주 (정확도 백본, VOLUME)**

* 소스: **KOSIS 「품목별 광공업 생산·출하·재고·내수·수출량」**(통계표 `DT_1F01012`, 광업·제조업동향조사). 이 조사는 매월 품목별로 생산량·출하량·재고량을 **量과 額(금액) 모두** 집계한다.  
* 타깃 변수: **맥주 내수량(domestic, VOLUME)** \= `beer_domestic_volume`. 출하(출하량)는 수출을 포함하므로, 국내 수요 proxy로는 **내수량**이 더 정확하다. (내수 분리가 어려우면 출하량 − 수출량으로 근사.)  
* 적용 범위(중요): 주세법상 맥주만 포함하므로 **발포주(필굿 등 기타주류)와 비알콜(음료)은 제외**된다. 즉 Layer A는 Cass Fresh·Cass Light·경쟁사 라거를 포괄하고 Cass 0.0·발포주는 포함하지 않는다 → 계층 분리가 통계 정의와 정확히 일치.  
* 성격: **유일한 정확도 백본.** 예측 정확도(외생변수 효과 포함) 결과는 여기서만 보고한다.  
* 수요 proxy 타당성: 맥주는 신선도 민감·저재고 품목이라 월별 내수량이 소비와 밀접하다. "내수 기반 수요 proxy"로 표기.

소싱 검증(반나절): ① `DT_1F01012`에서 맥주 품목 코드·단위(kL/톤) 확인 ② 내수량 필드 존재·결측 확인(없으면 출하−수출) ③ 동일 조사의 額(금액) 테이블에서 맥주 출하액/생산액 확인(§4 가교용) ④ 2020-01\~2025-12 월별 가용 확인(월보 \~1개월 시차로 공표).

### **3.2 Layer B — Cass Fresh / Cass Light 분해 (VALUE 점유율, 앵커)**

* 소스: **aT FIS 소매점 POS**(소매점유통POS데이터, 닐슨 기반)의 브랜드별 매출. 카스 후레쉬·카스 라이트가 브랜드 단위로 잡힌다(예: 2019년 4분기 POS에서 오비맥주 제조사 점유율 53.1%, 카스 후레쉬가 매출 1위 브랜드).  
* 처리: Layer A(알코올 맥주 volume)를 **카스 후레쉬·카스 라이트의 점유율**로 분해 → `cass_fresh_volume`, `cass_light_volume`.  
* 분류 정합: 카스 후레쉬·카스 라이트는 **둘 다 주세법상 맥주(라거)** 이므로 Layer A 안에 있다. (OB의 발포주는 필굿으로, Layer A·B 모두에서 제외.) 따라서 "라이트"는 별도 시장 세그먼트가 아니라 **브랜드 단위(카스 라이트)** 로 잡는다 — 공개 통계에 "라이트 세그먼트"라는 깨끗한 축이 없으므로 이게 더 정확하다.  
* 앵커 성격: 가정이 아니라 **POS 실측 점유율**. 점유율은 천천히 변하므로 분기 스냅샷을 월별 보간해도 견고하다.  
* 한계(명시): POS는 소매 스캔 표본(유흥/일부 채널 제외)이라 절대 매출이 아닌 **점유율 proxy**로 사용. 점유율은 채널 편향에 레벨보다 둔감.

### **3.3 Layer C — Cass 0.0 (비알콜, 별도 앵커·시나리오)**

* 분류 근거: 주세법상 알코올 1% 미만은 주류가 아니라 음료(식품위생법 적용)로 분류된다. **Cass 0.0(0.0% 비알콜)은 주류 통계(Layer A)에 없다** → 반드시 별도 앵커.  
* 시장 앵커(실측): 국내 비알콜 맥주 시장 규모 **2023년 잠정 약 590억 원, 2025년 2천억 원 이상 전망**(주류면허법 시행령 입법예고 관련 보도). 글로벌 비알콜 맥주 시장은 2022년 약 220억 달러, 연 5.6% 성장 전망. → 절대 규모와 성장 추세를 앵커로 사용.  
* 처리: 비알콜 시장 규모(연간) × **Cass 0.0의 가정 점유율** → `cass_0_0_scn`(시나리오). 비알콜 시장은 공개치가 연간·희소하므로 covariate 기반 월별 예측 대상이 아니라 **성장 추세 레이어**로 둔다.  
* 발효 관련성(중요): 비알콜(0.0%)은 무알콜(0.00%, 발효 안 함)과 달리 **일반 맥주처럼 발효 후 알코올을 제거**한다 → 실제 발효탱크를 점유한다. 따라서 통계상 음료여도 **AI-2의 발효 배분 문제에는 포함되는 것이 공정상 타당**하다. (이 점이 Layer C를 배분에 넣는 정당화이자, M3/M4 탱크 모델과의 정합 근거.)  
* 한계(명시): 세 스트림 중 데이터가 가장 약함. Cass 0.0 단위 점유율은 시나리오 입력이며, 이를 최대 한계로 보고한다.

---

## **4\. value ↔ volume 층 분리**

* **운영 통화는 VOLUME.** 발효탱크 점유·배분(M3/M4의 batch-equivalent, 84% 가동률, Little's Law)은 전부 물량이다. 따라서 백본(Layer A)과 최종 배분 입력은 물량으로 통일한다.  
* **VALUE는 점유율 산출에만.** aT FIS POS는 매출액(백만원)이라, Layer B의 분해 비율을 만드는 데에만 쓰고 **물량 총량에 직접 합산하지 않는다.**  
* **가교(KOSIS 量/額).** KOSIS는 맥주를 量(volume)과 額(value) 모두 제공하므로, 전체 맥주의 내재 단가(額/量)를 계산해 (a) POS 매출액 점유율을 물량 점유율로 보정하거나, (b) 최소한 "value 점유율 ≈ volume 점유율" 가정의 오차를 정량 점검할 수 있다.  
* **근사의 경계.** Cass Fresh·Light는 가격대가 유사한 주류 라거라 value≈volume 오차가 작다(경계 명시). 반면 Layer C 비알콜은 가격 구조가 달라 별도 환산(시장 규모 ÷ 출처 있는 비알콜 평균 단가)으로 volume-equiv를 만들며, 이 단가 가정을 명시한다(= v1처럼 규모·단가를 동시에 가정하지 않고, 규모는 실측 앵커·단가만 가정).

---

## **5\. 세그먼트 → Cass 매핑 정의**

3개 수요 스트림과 Cass 제품의 매핑, 그리고 분류 근거:

| 수요 스트림 | Cass 제품 | 데이터 출처/성격 | 분류 근거 |
| ----- | ----- | ----- | ----- |
| 알코올 라거 — 레귤러 | Cass Fresh | Layer A × POS 점유율 (실측·앵커) | 주세법 맥주, POS 브랜드 |
| 알코올 라거 — 라이트 | Cass Light | Layer A × POS 점유율 (실측·앵커) | 주세법 맥주(발포주 아님), POS 브랜드 |
| 비알콜 | Cass 0.0 | Layer C 별도 앵커 (시나리오) | 주세법상 음료, 발효 점유 |

* "세그먼트 단위 예측"의 실질: 정확도 예측은 Layer A(알코올 맥주 전체)에서 수행하고, Cass Fresh/Light는 **브랜드 앵커 점유율**로 분해, Cass 0.0는 **별도 비알콜 앵커**로 결합한다. 즉 데이터가 지지하는 선(주류 라거 vs 비알콜, 그리고 브랜드 점유율)만 사용하고, 공개 통계에 없는 "라이트 세그먼트 시계열"을 합성하지 않는다.  
* 배분 의사결정의 단위: 발효 공정 관점에서 레귤러 라거 / 라이트 라거 / 비알콜은 레시피·공정이 구분되며 모두 발효탱크를 점유한다 → 세 스트림에 대한 배분이 AI-2의 핵심 결정과 일치.

---

## **6\. 외생변수(covariate) — 약 10\~15개**

타깃(Layer A 내수량) 생성과 분리되고, 예측 시점에 알 수 있는지(known-future)가 명확한 변수만.

| 그룹 | 변수(예) | 가용성 | 비고 |
| ----- | ----- | ----- | ----- |
| 날씨·환경 | 월평균기온, 폭염일수(33℃↑), 열대야일수 | known-future \= 평년/KMA 전망, 과거=관측 | 미래 월 기온은 평년·전망 근사(불확실성 명시) |
| 이벤트·캘린더 | KBO 경기수, 대형스포츠(월드컵) 더미, 공휴일·연휴일수, 축제수 | known-future | 달력 확정 → 가장 깨끗한 covariate |
| 가격·경제 | 수입맥주 단가 YoY, OB 가격인상 더미 | 인상 더미 known-future, 단가 lag | 2024-04·2025-04 인상 |
| (선택) 관심도·뉴스 | Google Trends, 뉴스량 | known-past → t−1 lag | nowcasting 위험, 약한 covariate라 드롭 권장 |

* known-future와 known-past(lag)를 명확히 구분. 검색량·뉴스·실현 기온처럼 미래값을 모르는 변수는 lag 또는 제외. v1의 뉴스 제목 감성 proxy는 기본 제외.  
* ※ Google Trends·수입량을 **타깃 생성에서 제거**(Layer A는 KOSIS 실측)했으므로, 이제 이들을 covariate로 검증해도 순환참조가 아니다.

---

## **7\. 최종 데이터셋 구조**

| 구성 | 컬럼(예) | 계층/성격 | 단위 |
| ----- | ----- | ----- | ----- |
| 키 | `month` (2020-01\~2025-12) | — | — |
| 백본 타깃 | `beer_domestic_volume` | A · 실측 | VOLUME |
| 가교 보조 | `beer_value`(KOSIS 額) | A · 실측 | VALUE |
| 분해 점유율 | `cass_fresh_share`, `cass_light_share` | B · 앵커 | VALUE→volume 근사 |
| 비알콜 앵커 | `nonalc_market_value`(연간) | C · 앵커 | VALUE |
| 시나리오 타깃 | `cass_fresh_volume`, `cass_light_volume`, `cass_0_0_scn` | A×B / C | VOLUME(또는 volume-equiv) |
| covariate | §6의 10\~15개 | — | known-future/lag |

* 파일: `cass_demand_v3_monthly.csv`, 변수 사전 `cass_demand_v3_dictionary.csv`(출처·계층·단위·가용성·가정), 검증요약 `cass_demand_v3_validation.csv`.

---

## **8\. AI 모델 — zero-shot 파운데이션 모델**

### **8.1 모델: Chronos-2**

* Chronos-2(Amazon, 2025-10): 120M 인코더형 시계열 파운데이션 모델. **zero-shot**으로 univariate·multivariate·**covariate-informed** 예측을 지원(in-context learning). **다단계 분위수(quantile) 예측**을 native로 출력. 공개모델 중 GIFT-Eval·fev-bench SOTA, 특히 covariate 과제에서 이득이 큼. GPU/CPU 추론 가능. `pip install chronos-forecasting`.  
* 선택 근거: finetuning 불가 제약과 정합(zero-shot), known-future covariate 투입 가능, M4의 80%/95% 예측구간 요구와 정합(분위수 native).

### **8.2 실험 설계 (Layer A에서 수행)**

1. **univariate** — Layer A 내수량만 입력(계절성 한계 측정).  
2. **covariate-informed** — \+ §6 known-future covariate(날씨·이벤트·가격). univariate→covariate 오차 차이 \= 외생변수 **실제** 기여(타깃 실측이라 정당).  
3. (선택) **multivariate** — Layer A(알코올 맥주)와 Layer C(비알콜 시장) 등 공진 시리즈 공동 예측. 단, Cass Fresh/Light 분해는 Layer B 점유율로 처리(브랜드 시계열을 직접 학습하지 않음).

### **8.3 베이스라인·평가**

* 베이스라인(필수): **Seasonal Naive**(전년 동월). 선택 ETS/SARIMA.  
* 지표: MASE/WAPE(점추정) \+ pinball(분위수). 모두 Seasonal Naive 대비.  
* 검증: Train 컨텍스트 2020–2023, **검증 2024–2025(실측)**. (v1처럼 generated 구간을 평가에 쓰지 않음 — Layer A는 실측이므로 가능.)  
* **routine 월 vs event 월(폭염·월드컵) 분리 보고**(M4 §2.3 event-holdout).

### **8.4 정직한 기대치 (가이드라인 Failure Modes·5.2)**

* 짧은 데이터 \+ Google Trends류 covariate에 zero-shot TSFM을 적용한 연구(arXiv 2602.12120, 2026-03)는 covariate 투입이 **일률적 이득이 아니며** 짧은 표본·전환점에서 악화될 수 있음을 보고. → Seasonal Naive 강베이스라인 유지, covariate 효과는 "견고·재현되는 오차 감소"로 해석, event 월 위주로 검증·보고. 헤드라인은 "실측 날씨·이벤트가 계절 베이스라인 대비 오차를 줄이는지 정직 검증"으로.

### **8.5 대안 모델**

* Moirai/Moirai-MoE(zero-shot covariate), Chronos-Bolt \+ AutoGluon covariate regressor(CatBoost), TimesFM 2.x(`forecast_with_covariates`, 짧은 데이터엔 약할 수 있음).

---

## **9\. 의사결정 연결 및 주기 정합 (M3/M4)**

* **VOLUME 일관.** Layer A 내수량 예측(분위수) → M4 Branch 1 구간 인지 배분. 발효탱크 점유·가동률·Little's Law가 모두 물량이라 백본과 단위가 일치.  
* **세 스트림 배분.** 레귤러 라거(Cass Fresh) / 라이트 라거(Cass Light) / 비알콜(Cass 0.0)에 발효 capacity를 배분. Layer B 점유율로 Fresh/Light를 나누고, Layer C(발효 점유하는 비알콜)를 별도 스트림으로 더한다.  
* **주기(월별 근거).** 발효 리드타임 17일 → 의사결정은 "다음 달 발효 계획"에 가깝다. M4의 "일 06:00 갱신 / SKU×region×day / 주간 커밋"은 **월 단위 예측(1\~3개월, 월 1회 \+ 이벤트 트리거) / 발효 리드타임에 맞춘 월·격주 커밋**으로 정합화. 일별 안전재고는 월 예측 기반 운영 규칙(M4 Branch 2). region은 데이터(서울)와 맞춰 **국가 단위**, 지역 세분은 future work.  
* **시나리오2 시연.** 2026년 6\~7월(폭염+월드컵 월)을 기온·이벤트 covariate로 사전 인지 → 해당 월 발효 사전 배분.

---

## **10\. 검증 및 한계 (Data Readiness / Limitations)**

| 항목 | 성격 | 비고 |
| ----- | ----- | ----- |
| Layer A 맥주 내수량(월별) | **실측** | KOSIS, 정확도 백본 |
| KOSIS 額(금액) | **실측** | value↔volume 가교 |
| Cass Fresh/Light 점유율 | **실측 앵커** | aT FIS POS(분기), value≈volume 근사 |
| 비알콜 시장 규모 | **실측 앵커(희소)** | 590억(’23)→2000억(’25E), 연간 |
| Cass 0.0 점유율 | **시나리오** | 가정, 최대 한계 |
| 미래 월 기온 covariate | 가정(평년/전망) | 불확실성 명시 |

* 한계: ① Cass 0.0(비알콜)은 공개 실측이 희소 → 성장 추세 시나리오. ② POS는 소매 스캔 표본 → 점유율 proxy. ③ value≈volume 근사(Fresh/Light는 오차 작음, 비알콜은 별도 환산·단가 가정). ④ 72개월 짧은 표본 → covariate 효과가 작거나 event 월 한정 가능. ⑤ 주/일·지역 동학은 데이터로 표현 불가(POS 확보 시 future work).  
* 이 표·한계를 최종보고서 "AI Opportunity Analysis: Data Readiness/Feasibility"와 "Lessons Learned & Limitations"에 매핑.

### **10.1 잠재적 반론과 방어 (TA Q\&A 대비, 5.2)**

* "타깃이 Google Trends로 만들어진 것 아니냐?" → 아니다. Layer A 타깃은 KOSIS 맥주 내수량 **실측**이고, Google Trends는 (쓴다면) 검증용 covariate일 뿐 타깃 생성에 없다.  
* "Cass 0.0이 왜 주류 통계에 없냐?" → 주세법상 알코올 1% 미만은 음료라 주류 통계 밖. 그래서 별도 비알콜 시장 앵커(Layer C)를 쓴다.  
* "비알콜은 술도 아닌데 발효 배분에 왜 넣냐?" → 비알콜(0.0%)은 무알콜(0.00%)과 달리 발효 후 알코올을 제거하므로 **발효탱크를 점유**한다. 따라서 capacity 배분 대상이 맞다.  
* "POS는 매출액인데 물량 배분에 쓰면 단위가 틀리지 않냐?" → 물량 총량은 KOSIS volume(Layer A)으로 잡고, POS는 점유율 산출에만 쓰며, KOSIS 額/量으로 가교·오차 점검한다. Fresh/Light는 가격대가 유사해 근사 오차가 작다.  
* "라이트 세그먼트 데이터는 어디서 났냐?" → 별도 "라이트 세그먼트" 시계열을 만들지 않는다. 카스 라이트는 POS **브랜드** 단위로 잡고 Layer A를 점유율로 분해한다.  
* "외생변수가 정말 정확도를 높이냐?" → 일률적 이득을 주장하지 않는다. Seasonal Naive 대비 univariate vs covariate를 비교하고, event 월 위주로 효과를 정직하게(없으면 없다고) 보고한다.

---

## **11\. 재현 워크플로우**

1. KOSIS `DT_1F01012` 맥주 **내수량(volume)** \+ 額(value) 수집, §3.1 검증.  
2. aT FIS POS에서 카스 후레쉬·카스 라이트 점유율(분기) 수집 → 월별 보간.  
3. 비알콜 맥주 시장 규모(연간) 수집 → Cass 0.0 시나리오 점유율 적용.  
4. value↔volume 가교(KOSIS 額/量) \+ Fresh/Light 점유율 보정.  
5. covariate 10\~15개 구성(known-future/lag), 변수 사전 작성.  
6. Chronos-2 zero-shot: Layer A univariate / covariate-informed (+선택 multivariate) \+ Seasonal Naive.  
7. MASE/WAPE/pinball, routine vs event 월 분리 평가.  
8. 분위수 → 세 스트림 발효 배분(M4 Branch 1\) 연결, M3 시나리오2 월별 시연.  
9. M3/M4 일·주·지역 서술을 월·국가 단위로 정합화.

---

## **12\. 참고 출처**

* KOSIS 「품목별 광공업 생산·출하·재고·내수·수출량」 `DT_1F01012`(광업·제조업동향조사) — 맥주 월별 생산/출하/내수 量·額 실측. https://kosis.kr  
* aT FIS 식품산업통계정보 — 소매점 POS(브랜드별 매출), 가공식품 세분시장 현황 보고서, 식품시장 뉴스레터(맥주). https://www.atfis.or.kr  
* 비알콜 맥주 분류·시장: 주세법상 알코올 1% 미만 \= 음료(식품의약품안전처/주세법); 국내 비알콜 맥주 시장 2023 잠정 590억 → 2025 2천억 전망(주류면허법 시행령 입법예고 보도); 세계 무알콜 맥주 시장 2022 약 220억 달러, CAGR 5.6%.  
* Chronos-2(zero-shot univariate/multivariate/covariate, 분위수, 공개모델 GIFT-Eval·fev-bench SOTA) — GitHub `amazon-science/chronos-forecasting` · HF `amazon/chronos-2` · arXiv 2510.15821.  
* 짧은 데이터 \+ Google Trends류 covariate에서 zero-shot TSFM의 covariate 효과가 일률적이지 않다는 근거 — arXiv 2602.12120(2026-03). (보조: COSMIC arXiv 2506.03128, Moirai, TimesFM v2.)