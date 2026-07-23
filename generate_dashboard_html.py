"""
Cowork 아티팩트용 자체완결형(self-contained) HTML 대시보드를 생성합니다.

data/daily_log.csv, data/raw_spcx_price.csv, data/raw_fx_bok.csv, constants.py 를 읽어
값을 JSON으로 그대로 HTML에 임베드합니다 (아티팩트는 로컬 CSV에 라이브로 접근할 수 없으므로,
매번 실행 시점의 스냅샷을 굽습니다 - 그래서 스케줄 작업이 매 영업일 이 스크립트를 다시 실행해
아티팩트를 갱신하는 구조입니다).

사용법: cwd를 apex-dashboard 폴더로 맞추고 실행
    python3 generate_dashboard_html.py
출력: dashboard_artifact.html (같은 폴더)
"""
import csv
import json
import datetime as dt

import constants as C


def _read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


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
            "pct": round(pct, 4),
            "price": round(price, 2),
            "value_krw": round(value_krw, 0),
            "gain_krw": round(gain_krw, 0),
            "return_krw": round(gain_krw / cost_krw, 6),
        })
    return rows


def main():
    daily = _read_csv(C.DATA_CSV_PATH)
    raw_spcx = _read_csv(C.RAW_SPCX_CSV_PATH)
    raw_fx = _read_csv(C.RAW_FX_CSV_PATH)

    daily_sorted = sorted(daily, key=lambda r: r["date"])
    latest = daily_sorted[-1] if daily_sorted else None

    payload = {
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "constants": {
            "shares": C.MIRAE_SPCX_SHARES,
            "ipo_price": C.IPO_PRICE_USD,
            "acq_fx": C.ACQ_FX_RATE,
            "fund_shares": C.FUND_SPCX_SHARES,
            "mirae_pct": C.MIRAE_SHARE_PCT,
            "official_date": C.OFFICIAL_SNAPSHOT_DATE,
            "official_cost_krw": C.OFFICIAL_COST_KRW,
            "official_value_krw": C.OFFICIAL_VALUE_KRW,
            "official_gain_krw": C.OFFICIAL_GAIN_KRW,
            "official_fx": C.OFFICIAL_EOP_FX,
            "official_price": C.OFFICIAL_SPCX_PRICE,
        },
        "daily": daily_sorted,
        "raw_spcx": sorted(raw_spcx, key=lambda r: r["date"]),
        "raw_fx": sorted(raw_fx, key=lambda r: r["date"]),
        "latest": latest,
        "scenario": build_scenario(float(latest["fx_rate"])) if latest else [],
    }

    data_json = json.dumps(payload, ensure_ascii=False)

    html = HTML_TEMPLATE.replace("__DATA_JSON__", data_json)

    with open("dashboard_artifact.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"dashboard_artifact.html 생성 완료 ({len(daily_sorted)}행, 기준일 {latest['date'] if latest else 'N/A'})")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>미래생명 · APEX 펀드(SpaceX) 손익 대시보드</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.js" integrity="sha384-iU8HYtnGQ8Cy4zl7gbNMOhsDTTKX02BTXptVP/vqAWIaTfM7isw76iyZCsjL2eVi" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/gridjs.umd.js" integrity="sha384-/XXDzxe4FsGiAe50i/u9pY/Vy/uX654MHB1xoc1BJNnH1WXHhqHga9g3q5tF4gj7" crossorigin="anonymous"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/theme/mermaid.min.css" integrity="sha384-jZvDSsmGB9oGGT/4l9bHXGoAv1OxvG/cFmSo0dZaSqmBgvQTKDBFAMftlXTmMbNW" crossorigin="anonymous">
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px; background: #f7f7f8; color: #1a1a1a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Malgun Gothic", sans-serif;
  }
  h1 { font-size: 20px; margin: 0 0 4px; }
  .subtitle { color: #6b6b6b; font-size: 13px; margin-bottom: 20px; }
  .kpi-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 12px; margin-bottom: 24px;
  }
  .kpi-card {
    background: #fff; border: 1px solid #e5e5e5; border-radius: 10px; padding: 14px 16px;
  }
  .kpi-label { font-size: 12px; color: #6b6b6b; margin-bottom: 6px; }
  .kpi-value { font-size: 20px; font-weight: 600; }
  .kpi-sub { font-size: 12px; margin-top: 4px; }
  .pos { color: #c62828; }
  .neg { color: #1565c0; }
  .section {
    background: #fff; border: 1px solid #e5e5e5; border-radius: 10px; padding: 18px;
    margin-bottom: 20px;
  }
  .section h2 { font-size: 15px; margin: 0 0 12px; }
  .chart-wrap { position: relative; height: 280px; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }
  .note { font-size: 12px; color: #6b6b6b; line-height: 1.6; margin-top: 10px; }
  .scenario-controls { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
  .scenario-controls input[type=range] { flex: 1; }
  .scenario-readout { font-size: 13px; font-weight: 600; min-width: 210px; text-align: right; }
  table.compact { width: 100%; border-collapse: collapse; font-size: 13px; }
  table.compact th, table.compact td { padding: 6px 8px; text-align: right; border-bottom: 1px solid #f0f0f0; }
  table.compact th:first-child, table.compact td:first-child { text-align: left; }
  .gridjs-wrapper { font-size: 13px; }
  footer { font-size: 12px; color: #8a8a8a; margin-top: 8px; line-height: 1.7; }
</style>
</head>
<body>

<h1>🚀 미래생명 · APEX 펀드(SpaceX) 손익 대시보드</h1>
<div class="subtitle" id="subtitle"></div>

<div class="kpi-grid" id="kpiGrid"></div>

<div class="section">
  <h2>📈 SpaceX 종가 &amp; USD/KRW 매매기준율 추이</h2>
  <div class="two-col">
    <div class="chart-wrap"><canvas id="priceChart"></canvas></div>
    <div class="chart-wrap"><canvas id="fxChart"></canvas></div>
  </div>
</div>

<div class="section">
  <h2>💰 미래생명 평가손익 추이 (원화, 주가효과/환율효과 분해)</h2>
  <div class="chart-wrap"><canvas id="gainChart"></canvas></div>
  <div class="note">주가상승효과 = (평가금액USD − 투자원가USD) × 취득환율(1,519.8원 고정) · 외화환산손익 = 평가금액USD × (당일환율 − 취득환율). 두 효과의 합은 항상 총 평가손익과 정확히 일치합니다.</div>
</div>

<div class="section">
  <h2>🎛️ 시나리오: SpaceX 주가 등락률에 따른 손익 시뮬레이션</h2>
  <div class="scenario-controls">
    <span>공모가($135) 대비</span>
    <input type="range" id="scenarioSlider" min="-50" max="100" step="1" value="0">
    <span class="scenario-readout" id="scenarioReadout"></span>
  </div>
  <table class="compact" id="scenarioTable"></table>
  <div class="note">환율은 최신 daily_log 기준값으로 고정하고 주가 변동 효과만 분리해서 봅니다. 슬라이더는 이 브라우저 안에서 즉시 재계산되며 별도 서버 호출이 없습니다.</div>
</div>

<div class="section">
  <h2>📋 일별 손익 데이터 (파생: raw_spcx_price.csv × raw_fx_bok.csv 조인)</h2>
  <div id="dailyGrid"></div>
</div>

<div class="section">
  <h2>📦 Raw 원자료</h2>
  <div class="two-col">
    <div>
      <div class="note" style="margin-top:0">SpaceX 종가 (raw_spcx_price.csv)</div>
      <div id="rawSpcxGrid"></div>
    </div>
    <div>
      <div class="note" style="margin-top:0">USD/KRW 매매기준율 (raw_fx_bok.csv, 한국은행 ECOS)</div>
      <div id="rawFxGrid"></div>
    </div>
  </div>
</div>

<footer id="footer"></footer>

<script>
const DATA = __DATA_JSON__;

function krw(v) {
  const eok = v / 100000000;
  return (v < 0 ? "" : "") + eok.toLocaleString("ko-KR", {maximumFractionDigits: 1}) + "억원";
}
function usd(v) { return "$" + v.toLocaleString("en-US", {maximumFractionDigits: 0}); }
function pct(v) { return (v * 100).toFixed(1) + "%"; }
function signClass(v) { return v >= 0 ? "pos" : "neg"; }

document.getElementById("subtitle").textContent =
  `생성 시각: ${DATA.generated_at} · 미래생명 SpaceX 보유주식수 ${DATA.constants.shares.toLocaleString("ko-KR", {maximumFractionDigits:0})}주 · 취득환율 ${DATA.constants.acq_fx}원 · 공모가 $${DATA.constants.ipo_price}`;

// ---------------- KPI ----------------
const latest = DATA.latest;
const kpis = [
  { label: `평가금액 (${latest.date} 기준)`, value: krw(+latest.value_krw), sub: usd(+latest.value_usd), cls: "" },
  { label: "취득원가", value: krw(+latest.cost_krw), sub: usd(+latest.cost_usd), cls: "" },
  { label: "평가손익", value: krw(+latest.gain_krw), sub: pct(+latest.return_krw) + " (KRW)", cls: signClass(+latest.gain_krw) },
  { label: "수익률 (USD 기준)", value: pct(+latest.return_usd), sub: `SpaceX $${latest.spcx_price_usd} · 공모가 대비 ${pct(+latest.pct_vs_ipo)}`, cls: signClass(+latest.return_usd) },
  { label: "주가상승효과", value: krw(+latest.price_effect_krw), sub: "가격변동 × 취득환율", cls: signClass(+latest.price_effect_krw) },
  { label: "외화환산손익", value: krw(+latest.fx_effect_krw), sub: `환율 ${latest.fx_rate}원`, cls: signClass(+latest.fx_effect_krw) },
];
const kpiGrid = document.getElementById("kpiGrid");
kpiGrid.innerHTML = kpis.map(k => `
  <div class="kpi-card">
    <div class="kpi-label">${k.label}</div>
    <div class="kpi-value ${k.cls}">${k.value}</div>
    <div class="kpi-sub ${k.cls}">${k.sub}</div>
  </div>
`).join("");

// ---------------- Charts ----------------
const labels = DATA.daily.map(r => r.date);

new Chart(document.getElementById("priceChart"), {
  type: "line",
  data: { labels, datasets: [{ label: "SpaceX 종가 (USD)", data: DATA.daily.map(r => +r.spcx_price_usd),
    borderColor: "#c62828", backgroundColor: "rgba(198,40,40,0.08)", fill: true, tension: 0.2, pointRadius: 2 }] },
  options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, title: { display: true, text: "SpaceX 종가 (USD)" } } }
});

new Chart(document.getElementById("fxChart"), {
  type: "line",
  data: { labels, datasets: [{ label: "USD/KRW 매매기준율", data: DATA.daily.map(r => +r.fx_rate),
    borderColor: "#6a1b9a", backgroundColor: "rgba(106,27,154,0.08)", fill: true, tension: 0.2, pointRadius: 2 }] },
  options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, title: { display: true, text: "USD/KRW 매매기준율 (한국은행 ECOS)" } } }
});

new Chart(document.getElementById("gainChart"), {
  type: "bar",
  data: {
    labels,
    datasets: [
      { label: "주가상승효과", data: DATA.daily.map(r => +r.price_effect_krw / 1e8), backgroundColor: "#ef9a9a", stack: "s" },
      { label: "외화환산손익", data: DATA.daily.map(r => +r.fx_effect_krw / 1e8), backgroundColor: "#90caf9", stack: "s" },
      { label: "총 평가손익", data: DATA.daily.map(r => +r.gain_krw / 1e8), type: "line", borderColor: "#1a1a1a", backgroundColor: "#1a1a1a", pointRadius: 2, tension: 0.15 },
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    scales: { x: { stacked: true }, y: { stacked: true, title: { display: true, text: "억원" } } },
    plugins: { legend: { position: "bottom" } }
  }
});

// ---------------- Scenario ----------------
function computeScenario(pct) {
  const shares = DATA.constants.shares;
  const costUsd = shares * DATA.constants.ipo_price;
  const costKrw = costUsd * DATA.constants.acq_fx;
  const fx = +latest.fx_rate;
  const price = DATA.constants.ipo_price * (1 + pct / 100);
  const valueUsd = shares * price;
  const valueKrw = valueUsd * fx;
  const gainKrw = valueKrw - costKrw;
  return { price, valueKrw, gainKrw, returnKrw: gainKrw / costKrw };
}

function renderScenarioTable() {
  const rows = DATA.scenario.map(r => `
    <tr>
      <td>${(r.pct*100).toFixed(0)}%</td>
      <td>$${r.price.toFixed(2)}</td>
      <td>${krw(r.value_krw)}</td>
      <td class="${signClass(r.gain_krw)}">${krw(r.gain_krw)}</td>
      <td class="${signClass(r.return_krw)}">${pct(r.return_krw)}</td>
    </tr>`).join("");
  document.getElementById("scenarioTable").innerHTML = `
    <thead><tr><th>공모가 대비</th><th>SpaceX 주가</th><th>평가금액</th><th>평가손익</th><th>수익률</th></tr></thead>
    <tbody>${rows}</tbody>`;
}
renderScenarioTable();

const slider = document.getElementById("scenarioSlider");
const readout = document.getElementById("scenarioReadout");
function updateReadout() {
  const p = +slider.value;
  const r = computeScenario(p);
  readout.textContent = `주가 $${r.price.toFixed(2)} → 손익 ${krw(r.gainKrw)} (${pct(r.returnKrw)})`;
  readout.className = "scenario-readout " + signClass(r.gainKrw);
}
slider.addEventListener("input", updateReadout);
updateReadout();

// ---------------- Grid.js tables ----------------
new gridjs.Grid({
  columns: ["날짜", "SpaceX($)", "환율(원)", "평가금액", "평가손익", "수익률(KRW)"],
  data: DATA.daily.slice().reverse().map(r => [
    r.date, (+r.spcx_price_usd).toFixed(2), (+r.fx_rate).toFixed(1),
    krw(+r.value_krw), krw(+r.gain_krw), pct(+r.return_krw)
  ]),
  sort: true, search: true, pagination: { limit: 10 },
  style: { table: { fontSize: "13px" } }
}).render(document.getElementById("dailyGrid"));

new gridjs.Grid({
  columns: ["날짜", "종가(USD)", "출처"],
  data: DATA.raw_spcx.slice().reverse().map(r => [r.date, "$" + (+r.close_usd).toFixed(2), r.source]),
  sort: true, pagination: { limit: 8 },
  style: { table: { fontSize: "12px" } }
}).render(document.getElementById("rawSpcxGrid"));

new gridjs.Grid({
  columns: ["날짜", "매매기준율", "출처"],
  data: DATA.raw_fx.slice().reverse().map(r => [r.date, (+r.fx_rate).toFixed(1) + "원", r.source]),
  sort: true, pagination: { limit: 8 },
  style: { table: { fontSize: "12px" } }
}).render(document.getElementById("rawFxGrid"));

document.getElementById("footer").innerHTML =
  `데이터 출처: SpaceX(SPCX) 종가는 Yahoo Finance(stooq 폴백), USD/KRW 매매기준율은 한국은행 ECOS 공개API(731Y001)에서 수집됩니다. ` +
  `서울외국환중개(smbs.biz)는 이용약관상 자동 수집을 금지하고 있어 제외했습니다.<br>` +
  `이 아티팩트는 라이브 커넥터가 아닌 스냅샷 데이터를 담고 있으며, 영업일 매일 아침 8:40(KST) 예약 작업이 데이터를 갱신하고 이 아티팩트를 다시 저장합니다.`;
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
