# Bower Ag CowCare Tool - Railway Readiness Verification (PowerShell)
# Sprint 18D: Run locally on Windows before deploying to Railway.
#
# Usage (from project root):
#   .\scripts\verify_railway_readiness.ps1

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

Write-Host ""
Write-Host "============================================================"
Write-Host "  Bower Ag CowCare - Railway Deployment Readiness Check"
Write-Host "============================================================"
Write-Host ""

# Determine backend directory relative to where the script is run from
# Try from $PSScriptRoot first, fall back to current directory
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Get-Location
}

# Navigate up from scripts/ to project root, then into backend/
$ProjectRoot = Split-Path $ScriptDir -Parent
$BackendDir = Join-Path $ProjectRoot "backend"

# If that doesn't work, try from current working directory
if (-not (Test-Path $BackendDir)) {
    $BackendDir = Join-Path (Get-Location) "backend"
}

if (-not (Test-Path $BackendDir)) {
    Write-Host "ERROR: Cannot find backend directory." -ForegroundColor Red
    Write-Host "Run this script from the project root: .\scripts\verify_railway_readiness.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "  Backend dir: $BackendDir"
Write-Host ""

# --- Check 1: Required deployment files ---
Write-Host "--- 1. Required Deployment Files ---"

$requiredFiles = @(
    "nixpacks.toml",
    "railway.toml",
    "Procfile",
    "requirements.txt",
    "app\main.py",
    "app\core\prompts.py"
)

foreach ($f in $requiredFiles) {
    $fullPath = Join-Path $BackendDir $f
    if (Test-Path $fullPath) {
        Test-Pass "$f exists"
    } else {
        Test-Fail "$f MISSING"
    }
}

# --- Check 2: nixpacks.toml contains ffmpeg ---
Write-Host ""
Write-Host "--- 2. nixpacks.toml - ffmpeg ---"

$nixpacksPath = Join-Path $BackendDir "nixpacks.toml"
if (Test-Path $nixpacksPath) {
    $content = Get-Content $nixpacksPath -Raw
    if ($content -match "ffmpeg") {
        Test-Pass "nixpacks.toml includes ffmpeg"
    } else {
        Test-Fail "nixpacks.toml missing ffmpeg"
    }
} else {
    Test-Fail "nixpacks.toml not found"
}

# --- Check 3: railway.toml health check ---
Write-Host ""
Write-Host "--- 3. railway.toml - Health Check ---"

$railwayPath = Join-Path $BackendDir "railway.toml"
if (Test-Path $railwayPath) {
    $content = Get-Content $railwayPath -Raw
    if ($content -match 'healthcheckPath = "/health"') {
        Test-Pass "Health check path = /health"
    } else {
        Test-Fail "Health check path not configured"
    }

    if ($content -match 'healthcheckTimeout = (\d+)') {
        $timeout = [int]$Matches[1]
        $msg = "Health check timeout = " + $timeout + "s"
        if ($timeout -ge 300) {
            Test-Pass $msg
        } else {
            Test-Fail "$msg (must be 300 or more)"
        }
    } else {
        Test-Fail "healthcheckTimeout not found"
    }
} else {
    Test-Fail "railway.toml not found"
}

# --- Check 4: CORS configuration ---
Write-Host ""
Write-Host "--- 4. CORS Configuration ---"

$mainPyPath = Join-Path $BackendDir "app\main.py"
if (Test-Path $mainPyPath) {
    $content = Get-Content $mainPyPath -Raw
    if ($content -match "X-Location-Code") {
        Test-Pass "CORS includes X-Location-Code"
    } else {
        Test-Fail "CORS missing X-Location-Code"
    }

    if ($content -match "X-Language") {
        Test-Pass "CORS includes X-Language"
    } else {
        Test-Fail "CORS missing X-Language"
    }

    if ($content -match 'allow_headers=\["\*"\]') {
        Test-Fail "CORS still using wildcard"
    } else {
        Test-Pass "CORS headers are not wildcard"
    }
} else {
    Test-Fail "app/main.py not found"
}

# --- Check 5: Health endpoint returns ok ---
Write-Host ""
Write-Host "--- 5. Health Endpoint (code check) ---"

if (Test-Path $mainPyPath) {
    $content = Get-Content $mainPyPath -Raw
    if ($content -match '"status":\s*"ok"') {
        Test-Pass "Health endpoint returns status ok"
    } else {
        Test-Fail "Health endpoint does not return status ok"
    }
} else {
    Test-Fail "app/main.py not found"
}

# --- Check 6: Governance prompts ---
Write-Host ""
Write-Host "--- 6. Governance Prompts ---"

$promptsPath = Join-Path $BackendDir "app\core\prompts.py"
if (Test-Path $promptsPath) {
    $content = Get-Content $promptsPath -Raw
    $checks = @(
        "GOVERNANCE RULES",
        "NEVER recall pricing from memory",
        "BASE_SYSTEM_PROMPT",
        "WASH_AUDIT_REPORT_ADDENDUM",
        "Vendor display",
        "Location restrictions"
    )
    foreach ($check in $checks) {
        if ($content.Contains($check)) {
            Test-Pass "prompts.py contains: $check"
        } else {
            Test-Fail "prompts.py MISSING: $check"
        }
    }
} else {
    Test-Fail "app/core/prompts.py not found"
}

# --- Check 7: Environment variables ---
Write-Host ""
Write-Host "--- 7. Environment Variables ---"

$envPath = Join-Path $BackendDir ".env.example"
if (Test-Path $envPath) {
    $content = Get-Content $envPath -Raw
    $requiredVars = @(
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "ANTHROPIC_API_KEY",
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET_NAME",
        "APP_VERSION",
        "ENVIRONMENT",
        "ALLOWED_ORIGINS",
        "SENTRY_DSN"
    )
    foreach ($var in $requiredVars) {
        if ($content -match "(?m)^${var}=") {
            Test-Pass "$var documented"
        } else {
            Test-Fail "$var MISSING from .env.example"
        }
    }
} else {
    Test-Fail ".env.example not found"
}

# --- Summary ---
Write-Host ""
Write-Host "============================================================"
if ($Fail -gt 0) {
    Write-Host "  Results: $Pass passed, $Fail failed" -ForegroundColor Red
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "  DEPLOYMENT NOT READY - Fix failures above." -ForegroundColor Red
    exit 1
} else {
    Write-Host "  Results: $Pass passed, $Fail failed" -ForegroundColor Green
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "  ALL CHECKS PASSED - Ready for Railway deployment!" -ForegroundColor Green
    exit 0
}
