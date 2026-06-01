# Push PredictX to https://github.com/kinkkayz/predictx
# Run this in PowerShell (double-click or: .\push-github.ps1)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

git remote remove origin 2>$null
git remote add origin https://github.com/kinkkayz/predictx.git

$auth = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Log in to GitHub (browser will open)..." -ForegroundColor Cyan
    gh auth login -h github.com -p https -w
}

Write-Host ""
Write-Host "Pushing to github.com/kinkkayz/predictx ..." -ForegroundColor Cyan
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Done! Repo: https://github.com/kinkkayz/predictx" -ForegroundColor Green
    Write-Host "Next: Render -> New Web Service -> connect kinkkayz/predictx"
} else {
    Write-Host "Push failed. If the repo has a README on GitHub, run:" -ForegroundColor Yellow
    Write-Host "  git pull origin main --rebase"
    Write-Host "  git push -u origin main"
}
