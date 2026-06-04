# Model Training Data Only

실제 학습/모델 구현에 바로 필요한 파일만 모은 폴더입니다.

## 포함
- `final_cass_demand_model_dataset_with_exogenous_2020_2025.csv`: 최종 학습 입력 데이터셋
- `final_model_variable_dictionary.csv`: 변수 사전
- `final_exogenous_dataset_validation.csv`: 병합/범위/결측 검증 요약

## 제외
다음은 최종 데이터셋 생성·검증 과정에서는 사용되었지만, 모델 담당자가 직접 학습 입력으로 사용할 필요가 없어 제외했습니다.
- Google Trends 원천/중간 CSV
- UN Comtrade 원천/중간 CSV
- Open-Meteo 단독 날씨 CSV
- 외생변수별 중간 병합 CSV
- 기사 sample, 원문 PDF/TXT, 스크립트, 조사 메모

모델 학습은 원칙적으로 `final_cass_demand_model_dataset_with_exogenous_2020_2025.csv` 하나를 기준으로 진행하면 됩니다.
