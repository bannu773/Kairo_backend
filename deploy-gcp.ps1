# GCP Deployment Script for PowerShell
# Run this from the backend directory

Write-Host "=== Kairo Backend - GCP Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Check if gcloud is installed
Write-Host "Checking for gcloud CLI..." -ForegroundColor Yellow
try {
    $gcloudVersion = gcloud version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ gcloud CLI is installed" -ForegroundColor Green
    } else {
        throw "gcloud not found"
    }
} catch {
    Write-Host "✗ gcloud CLI not found" -ForegroundColor Red
    Write-Host "Please install from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Set project
Write-Host "Setting GCP project to fleet-ivy-478805-a7..." -ForegroundColor Yellow
gcloud config set project fleet-ivy-478805-a7

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to set project" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Project set successfully" -ForegroundColor Green
Write-Host ""

# Check if App Engine app exists
Write-Host "Checking if App Engine application exists..." -ForegroundColor Yellow
$appExists = gcloud app describe --project=fleet-ivy-478805-a7 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "App Engine application doesn't exist. Creating..." -ForegroundColor Yellow
    Write-Host "Note: This will create an App Engine app in us-central region" -ForegroundColor Cyan
    
    $confirm = Read-Host "Continue? (Y/n)"
    if ($confirm -ne "Y" -and $confirm -ne "y" -and $confirm -ne "") {
        Write-Host "Deployment cancelled" -ForegroundColor Yellow
        exit 0
    }
    
    gcloud app create --region=us-central --project=fleet-ivy-478805-a7
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to create App Engine application" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ App Engine application created" -ForegroundColor Green
} else {
    Write-Host "✓ App Engine application already exists" -ForegroundColor Green
}

Write-Host ""

# Enable required APIs
Write-Host "Enabling required APIs..." -ForegroundColor Yellow

$apis = @(
    "appengine.googleapis.com",
    "cloudbuild.googleapis.com",
    "speech.googleapis.com"
)

foreach ($api in $apis) {
    Write-Host "  Enabling $api..." -ForegroundColor Cyan
    gcloud services enable $api --project=fleet-ivy-478805-a7 2>$null
}

Write-Host "✓ APIs enabled" -ForegroundColor Green
Write-Host ""

# Check if app.yaml exists
if (-Not (Test-Path "app.yaml")) {
    Write-Host "✗ app.yaml not found in current directory" -ForegroundColor Red
    Write-Host "Please run this script from the backend directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ app.yaml found" -ForegroundColor Green
Write-Host ""

# Warn about secrets
Write-Host "IMPORTANT: Before deploying, make sure you have:" -ForegroundColor Yellow
Write-Host "  1. Generated secure SECRET_KEY and JWT_SECRET_KEY in app.yaml" -ForegroundColor Cyan
Write-Host "  2. Updated Google OAuth redirect URIs in Google Cloud Console" -ForegroundColor Cyan
Write-Host "  3. Verified MongoDB connection string" -ForegroundColor Cyan
Write-Host ""

$continueDeployment = Read-Host "Ready to deploy? (Y/n)"
if ($continueDeployment -ne "Y" -and $continueDeployment -ne "y" -and $continueDeployment -ne "") {
    Write-Host "Deployment cancelled" -ForegroundColor Yellow
    Write-Host "See GCP_DEPLOYMENT.md for more information" -ForegroundColor Cyan
    exit 0
}

Write-Host ""
Write-Host "Starting deployment..." -ForegroundColor Yellow
Write-Host ""

# Deploy
gcloud app deploy app.yaml --project=fleet-ivy-478805-a7 --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==================================" -ForegroundColor Green
    Write-Host "✓ Deployment successful!" -ForegroundColor Green
    Write-Host "==================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your app is deployed at:" -ForegroundColor Cyan
    Write-Host "https://fleet-ivy-478805-a7.uc.r.appspot.com" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Test health endpoint: https://fleet-ivy-478805-a7.uc.r.appspot.com/api/health" -ForegroundColor Cyan
    Write-Host "  2. Update frontend to use new backend URL" -ForegroundColor Cyan
    Write-Host "  3. Test authentication flow" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "View logs:" -ForegroundColor Yellow
    Write-Host "  gcloud app logs tail --project=fleet-ivy-478805-a7" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "✗ Deployment failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check the error messages above" -ForegroundColor Cyan
    Write-Host "  2. View logs: gcloud app logs tail --project=fleet-ivy-478805-a7" -ForegroundColor Cyan
    Write-Host "  3. See GCP_DEPLOYMENT.md for common issues" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}
