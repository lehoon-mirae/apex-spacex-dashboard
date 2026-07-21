"""
Raw 데이터 수집 소스.

- SpaceX(SPCX) 종가: Yahoo Finance(yfinance), 실패 시 stooq.com CSV로 폴백.
- USD/KRW 환율: 한국은행 ECOS 공개 API (원/미국달러 매매기준율, 통계코드 731Y001).
  서울외국환중개(smbs.biz)는 이용약관상 크롤러·스크래퍼 등 자동 수집을 금지하고 있어
  (위반 시 저작권법 제136조 형사처벌 조항 명시) 자동화 대상에서 제외했습니다.
  ECOS는 서울외국환중개가 산정에 참여하는 것과 동일한 공식 매매기준율을 무료로 제공하는
  합법적인 공개 API입니다.
"""
import csv
import datetime as dt
import json
import os
import urllib.request

from constants import (
    RAW_SPCX_CSV_PATH, RAW_FX_CSV_PATH, SPCX_TICKER,
    ECOS_BASE_URL, ECOS_STAT_CODE, ECOS_ITEM_CODE, ECOS_API_KEY_ENV,
)

RAW_SPCX_COLUMNS = ["date", "close_usd", "source", "fetched_at"]
RAW_FX_COLUMNS = ["date", "fx_rate", "stat_code", "source", "fetched_at"]


def _now_iso():
    return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def load_raw_dates(path, date_col="date"):
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8-sig") as f:
        return {row[date_col] for row in csv.DictReader(f)}


def append_raw_row(path, columns, row: dict):
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        if not file_exists:
            w.writeheader()
        w.writerow(row)


# ------------------------------------------------------------------
# SpaceX(SPCX) 종가
# ------------------------------------------------------------------
def fetch_spcx_price_yfinance():
    import yfinance as yf

    df = yf.Ticker(SPCX_TICKER).history(period="5d")
    if df.empty:
        raise RuntimeError("yfinance: SPCX 시세를 가져오지 못했습니다.")
    last_date = df.index[-1].strftime("%Y-%m-%d")
    last_close = float(df["Close"].iloc[-1])
    return last_date, last_close


def fetch_spcx_price_stooq_fallback():
    import io
    import pandas as pd

    req = urllib.request.Request(
        "https://stooq.com/q/d/l/?s=spcx.us&i=d", headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        df = pd.read_csv(io.StringIO(resp.read().decode("utf-8")))
    df = df.dropna()
    last_row = df.iloc[-1]
    return str(last_row["Date"]), float(last_row["Close"])


def fetch_spcx_price():
    try:
        date_str, price = fetch_spcx_price_yfinance()
        return date_str, price, "yfinance"
    except Exception:
        date_str, price = fetch_spcx_price_stooq_fallback()
        return date_str, price, "stooq_fallback"


# ------------------------------------------------------------------
# USD/KRW 매매기준율 (한국은행 ECOS)
# ------------------------------------------------------------------
def fetch_fx_ecos(days_back=10):
    """
    최근 days_back일간의 매매기준율 시계열을 [(date_str, value), ...] 로 반환합니다.
    ECOS_API_KEY 환경변수가 없으면 한국은행이 제공하는 공개 샘플 키('sample')로 폴백합니다
    (샘플 키는 1회 최대 10건 제한 - 무료 개인 키는 https://ecos.bok.or.kr 에서 즉시 발급 가능).
    """
    api_key = os.environ.get(ECOS_API_KEY_ENV, "sample")
    end = dt.date.today()
    start = end - dt.timedelta(days=days_back)
    count = 10 if api_key == "sample" else 100

    url = (
        f"{ECOS_BASE_URL}/{api_key}/json/kr/1/{count}/{ECOS_STAT_CODE}/D/"
        f"{start:%Y%m%d}/{end:%Y%m%d}/{ECOS_ITEM_CODE}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if "StatisticSearch" not in data:
        msg = data.get("RESULT", {}).get("MESSAGE", str(data))
        raise RuntimeError(f"ECOS API 오류: {msg}")

    out = []
    for row in data["StatisticSearch"]["row"]:
        d = row["TIME"]  # YYYYMMDD
        date_str = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        out.append((date_str, float(row["DATA_VALUE"])))
    return out


def update_raw_spcx():
    """최신 SPCX 종가를 raw_spcx_price.csv에 추가합니다 (이미 있는 날짜는 건너뜀)."""
    date_str, price, src = fetch_spcx_price()
    existing = load_raw_dates(RAW_SPCX_CSV_PATH)
    if date_str in existing:
        return None
    row = {"date": date_str, "close_usd": round(price, 4), "source": src, "fetched_at": _now_iso()}
    append_raw_row(RAW_SPCX_CSV_PATH, RAW_SPCX_COLUMNS, row)
    return row


def update_raw_fx(days_back=10):
    """ECOS에서 최근 매매기준율을 가져와 raw_fx_bok.csv에 없는 날짜만 추가합니다."""
    series = fetch_fx_ecos(days_back=days_back)
    existing = load_raw_dates(RAW_FX_CSV_PATH)
    added = []
    for date_str, value in series:
        if date_str in existing:
            continue
        row = {
            "date": date_str, "fx_rate": value, "stat_code": ECOS_STAT_CODE,
            "source": "BOK_ECOS_731Y001", "fetched_at": _now_iso(),
        }
        append_raw_row(RAW_FX_CSV_PATH, RAW_FX_COLUMNS, row)
        existing.add(date_str)
        added.append(row)
    return added
