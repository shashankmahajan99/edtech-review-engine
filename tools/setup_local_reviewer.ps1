param(
    [ValidateSet('llamacpp', 'ollama', 'strata')][string]$Provider = 'strata',
    [string]$Model = 'qwen3.5:9b',
    [string]$Examples = "$env:USERPROFILE\Downloads\Doc Examples",
    [string]$StrataConfig = "$env:USERPROFILE\Strata\strata-iq2_xs.json"
)
$ErrorActionPreference = 'Stop'
$reviewRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $reviewRoot 'output\local-model'
New-Item -ItemType Directory -Force $runtimeDir | Out-Null
$reviewConfig = @{
    provider = $Provider
    model = $Model
    base_url = 'http://127.0.0.1:11434'
    examples_path = (Join-Path $runtimeDir 'examples.json')
    timeout_seconds = 1200
}
if ($Provider -eq 'strata') {
    $strataSettings = Get-Content -LiteralPath $StrataConfig -Raw | ConvertFrom-Json
    $reviewConfig.base_url = "http://127.0.0.1:$($strataSettings.port)"
    $reviewConfig.model = $strataSettings.model_name
    $reviewConfig.api_key_file = $StrataConfig
    # Use the existing runtime. Do not alter its configuration or expose a port.
    Invoke-RestMethod -Uri "$($reviewConfig.base_url)/v1/models" -Headers @{Authorization="Bearer $($strataSettings.api_key)"} | Out-Null
} else {
    $runtimeExe = Join-Path $runtimeDir 'ollama\ollama.exe'
    if (-not (Test-Path -LiteralPath $runtimeExe)) {
        $archive = Join-Path $runtimeDir 'ollama-verified.zip'
        if (-not (Test-Path -LiteralPath $archive)) {
            & curl.exe --fail --location --retry 3 --output $archive 'https://github.com/ollama/ollama/releases/download/v0.40.11/ollama-windows-amd64.zip'
            if ($LASTEXITCODE) { throw 'Ollama download failed.' }
        }
        if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'bda4a493ba8a7c24d57263cd843cd68cee84f44aed4299eeed532acad7eda12a') {
            throw 'Ollama checksum verification failed.'
        }
        Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $runtimeDir 'ollama') -Force
    }
    $env:OLLAMA_MODELS = Join-Path $runtimeDir 'models'
    $env:OLLAMA_HOST = '127.0.0.1:11434'
    $env:OLLAMA_NO_CLOUD = '1'
    $env:OLLAMA_NUM_PARALLEL = '1'
    $env:OLLAMA_MAX_LOADED_MODELS = '1'
    try { Invoke-RestMethod "$($reviewConfig.base_url)/api/version" | Out-Null }
    catch {
        $runtimeProcess = Start-Process -FilePath $runtimeExe -ArgumentList 'serve' -WorkingDirectory $reviewRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'ollama.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'ollama.stderr.log') -PassThru
        $runtimeProcess.Id | Set-Content (Join-Path $runtimeDir 'ollama.pid')
        $ready = $false
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            try { Invoke-RestMethod "$($reviewConfig.base_url)/api/version" | Out-Null; $ready = $true; break }
            catch { Start-Sleep -Seconds 1 }
        }
        if (-not $ready) { throw 'Local runtime did not start; inspect output/local-model/ollama.stderr.log.' }
    }
    & $runtimeExe pull $Model
    if ($LASTEXITCODE) { throw 'Model download failed.' }
    if ($Model -eq 'qwen3.5:9b') {
        & python (Join-Path $PSScriptRoot 'create_text_reviewer.py')
        if ($LASTEXITCODE) { throw 'Text-only serving alias could not be created.' }
        $reviewConfig.model = 'thinkingstorm-qwen3.5:9b'
    }
    if ($Provider -eq 'llamacpp') {
        if ($Model -ne 'qwen3.5:9b') { throw 'The bundled text server launcher currently supports qwen3.5:9b.' }
        & $runtimeExe stop 'thinkingstorm-qwen3.5:9b'
        & (Join-Path $PSScriptRoot 'start_local_reviewer.ps1')
        $reviewConfig.base_url = 'http://127.0.0.1:11435'
    }
}
& python (Join-Path $PSScriptRoot 'index_local_review_examples.py') $Examples
if ($LASTEXITCODE) { throw 'Human example indexing failed.' }
$reviewConfig | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $runtimeDir 'config.json')
Write-Output "Local reviewer configured: $Provider / $($reviewConfig.model)."
Write-Output 'Set TS_REVIEW_BACKEND=local for CLI use. Studio reads the configured backend after deployment.'
