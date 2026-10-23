# Launch Apex Service Monitor as an independent background daemon
# Runs completely decoupled from AGY or any terminal window.

$ProjectDir = "C:\Users\shashank\edtech-review-engine"
Set-Location -Path $ProjectDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  STARTING APEX SERVICE MONITOR (HOST SUPERVISOR DAEMON) " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Stop any existing supervisor first
Get-Process | Where-Object { $_.CommandLine -like "*apex_service_monitor.py*" } | Stop-Process -Force -ErrorAction SilentlyContinue

$monitorScript = "$ProjectDir\orchestrator\apex_service_monitor.py"
$proc = Start-Process -FilePath "python" -ArgumentList "`"$monitorScript`"" -WorkingDirectory $ProjectDir -PassThru -WindowStyle Hidden

Write-Host "[OK] Apex Service Monitor is now running detached with PID: $($proc.Id)" -ForegroundColor Green
Write-Host "     This process is independent of the AGY chat and will keep all services alive 24/7." -ForegroundColor Green
Write-Host ""
Write-Host "Waiting 6 seconds for initial healthcheck and tunnel discovery..."
Start-Sleep -Seconds 6

$statusFile = "$ProjectDir\output\service_status.json"
if (Test-Path $statusFile) {
    Get-Content $statusFile
} else {
    Write-Host "[*] Status file initializing. View output\apex_monitor.log for details."
}
