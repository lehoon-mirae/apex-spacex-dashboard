"""
공통 손익 계산 함수.
fetch_daily_data.py 와 app.py 양쪽에서 동일한 로직을 사용하도록 분리했습니다.
"""
import csv

from constants import IPO_PRICE_USD, ACQ_FX_RATE, MIRAE_SPCX_SHARES, RAW_SPCX_CSV_PATH, RAW_FX_CSV_PATH, DATA_CSV_PATH


def compute_row(date_str: str, spcx_price: float, fx_rate: float, source: str = "actual") -> dict:
    """
    주어진 날짜의 SpaceX 종가(USD)와 환율(원/USD)로 미래생명 관점 손익 지표를 계산합니다.

    - 평가금액/손익은 미래생명 실제 보유주식수(575,111.21주) 기준입니다.
    - 취득원가는 공모가($135) x 취득시점 환율(1,519.8원)로 고정합니다.
    - 주가상승효과/외화환산손익 분해는 K-IFRS 외화환산 방식과 동일합니다.
      주가상승효과 = (평가금액USD - 투자원가USD) x 취득환율(고정)
      외화환산손익 = 평가금액USD x (당일환율 - 취득환율)
    """
    shares = MIRAE_SPCX_SHARES
    cost_usd = shares * IPO_PRICE_USD
    cost_krw = cost_usd * ACQ_FX_RATE

    value_usd = shares * spcx_price
    value_krw = value_usd * fx_rate

    gain_usd = value_usd - cost_usd
    gain_krw = value_krw - cost_krw

    ret_usd = gain_usd / cost_usd
    ret_krw = gain_krw / cost_krw

    price_effect_krw = (value_usd - cost_usd) * ACQ_FX_RATE
    fx_effect_krw = value_usd * (fx_rate - ACQ_FX_RATE)

    pct_vs_ipo = spcx_price / IPO_PRICE_USD - 1

    return {
        "date": date_str,
        "spcx_price_usd": round(spcx_price, 4),
        "fx_rate": round(fx_rate, 2),
        "pct_vs_ipo": round(pct_vs_ipo, 6),
        "value_usd": round(value_usd, 2),
        "value_krw": round(value_krw, 0),
        "cost_usd": round(cost_usd, 2),
        "cost_krw": round(cost_krw, 0),
        "gain_usd": round(gain_usd, 2),
        "gain_krw": round(gain_krw, 0),
        "return_usd": round(ret_usd, 6),
        "return_krw": round(ret_krw, 6),
        "price_effect_krw": round(price_effect_krw, 0),
        "fx_effect_krw": round(fx_effect_krw, 0),
        "source": source,
    }


CSV_COLUMNS = [
    "date", "spcx_price_usd", "fx_rate", "pct_vs_ipo",
    "value_usd", "value_krw", "cost_usd", "cost_krw",
    "gain_usd", "gain_krw", "return_usd", "return_krw",
    "price_effect_krw", "fx_effect_krw", "source",
]

# 기본 시나리오 스텝: 공모가 대비 등락률(%) 범위. Excel 분석과 동일한 격자를 사용합니다.
DEFAULT_SCENARIO_PCTS = [-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0]


def build_scenario_table(fx_rate: float, pcts=None) -> list:
    """
    SpaceX 주가 등락률(공모가 대비) 격자에 대해 미래생명 손익/수익률을 일괄 계산합니다.
    환율(fx_rate)은 시나리오 전체에 고정 적용되며(주가 변동 효과만 순수하게 보기 위함),
    호출부에서 "최신 실측 환율"이나 "사용자 지정 환율" 등을 자유롭게 넘길 수 있는
    구조로 분리했습니다 (대시보드 슬라이더, 배치 스크립트, 엑셀 재생성 등에서 공용 재사용).
    """
    pcts = pcts if pcts is not None else DEFAULT_SCENARIO_PCTS
    rows = []
    for pct in pcts:
        price = IPO_PRICE_USD * (1 + pct)
        label = "공모가 (기준)" if pct == 0 else f"공모가 대비 {pct*100:+.0f}%"
        row = compute_row(label, price, fx_rate, source="scenario")
        row["pct_vs_ipo"] = round(pct, 6)  # 라벨 대신 정확한 격자값으로 고정
        rows.append(row)
    return rows


def _read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_daily_log(spcx_path=RAW_SPCX_CSV_PATH, fx_path=RAW_FX_CSV_PATH, out_path=DATA_CSV_PATH):
    """
    raw_spcx_price.csv(원자료) x raw_fx_bok.csv(원자료)를 날짜 기준으로 내부조인(inner join)하여
    daily_log.csv(파생 데이터, 시계열)를 다시 생성합니다.

    - 두 원자료 모두 존재하는 날짜만 계산됩니다 (한쪽만 있는 날짜는 자동으로 건너뜀 -
      예: 한국 휴장일에 ECOS 데이터가 없거나, 미국 휴장일에 SPCX 종가가 없는 경우).
    - raw 파일은 append-only 원자료이며, daily_log.csv는 raw로부터 항상 재현 가능한
      파생 결과물입니다 (raw를 정정/보강하면 이 함수를 다시 실행해 반영).
    """
    spcx_rows = {r["date"]: float(r["close_usd"]) for r in _read_csv(spcx_path)}
    fx_rows = {r["date"]: float(r["fx_rate"]) for r in _read_csv(fx_path)}

    common_dates = sorted(set(spcx_rows) & set(fx_rows))
    out_rows = [compute_row(d, spcx_rows[d], fx_rows[d], source="auto") for d in common_dates]

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for row in out_rows:
            w.writerow(row)

    skipped_spcx_only = sorted(set(spcx_rows) - set(fx_rows))
    skipped_fx_only = sorted(set(fx_rows) - set(spcx_rows))
    return {
        "rows_written": len(out_rows),
        "spcx_only_dates": skipped_spcx_only,
        "fx_only_dates": skipped_fx_only,
    }
