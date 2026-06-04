# IMEN343 OB맥주 Cass 수요예측 외생변수: 이벤트·캘린더 월별 데이터

## 산출물

- 월별 모델 입력 파일: `data/exog_events_calendar_monthly.csv`
- 행 범위: `2020-01` ~ `2025-12`, 총 72개월
- 보조/감사용 원천 및 파생 파일:
  - `sources/events/2020_festival.zip` ~ `sources/events/2025_festival.zip`
  - `sources/events/extracted/*.xlsx`
  - `sources/events/mcst_festival_parsed_detail_2020_2025.csv`
  - `sources/events/mcst_festival_monthly_counts_2020_2025.csv`
  - `sources/events/kbo_monthly_schedule_counts_2020_2025.json`
  - 생성 스크립트: `sources/events/build_exog_events_calendar.py`

## 사용한 공개 데이터/근거

1. **문화체육관광부 지역축제 자료**
   - 공공데이터포털 항목: `문화체육관광부_지역축제 정보_20250106`
   - 제공 URL: `https://www.mcst.go.kr/site/s_culture/festival/festivalList.jsp`
   - MCST 다운로드 엔드포인트에서 연도별 `YYYY_festival.zip`을 받아 XLSX를 파싱.
   - 2020~2021은 시도별 시트, 2022~2025는 세부현황/조사표 시트를 사용.
2. **KBO 공식 경기일정**
   - `https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList`
   - 월별 `seasonId`, `gameMonth`, `srIdList` POST 호출.
   - 정규시즌: `srIdList=0,9,6`, 포스트시즌: `srIdList=3,4,5,7`.
   - `gameId`가 있는 완료 경기만 집계해 정규시즌은 매년 720경기로 검증됨.
3. **한국 공휴일**
   - Python `holidays.KR(observed=True)` 규칙 사용.
   - 대체공휴일 포함. 법령/관보 원문 API가 아니라 패키지 규칙 기반이므로 최종 연구 제출 전 수작업 검토 권장.
4. **국제 스포츠 이벤트**
   - 월별 더미/일수는 공식 개최기간을 수동 규칙으로 입력.
   - Tokyo 2020 Olympics: 2021-07-23~2021-08-08
   - Beijing 2022 Winter Olympics: 2022-02-04~2022-02-20
   - FIFA World Cup Qatar 2022: 2022-11-20~2022-12-18
   - Hangzhou 2022 Asian Games: 2023-09-23~2023-10-08
   - Paris 2024 Olympics: 2024-07-26~2024-08-11

## CSV 변수 사전과 모델링 의미

| 변수 | 의미 | 수요예측에서의 해석 |
|---|---:|---|
| `month`, `year` | 월 키 | 다른 월별 수요/날씨/검색량 데이터와 조인 |
| `days_in_month` | 월 일수 | 월 총량 모델에서 노출일수 보정 |
| `weekend_days` | 토·일 수 | 맥주 소비가 주말/외식 수요에 민감할 때 사용 |
| `public_holiday_count_kr` | 월 내 한국 공휴일 날짜 수 | 명절/휴일 소비, 유통 휴무, 여행 수요 영향 |
| `public_holiday_weekday_count_kr` | 평일에 걸린 공휴일 수 | 주말과 중복되지 않는 실제 추가 휴무 효과 |
| `nonworking_days_weekend_or_holiday` | 주말 또는 공휴일인 날짜 수 | 월별 비근무일 총량 |
| `longest_consecutive_nonwork_days` | 월과 겹치는 최장 연속 비근무일 길이 | 설/추석/대체공휴일 등 장기 연휴 효과 |
| `long_weekend_3plus_days_in_month` | 3일 이상 연휴에 속하는 월 내 날짜 수 | 여행·모임형 수요 집중도 |
| `holiday_names_kr` | 해당 월 공휴일명 | 감사/해석용 텍스트 |
| `is_summer_peak_jun_aug` | 6~8월 더미 | 여름 성수기 맥주 수요 효과 |
| `is_vacation_peak_jul_aug` | 7~8월 더미 | 휴가철 중심 성수기 효과 |
| `kbo_regular_games` | KBO 정규시즌 월별 완료 경기 수 | 스포츠 관람/치맥/야식 수요 프록시 |
| `kbo_regular_game_days` | 정규시즌 경기가 열린 날짜 수 | 경기 수보다 날짜 노출이 중요할 때 사용 |
| `is_kbo_regular_season` | 정규시즌 경기 존재 월 더미 | 단순 시즌성 더미 |
| `kbo_postseason_games` | KBO 포스트시즌 경기 수 | 가을야구 집중 이벤트 효과 |
| `kbo_postseason_game_days` | 포스트시즌 경기일 수 | 포스트시즌 날짜 노출 |
| `is_kbo_postseason` | 포스트시즌 존재 월 더미 | 10~11월 이벤트 더미 |
| `sports_major_event_days` | 월 내 대형 국제 스포츠 이벤트 개최일 수 | 국가대표/국제대회 관람 수요 프록시 |
| `is_sports_major_event_month` | 대형 스포츠 이벤트 월 더미 | 일수 대신 단순 충격 더미 |
| `olympics_days` | 올림픽 개최일 수 | 올림픽 효과 분리 |
| `fifa_world_cup_days` | 월드컵 개최일 수 | 월드컵 효과 분리 |
| `asian_games_days` | 아시안게임 개최일 수 | 아시안게임 효과 분리 |
| `sports_major_event_names` | 해당 이벤트명 | 감사/해석용 텍스트 |
| `regional_festival_count_planned` | MCST 지역축제의 월별 이벤트-월 count | 야외활동/지역 관광/모임 수요 프록시 |
| `regional_festival_days_est` | 축제 개최일수 추정 합계 | 행사 지속기간 기반 강도 변수 |
| `regional_festival_offline_or_hybrid_count` | 취소·온라인 전용을 제외한 오프라인/혼합 추정 축제 count | 실제 현장 소비에 더 가까운 변수 |
| `regional_festival_offline_or_hybrid_days_est` | 오프라인/혼합 축제 일수 추정 합계 | 현장형 행사 강도 |
| `regional_festival_vague_date_count` | 날짜가 `9월 중`처럼 모호했던 축제 count | 축제 변수의 품질/불확실성 진단 |
| `beer_festival_count_keyword` | 축제명/내용에 맥주·비어·치맥 등 키워드가 있는 축제 count | 맥주 직접 관련 이벤트 효과 |
| `beer_festival_days_est_keyword` | 맥주 키워드 축제 일수 추정 합계 | 맥주 직접 이벤트 강도 |
| `beer_festival_offline_or_hybrid_count_keyword` | 오프라인/혼합으로 추정되는 맥주 키워드 축제 count | 실제 현장 소비 가능성이 높은 맥주 이벤트 |
| `events_data_source_note` | 데이터 출처 요약 | 재현성/감사용 |

## 수치화 규칙

### 공휴일/연휴

- 월 내 공식 공휴일 날짜를 count.
- 주말과 공휴일의 합집합으로 비근무일을 만들고, 월 경계 ±7일을 보며 최장 연속 비근무일을 계산.
- 예: 2025년 10월은 개천절, 추석, 대체휴일, 한글날이 이어져 `longest_consecutive_nonwork_days=7`.

### KBO

- KBO 공식 스케줄 AJAX 결과에서 `gameId`가 있는 행만 완료 경기로 집계.
- 이 방식으로 2020~2025 정규시즌 합계가 매년 720경기로 맞음.
- 우천취소/연기 placeholder 행은 제외.

### 지역축제

- 축제가 두 달에 걸치면 두 달 모두 count된다. 즉 연간 고유 축제 수가 아니라 **월별 이벤트 노출 수**이다.
- 정확한 시작/종료일이 있으면 실제 겹치는 일수로 `*_days_est`를 계산.
- `9월 중`, `10월`, `9월말~10월초`처럼 날짜가 모호하면 해당 월/월범위를 count하되, 일수는 월별 1 proxy day로 제한해 과대계상을 줄였다.
- 2020 자료의 `취소`, `미개최` 표기는 오프라인/혼합 변수에서 제외.
- `온라인`, `비대면`만 보이는 행은 오프라인/혼합 변수에서 제외. `현장 및 비대면 병행`, `혼합`, `대면`은 포함.
- 맥주축제 변수는 `맥주|비어|beer|치맥|수제맥주` 키워드 기반이다.

### 대형 스포츠 이벤트

- 한국 대표팀 경기일이 아니라 대회 전체 개최기간을 월별 일수로 나눴다.
- TV 관람·회식·야식 수요의 넓은 프록시로 쓰고, 더 정밀한 모델에서는 한국 경기일/시간대 별도 변수로 대체하는 것이 좋다.

## 주요 caveat

- **Cass 실제 판매량이 아니라 외생변수 파일**이다. 기존 수요 proxy CSV와 `month`로 조인해 사용한다.
- 축제 자료는 연도별 계획/현황 파일의 형식이 다르다. 특히 2025는 2025-03-21 기준 개최계획이라 실제 취소/변경이 반영되지 않을 수 있다.
- 2020~2021은 COVID-19 영향으로 취소·온라인 전환이 많다. `regional_festival_count_planned`보다 `regional_festival_offline_or_hybrid_count`를 함께 보는 것을 권장한다.
- 공휴일은 `holidays` 패키지 규칙 기반이므로 논문/보고서 최종판에서는 정부 캘린더와 표본 월 몇 개를 검산하는 것이 안전하다.
- 축제 키워드 분류는 보수적이다. `막걸리`, `와인`, `전통주` 등은 맥주축제 변수에는 넣지 않았다.

## 추천 사용 방식

- 기본 모델: `is_summer_peak_jun_aug`, `public_holiday_weekday_count_kr`, `longest_consecutive_nonwork_days`, `kbo_regular_games`, `regional_festival_offline_or_hybrid_count`.
- 이벤트 강화 모델: 위 변수에 `sports_major_event_days`, `beer_festival_offline_or_hybrid_count_keyword`, `kbo_postseason_games` 추가.
- 다중공선성 주의: `is_summer_peak_jun_aug`, 날씨의 고온일수, 축제 수, KBO 경기 수는 계절성이 겹칠 수 있으므로 정규화/변수선택/라쏘 또는 ablation 비교 권장.
