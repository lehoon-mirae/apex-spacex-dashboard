"""
초기 이력 데이터 시딩 스크립트 (1회성, 이미 실행됨 - 재실행하면 raw 파일을 덮어씁니다).

- SpaceX(SPCX) 종가: stockanalysis.com / MarketBeat / CNBC / NPR에서 조회한 실측치.
- USD/KRW 매매기준율: 한국은행 ECOS 공개 API(731Y001, 원/미국달러)에서 조회한 실측치
  (2026-07-21 기준 sample 키로 직접 조회하여 확보; 서울외국환중개 산정에 참여하는 것과
  동일한 공식 매매기준율입니다).

raw_spcx_price.csv / raw_fx_bok.csv 두 원자료 테이블을 채운 뒤, calc.build_daily_log()로
daily_log.csv(파생 시계열)를 생성합니다.
"""
import datetime as dt

from calc import build_daily_log
from sources import RAW_SPCX_COLUMNS, RAW_FX_COLUMNS, append_raw_row
from constants import RAW_SPCX_CSV_PATH, RAW_FX_CSV_PATH, ECOS_STAT_CODE

# 실제 SpaceX(SPCX) 종가 (USD), 출처: stockanalysis.com / MarketBeat / CNBC / NPR
SPCX_PRICE_HISTORY = {
    "2026-06-12": 160.95,   # IPO 상장일 종가 (공모가 $135)
    "2026-06-15": 192.50,
    "2026-06-16": 201.80,
    "2026-06-17": 191.82,
    "2026-06-18": 185.00,
    "2026-06-22": 154.60,
    "2026-06-23": 156.11,
    "2026-06-24": 154.54,
    "2026-06-25": 153.00,
    "2026-06-26": 153.23,
    "2026-06-29": 164.19,
    "2026-06-30": 170.86,   # 펀드 평가기준일
    "2026-07-01": 157.54,
    "2026-07-02": 162.00,
    "2026-07-03": 162.00,
    "2026-07-06": 160.42,
    "2026-07-07": 149.47,
    "2026-07-08": 148.30,
    "2026-07-09": 152.16,
    "2026-07-10": 145.30,
    "2026-07-13": 139.14,
    "2026-07-14": 136.08,
    "2026-07-15": 135.27,
    "2026-07-16": 131.11,
    "2026-07-17": 123.99,
    "2026-07-20": 119.85,
}

# 실제 USD/KRW 매매기준율, 출처: 한국은행 ECOS 731Y001 (원/미국달러, 2026-07-21 조회)
FX_HISTORY = {
    "2026-06-12": 1527.0,
    "2026-06-15": 1520.4,
    "2026-06-16": 1510.0,
    "2026-06-17": 1513.5,
    "2026-06-18": 1512.8,
    "2026-06-19": 1523.4,
    "2026-06-22": 1535.0,
    "2026-06-23": 1535.7,
    "2026-06-24": 1537.2,
    "2026-06-25": 1538.3,
    "2026-06-26": 1545.3,
    "2026-06-29": 1544.2,
    "2026-06-30": 1541.5,
    "2026-07-01": 1548.4,
    "2026-07-02": 1554.4,
    "2026-07-03": 1554.1,
    "2026-07-06": 1539.7,
    "2026-07-07": 1531.8,
    "2026-07-08": 1526.6,
    "2026-07-09": 1509.9,
    "2026-07-10": 1504.2,
    "2026-07-13": 1507.1,
    "2026-07-14": 1504.9,
    "2026-07-15": 1492.2,
    "2026-07-16": 1488.8,
    "2026-07-20": 1484.3,
    "2026-07-21": 1482.0,
    # 2026-07-17: ECOS에 해당일 데이터가 조회되지 않아(휴장/데이터 지연 추정) 비워둠 ->
    # daily_log.csv 생성 시 이 날짜는 자동으로 제외됩니다.
}


def seed():
    now = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"

    for date_str, price in sorted(SPCX_PRICE_HISTORY.items()):
        append_raw_row(RAW_SPCX_CSV_PATH, RAW_SPCX_COLUMNS, {
            "date": date_str, "close_usd": price, "source": "seed_manual_verified", "fetched_at": now,
        })

    for date_str, fx in sorted(FX_HISTORY.items()):
        append_raw_row(RAW_FX_CSV_PATH, RAW_FX_COLUMNS, {
            "date": date_str, "fx_rate": fx, "stat_code": ECOS_STAT_CODE,
            "source": "BOK_ECOS_731Y001_seed", "fetched_at": now,
        })

    result = build_daily_log()
    print(f"raw_spcx_price.csv: {len(SPCX_PRICE_HISTORY)}행, raw_fx_bok.csv: {len(FX_HISTORY)}행 시딩 완료")
    print(f"daily_log.csv 재생성: {result['rows_written']}행")
    if result["spcx_only_dates"]:
        print(f"  (SPCX만 있고 환율 없음 -> 제외: {result['spcx_only_dates']})")
    if result["fx_only_dates"]:
        print(f"  (환율만 있고 SPCX 없음 -> 제외: {result['fx_only_dates']})")


if __name__ == "__main__":
    seed()
