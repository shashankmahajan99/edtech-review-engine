param([ValidateSet('4b','9b')][string]$EditorSize = '9b')
$ErrorActionPreference = 'Stop'
$reviewRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $reviewRoot 'output\humanizer'
New-Item -ItemType Directory -Force $runtimeDir | Out-Null
$artifacts = @(
    @{file='llama-b11335-cuda.zip'; sha='95c11f1371a81a3f2807e5827e72961850b395dc8bcc0112601fed9eb2f979b1'; url='https://github.com/ggml-org/llama.cpp/releases/download/b11335/llama-b11335-bin-win-cuda-12.4-x64.zip'},
    @{file='cudart-b11335.zip'; sha='8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6'; url='https://github.com/ggml-org/llama.cpp/releases/download/b11335/cudart-llama-bin-win-cuda-12.4-x64.zip'}
)
$editorDigest = if ($EditorSize -eq '9b') { '02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d' } else { 'a9d0a3e1d8c91732a3812becd31f8d4a8ff57414903f226306069f0437e2ac50' }
$cachedEditor = Join-Path $reviewRoot "output\local-model\models\blobs\sha256-$editorDigest"
if (-not (Test-Path -LiteralPath $cachedEditor) -or (Get-FileHash -LiteralPath $cachedEditor -Algorithm SHA256).Hash.ToLowerInvariant() -ne $editorDigest) {
    $artifacts += @{file="qwen3.5-$EditorSize-q4.gguf"; sha=$editorDigest; url="https://registry.ollama.ai/v2/library/qwen3.5/blobs/sha256:$editorDigest"}
}
foreach ($artifact in $artifacts) {
    $target = Join-Path $runtimeDir $artifact.file
    if (-not (Test-Path -LiteralPath $target) -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $artifact.sha) {
        & curl.exe --fail --location --retry 3 --continue-at - --output $target $artifact.url
        if ($LASTEXITCODE) { throw "Download failed for $($artifact.file)." }
    }
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $artifact.sha) { throw "Checksum mismatch for $($artifact.file); inspect the cached download before retrying." }
}
$engineDir = Join-Path $runtimeDir 'llamacpp'
if (-not (Test-Path -LiteralPath (Join-Path $engineDir 'llama-server.exe'))) {
    Expand-Archive -LiteralPath (Join-Path $runtimeDir 'llama-b11335-cuda.zip') -DestinationPath $engineDir -Force
    Expand-Archive -LiteralPath (Join-Path $runtimeDir 'cudart-b11335.zip') -DestinationPath $engineDir -Force
}
Write-Output 'Verified editor weights and official CUDA runtime. Start with tools/start_feedback_humanizer.ps1.'
