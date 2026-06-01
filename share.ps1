# Starts PredictX and prints a public share link (requires cloudflared).
# Install: winget install Cloudflare.cloudflared

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "cloudflared is not installed." -ForegroundColor Yellow
    Write-Host "Install it, then run this script again:"
    Write-Host "  winget install --id Cloudflare.cloudflared"
    Write-Host ""
    Write-Host "Or use permanent hosting — see DEPLOY.md (Render, free)."
    exit 1
}

Write-Host "Starting PredictX on http://localhost:8000 ..."
$app = Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory $root -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Opening public tunnel — copy the https://....trycloudflare.com URL below:" -ForegroundColor Cyan
Write-Host "(Press Ctrl+C to stop the tunnel; the app will keep running in the background.)"
Write-Host ""

try {
    cloudflared tunnel --url http://localhost:8000
} finally {
    Write-Host "Stopping app (PID $($app.Id))..."
    Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue
}
