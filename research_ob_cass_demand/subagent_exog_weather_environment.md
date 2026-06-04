# IMEN343 OB Cass 수요예측: 날씨/환경 외생변수 수집 결과

작성: 2026-05-28  
산출 CSV: `data/exog_weather_environment_monthly.csv`  
재현 스크립트: `scripts/build_exog_weather_environment.py`

## 1. 산출물 요약

- 기간: **2020-01 ~ 2025-12**, 월별 72행
- 지역 기준: 서울 중심 좌표 `37.5665, 126.9780` 및 서울시 대기오염 측정소 `중구`
- 컬럼 수: 68개
- 결측값: 없음
- 실제/공개 데이터 우선 사용:
  - 날씨: Open-Meteo Historical Weather API의 서울 좌표 reanalysis/model archive
  - 대기질: 서울 열린데이터광장 `MonthlyAverageAirQuality` API의 `중구` 측정소 월평균값
- 생성/가공 변수:
  - 폭염일·열대야·한파일 등은 일별 기온 threshold로 파생
  - 월 sin/cos, 계절 dummy, 방학/연말 indicator는 모델링용 캘린더 파생변수

## 2. 사용 데이터 원천

### 2.1 날씨: Open-Meteo Historical Weather API

요청 구조:

```text
https://archive-api.open-meteo.com/v1/archive
latitude=37.5665&longitude=126.9780&timezone=Asia/Seoul
start_date=YYYY-01-01&end_date=YYYY-12-31
```

사용 변수:

- Daily: 평균/최고/최저기온, 평균/최고/최저 체감온도, 강수량, 비, 적설, 강수시간, 풍속/돌풍, 일사량, 일조/주간시간
- Hourly: 기온, 상대습도, 체감온도, 강수, 풍속

Open-Meteo 응답 격자: `lat=37.57469`, `lon=126.96`, `elevation=34m`, `timezone=Asia/Seoul`.

### 2.2 대기질: 서울 열린데이터광장 월별 평균 대기오염도

요청 구조:

```text
http://openapi.seoul.go.kr:8088/sample/json/MonthlyAverageAirQuality/1/5/YYYYMM/중구
```

사용 필드:

| API 필드 | CSV 컬럼 | 의미 |
|---|---|---|
| `NTDX` | `seoul_air_no2_ppm` | 이산화질소 NO2, ppm |
| `OZON` | `seoul_air_o3_ppm` | 오존 O3, ppm |
| `CBMX` | `seoul_air_co_ppm` | 일산화탄소 CO, ppm |
| `SPDX` | `seoul_air_so2_ppm` | 아황산가스 SO2, ppm |
| `PM` | `seoul_pm10_ug_m3` | 미세먼지 PM10, µg/m³ |
| `FPM` | `seoul_pm25_ug_m3` | 초미세먼지 PM2.5, µg/m³ |

주의: sample API는 한 번에 5건까지만 허용되어 전체 25개 구 평균 대신 `중구` 단일 측정소를 사용했다. 서울 도심 proxy로는 유용하지만, 전 서울 평균이나 소비자 거주권역별 노출값은 아니다.

## 3. 주요 변수와 모델링 의미

| 변수 그룹 | 대표 컬럼 | 수요예측 의미 |
|---|---|---|
| 기온 | `seoul_avg_temp_c`, `seoul_avg_max_temp_c`, `seoul_month_max_temp_c` | 맥주 소비의 핵심 계절/더위 수요 proxy |
| 체감온도 | `seoul_avg_apparent_temp_c`, `seoul_hourly_apparent_temp_p95_c` | 습도·풍속을 반영한 실제 더위 체감, 야외활동/음료 수요 proxy |
| 습도 | `seoul_relative_humidity_mean_pct` | 불쾌지수·체감온도 및 장마철 수요 변화 보완 |
| 강수 | `seoul_precipitation_mm`, `seoul_rain_days_1mm`, `seoul_heavy_rain_days_30mm` | 외출/야외 음주 감소, 배달/가정 채널 변화 가능성 |
| 폭염/열대야 | `seoul_hot_days_30c`, `seoul_heatwave_warning_days_33c`, `seoul_tropical_nights_25c` | 더위 이벤트성 수요 증가 및 냉장/생산계획 민감도 |
| 한파/동절기 | `seoul_freezing_days_min_lt0c`, `seoul_cold_wave_days_min_le_minus12c`, `seoul_heating_degree_days_18c` | 겨울철 맥주 수요 둔화 및 계절 재고계획 proxy |
| 풍속/돌풍 | `seoul_hourly_wind_speed_mean_kmh`, `seoul_wind_gust_max_kmh` | 야외활동/체감온도 보정용 보조변수 |
| 일사/일조 | `seoul_shortwave_radiation_mj_m2_sum`, `seoul_sunshine_hours_sum` | 맑은 날·야외활동·피크 시즌 보조 signal |
| 대기질 | `seoul_pm10_ug_m3`, `seoul_pm25_ug_m3`, `seoul_air_o3_ppm` | 고농도 미세먼지/오존 시 야외활동 위축 가능성 |
| 월/계절성 | `month_sin_annual`, `month_cos_annual`, `is_summer_jun_aug` 등 | 날씨 외 남는 반복 계절성 포착 |

## 4. 파생 규칙

- `seoul_hot_days_30c`: 일최고기온 ≥ 30°C인 일수
- `seoul_heatwave_warning_days_33c`: 일최고기온 ≥ 33°C인 일수. 기상청 공식 폭염특보 발령일이 아니라 threshold proxy
- `seoul_tropical_nights_25c`: 일최저기온 ≥ 25°C인 일수
- `seoul_cold_wave_days_min_le_minus12c`: 일최저기온 ≤ -12°C인 일수. 공식 한파특보 발령일이 아니라 threshold proxy
- `seoul_cooling_degree_days_18c`: Σ max(일평균기온 - 18, 0)
- `seoul_heating_degree_days_18c`: Σ max(18 - 일평균기온, 0)
- `seoul_pm10_month_avg_bad_flag_gt80`: 월평균 PM10 > 80µg/m³ flag
- `seoul_pm25_month_avg_bad_flag_gt35`: 월평균 PM2.5 > 35µg/m³ flag

## 5. Caveats

1. **Open-Meteo 날씨는 관측소 원자료가 아니라 격자형 reanalysis/model archive**다. 서울 ASOS 공식 관측값과 소폭 다를 수 있다.
2. **폭염/열대야/한파 변수는 공식 특보 이력 아님**. 수요모델 입력용 threshold count다.
3. **대기질은 `중구` 단일 측정소 월평균**이다. sample key 제약으로 전체 구 평균을 만들지 않았다. 발표/보고서에서는 “서울 도심 대기질 proxy”로 표현하는 것이 안전하다.
4. PM bad flag는 월평균 threshold 초과 여부이지, 나쁨 등급 일수(count)가 아니다.
5. 기상/대기 변수는 서로 강한 계절성과 상관관계가 있으므로, 모델링 시 VIF/regularization/feature selection을 권장한다.

## 6. 기존 데이터와의 관계

기존 `data/monthly_weather_seoul_open_meteo_2020_2025.csv`는 평균기온·평균최고기온·강수량·30°C 이상 일수·강수일수 중심이었다. 새 파일은 여기에 다음을 확장했다.

- 습도, 체감온도, 풍속/돌풍
- 폭염 33°C, 열대야 25°C, 한파 threshold, 냉방/난방도일
- 강수 강도 count, 일사/일조
- 서울시 공식 월평균 대기질 PM10/PM2.5/NO2/O3/CO/SO2
- 모델용 월/계절성 indicator
