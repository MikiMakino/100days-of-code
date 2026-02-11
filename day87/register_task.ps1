#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Day 87 Email Monitor をタスクスケジューラに登録する。

.DESCRIPTION
    5分おきに email_monitor.py を実行するタスクを登録する。
    「ユーザーがログオンしている場合のみ実行」で登録される（Outlook COMに必要）。

.NOTES
    管理者権限の PowerShell で実行してください:
        powershell -ExecutionPolicy Bypass -File register_task.ps1

    登録解除:
        Unregister-ScheduledTask -TaskName "Day87_EmailMonitor" -Confirm:$false
#>

# --- 設定 ---
$TaskName        = "Day87_EmailMonitor"
$Description     = "Outlookメール監視: 特定件名のメールを5分おきにチェックし、添付保存・台帳記録を行う"
$ScriptDir       = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PythonExe       = "python"                          # フルパスでもOK: "C:\Python312\python.exe"
$ScriptPath      = Join-Path $ScriptDir "email_monitor.py"
$IntervalMinutes = 5

# --- python.exe の存在確認 ---
$pythonPath = Get-Command $PythonExe -ErrorAction SilentlyContinue
if (-not $pythonPath) {
    Write-Error "python.exe が見つかりません。PATHを確認するか、`$PythonExe にフルパスを指定してください。"
    exit 1
}
Write-Host "Python: $($pythonPath.Source)" -ForegroundColor Cyan

# --- email_monitor.py の存在確認 ---
if (-not (Test-Path $ScriptPath)) {
    Write-Error "email_monitor.py が見つかりません: $ScriptPath"
    exit 1
}
Write-Host "Script: $ScriptPath" -ForegroundColor Cyan
Write-Host "Interval: ${IntervalMinutes} minutes" -ForegroundColor Cyan

# --- 既存タスクの確認 ---
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host ""
    Write-Host "既存のタスク '$TaskName' が見つかりました。" -ForegroundColor Yellow
    $choice = Read-Host "上書きしますか？ (Y/N)"
    if ($choice -ne "Y" -and $choice -ne "y") {
        Write-Host "キャンセルしました。" -ForegroundColor Yellow
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "既存タスクを削除しました。" -ForegroundColor Yellow
}

# --- トリガー: N分おきに繰り返し ---
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

# --- アクション: python email_monitor.py ---
$action = New-ScheduledTaskAction `
    -Execute $pythonPath.Source `
    -Argument "`"$ScriptPath`"" `
    -WorkingDirectory $ScriptDir

# --- 設定 ---
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

# --- 登録 ---
Register-ScheduledTask `
    -TaskName $TaskName `
    -Description $Description `
    -Trigger $trigger `
    -Action $action `
    -Settings $settings `
    -RunLevel Limited

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " タスク '$TaskName' を登録しました" -ForegroundColor Green
Write-Host " 実行間隔: ${IntervalMinutes}分" -ForegroundColor Green
Write-Host " 作業フォルダ: $ScriptDir" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "確認: Get-ScheduledTask -TaskName '$TaskName' | Format-List"
Write-Host "手動実行: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "登録解除: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
