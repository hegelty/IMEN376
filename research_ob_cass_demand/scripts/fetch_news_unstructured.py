#!/usr/bin/env python3
"""
Collect monthly unstructured/news exogenous variables for the OB/Cass demand project.

Primary source: Google News RSS search with explicit after:/before: date filters, Korean locale.
GDELT DOC API was considered first, but the public endpoint repeatedly returned HTTP 429
from this environment during collection; see the generated report for caveats.

The RSS endpoint returns at most about 100 items per request, so this script recursively
splits intervals when a query hits the cap, then de-duplicates articles within month/category.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

PROJECT = Path('/home/hegelty/programming/IMEN343/research_ob_cass_demand')
DATA_DIR = PROJECT / 'data'
CACHE_DIR = PROJECT / 'data' / 'news_rss_cache'
OUT_CSV = DATA_DIR / 'exog_news_unstructured_monthly.csv'
META_JSON = DATA_DIR / 'exog_news_unstructured_metadata.json'

RSS_URL = 'https://news.google.com/rss/search'
LOCALE_PARAMS = {'hl': 'ko', 'gl': 'KR', 'ceid': 'KR:ko'}
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 news-count-research/1.0'
REQUEST_SLEEP_SEC = 0.35
RSS_CAP = 100

# Category queries are intentionally broad enough for monthly demand proxies, but still anchored
# to beer/alcohol/beverage terms where possible to reduce generic news noise.
CATEGORIES = {
    'beer': {
        'query': '맥주 OR beer',
        'column': 'news_beer_mentions',
        'meaning': 'General beer media attention / category salience.',
    },
    'cass_ob': {
        'query': '(카스 OR 오비맥주 OR OB맥주 OR "OB맥주" OR "OB Beer" OR Cass) (맥주 OR beer OR 주류 OR 오비)',
        'column': 'news_cass_ob_mentions',
        'meaning': 'Cass/OB brand-specific attention and possible marketing/promotional intensity proxy.',
    },
    'nonalcohol': {
        'query': '(무알콜 OR 무알코올 OR 논알콜 OR 비알코올 OR "non-alcoholic" OR "zero alcohol") (맥주 OR beer)',
        'column': 'news_nonalcohol_beer_mentions',
        'meaning': 'No/low-alcohol beer trend attention; possible substitution or category expansion signal.',
    },
    'heat_weather': {
        'query': '(폭염 OR 무더위 OR 날씨 OR 기온 OR 열대야 OR 장마) (맥주 OR beer OR 주류 OR 음료)',
        'column': 'news_heat_weather_mentions',
        'meaning': 'Weather/heat coverage tied to beer/alcohol/beverage consumption context.',
    },
    'festival': {
        'query': '(축제 OR 페스티벌 OR 맥주축제 OR "beer festival") (맥주 OR beer OR 카스 OR 오비맥주)',
        'column': 'news_festival_beer_mentions',
        'meaning': 'Festival/event/beer-festival attention; proxy for outdoor/social consumption occasions.',
    },
    'reg_price_health': {
        'query': '(규제 OR 주세 OR 종량세 OR 가격인상 OR 인상 OR 건강 OR 절주 OR 음주 OR 다이어트) (맥주 OR beer OR 주류)',
        'column': 'news_reg_price_health_mentions',
        'meaning': 'Regulatory, tax, price, moderation, and health-trend attention; possible demand dampener or structural-shift proxy.',
    },
}

POSITIVE_KEYWORDS = [
    '성장', '증가', '상승', '회복', '호황', '인기', '흥행', '최대', '신제품', '출시', '확대',
    '할인', '축제', '페스티벌', '성수기', '1위', '선호', '수상', '완판', '돌풍', '강세',
]
NEGATIVE_KEYWORDS = [
    '감소', '하락', '침체', '위축', '부진', '적자', '불매', '논란', '규제', '과징금', '리콜',
    '사고', '음주운전', '위험', '우려', '가격인상', '가격 인상', '인상', '주세', '세금',
    '코로나', '팬데믹', '파업', '중단', '폭염', '장마', '건강', '절주',
]

TAG_RE = re.compile(r'<[^>]+>')
SPACE_RE = re.compile(r'\s+')


def month_starts(start='2020-01-01', end='2025-12-01'):
    cur = dt.date.fromisoformat(start)
    last = dt.date.fromisoformat(end)
    while cur <= last:
        yield cur
        y = cur.year + (cur.month // 12)
        m = cur.month % 12 + 1
        cur = dt.date(y, m, 1)


def next_month(d: dt.date) -> dt.date:
    return dt.date(d.year + (d.month // 12), d.month % 12 + 1, 1)


def normalize_text(s: str | None) -> str:
    if not s:
        return ''
    s = html.unescape(s)
    s = TAG_RE.sub(' ', s)
    return SPACE_RE.sub(' ', s).strip()


def cache_key(query: str, start: dt.date, end: dt.date) -> str:
    raw = json.dumps({'q': query, 'start': start.isoformat(), 'end': end.isoformat(), **LOCALE_PARAMS}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()


def fetch_rss(query: str, start: dt.date, end: dt.date) -> tuple[list[dict], bool, str]:
    """Fetch a single RSS interval [start, end). Returns items, hit_cap, URL."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = cache_key(query, start, end)
    cache_path = CACHE_DIR / f'{key}.xml'
    dated_query = f'{query} after:{start.isoformat()} before:{end.isoformat()}'
    params = dict(LOCALE_PARAMS)
    params['q'] = dated_query
    url = RSS_URL + '?' + urllib.parse.urlencode(params)

    if cache_path.exists():
        data = cache_path.read_bytes()
    else:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        last_err = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=35) as resp:
                    data = resp.read()
                cache_path.write_bytes(data)
                time.sleep(REQUEST_SLEEP_SEC)
                break
            except Exception as e:  # noqa: BLE001 - retry network hiccups
                last_err = e
                time.sleep(2.0 * (attempt + 1))
        else:
            raise RuntimeError(f'Failed to fetch RSS after retries: {url} :: {last_err}')

    root = ET.fromstring(data)
    out = []
    for item in root.findall('.//item'):
        title = normalize_text(item.findtext('title'))
        desc = normalize_text(item.findtext('description'))
        link = normalize_text(item.findtext('link'))
        guid = normalize_text(item.findtext('guid'))
        source = normalize_text(item.findtext('source'))
        pub_text = normalize_text(item.findtext('pubDate'))
        pub_date = None
        if pub_text:
            try:
                pub_dt = parsedate_to_datetime(pub_text)
                pub_date = pub_dt.date().isoformat()
            except Exception:
                pub_date = None
        out.append({
            'title': title,
            'description': desc,
            'link': link,
            'guid': guid,
            'source': source,
            'pubDate': pub_text,
            'pub_date': pub_date,
        })
    return out, len(out) >= RSS_CAP, url


def split_interval(start: dt.date, end: dt.date) -> tuple[dt.date, dt.date] | None:
    days = (end - start).days
    if days <= 1:
        return None
    mid = start + dt.timedelta(days=days // 2)
    return mid, mid


def collect_interval(query: str, start: dt.date, end: dt.date, urls: list[str], cap_leafs: list[dict]) -> list[dict]:
    items, hit_cap, url = fetch_rss(query, start, end)
    urls.append(url)
    if hit_cap and (end - start).days > 1:
        mid = start + dt.timedelta(days=(end - start).days // 2)
        return collect_interval(query, start, mid, urls, cap_leafs) + collect_interval(query, mid, end, urls, cap_leafs)
    if hit_cap:
        cap_leafs.append({'start': start.isoformat(), 'end': end.isoformat(), 'url': url})
    return items


def article_key(item: dict) -> str:
    # Google News RSS links are often stable redirect URLs; fall back to normalized title/source/date.
    link = item.get('link') or item.get('guid') or ''
    if link:
        return 'link:' + link
    raw = '|'.join([item.get('title', ''), item.get('source', ''), item.get('pub_date', '')]).lower()
    return 'text:' + hashlib.sha1(raw.encode('utf-8')).hexdigest()


def filter_to_interval(items: list[dict], start: dt.date, end: dt.date) -> list[dict]:
    filtered = []
    for item in items:
        pd = item.get('pub_date')
        if not pd:
            filtered.append(item)
            continue
        try:
            d = dt.date.fromisoformat(pd)
        except ValueError:
            filtered.append(item)
            continue
        if start <= d < end:
            filtered.append(item)
    return filtered


def keyword_hits(text: str, keywords: list[str]) -> int:
    return sum(text.count(k) for k in keywords)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    months = list(month_starts())
    rows = []
    metadata = {
        'created_at_utc': dt.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
        'source': 'Google News RSS search, hl=ko, gl=KR, ceid=KR:ko',
        'rss_cap_per_request': RSS_CAP,
        'categories': CATEGORIES,
        'positive_keywords': POSITIVE_KEYWORDS,
        'negative_keywords': NEGATIVE_KEYWORDS,
        'requests': {},
        'cap_leafs': {},
        'notes': [
            'Counts are de-duplicated RSS item counts, not full article universe counts.',
            'Recursive date splitting is used when a request returns about 100 items.',
            'External article text is treated as untrusted; only title/description/source/date metadata is parsed.',
        ],
    }

    for month_start in months:
        month_end = next_month(month_start)
        month_label = month_start.strftime('%Y-%m')
        row = {'month': month_label}
        union_items = {}
        row['_cap_any'] = 0

        for cat, spec in CATEGORIES.items():
            urls: list[str] = []
            cap_leafs: list[dict] = []
            items = collect_interval(spec['query'], month_start, month_end, urls, cap_leafs)
            items = filter_to_interval(items, month_start, month_end)
            dedup = {}
            for it in items:
                dedup[article_key(it)] = it
                union_items[article_key(it)] = it
            count = len(dedup)
            row[spec['column']] = count
            row[f'{spec["column"]}_cap_flag'] = 1 if cap_leafs else 0
            row['_cap_any'] = max(row['_cap_any'], 1 if cap_leafs else 0)
            metadata['requests'].setdefault(month_label, {})[cat] = len(urls)
            if cap_leafs:
                metadata['cap_leafs'].setdefault(month_label, {})[cat] = cap_leafs
            print(month_label, cat, count, 'requests', len(urls), 'cap_leafs', len(cap_leafs), flush=True)

        pos_articles = neg_articles = pos_hits = neg_hits = 0
        for it in union_items.values():
            text = ' '.join([it.get('title', ''), it.get('description', ''), it.get('source', '')])
            ph = keyword_hits(text, POSITIVE_KEYWORDS)
            nh = keyword_hits(text, NEGATIVE_KEYWORDS)
            pos_hits += ph
            neg_hits += nh
            if ph > 0:
                pos_articles += 1
            if nh > 0:
                neg_articles += 1
        row['news_unique_articles_all_categories'] = len(union_items)
        row['news_positive_keyword_article_count'] = pos_articles
        row['news_negative_keyword_article_count'] = neg_articles
        row['news_positive_keyword_hits'] = pos_hits
        row['news_negative_keyword_hits'] = neg_hits
        row['news_sentiment_net_article_count'] = pos_articles - neg_articles
        row['news_sentiment_net_keyword_hits'] = pos_hits - neg_hits
        row['any_rss_cap_leaf_flag'] = row.pop('_cap_any')
        rows.append(row)

    fieldnames = ['month']
    for spec in CATEGORIES.values():
        fieldnames.append(spec['column'])
        fieldnames.append(f'{spec["column"]}_cap_flag')
    fieldnames += [
        'news_unique_articles_all_categories',
        'news_positive_keyword_article_count',
        'news_negative_keyword_article_count',
        'news_positive_keyword_hits',
        'news_negative_keyword_hits',
        'news_sentiment_net_article_count',
        'news_sentiment_net_keyword_hits',
        'any_rss_cap_leaf_flag',
    ]

    with OUT_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    META_JSON.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {OUT_CSV} rows={len(rows)}')
    print(f'Wrote {META_JSON}')


if __name__ == '__main__':
    main()
