# 미래생명 · APEX 펀드(SpaceX) 손익 대시보드

미래생명이 APEX 펀드(Apex Fund. Ltd.)를 통해 보유한 SpaceX 익스포저의 평가손익을
매일 자동으로 갱신하고, 웹 대시보드(Streamlit)로 확인할 수 있도록 만든 저장소입니다.

- **데이터 자동 수집 (raw)**: 매일 GitHub Actions가 SpaceX(SPCX) 종가는 Yahoo Finance(stooq 폴백)에서,
  USD/KRW 환율(매매기준율)은 **한국은행 ECOS 공개 API**(통계코드 731Y001)에서 가져와
  각각 `data/raw_spcx_price.csv`, `data/raw_fx_bok.csv`에 원자료로 누적(append-only)합니다.
- **데이터 파생 (derived)**: 두 raw 파일을 날짜 기준으로 조인(inner join)해
  `data/daily_log.csv`(시계열 계산 결과)를 매번 다시 생성합니다 (`calc.build_daily_log()`).
  raw는 있는 그대로의 원자료, daily_log.csv는 raw로부터 항상 재현 가능한 파생 결과라는
  원칙(raw/derived, 이른바 "bronze/silver" 패턴)을 따릅니다.
- **대시보드**: `app.py` (Streamlit)가 raw 원자료와 파생 시계열을 모두 읽어 KPI, 시계열 차트,
  요인분해 차트, 시나리오 시뮬레이터, raw 데이터 원본 뷰를 보여줍니다.
- **엑셀**: `reference/` 폴더의 기존 분석 엑셀에 `일별로그(자동갱신)` 시트를 추가해,
  엑셀로도 동일한 이력을 확인할 수 있습니다 (`export_to_excel.py`로 언제든 재생성 가능).

> ⚠️ **왜 서울외국환중개(smbs.biz)를 직접 크롤링하지 않았나요?**
> smbs.biz는 이용약관에서 크롤러·스크래퍼 등을 이용한 자동 수집을 명시적으로 금지하고 있고
> (위반 시 저작권법 제136조에 따른 형사처벌 조항까지 명시), 환율 테이블도 자바스크립트로
> 렌더링되어 정적 크롤링이 되지 않습니다. 대신 서울외국환중개가 고시에 참여하는 것과 동일한
> 공식 "매매기준율"을 **한국은행 ECOS**가 무료 공개 API로 제공하므로, 이를 합법적인 대체
> 데이터 소스로 사용합니다.

## 폴더 구조

```
apex-dashboard/
├── app.py                     # Streamlit 대시보드
├── fetch_daily_data.py        # 매일 실행되는 자동 수집 스크립트 (raw 수집 -> daily_log 재생성)
├── sources.py                  # raw 데이터 수집 로직 (SPCX: Yahoo/stooq, FX: 한국은행 ECOS)
├── export_to_excel.py         # CSV -> 엑셀 '일별로그' 시트 내보내기 (선택)
├── calc.py                    # 공통 손익 계산 로직 + raw->derived 조인(build_daily_log)
├── constants.py                # 미래생명 보유주식수, 공모가, 취득환율, ECOS 설정 등 기준값
├── seed_history.py             # 최초 1회 이력 시딩 스크립트 (이미 실행됨)
├── requirements.txt
├── data/
│   ├── raw_spcx_price.csv      # raw: SpaceX 종가 원자료 (append-only)
│   ├── raw_fx_bok.csv          # raw: USD/KRW 매매기준율 원자료, 한국은행 ECOS (append-only)
│   └── daily_log.csv           # 파생 데이터: 위 두 raw를 날짜로 조인해 재계산한 시계열
├── reference/
│   └── APEX펀드_SpaceX투자_손익분석.xlsx   # 6/30 기준 상세 분석 엑셀 원본
└── .github/workflows/
    └── daily_update.yml        # 매일 자동 실행되는 GitHub Actions
```

## 손익 계산 방식 (요약)

- 미래생명 SpaceX 보유주식수: **575,111.21주** (원본자료 확정치, `constants.py`에 고정)
- 취득원가 = 575,111.21주 × 공모가($135) × 취득환율(1,519.8원, 고정)
- 평가금액 = 575,111.21주 × 당일 SpaceX 종가 × 당일 USD/KRW 환율
- 평가손익 = 평가금액 − 취득원가, 이를 **주가상승효과**(가격변동×취득환율)와
  **외화환산손익**(평가금액×환율변동)으로 K-IFRS 방식과 동일하게 분해합니다.
- 이 방식은 "SpaceX Look-through" 기준이며, 6/30 시점 펀드 공식 NAV 기준 손익
  (예금·운용보수 등 반영, 원본자료 3,306.4백만원)과는 구조상 소폭 차이가 있습니다.
  대시보드 하단 "참고" 섹션에서 두 수치를 비교해 보여줍니다.

---

## 배포 가이드 (GitHub + Streamlit Community Cloud, 모두 무료)

### 1단계. GitHub 저장소 만들기
1. https://github.com 에서 계정이 없으면 새로 만듭니다 (무료).
2. 우측 상단 **+ → New repository** 클릭 → 이름 예: `apex-spacex-dashboard` → Public 선택 → Create.
3. 이 폴더(`apex-dashboard/`) 전체를 로컬 컴퓨터에 내려받은 뒤, 아래 명령으로 업로드합니다.
   (Git이 없다면 GitHub 웹페이지의 "uploading an existing file" 기능으로 폴더를 통째로 드래그해도 됩니다.)

```bash
cd apex-dashboard
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/<본인계정>/apex-spacex-dashboard.git
git push -u origin main
```

### 2단계. GitHub Actions 자동수집 켜기
- 저장소를 올리면 `.github/workflows/daily_update.yml` 이 자동으로 인식되어,
  **영업일(월~금) 매일 한국시간(KST) 오전 8시 40분**에 자동 실행됩니다
  (cron `40 23 * * 0-4`, UTC 기준 일~목 23:40). GitHub Actions cron은 공휴일을 인식하지
  못하므로 국내 공휴일이 평일과 겹치는 날에도 실행은 되지만, 그날은 시장이 열리지 않아
  새 데이터가 없으면 raw CSV에 아무 것도 추가되지 않고 커밋 없이 조용히 종료됩니다.
- 바로 테스트해보려면 GitHub 저장소 페이지 → **Actions** 탭 → `Daily APEX/SpaceX data update`
  → **Run workflow** 버튼으로 즉시 1회 실행해볼 수 있습니다.
- 실행 후 `data/raw_spcx_price.csv`, `data/raw_fx_bok.csv`, `data/daily_log.csv`에 새 행이
  자동 커밋되는지 확인하세요.
- **(선택) 한국은행 ECOS 개인 API 키 등록** — https://ecos.bok.or.kr 에서 무료로 발급받은
  개인 인증키를 저장소 **Settings → Secrets and variables → Actions → New repository secret**에
  이름 `ECOS_API_KEY`로 등록하면 이를 사용합니다. 등록하지 않으면 공개 샘플 키(`sample`,
  1회 조회 최대 10건)로 자동 폴백하는데, 매일 1회만 최신 환율을 조회하는 이 워크플로에는
  충분하지만 과거 이력을 한 번에 대량 재수집하려면 개인 키가 필요합니다.
- ⚠️ 로컬 개발 환경(이 세션의 샌드박스)에서는 방화벽 때문에 Yahoo Finance / ECOS API를 직접
  호출해볼 수 없었습니다. GitHub Actions 러너는 일반 인터넷 접근이 가능하므로 정상 동작하지만,
  **배포 후 첫 실행 결과를 꼭 확인**해 주세요. 만약 SPCX 수집이 실패한다면 Actions 로그를 확인하고,
  `fetch_daily_data.py`의 stooq 폴백이 대신 동작하는지 봐 주세요. ECOS 조회가 실패해도(예: 휴장일)
  워크플로는 중단되지 않고 SPCX 원자료만 추가한 뒤 다음날 다시 시도합니다.

### 3단계. Streamlit Community Cloud에 배포
1. https://streamlit.io/cloud 접속 → GitHub 계정으로 로그인/가입 (무료).
2. **New app** 클릭 → 방금 만든 저장소(`apex-spacex-dashboard`) 선택.
3. Main file path에 `app.py` 입력 → **Deploy** 클릭.
4. 몇 분 내로 `https://<앱이름>.streamlit.app` 형태의 공개 URL이 생성됩니다.
   이 링크를 북마크해두면 매일 자동 갱신된 대시보드를 바로 확인할 수 있습니다.
5. 데이터가 갱신된 후 대시보드에 반영되지 않으면, 앱 우측 상단 메뉴 → **Rerun** 또는
   **Clear cache**를 눌러주세요 (대시보드는 1시간 캐시를 사용합니다, `app.py`의 `ttl=3600`).

### 4단계. (선택) 비공개로 운영하고 싶다면
- GitHub 저장소를 Private으로 만들어도 Streamlit Community Cloud와 연동 가능합니다
  (Streamlit이 저장소 접근 권한을 요청하면 승인해주면 됩니다).
- 앱 자체를 비공개로 하려면 Streamlit Cloud의 앱 설정에서 뷰어를 제한할 수 있습니다
  (Streamlit for Teams/Enterprise 기능이 필요할 수 있음).

---

## 로컬에서 미리 보기

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 데이터를 수동으로 갱신하고 싶을 때

`data/daily_log.csv`는 raw 파일로부터 다시 계산되는 **파생 데이터**이므로 직접 수정하지 말고,
raw 파일(`data/raw_spcx_price.csv`, `data/raw_fx_bok.csv`)에 값을 추가한 뒤
`build_daily_log()`를 다시 실행하세요:

```python
from sources import append_raw_row, RAW_SPCX_COLUMNS, RAW_FX_COLUMNS
from constants import RAW_SPCX_CSV_PATH, RAW_FX_CSV_PATH
from calc import build_daily_log
from datetime import datetime, timezone

now = datetime.now(timezone.utc).isoformat()
append_raw_row(RAW_SPCX_CSV_PATH, RAW_SPCX_COLUMNS,
               {"date": "2026-07-21", "close_usd": 130.50, "source": "manual", "fetched_at": now})
append_raw_row(RAW_FX_CSV_PATH, RAW_FX_COLUMNS,
               {"date": "2026-07-21", "fx_rate": 1552.10, "stat_code": "manual",
                "source": "manual", "fetched_at": now})

print(build_daily_log())  # raw_spcx_price.csv x raw_fx_bok.csv 를 조인해 daily_log.csv 재생성
```

또는 두 raw CSV를 엑셀/구글시트로 열어 직접 행을 추가한 뒤, 같은 방식으로
`build_daily_log()`만 다시 실행해도 됩니다. raw는 원자료 그대로 보존하고,
파생 결과(`daily_log.csv`)는 항상 raw로부터 재현 가능하게 유지하기 위함입니다.
