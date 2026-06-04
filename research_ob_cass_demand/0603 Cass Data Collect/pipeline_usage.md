# Cass Demand Pipeline Usage

작성일: 2026-06-03

## 1. End-to-end 실행

기존 수집 CSV를 유지하고 모델/Phase 1 status만 재생성:

```powershell
python .\scripts\run_pipeline.py --skip-collect
```

공개 데이터까지 다시 수집:

```powershell
python .\scripts\run_pipeline.py
```

Chronos-2를 건너뛰고 baseline/report만 생성:

```powershell
python .\scripts\run_pipeline.py --skip-collect --skip-chronos
```

## 2. Phase 1 템플릿 주의

`scripts/prepare_phase1_templates.py`는 기본적으로 기존 템플릿 파일을 보존한다. 내부 데이터를 채운 뒤 실수로 지우지 않기 위한 동작이다.

템플릿을 강제로 초기화하려면:

```powershell
python .\scripts\prepare_phase1_templates.py --overwrite
```

## 3. 주요 산출물

- `model_outputs/model_run_summary.md`
- `model_outputs/phase_acceptance_check.csv`
- `model_outputs/workflow_action_queue.csv`
- `model_outputs/monitoring_snapshot.csv`
- `model_outputs/monitoring_alerts.csv`
- `model_outputs/phase1_ingestion_status.csv`
- `model_outputs/phase1_model_input_status.csv`
- `data/phase1_model_input.csv`

## 4. Daily Refresh

스케줄 등록 없이 daily runner를 한 번 실행:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_daily_pipeline.ps1 -SkipCollect
```

Windows Task Scheduler에 매일 06:00 실행 등록:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_daily_pipeline_task.ps1 -At 06:00
```

위 등록 스크립트는 직접 실행해야 하며, 현재 작업에서는 스케줄을 등록하지 않았다.

## 5. 현재 정상 blocker

현재 `data/phase1_*_template.csv` 파일들은 schema만 있고 실제 내부 데이터 row가 없다. 따라서 `phase1_model_input_status.csv`의 `BLOCKED`는 정상이다.

Phase 1로 전환하려면 최소한 `data/phase1_sku_demand_template.csv`에 실제 `actual_demand_kl` row가 필요하다.
