# ─────────────────────────────────────────────────────────
# Bower Ag CowCare Tool - Vercel Frontend Smoke Test
# Sprint 19D: Run after Vercel deployment to verify frontend
# Usage: .\scripts\verify_vercel_deploy.ps1 -VercelUrl "https://your-project.vercel.app"
# ─────────────────────────────────────────────────────────
param(
    [Parameter(Mandatory=$true)]
    [string]$VercelUrl
)

# Remove trailing slash
$VercelUrl = $VercelUrl.TrimEnd('/')

$pass = 0
$fail = 0
$total = 0

function Test-Check {
    param([string]$Name, [scriptblock]$Block)
    $script:total++
    try {
        $result = & $Block
        if ($result) {
            Write-Host "[PASS] $Name" -ForegroundColor Green
            $script:pass++
        } else {
            Write-Host "[FAIL] $Name" -ForegroundColor Red
            $script:fail++
        }
    } catch {
        Write-Host "[FAIL] $Name - Error: $_" -ForegroundColor Red
        $script:fail++
    }
}

Write-Host ""
Write-Host "=== Bower Ag CowCare Tool - Vercel Smoke Test ===" -ForegroundColor Cyan
Write-Host "Target: $VercelUrl"
Write-Host ""

# --- Page Load Tests ---
Write-Host "--- Page Load ---" -ForegroundColor Yellow

Test-Check "Homepage returns 200" {
    $r = Invoke-WebRequest -Uri $VercelUrl -UseBasicParsing -ErrorAction Stop
    $r.StatusCode -eq 200
}

Test-Check "Homepage contains root div" {
    $r = Invoke-WebRequest -Uri $VercelUrl -UseBasicParsing -ErrorAction Stop
    $r.Content -match 'id="root"'
}

Test-Check "Homepage contains app title" {
    $r = Invoke-WebRequest -Uri $VercelUrl -UseBasicParsing -ErrorAction Stop
    $r.Content -match "CowCare Tool"
}

# --- SPA Routing ---
Write-Host ""
Write-Host "--- SPA Routing (rewrites) ---" -ForegroundColor Yellow

Test-Check "Deep link /login returns 200 (SPA rewrite)" {
    $r = Invoke-WebRequest -Uri "$VercelUrl/login" -UseBasicParsing -ErrorAction Stop
    $r.StatusCode -eq 200
}

Test-Check "Deep link /dashboard returns 200 (SPA rewrite)" {
    $r = Invoke-WebRequest -Uri "$VercelUrl/dashboard" -UseBasicParsing -ErrorAction Stop
    $r.StatusCode -eq 200
}

Test-Check "Deep link /products returns 200 (SPA rewrite)" {
    $r = Invoke-WebRequest -Uri "$VercelUrl/products" -UseBasicParsing -ErrorAction Stop
    $r.StatusCode -eq 200
}

# --- Security Headers ---
Write-Host ""
Write-Host "--- Security Headers ---" -ForegroundColor Yellow

Test-Check "X-Content-Type-Options: nosniff" {
    $r = Invoke-WebRequest -Uri $VercelUrl -UseBasicParsing -ErrorAction Stop
    $r.Headers["X-Content-Type-Options"] -eq "nosniff"
}

Test-Check "X-Frame-Options: DENY" {
    $r = Invoke-WebRequest -Uri $VercelUrl -UseBasicParsing -ErrorAction Stop
    $r.Headers["X-Frame-Options"] -eq "DENY"
}

Test-Check "Referrer-Policy present" {
    $r = Invoke-WebRequest -Uri $VercelUrl -UseBasicParsing -ErrorAction Stop
    $r.Headers["Referrer-Policy"] -eq "strict-origin-when-cross-origin"
}

# --- Static Assets ---
Write-Host ""
Write-Host "--- Static Assets ---" -ForegroundColor Yellow

Test-Check "Favicon accessible" {
    $r = Invoke-WebRequest -Uri "$VercelUrl/favicon.svg" -UseBasicParsing -ErrorAction Stop
    $r.StatusCode -eq 200
}

Test-Check "PWA icon 192x192 accessible" {
    $r = Invoke-WebRequest -Uri "$VercelUrl/pwa-192x192.png" -UseBasicParsing -ErrorAction Stop
    $r.StatusCode -eq 200
}

Test-Check "Apple touch icon accessible" {
    $r = Invoke-WebRequest -Uri "$VercelUrl/apple-touch-icon.png" -UseBasicParsing -ErrorAction Stop
    $r.StatusCode -eq 200
}

# --- PWA ---
Write-Host ""
Write-Host "--- PWA ---" -ForegroundColor Yellow

Test-Check "Service worker (sw.js) accessible" {
    $r = Invoke-WebRequest -Uri "$VercelUrl/sw.js" -UseBasicParsing -ErrorAction Stop
    $r.StatusCode -eq 200
}

Test-Check "Service worker has no-cache header" {
    $r = Invoke-WebRequest -Uri "$VercelUrl/sw.js" -UseBasicParsing -ErrorAction Stop
    $r.Headers["Cache-Control"] -match "no-cache"
}

# --- Backend Connectivity ---
Write-Host ""
Write-Host "--- Backend Connectivity ---" -ForegroundColor Yellow

$backendUrl = "https://bawashup-gpt-production.up.railway.app"

Test-Check "Railway backend /health reachable" {
    $r = Invoke-WebRequest -Uri "$backendUrl/health" -UseBasicParsing -ErrorAction Stop
    $r.StatusCode -eq 200
}

Test-Check "Railway backend returns status ok" {
    $r = Invoke-WebRequest -Uri "$backendUrl/health" -UseBasicParsing -ErrorAction Stop
    $body = $r.Content | ConvertFrom-Json
    $body.status -eq "ok"
}

# --- Summary ---
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Results: $pass/$total passed, $fail failed" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Red" })
Write-Host "============================================" -ForegroundColor Cyan

if ($fail -gt 0) {
    Write-Host ""
    Write-Host "Some checks failed. See above for details." -ForegroundColor Red
    exit 1
} else {
    Write-Host ""
    Write-Host "All checks passed! Frontend is deployed correctly." -ForegroundColor Green
    exit 0
}
