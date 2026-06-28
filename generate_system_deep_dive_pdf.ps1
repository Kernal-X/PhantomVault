$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$htmlPath = Join-Path $repoRoot "system_deep_dive.html"
$pdfPath = Join-Path $repoRoot "system_deep_dive.pdf"

if (-not (Test-Path $htmlPath)) {
    throw "HTML source not found at $htmlPath"
}

$chromeCandidates = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)

$browser = $chromeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $browser) {
    throw "Chrome/Edge not found. Install Chrome or Edge, then rerun this script."
}

$fileUri = "file:///" + ($htmlPath -replace "\\", "/").Replace(" ", "%20")

Write-Host "Using browser:" $browser
Write-Host "HTML source:" $htmlPath
Write-Host "PDF target:" $pdfPath

& $browser `
    --headless=new `
    --disable-gpu `
    --no-sandbox `
    --allow-file-access-from-files `
    --enable-local-file-accesses `
    --virtual-time-budget=15000 `
    "--print-to-pdf=$pdfPath" `
    $fileUri

if (-not (Test-Path $pdfPath)) {
    throw "PDF generation command completed, but the PDF was not found at $pdfPath"
}

Write-Host ""
Write-Host "PDF created successfully:"
Write-Host $pdfPath
