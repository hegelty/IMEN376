# 월별 맥주/저칼로리/논알콜 수요 프록시 데이터 생성 방법

작성일: 2026-05-28  
파일: `data/monthly_beer_segment_demand_proxy_2020_2025.csv`

## 왜 생성 데이터가 필요한가

공개자료를 추가로 확인해도 **Cass Fresh / Cass Light / Cass 0.0의 월별 실제 판매량·출고량은 공개되어 있지 않다.** 국세청/e-나라지표는 연간 주종별 출고량이고, 닐슨코리아 수치는 기사에서 일부 반기/분기 점유율만 인용된다. 따라서 월별 예측 모델을 만들려면 다음처럼 **공식 연간 anchor + 실제 월별 proxy + 시장점유율 가정**으로 데이터를 생성해야 한다.

## 실제로 확보한 월별 원자료

| 원자료 | 파일 | 성격 |
|---|---|---|
| UN Comtrade HS2203 한국 월별 맥주 수입/수출 | `data/monthly_hs2203_comtrade_korea_2020_2025.csv` | 실제 월별 중량/금액. 수입맥주 경쟁·계절성 proxy |
| Google Trends 맥주/무알콜/논알콜 | `data/monthly_google_trends_beer_segments_2020_2026.csv` | 실제 검색 관심도 월별 index |
| Google Trends 카스/카스 라이트/카스 제로 | `data/monthly_google_trends_cass_products_2020_2026.csv` | 실제 브랜드 검색 관심도 월별 index |
| 서울 월별 날씨 | `data/monthly_weather_seoul_open_meteo_2020_2025.csv` | 평균기온, 최고기온, 강수량, 30℃ 이상 일수, 강수일수 |

최종 모델 입력용 파일은 위 자료를 합친 `data/monthly_beer_segment_modeling_dataset_2020_2025.csv`이다.

## 생성 산식

### 1. 전체 알코올 맥주 월별 수요

연간 anchor는 `beer_market_timeseries_1994_2024.csv`의 apparent market이다.

```text
연간 맥주 시장(kL) = 국내 맥주 출고량 + HS2203 수입량 - HS2203 수출량
월별 weight = normalize(0.45 × 월별 HS2203 수입량 + 0.55 × Google Trends '맥주')
월별 알코올 맥주 수요 proxy = 연간 맥주 시장 × 월별 weight
```

2025년은 아직 공식 출고량이 없어서 2024년 대비 수입맥주와 검색량 YoY를 반영한 provisional estimate다.

### 2. 저칼로리/라이트 맥주

공개 anchor:
- Cass Light 2024H1 가정시장 점유율: **3.4%**
- Cass Light 2025Q2 가정시장 점유율: **4.9%**
- 2024년 이마트 light beer 매출 YoY **+32%**, 전체 맥주 매출 **-6.4%** 보도

생성 가정:
```text
연간 light/low-calorie share: 2020 2.4% → 2023 3.0% → 2024 3.6% → 2025 4.7%
월별 low-calorie 수요 = 연간 맥주 시장 × 연간 share × 월별 light weight
월별 light weight = Google Trends '카스 라이트' + 일반 맥주 계절성 blend
```

### 3. 논알콜/무알콜 맥주

공개 anchor:
- FIS: 무알콜 맥주 시장 2014년 81억 원 → 2019년 153억 원
- Euromonitor/보도: 2021년 415억 원, 2023년 644억 원, 2027년 1,000억 원 전망
- 2025H1 Hite Zero 0.00 판매액 점유율 37.5%; Cass 0.0 정확 점유율은 미공개

생성 가정:
```text
연간 non-alcoholic beer market value: 2020 280억 → 2021 415억 → 2023 644억 → 2024 700억 → 2025 800억 원
월별 value = 연간 value × normalize(Google Trends '무알콜 맥주' + '논알콜 맥주')
월별 volume proxy = 월별 value / 4.0백만원 per kL
```

가격 4.0백만원/kL은 1L당 4,000원으로 환산한 rough assumption이다. 실제 SKU/채널 가격에 따라 달라질 수 있다.

## 컬럼 해석

- `alcoholic_beer_total_proxy_kl`: 전체 알코올 맥주 월별 수요 proxy
- `regular_beer_excluding_low_calorie_proxy_kl`: 전체 알코올 맥주에서 low-calorie/light segment를 뺀 일반 맥주 proxy
- `low_calorie_light_beer_proxy_kl`: 저칼로리/라이트 맥주 proxy
- `nonalcoholic_beer_proxy_kl`: 논알콜/무알콜 맥주 volume proxy
- `cass_fresh_proxy_kl`, `cass_light_proxy_kl`, `cass_0_0_or_all_zero_proxy_kl`: Cass 제품군으로 내려가는 시나리오용 proxy. 실제 판매량 아님.
- `seoul_avg_temp_c`, `seoul_hot_days_30c`, `seoul_precipitation_mm`: 날씨 외생변수.
- `weekend_days`, `public_holiday_count_kr_approx`, `is_summer_peak_jun_aug`, `is_kbo_regular_season`: 캘린더/이벤트 외생변수.

## 보고서 표현 권장

> 월별 SKU 판매량은 공개되어 있지 않으므로, 본 모델은 공식 연간 출고량·수입통계와 월별 검색량을 이용해 월별 총수요를 분해하고, 공개 점유율 및 시장 성장률을 이용해 일반 맥주/저칼로리 맥주/논알콜 맥주 수요를 생성하였다. 생성값은 실제 내부 판매량이 아니라 AI 수요예측 기회와 생산계획 민감도 분석을 위한 proxy dataset이다.
