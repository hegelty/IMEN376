# OB맥주 Cass 제품군 수요예측 데이터 수집 보고서

작성일: 2026-05-28  
과목/프로젝트: IMEN343 생산운영관리 Term Project — OB맥주 Cass 제품군 공급망 및 생산운영 최적화  
작성 목적: Cass Fresh, Cass Light, Cass 0.0/All Zero 수요예측 모델 구축을 위한 공개 데이터 수집, 가용성 평가, 월별 프록시 데이터셋 구축 방법 정리

---

## 1. Executive Summary

본 조사는 OB맥주 Cass 제품군의 AI 기반 수요예측 가능성을 보이기 위해 수행되었다. 최초 목표는 Cass Fresh, Cass Light, Cass 0.0 각각의 실제 월별 생산량·출고량·판매량을 확보하는 것이었으나, 공개자료 조사 결과 **SKU별 실제 월별 판매량 또는 출고량은 공개되어 있지 않다**는 결론에 도달했다.

다만 프로젝트 목적상 수요예측 모델을 구축할 수 있도록, 다음의 공개·준공식 데이터와 월별 프록시를 결합하여 **월별 세그먼트 수요 데이터셋**을 생성했다.

- 공식 연간 맥주 시장 규모: 국세청/e-나라지표 맥주 출고량 1994~2024
- 월별 시장 계절성 proxy: UN Comtrade HS2203 한국 맥주 수입·수출 월별 자료 2020~2025
- 브랜드/세그먼트 관심도 proxy: Google Trends `맥주`, `카스`, `카스 라이트`, `카스 0.0`, `무알콜 맥주`, `논알콜 맥주`
- 외생변수: 서울 월별 날씨, 공휴일 수, 주말 수, 여름 성수기, KBO 시즌 더미
- 공개 점유율 anchor: Cass Fresh, Cass Light 가정시장 점유율 및 OB맥주 제조사 점유율
- 시장 규모 anchor: 무·비알코올 맥주 시장 규모 및 성장 전망

최종 산출물은 `data/monthly_beer_segment_modeling_dataset_2020_2025.csv`이며, 2020년 1월부터 2025년 12월까지 월별 72개 행과 38개 컬럼으로 구성되어 있다. 이 파일은 전체 알코올 맥주, 일반 맥주, 저칼로리/라이트 맥주, 논알콜/무알콜 맥주, Cass Fresh, Cass Light, Cass 0.0/All Zero 프록시 수요 및 외생변수를 포함한다.

---

## 2. 데이터 수집 목표 및 기준

### 2.1 원래 목표

프로젝트의 생산운영관리 관점에서 필요한 데이터는 다음과 같았다.

1. Cass Fresh 월별 수요 또는 판매량
2. Cass Light 월별 수요 또는 판매량
3. Cass 0.0 / Cass All Zero 월별 수요 또는 판매량
4. 제품군별 수요예측에 사용할 외생변수
   - 날씨
   - 계절성
   - 공휴일
   - 스포츠/이벤트
   - 검색 관심도
   - 가격 또는 시장규모

### 2.2 데이터 평가 기준

수집 데이터는 다음 기준으로 구분했다.

| 구분 | 의미 | 예시 |
|---|---|---|
| 공개 실측 | 공식 통계 또는 시장조사 수치가 직접 공개된 값 | 국세청 맥주 출고량, UN Comtrade 수입량 |
| 공개 보도/준공식 | 기사 또는 보고서가 시장조사/회사자료를 인용한 값 | USDA/FAS의 Cass 2023 매출, 닐슨코리아 인용 점유율 |
| 프록시 | 직접 수요는 아니지만 수요와 관련 있는 월별 대체 지표 | Google Trends, 수입맥주 월별 수입량 |
| 생성 데이터 | 공식 연간 총량과 프록시를 결합해 만든 모델용 데이터 | 월별 세그먼트별 수요 proxy |

---

## 3. 핵심 수집 결과

### 3.1 제품별 실제 데이터 가용성

| 제품/범위 | 실제 월별 판매량 | 실제 연간 판매량 | 공개 매출/점유율 | 판단 |
|---|---:|---:|---:|---|
| Cass Fresh | 미공개 | 미공개 | 가정시장 판매량 점유율 공개 | 점유율 기반 프록시 가능 |
| Cass Light | 미공개 | 미공개 | 가정시장 판매량 점유율 공개 | 저칼로리 맥주 세그먼트 proxy 가능 |
| Cass 0.0 / All Zero | 미공개 | 미공개 | 정확 점유율 미공개 | 무·비알코올 시장 성장률 기반 생성 필요 |
| Cass 전체 브랜드 | 미공개 | 미공개 | 2023 매출 1.52조 원 | 매출 anchor로 활용 가능 |
| 전체 맥주 시장 | 월별 국내 출고량 미공개 | 연간 출고량 공개 | 1994~2024 장기 시계열 | 연간 anchor로 활용 |

가장 중요한 발견은 USDA/FAS `South Korea Beer Market Report`에서 2023년 Cass 단일 브랜드 매출이 **1.52조 원**으로 제시된 점이다. 이는 판매량은 아니지만 Cass 브랜드 규모를 보여주는 가장 강한 공개 anchor다.

### 3.2 주요 공개 수치

| 항목 | 기간 | 수치 | 성격 | 출처 |
|---|---:|---:|---|---|
| Cass 브랜드 매출 | 2023 | 1.52조 원 | 회사자료 인용 | USDA/FAS KS2024-0035 |
| Cass 국내 맥주 제품 순위 | 2023 | 1위 | 회사자료 인용 | USDA/FAS KS2024-0035 |
| Cass Fresh 가정시장 점유율 | 2024H1 | 44.0% | 닐슨코리아 인용 | 동아일보/매일경제/아주경제 등 |
| Cass Light 가정시장 점유율 | 2024H1 | 3.4% | 닐슨코리아 인용 | 동아일보/매일경제/아주경제 등 |
| OB맥주 제조사 가정시장 점유율 | 2024H1 | 55.3% | 닐슨코리아 인용 | 동아일보/매일경제/아주경제 등 |
| Cass Fresh 가정시장 점유율 | 2025Q2/H1 | 48.8% | 보도/시장조사 인용 | BusinessKorea 등 |
| Cass Light 가정시장 점유율 | 2025Q2 | 4.9% | 보도/시장조사 인용 | BusinessKorea 등 |
| 전체 맥주 국내 출고량 | 2024 | 1,637천 kL | 공식 통계 | e-나라지표/국세청 |
| 전체 맥주 apparent market | 2024 | 1,759.1천 kL | 계산값 | 국세청 + UN Comtrade |
| 무·비알코올 맥주 시장 | 2023 | 644억 원 | 시장조사/보도 | Euromonitor 인용 보도 |

---

## 4. 수집 및 생성 데이터 파일

### 4.1 원자료 및 요약 파일

| 파일 | 행/컬럼 | 내용 |
|---|---:|---|
| `data/beer_market_timeseries_1994_2024.csv` | 31행 / 7컬럼 | 1994~2024 국내 맥주 출고량, 수입/수출, apparent market |
| `data/cass_ob_key_observations.csv` | 22행 / 9컬럼 | Cass/OB 핵심 수치, 출처, 실제/추정 구분 |
| `data/cass_volume_proxy_scenarios.csv` | 8행 / 9컬럼 | Cass Fresh/Light/OB 물량 프록시 계산 시나리오 |
| `data/forecasting_data_sources.csv` | 12행 / 6컬럼 | 추가 수요예측 데이터 소스 목록 |

### 4.2 월별 모델링 데이터

| 파일 | 행/컬럼 | 내용 |
|---|---:|---|
| `data/monthly_beer_segment_modeling_dataset_2020_2025.csv` | 72행 / 38컬럼 | 최종 모델 입력용 월별 데이터셋 |
| `data/monthly_beer_segment_demand_proxy_2020_2025.csv` | 72행 / 28컬럼 | 월별 수요 proxy 본체 |
| `data/monthly_beer_segment_demand_proxy_validation.csv` | 6행 / 11컬럼 | 연간 anchor와 월별 합계 검증 |
| `data/monthly_hs2203_comtrade_korea_2020_2025.csv` | 72행 / 8컬럼 | HS2203 월별 맥주 수입/수출 실제값 |
| `data/monthly_google_trends_beer_segments_2020_2026.csv` | 77행 / 7컬럼 | 맥주/수입맥주/무알콜/논알콜 검색 관심도 |
| `data/monthly_google_trends_cass_products_2020_2026.csv` | 77행 / 7컬럼 | 카스/카스 라이트/카스 제로 검색 관심도 |
| `data/monthly_weather_seoul_open_meteo_2020_2025.csv` | 72행 / 7컬럼 | 서울 월별 날씨 외생변수 |

---

## 5. 월별 수요 데이터 생성 방법

### 5.1 전체 알코올 맥주 시장

연간 전체 맥주 시장은 다음 방식으로 계산했다.

```text
연간 맥주 apparent market(kL)
= 국내 맥주 출고량(kL) + HS2203 수입량(kL 근사) - HS2203 수출량(kL 근사)
```

국내 맥주 출고량은 e-나라지표/국세청 자료를 사용했고, 수입·수출은 UN Comtrade HS2203 월별 및 연간 자료를 사용했다. 맥주는 밀도가 물과 유사하므로 수입·수출 중량에 대해 `1t ≈ 1kL` 근사를 적용했다.

연간 총량을 월별로 분해하기 위해 다음 월별 가중치를 만들었다.

```text
월별 weight
= normalize(0.45 × 월별 HS2203 수입량 + 0.55 × Google Trends '맥주')

월별 알코올 맥주 수요 proxy
= 연간 맥주 apparent market × 월별 weight
```

이 방식은 수입맥주 월별 움직임과 소비자 검색 관심도를 결합하여 맥주 수요의 계절성을 반영하기 위한 것이다.

### 5.2 일반 맥주와 저칼로리/라이트 맥주 분리

저칼로리/라이트 맥주는 Cass Light 점유율과 보도된 light beer 성장률을 근거로 별도 세그먼트로 분리했다.

공개 anchor:
- Cass Light 2024H1 가정시장 점유율: 3.4%
- Cass Light 2025Q2 가정시장 점유율: 4.9%
- 2024년 이마트 light beer 매출 YoY +32%, 전체 맥주 매출 -6.4% 보도

생성 가정:

```text
연간 light/low-calorie share
2020: 2.4%
2021: 2.5%
2022: 2.7%
2023: 3.0%
2024: 3.6%
2025: 4.7%

월별 low-calorie 수요
= 연간 맥주 시장 × 연간 light share × 월별 light weight
```

일반 맥주는 전체 알코올 맥주에서 저칼로리/라이트 맥주를 차감해 계산했다.

```text
일반 맥주 수요 proxy
= 전체 알코올 맥주 수요 proxy - 저칼로리/라이트 맥주 수요 proxy
```

### 5.3 논알콜/무알콜 맥주 세그먼트

논알콜/무알콜 맥주는 알코올 맥주 출고량 통계에 직접 포함되지 않거나 정의가 다를 수 있으므로, 시장규모 금액 자료를 별도 anchor로 사용했다.

공개 anchor:
- FIS: 무알콜 맥주 시장 2014년 81억 원 → 2019년 153억 원
- Euromonitor/보도: 2021년 415억 원, 2023년 644억 원, 2027년 1,000억 원 전망
- 2025H1 Hite Zero 0.00 판매액 점유율 37.5%; Cass 0.0 정확 점유율은 미공개

생성 가정:

```text
연간 non-alcoholic beer market value
2020: 280억 원
2021: 415억 원
2022: 520억 원
2023: 644억 원
2024: 700억 원
2025: 800억 원

월별 value
= 연간 value × normalize(Google Trends '무알콜 맥주' + '논알콜 맥주')

월별 volume proxy
= 월별 value / 4.0백만원 per kL
```

여기서 4.0백만원/kL은 1L당 4,000원으로 환산한 rough assumption이다. 실제 제품 가격과 유통채널에 따라 달라질 수 있으므로, 이 값은 절대 판매량이 아니라 모델용 scale proxy로 해석해야 한다.

### 5.4 Cass 제품군으로의 배분

Cass Fresh와 Cass Light는 공개 점유율을 사용해 다음 방식으로 프록시를 생성했다.

```text
Cass Fresh proxy = 전체 맥주 시장 × Cass Fresh share assumption × 월별 맥주 weight
Cass Light proxy = 전체 맥주 시장 × Cass Light share assumption × 월별 light weight
```

Cass 0.0 / All Zero는 정확한 공개 점유율이 없어 무·비알코올 시장 내 Cass 계열 가정 점유율을 적용했다. 이 값은 실제 자료가 아니라 시나리오 변수로 처리해야 한다.

---

## 6. 월별 데이터 검증

생성 데이터는 연간 anchor와 월별 합계가 일치하는지 검증했다. 2020~2024년은 공식 연간 자료에 맞춘 `official-constrained` 상태이며, 2025년은 아직 공식 출고량이 없어 `generated/provisional` 상태다.

| 연도 | 상태 | 연간 알코올 맥주 anchor(kL) | 월별 합계(kL) | 저칼로리/라이트(kL) | 논알콜/무알콜(kL) |
|---:|---|---:|---:|---:|---:|
| 2020 | official-constrained | 1,735,600 | 1,735,600 | 41,654 | 7,000 |
| 2021 | official-constrained | 1,700,900 | 1,700,900 | 42,523 | 10,375 |
| 2022 | official-constrained | 1,824,200 | 1,824,200 | 49,253 | 13,000 |
| 2023 | official-constrained | 1,822,000 | 1,822,000 | 54,660 | 16,100 |
| 2024 | official-constrained | 1,759,100 | 1,759,100 | 63,328 | 17,500 |
| 2025 | generated/provisional | 1,899,828 | 1,899,828 | 89,292 | 20,000 |

검증 결과, 2020~2024년 월별 알코올 맥주 수요 proxy의 합계는 연간 apparent market anchor와 일치한다. 따라서 월별 분포는 생성값이지만, 연간 총량은 공식 통계 기반 시장 규모를 유지한다.

---

## 7. 최종 모델링 데이터셋 구성

최종 파일 `data/monthly_beer_segment_modeling_dataset_2020_2025.csv`의 주요 컬럼은 다음과 같다.

### 7.1 수요 타깃 컬럼

| 컬럼 | 의미 |
|---|---|
| `alcoholic_beer_total_proxy_kl` | 전체 알코올 맥주 월별 수요 proxy |
| `regular_beer_excluding_low_calorie_proxy_kl` | 저칼로리/라이트를 제외한 일반 맥주 수요 proxy |
| `low_calorie_light_beer_proxy_kl` | 저칼로리/라이트 맥주 수요 proxy |
| `nonalcoholic_beer_proxy_kl` | 논알콜/무알콜 맥주 수요 proxy |
| `cass_fresh_proxy_kl` | Cass Fresh 월별 수요 proxy |
| `cass_light_proxy_kl` | Cass Light 월별 수요 proxy |
| `cass_0_0_or_all_zero_proxy_kl` | Cass 0.0 / All Zero 월별 수요 proxy |

### 7.2 외생변수 컬럼

| 컬럼 | 의미 |
|---|---|
| `hs2203_import_kg_actual` | 월별 맥주 수입 중량 실제값 |
| `hs2203_export_kg_actual` | 월별 맥주 수출 중량 실제값 |
| `google_trends_beer` | `맥주` 검색 관심도 |
| `google_trends_nonalc_beer` | `무알콜 맥주` + `논알콜 맥주` 검색 관심도 |
| `google_trends_cass_beer` | `카스 맥주` 검색 관심도 |
| `google_trends_cass_light` | `카스 라이트` 검색 관심도 |
| `google_trends_cass_zero_terms` | `카스 0.0`, `카스 제로`, `카스 올제로` 검색 관심도 합산 |
| `seoul_avg_temp_c` | 서울 월평균기온 |
| `seoul_hot_days_30c` | 서울 월별 30℃ 이상 일수 |
| `seoul_precipitation_mm` | 서울 월강수량 |
| `weekend_days` | 월별 주말 수 |
| `public_holiday_count_kr_approx` | 월별 한국 공휴일 수 근사 |
| `is_summer_peak_jun_aug` | 6~8월 여름 성수기 더미 |
| `is_kbo_regular_season` | KBO 정규시즌 더미 |

---

## 8. 수요예측 모델 활용 방안

### 8.1 권장 모델 구조

본 데이터셋은 다음 세 가지 방향으로 활용할 수 있다.

1. **시장 전체 수요예측 모델**
   - y: `alcoholic_beer_total_proxy_kl`
   - X: 날씨, 공휴일, 검색량, 수입맥주량, KBO 시즌
   - 목적: 전체 맥주 시장 수요 예측

2. **세그먼트별 다중 타깃 모델**
   - y1: `regular_beer_excluding_low_calorie_proxy_kl`
   - y2: `low_calorie_light_beer_proxy_kl`
   - y3: `nonalcoholic_beer_proxy_kl`
   - 목적: 일반 맥주/저칼로리/논알콜 수요의 구조적 변화 포착

3. **Cass 제품군 생산계획 시나리오 모델**
   - y1: `cass_fresh_proxy_kl`
   - y2: `cass_light_proxy_kl`
   - y3: `cass_0_0_or_all_zero_proxy_kl`
   - 목적: 병목 설비 및 생산 믹스 최적화 입력값 생성

### 8.2 추천 모델

| 모델 | 사용 목적 | 장점 |
|---|---|---|
| Seasonal Naive | 기준선 모델 | 발표에서 성능 비교 기준으로 적합 |
| SARIMAX | 월별 시계열 + 외생변수 | 계절성과 외생변수 해석 가능 |
| Prophet | 빠른 데모 | 추세/계절성/휴일 효과 시각화 용이 |
| LightGBM/XGBoost | 다변량 비선형 예측 | 날씨, 검색량, 이벤트 효과 반영에 유리 |

프로젝트 발표에서는 Seasonal Naive와 LightGBM 또는 SARIMAX를 비교하는 방식이 가장 설득력 있다. 단순 시계열 기준선 대비 검색량·날씨·공휴일을 넣었을 때 오차가 줄어드는지를 보여주면 AI 수요예측의 운영적 가치를 설명하기 좋다.

---

## 9. 한계 및 주의사항

1. **Cass SKU별 실제 월별 판매량은 공개자료가 아니다.**
   - 본 데이터셋의 Cass Fresh, Cass Light, Cass 0.0 값은 실제 내부 판매량이 아니라 proxy다.

2. **가정시장 점유율과 전체 시장 출고량의 기준이 다르다.**
   - Cass Fresh/Light 점유율은 주로 가정시장(off-trade) 기준이다.
   - 전체 맥주 출고량은 국내분 출고량 또는 apparent market 기준이다.
   - 따라서 제품별 프록시는 정확한 출하량이 아니라 생산계획 시나리오 입력값으로 사용해야 한다.

3. **논알콜/무알콜 맥주는 시장 정의가 다를 수 있다.**
   - `무알코올`, `비알코올`, `논알코올` 제품은 법적·시장조사상 분류가 다를 수 있다.
   - Cass 0.0은 정확한 시장점유율이 공개되지 않았다.

4. **Google Trends는 절대 수요가 아니라 상대 관심도다.**
   - 검색량은 수요의 원인이 아니라 수요와 동행하거나 선행할 수 있는 proxy다.
   - 모델 해석 시 “검색 관심도 기반 프록시”라고 표현해야 한다.

5. **2025년 데이터는 provisional generated 값이다.**
   - 2025년 공식 국세청 출고량이 아직 없으므로, 수입맥주 및 검색량 YoY를 반영해 생성했다.
   - 발표에서는 2025년을 검증용이 아니라 예측/시나리오 구간으로 두는 것이 안전하다.

---

## 10. 보고서/발표용 권장 문구

> Cass 제품군의 실제 SKU별 월별 판매량은 공개되어 있지 않다. 따라서 본 프로젝트는 공식 연간 맥주 출고량, HS2203 월별 맥주 수입·수출, Google Trends 검색 관심도, 날씨 및 공휴일 변수를 결합하여 월별 수요 proxy를 생성하였다. 또한 공개된 Cass Fresh 및 Cass Light 가정시장 점유율과 무·비알코올 맥주 시장 성장 자료를 활용해 일반 맥주, 저칼로리 맥주, 논알콜 맥주 세그먼트를 분리하였다. 본 데이터는 실제 내부 판매량이 아니라, AI 수요예측과 생산운영 최적화 가능성을 검증하기 위한 모델링용 프록시 데이터셋이다.

---

## 11. 결론

본 데이터 수집의 가장 큰 성과는 공개자료만으로는 Cass 제품별 실제 월별 판매량을 얻을 수 없다는 한계를 명확히 확인하고, 그 한계를 우회할 수 있는 월별 모델링 데이터셋을 구축했다는 점이다. 특히 전체 맥주 시장은 공식 연간 통계에 고정하고, 월별 계절성은 실제 월별 수입통계와 검색 관심도로 분해했기 때문에 단순 임의 생성보다 근거가 강하다.

최종 데이터셋은 일반 맥주, 저칼로리/라이트 맥주, 논알콜/무알콜 맥주를 월별로 분리하고, Cass Fresh, Cass Light, Cass 0.0/All Zero의 제품군별 proxy까지 포함한다. 따라서 IMEN343 프로젝트에서 AI 수요예측 모델을 실제로 구현하고, 그 결과를 생산 믹스·병목 공정·재고계획 논의로 연결하기에 충분한 입력 데이터로 사용할 수 있다.

---

## Appendix A. 주요 출처

- e-나라지표/국세청, 주류 출고량 현황: https://www.index.go.kr/unity/potal/main/EachDtlPageDetail.do?idx_cd=2824
- UN Comtrade API, HS2203 Beer made from malt: https://comtradeapi.un.org/
- USDA/FAS, South Korea Beer Market Report KS2024-0035: https://www.fas.usda.gov/data/gain/2025/01/south-korea-south-korea-beer-market-report
- aT/FIS 식품산업통계정보, 2021 맥주 마켓리포트: https://www.atfis.or.kr/
- Google Trends: https://trends.google.com/trends/
- Open-Meteo Archive API: https://open-meteo.com/
- BusinessKorea, Cass brand value and market share article: https://www.businesskorea.co.kr/news/articleView.html?idxno=249887
- NewsSpace, OB맥주 2024 실적 보도: https://www.newsspace.kr/news/article.html?no=6448
