param(
    [switch]$SkipCollect,
    [switch]$SkipChronos
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $LogDir "cass_pipeline_$Timestamp.log"

$ArgsList = @((Join-Path $ScriptDir "run_pipeline.py"))
if ($SkipCollect) {
    $ArgsList += "--skip-collect"
}
if ($SkipChronos) {
    $ArgsList += "--skip-chronos"
}

Push-Location $Root
try {
    "Started: $(Get-Date -Format o)" | Tee-Object -FilePath $LogPath
    "Command: python $($ArgsList -join ' ')" | Tee-Object -FilePath $LogPath -Append
    $ArgumentString = ($ArgsList | ForEach-Object {
        if ($_ -match "\s") {
            '"' + ($_ -replace '"', '\"') + '"'
        }
        else {
            $_
        }
    }) -join " "
    $Psi = New-Object System.Diagnostics.ProcessStartInfo
    $Psi.FileName = "python"
    $Psi.Arguments = $ArgumentString
    $Psi.WorkingDirectory = $Root
    $Psi.UseShellExecute = $false
    $Psi.RedirectStandardOutput = $true
    $Psi.RedirectStandardError = $true
    $Process = New-Object System.Diagnostics.Process
    $Process.StartInfo = $Psi
    [void]$Process.Start()
    $StdoutText = $Process.StandardOutput.ReadToEnd()
    $StderrText = $Process.StandardError.ReadToEnd()
    $Process.WaitForExit()
    if ($StdoutText) {
        $StdoutText.TrimEnd() | Tee-Object -FilePath $LogPath -Append
    }
    if ($StderrText) {
        $StderrText.TrimEnd() | Tee-Object -FilePath $LogPath -Append
    }
    $ExitCode = $Process.ExitCode
    if ($ExitCode -ne 0) {
        throw "Pipeline failed with exit code $ExitCode"
    }
    "Finished: $(Get-Date -Format o)" | Tee-Object -FilePath $LogPath -Append
}
finally {
    Pop-Location
}
