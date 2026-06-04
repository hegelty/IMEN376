from pathlib import Path
import requests, hashlib, time, urllib.parse
base=Path('/home/hegelty/programming/IMEN343/research_ob_cass_demand')
cache=base/'data'/'news_rss_cache'; cache.mkdir(exist_ok=True)
queries=[
 '맥주 OR beer',
 '(카스 OR 오비맥주 OR OB맥주 OR "OB맥주" OR "OB Beer" OR Cass) (맥주 OR beer OR 주류 OR 오비)',
 '(무알콜 OR 무알코올 OR 논알콜 OR 비알코올 OR "non-alcoholic" OR "zero alcohol") (맥주 OR beer)',
 '(폭염 OR 무더위 OR 날씨 OR 기온 OR 열대야 OR 장마) (맥주 OR beer OR 주류 OR 음료)',
 '(축제 OR 페스티벌 OR 맥주축제 OR "beer festival") (맥주 OR beer OR 카스 OR 오비맥주)',
 '(규제 OR 주세 OR 종량세 OR 가격인상 OR 인상 OR 건강 OR 절주 OR 음주 OR 다이어트) (맥주 OR beer OR 주류)',
]
s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0'})
count=0; skipped=0
for year in [2024,2025]:
 for month in range(1,13):
  y2=year+(month//12); m2=month%12+1
  after=f'{year}-{month:02d}-01'; before=f'{y2}-{m2:02d}-01'
  for q in queries:
   full=f'{q} after:{after} before:{before}'
   url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':full,'hl':'ko','gl':'KR','ceid':'KR:ko'})
   h=hashlib.sha1(url.encode()).hexdigest()
   p=cache/f'{h}.xml'
   if p.exists() and p.stat().st_size>200:
    skipped+=1; continue
   try:
    r=s.get(url,timeout=20)
    p.write_bytes(r.content)
    count+=1
    print('fetched', after, q[:20], r.status_code, len(r.content), flush=True)
   except Exception as e:
    print('ERR', after, q[:20], e, flush=True)
   time.sleep(0.2)
print('done fetched',count,'skipped',skipped)
