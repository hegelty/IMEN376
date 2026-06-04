# IMEN343 OB Cass 수요예측: 가격·경제 외생변수 보완 결과

산출 파일: `data/exog_economic_price_monthly.csv`

## 사용 자료와 변수

- `imported_beer_unit_value_usd_per_kg`: UN Comtrade HS2203 월별 수입액/수입중량. 수입맥주 단가와 프리미엄화/비용 압력 proxy.
- `imported_beer_unit_value_yoy_pct`: 수입맥주 단가 전년동월비.
- `monthly_google_trends_price_econ_2020_2026.csv`: Google Trends로 수집한 `물가`, `외식 물가`, `맥주 가격`, `주류 가격`, `소비심리` 검색 관심도.
- `price_pressure_search_index`: 가격 관련 검색 관심도 합계. 소비자 가격 민감도/물가 관심 proxy.
- `korea_cpi_generated_index_2020_01_100`: 한국 연간 CPI 상승률 anchor를 월별로 평활 분해한 생성 CPI index.
- `korea_cpi_generated_yoy_pct`: 생성 CPI의 전년동월비.
- `ob_major_price_increase_event_dummy`: OB/Cass 주요 출고가 인상 보도 시점 더미(2024-04, 2025-04).
- `months_since_ob_price_event_cap6`: 가격 인상 이후 0~6개월 lag 효과.

## Caveat

주류/맥주 전용 CPI는 KOSIS 동적 표 접근이 불안정해 자동 수집하지 못했다. 대신 실제 수입맥주 단가, 가격 관련 검색량, 연간 CPI anchor 기반 생성 CPI, 가격 인상 이벤트 더미를 사용했다. CPI index는 실제 월별 CPI가 아니라 연간 물가상승률을 월별로 평활화한 모델용 proxy다.
