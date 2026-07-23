"""
배포용(GitHub Pages) 정적 HTML 대시보드 생성 스크립트.

app.py(Streamlit)와 동일한 화면구성(1.주가추이 -> 2.손익현황 -> 3.손익추이 -> 4.기초데이터 -> 5.Raw데이터)을
Plotly.js(CDN) + 순수 HTML/JS로 재현한 정적 사이트를 만듭니다. 서버가 필요 없어 GitHub Pages 같은
정적 호스팅에 그대로 올릴 수 있습니다.

data/daily_log.csv, data/raw_spcx_price.csv, data/raw_fx_bok.csv, constants.py 를 읽어
값을 JSON으로 HTML에 그대로 임베드합니다 (빌드 시점 스냅샷 - GitHub Actions가 매 영업일
fetch_daily_data.py 로 데이터를 갱신한 뒤 이 스크립트를 다시 실행해 docs/index.html 을 재생성/재배포합니다).

사용법: cwd를 apex-dashboard 폴더로 맞추고 실행
    python3 generate_deploy_html.py
출력: docs/index.html (GitHub Pages가 이 폴더를 서빙하도록 설정)
"""
import csv
import json
import os
import datetime as dt

import constants as C


def _read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_monthly(daily_sorted):
    by_month = {}
    for r in daily_sorted:
        ym = r["date"][:7]
        by_month[ym] = r  # keeps overwriting -> last (max date) row per month since daily_sorted is date-ascending
    months = sorted(by_month.keys())
    rows = []
    prev_gain = None
    for i, ym in enumerate(months):
        r = by_month[ym]
        gain = float(r["gain_krw"])
        change = gain if prev_gain is None else gain - prev_gain
        rows.append({
            "year_month": ym,
            "date": r["date"],
            "spcx_price_usd": float(r["spcx_price_usd"]),
            "fx_rate": float(r["fx_rate"]),
            "value_krw": float(r["value_krw"]),
            "gain_krw": gain,
            "monthly_gain_change": change,
            "return_krw": float(r["return_krw"]),
        })
        prev_gain = gain
    return rows


def build_scenario(fx_rate):
    pcts = [-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0]
    shares = C.MIRAE_SPCX_SHARES
    cost_usd = shares * C.IPO_PRICE_USD
    cost_krw = cost_usd * C.ACQ_FX_RATE
    rows = []
    for pct in pcts:
        price = C.IPO_PRICE_USD * (1 + pct)
        value_usd = shares * price
        value_krw = value_usd * fx_rate
        gain_krw = value_krw - cost_krw
        rows.append({
            "pct": round(pct, 4), "price": round(price, 2),
            "value_krw": round(value_krw, 0), "gain_krw": round(gain_krw, 0),
            "return_krw": round(gain_krw / cost_krw, 6),
        })
    return rows


def main():
    daily = _read_csv(C.DATA_CSV_PATH)
    raw_spcx = _read_csv(C.RAW_SPCX_CSV_PATH)
    raw_fx = _read_csv(C.RAW_FX_CSV_PATH)

    daily_sorted = sorted(daily, key=lambda r: r["date"])
    latest = daily_sorted[-1] if daily_sorted else None
    prev = daily_sorted[-2] if len(daily_sorted) > 1 else latest

    row_630 = next((r for r in daily_sorted if r["date"] == C.OFFICIAL_SNAPSHOT_DATE), None)

    payload = {
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "constants": {
            "shares": C.MIRAE_SPCX_SHARES, "ipo_price": C.IPO_PRICE_USD, "acq_fx": C.ACQ_FX_RATE,
            "fund_shares": C.FUND_SPCX_SHARES, "mirae_pct": C.MIRAE_SHARE_PCT,
            "official_date": C.OFFICIAL_SNAPSHOT_DATE, "official_cost_krw": C.OFFICIAL_COST_KRW,
            "official_value_krw": C.OFFICIAL_VALUE_KRW, "official_gain_krw": C.OFFICIAL_GAIN_KRW,
            "official_fx": C.OFFICIAL_EOP_FX, "official_price": C.OFFICIAL_SPCX_PRICE,
        },
        "daily": daily_sorted,
        "monthly": build_monthly(daily_sorted),
        "raw_spcx": sorted(raw_spcx, key=lambda r: r["date"]),
        "raw_fx": sorted(raw_fx, key=lambda r: r["date"]),
        "latest": latest,
        "prev": prev,
        "row_630_gain_krw": float(row_630["gain_krw"]) if row_630 else None,
        "scenario": build_scenario(float(latest["fx_rate"])) if latest else [],
    }

    data_json = json.dumps(payload, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("__DATA_JSON__", data_json)

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"docs/index.html 생성 완료 ({len(daily_sorted)}행, 기준일 {latest['date'] if latest else 'N/A'})")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>미래생명 · APEX 펀드(SpaceX) 손익 대시보드</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 28px 32px 60px; background: #ffffff; color: #262730;
    font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", "Malgun Gothic", sans-serif;
    max-width: 1400px; margin-left: auto; margin-right: auto;
  }
  h1 { font-size: 28px; margin: 4px 0 6px; }
  .caption { color: #6b6b6b; font-size: 14px; margin-bottom: 18px; }
  hr { border: none; border-top: 1px solid #e6e6e6; margin: 26px 0; }
  h2.subheader { font-size: 21px; margin: 0 0 16px; }
  h4 { font-size: 15px; margin: 18px 0 10px; color: #31333f; }
  h5 { font-size: 13px; margin: 4px 0 8px; color: #454756; }
  .cols { display: grid; gap: 20px; }
  .cols-2 { grid-template-columns: 1fr 1fr; }
  .cols-2-3 { grid-template-columns: 4fr 3fr; }
  .cols-3-4 { grid-template-columns: 3fr 4fr; }
  @media (max-width: 900px) { .cols-2, .cols-2-3, .cols-3-4 { grid-template-columns: 1fr; } }
  .metric-row { display: flex; gap: 28px; flex-wrap: wrap; margin: 8px 0 4px; }
  .metric { min-width: 170px; }
  .metric-label { font-size: 13px; color: #6b6b6b; }
  .metric-value { font-size: 26px; font-weight: 600; margin-top: 2px; }
  .metric-delta { font-size: 13px; margin-top: 2px; }
  .metric-delta.up { color: #c62828; }
  .metric-delta.down { color: #1565c0; }
  .plot { width: 100%; height: 350px; }
  .plot-sm { width: 100%; height: 280px; }
  table.status { width: 100%; border-collapse: collapse; font-size: 14px; }
  table.status th, table.status td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #f0f0f0; }
  table.status th { color: #6b6b6b; font-weight: 600; font-size: 13px; }
  table.datatable { width: 100%; border-collapse: collapse; font-size: 13px; }
  table.datatable th, table.datatable td { padding: 6px 9px; text-align: right; border-bottom: 1px solid #f0f0f0; white-space: nowrap; }
  table.datatable th:first-child, table.datatable td:first-child { text-align: left; }
  .table-scroll { overflow-x: auto; max-height: 460px; overflow-y: auto; border: 1px solid #eee; border-radius: 6px; }
  .slider-row { display: grid; grid-template-columns: 3fr 1fr; gap: 16px; align-items: center; margin-bottom: 14px; }
  .slider-row label { font-size: 13px; color: #454756; display: block; margin-bottom: 4px; }
  input[type=range] { width: 100%; }
  input[type=number] { width: 100%; padding: 6px 8px; border: 1px solid #d5d5d8; border-radius: 6px; font-size: 14px; }
  details { border: 1px solid #eee; border-radius: 8px; padding: 10px 14px; margin-top: 14px; }
  summary { cursor: pointer; font-size: 14px; color: #31333f; }
  details p, details li { font-size: 13.5px; line-height: 1.7; color: #31333f; }
  .caption-sm { font-size: 12.5px; color: #6b6b6b; margin-top: 8px; line-height: 1.6; }
  footer { font-size: 12px; color: #8a8a8a; margin-top: 12px; line-height: 1.7; }
</style>
</head>
<body>

<h1>미래생명 · APEX 펀드(SpaceX) 손익 대시보드</h1>
<div class="caption" id="topCaption"></div>
<hr>

<!-- 1. 주가 추이 -->
<h2 class="subheader">📈 1. 주가 추이 (SpaceX 주가 및 환율 변동 추이)</h2>
<div class="cols cols-2">
  <div><h4>SpaceX 주가 (USD)</h4><div class="plot" id="plotPrice"></div></div>
  <div><h4>USD/KRW 환율</h4><div class="plot" id="plotFx"></div></div>
</div>
<hr>

<!-- 2. 손익 현황 -->
<h2 class="subheader">💰 2. 손익 현황 (최신 현황 및 시나리오)</h2>
<h4>[최신 시장 지표]</h4>
<div class="metric-row" id="marketMetrics"></div>

<h4>[최신 손익 현황 요약 및 요인분해]</h4>
<div class="cols cols-2-3">
  <div id="statusTableWrap"></div>
  <div class="plot-sm" id="plotWaterfall"></div>
</div>

<h4>[🔮 시나리오 시뮬레이터 (슬라이더 조절 &amp; 직접 입력)]</h4>
<div class="slider-row">
  <div><label>SpaceX 주가 (USD) 슬라이더</label><input type="range" id="priceSlider" min="20" max="400" step="0.1"></div>
  <div><label>주가 직접 입력 (USD)</label><input type="number" id="priceInput" min="20" max="400" step="0.1"></div>
</div>
<div class="slider-row">
  <div><label>USD/KRW 환율 (원) 슬라이더</label><input type="range" id="fxSlider" min="1200" max="1800" step="1"></div>
  <div><label>환율 직접 입력 (원)</label><input type="number" id="fxInput" min="1200" max="1800" step="1"></div>
</div>
<div class="metric-row" id="scenarioMetrics"></div>
<div class="caption-sm" id="scenarioCaption"></div>

<details>
  <summary>참고: 2026-06-30 공식(NAV·기준가 기준) 스냅샷과의 차이</summary>
  <div id="navCompare"></div>
</details>
<hr>

<!-- 3. 손익 추이 -->
<h2 class="subheader">📊 3. 손익 추이 (일별 추이 및 월별 손익 내역)</h2>
<h4>[일별 손익 추이]</h4>
<div class="cols cols-2">
  <div><h5>평가손익 추이 (억원)</h5><div class="plot" id="plotGain"></div></div>
  <div><h5>요인분해 누적 기여도 (억원)</h5><div class="plot" id="plotFactor"></div></div>
</div>
<h4>[월별 손익 내역]</h4>
<div class="cols cols-3-4">
  <div><h5>월간 손익 변동 추이 (전월비, 억원)</h5><div class="plot-sm" id="plotMonthly"></div></div>
  <div><h5>월별 요약 테이블</h5><div class="table-scroll" id="monthlyTableWrap"></div></div>
</div>
<hr>

<!-- 4. 기초데이터 -->
<h2 class="subheader">📋 4. 기초데이터 (일별 로그 데이터 및 지표 상세)</h2>
<div class="table-scroll" id="dailyTableWrap"></div>
<div class="caption-sm">
  데이터 출처: SpaceX(SPCX) 종가는 Yahoo Finance(stooq 폴백), USD/KRW 매매기준율은 한국은행 ECOS 공개API(731Y001)에서 매일 자동 수집됩니다 (GitHub Actions, fetch_daily_data.py).
  서울외국환중개(smbs.biz)는 이용약관상 자동 수집을 금지하고 있어 제외했습니다.
</div>
<hr>

<!-- 5. Raw 데이터 -->
<h2 class="subheader">📦 5. Raw 데이터 (수집 원자료 시계열)</h2>
<div class="caption-sm" style="margin-bottom:14px">
  raw_spcx_price.csv / raw_fx_bok.csv는 append-only 원자료이며, 위 4.기초데이터(daily_log.csv)는 두 원자료를 날짜로 조인해 매번 다시 계산한 파생 데이터입니다.
</div>
<div class="cols cols-2">
  <div><h5>SpaceX 종가 (raw_spcx_price.csv)</h5><div class="table-scroll" id="rawSpcxWrap" style="max-height:320px"></div></div>
  <div><h5>USD/KRW 매매기준율 (raw_fx_bok.csv)</h5><div class="table-scroll" id="rawFxWrap" style="max-height:320px"></div></div>
</div>

<footer id="footer"></footer>

<script>
const DATA = __DATA_JSON__;

function fmtKrw(x, signed) {
  const v = x / 1e8;
  const s = v.toLocaleString("ko-KR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  return (signed && v >= 0 ? "+" : "") + s + "억원";
}
function fmtUsd(x) { return "$" + (+x).toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2}); }
function fmtPct(x, signed) {
  const v = x * 100;
  const s = v.toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  return (signed && v >= 0 ? "+" : "") + s + "%";
}
function fmtFx(x) { return (+x).toLocaleString("ko-KR", {minimumFractionDigits: 1, maximumFractionDigits: 1}) + "원"; }

const daily = DATA.daily;
const dates = daily.map(r => r.date);
const latest = DATA.latest, prev = DATA.prev, K = DATA.constants;

document.getElementById("topCaption").textContent =
  `데이터 기준일: ${latest.date}  |  미래생명 SpaceX 보유주식수 ${K.shares.toLocaleString("ko-KR",{minimumFractionDigits:2,maximumFractionDigits:2})}주 · 공모가 $${K.ipo_price.toFixed(0)} · 취득환율 ${K.acq_fx.toFixed(1)}원 기준`;

// ================= 1. 주가 추이 =================
Plotly.newPlot("plotPrice", [{
  x: dates, y: daily.map(r => +r.spcx_price_usd), mode: "lines+markers",
  line: { color: "#c62828", width: 2.5 }, marker: { size: 4 }
}], {
  margin: { l: 50, r: 10, t: 10, b: 30 }, yaxis: { title: "USD" },
  shapes: [{ type: "line", x0: 0, x1: 1, xref: "paper", y0: K.ipo_price, y1: K.ipo_price, yref: "y",
    line: { dash: "dash", color: "gray" } }],
  annotations: [{ x: 1, xref: "paper", y: K.ipo_price, yref: "y", text: `공모가 $${K.ipo_price.toFixed(0)}`,
    showarrow: false, xanchor: "right", yanchor: "bottom", font: { color: "gray", size: 11 } }]
}, { displayModeBar: false, responsive: true });

Plotly.newPlot("plotFx", [{
  x: dates, y: daily.map(r => +r.fx_rate), mode: "lines+markers",
  line: { color: "#6a1b9a", width: 2.5 }, marker: { size: 4 }
}], {
  margin: { l: 55, r: 10, t: 10, b: 30 }, yaxis: { title: "원/USD" },
  shapes: [{ type: "line", x0: 0, x1: 1, xref: "paper", y0: K.acq_fx, y1: K.acq_fx, yref: "y",
    line: { dash: "dash", color: "gray" } }],
  annotations: [{ x: 1, xref: "paper", y: K.acq_fx, yref: "y", text: `취득환율 ${K.acq_fx.toFixed(0)}원`,
    showarrow: false, xanchor: "right", yanchor: "bottom", font: { color: "gray", size: 11 } }]
}, { displayModeBar: false, responsive: true });

// ================= 2. 손익 현황 =================
function metricHtml(label, value, delta, deltaCls) {
  return `<div class="metric">
    <div class="metric-label">${label}</div>
    <div class="metric-value">${value}</div>
    ${delta ? `<div class="metric-delta ${deltaCls}">${delta}</div>` : ""}
  </div>`;
}
const priceDelta = (+latest.spcx_price_usd - +prev.spcx_price_usd);
const fxDelta = (+latest.fx_rate - +prev.fx_rate);
document.getElementById("marketMetrics").innerHTML =
  metricHtml("SpaceX 종가 (USD)", fmtUsd(latest.spcx_price_usd),
    `${priceDelta >= 0 ? "+" : ""}${priceDelta.toFixed(2)} (전일比)`, priceDelta >= 0 ? "up" : "down") +
  metricHtml("USD/KRW 환율", fmtFx(latest.fx_rate),
    `${fxDelta >= 0 ? "+" : ""}${fxDelta.toFixed(1)}원 (전일比)`, fxDelta >= 0 ? "up" : "down");

const statusRows = [
  ["투자원가 (Acquisition Cost)", fmtUsd(latest.cost_usd), `${K.acq_fx.toFixed(1)}원`, fmtKrw(+latest.cost_krw)],
  ["평가금액 (Current Valuation)", fmtUsd(latest.value_usd), `${(+latest.fx_rate).toFixed(1)}원`, fmtKrw(+latest.value_krw)],
  ["평가손익 (Total P&L)", fmtUsd(latest.gain_usd), "-", fmtKrw(+latest.gain_krw)],
  ["&nbsp;&nbsp;└ 주가상승효과 (Price Effect)", fmtUsd(+latest.value_usd - +latest.cost_usd), `${K.acq_fx.toFixed(1)}원 (취득환율)`, fmtKrw(+latest.price_effect_krw)],
  ["&nbsp;&nbsp;└ 외화환산손익 (FX Translation)", "-", `${(fxDelta>=0?"+":"")}${fxDelta.toFixed(1)}원 (환율변동)`, fmtKrw(+latest.fx_effect_krw)],
  ["누적 수익률 (Cumulative Return)", fmtPct(+latest.return_usd), "-", fmtPct(+latest.return_krw)],
];
document.getElementById("statusTableWrap").innerHTML = `
  <table class="status">
  <thead><tr><th>구분</th><th>외화 (USD)</th><th>적용환율 (FX Rate)</th><th>원화 (억원)</th></tr></thead>
  <tbody>${statusRows.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td></tr>`).join("")}</tbody>
  </table>`;

Plotly.newPlot("plotWaterfall", [{
  type: "waterfall", orientation: "v",
  measure: ["relative", "relative", "relative", "total"],
  x: ["1. 취득원가", "2. 주가상승효과", "3. 외화환산손익", "4. 최신 평가금액"],
  textposition: "outside",
  text: [
    `${(+latest.cost_krw/1e8).toLocaleString("ko-KR",{maximumFractionDigits:2})}억`,
    `${(+latest.price_effect_krw/1e8>=0?"+":"")}${(+latest.price_effect_krw/1e8).toLocaleString("ko-KR",{maximumFractionDigits:2})}억`,
    `${(+latest.fx_effect_krw/1e8>=0?"+":"")}${(+latest.fx_effect_krw/1e8).toLocaleString("ko-KR",{maximumFractionDigits:2})}억`,
    `${(+latest.value_krw/1e8).toLocaleString("ko-KR",{maximumFractionDigits:2})}억`,
  ],
  y: [+latest.cost_krw/1e8, +latest.price_effect_krw/1e8, +latest.fx_effect_krw/1e8, +latest.value_krw/1e8],
  connector: { line: { color: "gray", width: 1.5 } },
  decreasing: { marker: { color: "#c62828" } },
  increasing: { marker: { color: "#2e7d32" } },
  totals: { marker: { color: "#1f4e78" } },
}], {
  margin: { l: 45, r: 10, t: 10, b: 40 }, yaxis: { title: "억원" }, showlegend: false
}, { displayModeBar: false, responsive: true });

// ---- 시나리오 시뮬레이터 ----
const priceSlider = document.getElementById("priceSlider"), priceInput = document.getElementById("priceInput");
const fxSlider = document.getElementById("fxSlider"), fxInput = document.getElementById("fxInput");
priceSlider.value = priceInput.value = (+latest.spcx_price_usd).toFixed(1);
fxSlider.value = fxInput.value = (+latest.fx_rate).toFixed(0);

function computeRow(price, fx) {
  const shares = K.shares;
  const costUsd = shares * K.ipo_price, costKrw = costUsd * K.acq_fx;
  const valueUsd = shares * price, valueKrw = valueUsd * fx;
  const gainKrw = valueKrw - costKrw;
  const priceEffect = (valueUsd - costUsd) * K.acq_fx;
  const fxEffect = valueUsd * (fx - K.acq_fx);
  return { valueKrw, gainKrw, returnKrw: gainKrw / costKrw, pctVsIpo: price / K.ipo_price - 1, priceEffect, fxEffect, costKrw };
}

function renderScenario() {
  const price = +priceInput.value, fx = +fxInput.value;
  const sim = computeRow(price, fx);
  document.getElementById("scenarioMetrics").innerHTML =
    metricHtml("시나리오 평가금액 (억원)", fmtKrw(sim.valueKrw)) +
    metricHtml("시나리오 평가손익 (억원)", fmtKrw(sim.gainKrw)) +
    metricHtml("시나리오 수익률", fmtPct(sim.returnKrw)) +
    metricHtml("공모가 대비 등락률", fmtPct(sim.pctVsIpo));
  document.getElementById("scenarioCaption").textContent =
    `주가상승효과 ${fmtKrw(sim.priceEffect)} · 외화환산손익 ${fmtKrw(sim.fxEffect)} (취득원가 ${fmtKrw(sim.costKrw)} 기준, 미래생명 보유주식수 ${K.shares.toLocaleString("ko-KR",{minimumFractionDigits:2,maximumFractionDigits:2})}주)`;
}
function syncPrice(v) { priceSlider.value = v; priceInput.value = v; renderScenario(); }
function syncFx(v) { fxSlider.value = v; fxInput.value = v; renderScenario(); }
priceSlider.addEventListener("input", e => syncPrice(e.target.value));
priceInput.addEventListener("input", e => syncPrice(e.target.value));
fxSlider.addEventListener("input", e => syncFx(e.target.value));
fxInput.addEventListener("input", e => syncFx(e.target.value));
renderScenario();

// NAV 비교
document.getElementById("navCompare").innerHTML = `
  <ul>
    <li><b>공식 평가손익 (원본자료, NAV·기준가 기준, ${K.official_date})</b>: ${fmtKrw(K.official_gain_krw)}
      (취득금액 ${fmtKrw(K.official_cost_krw)} → 평가금액 ${fmtKrw(K.official_value_krw)})
      — 펀드 전체(예금·외화예치금·기타자산·운용보수 등) 효과가 모두 반영된 확정 손익입니다.</li>
    <li><b>SpaceX Look-through 평가손익 (${K.official_date}, 이 대시보드 방식)</b>: ${DATA.row_630_gain_krw !== null ? fmtKrw(DATA.row_630_gain_krw) : "기록 없음"}
      — 미래생명 실제 보유주식수(${K.shares.toLocaleString("ko-KR",{maximumFractionDigits:2})}주) × SpaceX 주가로 산출한 SpaceX 고유 손익입니다.</li>
    <li>두 수치의 차이는 운용보수, 현금성자산(예금·외화예치금) 효과, 그리고 Apex Fund. Ltd.의 SpaceX 보유주식수(${K.fund_shares.toLocaleString("ko-KR")}주) × 6/30가격이
      원본자료 공시 평가금액과 약 0.8% 차이 나는 점에 기인합니다.</li>
    <li>이 대시보드는 <b>일일 자동 갱신이 가능한 SpaceX Look-through 방식</b>을 기준으로 하며, 공식 NAV 기준 손익은 펀드 운용사가 공식 기준가를 발표하는 시점에만 갱신 가능합니다.</li>
  </ul>`;

// ================= 3. 손익 추이 =================
Plotly.newPlot("plotGain", [{
  x: dates, y: daily.map(r => +r.gain_krw / 1e8), mode: "lines+markers", name: "평가손익",
  line: { color: "#1f4e78", width: 3 }
}], {
  margin: { l: 55, r: 10, t: 10, b: 30 }, yaxis: { title: "평가손익 (억원)" },
  shapes: [{ type: "line", x0: 0, x1: 1, xref: "paper", y0: 0, y1: 0, yref: "y", line: { dash: "dot", color: "gray" } }]
}, { displayModeBar: false, responsive: true });

Plotly.newPlot("plotFactor", [
  { x: dates, y: daily.map(r => +r.price_effect_krw / 1e8), stackgroup: "one", name: "주가상승효과", line: { color: "#2e7d32" } },
  { x: dates, y: daily.map(r => +r.fx_effect_krw / 1e8), stackgroup: "one", name: "외화환산손익", line: { color: "#f9a825" } },
  { x: dates, y: daily.map(r => +r.gain_krw / 1e8), mode: "lines", name: "평가손익 합계", line: { color: "#1f4e78", width: 2, dash: "dot" } },
], {
  margin: { l: 50, r: 10, t: 10, b: 30 }, yaxis: { title: "억원" }, legend: { orientation: "h", y: -0.25 }
}, { displayModeBar: false, responsive: true });

// 월별
const monthly = DATA.monthly;
const monthColors = monthly.map(m => m.monthly_gain_change >= 0 ? "#2e7d32" : "#c62828");
Plotly.newPlot("plotMonthly", [{
  type: "bar", x: monthly.map(m => m.year_month), y: monthly.map(m => m.monthly_gain_change / 1e8),
  marker: { color: monthColors },
  text: monthly.map(m => `${m.monthly_gain_change >= 0 ? "+" : ""}${(m.monthly_gain_change/1e8).toLocaleString("ko-KR",{maximumFractionDigits:2})}억`),
  textposition: "outside"
}], {
  margin: { l: 55, r: 10, t: 20, b: 40 }, yaxis: { title: "변동액 (억원)" }
}, { displayModeBar: false, responsive: true });

document.getElementById("monthlyTableWrap").innerHTML = `
  <table class="datatable">
  <thead><tr><th>년-월</th><th>월말 주가</th><th>월말 환율</th><th>평가금액</th><th>평가손익</th><th>월간 손익변동</th><th>누적수익률</th></tr></thead>
  <tbody>${monthly.map(m => `<tr>
    <td>${m.year_month}</td><td>${fmtUsd(m.spcx_price_usd)}</td><td>${fmtFx(m.fx_rate)}</td>
    <td>${fmtKrw(m.value_krw)}</td><td>${fmtKrw(m.gain_krw)}</td>
    <td>${fmtKrw(m.monthly_gain_change, true)}</td><td>${fmtPct(m.return_krw, true)}</td>
  </tr>`).join("")}</tbody>
  </table>`;

// ================= 4. 기초데이터 =================
document.getElementById("dailyTableWrap").innerHTML = `
  <table class="datatable">
  <thead><tr><th>날짜</th><th>SpaceX 종가(USD)</th><th>환율(원)</th><th>공모가대비</th><th>평가금액</th><th>평가손익</th><th>수익률</th><th>주가효과</th><th>환산효과</th><th>데이터출처</th></tr></thead>
  <tbody>${daily.slice().reverse().map(r => `<tr>
    <td>${r.date}</td><td>${fmtUsd(r.spcx_price_usd)}</td><td>${fmtFx(r.fx_rate)}</td>
    <td>${fmtPct(+r.pct_vs_ipo, true)}</td><td>${fmtKrw(+r.value_krw)}</td><td>${fmtKrw(+r.gain_krw)}</td>
    <td>${fmtPct(+r.return_krw, true)}</td><td>${fmtKrw(+r.price_effect_krw)}</td><td>${fmtKrw(+r.fx_effect_krw)}</td><td>${r.source}</td>
  </tr>`).join("")}</tbody>
  </table>`;

// ================= 5. Raw 데이터 =================
document.getElementById("rawSpcxWrap").innerHTML = `
  <table class="datatable">
  <thead><tr><th>날짜</th><th>종가(USD)</th><th>출처</th></tr></thead>
  <tbody>${DATA.raw_spcx.slice().reverse().map(r => `<tr><td>${r.date}</td><td>${fmtUsd(r.close_usd)}</td><td>${r.source}</td></tr>`).join("")}</tbody>
  </table>`;
document.getElementById("rawFxWrap").innerHTML = `
  <table class="datatable">
  <thead><tr><th>날짜</th><th>매매기준율</th><th>출처</th></tr></thead>
  <tbody>${DATA.raw_fx.slice().reverse().map(r => `<tr><td>${r.date}</td><td>${fmtFx(r.fx_rate)}</td><td>${r.source}</td></tr>`).join("")}</tbody>
  </table>`;

document.getElementById("footer").innerHTML =
  `생성 시각: ${DATA.generated_at} · 이 페이지는 정적 스냅샷이며, 영업일 매일 아침 GitHub Actions가 데이터를 갱신하고 재배포합니다.`;
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
