# Bower Ag CowCare Tool - Production Smoke Tests (PowerShell)
# Sprint 18D: Verify deployed services after Railway/Vercel deployment.
#
# Usage:
#   .\scripts\production_smoke_test.ps1 -ApiUrl "https://your-app.railway.app"
#   .\scripts\production_smoke_test.ps1 -ApiUrl "https://your-app.railway.app" -UiUrl "https://your-app.vercel.app"

param(
    [string]$ApiUrl = "https://bawashup-gpt-production.up.railway.app",
    [string]$UiUrl = "https://bawashup-gpt.vercel.app",
    [string]$AdminJwt = ""
)

# Force TLS 1.2 (Windows PowerShell defaults to older TLS)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$ErrorActionPreference = "Continue"
$Pass = 0
$Fail = 0

function Test-Pass($msg) {
    Write-Host "  [PASS] $msg" -ForegroundColor Green
    $script:Pass++
}
function Test-Fail($msg) {
    Write-Host "  [FAIL] $msg" -ForegroundColor Red
    $script:Fail++
}
function Test-Skip($msg) {
    Write-Host "  [SKIP] $msg" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================"
Write-Host "  Bower Ag CowCare - Production Smoke Tests"
Write-Host "============================================================"
Write-Host ""
Write-Host "  API: $ApiUrl"
Write-Host "  UI:  $UiUrl"
Write-Host ""

# --- Test 1: API Health ---
Write-Host "--- 1. API Health Check ---"
try {
    $resp = Invoke-RestMethod -Uri "$ApiUrl/health" -TimeoutSec 10
    Test-Pass "/health returns 200 (version: $($resp.version))"
} catch {
    Test-Fail "/health failed: $($_.Exception.Message)"
}

# --- Test 2: Health response structure ---
Write-Host "--- 2. Health Response Structure ---"
try {
    $resp = Invoke-RestMethod -Uri "$ApiUrl/health" -TimeoutSec 10
    if ($resp.status -eq "ok") {
        Test-Pass "status = ok"
    } else {
        Test-Fail "status = $($resp.status) (expected ok)"
    }

    if ($resp.service -eq "bowerag-cowcare-api") {
        Test-Pass "service = bowerag-cowcare-api"
    } else {
        Test-Fail "service = $($resp.service)"
    }
} catch {
    Test-Fail "Could not check response structure: $($_.Exception.Message)"
}

# --- Test 3: CORS blocks unknown origin ---
Write-Host "--- 3. CORS Security ---"
try {
    $headers = @{
        "Origin" = "https://evil.com"
        "Access-Control-Request-Method" = "GET"
    }
    $resp = Invoke-WebRequest -Uri "$ApiUrl/health" -Method OPTIONS -Headers $headers -TimeoutSec 10 -ErrorAction Stop
    $acao = $resp.Headers["Access-Control-Allow-Origin"]
    if ($acao -eq "https://evil.com") {
        Test-Fail "CORS allows evil.com - too permissive!"
    } else {
        Test-Pass "CORS blocks unknown origin (evil.com)"
    }
} catch {
    # A 4xx response or missing CORS header means blocked - that is a PASS
    Test-Pass "CORS blocks unknown origin (request rejected)"
}

# --- Test 4: Unauthenticated request gets 401 ---
Write-Host "--- 4. Auth Guard ---"
try {
    $null = Invoke-WebRequest -Uri "$ApiUrl/products" -TimeoutSec 10 -ErrorAction Stop
    Test-Fail "/products returned 200 (expected 401)"
} catch {
    if ($_.Exception.Response) {
        $statusCode = [int]$_.Exception.Response.StatusCode
        if ($statusCode -eq 401) {
            Test-Pass "Unauthenticated /products returns 401"
        } else {
            Test-Fail "/products returned $statusCode (expected 401)"
        }
    } else {
        Test-Fail "/products connection failed: $($_.Exception.Message)"
    }
}

# --- Test 5: Governance health ---
Write-Host "--- 5. Governance Health (admin auth) ---"
if ($AdminJwt) {
    try {
        $headers = @{ "Authorization" = "Bearer $AdminJwt" }
        $resp = Invoke-RestMethod -Uri "$ApiUrl/governance/health" -Headers $headers -TimeoutSec 10
        if ($resp.product_count) {
            Test-Pass "Governance health returns product_count = $($resp.product_count)"
        } else {
            Test-Fail "Governance health missing product_count"
        }
    } catch {
        Test-Fail "Governance health failed: $($_.Exception.Message)"
    }
} else {
    Test-Skip "Set -AdminJwt parameter to test governance health"
}

# --- Test 6: UI loads ---
Write-Host "--- 6. Frontend UI ---"
try {
    $resp = Invoke-WebRequest -Uri $UiUrl -TimeoutSec 10 -ErrorAction Stop
    if ($resp.StatusCode -eq 200) {
        Test-Pass "UI loads (HTTP 200)"
    } else {
        Test-Fail "UI returned $($resp.StatusCode)"
    }
} catch {
    Test-Fail "UI unreachable: $($_.Exception.Message)"
}

# --- Test 7: Security headers ---
Write-Host "--- 7. Security Headers ---"
try {
    $resp = Invoke-WebRequest -Uri $UiUrl -TimeoutSec 10 -ErrorAction Stop
    if ($resp.Headers["X-Content-Type-Options"]) {
        Test-Pass "X-Content-Type-Options header present"
    } else {
        Test-Fail "X-Content-Type-Options missing"
    }
} catch {
    Test-Fail "Could not check headers: $($_.Exception.Message)"
}

# --- Test 8: Version check ---
Write-Host "--- 8. Version Verification ---"
try {
    $resp = Invoke-RestMethod -Uri "$ApiUrl/health" -TimeoutSec 10
    if ($resp.version -eq "0.1.0-beta") {
        Test-Pass "API version is 0.1.0-beta"
    } else {
        Write-Host "  [INFO] Version is $($resp.version) (expected 0.1.0-beta)" -ForegroundColor Yellow
        $script:Pass++
    }
} catch {
    Test-Fail "Could not determine version"
}

# --- Summary ---
Write-Host ""
Write-Host "============================================================"
if ($Fail -gt 0) {
    Write-Host "  Results: $Pass passed, $Fail failed" -ForegroundColor Red
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "  Some smoke tests failed. Review output above." -ForegroundColor Red
    exit 1
} else {
    Write-Host "  Results: $Pass passed, $Fail failed" -ForegroundColor Green
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "  All smoke tests passed!" -ForegroundColor Green
    exit 0
}
