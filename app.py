"""
미래생명 - APEX 펀드(SpaceX) 손익 대시보드
Streamlit 앱. data/daily_log.csv 를 데이터 소스로 사용하며,
GitHub Actions가 매일 이 CSV를 자동 갱신합니다 (fetch_daily_data.py 참고).
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calc import compute_row
from constants import (
    DATA_CSV_PATH, IPO_PRICE_USD, ACQ_FX_RATE, MIRAE_SPCX_SHARES,
    FUND_SPCX_SHARES, MIRAE_SHARE_PCT,
    OFFICIAL_SNAPSHOT_DATE, OFFICIAL_COST_KRW, OFFICIAL_VALUE_KRW,
    OFFICIAL_GAIN_KRW, OFFICIAL_EOP_FX, OFFICIAL_SPCX_PRICE,
)

st.set_page_config(page_title="미래생명 APEX 펀드(SpaceX) 대시보드", layout="wide")

# --- 비밀번호 인증 로직 ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 대시보드 접근 권한 필요")
    pwd = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("확인"):
        if pwd == "apex2026":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("비밀번호가 일치하지 않습니다.")
    st.stop()
# --------------------------


@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(DATA_CSV_PATH, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def krw(x):
    # 원화인 경우 '억원' 단위로 표기하고 소수점 둘째 자리까지 반올림
    val = x / 1e8
    return f"{val:,.2f}억원"


def krw_diff_str(x):
    val = x / 1e8
    return f"{val:+,.2f}억원"


def usd(x):
    return f"${x:,.2f}"


def pct(x):
    return f"{x*100:,.2f}%"


df = load_data()
latest = df.iloc[-1]
prev = df.iloc[-2] if len(df) > 1 else latest

st.title("미래생명 · APEX 펀드(SpaceX) 손익 대시보드")
st.caption(
    f"데이터 기준일: {latest['date'].strftime('%Y-%m-%d')}  |  "
    f"미래생명 SpaceX 보유주식수 {MIRAE_SPCX_SHARES:,.2f}주 · 공모가 ${IPO_PRICE_USD:,.0f} · 취득환율 {ACQ_FX_RATE:,.1f}원 기준"
)

st.markdown("---")

# ------------------------------------------------------------------
# 1번 주가 추이
# ------------------------------------------------------------------
st.subheader("📈 1. 주가 추이 (SpaceX 주가 및 환율 변동 추이)")
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### SpaceX 주가 (USD)")
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df["date"], y=df["spcx_price_usd"], mode="lines+markers",
                               line=dict(color="#c62828", width=2.5)))
    fig3.add_hline(y=IPO_PRICE_USD, line_dash="dash", line_color="gray",
                   annotation_text=f"공모가 ${IPO_PRICE_USD:.0f}")
    fig3.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="USD", xaxis_title=None)
    st.plotly_chart(fig3, use_container_width=True)
    
with c2:
    st.markdown("#### USD/KRW 환율")
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=df["date"], y=df["fx_rate"], mode="lines+markers",
                               line=dict(color="#6a1b9a", width=2.5)))
    fig4.add_hline(y=ACQ_FX_RATE, line_dash="dash", line_color="gray",
                   annotation_text=f"취득환율 {ACQ_FX_RATE:.0f}원")
    fig4.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="원/USD", xaxis_title=None)
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# ------------------------------------------------------------------
# 2번 손익 현황 (표 형식의 손익 현황 리팩토링)
# ------------------------------------------------------------------
st.subheader("💰 2. 손익 현황 (최신 현황 및 시나리오)")

# 시장 지표 KPI 카드 (SpaceX 종가, 환율)
st.markdown("#### [최신 시장 지표]")
mk1, mk2, mk3 = st.columns([1.5, 1.5, 4])
with mk1:
    st.metric("SpaceX 종가 (USD)", usd(latest["spcx_price_usd"]),
              f"{latest['spcx_price_usd'] - prev['spcx_price_usd']:+.2f} (전일比)")
with mk2:
    st.metric("USD/KRW 환율", f"{latest['fx_rate']:,.1f}원",
              f"{latest['fx_rate'] - prev['fx_rate']:+.1f}원 (전일比)")
with mk3:
    st.empty()

st.markdown(" ")

# 손익현황 표와 Waterfall 차트 배치
st.markdown("#### [최신 손익 현황 요약 및 요인분해]")
sh_left, sh_right = st.columns([4, 3])

with sh_left:
    status_data = {
        "구분": [
            "투자원가 (Acquisition Cost)",
            "평가금액 (Current Valuation)",
            "평가손익 (Total P&L)",
            "   └ 주가상승효과 (Price Effect)",
            "   └ 외화환산손익 (FX Translation)",
            "누적 수익률 (Cumulative Return)"
        ],
        "외화 (USD)": [
            usd(latest["cost_usd"]),
            usd(latest["value_usd"]),
            usd(latest["gain_usd"]),
            usd(latest["value_usd"] - latest["cost_usd"]),
            "-",
            pct(latest["return_usd"])
        ],
        "적용환율 (FX Rate)": [
            f"{ACQ_FX_RATE:,.1f}원",
            f"{latest['fx_rate']:,.1f}원",
            "-",
            f"{ACQ_FX_RATE:,.1f}원 (취득환율)",
            f"{latest['fx_rate'] - ACQ_FX_RATE:+,.1f}원 (환율변동)",
            "-"
        ],
        "원화 (억원)": [
            krw(latest["cost_krw"]),
            krw(latest["value_krw"]),
            krw(latest["gain_krw"]),
            krw(latest["price_effect_krw"]),
            krw(latest["fx_effect_krw"]),
            pct(latest["return_krw"])
        ]
    }
    df_status = pd.DataFrame(status_data)
    st.dataframe(df_status, use_container_width=True, hide_index=True)

with sh_right:
    # 최신 손익 요인분해 Waterfall 차트 (현황 중심 차트)
    fig_waterfall = go.Figure(go.Waterfall(
        name="손익 요인분해",
        orientation="v",
        measure=["relative", "relative", "relative", "total"],
        x=["1. 취득원가", "2. 주가상승효과", "3. 외화환산손익", "4. 최신 평가금액"],
        textposition="outside",
        text=[
            f"{latest['cost_krw']/1e8:,.2f}억",
            f"{latest['price_effect_krw']/1e8:+,.2f}억",
            f"{latest['fx_effect_krw']/1e8:+,.2f}억",
            f"{latest['value_krw']/1e8:,.2f}억"
        ],
        y=[
            latest['cost_krw']/1e8,
            latest['price_effect_krw']/1e8,
            latest['fx_effect_krw']/1e8,
            latest['value_krw']/1e8
        ],
        connector=dict(line=dict(color="gray", width=1.5)),
        decreasing=dict(marker=dict(color="#c62828")),
        increasing=dict(marker=dict(color="#2e7d32")),
        totals=dict(marker=dict(color="#1f4e78"))
    ))
    fig_waterfall.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title="억원",
        showlegend=False
    )
    st.plotly_chart(fig_waterfall, use_container_width=True)

st.markdown(" ")

# What-if 시나리오 시뮬레이터 (슬라이더 및 Key-in 동시 지원)
st.markdown("#### [🔮 시나리오 시뮬레이터 (슬라이더 조절 & 직접 입력)]")

sc1_col1, sc1_col2 = st.columns([3, 1])
with sc1_col1:
    price_slider = st.slider("SpaceX 주가 (USD) 슬라이더", min_value=20.0, max_value=400.0,
                             value=float(latest["spcx_price_usd"]), step=0.1)
with sc1_col2:
    price_input = st.number_input("주가 직접 입력 (USD)", min_value=20.0, max_value=400.0,
                                  value=price_slider, step=0.1)

sc2_col1, sc2_col2 = st.columns([3, 1])
with sc2_col1:
    fx_slider = st.slider("USD/KRW 환율 (원) 슬라이더", min_value=1200.0, max_value=1800.0,
                           value=float(latest["fx_rate"]), step=1.0)
with sc2_col2:
    fx_input = st.number_input("환율 직접 입력 (원)", min_value=1200.0, max_value=1800.0,
                                value=fx_slider, step=1.0)

# 최종 입력 값 결정
sim_price = price_input
sim_fx = fx_input

sim = compute_row("시나리오", sim_price, sim_fx, source="simulation")
s1, s2, s3, s4 = st.columns(4)
s1.metric("시나리오 평가금액 (억원)", krw(sim["value_krw"]))
s2.metric("시나리오 평가손익 (억원)", krw(sim["gain_krw"]))
s3.metric("시나리오 수익률", pct(sim["return_krw"]))
s4.metric("공모가 대비 등락률", pct(sim["pct_vs_ipo"]))

st.caption(
    f"주가상승효과 {krw(sim['price_effect_krw'])} · 외화환산손익 {krw(sim['fx_effect_krw'])} "
    f"(취득원가 {krw(sim['cost_krw'])} 기준, 미래생명 보유주식수 {MIRAE_SPCX_SHARES:,.2f}주)"
)

# 공식(6/30 NAV기준) 스냅샷과의 비교
with st.expander("참고: 2026-06-30 공식(NAV·기준가 기준) 스냅샷과의 차이"):
    row_630 = df[df["date"] == OFFICIAL_SNAPSHOT_DATE]
    lookthrough_gain_630 = row_630["gain_krw"].iloc[0] if not row_630.empty else None
    st.markdown(
        f"""
- **공식 평가손익 (원본자료, NAV·기준가 기준, {OFFICIAL_SNAPSHOT_DATE})**: {krw(OFFICIAL_GAIN_KRW)}
  (취득금액 {krw(OFFICIAL_COST_KRW)} → 평가금액 {krw(OFFICIAL_VALUE_KRW)})
  — 펀드 전체(예금·외화예치금·기타자산·운용보수 등) 효과가 모두 반영된 확정 손익입니다.
- **SpaceX Look-through 평가손익 ({OFFICIAL_SNAPSHOT_DATE}, 이 대시보드 방식)**: {krw(lookthrough_gain_630) if lookthrough_gain_630 is not None else '기록 없음'}
  — 미래생명 실제 보유주식수(575,111.21주) × SpaceX 주가로 산출한 SpaceX 고유 손익입니다.
- 두 수치의 차이는 운용보수, 현금성자산(예금·외화예치금) 효과, 그리고 Apex Fund. Ltd.의 SpaceX 보유주식수(2,486,250주) × 6/30가격이
  원본자료 공시 평가금액(USD 428,188,740)과 약 0.8% 차이 나는 점에 기인합니다.
- 이 대시보드는 **일일 자동 갱신이 가능한 SpaceX Look-through 방식**을 기준으로 하며, 공식 NAV 기준 손익은
  펀드 운용사가 공식 기준가를 발표하는 시점에만 갱신 가능합니다.
        """
    )

st.markdown("---")

# ------------------------------------------------------------------
# 3번 손익 추이 (일별 추이 + 월별 손익 내역 추가)
# ------------------------------------------------------------------
st.subheader("📊 3. 손익 추이 (일별 추이 및 월별 손익 내역)")

st.markdown("#### [일별 손익 추이]")
c3_1, c3_2 = st.columns(2)

with c3_1:
    st.markdown("##### 평가손익 추이 (억원)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["gain_krw"] / 1e8, mode="lines+markers",
                              name="평가손익", line=dict(color="#1f4e78", width=3)))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10),
                       yaxis_title="평가손익 (억원)", xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)
    
with c3_2:
    st.markdown("##### 요인분해 누적 기여도 (억원)")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["date"], y=df["price_effect_krw"] / 1e8, stackgroup="one",
                               name="주가상승효과", line=dict(color="#2e7d32")))
    fig2.add_trace(go.Scatter(x=df["date"], y=df["fx_effect_krw"] / 1e8, stackgroup="one",
                               name="외화환산손익", line=dict(color="#f9a825")))
    fig2.add_trace(go.Scatter(x=df["date"], y=df["gain_krw"] / 1e8, mode="lines",
                               name="평가손익 합계", line=dict(color="#1f4e78", width=2, dash="dot")))
    fig2.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10),
                        yaxis_title="억원", xaxis_title=None)
    st.plotly_chart(fig2, use_container_width=True)

st.markdown(" ")

# 월별 데이터 집계 및 월별 손익 내역 시각화
st.markdown("#### [월별 손익 내역]")

df_monthly = df.copy()
df_monthly["year_month"] = df_monthly["date"].dt.strftime("%Y-%m")
# 각 월의 마지막 영업일 기준 데이터 추출
monthly_summary = df_monthly.loc[df_monthly.groupby("year_month")["date"].idxmax()].copy()
monthly_summary = monthly_summary.sort_values("date").reset_index(drop=True)

# 월간 평가손익 변동 계산
monthly_summary["monthly_gain_change"] = monthly_summary["gain_krw"].diff()
monthly_summary["monthly_gain_change"] = monthly_summary["monthly_gain_change"].fillna(0)
if len(monthly_summary) > 0:
    monthly_summary.loc[monthly_summary.index[0], "monthly_gain_change"] = monthly_summary.loc[monthly_summary.index[0], "gain_krw"]

c3_m1, c3_m2 = st.columns([3, 4])

with c3_m1:
    st.markdown("##### 월간 손익 변동 추이 (전월비, 억원)")
    colors = ["#2e7d32" if x >= 0 else "#c62828" for x in monthly_summary["monthly_gain_change"]]
    
    fig_monthly = go.Figure()
    fig_monthly.add_trace(go.Bar(
        x=monthly_summary["year_month"],
        y=monthly_summary["monthly_gain_change"] / 1e8,
        marker_color=colors,
        text=(monthly_summary["monthly_gain_change"] / 1e8).map(lambda x: f"{x:+,.2f}억"),
        textposition="outside"
    ))
    fig_monthly.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="변동액 (억원)",
        xaxis_title=None
    )
    st.plotly_chart(fig_monthly, use_container_width=True)

with c3_m2:
    st.markdown("##### 월별 요약 테이블")
    disp_monthly = monthly_summary.copy()
    disp_monthly["date_label"] = disp_monthly["date"].dt.strftime("%Y-%m")
    
    # 원화 컬럼들 억원 단위 변환 및 포맷팅
    disp_monthly["value_krw"] = (disp_monthly["value_krw"] / 1e8).map(lambda x: f"{x:,.2f}억원")
    disp_monthly["gain_krw"] = (disp_monthly["gain_krw"] / 1e8).map(lambda x: f"{x:,.2f}억원")
    disp_monthly["monthly_gain_change"] = (disp_monthly["monthly_gain_change"] / 1e8).map(lambda x: f"{x:+,.2f}억원")
    
    # 기타 컬럼 포맷팅
    disp_monthly["spcx_price_usd"] = disp_monthly["spcx_price_usd"].map(lambda x: f"${x:,.2f}")
    disp_monthly["fx_rate"] = disp_monthly["fx_rate"].map(lambda x: f"{x:,.1f}원")
    disp_monthly["return_krw"] = (disp_monthly["return_krw"] * 100).map(lambda x: f"{x:+.2f}%")
    
    show_monthly_cols = ["date_label", "spcx_price_usd", "fx_rate", "value_krw", "gain_krw", "monthly_gain_change", "return_krw"]
    disp_monthly = disp_monthly[show_monthly_cols]
    disp_monthly.columns = ["년-월", "월말 주가", "월말 환율", "평가금액", "평가손익", "월간 손익변동", "누적수익률"]
    
    st.dataframe(disp_monthly, use_container_width=True, hide_index=True)

st.markdown("---")

# ------------------------------------------------------------------
# 4번 기초데이터
# ------------------------------------------------------------------
st.subheader("📋 4. 기초데이터 (일별 로그 데이터 및 지표 상세)")

show_cols = ["date", "spcx_price_usd", "fx_rate", "pct_vs_ipo", "value_krw",
             "gain_krw", "return_krw", "price_effect_krw", "fx_effect_krw", "source"]
disp = df[show_cols].sort_values("date", ascending=False).copy()
disp["date"] = disp["date"].dt.strftime("%Y-%m-%d")

# 원화 컬럼들 억원 단위 변환 및 포맷팅
disp["value_krw"] = (disp["value_krw"] / 1e8).map(lambda x: f"{x:,.2f}억원")
disp["gain_krw"] = (disp["gain_krw"] / 1e8).map(lambda x: f"{x:,.2f}억원")
disp["price_effect_krw"] = (disp["price_effect_krw"] / 1e8).map(lambda x: f"{x:,.2f}억원")
disp["fx_effect_krw"] = (disp["fx_effect_krw"] / 1e8).map(lambda x: f"{x:,.2f}억원")

# 기타 컬럼 포맷팅
disp["spcx_price_usd"] = disp["spcx_price_usd"].map(lambda x: f"${x:,.2f}")
disp["fx_rate"] = disp["fx_rate"].map(lambda x: f"{x:,.1f}원")
disp["pct_vs_ipo"] = (disp["pct_vs_ipo"] * 100).map(lambda x: f"{x:+.2f}%")
disp["return_krw"] = (disp["return_krw"] * 100).map(lambda x: f"{x:+.2f}%")

disp.columns = ["날짜", "SpaceX 종가(USD)", "환율(원)", "공모가대비", "평가금액",
                "평가손익", "수익률", "주가효과", "환산효과", "데이터출처"]

st.dataframe(disp, use_container_width=True, hide_index=True)

st.caption(
    "데이터 출처: SpaceX(SPCX) 종가·USD/KRW 환율은 Yahoo Finance에서 매일 자동 수집됩니다 (GitHub Actions, fetch_daily_data.py). "
    "2026-07-17 이전 이력은 상장 시점 뉴스·시세 사이트 실측치로 시딩되었으며, 환율은 취득환율↔평가기준일 환율 구간을 보간한 근사치입니다."
)
