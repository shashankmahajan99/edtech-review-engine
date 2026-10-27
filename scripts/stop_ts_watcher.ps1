# Stop the ThinkingStorm inbox watcher started by start_ts_watcher.ps1.

$root = if ($PSScriptRoot) { (Resolve-Path "$PSScriptRoot\..").Path } else { (Get-Location).Path }
$outbox = Join-Path $root "outbox"
$pidFile = Join-Path $outbox "watcher.pid"

$stopped = $false
if (Test-Path $pidFile) {
    $watcherPid = Get-Content $pidFile | Select-Object -First 1
    if ($watcherPid) {
        try {
            Stop-Process -Id ([int]$watcherPid) -Force -ErrorAction Stop
            Write-Host "Stopped watcher PID $watcherPid."
            $stopped = $true
        } catch {
            Write-Host "PID $watcherPid not running."
        }
    }
    Remove-Item $pidFile -Force
}

if (-not $stopped) {
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
        Where-Object { $_.CommandLine -like "*engine.review.cli watch*" } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force
            Write-Host "Stopped watcher PID $($_.ProcessId)."
            $stopped = $true
        }
}

if (-not $stopped) { Write-Host "No watcher was running." }
