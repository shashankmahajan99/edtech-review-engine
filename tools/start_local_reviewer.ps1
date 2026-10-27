param([int]$ReasoningBudget = 1024)
$ErrorActionPreference = 'Stop'
$reviewRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $reviewRoot 'output\local-model'
$manifestPath = Join-Path $runtimeDir 'models\manifests\registry.ollama.ai\library\qwen3.5\9b'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$language = $manifest.layers | Where-Object mediaType -eq 'application/vnd.ollama.image.model' | Select-Object -First 1
if (-not $language) { throw 'Downloaded Qwen language weights were not found.' }
$weights = Join-Path $runtimeDir ('models\blobs\' + $language.digest.Replace(':','-'))
$engine = Join-Path $runtimeDir 'ollama\lib\ollama\llama-server.exe'
if (-not (Test-Path -LiteralPath $engine)) { throw 'Install the official portable runtime with setup_local_reviewer.ps1 first.' }
try {
    $health = Invoke-RestMethod 'http://127.0.0.1:11435/health'
    if ($health.status -eq 'ok') { Write-Output 'Local text reviewer already running.'; exit 0 }
} catch {}
$env:PATH = (Join-Path $runtimeDir 'ollama\lib\ollama\cuda_v13') + ';' + $env:PATH
$env:GGML_BACKEND_PATH = Join-Path $runtimeDir 'ollama\lib\ollama\cuda_v13\ggml-cuda.dll'
$arguments = @('--model', ('"' + $weights + '"'), '--alias', 'thinkingstorm-qwen3.5:9b',
    '--host', '127.0.0.1', '--port', '11435', '--offline', '--no-webui',
    '--ctx-size', '16384', '--parallel', '1', '--load-mode', 'none', '--threads', '8', '--batch-size', '512',
    '--ubatch-size', '256', '--device', 'CUDA0', '--gpu-layers', '22', '--fit', 'on', '--fit-target', '768', '--flash-attn', 'on', '--log-verbosity', '4',
    '--reasoning-budget', "$ReasoningBudget")
$process = Start-Process -FilePath $engine -ArgumentList $arguments -WorkingDirectory $reviewRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'reviewer.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'reviewer.stderr.log') -PassThru
$process.Id | Set-Content (Join-Path $runtimeDir 'reviewer.pid')
Write-Output "Started local text reviewer PID $($process.Id); reasoning budget $ReasoningBudget tokens."
