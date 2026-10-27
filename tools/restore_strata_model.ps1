param(
    [string]$StrataRoot = "$env:USERPROFILE\Strata",
    [int]$Context = 16384
)
$ErrorActionPreference = 'Stop'
$reviewRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $reviewRoot 'output\local-model'
New-Item -ItemType Directory -Force $runtimeDir | Out-Null
$existing = Join-Path $StrataRoot 'strata-iq2_xs.json'
$backup = Join-Path $runtimeDir 'strata-original-config.private.json'
if ((Test-Path -LiteralPath $existing) -and -not (Test-Path -LiteralPath $backup)) {
    Copy-Item -LiteralPath $existing -Destination $backup
}
$python = Join-Path $StrataRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Install Strata first; this restores the model for an existing installation.' }
& $python (Join-Path $StrataRoot 'setup.py') --yes --setup --family qwen --model IQ2_XS --context $Context --vision no --data-dir (Join-Path $runtimeDir 'strata-data') --host 127.0.0.1 --port 11436 --vram-reserve-mib 850 --no-start
if ($LASTEXITCODE) { throw 'Strata model restoration failed. Rerun to resume the download.' }
Write-Output 'Strata model restored. Start it with tools/start_strata_reviewer.ps1 before deployment.'
