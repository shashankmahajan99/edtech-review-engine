param(
    [string]$StrataRoot = "$env:USERPROFILE\Strata",
    [string]$DataDir = '',
    [int]$Port = 11436,
    [int]$VramReserveMiB = 850,
    [switch]$NoMtp
)
$ErrorActionPreference = 'Stop'
$reviewRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $reviewRoot 'output\local-model'
$source = Join-Path $StrataRoot 'strata-iq2_xs.json'
$settings = Get-Content -LiteralPath $source -Raw | ConvertFrom-Json
$privateConfig = Join-Path $runtimeDir 'strata-runtime.private.json'
$pidFile = Join-Path $runtimeDir 'strata-server.pid'
if ((Test-Path -LiteralPath $privateConfig) -and (Test-Path -LiteralPath $pidFile)) {
    $existing = Get-Content -LiteralPath $privateConfig -Raw | ConvertFrom-Json
    $recordedPid = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
    $owned = Get-CimInstance Win32_Process -Filter "ProcessId=$recordedPid"
    if ($owned.CommandLine -like '*serve\server.py*strata-runtime.private.json*' -and $existing.port -eq $Port) {
        $existingHeaders = @{}
        if ($existing.api_key) { $existingHeaders.Authorization = "Bearer $($existing.api_key)" }
        $loadedModels = $null
        try { $loadedModels = Invoke-RestMethod "http://127.0.0.1:$Port/v1/models" -Headers $existingHeaders -TimeoutSec 5 } catch {}
        if ($loadedModels.data -and $loadedModels.data.id -notcontains $settings.model_name) { throw 'The existing runtime is serving a different model.' }
        Write-Output 'The recorded Strata reviewer is already running or loading; its private configuration was preserved.'
        exit 0
    }
}
if (-not $DataDir -and (Test-Path -LiteralPath $privateConfig)) {
    # Reuse the restored workspace paths and hardware profile after a reboot.
    # The original Strata configuration may still name its old, absent data root.
    $settings = Get-Content -LiteralPath $privateConfig -Raw | ConvertFrom-Json
}
if ($DataDir) {
    $resolvedData = (Resolve-Path -LiteralPath $DataDir).Path
    $nativePosition = [Array]::IndexOf($settings.args, '--native')
    if ($nativePosition -lt 0) { throw 'Cannot locate the native model in the existing Strata configuration.' }
    $oldData = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $settings.args[$nativePosition + 1]))
    $settings.args = @($settings.args | ForEach-Object {
        if ($_.StartsWith($oldData, [StringComparison]::OrdinalIgnoreCase)) { $resolvedData + $_.Substring($oldData.Length) } else { $_ }
    })
    if ($settings.tokenizer.StartsWith($oldData, [StringComparison]::OrdinalIgnoreCase)) {
        $settings.tokenizer = $resolvedData + $settings.tokenizer.Substring($oldData.Length)
    }
}
if ($NoMtp) {
    $draftPosition = [Array]::IndexOf($settings.args, '--mtp')
    if ($draftPosition -ge 0) {
        $settings.args = @($settings.args[0..($settings.args.Count - 1)] | Select-Object -Index (0..($settings.args.Count - 1) | Where-Object { $_ -ne $draftPosition -and $_ -ne ($draftPosition + 1) }))
    }
}
$reservePosition = [Array]::IndexOf($settings.args, '--vram-reserve-mib')
if ($reservePosition -ge 0) { $settings.args[$reservePosition + 1] = "$VramReserveMiB" }
else { $settings.args += @('--vram-reserve-mib', "$VramReserveMiB") }
foreach ($flag in @('--pack', '--native', '--ple-gguf', '--mtp')) {
    $position = [Array]::IndexOf($settings.args, $flag)
    if ($position -ge 0 -and -not (Test-Path -LiteralPath $settings.args[$position + 1])) {
        throw "Strata data for $flag is missing. Run tools/restore_strata_model.ps1 first."
    }
}
$settings.host = '127.0.0.1'
$settings.port = $Port
$settings.log = Join-Path $runtimeDir 'strata-engine.log'
$settings | Add-Member -NotePropertyName reasoning_budget_tokens -NotePropertyValue 1024 -Force
[IO.File]::WriteAllText($privateConfig, ($settings | ConvertTo-Json -Depth 12), [Text.UTF8Encoding]::new($false))
$reviewConfig = @{
    provider='strata'; model=$settings.model_name; base_url="http://127.0.0.1:$Port"
    api_key_file=$privateConfig; examples_path=(Join-Path $runtimeDir 'examples.json')
    trace_dir=(Join-Path $runtimeDir 'strata-traces'); context_tokens=16384
    reasoning_budget_tokens=1024; timeout_seconds=1200
}
$reviewConfig | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $runtimeDir 'candidate-config.json')
$headers = @{}
if ($settings.api_key) { $headers.Authorization = "Bearer $($settings.api_key)" }
$models = $null
try {
    $models = Invoke-RestMethod "http://127.0.0.1:$Port/v1/models" -Headers $headers -TimeoutSec 5
} catch {}
if ($null -ne $models) {
    if ($models.data -and $models.data.id -notcontains $settings.model_name) { throw "Port $Port is serving a different model; leave that process running and select a separate port." }
    Write-Output 'Strata is already running or loading. No duplicate server was started.'
    exit 0
}
$python = Join-Path $StrataRoot '.venv\Scripts\python.exe'
$arguments = @('-u', ('"' + (Join-Path $StrataRoot 'serve\server.py') + '"'), '--engine', 'strata', '--config', ('"' + $privateConfig + '"'), '--host', '127.0.0.1', '--port', "$Port")
$process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $StrataRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'strata-server.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'strata-server.stderr.log') -PassThru
$process.Id | Set-Content (Join-Path $runtimeDir 'strata-server.pid')
Write-Output "Started Strata reviewer PID $($process.Id). Model loading may take several minutes."
