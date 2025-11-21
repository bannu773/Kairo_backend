# Pre-Deployment Checklist Script
# Run this before deploying to catch common issues

Write-Host "=== GCP Deployment Pre-Flight Checklist ===" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# Check 1: Google Cloud SDK
Write-Host "[1/8] Checking for Google Cloud SDK..." -ForegroundColor Yellow
try {
    $null = gcloud version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ Google Cloud SDK installed" -ForegroundColor Green
    } else {
        Write-Host "    ✗ Google Cloud SDK not found" -ForegroundColor Red
        Write-Host "      Install from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Cyan
        $allGood = $false
    }
} catch {
    Write-Host "    ✗ Google Cloud SDK not found" -ForegroundColor Red
    Write-Host "      Install from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Cyan
    $allGood = $false
}

# Check 2: app.yaml exists
Write-Host "[2/8] Checking for app.yaml..." -ForegroundColor Yellow
if (Test-Path "app.yaml") {
    Write-Host "    ✓ app.yaml found" -ForegroundColor Green
} else {
    Write-Host "    ✗ app.yaml not found" -ForegroundColor Red
    Write-Host "      Make sure you're in the backend directory" -ForegroundColor Cyan
    $allGood = $false
}

# Check 3: requirements.txt exists
Write-Host "[3/8] Checking for requirements.txt..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    Write-Host "    ✓ requirements.txt found" -ForegroundColor Green
} else {
    Write-Host "    ✗ requirements.txt not found" -ForegroundColor Red
    $allGood = $false
}

# Check 4: run.py exists
Write-Host "[4/8] Checking for run.py..." -ForegroundColor Yellow
if (Test-Path "run.py") {
    Write-Host "    ✓ run.py found" -ForegroundColor Green
} else {
    Write-Host "    ✗ run.py not found" -ForegroundColor Red
    $allGood = $false
}

# Check 5: Secret keys in app.yaml
Write-Host "[5/8] Checking SECRET_KEY in app.yaml..." -ForegroundColor Yellow
$appYamlContent = Get-Content "app.yaml" -Raw
if ($appYamlContent -match "SECRET_KEY:\s*'your-production-secret-key-change-this'") {
    Write-Host "    ⚠ SECRET_KEY still using default value!" -ForegroundColor Yellow
    Write-Host "      Generate a secure key with:" -ForegroundColor Cyan
    Write-Host "      python -c `"import secrets; print(secrets.token_hex(32))`"" -ForegroundColor White
    $allGood = $false
} else {
    Write-Host "    ✓ SECRET_KEY appears to be customized" -ForegroundColor Green
}

# Check 6: JWT Secret key in app.yaml
Write-Host "[6/8] Checking JWT_SECRET_KEY in app.yaml..." -ForegroundColor Yellow
if ($appYamlContent -match "JWT_SECRET_KEY:\s*'your-production-jwt-secret-key-change-this'") {
    Write-Host "    ⚠ JWT_SECRET_KEY still using default value!" -ForegroundColor Yellow
    Write-Host "      Generate a secure key with:" -ForegroundColor Cyan
    Write-Host "      python -c `"import secrets; print(secrets.token_hex(32))`"" -ForegroundColor White
    $allGood = $false
} else {
    Write-Host "    ✓ JWT_SECRET_KEY appears to be customized" -ForegroundColor Green
}

# Check 7: Python availability
Write-Host "[7/8] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ Python found: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "    ⚠ Python not found (needed for generating secrets)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "    ⚠ Python not found (needed for generating secrets)" -ForegroundColor Yellow
}

# Check 8: Project authentication
Write-Host "[8/8] Checking GCP authentication..." -ForegroundColor Yellow
try {
    $currentProject = gcloud config get-value project 2>$null
    if ($currentProject -eq "fleet-ivy-478805-a7") {
        Write-Host "    ✓ Authenticated with project: fleet-ivy-478805-a7" -ForegroundColor Green
    } else {
        Write-Host "    ⚠ Current project: $currentProject" -ForegroundColor Yellow
        Write-Host "      Run: gcloud config set project fleet-ivy-478805-a7" -ForegroundColor Cyan
    }
} catch {
    Write-Host "    ⚠ Not authenticated with GCP" -ForegroundColor Yellow
    Write-Host "      Run: gcloud auth login" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan

if ($allGood) {
    Write-Host "✓ All checks passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ready to deploy! Run:" -ForegroundColor Cyan
    Write-Host "  .\deploy-gcp.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "Or manually:" -ForegroundColor Cyan
    Write-Host "  gcloud app deploy" -ForegroundColor White
} else {
    Write-Host "⚠ Some issues found!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please fix the issues above before deploying." -ForegroundColor Cyan
    Write-Host "See GCP_DEPLOYMENT.md for detailed instructions." -ForegroundColor Cyan
}

Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Additional reminders
Write-Host "Don't forget:" -ForegroundColor Yellow
Write-Host "  1. Update Google OAuth redirect URIs in Google Cloud Console" -ForegroundColor Cyan
Write-Host "     https://console.cloud.google.com/apis/credentials" -ForegroundColor White
Write-Host "  2. Add this redirect URI:" -ForegroundColor Cyan
Write-Host "     https://fleet-ivy-478805-a7.uc.r.appspot.com/api/auth/callback" -ForegroundColor White
Write-Host ""
