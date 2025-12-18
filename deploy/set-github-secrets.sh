#!/bin/bash
# Bash script to set GitHub Secrets for Fixed Asset API deployment
# Run from VS Code terminal (Git Bash or WSL)
#
# Prerequisites:
#   - GitHub CLI installed: https://cli.github.com/
#   - Logged in: gh auth login
#
# Usage:
#   ./set-github-secrets.sh
#   ./set-github-secrets.sh --account-id 123456789012

set -e

# Configuration (edit these or pass as arguments)
AWS_REGION="${AWS_REGION:-ap-south-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-777149301332}"
ECR_REPOSITORY="${ECR_REPOSITORY:-fixed-asset-api}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --region) AWS_REGION="$2"; shift 2 ;;
        --account-id) AWS_ACCOUNT_ID="$2"; shift 2 ;;
        --ecr-repo) ECR_REPOSITORY="$2"; shift 2 ;;
        --postgres-password) POSTGRES_PASSWORD="$2"; shift 2 ;;
        --secret-key) SECRET_KEY="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI not found. Install from: https://cli.github.com/"
    exit 1
fi

# Check if logged in
if ! gh auth status &> /dev/null; then
    echo "Not logged in to GitHub CLI. Run: gh auth login"
    exit 1
fi

echo "============================================"
echo " Setting GitHub Secrets for Fixed Asset API"
echo "============================================"
echo ""

# Generate passwords if not provided
if [ -z "$POSTGRES_PASSWORD" ]; then
    POSTGRES_PASSWORD=$(openssl rand -hex 16)
    echo "Generated POSTGRES_PASSWORD"
fi

if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY=$(openssl rand -hex 32)
    echo "Generated SECRET_KEY"
fi

# Derived values
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
AWS_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/github-actions-fixed-asset-api"

echo ""
echo "Setting secrets..."
echo ""

# Function to set secret
set_secret() {
    local name=$1
    local value=$2
    printf "  Setting %s..." "$name"
    if echo "$value" | gh secret set "$name" 2>/dev/null; then
        echo " OK"
    else
        echo " FAILED"
    fi
}

# Set all secrets
set_secret "AWS_REGION" "$AWS_REGION"
set_secret "AWS_ROLE_ARN" "$AWS_ROLE_ARN"
set_secret "ECR_REGISTRY" "$ECR_REGISTRY"
set_secret "ECR_REPOSITORY" "$ECR_REPOSITORY"
set_secret "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD"
set_secret "SECRET_KEY" "$SECRET_KEY"

echo ""
echo "============================================"
echo " GitHub Secrets Configured!"
echo "============================================"
echo ""
echo "Secrets set:"
echo "  AWS_REGION:        $AWS_REGION"
echo "  AWS_ROLE_ARN:      $AWS_ROLE_ARN"
echo "  ECR_REGISTRY:      $ECR_REGISTRY"
echo "  ECR_REPOSITORY:    $ECR_REPOSITORY"
echo "  POSTGRES_PASSWORD: ********"
echo "  SECRET_KEY:        ********"
echo ""
echo "Next steps:"
echo "  1. Run deploy/aws/setup-aws.sh to create AWS resources (if not done)"
echo "  2. Push to v2 or main branch to trigger deployment"
echo ""

# Save generated passwords to a local file (gitignored)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat > "$SCRIPT_DIR/.secrets.local" << EOF
# Generated secrets - DO NOT COMMIT
# Generated: $(date)

POSTGRES_PASSWORD=$POSTGRES_PASSWORD
SECRET_KEY=$SECRET_KEY
EOF

echo "Generated passwords saved to: deploy/.secrets.local"
echo "(This file is gitignored - keep it safe!)"
