#!/usr/bin/env python3
"""Build monthly exogenous calendar/event variables for Cass demand modeling.

Inputs downloaded from public endpoints:
- MCST regional festival ZIP/XLSX files (2020-2025)
- KBO official Schedule.asmx endpoint (monthly regular/postseason schedule)
- Python holidays package for Korea public holidays (official holiday rules incl. substitutes)
"""
from __future__ import annotations

import calendar
import datetime as dt
import io
import json
import math
import os
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import holidays
import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[2]
EVENT_SRC = BASE / "sources" / "events"
EXTRACT_DIR = EVENT_SRC / "extracted"
OUT_CSV = BASE / "data" / "exog_events_calendar_monthly.csv"
KBO_RAW_JSON = EVENT_SRC / "kbo_monthly_schedule_counts_2020_2025.json"
FESTIVAL_MONTHLY_CSV = EVENT_SRC / "mcst_festival_monthly_counts_2020_2025.csv"

MONTHS = pd.period_range("2020-01", "2025-12", freq="M")
YEARS = range(2020, 2026)


def month_start_end(period: pd.Period) -> tuple[dt.date, dt.date]:
    start = dt.date(period.year, period.month, 1)
    end = dt.date(period.year, period.month, calendar.monthrange(period.year, period.month)[1])
    return start, end


def daterange(a: dt.date, b: dt.date):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def ensure_mcst_festival_files() -> list[Path]:
    EVENT_SRC.mkdir(parents=True, exist_ok=True)
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    base_url = "https://www.mcst.go.kr/servlets/eduport/front/upload/UplDownloadFile"
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.mcst.go.kr/site/s_culture/festival/festivalList.jsp",
    })
    for year in YEARS:
        zpath = EVENT_SRC / f"{year}_festival.zip"
        if not zpath.exists() or zpath.stat().st_size < 1000:
            params = {
                "pFileName": f"{year}_festival.zip",
                "pRealName": f"{year}_festival.zip",
                "pPath": "PORTAL.DOCUMENT.UPLOAD",
                "pFlag": "",
            }
            r = session.get(base_url, params=params, timeout=60)
            r.raise_for_status()
            zpath.write_bytes(r.content)
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(EXTRACT_DIR)
    return sorted(EXTRACT_DIR.glob("*.xlsx"))


def detect_year_from_name(path: Path) -> int:
    s = path.name
    m = re.search(r"20\d{2}", s)
    if m:
        return int(m.group(0))
    if s.startswith("21") or "21년" in s:
        return 2021
    raise ValueError(f"Cannot infer year from {path}")


def normalize_text(x: Any) -> str:
    if pd.isna(x):
        return ""
    return str(x).replace("\u3000", " ").strip()


def find_header_and_cols(raw: pd.DataFrame) -> tuple[int, dict[str, int]] | None:
    for i in range(min(len(raw), 15)):
        vals = [normalize_text(v) for v in raw.iloc[i].tolist()]
        if any("축제명" in v for v in vals) and any("개최" in v and "기간" in v for v in vals):
            cols: dict[str, int] = {}
            for j, v in enumerate(vals):
                vv = v.replace("\n", "")
                if "축제명" in vv and "name" not in cols:
                    cols["name"] = j
                if "개최" in vv and "기간" in vv and "date" not in cols:
                    cols["date"] = j
                if ("축제유형" in vv or "축제 유형" in vv) and "type" not in cols:
                    cols["type"] = j
                if ("개최방식" in vv or "개최 방식" in vv) and "mode" not in cols:
                    cols["mode"] = j
                if "개최여부" in vv and "status" not in cols:
                    cols["status"] = j
                if ("광역" in vv or "시도명" in vv) and "sido" not in cols:
                    cols["sido"] = j
            if "name" in cols and "date" in cols:
                return i, cols
    return None


def parse_int_cell(x: Any) -> int | None:
    s = normalize_text(x)
    s = re.sub(r"[^0-9]", "", s)
    return int(s) if s else None


def month_only_to_range(year: int, month: int) -> tuple[dt.date, dt.date, bool]:
    return (dt.date(year, month, 1), dt.date(year, month, calendar.monthrange(year, month)[1]), True)


def parse_festival_period(text: str, year: int) -> tuple[dt.date | None, dt.date | None, bool, str]:
    """Parse Korean festival period strings into approximate start/end dates.

    Returns (start, end, is_vague, parse_note). If day is unavailable, month-level
    coverage is used and flagged vague. Cross-year ranges are not expected here.
    """
    orig = normalize_text(text)
    if not orig or orig.lower() == "nan":
        return None, None, True, "empty"
    s = orig
    s = s.replace("∼", "~").replace("～", "~").replace("-", "~")
    s = re.sub(r"\s+", "", s)
    # Remove duration/expected annotations that commonly confuse parsing.
    s = re.sub(r"\([^)]*(?:일간|예정|개최|온라인|비대면|대면|동안|간)[^)]*\)", "", s)
    s = s.replace("년도", "년")
    # Normalize Korean date markers to dots where possible.
    s_norm = s.replace("년", ".").replace("월", ".").replace("일", ".")
    s_norm = re.sub(r"\.{2,}", ".", s_norm)

    # Month-only ranges such as 9월말~10월초 / 9월~10월.
    month_nums = [int(m) for m in re.findall(r"(?<!\d)(1[0-2]|0?[1-9])월", orig)]
    if len(month_nums) >= 2 and not re.search(r"\d{1,2}\s*[\.월]\s*\d{1,2}", orig):
        sm, em = month_nums[0], month_nums[1]
        return dt.date(year, sm, 1), dt.date(year, em, calendar.monthrange(year, em)[1]), True, "month_range_vague"
    if len(month_nums) == 1 and not re.search(r"\d{1,2}\s*[\.월]\s*\d{1,2}", orig):
        a, b, _ = month_only_to_range(year, month_nums[0])
        return a, b, True, "month_only_vague"

    # Explicit full dates: yyyy.mm.dd, yy.mm.dd, mm.dd.
    # Use the first two date-like tokens. For end token with missing month, infer from start.
    tokens = []
    for part in re.split(r"~|부터|까지|,|/", s_norm):
        if not part:
            continue
        nums = [int(n) for n in re.findall(r"\d+", part)]
        if len(nums) >= 3:
            yy, mm, dd = nums[0], nums[1], nums[2]
            if yy < 100:
                yy += 2000
            tokens.append((yy, mm, dd))
        elif len(nums) >= 2:
            mm, dd = nums[0], nums[1]
            tokens.append((year, mm, dd))
        elif len(nums) == 1:
            # Bare end day; month will be inferred later.
            tokens.append((None, None, nums[0]))
    valid = []
    for yy, mm, dd in tokens:
        if mm is None:
            valid.append((yy, mm, dd))
            continue
        if 1 <= mm <= 12 and 1 <= dd <= 31:
            try:
                valid.append((yy, mm, min(dd, calendar.monthrange(yy, mm)[1])))
            except Exception:
                pass
    if valid:
        sy, sm, sd = valid[0]
        if sy is None or sm is None:
            return None, None, True, "unparsed"
        start = dt.date(sy, sm, min(sd, calendar.monthrange(sy, sm)[1]))
        if len(valid) >= 2:
            ey, em, ed = valid[1]
            if ey is None:
                ey = sy
            if em is None:
                em = sm
                # If end day appears less than start day and this is near year-end, infer next month.
                if ed < sd:
                    em = sm + 1
                    if em == 13:
                        em, ey = 1, sy + 1
            end = dt.date(ey, em, min(ed, calendar.monthrange(ey, em)[1]))
        else:
            end = start
        if end < start:
            end = start
        return start, end, False, "exact_or_partial"

    # Fallback: detect numeric month followed by vague Korean terms.
    m = re.search(r"(?<!\d)(1[0-2]|0?[1-9])(?:월|\.)", orig)
    if m:
        a, b, _ = month_only_to_range(year, int(m.group(1)))
        return a, b, True, "month_detected_vague"
    return None, None, True, "unparsed"


def month_overlap_days(start: dt.date, end: dt.date) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for d in daterange(start, end):
        if 2020 <= d.year <= 2025:
            out[f"{d.year:04d}-{d.month:02d}"] += 1
    return out


def festival_rows_from_xlsx(path: Path) -> list[dict[str, Any]]:
    year = detect_year_from_name(path)
    xl = pd.ExcelFile(path)
    detail_sheets = []
    if year in (2020, 2021):
        detail_sheets = [s for s in xl.sheet_names if s != "총괄표"]
    else:
        detail_sheets = [s for s in xl.sheet_names if "세부" in s or "조사" in s]
        if not detail_sheets:
            detail_sheets = xl.sheet_names[1:]
    rows: list[dict[str, Any]] = []
    for sheet in detail_sheets:
        raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
        detected = find_header_and_cols(raw)
        if not detected:
            continue
        header_idx, cols = detected
        subheader_vals = [normalize_text(v) for v in raw.iloc[header_idx + 1].tolist()] if header_idx + 1 < len(raw) else []
        dc0 = cols["date"]
        split_date_format = (
            dc0 + 5 < len(subheader_vals)
            and "시작" in subheader_vals[dc0]
            and "종료" in subheader_vals[dc0 + 3]
        )
        for ridx in range(header_idx + 1, len(raw)):
            row = raw.iloc[ridx]
            name = normalize_text(row.iloc[cols["name"]])
            period = normalize_text(row.iloc[cols["date"]])
            if not name or name in {"축제명", "<예시>"} or name.startswith("*"):
                continue
            if not period or period in {"개최기간", "<예시>"}:
                continue
            ftype = normalize_text(row.iloc[cols.get("type", -1)]) if "type" in cols else ""
            mode = normalize_text(row.iloc[cols.get("mode", -1)]) if "mode" in cols else ""
            status = normalize_text(row.iloc[cols.get("status", -1)]) if "status" in cols else ""
            sido = normalize_text(row.iloc[cols.get("sido", -1)]) if "sido" in cols else sheet

            # 2025-format files split 개최기간 into 시작일/종료일 year-month-day columns.
            # Detect numeric cells immediately to the right of the 개최기간 header.
            start = end = None
            vague = True
            parse_note = ""
            dc = cols["date"]
            if split_date_format and dc + 5 < len(row):
                sy = parse_int_cell(row.iloc[dc])
                sm = parse_int_cell(row.iloc[dc + 1])
                sd = parse_int_cell(row.iloc[dc + 2])
                ey = parse_int_cell(row.iloc[dc + 3])
                em = parse_int_cell(row.iloc[dc + 4])
                ed = parse_int_cell(row.iloc[dc + 5])
                if sy and sm and ey and em and 1 <= sm <= 12 and 1 <= em <= 12:
                    if sd and ed:
                        start = dt.date(sy, sm, min(sd, calendar.monthrange(sy, sm)[1]))
                        end = dt.date(ey, em, min(ed, calendar.monthrange(ey, em)[1]))
                        vague = False
                        parse_note = "split_date_exact"
                    else:
                        start = dt.date(sy, sm, 1)
                        end = dt.date(ey, em, calendar.monthrange(ey, em)[1])
                        vague = True
                        parse_note = "split_month_vague"
                    period = f"{sy}.{sm}.{sd or ''}~{ey}.{em}.{ed or ''}"
            if start is None or end is None:
                start, end, vague, parse_note = parse_festival_period(period, year)
            if start is None or end is None:
                # Try status field for 2020 rows with revised online dates in 개최여부.
                start, end, vague, parse_note = parse_festival_period(status, year)
            if start is None or end is None:
                continue
            text_all = " ".join([name, period, ftype, mode, status])
            cancelled = bool(re.search(r"취소|미개최|취소예정", text_all))
            online_only = bool(re.search(r"비대면|온라인", text_all)) and not bool(re.search(r"현장|대면|오프라인|혼합|병행", text_all))
            offline_or_hybrid = (not cancelled) and (not online_only)
            beer = bool(re.search(r"맥주|비어|beer|치맥|수제맥주", text_all, flags=re.I))
            rows.append({
                "source_file": path.name,
                "source_sheet": sheet,
                "year": year,
                "sido": sido,
                "festival_name": name,
                "festival_type": ftype,
                "period_raw": period,
                "mode_raw": mode,
                "status_raw": status,
                "start_date": start,
                "end_date": end,
                "date_is_vague": vague,
                "parse_note": parse_note,
                "is_cancelled_or_not_held": cancelled,
                "is_online_only_inferred": online_only,
                "is_offline_or_hybrid_inferred": offline_or_hybrid,
                "is_beer_festival_keyword": beer,
            })
    return rows


def build_festival_monthly() -> pd.DataFrame:
    files = ensure_mcst_festival_files()
    all_rows = []
    for path in files:
        all_rows.extend(festival_rows_from_xlsx(path))
    monthly: dict[str, dict[str, Any]] = {str(p): defaultdict(int) for p in MONTHS}
    for r in all_rows:
        overlaps = month_overlap_days(r["start_date"], r["end_date"])
        for month, days in overlaps.items():
            if month not in monthly:
                continue
            monthly[month]["regional_festival_count_planned"] += 1
            # For vague month-level periods, count one proxy day per covered month to avoid overstating month-long estimates.
            est_days = 1 if r["date_is_vague"] else days
            monthly[month]["regional_festival_days_est"] += est_days
            if r["is_offline_or_hybrid_inferred"]:
                monthly[month]["regional_festival_offline_or_hybrid_count"] += 1
                monthly[month]["regional_festival_offline_or_hybrid_days_est"] += est_days
            if r["date_is_vague"]:
                monthly[month]["regional_festival_vague_date_count"] += 1
            if r["is_beer_festival_keyword"]:
                monthly[month]["beer_festival_count_keyword"] += 1
                monthly[month]["beer_festival_days_est_keyword"] += est_days
                if r["is_offline_or_hybrid_inferred"]:
                    monthly[month]["beer_festival_offline_or_hybrid_count_keyword"] += 1
    df = pd.DataFrame([{"month": m, **dict(vals)} for m, vals in monthly.items()])
    for c in [
        "regional_festival_count_planned", "regional_festival_days_est",
        "regional_festival_offline_or_hybrid_count", "regional_festival_offline_or_hybrid_days_est",
        "regional_festival_vague_date_count", "beer_festival_count_keyword",
        "beer_festival_days_est_keyword", "beer_festival_offline_or_hybrid_count_keyword",
    ]:
        if c not in df:
            df[c] = 0
        df[c] = df[c].fillna(0).astype(int)
    # Save detail for auditability.
    detail = pd.DataFrame(all_rows)
    if not detail.empty:
        detail2 = detail.copy()
        detail2["start_date"] = detail2["start_date"].astype(str)
        detail2["end_date"] = detail2["end_date"].astype(str)
        detail2.to_csv(EVENT_SRC / "mcst_festival_parsed_detail_2020_2025.csv", index=False, encoding="utf-8-sig")
    df.to_csv(FESTIVAL_MONTHLY_CSV, index=False, encoding="utf-8-sig")
    return df


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_kbo_month(year: int, month: int, srid: str) -> dict[str, Any]:
    url = "https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList"
    data = {"leId": 1, "srIdList": srid, "seasonId": str(year), "gameMonth": f"{month:02d}", "teamId": ""}
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.koreabaseball.com/Schedule/Schedule.aspx"}
    r = requests.post(url, data=data, headers=headers, timeout=30)
    r.raise_for_status()
    j = r.json()
    rows = j.get("rows", [])
    game_count = 0
    game_dates: set[str] = set()
    cancelled_like = 0
    for item in rows:
        cells = item.get("row", [])
        texts = [strip_html(c.get("Text", "")) for c in cells]
        html = " ".join(c.get("Text", "") or "" for c in cells)
        joined = " ".join(texts)
        # KBO rows are one game per row. A played/scheduled game usually has a gameId link.
        # Exclude clearly canceled/no-game rows when present.
        if re.search(r"취소|우천취소|경기취소|노게임", joined):
            cancelled_like += 1
            continue
        # Completed KBO rows expose GameCenter links with gameId/gameDate.
        # Rows without gameId are usually postponed/canceled placeholder rows; do not count them as played games.
        if "gameId=" in html:
            game_count += 1
            m = re.search(r"gameDate=(\d{8})", html)
            if m:
                game_dates.add(m.group(1))
    return {"games": game_count, "game_days": len(game_dates), "cancelled_like_rows": cancelled_like, "raw_rows": len(rows)}


def build_kbo_monthly() -> pd.DataFrame:
    records = []
    cache: dict[str, Any] = {}
    for p in MONTHS:
        y, m = p.year, p.month
        rec = {"month": str(p)}
        for label, srid in [("regular", "0,9,6"), ("postseason", "3,4,5,7")]:
            key = f"{y}-{m:02d}-{label}"
            try:
                val = get_kbo_month(y, m, srid)
            except Exception as e:
                val = {"games": 0, "game_days": 0, "cancelled_like_rows": 0, "raw_rows": 0, "error": str(e)}
            cache[key] = val
            rec[f"kbo_{label}_games"] = int(val.get("games", 0))
            rec[f"kbo_{label}_game_days"] = int(val.get("game_days", 0))
        records.append(rec)
    KBO_RAW_JSON.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    df = pd.DataFrame(records)
    df["is_kbo_regular_season"] = (df["kbo_regular_games"] > 0).astype(int)
    df["is_kbo_postseason"] = (df["kbo_postseason_games"] > 0).astype(int)
    return df


def build_holiday_monthly() -> pd.DataFrame:
    kr_holidays = holidays.KR(years=list(YEARS), observed=True, language="ko")
    records = []
    for p in MONTHS:
        start, end = month_start_end(p)
        month_days = list(daterange(start, end))
        holiday_dates = [d for d in month_days if d in kr_holidays]
        weekend_dates = [d for d in month_days if d.weekday() >= 5]
        nonwork = set(holiday_dates) | set(weekend_dates)
        # Include one-week margins for cross-month long-weekend runs.
        margin_start = start - dt.timedelta(days=7)
        margin_end = end + dt.timedelta(days=7)
        all_nonwork = {d for d in daterange(margin_start, margin_end) if d.weekday() >= 5 or d in kr_holidays}
        longest = 0
        long_days_in_month = 0
        d = margin_start
        while d <= margin_end:
            if d in all_nonwork:
                seq = []
                while d <= margin_end and d in all_nonwork:
                    seq.append(d)
                    d += dt.timedelta(days=1)
                if any(start <= x <= end for x in seq):
                    longest = max(longest, len(seq))
                    if len(seq) >= 3:
                        long_days_in_month += sum(1 for x in seq if start <= x <= end)
            else:
                d += dt.timedelta(days=1)
        records.append({
            "month": str(p),
            "year": p.year,
            "days_in_month": len(month_days),
            "weekend_days": len(weekend_dates),
            "public_holiday_count_kr": len(holiday_dates),
            "public_holiday_weekday_count_kr": sum(1 for d in holiday_dates if d.weekday() < 5),
            "nonworking_days_weekend_or_holiday": len(nonwork),
            "longest_consecutive_nonwork_days": longest,
            "long_weekend_3plus_days_in_month": long_days_in_month,
            "holiday_names_kr": "; ".join(f"{d.isoformat()} {kr_holidays[d]}" for d in holiday_dates),
        })
    return pd.DataFrame(records)


def event_overlap_days(start: str, end: str) -> dict[str, int]:
    a = dt.date.fromisoformat(start)
    b = dt.date.fromisoformat(end)
    return month_overlap_days(a, b)


def build_major_sports_monthly() -> pd.DataFrame:
    events = [
        {"name": "Tokyo 2020 Summer Olympics (held 2021)", "kind": "olympics", "start": "2021-07-23", "end": "2021-08-08"},
        {"name": "Beijing 2022 Winter Olympics", "kind": "olympics", "start": "2022-02-04", "end": "2022-02-20"},
        {"name": "FIFA World Cup Qatar 2022", "kind": "fifa_world_cup", "start": "2022-11-20", "end": "2022-12-18"},
        {"name": "Hangzhou 2022 Asian Games (held 2023)", "kind": "asian_games", "start": "2023-09-23", "end": "2023-10-08"},
        {"name": "Paris 2024 Summer Olympics", "kind": "olympics", "start": "2024-07-26", "end": "2024-08-11"},
    ]
    records = {str(p): defaultdict(int) for p in MONTHS}
    names = defaultdict(list)
    for ev in events:
        for month, days in event_overlap_days(ev["start"], ev["end"]).items():
            if month not in records:
                continue
            records[month]["sports_major_event_days"] += days
            records[month][f"{ev['kind']}_days"] += days
            names[month].append(ev["name"])
    out = []
    for p in MONTHS:
        month = str(p)
        rec = {"month": month}
        for c in ["sports_major_event_days", "olympics_days", "fifa_world_cup_days", "asian_games_days"]:
            rec[c] = int(records[month].get(c, 0))
        rec["is_sports_major_event_month"] = int(rec["sports_major_event_days"] > 0)
        rec["sports_major_event_names"] = "; ".join(names.get(month, []))
        out.append(rec)
    return pd.DataFrame(out)


def build_calendar() -> pd.DataFrame:
    h = build_holiday_monthly()
    kbo = build_kbo_monthly()
    sports = build_major_sports_monthly()
    fest = build_festival_monthly()
    df = h.merge(kbo, on="month", how="left").merge(sports, on="month", how="left").merge(fest, on="month", how="left")
    df["is_summer_peak_jun_aug"] = df["month"].str[5:7].astype(int).isin([6, 7, 8]).astype(int)
    df["is_vacation_peak_jul_aug"] = df["month"].str[5:7].astype(int).isin([7, 8]).astype(int)
    df["events_data_source_note"] = (
        "KR holidays from python-holidays/KR observed rules; KBO official Schedule.asmx; "
        "MCST regional festival ZIP/XLSX files; global sports event dates hand-coded from official event calendars."
    )
    # Column order.
    cols = [
        "month", "year", "days_in_month", "weekend_days",
        "public_holiday_count_kr", "public_holiday_weekday_count_kr", "nonworking_days_weekend_or_holiday",
        "longest_consecutive_nonwork_days", "long_weekend_3plus_days_in_month", "holiday_names_kr",
        "is_summer_peak_jun_aug", "is_vacation_peak_jul_aug",
        "kbo_regular_games", "kbo_regular_game_days", "is_kbo_regular_season",
        "kbo_postseason_games", "kbo_postseason_game_days", "is_kbo_postseason",
        "sports_major_event_days", "is_sports_major_event_month", "olympics_days", "fifa_world_cup_days", "asian_games_days", "sports_major_event_names",
        "regional_festival_count_planned", "regional_festival_days_est", "regional_festival_offline_or_hybrid_count", "regional_festival_offline_or_hybrid_days_est", "regional_festival_vague_date_count",
        "beer_festival_count_keyword", "beer_festival_days_est_keyword", "beer_festival_offline_or_hybrid_count_keyword",
        "events_data_source_note",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = 0 if c not in {"holiday_names_kr", "sports_major_event_names", "events_data_source_note"} else ""
    out = df[cols].copy()
    for text_col in ["holiday_names_kr", "sports_major_event_names", "events_data_source_note"]:
        out[text_col] = out[text_col].fillna("").replace("", "none")
    return out


def main() -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df = build_calendar()
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"Wrote {OUT_CSV} rows={len(df)} cols={len(df.columns)}")
    print(df.head().to_string())
    print(df.tail().to_string())


if __name__ == "__main__":
    main()
