# Cass 수요예측 — 데이터 수집 PRD

**버전:** 1.0 | **기준 문서:** Cass 수요예측 데이터 및 AI 모델 방법론 (v2) | **작성일:** 2026-06-03

---

## 1. Overview

### 1.1 목적

Chronos-2 기반 zero-shot 수요예측 모델의 입력 데이터를 수집·정제하여 분석 가능한 월별 CSV로 산출한다. 예측 정확도 주장은 **Layer A(실측)**에서만 하고, 브랜드 분해와 비알콜 레이어는 앵커·시나리오로 처리한다.

### 1.2 수집 범위

| 항목 | 내용 |
|------|------|
| 기간 | 2020-01 ~ 2025-12 (72개월) |
| 단위 | 월별 (일부 분기·연간 → 월별 보간) |
| 최종 산출 | `cass_demand_v3_monthly.csv` |
| 부속 파일 | `cass_demand_v3_dictionary.csv`, `cass_demand_v3_validation.csv` |

### 1.3 데이터 계층 요약

| 계층 | 대상 | 성격 | 모델 역할 |
|------|------|------|-----------|
| **Layer A** | 전체 알코올 맥주 내수량 | 실측 | 예측 타깃 (정확도 백본) |
| **Layer B** | Cass Fresh / Cass Light 점유율 | 실측 앵커 | Layer A → 브랜드 분해 |
| **Layer C** | Cass 0.0 비알콜 시장 | 시나리오 앵커 | 별도 성장 레이어 |
| **Covariate** | 날씨·이벤트·가격 (10~15개) | 실측 / known-future | 예측 외생변수 |

---

## 2. Layer A — KOSIS 맥주 내수량 (정확도 백본)

### 2.1 소스

- **기관:** 통계청 KOSIS
- **조사명:** 광업·제조업동향조사 「품목별 광공업 생산·출하·재고·내수·수출량」
- **통계표 ID:** `DT_1F01012`
- **접근 경로:** https://kosis.kr → 통계표검색 → `DT_1F01012`

### 2.2 수집 항목

| 컬럼명 (CSV) | KOSIS 항목 | 단위 | 필수 |
|-------------|-----------|------|------|
| `beer_domestic_volume` | 맥주 **내수량** | kL 또는 톤 | 필수 |
| `beer_export_volume` | 맥주 수출량 | kL 또는 톤 | 내수량 직접 필드 없을 때 fallback |
| `beer_shipment_volume` | 맥주 출하량 | kL 또는 톤 | 내수량 직접 필드 없을 때 fallback |
| `beer_value` | 맥주 출하액 (또는 생산액) | 백만원 | 필수 (value↔volume 가교) |

> **내수량 fallback:** `DT_1F01012`에 내수량 직접 필드가 없으면 `beer_domestic_volume = beer_shipment_volume − beer_export_volume` 으로 계산. 수출량은 관세청 HS Code 2203(맥주)로 보완 가능.

### 2.3 수집 방법

**방법 1 — KOSIS OpenAPI (권장)**
```
엔드포인트: https://kosis.kr/openapi/statisticsData.do
파라미터:
  method=getList
  apiKey=<발급 키>
  itmId=T20+T21+T22+T23   (생산/출하/내수/수출 항목 코드, 실제 코드 확인 필요)
  objL1=맥주 품목코드
  format=json
  startPrdDe=202001
  endPrdDe=202512
```
- API 키 발급: https://kosis.kr/openapi (회원가입 후 즉시 발급)

**방법 2 — 웹 수동 다운로드**
1. https://kosis.kr → 국내통계 → 광업·제조업동향조사 → `DT_1F01012`
2. 조회 조건: 품목 = 맥주, 항목 = 생산량/출하량/내수량/수출량/출하액, 기간 2020.01 ~ 2025.12
3. 다운로드: Excel → CSV 변환

### 2.4 단위 확인 사항

- 단위가 **kL인지 톤인지** 반드시 확인하고 `beer_domestic_volume_unit` 컬럼에 기록
- 연도별 집계 방식 변경 여부 확인 (2020~2025 기간 내)

### 2.5 검증 기준

| 검증 항목 | 기준 |
|-----------|------|
| 행 수 | 72개 (2020-01 ~ 2025-12) |
| 결측 허용 | 0개 (결측 시 선형 보간 후 플래그) |
| 계절 패턴 | 7~8월 피크, 12~2월 저점 확인 |
| 연간 합계 | KOSIS 연보(연간 집계)와 월별 합산 오차 ≤ 1% |
| YoY 변동 | 단일 월 ±30% 초과 시 이상치 플래그 |

---

## 3. Layer B — aT FIS POS 브랜드 점유율

### 3.1 소스

- **기관:** aT 한국농수산식품유통공사 FIS 식품산업통계정보
- **데이터:** 소매점유통POS데이터 (닐슨IQ 기반)
- **접근 경로:** https://www.atfis.or.kr → 식품시장 → 소매점유통POS

### 3.2 수집 항목

| 컬럼명 (CSV) | 내용 | 단위 | 주기 |
|-------------|------|------|------|
| `cass_fresh_pos_sales` | 카스 후레쉬 POS 매출액 | 백만원 | 분기 |
| `cass_light_pos_sales` | 카스 라이트 POS 매출액 | 백만원 | 분기 |
| `total_beer_pos_sales` | 전체 맥주(주세법) POS 매출액 | 백만원 | 분기 |
| `cass_fresh_share` | 카스 후레쉬 점유율 | % | 분기 → 월 보간 |
| `cass_light_share` | 카스 라이트 점유율 | % | 분기 → 월 보간 |

> **중요:** aT FIS POS에서 "카스 후레쉬"와 "카스 라이트"가 **브랜드 단위로 분리**되어 제공되는지 반드시 확인. 만약 브랜드 분리가 없고 "오비맥주" 제조사 단위만 제공된다면 §3.4 fallback 적용.

### 3.3 수집 방법

**방법 1 — 보고서 직접 다운로드**
1. https://www.atfis.or.kr → 식품시장 → 가공식품 세분시장 현황 → 맥주
2. 연도별 맥주 시장 보고서 (2020~2025) 다운로드
3. 브랜드별 점유율 표에서 카스 후레쉬·카스 라이트 항목 추출

**방법 2 — 식품시장 뉴스레터**
- 분기별 맥주 뉴스레터 → 브랜드 점유율 수치 수집

### 3.4 Fallback (브랜드 분리 불가 시)

브랜드 단위 분리가 공개되지 않는 경우:
- `ob_beer_share`: 오비맥주 전체 맥주 점유율 (Layer A 기준)
- `cass_within_ob_ratio`: Cass 계열의 OB 내 비율 (업계 보고서·언론 기반 추정, 시나리오 처리)
- `cass_fresh_share = ob_beer_share × cass_within_ob_ratio × fresh_within_cass_ratio` (모두 가정 명시)

### 3.5 월별 보간

분기 점유율 → 월별 변환: **선형 보간** (분기 말 값을 3개월에 균등 배분)

```python
# 보간 예시
quarterly_share.resample('MS').interpolate(method='linear')
```

### 3.6 Value → Volume 근사

- **전제:** Cass Fresh와 Cass Light는 가격대가 유사한 주류 라거 → `value 점유율 ≈ volume 점유율`
- **검증:** KOSIS `beer_value` / `beer_domestic_volume` 으로 전체 맥주 내재 단가 계산 → Fresh/Light 가격 차이가 ≤ 10% 이면 근사 유효
- **결과 컬럼:** `cass_fresh_volume = beer_domestic_volume × cass_fresh_share`, `cass_light_volume = beer_domestic_volume × cass_light_share`

### 3.7 검증 기준

| 검증 항목 | 기준 |
|-----------|------|
| 분기 데이터 | 20개 포인트 (2020 Q1 ~ 2025 Q4) |
| 월별 보간 후 | 72개 행 |
| `cass_fresh_share + cass_light_share` | ≤ `ob_beer_share` |
| 점유율 변동 | QoQ ±5%p 초과 시 플래그 |

---

## 4. Layer C — 비알콜 맥주 시장 규모 (시나리오)

### 4.1 소스 및 수집 항목

| 항목 | 수치 | 출처 | 성격 |
|------|------|------|------|
| 국내 비알콜 맥주 시장 규모 2023 | 약 590억원 | aT FIS 또는 언론 보도 | 앵커 (연간) |
| 국내 비알콜 맥주 시장 규모 2025E | 2,000억원 이상 전망 | 주류면허법 시행령 입법예고 관련 보도 | 전망치 |
| 글로벌 비알콜 맥주 시장 CAGR | ~5.6% (2022~) | 글로벌 시장조사 보고서 | 참고 |
| Cass 0.0 시장점유율 | **시나리오 입력** (예: 10~20%) | 가정 | 시나리오 |

> **출처 보강 필요:** 590억 수치의 원 출처(기사명·발행일)를 `cass_demand_v3_dictionary.csv`에 반드시 기록. 가능하면 aT FIS 비알콜 음료 시장 보고서 또는 한국주류산업협회 공표치로 교체.

### 4.2 처리 방법

```
비알콜 시장 규모(VALUE, 연간) → 월별 선형 배분 → `nonalc_market_value`
비알콜 평균 단가(가정) → volume 환산 → `nonalc_market_volume`
Cass 0.0 점유율 시나리오 × `nonalc_market_volume` → `cass_0_0_scn`
```

### 4.3 시나리오 설정

| 시나리오 | Cass 0.0 점유율 | 근거 |
|---------|-----------------|------|
| Base | 15% | 업계 추정 중간값 |
| Low | 10% | 보수적 |
| High | 25% | 공격적 (시장 선도 가정) |

### 4.4 검증 기준

- 연간 시장 규모의 합리적 범위: 2020년 100억 미만 ~ 2025년 2,000억 내외
- 성장률이 연 50% 초과면 가정 재검토

---

## 5. Covariates (외생변수, 10~15개)

### 5.1 변수 목록 및 수집 명세

#### 5.1.1 날씨·환경 (known-future = 평년/KMA 전망)

| 컬럼명 | 변수 | 소스 | 접근 방법 | 주기 | 단위 |
|--------|------|------|-----------|------|------|
| `temp_avg` | 월평균기온 | 기상청 기상자료개방포털 | ASOS API | 월별 | °C |
| `heatwave_days` | 폭염일수 (일 최고기온 ≥ 33°C) | 기상청 기상자료개방포털 | ASOS API | 월별 | 일수 |
| `tropical_night_days` | 열대야일수 (일 최저기온 ≥ 25°C) | 기상청 기상자료개방포털 | ASOS API | 월별 | 일수 |

**기상청 ASOS API 접근:**
```
엔드포인트: https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList
파라미터:
  serviceKey=<공공데이터포털 API 키>
  pageNo=1&numOfRows=999
  dataType=JSON
  dataCd=ASOS
  dateCd=DAY
  startDt=20200101
  endDt=20251231
  stnIds=108   (서울 기상관측소)
```
- API 키 발급: https://www.data.go.kr → 한국기상데이터포털 → ASOS

#### 5.1.2 이벤트·캘린더 (known-future)

| 컬럼명 | 변수 | 소스 | 접근 방법 | 주기 |
|--------|------|------|-----------|------|
| `kbo_games` | KBO 월별 경기수 | KBO 공식 홈페이지 | 수동 (연도별 일정표) | 월별 |
| `world_cup_dummy` | 피파 월드컵 개최 더미 | FIFA 공식 일정 | 수동 | 월별 (0/1) |
| `holiday_days` | 공휴일·연휴 일수 | 공공데이터포털 (한국천문연구원) | API | 월별 |
| `festival_dummy` | 대형 페스티벌 더미 (선택) | 문화체육관광부 | 수동 | 월별 (0/1) |

**공휴일 API:**
```
엔드포인트: https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getHoliDeInfo
파라미터:
  serviceKey=<API 키>
  solYear=2020 ~ 2025
  solMonth=01 ~ 12
  _type=json
```

**KBO 수동 수집:**
- https://www.koreabaseball.com/Schedule/Schedule.aspx
- 연도별 월별 정규시즌 경기 수 집계 (2020년 코로나 감소 반영)

#### 5.1.3 가격·경제

| 컬럼명 | 변수 | 소스 | 접근 방법 | 주기 | 비고 |
|--------|------|------|-----------|------|------|
| `import_beer_price_yoy` | 수입맥주 평균 단가 YoY 변화율 | 관세청 수출입무역통계 | OpenAPI | 월별 | HS 2203 |
| `ob_price_hike_dummy` | OB맥주 출고가 인상 더미 | 언론 보도 수동 | 수동 | 월별 (0/1) | 2024-04, 2025-04 인상 |

**관세청 수출입무역통계 API:**
```
엔드포인트: https://unipass.customs.go.kr:38010/ext/rest/imprtStatJsxmlService/retrieveImprtStatJsxml
파라미터:
  crkyCd=<발급 키>
  hsSgn=2203   (맥주)
  statDt=202001 ~ 202512
```
- API 키: https://unipass.customs.go.kr → 오픈API 서비스

#### 5.1.4 제외 변수

| 변수 | 제외 이유 |
|------|-----------|
| Google Trends (맥주 검색량) | known-past, 타깃 생성과 분리됐어도 과적합 위험, 약한 covariate |
| 뉴스 감성 점수 | known-past, 방법론 v2에서 명시적 제외 |
| 실현 기온 (미래 월) | 예측 시점에 알 수 없음 → 평년값으로 대체 (known-future 근사) |

### 5.2 Known-future 처리 원칙

| 구분 | 정의 | 처리 |
|------|------|------|
| **Known-future** | 예측 시점에 미래값을 알 수 있는 변수 | 직접 covariate 투입 |
| **Known-past (lag)** | 미래값을 모르는 변수 | t-1 lag 또는 제외 |

- 미래 월 기온: **평년값** 또는 KMA 1개월 전망 근사 → 불확실성 명시
- 달력 변수 (공휴일·KBO·월드컵): 완전히 known-future

---

## 6. 최종 산출 파일 스키마

### 6.1 `cass_demand_v3_monthly.csv`

| 컬럼명 | 타입 | 단위 | 계층 | 성격 |
|--------|------|------|------|------|
| `month` | str (YYYY-MM) | — | key | — |
| `beer_domestic_volume` | float | kL (또는 톤) | A | 실측 |
| `beer_value` | float | 백만원 | A | 실측 |
| `cass_fresh_share` | float | % (0~100) | B | 실측 앵커 |
| `cass_light_share` | float | % (0~100) | B | 실측 앵커 |
| `cass_fresh_volume` | float | kL | A×B | 파생 |
| `cass_light_volume` | float | kL | A×B | 파생 |
| `nonalc_market_value` | float | 억원 | C | 앵커 |
| `cass_0_0_scn_base` | float | kL-equiv | C | 시나리오 |
| `cass_0_0_scn_low` | float | kL-equiv | C | 시나리오 |
| `cass_0_0_scn_high` | float | kL-equiv | C | 시나리오 |
| `temp_avg` | float | °C | covariate | known-future |
| `heatwave_days` | int | 일수 | covariate | known-future |
| `tropical_night_days` | int | 일수 | covariate | known-future |
| `kbo_games` | int | 경기수 | covariate | known-future |
| `world_cup_dummy` | int | 0/1 | covariate | known-future |
| `holiday_days` | int | 일수 | covariate | known-future |
| `import_beer_price_yoy` | float | % | covariate | lag |
| `ob_price_hike_dummy` | int | 0/1 | covariate | known-future |

### 6.2 `cass_demand_v3_dictionary.csv`

| 컬럼 | 내용 |
|------|------|
| `column_name` | CSV 컬럼명 |
| `layer` | A / B / C / covariate |
| `source` | 데이터 출처 (기관명 + URL) |
| `unit` | 단위 |
| `frequency` | 원본 주기 (월/분기/연간) |
| `availability` | known-future / known-past / lag |
| `assumption` | 가정 사항 (없으면 "실측") |
| `notes` | 기타 주의사항 |

### 6.3 `cass_demand_v3_validation.csv`

| 컬럼 | 내용 |
|------|------|
| `check_item` | 검증 항목명 |
| `layer` | 해당 계층 |
| `expected` | 기대값 / 기준 |
| `actual` | 실제 결과 |
| `status` | PASS / FAIL / FLAG |
| `notes` | 비고 |

---

## 7. 수집 워크플로우 & 타임라인

### 7.1 단계별 작업

```
Step 1 [0.5일]  KOSIS API 키 발급 + DT_1F01012 맥주 내수량·출하액 수집 (Layer A)
Step 2 [0.5일]  기상청 ASOS API 키 발급 + 기온·폭염·열대야 수집 (Covariate 날씨)
Step 3 [0.5일]  공공데이터포털 API 키 발급 + 공휴일 수집 (Covariate 캘린더)
Step 4 [0.5일]  관세청 API + 수입맥주 단가 수집 (Covariate 가격)
Step 5 [1일]    aT FIS POS 브랜드 점유율 수집 (Layer B) + 월별 보간
Step 6 [0.5일]  비알콜 시장 규모 수집 + 시나리오 설정 (Layer C)
Step 7 [0.5일]  KBO 경기수·OB 가격인상 더미 수동 수집 (Covariate)
Step 8 [1일]    통합 CSV 조립 + value↔volume 가교 검증 + validation 체크
```

**총 예상 소요:** 약 5일 (API 발급 대기 포함)

### 7.2 의존성

```
Step 1 완료 → Step 8 가능 (Layer A가 백본)
Step 5 완료 → Step 8 가능 (Layer B 점유율 필요)
Step 2~4, 6~7은 Step 8 전에만 완료하면 됨 (병렬 가능)
```

---

## 8. 데이터 품질 기준

### 8.1 결측값 처리

| 계층 | 허용 결측 | 처리 방법 |
|------|-----------|-----------|
| Layer A (백본) | 0개 | 인접 월 선형 보간 후 `_imputed` 플래그 컬럼 추가 |
| Layer B (점유율) | 분기 내 결측 허용 | 분기 평균으로 채움 |
| Layer C (비알콜) | 연간 데이터이므로 월 결측 정상 | 선형 배분 |
| Covariate | 1개월 이하 허용 | 선형 보간 후 플래그 |

### 8.2 이상치 탐지

```python
# Layer A: YoY 변동 ±30% 초과 → 플래그
flag = abs(beer_domestic_volume.pct_change(12)) > 0.30

# Layer B: 점유율 합계가 100% 초과 → 오류
assert (cass_fresh_share + cass_light_share).max() <= 100

# Covariate: 기온 -20°C 미만 or 40°C 초과 → 이상치 의심
flag_temp = (temp_avg < -20) | (temp_avg > 40)
```

### 8.3 레이어별 최종 검증 쿼리

```sql
-- V1: Layer A 행 수 확인
SELECT COUNT(*) FROM data WHERE month BETWEEN '2020-01' AND '2025-12';
-- 기대값: 72

-- V2: Layer A 계절 패턴 (7월 > 1월)
SELECT AVG(beer_domestic_volume) FROM data WHERE MONTH(month) = 7
  > SELECT AVG(beer_domestic_volume) FROM data WHERE MONTH(month) = 1;

-- V3: Layer B 점유율 합계
SELECT MAX(cass_fresh_share + cass_light_share) FROM data;
-- 기대값: ≤ OB 전체 점유율

-- V4: value↔volume 단가 일관성
SELECT beer_value / beer_domestic_volume AS implied_price FROM data;
-- 이상치: 전 기간 평균 대비 ±50% 초과 월 확인
```

---

## 9. API 키 발급 체크리스트

| 서비스 | 발급처 | 예상 소요 | 비고 |
|--------|--------|-----------|------|
| KOSIS OpenAPI | https://kosis.kr/openapi | 즉시 | 회원가입 필요 |
| 기상청 ASOS | https://www.data.go.kr | 1~2일 (자동 승인) | 공공데이터포털 통합 키 |
| 공공데이터포털 (공휴일) | https://www.data.go.kr | 1~2일 | 동일 키로 다중 API 가능 |
| 관세청 수출입무역통계 | https://unipass.customs.go.kr | 1~3일 | 별도 신청 |

---

## 10. 한계 및 리스크

| 항목 | 리스크 | 대응 |
|------|--------|------|
| Layer A 내수량 필드 미존재 | KOSIS에서 내수량 직접 필드가 없을 수 있음 | 출하량 − 수출량으로 계산, 수출량은 관세청 보완 |
| Layer B 브랜드 분리 미공개 | aT FIS에서 Fresh/Light 분리 점유율이 미공개일 수 있음 | §3.4 fallback 적용, 가정 명시 |
| Layer C 앵커 출처 신뢰성 | 590억 수치가 언론 보도 기반 | 원 기사 출처 각주 필수, 공신력 기관 자료로 교체 시도 |
| 미래 기온 covariate | 예측 시점에 실현값 모름 | 평년값 사용, 불확실성 §6.2에 명시 |
| 짧은 표본 (72개월) | Chronos-2 covariate 효과가 event 월 한정일 수 있음 | 방법론 §8.4 정직한 기대치 유지 |

---

## 11. 참고 링크

| 소스 | URL |
|------|-----|
| KOSIS 통계표 DT_1F01012 | https://kosis.kr |
| KOSIS OpenAPI 가이드 | https://kosis.kr/openapi |
| aT FIS 식품산업통계정보 | https://www.atfis.or.kr |
| 기상청 기상자료개방포털 | https://data.kma.go.kr |
| 공공데이터포털 | https://www.data.go.kr |
| 관세청 수출입무역통계 | https://unipass.customs.go.kr |
| KBO 공식 홈페이지 | https://www.koreabaseball.com |
| Chronos-2 GitHub | https://github.com/amazon-science/chronos-forecasting |
