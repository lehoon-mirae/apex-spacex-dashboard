# ============================================================
# sync_push.ps1
# 로컬 PC의 최신 data/*.csv를 GitHub에 push합니다.
# 사용법: 탐색기에서 우클릭 > "PowerShell로 실행" 또는
#         PowerShell에서: .\sync_push.ps1
# ============================================================

$RepoDir    = "C:\deploy\apex-spacex-dashboard"
$SourceDir  = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location $RepoDir

Write-Host "`n[1/4] GitHub 최신 변경사항 pull 중..." -ForegroundColor Cyan
git pull origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "오류: git pull 실패. 충돌을 해결한 후 다시 실행하세요." -ForegroundColor Red
    pause; exit 1
}

# 스크립트 실행 위치(로컬 워크스페이스)와 배포 폴더가 다를 경우 복사
$LocalData  = Join-Path $SourceDir "data"
$DeployData = Join-Path $RepoDir   "data"

if ((Resolve-Path $LocalData -ErrorAction SilentlyContinue) -and
    ($LocalData -ne $DeployData)) {
    Write-Host "[2/4] 로컬 data/ → 배포 폴더로 복사 중..." -ForegroundColor Cyan
    Copy-Item "$LocalData\*" $DeployData -Force
} else {
    Write-Host "[2/4] 배포 폴더 = 로컬 폴더 — 복사 생략" -ForegroundColor Gray
}

Write-Host "[3/4] 변경된 파일 스테이징..." -ForegroundColor Cyan
git add data/

$status = git diff --cached --name-only
if (-not $status) {
    Write-Host "`n변경된 데이터가 없습니다. push를 건너뜁니다." -ForegroundColor Yellow
    pause; exit 0
}

Write-Host "변경된 파일:`n$status" -ForegroundColor White

$Date = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "data: 로컬 수동 업로드 $Date"

Write-Host "[4/4] GitHub에 push 중..." -ForegroundColor Cyan
git push origin main
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ GitHub push 완료!" -ForegroundColor Green
} else {
    Write-Host "`n❌ push 실패. 인증 상태를 확인하세요." -ForegroundColor Red
}

pause
