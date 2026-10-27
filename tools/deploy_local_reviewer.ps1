param([string]$CandidateConfig = 'output/local-model/candidate-config.json',
      [ValidateSet('local','fast')][string]$Mode = 'local',
      [ValidateSet('local','off')][string]$HumanizerMode = 'local')
$ErrorActionPreference = 'Stop'
$reviewRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $reviewRoot
$targetBackend = if ($Mode -eq 'fast') { 'rules' } else { 'local' }
if ($Mode -eq 'fast') {
    $humanizerConfig = Join-Path $reviewRoot 'output\humanizer\config.json'
    $candidate = [pscustomobject]@{provider='rules'; model=$null}
    if ($HumanizerMode -eq 'local') {
        $humanizer = Get-Content -LiteralPath $humanizerConfig -Raw | ConvertFrom-Json
        $humanizerOrigin = [Uri]$humanizer.base_url
        if ($humanizerOrigin.Scheme -ne 'http' -or $humanizerOrigin.Host -notin @('127.0.0.1','localhost','::1')) { throw 'Humanizer must use loopback HTTP.' }
        $humanizerHealth = Invoke-RestMethod "$($humanizer.base_url)/health" -TimeoutSec 5
        $available = Invoke-RestMethod "$($humanizer.base_url)/v1/models" -TimeoutSec 5
        if ($humanizerHealth.status -ne 'ok' -or $available.data.id -notcontains $humanizer.model) { throw 'Dedicated humanizer is not ready with the expected model.' }
        $candidate = [pscustomobject]@{provider='rules+local-humanizer'; model=$(if ($humanizer.model_name) { $humanizer.model_name } else { $humanizer.model })}
    }
} else {
    $HumanizerMode = 'off'
    $candidate = Get-Content -LiteralPath $CandidateConfig -Raw | ConvertFrom-Json
if ($candidate.provider -eq 'ollama') {
    $available = Invoke-RestMethod "$($candidate.base_url)/api/tags"
    if ($available.models.name -notcontains $candidate.model) { throw 'Configured model is not available in the local runtime.' }
} elseif ($candidate.provider -eq 'llamacpp') {
    $available = Invoke-RestMethod "$($candidate.base_url)/v1/models"
    if ($available.data.id -notcontains $candidate.model) { throw 'Configured model is not available in the local text runtime.' }
} elseif ($candidate.provider -eq 'strata') {
    $strataSettings = Get-Content -LiteralPath $candidate.api_key_file -Raw | ConvertFrom-Json
    $available = Invoke-RestMethod "$($candidate.base_url)/v1/models" -Headers @{Authorization="Bearer $($strataSettings.api_key)"}
    if ($available.data.id -notcontains $candidate.model) { throw 'Strata did not report the configured loaded model.' }
} else { throw 'Unsupported local provider.' }
}
$deployStamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$deployDir = Join-Path $reviewRoot "output\deployments\$deployStamp-local-reviewer"
New-Item -ItemType Directory -Force $deployDir | Out-Null
$pidsFile = Join-Path $reviewRoot 'output\daemon_pids.json'
$daemons = Get-Content -LiteralPath $pidsFile -Raw | ConvertFrom-Json
$portalProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($daemons.ServerPID)"
if ($portalProcess -and $portalProcess.CommandLine -notlike '*run_portal.py*') { throw 'Portal PID no longer matches the recorded application.' }
$watcherProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($daemons.WatcherPID)"
if ($watcherProcess -and ($watcherProcess.CommandLine -notlike '*engine.review.cli watch*' -or $watcherProcess.CommandLine -notlike "*$reviewRoot\inbox*")) { throw 'Watcher PID no longer matches this workspace.' }
if ($Mode -eq 'local') { Copy-Item -LiteralPath $CandidateConfig -Destination 'output/local-model/config.json' -Force }
$runtimeProfile = Join-Path $reviewRoot 'output\review-runtime.json'
if (Test-Path -LiteralPath $runtimeProfile) { Copy-Item -LiteralPath $runtimeProfile -Destination (Join-Path $deployDir 'previous-runtime.json') }
$profile = @{backend=$targetBackend; humanizer=$HumanizerMode}
if ($HumanizerMode -eq 'local') { $profile.humanizer_config = $humanizerConfig }
$profile | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath "$runtimeProfile.new"
Move-Item -LiteralPath "$runtimeProfile.new" -Destination $runtimeProfile -Force
if ($portalProcess) { Stop-Process -Id $portalProcess.ProcessId }
if ($watcherProcess) { Stop-Process -Id $watcherProcess.ProcessId }
# Process termination can return before Windows releases the listening socket.
for ($releaseAttempt = 0; $releaseAttempt -lt 30; $releaseAttempt++) {
    $oldListener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if (-not $oldListener) { break }
    Start-Sleep -Milliseconds 500
}
if ($oldListener) { throw 'Port 8000 is still occupied; no replacement processes were started.' }
$env:TS_REVIEW_BACKEND = $targetBackend
$env:TS_HUMANIZER = $HumanizerMode
if ($HumanizerMode -eq 'local') { $env:TS_HUMANIZER_CONFIG = $humanizerConfig }
$env:TS_LOCAL_CONFIG = Join-Path $reviewRoot 'output\local-model\config.json'
$env:PYTHONIOENCODING = 'utf-8'
$pythonExe = (Get-Command python).Source
$portal = Start-Process -FilePath $pythonExe -ArgumentList '-u','run_portal.py' -WorkingDirectory $reviewRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $deployDir 'portal.stdout.log') -RedirectStandardError (Join-Path $deployDir 'portal.stderr.log') -PassThru
$watcher = Start-Process -FilePath $pythonExe -ArgumentList '-u','-m','engine.review.cli','watch','--inbox',"$reviewRoot\inbox",'--outbox',"$reviewRoot\outbox",'--interval','10','--backend',$targetBackend -WorkingDirectory $reviewRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $deployDir 'watcher.stdout.log') -RedirectStandardError (Join-Path $deployDir 'watcher.stderr.log') -PassThru
$daemons.ServerPID = $portal.Id
$daemons.WatcherPID = $watcher.Id
$daemons | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath $pidsFile
$portalReady = $false
for ($startupAttempt = 0; $startupAttempt -lt 30; $startupAttempt++) {
    $portal.Refresh()
    $watcher.Refresh()
    if ($portal.HasExited -or $watcher.HasExited) { throw "A deployed process exited during startup. Inspect logs in $deployDir" }
    try {
        $health = Invoke-WebRequest 'http://127.0.0.1:8000/thinkingstorm' -UseBasicParsing -TimeoutSec 2
        if ($health.StatusCode -eq 200) { $portalReady = $true; break }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $portalReady) { throw "Portal did not become ready. Inspect logs in $deployDir" }
$daemons.LastDeployedAtUtc = $deployStamp
$daemons | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath $pidsFile
@{ deployed_at_utc=$deployStamp; provider=$candidate.provider; model=$candidate.model; backend=$targetBackend; humanizer=$HumanizerMode; portal_pid=$portal.Id; watcher_pid=$watcher.Id; scope='localhost'; detector_score=$null } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $deployDir 'deployment.json')
$deployDir | Set-Content output/local-model/latest-deployment.txt
Write-Output "Local reviewer deployed. Portal PID $($portal.Id), watcher PID $($watcher.Id)."
