# 24/7 Apex Enterprise Daemon Supervisor
# Starts FastAPI server, Cloudflare HTTPS public tunnel, poller watchdog, and Apex Service Monitor.

$ErrorActionPreference = "Continue"
$ProjectDir = if ($PSScriptRoot) { (Resolve-Path "$PSScriptRoot\..").Path } else { (Get-Location).Path }
Set-Location -Path $ProjectDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  APEX ACADEMIC REVIEW DESK - 24/7 PRODUCTION DAEMON     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Cleanup existing instances first
Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

$cloudflaredBin = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
if (-not (Test-Path $cloudflaredBin)) {
    $cloudflaredBin = "cloudflared"
}

$tunnelLog = "$ProjectDir\output\tunnel.log"
if (Test-Path $tunnelLog) {
    Remove-Item $tunnelLog -Force -ErrorAction SilentlyContinue
}

# 1. Start FastAPI Web Server
Write-Host "[1/4] Starting FastAPI Web Server on http://127.0.0.1:8000..." -ForegroundColor Yellow
$serverProcess = Start-Process -FilePath "python" -ArgumentList "run_portal.py" -WorkingDirectory $ProjectDir -PassThru -WindowStyle Hidden

# 2. Start Cloudflare Tunnel via shell redirection
Write-Host "[2/4] Starting Cloudflare Edge HTTPS Tunnel..." -ForegroundColor Yellow
$tunnelProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"`"$cloudflaredBin`" tunnel --url http://127.0.0.1:8000 > `"$tunnelLog`" 2>&1`"" -WorkingDirectory $ProjectDir -PassThru -WindowStyle Hidden

# 3. Start Poller Daemon
Write-Host "[3/4] Starting Autonomous Poller Watchdog..." -ForegroundColor Yellow
$pollerProcess = Start-Process -FilePath "python" -ArgumentList "run_poller.py 30" -WorkingDirectory $ProjectDir -PassThru -WindowStyle Hidden

# 4. Start Apex Service Monitor
Write-Host "[4/4] Starting Apex Service Monitor Host Supervisor..." -ForegroundColor Yellow
$monitorProcess = Start-Process -FilePath "python" -ArgumentList "orchestrator\apex_service_monitor.py" -WorkingDirectory $ProjectDir -PassThru -WindowStyle Hidden

# Save PIDs
$pids = [PSCustomObject]@{
    ServerPID  = $serverProcess.Id
    TunnelPID  = $tunnelProcess.Id
    PollerPID  = $pollerProcess.Id
    MonitorPID = $monitorProcess.Id
    StartedAt  = (Get-Date).ToString("s")
}
$pids | ConvertTo-Json | Set-Content "$ProjectDir\output\daemon_pids.json"

Write-Host ""
Write-Host "[OK] All 4 independent services spawned detached from AGY!" -ForegroundColor Green
Write-Host "     Server PID  : $($serverProcess.Id)"
Write-Host "     Tunnel PID  : $($tunnelProcess.Id)"
Write-Host "     Poller PID  : $($pollerProcess.Id)"
Write-Host "     Monitor PID : $($monitorProcess.Id)"
Write-Host ""
Write-Host "Waiting 8 seconds for tunnel registration..."
Start-Sleep -Seconds 8

if (Test-Path $tunnelLog) {
    $content = Get-Content $tunnelLog -Raw
    $urls = [regex]::Matches($content, "https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    if ($urls.Count -gt 0) {
        $liveUrl = $urls[$urls.Count - 1].Value
        Write-Host "==========================================================" -ForegroundColor Green
        Write-Host "  LIVE GLOBAL HTTPS URL: $liveUrl" -ForegroundColor White -BackgroundColor DarkBlue
        Write-Host "==========================================================" -ForegroundColor Green
    } else {
        Write-Host "[*] Tunnel registered. Check output\tunnel.log for URL." -ForegroundColor Yellow
    }
}
