param([int]$Port = 11437, [switch]$StopStrata,
      [ValidateSet('instruct','completion')][string]$ModelType = 'instruct',
      [ValidateSet('4b','9b')][string]$EditorSize = '9b')
$ErrorActionPreference = 'Stop'
$reviewRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $reviewRoot 'output\humanizer'
$engineDir = Join-Path $runtimeDir 'llamacpp'
$engine = Join-Path $engineDir 'llama-server.exe'
$weightsName = if ($ModelType -eq 'instruct') { 'qwen3.5-4b-q4.gguf' } else { 'humanizer-12b-IQ2_XS-QAT.gguf' }
$weights = Join-Path $runtimeDir $weightsName
if ($ModelType -eq 'instruct' -and $EditorSize -eq '9b') {
    $weightsName = 'sha256-02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d'
    $weights = Join-Path $reviewRoot "output\local-model\models\blobs\$weightsName"
    if (-not (Test-Path -LiteralPath $weights)) { $weightsName = 'qwen3.5-9b-q4.gguf'; $weights = Join-Path $runtimeDir $weightsName }
}
$alias = if ($ModelType -eq 'instruct') { 'thinkingstorm-editor' } else { 'thinkingstorm-humanizer' }
$pidFile = Join-Path $runtimeDir 'server.pid'
if (Test-Path -LiteralPath $pidFile) {
    $recorded = Get-CimInstance Win32_Process -Filter "ProcessId=$([int](Get-Content -LiteralPath $pidFile -Raw))"
    if ($recorded -and $recorded.CommandLine -like "*$weightsName*") {
        Write-Output "Recorded humanizer is already running (PID $($recorded.ProcessId))."
        exit 0
    }
    if ($recorded) { throw 'A different recorded model is still running. Stop that verified workspace process before switching candidates.' }
}
if (-not (Test-Path -LiteralPath $engine)) { throw 'The verified official llama.cpp b11335 runtime is missing; see the humanizer setup guide.' }
if (-not (Test-Path -LiteralPath $weights)) { throw 'Download the pinned humanizer model first; see vendor/humanizer/README.md.' }
$expectedHash = if ($ModelType -eq 'instruct') { 'A9D0A3E1D8C91732A3812BECD31F8D4A8FF57414903F226306069F0437E2AC50' } else { '383E5CA8F1F48AB5F65013ADBC1965FA70D1D1AFA6C45D932C34B854E38EDBB5' }
if ($ModelType -eq 'instruct' -and $EditorSize -eq '9b') { $expectedHash = '02D45DC1CF451BA2475AC33B301C2DD8F985ABE4C182CE04A1F2F5BF0260278D' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $weights).Hash -ne $expectedHash) { throw 'Humanizer checksum mismatch.' }
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "Port $Port is already occupied; no process was stopped." }
if ($StopStrata) {
    $strataPidFile = Join-Path $reviewRoot 'output\local-model\strata-server.pid'
    if (Test-Path -LiteralPath $strataPidFile) {
        $strataPid = [int](Get-Content -LiteralPath $strataPidFile -Raw)
        $allProcesses = @(Get-CimInstance Win32_Process)
        $strataOwner = $allProcesses | Where-Object ProcessId -eq $strataPid
        if ($strataOwner) {
            if ($strataOwner.CommandLine -notlike '*Strata\serve\server.py*strata-runtime.private.json*') { throw 'Recorded Strata process identity changed.' }
            $ownedIds = @($strataPid)
            do {
                $children = @($allProcesses | Where-Object { $_.ParentProcessId -in $ownedIds -and $_.ProcessId -notin $ownedIds })
                $ownedIds += @($children.ProcessId)
            } while ($children.Count)
            $ownedProcesses = @($allProcesses | Where-Object { $_.ProcessId -in $ownedIds -and $_.Name -ne 'conhost.exe' })
            foreach ($ownedProcess in $ownedProcesses) {
                if ($ownedProcess.CommandLine -notlike '*Strata\serve\server.py*strata-runtime.private.json*' -and
                    $ownedProcess.CommandLine -notlike "*Strata\engine\strata.exe*$reviewRoot\output\local-model\strata-data*") { throw 'Unexpected descendant of the Strata reviewer; nothing stopped.' }
            }
            foreach ($ownedProcess in $ownedProcesses) { Stop-Process -Id $ownedProcess.ProcessId -ErrorAction SilentlyContinue }
            Write-Output 'Stopped the verified workspace Strata reviewer to release its GPU memory.'
        }
    }
}
$env:PATH = $engineDir + ';' + $env:PATH
$env:GGML_BACKEND_PATH = $engineDir
$arguments = @('--model', ('"' + $weights + '"'), '--alias', $alias,
    '--host', '127.0.0.1', '--port', "$Port", '--offline', '--no-webui', '--slots',
    '--ctx-size', '4096', '--parallel', '1', '--threads', '8',
    '--batch-size', '512', '--ubatch-size', '256', '--device', 'CUDA0', '--gpu-layers', '99',
    '--fit', 'on', '--fit-target', '768', '--flash-attn', 'on', '--log-verbosity', '4')
if ($ModelType -eq 'instruct') { $arguments += @('--jinja', '--reasoning-budget', '0') }
$process = Start-Process -FilePath $engine -ArgumentList $arguments -WorkingDirectory $reviewRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'server.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'server.stderr.log') -PassThru
$process.Id | Set-Content -LiteralPath $pidFile
$promptName = if ($ModelType -eq 'instruct') { 'editor_prompt.txt' } else { 'prompt_format.json' }
@{base_url="http://127.0.0.1:$Port"; model=$alias; model_name=$(if ($ModelType -eq 'instruct') { "qwen3.5:$EditorSize" } else { 'humanizer-12b-IQ2_XS-QAT' }); provider=$ModelType; prompt_path=(Join-Path $reviewRoot "vendor\humanizer\$promptName"); budget_seconds=180; call_timeout_seconds=30} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $runtimeDir 'config.json')
Write-Output "Started dedicated humanizer PID $($process.Id) on localhost:$Port."
