from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

PKG = Path('/home/hegelty/programming/IMEN343/research_ob_cass_demand/final_presentation_ai_package')
FIG = PKG / 'figures'
OUT = PKG / 'model_outputs'
DATA = PKG / 'data'
FIG.mkdir(exist_ok=True)

plt.rcParams.update({
    'figure.dpi': 160,
    'savefig.dpi': 220,
    'font.size': 10,
    'axes.titlesize': 14,
    'axes.labelsize': 10,
    'legend.fontsize': 9,
    'axes.grid': True,
    'grid.alpha': 0.25,
})


def savefig(name):
    path = FIG / name
    plt.tight_layout()
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    return path

# Load data
integrated = pd.read_csv(DATA / 'user_method_integrated_dataset.csv')
integrated['month'] = pd.to_datetime(integrated['month'])
ml_pred = pd.read_csv(OUT / 'user_method_model_backtest_predictions.csv')
chronos_pred = pd.read_csv(OUT / 'chronos2_user_method_predictions.csv')
metrics = pd.read_csv(OUT / 'user_method_all_model_metrics.csv')
ml_pred['month_dt'] = pd.to_datetime(ml_pred['month'])
chronos_pred['month_dt'] = pd.to_datetime(chronos_pred['month'])

# 1. Target construction components
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(integrated['month'], integrated['beer_apparent_consumption_user_method_kl'], label='Apparent consumption target', linewidth=2.4, color='#1f77b4')
ax.plot(integrated['month'], integrated['beer_domestic_volume'], label='Domestic shipment base', linewidth=1.7, color='#ff7f0e', alpha=0.85)
ax.fill_between(integrated['month'], 0, integrated['hs2203_import_kl_approx'], label='HS2203 import kL approx', color='#2ca02c', alpha=0.25)
ax.fill_between(integrated['month'], -integrated['hs2203_export_kl_approx'], 0, label='HS2203 export kL approx (subtracted)', color='#d62728', alpha=0.25)
ax.set_title('Demand Target Construction: Domestic Shipment + Import - Export')
ax.set_ylabel('kL per month')
ax.legend(loc='upper left', ncol=2)
savefig('01_target_construction_apparent_consumption.png')

# 2. Actual vs forecasts: Chronos and Seasonal Naive
seasonal = ml_pred[ml_pred['model'] == 'seasonal_naive'].copy()
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(chronos_pred['month_dt'], chronos_pred['actual'], label='Actual target proxy', linewidth=2.5, color='#111111')
ax.plot(chronos_pred['month_dt'], chronos_pred['prediction'], label='Chronos-2 forecast', linewidth=2.2, color='#1f77b4')
ax.plot(seasonal['month_dt'], seasonal['prediction'], label='Seasonal Naive forecast', linewidth=2.0, linestyle='--', color='#ff7f0e')
if '0.1' in chronos_pred.columns and '0.9' in chronos_pred.columns:
    ax.fill_between(chronos_pred['month_dt'], chronos_pred['0.1'], chronos_pred['0.9'], color='#1f77b4', alpha=0.14, label='Chronos-2 80% interval')
ax.set_title('Backtest Forecast: Chronos-2 vs Seasonal Naive')
ax.set_ylabel('kL per month')
ax.legend(loc='upper left')
savefig('02_backtest_actual_vs_chronos2_seasonal.png')

# 3. MASE comparison top models
all_metrics = metrics[metrics['split'] == 'all_test'].copy().sort_values('MASE').head(12)
label_map = {
    'chronos2_user_method': 'Chronos-2',
    'seasonal_naive': 'Seasonal Naive',
    'lagged_gt_gradient_boosting': 'GB + lagged GT',
    'gradient_boosting': 'GradientBoosting',
    'lagged_gt_extra_trees': 'ExtraTrees + lagged GT',
    'extra_trees': 'ExtraTrees',
    'lagged_gt_random_forest': 'RF + lagged GT',
    'random_forest': 'RandomForest',
    'lagged_gt_knn': 'KNN + lagged GT',
    'knn': 'KNN',
    'hist_gradient_boosting': 'HistGradientBoosting',
    'lagged_gt_hist_gradient_boosting': 'HGB + lagged GT',
}
all_metrics['label'] = all_metrics['model'].map(label_map).fillna(all_metrics['model'])
colors = ['#1f77b4' if m == 'chronos2_user_method' else '#ff7f0e' if m == 'seasonal_naive' else '#7f7f7f' for m in all_metrics['model']]
fig, ax = plt.subplots(figsize=(11, 5.5))
ax.barh(all_metrics['label'][::-1], all_metrics['MASE'][::-1], color=colors[::-1])
ax.set_title('Model Comparison by MASE (Lower is Better)')
ax.set_xlabel('MASE')
for i, v in enumerate(all_metrics['MASE'][::-1]):
    ax.text(v + 0.01, i, f'{v:.3f}', va='center')
savefig('03_model_comparison_mase.png')

# 4. WAPE comparison top models
all_wape = metrics[metrics['split'] == 'all_test'].copy().sort_values('WAPE').head(12)
all_wape['label'] = all_wape['model'].map(label_map).fillna(all_wape['model'])
colors = ['#1f77b4' if m == 'chronos2_user_method' else '#ff7f0e' if m == 'seasonal_naive' else '#7f7f7f' for m in all_wape['model']]
fig, ax = plt.subplots(figsize=(11, 5.5))
ax.barh(all_wape['label'][::-1], all_wape['WAPE'][::-1], color=colors[::-1])
ax.set_title('Model Comparison by WAPE (Lower is Better)')
ax.set_xlabel('WAPE')
for i, v in enumerate(all_wape['WAPE'][::-1]):
    ax.text(v + 0.0008, i, f'{v:.3f}', va='center')
savefig('04_model_comparison_wape.png')

# 5. Absolute error over time
err = chronos_pred[['month_dt','actual','prediction']].rename(columns={'prediction':'chronos_pred'})
err = err.merge(seasonal[['month_dt','prediction']].rename(columns={'prediction':'seasonal_pred'}), on='month_dt', how='left')
err['chronos_abs_error'] = (err['actual'] - err['chronos_pred']).abs()
err['seasonal_abs_error'] = (err['actual'] - err['seasonal_pred']).abs()
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(err['month_dt'], err['chronos_abs_error'], label='Chronos-2 absolute error', linewidth=2.2, color='#1f77b4')
ax.plot(err['month_dt'], err['seasonal_abs_error'], label='Seasonal Naive absolute error', linewidth=2.0, linestyle='--', color='#ff7f0e')
ax.set_title('Backtest Absolute Error Over Time')
ax.set_ylabel('Absolute error (kL)')
ax.legend(loc='upper left')
savefig('05_absolute_error_over_time.png')

# 6. Non-alcohol / Cass 0.0 segment
fig, ax1 = plt.subplots(figsize=(12, 5))
if 'nonalc_segment_user_method_kl' in integrated.columns:
    ax1.plot(integrated['month'], integrated['nonalc_segment_user_method_kl'], label='Non-alcohol segment proxy (kL)', linewidth=2.3, color='#9467bd')
if 'cass_zero_user_method_kl' in integrated.columns:
    ax1.plot(integrated['month'], integrated['cass_zero_user_method_kl'], label='Cass 0.0 / zero-alcohol proxy (kL)', linewidth=2.0, color='#8c564b')
ax1.set_title('Non-alcohol / Zero-alcohol Segment Proxy')
ax1.set_ylabel('kL proxy')
ax1.legend(loc='upper left')
savefig('06_nonalc_zero_segment_proxy.png')

# 7. Event/stress markers with target
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(integrated['month'], integrated['beer_apparent_consumption_user_method_kl'], label='Apparent consumption target', linewidth=2.4, color='#1f77b4')
event_mask = (
    (pd.to_numeric(integrated.get('heatwave_days', 0), errors='coerce').fillna(0) > 0)
    | (pd.to_numeric(integrated.get('tropical_night_days', 0), errors='coerce').fillna(0) > 0)
    | (pd.to_numeric(integrated.get('kbo_games', 0), errors='coerce').fillna(0) >= 100)
    | (pd.to_numeric(integrated.get('ob_price_hike_dummy', 0), errors='coerce').fillna(0) > 0)
)
events = integrated[event_mask]
ax.scatter(events['month'], events['beer_apparent_consumption_user_method_kl'], label='Event / stress month', color='#d62728', s=42, zorder=3)
ax.set_title('Demand Target with Event / Stress Months')
ax.set_ylabel('kL per month')
ax.legend(loc='upper left')
savefig('07_event_stress_months_on_target.png')

# 8. Presentation summary table as image
summary = pd.DataFrame([
    ['Chronos-2', 0.387142, 0.016822, 'Best final AI model'],
    ['Seasonal Naive', 0.445234, 0.019346, 'Strong sanity-check baseline'],
    ['GradientBoosting + lagged GT', 0.615030, 0.026724, 'Best lagged-GT ML model'],
    ['GradientBoosting', 0.692605, 0.030095, 'Best non-GT ML model'],
    ['ExtraTrees + lagged GT', 0.709036, 0.030809, 'Tree ensemble with demand-sensing'],
], columns=['Model','MASE','WAPE','Use in presentation'])
fig, ax = plt.subplots(figsize=(12, 2.8))
ax.axis('off')
tbl = ax.table(cellText=summary.values, colLabels=summary.columns, cellLoc='center', loc='center')
tbl.auto_set_font_size(False)
tbl.set_fontsize(9)
tbl.scale(1, 1.5)
for (row, col), cell in tbl.get_celld().items():
    if row == 0:
        cell.set_facecolor('#1f77b4')
        cell.set_text_props(color='white', weight='bold')
    elif row == 1:
        cell.set_facecolor('#dbeafe')
ax.set_title('Final Model Results Summary', pad=12)
savefig('08_final_model_summary_table.png')

# Figure index
figure_notes = '''# Figure Index for Presentation

1. `01_target_construction_apparent_consumption.png` — Shows final demand target construction: domestic shipment + HS2203 import - HS2203 export.
2. `02_backtest_actual_vs_chronos2_seasonal.png` — Main backtest chart: actual target proxy vs Chronos-2 vs Seasonal Naive, including Chronos interval.
3. `03_model_comparison_mase.png` — Main model ranking by MASE.
4. `04_model_comparison_wape.png` — Main model ranking by WAPE.
5. `05_absolute_error_over_time.png` — Shows monthly absolute error comparison between Chronos-2 and Seasonal Naive.
6. `06_nonalc_zero_segment_proxy.png` — Non-alcohol / zero-alcohol segment proxy for Cass 0.0 discussion.
7. `07_event_stress_months_on_target.png` — Target series with event/stress month markers.
8. `08_final_model_summary_table.png` — Slide-ready summary table of top model results.
'''
(FIG / 'FIGURE_INDEX.md').write_text(figure_notes, encoding='utf-8')
print('Generated figures in', FIG)
for p in sorted(FIG.glob('*.png')):
    print(p.name)
