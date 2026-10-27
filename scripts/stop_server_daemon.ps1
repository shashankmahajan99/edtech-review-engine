# Gracefully stops all Apex Review background server processes

$ProjectDir = if ($PSScriptRoot) { (Resolve-Path "$PSScriptRoot\..").Path } else { (Get-Location).Path }
$pidFile = Join-Path $ProjectDir "output\daemon_pids.json"

if (Test-Path $pidFile) {
    $pids = Get-Content $pidFile | ConvertFrom-Json
    Write-Host "Stopping background server processes..." -ForegroundColor Yellow

    if ($pids.ServerPID) { Stop-Process -Id $pids.ServerPID -Force -ErrorAction SilentlyContinue; Write-Host "Stopped Server (PID: $($pids.ServerPID))" }
    if ($pids.TunnelPID) { Stop-Process -Id $pids.TunnelPID -Force -ErrorAction SilentlyContinue; Write-Host "Stopped Tunnel (PID: $($pids.TunnelPID))" }
    if ($pids.PollerPID) { Stop-Process -Id $pids.PollerPID -Force -ErrorAction SilentlyContinue; Write-Host "Stopped Poller (PID: $($pids.PollerPID))" }

    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] All background services stopped." -ForegroundColor Green
} else {
    Write-Host "[!] No active daemon PID file found." -ForegroundColor Yellow
}
