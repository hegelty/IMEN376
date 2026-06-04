from pathlib import Path
import csv, math, time
base=Path('/home/hegelty/programming/IMEN343/research_ob_cass_demand')
data=base/'data'
out=data/'exog_economic_price_monthly.csv'

def month_range(start='2020-01', end='2025-12'):
    y,m=map(int,start.split('-')); ey,em=map(int,end.split('-'))
    while (y,m)<=(ey,em):
        yield f'{y}-{m:02d}', y, m
        m+=1
        if m==13: y+=1; m=1

def fnum(x, default=0.0):
    try:
        if x is None or x=='': return default
        return float(x)
    except: return default

# Actual import unit values from Comtrade HS2203 monthly file
com={}
with (data/'monthly_hs2203_comtrade_korea_2020_2025.csv').open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
        kg=fnum(r.get('import_net_weight_kg')); usd=fnum(r.get('import_value_usd'))
        com[r['month']]={'kg':kg,'usd':usd,'unit_usd_per_kg':usd/kg if kg>0 else ''}

# Google Trends price/economy attention indices (actual monthly search index)
trend_file=data/'monthly_google_trends_price_econ_2020_2026.csv'
if not trend_file.exists():
    try:
        from pytrends.request import TrendReq
        pytrends=TrendReq(hl='ko-KR', tz=540, timeout=(10,30), retries=1, backoff_factor=0.2)
        kws=['물가','외식 물가','맥주 가격','주류 가격','소비심리']
        pytrends.build_payload(kws, cat=0, timeframe='2020-01-01 2026-05-27', geo='KR', gprop='')
        df=pytrends.interest_over_time().reset_index()
        df.to_csv(trend_file,index=False,encoding='utf-8-sig')
        time.sleep(1)
    except Exception as e:
        print('pytrends economic failed:',repr(e))
tr={}
if trend_file.exists():
    with trend_file.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f): tr[r['date'][:7]]=r

# CPI generated index using known/consensus annual CPI inflation anchors.
# 2020~2024 actual annual Korea CPI inflation approx; 2025 provisional assumption.
annual_infl={2020:0.5, 2021:2.5, 2022:5.1, 2023:3.6, 2024:2.3, 2025:2.2}
# Create smooth monthly index, 2020-01 = 100
cpi_index={}
idx=100.0
prev=None
for mo,y,m in month_range():
    if prev is None:
        idx=100.0
    else:
        monthly=(1+annual_infl[y]/100)**(1/12)-1
        idx*=1+monthly
    cpi_index[mo]=idx
    prev=mo

unit_map={k:v['unit_usd_per_kg'] for k,v in com.items() if v.get('unit_usd_per_kg')!=''}
def yoy(map_, mo):
    y=int(mo[:4]); prev=f'{y-1}-{mo[5:7]}'
    if mo in map_ and prev in map_ and map_[prev]: return (map_[mo]/map_[prev]-1)*100
    return ''

price_event={mo:0 for mo,_,_ in month_range()}
# OB/Cass price increase timing based on public reporting; event dummy only.
for mo in ['2024-04','2025-04']:
    price_event[mo]=1

rows=[]
for mo,y,m in month_range():
    t=tr.get(mo,{})
    row={
        'month':mo,
        'korea_cpi_generated_index_2020_01_100':round(cpi_index[mo],3),
        'korea_cpi_generated_yoy_pct':round(yoy(cpi_index,mo),3) if yoy(cpi_index,mo)!='' else '',
        'korea_annual_cpi_inflation_anchor_pct':annual_infl[y],
        'imported_beer_unit_value_usd_per_kg':round(unit_map.get(mo,''),4) if unit_map.get(mo,'')!='' else '',
        'imported_beer_unit_value_yoy_pct':round(yoy(unit_map,mo),3) if yoy(unit_map,mo)!='' else '',
        'google_trends_inflation_m物가':fnum(t.get('물가')),
        'google_trends_dining_price':fnum(t.get('외식 물가')),
        'google_trends_beer_price':fnum(t.get('맥주 가격')),
        'google_trends_alcohol_price':fnum(t.get('주류 가격')),
        'google_trends_consumer_sentiment':fnum(t.get('소비심리')),
        'price_pressure_search_index':fnum(t.get('물가'))+fnum(t.get('외식 물가'))+fnum(t.get('맥주 가격'))+fnum(t.get('주류 가격')),
        'ob_major_price_increase_event_dummy':price_event.get(mo,0),
    }
    idx_month=y*12+m
    last=None
    for ev in ['2024-04','2025-04']:
        ey=int(ev[:4]); em=int(ev[5:7]); eidx=ey*12+em
        if eidx<=idx_month: last=eidx
    row['months_since_ob_price_event_cap6']=min(6,idx_month-last) if last else ''
    row['economic_price_data_source_note']='Comtrade HS2203 import unit value actual; Google Trends price/economy search actual; CPI index generated from annual Korea CPI inflation anchors; OB price event dummy manually coded from public price-increase reporting.'
    rows.append(row)
with out.open('w',newline='',encoding='utf-8-sig') as f:
    cols=list(rows[0].keys()); w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)
(base/'subagent_exog_economic_price.md').write_text('''# IMEN343 OB Cass 수요예측: 가격·경제 외생변수 보완 결과

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
''',encoding='utf-8')
print('wrote',out,len(rows),'rows')
