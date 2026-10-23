$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$log = "C:\Users\shashank\edtech-review-engine\output\tunnel.log"

Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Start-Process -FilePath $cloudflared -ArgumentList "tunnel --url http://127.0.0.1:8000" -RedirectStandardError $log -WindowStyle Hidden
Start-Sleep -Seconds 6

if (Test-Path $log) {
    Get-Content $log
} else {
    Write-Host "Log not created"
}
