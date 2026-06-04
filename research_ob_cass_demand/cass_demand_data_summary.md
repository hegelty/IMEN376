# OB맥주 Cass 제품군 수요예측 데이터 수집 요약

작성일: 2026-05-28  
프로젝트: IMEN343 생산운영관리 Term Project — OB맥주 Cass 제품군 공급망/생산운영 최적화

## 1. 결론

공개자료 기준으로 **Cass Fresh, Cass Light, Cass 0.0 각각의 실제 생산량·출고량·판매량 시계열은 확인되지 않았다.**  
다만 프로젝트에서 AI 수요예측 기회를 보이기에는 충분한 대체 데이터가 확보되었다.

가장 쓸 만한 데이터는 다음 순서다.

1. **Cass 단일 브랜드 매출:** USDA/FAS `South Korea Beer Market Report`가 2023년 Cass 매출을 **1.52조 원**으로 제시한다.
2. **Cass Fresh / Cass Light 가정시장 점유율:** 닐슨코리아 인용 기사 기준 2024H1 Cass Fresh **44.0%**, Cass Light **3.4%**; 2025Q2 Cass Fresh **48.8%**, Cass Light **4.9%**.
3. **전체 맥주 시장 장기 수요:** e-나라지표/국세청 맥주 국내 출고량 1994~2024. 2024년은 **1,637천 kL**.
4. **apparent market:** 국내 출고량 + HS2203 수입 - HS2203 수출. 2024년은 **약 1,759.1천 kL**.
5. **모델 외생변수:** 검색량(Naver/Google), 날씨(ASOS), 공휴일, KBO 일정, CPI/가격, 수입맥주 HS2203.

## 2. 생성한 파일

| 파일 | 내용 |
|---|---|
| `data/beer_market_timeseries_1994_2024.csv` | 1994~2024 국내 맥주 출고량, 수입/수출, apparent market 추정치 |
| `data/cass_ob_key_observations.csv` | Cass/OB 관련 핵심 실측·보도·추정 수치와 출처 |
| `data/cass_volume_proxy_scenarios.csv` | Cass Fresh/Light/OB 전체 물량 프록시 계산 시나리오 |
| `data/forecasting_data_sources.csv` | 수요예측 모델용 데이터 소스 체크리스트 |
| `cass_demand_data_summary.md` | 현재 문서 |

## 3. 핵심 실제/준실제 데이터

| 대상 | 기간 | 수치 | 성격 | 출처 |
|---|---:|---:|---|---|
| Cass | 2023 | 1.52조 원 매출 | Cass 단일 브랜드 매출, Company Data 인용 | USDA/FAS KS2024-0035 Table 3 |
| Cass | 2023 | 국내 맥주 제품 매출 1위 | 순위 | USDA/FAS KS2024-0035 |
| Cass Fresh | 2024H1 | 44.0% | 가정시장 판매량 점유율 | 닐슨코리아 인용 기사 |
| Cass Light | 2024H1 | 3.4% | 가정시장 판매량 점유율 | 닐슨코리아 인용 기사 |
| OB맥주 | 2024H1 | 55.3% | 가정시장 제조사 판매량 점유율 | 닐슨코리아 인용 기사 |
| Cass Fresh | 2025Q2/H1 | 48.8% | 가정시장 판매량 점유율 | BusinessKorea 등 |
| Cass Light | 2025Q2 | 4.9% | 가정시장 판매량 점유율 | BusinessKorea 등 |
| OB맥주 | 2024 | 1조 7,404억 원 매출 | DART 감사보고서 인용 보도 | NewsSpace |
| 전체 맥주 | 2024 | 1,637천 kL | 공식 국내 출고량 | e-나라지표/국세청 |
| 전체 맥주 | 2024 | 1,759.1천 kL | apparent market 추정 | 국세청 + UN Comtrade |

## 4. 제품별 판매량이 없을 때의 프록시 산식

### 4.1 가정시장 점유율 기반 물량 프록시

```text
제품 물량 proxy = 전체 맥주 시장 물량 × 제품 가정시장 판매량 점유율
```

예시:

| 시나리오 | 계산식 | 결과 | 해석 |
|---|---:|---:|---|
| Cass Fresh 2024H1 기준 | 1,637,210 kL × 44.0% | 약 720,372 kL | 보수적 기준 프록시 |
| Cass Light 2024H1 기준 | 1,637,210 kL × 3.4% | 약 55,665 kL | Light 규모감 |
| Cass Fresh 2025Q2 기준 | 1,637,210 kL × 48.8% | 약 798,959 kL | 성장 시나리오 |
| Cass Light 2025Q2 기준 | 1,637,210 kL × 4.9% | 약 80,223 kL | 성장 시나리오 |
| OB 전체 2025Q1 기준 | 1,637,210 kL × 60.1% | 약 983,963 kL | capacity upper/check |

주의: 이 값들은 **실제 출하량이 아니다.** 가정시장(off-trade) 점유율을 전체 출고량에 곱한 값이라 유흥시장(on-trade), 수입맥주, 제품 믹스 차이를 무시한다. 보고서에는 “수요예측 모델 초기값/시나리오용 proxy”라고 명시해야 한다.

### 4.2 Cass 매출 역산 물량 rough estimate

USDA/FAS의 2023 Cass 매출 1.52조 원을 2019년 평균 맥주 출고가로 나누면:

```text
2019 평균 맥주 출고가 = 3,688,267백만원 / 1,715,995 kL ≈ 2.149 백만원/kL
Cass 물량 rough estimate = 1,520,000백만원 / 2.149 ≈ 707,192 kL
```

이 산식은 가격단계, 연도, 채널, 제품 믹스가 다르기 때문에 **매우 거친 보조 추정**이다. 점유율 기반 프록시와 함께 민감도 범위로만 쓰는 편이 안전하다.

## 5. 모델링 권장안

### A안: 연간 시장 수요 모델 — 가장 안전

- y: `beer_market_timeseries_1994_2024.csv`의 `apparent_market_thousand_kl_est` 또는 `domestic_beer_shipments_thousand_kl`
- X: 수입맥주량, 평균기온/폭염일수, CPI, 소비 트렌드, 경기침체/코로나 더미
- 장점: 장기 시계열이 있어 모델 설명이 안정적
- 단점: Cass 제품별 생산계획으로 바로 내려가기엔 coarse함

### B안: Cass 제품군 시나리오 모델 — 프로젝트 목적에 가장 적합

- y_base: 전체 맥주 시장 수요
- share assumptions: Cass Fresh 44.0~48.8%, Cass Light 3.4~4.9%, OB 전체 55.3~60.1%
- Cass 0.0/All Zero: 무·비알코올 시장 성장률과 검색량을 별도 성장 SKU로 둠
- capacity constraint: Cass Fresh + Cass Light + 0.0 + 기타 OB 제품 ≤ OB 전체 share

### C안: 월별 데모 모델 — 발표 시각화에 좋음

- y 후보: aTFIS POS 월별 맥주 매출 또는 HS2203 월별 수입맥주량
- X: `카스`, `카스 라이트`, `카스 0.0`, `맥주` 검색량 + ASOS 날씨 + 공휴일 + KBO 경기 수 + CPI
- 모델: SARIMAX/Prophet/LightGBM with lag features

## 6. 보고서에 넣을 Caveat 문구

> OB맥주 및 Cass 제품군의 SKU별 실제 생산량·출고량·판매량은 공개자료에서 확인되지 않았다. 따라서 본 프로젝트는 공식 전체 맥주 출고량, 수입·수출 통계, Cass 브랜드 매출, 가정시장 점유율, 검색량·날씨·가격 등의 외생변수를 결합해 수요예측 가능성을 보이는 proxy model로 설계한다. 모든 추정 물량은 실제 내부 판매량이 아니라 생산운영 모델의 초기 시나리오 입력값으로 해석한다.

## 7. 1차 추천 입력값

발표/보고서에서 바로 쓰려면 다음 세트를 추천한다.

- 전체 시장 기준: 2024 domestic shipments **1,637천 kL**, apparent market **1,759.1천 kL**
- Cass Fresh share: 보수 **44.0%**, 성장 **48.8%**
- Cass Light share: 보수 **3.4%**, 성장 **4.9%**
- OB manufacturer share cap: **55.3~60.1%**
- Cass 0.0: 판매량 미공개. 무·비알코올 시장 성장 SKU로 별도 처리
- Cass 단일 브랜드 매출 anchor: 2023 **1.52조 원**

## 8. 추가 월별 데이터셋

사용자가 월별 예측 모델을 만들 수 있도록, 추가로 월별 proxy/modeling dataset을 생성했다.

| 파일 | 내용 |
|---|---|
| `data/monthly_beer_segment_modeling_dataset_2020_2025.csv` | 최종 모델 입력용 월별 데이터셋. 전체 알코올 맥주, 일반 맥주, 저칼로리/라이트 맥주, 논알콜/무알콜 맥주, Cass Fresh/Light/0.0 proxy와 외생변수 포함 |
| `data/monthly_beer_segment_demand_proxy_2020_2025.csv` | 월별 수요 proxy 본체 |
| `data/monthly_beer_segment_demand_proxy_validation.csv` | 연간 anchor와 월별 합계 검증표 |
| `data/monthly_hs2203_comtrade_korea_2020_2025.csv` | UN Comtrade HS2203 월별 한국 맥주 수입/수출 실제값 |
| `data/monthly_google_trends_beer_segments_2020_2026.csv` | Google Trends 맥주/수입맥주/무알콜/논알콜 검색 관심도 |
| `data/monthly_google_trends_cass_products_2020_2026.csv` | Google Trends 카스/카스 라이트/카스 제로 검색 관심도 |
| `data/monthly_weather_seoul_open_meteo_2020_2025.csv` | 서울 월별 날씨 외생변수 |
| `monthly_demand_proxy_method.md` | 월별 데이터 생성 산식과 caveat |

중요: 2020~2024년 전체 알코올 맥주 총량은 공식 연간 통계에 맞춰 월별로 분해했다. 2025년은 공식 연간 출고량이 아직 없으므로 provisional generated 값이다.
