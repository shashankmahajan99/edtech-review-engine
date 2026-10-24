# Start the ThinkingStorm inbox watcher in the background.
# Drop .docx files into .\inbox and pick deliverables up from .\outbox.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$inbox = Join-Path $root "inbox"
$outbox = Join-Path $root "outbox"
$log = Join-Path $outbox "watcher.log"
New-Item -ItemType Directory -Force -Path $inbox, $outbox | Out-Null

$stopFile = Join-Path $inbox "STOP"
if (Test-Path $stopFile) { Remove-Item $stopFile -Force }

$python = (Get-Command python).Source
$cliArgs = @("-u", "-m", "engine.review.cli", "watch", "--inbox", $inbox, "--outbox", $outbox, "--interval", "10")

$existing = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -like "*engine.review.cli watch*" }
if ($existing) {
    Write-Host "Watcher already running (PID $($existing.ProcessId -join ', '))."
    exit 0
}

$proc = Start-Process -FilePath $python -ArgumentList $cliArgs -WorkingDirectory $root `
    -RedirectStandardOutput $log -RedirectStandardError "$log.err" -PassThru -WindowStyle Hidden

$proc.Id | Set-Content (Join-Path $outbox "watcher.pid")
Write-Host "Watcher started (PID $($proc.Id))."
Write-Host "  inbox : $inbox"
Write-Host "  outbox: $outbox"
Write-Host "  log   : $log"
