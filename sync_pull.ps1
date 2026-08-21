# ============================================================
# sync_pull.ps1
# GitHub의 최신 data/*.csv를 로컬 PC로 다운로드합니다.
# GitHub Actions가 자동 갱신한 데이터를 로컬에 반영할 때 사용합니다.
# 사용법: 탐색기에서 우클릭 > "PowerShell로 실행" 또는
#         PowerShell에서: .\sync_pull.ps1
# ============================================================

$RepoDir    = "C:\deploy\apex-spacex-dashboard"
$TargetDir  = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location $RepoDir

Write-Host "`n[1/3] GitHub에서 최신 데이터 pull 중..." -ForegroundColor Cyan
git pull origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "오류: git pull 실패." -ForegroundColor Red
    pause; exit 1
}

# 배포 폴더와 원래 로컬 워크스페이스가 다를 경우에만 복사
$DeployData = Join-Path $RepoDir  "data"
$LocalData  = Join-Path $TargetDir "data"

if ($DeployData -ne $LocalData) {
    Write-Host "[2/3] 배포 폴더 data/ → 로컬 워크스페이스로 복사 중..." -ForegroundColor Cyan
    if (-not (Test-Path $LocalData)) { New-Item -ItemType Directory -Path $LocalData | Out-Null }
    Copy-Item "$DeployData\*" $LocalData -Force
    Write-Host "      복사 완료: $LocalData" -ForegroundColor White
} else {
    Write-Host "[2/3] 배포 폴더 = 로컬 폴더 — 복사 생략" -ForegroundColor Gray
}

Write-Host "[3/3] 최신 데이터 확인 중..." -ForegroundColor Cyan
$csvPath = Join-Path $DeployData "daily_log.csv"
if (Test-Path $csvPath) {
    $lastLine = Get-Content $csvPath | Select-Object -Last 1
    $lastDate = ($lastLine -split ",")[0]
    Write-Host "`n✅ GitHub → 로컬 동기화 완료!" -ForegroundColor Green
    Write-Host "   daily_log.csv 최신 날짜: $lastDate" -ForegroundColor White
} else {
    Write-Host "경고: daily_log.csv를 찾을 수 없습니다." -ForegroundColor Yellow
}

pause
