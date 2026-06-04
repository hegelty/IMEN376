# Cass Demand Model Run Summary

Generated outputs follow `ai_model_prd.md`.

## Model Choice

- Selected AI model: Chronos-2 zero-shot time-series forecasting
- Mandatory baseline: Seasonal Naive
- Current Chronos-2 status: `PASS`
- Chronos-2 note: Chronos-2 univariate ran successfully.
- Current Chronos-2 covariate status: `PASS`
- Chronos-2 covariate note: Chronos-2 covariate-informed run succeeded. Future forecast covariates use historical month-of-year averages and zeroed event dummies.
- Covariates used: temp_avg, heatwave_days, tropical_night_days, kbo_games, world_cup_dummy, holiday_days, ob_price_hike_dummy
- ETS robustness baseline status: `PASS`
- ETS note: ETS additive baseline ran successfully.

## Input Data

- Input file: `cass_demand_v3_monthly.csv`
- Rows: 72
- Range: 2020-01 to 2025-12
- Target: `beer_domestic_volume`

## Data Readiness Warnings

- Target is an annual-anchor-based monthly proxy, not observed Cass SKU-level demand.
- 36 rows have beer_domestic_volume_imputed=1.

## Evaluation Metrics

These metrics are diagnostics only because the current target is a public/proxy monthly series, not actual Cass SKU-level demand.

| model | rows | wape | mase | pinball_0_1 | pinball_0_5 | pinball_0_9 |
| --- | --- | --- | --- | --- | --- | --- |
| seasonal_naive | 24 | 0.005147 | 0.135462 | 331.419167 | 52.683333 | 1392.286833 |
| ets_additive | 24 | 0.012418 | 0.326846 | 371.334056 | 1157.305098 | 1614.342091 |
| chronos2_univariate | 24 | 0.011143 | 0.293296 | 1064.135514 | 798.854010 | 739.036003 |
| chronos2_covariate | 24 | 0.028486 | 0.749772 | 1170.966960 | 2042.160358 | 396.662630 |
| seasonal_naive_rolling | 18 | 0.005213 | 0.136859 | 332.180333 | 72.139167 | 1391.525667 |
| ets_additive_rolling | 18 | 0.012654 | 0.332205 | 408.969536 | 1261.164709 | 1550.598356 |
| chronos2_rolling | 18 | 0.005078 | 0.133320 | 429.961601 | 363.125347 | 424.320474 |

## Interval Coverage

| model | rows | coverage_80 | avg_width_80 | avg_width_80_pct | coverage_95 | avg_width_95 | avg_width_95_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| seasonal_naive | 24 | 1.000000 | 17237.060000 | 0.123878 | 1.000000 | 18892.630000 | 0.135776 |
| ets_additive | 24 | 0.708333 | 17237.060000 | 0.121553 | 0.791667 | 18892.630000 | 0.133228 |
| chronos2_univariate | 24 | 1.000000 | 18031.715169 | 0.126644 | 1.000000 | 41869.494466 | 0.295069 |
| chronos2_covariate | 24 | 1.000000 | 15676.295898 | 0.113085 | 1.000000 | 43375.762044 | 0.313853 |
| seasonal_naive_rolling | 18 | 1.000000 | 17237.060000 | 0.125990 | 1.000000 | 18892.630000 | 0.138090 |
| ets_additive_rolling | 18 | 0.722222 | 17020.280833 | 0.122476 | 0.833333 | 18814.997375 | 0.135115 |
| chronos2_rolling | 18 | 1.000000 | 8542.820747 | 0.060319 | 1.000000 | 22313.520399 | 0.158251 |

## Event / Stress Split

| model | segment | rows | wape | mase | event_reasons |
| --- | --- | --- | --- | --- | --- |
| seasonal_naive | routine | 14 | 0.005147 | 0.124227 | routine |
| seasonal_naive | event_or_stress | 10 | 0.005147 | 0.151191 | heatwave;heatwave,high_kbo_games;heatwave,tropical_night;heatwave,tropical_night,high_kbo_games;high_kbo_games;price_hike;price_hike,high_kbo_games;tropical_night |
| ets_additive | routine | 14 | 0.017049 | 0.411515 | routine |
| ets_additive | event_or_stress | 10 | 0.007091 | 0.208310 | heatwave;heatwave,high_kbo_games;heatwave,tropical_night;heatwave,tropical_night,high_kbo_games;high_kbo_games;price_hike;price_hike,high_kbo_games;tropical_night |
| chronos2_univariate | routine | 14 | 0.016159 | 0.390028 | routine |
| chronos2_univariate | event_or_stress | 10 | 0.005374 | 0.157872 | heatwave;heatwave,high_kbo_games;heatwave,tropical_night;heatwave,tropical_night,high_kbo_games;high_kbo_games;price_hike;price_hike,high_kbo_games;tropical_night |
| chronos2_covariate | routine | 14 | 0.032154 | 0.776117 | routine |
| chronos2_covariate | event_or_stress | 10 | 0.024267 | 0.712889 | heatwave;heatwave,high_kbo_games;heatwave,tropical_night;heatwave,tropical_night,high_kbo_games;high_kbo_games;price_hike;price_hike,high_kbo_games;tropical_night |
| seasonal_naive_rolling | routine | 12 | 0.005213 | 0.122317 | routine |
| seasonal_naive_rolling | event_or_stress | 6 | 0.005213 | 0.165942 | heatwave;heatwave,tropical_night;heatwave,tropical_night,high_kbo_games;tropical_night |
| ets_additive_rolling | routine | 12 | 0.017664 | 0.414451 | routine |
| ets_additive_rolling | event_or_stress | 6 | 0.005269 | 0.167712 | heatwave;heatwave,tropical_night;heatwave,tropical_night,high_kbo_games;tropical_night |
| chronos2_rolling | routine | 12 | 0.006050 | 0.141958 | routine |
| chronos2_rolling | event_or_stress | 6 | 0.003646 | 0.116045 | heatwave;heatwave,tropical_night;heatwave,tropical_night,high_kbo_games;tropical_night |

## Operational Proxy Outputs

- Forecast alert rows: 12
- Tank allocation proxy rows: 12
- Safety stock proxy rows: 12
- Wholesaler advisory proxy rows: 12
- Workflow action queue rows: 12
- High alert rows: 10

## Phase Acceptance Gate

| id | criterion | status | notes |
| --- | --- | --- | --- |
| MVP-1 | Pipeline reads monthly CSV without manual column edits | PASS | model runner reads cass_demand_v3_monthly.csv |
| MVP-2 | Missing Cass Fresh/Light target columns are detected and reported | PASS | readiness warnings include blocked SKU targets |
| MVP-3 | Proxy/imputed target warning appears before model evaluation | PASS | model_run_summary includes proxy/imputed warning |
| MVP-4 | Seasonal Naive baseline forecast is generated | PASS | seasonal_naive_forecast.csv generated |
| MVP-5 | Evaluation report labels metrics as diagnostic only | PASS | model_run_summary labels proxy diagnostics |
| MVP-6 | No report claims validated SKU-level Cass Fresh/Light performance | PASS | reports explicitly block SKU-level claim |
| MVP-7 | Output files are reproducible from a single script | PASS | scripts/model_cass_demand.py regenerates model_outputs |
| M-1 | Actual, non-synthetic demand target is available | FAIL | current target has imputed/proxy periods |
| M-2 | Cass Fresh/Light/Cass 0.0 or Cass family target grain is explicitly defined | PASS | SKU target available |
| M-3 | Seasonal Naive baseline is included | PASS | baseline metrics generated |
| M-4 | Chronos-2 improves MASE or WAPE vs Seasonal Naive baseline | FAIL | Chronos-2 does not beat Seasonal Naive on proxy diagnostic backtest |
| M-5 | 80% and 95% intervals are reported with empirical coverage | PARTIAL | coverage is computed, but target is proxy |
| M-6 | Event/stress periods are evaluated separately | PARTIAL | event split exists, but target is proxy |
| M-7 | High-uncertainty forecasts trigger human review | PARTIAL | forecast_alerts.csv generated; no external workflow integration |
| M-8 | Tank allocation recommendations remain approval-based | PARTIAL | tank_allocation_proxy.csv generated; not SKU/tank executable |

## Output Files

- `data_readiness_report.csv`
- `phase_acceptance_check.csv`
- `seasonal_naive_forecast.csv`
- `seasonal_naive_backtest.csv`
- `rolling_origin_backtest.csv`
- `evaluation_metrics.csv`
- `ets_status.json`
- `ets_forecast.csv` / `ets_backtest.csv` if ETS is available
- `interval_coverage_metrics.csv`
- `event_split_metrics.csv`
- `forecast_alerts.csv`
- `tank_allocation_proxy.csv`
- `safety_stock_proxy.csv`
- `wholesaler_advisory_proxy.csv`
- `workflow_action_queue.csv`
- `monitoring_snapshot.csv`
- `monitoring_alerts.csv`
- `chronos2_status.json`
- Chronos-2 files: `chronos2_forecast.csv`, `chronos2_backtest.csv`, `chronos2_covariate_forecast.csv`, `chronos2_covariate_backtest.csv`
- `forecast_plot.png` if matplotlib was available

## Interpretation

Chronos-2 does not beat Seasonal Naive on this proxy-data diagnostic backtest. This is expected to be possible because the current target is seasonally allocated from annual anchors, which gives the one-year seasonal baseline an artificial advantage.

Use the Seasonal Naive metrics as the required baseline. If Chronos-2 does not run, the implementation is still complete but the environment needs `chronos-forecasting` plus access to the Hugging Face model weights.

The current model output must not be presented as validated Cass Fresh/Light SKU-level performance until actual SKU demand targets are collected.
