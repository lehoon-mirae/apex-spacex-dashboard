# ============================================================
# setup_scheduler.ps1
# Windows 작업 스케줄러에 "APEX 데이터 자동 동기화" 태스크를 등록합니다.
# 매일 오전 9시 30분에 sync_pull.ps1 을 자동 실행합니다.
#
# 사용법 (관리자 권한 PowerShell에서 한 번만 실행):
#   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\setup_scheduler.ps1
# ============================================================

$TaskName   = "APEX_Data_Sync"
$ScriptPath = "C:\deploy\apex-spacex-dashboard\sync_pull.ps1"
$PsExe      = "powershell.exe"
$Args       = "-ExecutionPolicy Bypass -NonInteractive -File `"$ScriptPath`""

# 기존 태스크 제거 (재등록 시)
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "기존 태스크 제거 완료" -ForegroundColor Yellow
}

# 트리거: 매일 오전 9:30 (평일만)
$trigger = New-ScheduledTaskTrigger -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "09:30AM"

# 실행 계정: 현재 로그인 사용자
$principal = New-ScheduledTaskPrincipal `
    -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Highest

$action = New-ScheduledTaskAction -Execute $PsExe -Argument $Args

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Trigger   $trigger `
    -Action    $action `
    -Principal $principal `
    -Settings  $settings `
    -Description "APEX SpaceX 대시보드 — GitHub에서 최신 data/*.csv를 매일 자동 pull" | Out-Null

Write-Host "`n✅ 작업 스케줄러 등록 완료!" -ForegroundColor Green
Write-Host "   태스크 이름 : $TaskName"     -ForegroundColor White
Write-Host "   실행 스크립트: $ScriptPath"  -ForegroundColor White
Write-Host "   실행 시각    : 평일 오전 9:30" -ForegroundColor White
Write-Host "`n작업 스케줄러 열기: Win+R → taskschd.msc" -ForegroundColor Gray

pause
