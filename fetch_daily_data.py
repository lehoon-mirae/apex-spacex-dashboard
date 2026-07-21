"""
매일 실행되는 자동 데이터 수집 스크립트.
GitHub Actions(.github/workflows/daily_update.yml)가 매일 정해진 시각에 이 스크립트를 실행하고,
변경된 data/*.csv를 저장소에 자동 커밋합니다.

데이터 흐름 (raw -> derived):
  1) raw_spcx_price.csv  <- Yahoo Finance(yfinance), 실패 시 stooq.com 폴백
  2) raw_fx_bok.csv       <- 한국은행 ECOS 공개 API (원/미국달러 매매기준율, 731Y001)
  3) daily_log.csv        <- 위 두 raw 테이블을 날짜로 조인해 계산한 파생 시계열 (자동 재생성)

USD/KRW 환율은 서울외국환중개(smbs.biz)가 아닌 한국은행 ECOS를 사용합니다.
smbs.biz는 이용약관상 크롤러·스크래퍼 등 자동 수집을 명시적으로 금지하고 있어
(위반 시 저작권법 제136조 형사처벌 조항 명시) 자동화 대상에서 제외했습니다.
ECOS는 서울외국환중개가 산정에 참여하는 것과 동일한 공식 매매기준율을 무료로 제공하는
합법적인 공개 API입니다 (ECOS_API_KEY 환경변수 미설정 시 공개 샘플 키로 동작).

로컬 샌드박스에서는 방화벽 정책상 실제 fetch(yfinance/ECOS)를 실행해볼 수 없었습니다.
GitHub Actions 러너는 일반 인터넷 접근이 가능하므로 정상 동작하지만, 배포 후 Actions 탭에서
첫 실행 결과를 꼭 확인하세요 (README 참고).
"""
import sys

from calc import build_daily_log
from sources import update_raw_spcx, update_raw_fx


def main():
    spcx_row = update_raw_spcx()
    if spcx_row:
        print(f"[SPCX] 신규 raw 데이터 추가: {spcx_row}")
    else:
        print("[SPCX] 오늘 날짜 데이터가 이미 존재합니다.")

    try:
        fx_rows = update_raw_fx(days_back=10)
        if fx_rows:
            print(f"[FX/ECOS] 신규 raw 데이터 {len(fx_rows)}건 추가: {[r['date'] for r in fx_rows]}")
        else:
            print("[FX/ECOS] 추가할 신규 날짜가 없습니다.")
    except Exception as e:
        print(f"[FX/ECOS] 수집 실패: {e}", file=sys.stderr)

    result = build_daily_log()
    print(f"[daily_log] {result['rows_written']}행으로 재생성 완료")
    if result["spcx_only_dates"]:
        print(f"  SPCX만 있고 환율 없음(제외): {result['spcx_only_dates']}")
    if result["fx_only_dates"]:
        print(f"  환율만 있고 SPCX 없음(제외): {result['fx_only_dates']}")


if __name__ == "__main__":
    main()
