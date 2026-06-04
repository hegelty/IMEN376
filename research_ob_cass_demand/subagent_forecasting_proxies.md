# OB Cass 수요예측 데모용 데이터/프록시 후보 조사

조사 시점: 2026-05-28 KST  
목표: **월별/연간 한국 맥주 수요 또는 Cass 수요의 대체지표**와 외생변수(검색 관심, 날씨, 이벤트, 가격)를 조합해 데모 수요예측 모델을 만들 수 있는 데이터 소스를 정리한다.

## 1. 결론 요약

- **브랜드별 Cass 실제 판매량 공개 데이터는 찾기 어렵다.** 데모에서는 `맥주 카테고리 수요`를 타깃으로 두고, Cass는 검색량/가격/브랜드 POS 순위 등으로 보강하는 방식이 현실적이다.
- 가장 실용적인 타깃 후보는 다음 순서:
  1. **aTFIS 소매 POS**: 월별, 품목/제조사/브랜드/유통채널 매출 프록시. 단, 사이트/다운로드 구조 확인 필요.
  2. **국세청/TASIS·절주온 주류 출고량**: 연간 맥주 출고량. 장기 추세 검증용.
  3. **관세청 수출입무역통계 HS 2203**: 월별 수입맥주 물량/금액. 국내 맥주 직접수요는 아니지만 경쟁·시장 분위기 프록시.
  4. **Google Trends / Naver DataLab**: `카스`, `카스 라이트`, `카스 0.0`, `카스 맥주`, `맥주` 검색 관심도. 브랜드별 월별 외생변수로 유용.
- 외생변수는 **ASOS 일/시간 기상자료**, **공휴일/특일**, **KBO 경기일정**, **지역축제**, **맥주 CPI/참가격** 조합이 좋다.

---

## 2. 수요 타깃/판매 프록시 데이터

| 후보 | URL | 접근 방식 | 변수/커버리지 | 장점 | caveat |
|---|---|---|---|---|---|
| **aTFIS 식품산업통계정보 - 소매 POS** | https://www.atfis.or.kr/ | 웹 조회/다운로드 가능 여부 확인 필요. 검색 결과상 `데이터설명 > 소매 POS > 시장분석` 메뉴 존재 | 국내 주요 가공식품의 품목별 소매점 POS. 제조사/브랜드/세분시장/유통채널, 월 업데이트. 검색 결과 기준 데이터 제공기관: 마켓링크(2020~2023), 업데이트 주기 월 | 월별 맥주 판매액·브랜드/제조사 지표를 얻을 수 있으면 데모 타깃으로 최상 | 사이트가 동적이고 일부 메뉴는 로그인/브라우저 확인 필요. 브랜드 Cass가 직접 노출되는지 확인 필요 |
| **주류산업정보 실태조사(aT/KREI 등)** | 검색 키워드: `2023 주류산업정보 실태조사`, `주류산업정보 실태조사 맥주 출고` | PDF/HWP 보고서 다운로드 후 표 추출 | 주류산업/생산/소비 현황, 주종별 출고량·출고금액. 2019/2020/2021/2023 보고서 검색 확인 | 주류 시장 설명·연간 값·모델 배경자료에 좋음 | 보고서형이라 자동화/월별 모델에는 약함. 국세청 통계와 집계 기준 차이 있음(과세+면세, 기준도수 환산 여부 등) |
| **TASIS 국세통계포털** | https://tasis.nts.go.kr/ | 웹 조회/엑셀 다운로드 가능성. 검색어: `주류 출고량`, `맥주 출고량` | 주세 신고 기반 주종별 출고량/세액, 보통 연간 | 공식성 높음. 장기 추세/검증용 | 동적 사이트라 자동 스크래핑 난이도 있음. 월별보다 연간 위주일 가능성 큼 |
| **절주온 - 주요 주류 출고현황** | https://www.khepi.or.kr/ 또는 검색: `총 주요 주류 출고현황 절주온`, `주요 주류 출고현황 국내분 절주온` | 웹 표 스크래핑 가능성. 네이버 검색 스니펫에서 2005년 이후 주종별 수치 확인 | 연도, 총 출고량, 탁주/약주/맥주/소주 등 주종별 출고량 | 공개 웹 표라 연간 맥주 수요 proxy로 빠르게 쓰기 좋음 | 직접 URL 접근 시 설정 오류가 나올 수 있어 브라우저/검색 경유 필요. 연간 단위 |
| **관세청 수출입무역통계 - 품목별 수출입실적(GW)** | https://www.data.go.kr/tcs/dss/selectDataSetList.do?keyword=수출입무역통계 / https://tradedata.go.kr/cts/index.do | 공공데이터포털 OpenAPI(XML), 관세청 포털 다운로드. HS `2203`(맥주) 조회 | 월/연도, HS code, 수출입 금액, 중량/수량, 국가별 가능 | 수입맥주 경쟁강도·시장 트렌드 프록시로 유용. 월별 가능 | 국내 Cass 수요가 아니라 경쟁/대체재 지표. API 활용신청 필요 가능 |
| **KITA 무역통계** | https://stat.kita.net/stat/kts/ctr/CtrTotalImpExpList.screen | 웹 조회/엑셀 다운로드 | 품목별/국가별 월별 수출입 | 관세청 API 대안 | 스크래핑 약관/자동화 제한 확인 필요 |
| **서울시 주류 섭취빈도율 통계** | 공공데이터포털 검색어: `서울특별시 주류 섭취빈도율 통계` | CSV 다운로드 | 지역/연도별 음주 빈도·행태 | 수요 자체보다 인구통계적 음주성향 보조변수 | 서울 한정, 연간/조사 기반, 브랜드/맥주 수요 직접값 아님 |

### 추천 타깃 구성

- **월별 모델 데모**: `aTFIS 소매 POS 맥주 카테고리 월별 매출액`을 y로 사용. 브랜드 Cass가 있으면 브랜드 매출/점유율까지 확장.
- **데이터 확보가 막히면**: `관세청 HS2203 월별 수입맥주 수입량/금액` + `Google/Naver 맥주·카스 검색량`으로 “맥주 시장 관심/경쟁 수요” 데모를 만들고, 연간 출고량으로 sanity check.
- **연간 설명 모델**: 절주온/TASIS 주류 출고량을 y로 두고, 연평균 기온/폭염일수/가격지수/인구/트렌드 평균을 외생변수로 사용.

---

## 3. 검색 관심도: Cass 브랜드 프록시

| 후보 | URL | 접근 방식 | 변수/커버리지 | caveat |
|---|---|---|---|---|
| **Google Trends** | https://trends.google.com/trends/ | 웹 CSV 다운로드 또는 `pytrends` 비공식 API (`pip install pytrends`) | KR 지역, 일/주/월별 상대 관심도(0~100). 쿼리: `카스`, `카스 맥주`, `카스 라이트`, `카스 0.0`, `Cass beer`, `맥주` | 비공식 API는 rate limit/백엔드 변경 위험. Google Trends 직접 접근은 429 가능. 5개 키워드 제한 및 상대척도 정규화 주의 |
| **pytrends** | https://pypi.org/project/pytrends/ / https://github.com/GeneralMills/pytrends | Python 비공식 API | interest_over_time, related_queries, interest_by_region | 유지보수/차단 이슈. 재현성을 위해 CSV 수동 다운로드도 보관 권장 |
| **Naver DataLab 검색어 트렌드** | 웹: https://datalab.naver.com/keyword/trendSearch.naver / API 문서: https://developers.naver.com/docs/serviceapi/datalab/search/search.md | 공식 API: `POST https://openapi.naver.com/v1/datalab/search`, Client ID/Secret 필요 | 2016년 1월 이후. 기간별/성별/연령별/PC·모바일 검색 비율. keywordGroups에 Cass 관련 묶음 설정 가능 | 절대 검색량 아님(상대 ratio). 네이버 개발자 앱 키 필요. 동의어/오타를 그룹화해야 안정적 |

### Naver DataLab 쿼리 설계 예시

- 그룹1 `카스`: `카스, 카스맥주, 카스 맥주, Cass, Cass beer`
- 그룹2 `카스 라이트`: `카스라이트, 카스 라이트, Cass Light`
- 그룹3 `카스 0.0`: `카스0.0, 카스 0.0, 카스제로, 카스 제로, Cass 0.0`
- 그룹4 `맥주 일반`: `맥주, 편의점 맥주, 생맥주`
- 모델 입력: 월별 평균 ratio, 전월 대비 변화율, 여름철 상호작용(`검색량 × 평균기온`) 등.

---

## 4. 날씨/계절 외생변수

| 후보 | URL | 접근 방식 | 변수/커버리지 | 추천 파생변수 | caveat |
|---|---|---|---|---|---|
| **기상청 ASOS 일자료 조회서비스** | https://www.data.go.kr/data/15059093/openapi.do | 공공데이터포털 REST API(JSON/XML), 활용신청 필요 | 전국 ASOS, 1904년 4월~현재(지점별 상이), 일 단위. 평균/최고/최저 기온, 강수량, 습도, 일조, 일사 등 | 월평균기온, 최고기온 평균, 폭염일수(최고≥30/33), 강수일수, 강수량 합계, 습도, 주말 고온일수 | 지역별 수요가 없으면 서울(108) 또는 전국 주요 도시 가중 평균 사용 |
| **기상청 ASOS 시간자료 조회서비스** | https://www.data.go.kr/data/15057210/openapi.do | REST API(JSON/XML) | 시간 단위 기온/강수/습도/풍속 등 | 야간 고온, 경기시간대 날씨, 주말 오후 기온 | 데이터량 큼. 월별 모델엔 일자료로 충분 |
| **기상자료개방포털 ASOS CSV** | https://data.kma.go.kr/data/grnd/selectAsosRltmList.do?pgmNo=36 | 웹 다운로드 CSV | ASOS 지점별 관측자료 | API 키 없이 수동 다운로드 가능성 | 대량 다운로드/자동화는 포털 정책 확인 |

---

## 5. 이벤트/캘린더 외생변수

| 후보 | URL | 접근 방식 | 변수/커버리지 | 추천 파생변수 | caveat |
|---|---|---|---|---|---|
| **한국천문연구원 특일 정보** | https://www.data.go.kr/data/15012690/openapi.do | REST API(XML), 활용신청 필요 | 국경일, 공휴일, 기념일, 24절기, 잡절. 연/월 기준 조회. `locdate`, `dateName`, `isHoliday` | 월별 공휴일 수, 연휴 길이, 설/추석 더미, 월드컵/올림픽 별도 더미와 조합 | API 기본 XML. 대체공휴일 반영 여부 확인 필요 |
| **KBO 경기일정** | https://www.koreabaseball.com/Schedule/Schedule.aspx | 웹 페이지/비공식 스크래핑 | 일자, 팀, 구장, 경기결과 | 월별 KBO 경기 수, 주말 경기 수, 홈경기 수, 야구 시즌 더미 | 공식 API는 명확하지 않음. 스크래핑 안정성/약관 확인 필요 |
| **문화체육관광부 지역축제 정보** | 공공데이터포털 검색어 `문화체육관광부_지역축제 정보` 또는 `전국 축제 행사` | XLSX 다운로드 | 축제명, 기간, 지역, 방문객/예산 등(데이터 설명상) | 월별 축제 수, 여름 축제 수, 지역별 축제 가중치 | 음주/맥주 수요와 직접 연결은 약함. 전국 aggregation 필요 |
| **대형 스포츠/국제 이벤트 수동 캘린더** | FIFA/AFC/올림픽/KBO 포스트시즌 등 | 직접 CSV 작성 권장 | 이벤트명, 시작/종료일, 한국 경기 여부, 밤 시간대 여부 | 월드컵/아시안컵/올림픽 더미, 한국 경기일 수 | 표본 수 적지만 Cass 광고/맥주 소비에는 중요할 수 있음 |

---

## 6. 가격/프로모션 외생변수

| 후보 | URL | 접근 방식 | 변수/커버리지 | 활용 | caveat |
|---|---|---|---|---|---|
| **KOSIS 소비자물가지수 - 맥주/주류** | https://kosis.kr/ / OpenAPI: https://kosis.kr/openapi/index/index.jsp | KOSIS 웹 다운로드 또는 OpenAPI(인증키 필요). 검색어: `품목별 소비자물가지수 맥주`, `주류 소비자물가지수` | 월별 CPI(2020=100), 품목별/지역별 가능 | 맥주 가격지수, 주류 물가지수, 실질 수요 보정 | KOSIS API key 필요. 정확한 표 ID는 KOSIS에서 조회 필요 |
| **한국소비자원 참가격 - 생필품 가격 정보** | 포털: https://www.price.go.kr/tprice/portal/main/main.do / API: https://www.data.go.kr/data/3043385/openapi.do | 공공데이터포털 OpenAPI(XML), 일부 CSV/JSON+XML 자동변환 파일도 있음 | 상품명, 조사일, 판매가격, 판매업소, 제조사, 세일 여부 등. 전국 주요 유통업체 실제 판매가격 평균 | 맥주/안주류가 포함되면 Cass 또는 경쟁제품 가격·할인 proxy | 주류 품목 포함 여부 확인 필요. API URL 문서와 실제 endpoint 동작 확인 필요. 트래픽 개발계정 2,000 |
| **온라인몰 가격 스크래핑(쿠팡/이마트몰/홈플러스 등)** | 각 쇼핑몰 검색 | 가능하지만 약관 확인 필수. 가능하면 수동 샘플링/CSV | Cass 355/500ml, Cass Light, Cass 0.0 가격, 할인, 재고 | 브랜드별 가격/프로모션에 가장 직접적 | 자동 스크래핑 법적·약관 리스크. 주류 온라인 판매 제한으로 일반 맥주는 데이터가 부족할 수 있음. 무알콜 Cass 0.0은 온라인 가격이 상대적으로 쉬움 |

---

## 7. 빠른 데모 파이프라인 제안

1. **월별 날짜 spine 생성**: 2016-01 이후 월 단위.
2. **타깃 y 선택**
   - 1순위: aTFIS POS `맥주 월별 매출액/판매액`.
   - 2순위: 관세청 HS2203 월별 `수입중량/수입금액`을 시장 proxy로 사용.
   - 3순위: 연간 출고량이면 연간 모델 또는 월별 분해(검색량·날씨 비중으로 temporal disaggregation) 데모.
3. **외생변수 결합**
   - 검색: Google/Naver `카스`, `카스 라이트`, `카스 0.0`, `맥주` 월별 ratio.
   - 날씨: ASOS 서울/전국 월평균기온, 폭염일수, 강수일수.
   - 캘린더: 공휴일 수, 연휴 더미, KBO 시즌/경기 수, 월드컵 등 이벤트 더미.
   - 가격: 맥주 CPI, 주류 CPI, 가능하면 참가격/수동 가격 샘플.
4. **모델**
   - baseline: seasonal naive / SARIMAX.
   - demo 모델: Prophet/LightGBM/XGBoost with lag features(`y_lag1`, `trend_lag1`, `temp`, `holiday_count`).
5. **주의**
   - 검색량은 수요의 원인이 아니라 관심도 proxy라 leakage/동시성 주의.
   - POS/출고/수입은 정의가 다르므로 한 그래프에 놓을 때 단위와 집계기준을 명확히 구분.
   - Cass 브랜드 실제 수요를 주장하지 말고 “Cass demand proxy / beer category demand proxy”라고 표현.

---

## 8. 우선 확인할 URL 체크리스트

- aTFIS 소매 POS: https://www.atfis.or.kr/  
  검색 키워드: `aTFIS 소매 POS 맥주 브랜드 매출`, `데이터설명 소매 POS 시장분석`
- 절주온 주류 출고현황: https://www.khepi.or.kr/  
  검색 키워드: `총 주요 주류 출고현황 절주온`, `주요 주류 출고현황 국내분 절주온`
- TASIS 국세통계포털: https://tasis.nts.go.kr/
- 관세청 수출입무역통계: https://tradedata.go.kr/cts/index.do
- 공공데이터포털 관세청 GW: https://www.data.go.kr/tcs/dss/selectDataSetList.do?keyword=수출입무역통계
- Naver DataLab: https://datalab.naver.com/keyword/trendSearch.naver
- Google Trends: https://trends.google.com/trends/
- ASOS 일자료 API: https://www.data.go.kr/data/15059093/openapi.do
- 특일 정보 API: https://www.data.go.kr/data/15012690/openapi.do
- 참가격 API: https://www.data.go.kr/data/3043385/openapi.do
