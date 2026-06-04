param(
    [string]$TaskName = "CassDemandPipelineDaily",
    [string]$At = "06:00",
    [switch]$SkipCollect,
    [switch]$SkipChronos
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DailyScript = Join-Path $ScriptDir "run_daily_pipeline.ps1"

$ArgumentList = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "`"$DailyScript`""
)
if ($SkipCollect) {
    $ArgumentList += "-SkipCollect"
}
if ($SkipChronos) {
    $ArgumentList += "-SkipChronos"
}

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ($ArgumentList -join " ")
$Trigger = New-ScheduledTaskTrigger -Daily -At $At
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel LeastPrivilege

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Force | Out-Null
Write-Output "Registered scheduled task '$TaskName' at $At."
Write-Output "Script: $DailyScript"
