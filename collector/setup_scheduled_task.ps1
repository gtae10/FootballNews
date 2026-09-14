<#
.SYNOPSIS
    scheduler.py(수집+번역 30분 주기 배치)를 Windows 작업 스케줄러에 등록한다.

.DESCRIPTION
    PC 부팅 시 자동 시작하고, 프로세스가 죽으면 자동으로 재시작되도록 등록한다.
    SYSTEM 계정으로 등록하므로 로그아웃 상태에서도 계속 실행된다(별도 비밀번호
    저장이 필요 없다). 이미 같은 이름의 작업이 있으면 지우고 다시 등록한다
    (idempotent) — 다른 PC로 옮기거나 설정을 바꾼 뒤 재실행해도 안전하다.

.NOTES
    관리자 권한 PowerShell에서 실행해야 한다(작업 등록에 관리자 권한 필요).
    사용법: collector 폴더에서 `./setup_scheduled_task.ps1`
#>

$ErrorActionPreference = "Stop"

$TaskName = "LiverpoolNewsScheduler"
$CollectorDir = $PSScriptRoot
$PythonExe = (Get-Command python).Source

if (-not $PythonExe) {
    throw "python 실행 파일을 PATH에서 찾을 수 없습니다. python이 설치돼 있고 PATH에 등록돼 있는지 확인하세요."
}

Write-Host "작업 이름: $TaskName"
Write-Host "python 경로: $PythonExe"
Write-Host "작업 디렉터리: $CollectorDir"

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "scheduler.py" -WorkingDirectory $CollectorDir
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)  # scheduler.py는 BlockingScheduler로 무한 실행되므로 시간 제한을 두지 않는다

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "기존 작업 '$TaskName'을 지우고 다시 등록합니다."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Principal $Principal -Settings $Settings `
    -Description "리버풀 뉴스 앱: RSS 수집 + 번역 배치 (30분 주기, scheduler.py가 자체적으로 반복). PC 부팅 시 자동 시작, 로그아웃과 무관하게 SYSTEM 계정으로 실행." `
    | Out-Null

Write-Host "등록 완료. 확인:"
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskName $TaskName | Select-Object NextRunTime, LastRunTime, LastTaskResult
