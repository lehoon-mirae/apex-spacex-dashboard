"""
APEX 펀드 / 미래생명 SpaceX 손익분석 - 공통 상수
원본자료: APEX 펀드 정보_2026년 6월말.xlsx (2026-06-30 평가기준일 확정치)
"""

# --- 미래생명 (Look-through 모델 기준, 자동 일일 갱신용) ---
MIRAE_SPCX_SHARES = 575111.2099619086      # 미래생명의 SpaceX 보유주식수 (원본자료 확정치)
IPO_PRICE_USD = 135.0                       # SpaceX 공모가 (2026-06-12 상장)
ACQ_FX_RATE = 1519.8                        # 취득시점 환율 (원/USD, 원본자료)

# --- 펀드 전체 (참고용) ---
FUND_SPCX_SHARES = 2486250                  # Apex Fund. Ltd. 전체 SpaceX 보유주식수 (원본자료)
MIRAE_SHARE_PCT = 0.2313167259776045        # 미래생명 지분율 (=575,111.21 / 2,486,250)

# --- 6/30 공식(NAV 기준) 스냅샷 (원본자료, 참고/조정용) ---
OFFICIAL_SNAPSHOT_DATE = "2026-06-30"
OFFICIAL_COST_KRW = 124231573148            # 미래생명 취득금액 (원본자료)
OFFICIAL_VALUE_KRW = 157295557878           # 미래생명 평가금액 (원본자료, NAV/기준가 기준)
OFFICIAL_GAIN_KRW = 33063984730             # 미래생명 평가손익 (원본자료, NAV/기준가 기준)
OFFICIAL_EOP_FX = 1549.4                    # 2026-06-30 평가기준일 환율 (원본자료)
OFFICIAL_SPCX_PRICE = 170.86                # 2026-06-30 SpaceX 종가

# --- 조회 심볼 ---
SPCX_TICKER = "SPCX"        # SpaceX 나스닥 티커

# --- 한국은행 ECOS 공개 API (USD/KRW 매매기준율) ---
# 서울외국환중개(smbs.biz)는 이용약관에서 크롤러·스크래퍼 등 자동 수집을 명시적으로 금지하고
# (위반 시 저작권법 제136조에 따른 형사처벌 조항 명시) 있어 자동화 대상에서 제외했습니다.
# 대신 서울외국환중개가 산정에 참여하는 것과 동일한 공식 "매매기준율"을 한국은행 ECOS가
# 무료 공개 API로 제공하므로 이를 사용합니다.
ECOS_BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"
ECOS_STAT_CODE = "731Y001"      # 3.1.1.1. 주요국 통화의 대원화환율
ECOS_ITEM_CODE = "0000001"      # 원/미국달러(매매기준율)
ECOS_API_KEY_ENV = "ECOS_API_KEY"   # GitHub Secrets 등 환경변수명 (미설정 시 'sample' 키로 폴백, 1회 최대 10건)

# --- 데이터 파일 경로 ---
DATA_CSV_PATH = "data/daily_log.csv"          # 파생/가공 데이터 (raw 조인 결과, 시계열)
RAW_SPCX_CSV_PATH = "data/raw_spcx_price.csv"  # raw: SpaceX 종가 원자료 (Yahoo Finance)
RAW_FX_CSV_PATH = "data/raw_fx_bok.csv"        # raw: USD/KRW 매매기준율 원자료 (한국은행 ECOS)
