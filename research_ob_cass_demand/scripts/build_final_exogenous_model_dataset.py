from pathlib import Path
import csv
base=Path('/home/hegelty/programming/IMEN343/research_ob_cass_demand')
data=base/'data'

def read_csv(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def index_by_month(rows):
    return {r['month']:r for r in rows}

base_rows=read_csv(data/'monthly_beer_segment_modeling_dataset_2020_2025.csv')
files=[
    ('weather', data/'exog_weather_environment_monthly.csv'),
    ('events', data/'exog_events_calendar_monthly.csv'),
    ('news', data/'exog_news_unstructured_monthly.csv'),
    ('econ', data/'exog_economic_price_monthly.csv'),
]
lookup=[]
for group,p in files:
    rows=read_csv(p)
    lookup.append((group,index_by_month(rows), rows[0].keys()))

merged=[]
used=set(base_rows[0].keys())
all_cols=list(base_rows[0].keys())
source_cols=[]
for group,idx,cols in lookup:
    for c in cols:
        if c=='month': continue
        nc=c if c not in used else f'{group}__{c}'
        used.add(nc); all_cols.append(nc); source_cols.append((group,c,nc))

for r in base_rows:
    nr=dict(r)
    mo=r['month']
    for group,idx,cols in lookup:
        sr=idx.get(mo,{})
        for c in cols:
            if c=='month': continue
            nc=c if c in all_cols and c not in r else f'{group}__{c}'
            # Need match mapping, not recompute ambiguity
        
    # use source_cols mapping
    for group,orig,nc in source_cols:
        sr=next((idx for g,idx,cols in lookup if g==group),{}).get(mo,{})
        nr[nc]=sr.get(orig,'')
    merged.append(nr)

out=data/'final_cass_demand_model_dataset_with_exogenous_2020_2025.csv'
with out.open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=all_cols); w.writeheader(); w.writerows(merged)

# Variable dictionary
manual={
'alcoholic_beer_total_proxy_kl':'전체 알코올 맥주 월별 수요 proxy(kL). 공식 연간 apparent market을 월별 수입맥주/검색량으로 분해.',
'regular_beer_excluding_low_calorie_proxy_kl':'저칼로리/라이트를 제외한 일반 맥주 월별 수요 proxy(kL).',
'low_calorie_light_beer_proxy_kl':'저칼로리/라이트 맥주 월별 수요 proxy(kL). Cass Light 공개 점유율과 성장 보도를 반영.',
'nonalcoholic_beer_proxy_kl':'논알콜/무알콜 맥주 월별 수요 proxy(kL). 시장규모 금액과 검색량 기반 생성.',
'cass_fresh_proxy_kl':'Cass Fresh 월별 수요 proxy(kL). 실제 판매량이 아니라 공개 점유율 기반 시나리오 값.',
'cass_light_proxy_kl':'Cass Light 월별 수요 proxy(kL). 실제 판매량이 아니라 공개 점유율 기반 시나리오 값.',
'cass_0_0_or_all_zero_proxy_kl':'Cass 0.0/All Zero 월별 수요 proxy(kL). 무·비알코올 시장 내 Cass 계열 share 가정.',
}
def group_of(col):
    if col in base_rows[0]: return 'demand_base_or_existing_proxy'
    for g,orig,nc in source_cols:
        if nc==col: return g
    return 'unknown'
def desc(col):
    if col in manual: return manual[col]
    if col.startswith('seoul_') or col.startswith('weather__seoul_'): return '서울 기준 날씨/환경 변수. 맥주 수요의 계절성·야외활동·체감더위/대기질 효과를 설명.'
    if 'kbo' in col.lower(): return 'KBO 경기/시즌 변수. 야구 관람·치맥·야식/외식 수요 proxy.'
    if 'festival' in col.lower(): return '지역축제/맥주축제 변수. 야외 행사와 관광·모임 수요 proxy.'
    if 'holiday' in col.lower() or 'nonwork' in col.lower() or 'weekend' in col.lower(): return '공휴일/주말/연휴 변수. 여행·모임·외식 수요와 유통 영업일 효과 proxy.'
    if 'news' in col.lower(): return 'Google News RSS 기사 수 또는 제목 키워드 count. 비정형 이슈·관심도·긍부정 proxy.'
    if 'google_trends' in col.lower(): return 'Google Trends 검색 관심도. 절대 검색량이 아니라 상대 index.'
    if 'cpi' in col.lower() or 'price' in col.lower() or 'unit_value' in col.lower() or 'inflation' in col.lower(): return '가격/물가/수입단가/가격관심도 변수. 가격 민감도와 비용 압력 proxy.'
    if 'month_sin' in col or 'month_cos' in col or 'season' in col.lower() or 'summer' in col.lower(): return '계절성 파생 변수.'
    return '모델 입력 후보 변수. 상세 출처는 그룹별 설명 문서 참고.'

dict_out=data/'final_model_variable_dictionary.csv'
with dict_out.open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=['variable','group','description','modeling_use','caveat'])
    w.writeheader()
    for c in all_cols:
        g=group_of(c)
        caveat=''
        if g=='news': caveat='기사 수는 Google News RSS 검색결과 count이며 전체 뉴스량이 아님. 키워드 감성은 제목 기반 단순 proxy.'
        elif g=='weather': caveat='Open-Meteo 격자형 archive 및 서울 중구 대기질 proxy. 공식 ASOS/전국 평균 아님.'
        elif g=='events': caveat='축제/스포츠/공휴일 count는 공개자료/규칙 기반. 일부 축제는 계획 자료라 취소·변경 가능.'
        elif g=='econ': caveat='일부 CPI는 연간 anchor 기반 생성값. 주류 전용 CPI 아님.'
        elif 'proxy' in c: caveat='실제 내부 판매량이 아니라 공개자료 기반 proxy 또는 생성값.'
        w.writerow({'variable':c,'group':g,'description':desc(c),'modeling_use':desc(c),'caveat':caveat})

# summary validation
summary=data/'final_exogenous_dataset_validation.csv'
with summary.open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['item','value'])
    w.writerow(['rows',len(merged)]); w.writerow(['columns',len(all_cols)])
    w.writerow(['start_month',merged[0]['month']]); w.writerow(['end_month',merged[-1]['month']])
    for group,idx,cols in lookup:
        w.writerow([f'{group}_source_months',len(idx)]); w.writerow([f'{group}_source_columns',len(list(cols))])
print('wrote',out,len(merged),'rows',len(all_cols),'cols')
print('wrote',dict_out)
