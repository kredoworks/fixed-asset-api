# PowerShell script to set GitHub Secrets for Fixed Asset API deployment
# Run this from VS Code terminal (PowerShell)
#
# Prerequisites:
#   - GitHub CLI installed: winget install GitHub.cli
#   - Logged in: gh auth login

param(
    [string]$AwsRegion = "ap-south-1",
    [string]$AwsAccountId = "777149301332",
    [string]$EcrRepository = "fixed-asset-api",
    [string]$PostgresPassword = "1234567",
    [string]$SecretKey
)

# Check if gh is installed
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "GitHub CLI not found. Install with: winget install GitHub.cli" -ForegroundColor Red
    exit 1
}

# Check if logged in
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Not logged in to GitHub CLI. Run: gh auth login" -ForegroundColor Red
    exit 1
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Setting GitHub Secrets for Fixed Asset API" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Generate passwords if not provided
if (-not $PostgresPassword) {
    $PostgresPassword = -join ((48..57) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    Write-Host "Generated POSTGRES_PASSWORD" -ForegroundColor Yellow
}

if (-not $SecretKey) {
    $SecretKey = -join ((48..57) + (97..122) | Get-Random -Count 64 | ForEach-Object { [char]$_ })
    Write-Host "Generated SECRET_KEY" -ForegroundColor Yellow
}

# Derived values
$EcrRegistry = "$AwsAccountId.dkr.ecr.$AwsRegion.amazonaws.com"
$AwsRoleArn = "arn:aws:iam::${AwsAccountId}:role/github-actions-fixed-asset-api"

# Secrets to set
$secrets = @{
    "AWS_REGION"        = $AwsRegion
    "AWS_ROLE_ARN"      = $AwsRoleArn
    "ECR_REGISTRY"      = $EcrRegistry
    "ECR_REPOSITORY"    = $EcrRepository
    "POSTGRES_PASSWORD" = $PostgresPassword
    "SECRET_KEY"        = $SecretKey
}

Write-Host "Setting secrets..." -ForegroundColor Cyan
Write-Host ""

foreach ($secret in $secrets.GetEnumerator()) {
    Write-Host "  Setting $($secret.Key)..." -NoNewline

    # Set the secret using gh cli
    $secret.Value | gh secret set $secret.Key 2>&1 | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK" -ForegroundColor Green
    }
    else {
        Write-Host " FAILED" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " GitHub Secrets Configured!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Secrets set:" -ForegroundColor Cyan
Write-Host "  AWS_REGION:        $AwsRegion"
Write-Host "  AWS_ROLE_ARN:      $AwsRoleArn"
Write-Host "  ECR_REGISTRY:      $EcrRegistry"
Write-Host "  ECR_REPOSITORY:    $EcrRepository"
Write-Host "  POSTGRES_PASSWORD: ********"
Write-Host "  SECRET_KEY:        ********"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run deploy/aws/setup-aws.sh to create AWS resources (if not done)"
Write-Host "  2. Push to v2 or main branch to trigger deployment"
Write-Host ""

# Save generated passwords to a local file (gitignored)
$envLocalPath = Join-Path $PSScriptRoot ".secrets.local"
@"
# Generated secrets - DO NOT COMMIT
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

POSTGRES_PASSWORD=$PostgresPassword
SECRET_KEY=$SecretKey
"@ | Out-File -FilePath $envLocalPath -Encoding UTF8

Write-Host "Generated passwords saved to: deploy/.secrets.local" -ForegroundColor Gray
Write-Host "(This file is gitignored - keep it safe!)" -ForegroundColor Gray
