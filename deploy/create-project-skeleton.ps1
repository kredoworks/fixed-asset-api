# PowerShell script to create a reusable FastAPI + AWS deployment skeleton
# Usage: .\create-project-skeleton.ps1 -ProjectName "my-api" -AwsRegion "ap-south-1" -Port 8000
#
# This creates:
#   - Dockerfile
#   - docker-compose.yml / docker-compose.prod.yml
#   - GitHub Actions workflow
#   - AWS setup script
#   - GitHub secrets script

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectName,

    [string]$AwsRegion = "ap-south-1",
    [string]$AwsAccountId = "",
    [string]$GitHubRepo = "",  # format: owner/repo
    [int]$Port = 8000,
    [string]$OutputDir = "."
)

# Get AWS Account ID if not provided
if (-not $AwsAccountId) {
    try {
        $AwsAccountId = aws sts get-caller-identity --query Account --output text 2>$null
        if (-not $AwsAccountId) {
            Write-Host "Could not get AWS Account ID. Please provide -AwsAccountId parameter" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "AWS CLI not configured. Please provide -AwsAccountId parameter" -ForegroundColor Red
        exit 1
    }
}

# Get GitHub repo if not provided
if (-not $GitHubRepo) {
    try {
        $GitHubRepo = git remote get-url origin 2>$null | Select-String -Pattern "github.com[:/](.+?)(?:\.git)?$" | ForEach-Object { $_.Matches[0].Groups[1].Value }
    } catch {
        Write-Host "Could not detect GitHub repo. Please provide -GitHubRepo parameter" -ForegroundColor Yellow
    }
}

$ProjectSlug = $ProjectName.ToLower() -replace '[^a-z0-9]', '-'

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Creating Deployment Skeleton" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Project:     $ProjectName"
Write-Host "  Slug:        $ProjectSlug"
Write-Host "  AWS Region:  $AwsRegion"
Write-Host "  Account ID:  $AwsAccountId"
Write-Host "  GitHub Repo: $GitHubRepo"
Write-Host "  Port:        $Port"
Write-Host ""

# Create directories
$dirs = @(
    "$OutputDir/.github/workflows",
    "$OutputDir/deploy/aws"
)
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

# ============================================
# 1. Dockerfile
# ============================================
$dockerfile = @"
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PATH="`$POETRY_HOME/bin:`$PATH"

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN poetry install --without dev --no-interaction --no-ansi

COPY . .
RUN mkdir -p uploads

EXPOSE $Port

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$Port"]
"@

# ============================================
# 2. docker-compose.yml (local dev)
# ============================================
$dockerCompose = @"
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ${ProjectSlug}_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    ports:
      - "$Port`:$Port"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/${ProjectSlug}_db
      SECRET_KEY: `${SECRET_KEY:-dev-secret-key-change-in-production}
      ENV: dev
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./uploads:/app/uploads

volumes:
  postgres_data:
"@

# ============================================
# 3. docker-compose.prod.yml
# ============================================
$dockerComposeProd = @"
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: `${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
      POSTGRES_DB: ${ProjectSlug}_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    image: `${ECR_REGISTRY}/${ProjectSlug}:`${IMAGE_TAG:-latest}
    restart: always
    ports:
      - "$Port`:$Port"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:`${POSTGRES_PASSWORD}@db:5432/${ProjectSlug}_db
      SECRET_KEY: `${SECRET_KEY:?SECRET_KEY is required}
      ENV: prod
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - uploads_data:/app/uploads

volumes:
  postgres_data:
    name: ${ProjectSlug}_postgres_data
  uploads_data:
    name: ${ProjectSlug}_uploads_data
"@

# ============================================
# 4. GitHub Actions Workflow
# ============================================
$githubWorkflow = @"
name: Deploy to AWS

on:
  push:
    branches: [main, v2]

env:
  AWS_REGION: `${{ secrets.AWS_REGION }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    outputs:
      image_tag: `${{ steps.meta.outputs.tags }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: `${{ secrets.AWS_ROLE_ARN }}
          aws-region: `${{ secrets.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push Docker image
        id: meta
        env:
          ECR_REGISTRY: `${{ secrets.ECR_REGISTRY }}
          ECR_REPOSITORY: `${{ secrets.ECR_REPOSITORY }}
          IMAGE_TAG: `${{ github.sha }}
        run: |
          docker build -t `$ECR_REGISTRY/`$ECR_REPOSITORY:`$IMAGE_TAG -t `$ECR_REGISTRY/`$ECR_REPOSITORY:latest .
          docker push `$ECR_REGISTRY/`$ECR_REPOSITORY:`$IMAGE_TAG
          docker push `$ECR_REGISTRY/`$ECR_REPOSITORY:latest
          echo "tags=`$IMAGE_TAG" >> `$GITHUB_OUTPUT

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: `${{ secrets.AWS_ROLE_ARN }}
          aws-region: `${{ secrets.AWS_REGION }}

      - name: Get or Create EC2 instance
        id: ec2
        run: |
          INSTANCE_ID=`$(aws ec2 describe-instances \
            --filters "Name=tag:Name,Values=${ProjectSlug}" "Name=instance-state-name,Values=running" \
            --query 'Reservations[0].Instances[0].InstanceId' --output text)

          if [ "`$INSTANCE_ID" == "None" ] || [ -z "`$INSTANCE_ID" ]; then
            echo "Creating new EC2 instance..."
            INSTANCE_ID=`$(aws ec2 run-instances \
              --launch-template LaunchTemplateName=${ProjectSlug}-template \
              --query 'Instances[0].InstanceId' --output text)

            aws ec2 wait instance-running --instance-ids `$INSTANCE_ID
            sleep 60  # Wait for SSM agent
          fi

          echo "instance_id=`$INSTANCE_ID" >> `$GITHUB_OUTPUT

      - name: Deploy via SSM
        env:
          INSTANCE_ID: `${{ steps.ec2.outputs.instance_id }}
          ECR_REGISTRY: `${{ secrets.ECR_REGISTRY }}
          ECR_REPOSITORY: `${{ secrets.ECR_REPOSITORY }}
          IMAGE_TAG: `${{ needs.build-and-push.outputs.image_tag }}
        run: |
          COMMAND_ID=`$(aws ssm send-command \
            --instance-ids `$INSTANCE_ID \
            --document-name "AWS-RunShellScript" \
            --parameters commands='[
              "cd /opt/${ProjectSlug}",
              "aws ecr get-login-password --region ${AwsRegion} | docker login --username AWS --password-stdin ${AwsAccountId}.dkr.ecr.${AwsRegion}.amazonaws.com",
              "export ECR_REGISTRY='${AwsAccountId}.dkr.ecr.${AwsRegion}.amazonaws.com'",
              "export IMAGE_TAG='`${{ needs.build-and-push.outputs.image_tag }}'",
              "export POSTGRES_PASSWORD='`${{ secrets.POSTGRES_PASSWORD }}'",
              "export SECRET_KEY='`${{ secrets.SECRET_KEY }}'",
              "docker-compose -f docker-compose.prod.yml pull",
              "docker-compose -f docker-compose.prod.yml up -d"
            ]' \
            --query 'Command.CommandId' --output text)

          aws ssm wait command-executed --command-id `$COMMAND_ID --instance-id `$INSTANCE_ID || true

          STATUS=`$(aws ssm get-command-invocation --command-id `$COMMAND_ID --instance-id `$INSTANCE_ID --query 'Status' --output text)
          echo "Deployment status: `$STATUS"
"@

# ============================================
# 5. AWS Setup Script
# ============================================
$awsSetup = @"
#!/bin/bash
# AWS Setup Script for $ProjectName
# Run this once to create all AWS resources

set -e

# Configuration
AWS_REGION="$AwsRegion"
ACCOUNT_ID="$AwsAccountId"
PROJECT_SLUG="$ProjectSlug"
GITHUB_REPO="$GitHubRepo"
PORT=$Port

echo "============================================"
echo " AWS Setup for `$PROJECT_SLUG"
echo "============================================"

# 1. Create ECR Repository
echo "Creating ECR repository..."
aws ecr create-repository --repository-name `$PROJECT_SLUG --image-scanning-configuration scanOnPush=true 2>/dev/null || echo "ECR repo exists"

# 2. Create OIDC Provider (if not exists)
echo "Creating OIDC provider..."
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 2>/dev/null || echo "OIDC provider exists"

# 3. Create GitHub Actions IAM Role
echo "Creating GitHub Actions role..."
aws iam create-role \
  --role-name github-actions-`$PROJECT_SLUG \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Federated": "arn:aws:iam::'`$ACCOUNT_ID':oidc-provider/token.actions.githubusercontent.com"},
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
        "StringLike": {"token.actions.githubusercontent.com:sub": "repo:'`$GITHUB_REPO':*"}
      }
    }]
  }' 2>/dev/null || echo "Role exists"

# 4. Attach permissions
aws iam put-role-policy --role-name github-actions-`$PROJECT_SLUG --policy-name Permissions --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*"},
    {"Effect": "Allow", "Action": ["ecr:*"], "Resource": "arn:aws:ecr:'`$AWS_REGION':'`$ACCOUNT_ID':repository/'`$PROJECT_SLUG'"},
    {"Effect": "Allow", "Action": ["ec2:Describe*", "ec2:RunInstances", "ec2:CreateTags"], "Resource": "*"},
    {"Effect": "Allow", "Action": ["ssm:SendCommand", "ssm:GetCommandInvocation"], "Resource": "*"},
    {"Effect": "Allow", "Action": "iam:PassRole", "Resource": "arn:aws:iam::'`$ACCOUNT_ID':role/ec2-'`$PROJECT_SLUG'"}
  ]
}'

# 5. Create EC2 Instance Role
echo "Creating EC2 role..."
aws iam create-role --role-name ec2-`$PROJECT_SLUG --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}' 2>/dev/null || echo "EC2 role exists"

aws iam attach-role-policy --role-name ec2-`$PROJECT_SLUG --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore 2>/dev/null || true
aws iam attach-role-policy --role-name ec2-`$PROJECT_SLUG --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly 2>/dev/null || true

aws iam create-instance-profile --instance-profile-name ec2-`$PROJECT_SLUG 2>/dev/null || true
aws iam add-role-to-instance-profile --instance-profile-name ec2-`$PROJECT_SLUG --role-name ec2-`$PROJECT_SLUG 2>/dev/null || true

# 6. Create Security Group
echo "Creating security group..."
SG_ID=`$(aws ec2 create-security-group --group-name `$PROJECT_SLUG-sg --description "SG for `$PROJECT_SLUG" --query 'GroupId' --output text 2>/dev/null || \
  aws ec2 describe-security-groups --filters "Name=group-name,Values=`$PROJECT_SLUG-sg" --query 'SecurityGroups[0].GroupId' --output text)

aws ec2 authorize-security-group-ingress --group-id `$SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 2>/dev/null || true
aws ec2 authorize-security-group-ingress --group-id `$SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 2>/dev/null || true
aws ec2 authorize-security-group-ingress --group-id `$SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0 2>/dev/null || true
aws ec2 authorize-security-group-ingress --group-id `$SG_ID --protocol tcp --port `$PORT --cidr 0.0.0.0/0 2>/dev/null || true

# 7. Get latest Amazon Linux 2023 AMI
AMI_ID=`$(aws ec2 describe-images --owners amazon --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=state,Values=available" --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' --output text)

# 8. Create Launch Template
echo "Creating launch template..."
USERDATA=`$(base64 -w 0 << 'USERDATA_EOF'
#!/bin/bash
yum update -y
yum install -y docker
systemctl enable docker && systemctl start docker
usermod -aG docker ec2-user
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-`$(uname -s)-`$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
mkdir -p /opt/$ProjectSlug && chown ec2-user:ec2-user /opt/$ProjectSlug
USERDATA_EOF
)

aws ec2 create-launch-template --launch-template-name `$PROJECT_SLUG-template --launch-template-data "{
  \"ImageId\": \"`$AMI_ID\",
  \"InstanceType\": \"t3.micro\",
  \"IamInstanceProfile\": {\"Name\": \"ec2-`$PROJECT_SLUG\"},
  \"SecurityGroupIds\": [\"`$SG_ID\"],
  \"UserData\": \"`$USERDATA\",
  \"TagSpecifications\": [{\"ResourceType\": \"instance\", \"Tags\": [{\"Key\": \"Name\", \"Value\": \"`$PROJECT_SLUG\"}]}]
}" 2>/dev/null || echo "Launch template exists"

echo ""
echo "============================================"
echo " AWS Setup Complete!"
echo "============================================"
echo ""
echo "GitHub Secrets to configure:"
echo "  AWS_REGION:        `$AWS_REGION"
echo "  AWS_ROLE_ARN:      arn:aws:iam::`$ACCOUNT_ID:role/github-actions-`$PROJECT_SLUG"
echo "  ECR_REGISTRY:      `$ACCOUNT_ID.dkr.ecr.`$AWS_REGION.amazonaws.com"
echo "  ECR_REPOSITORY:    `$PROJECT_SLUG"
echo "  POSTGRES_PASSWORD: (generate secure password)"
echo "  SECRET_KEY:        (generate with: openssl rand -hex 32)"
"@

# ============================================
# 6. GitHub Secrets Script
# ============================================
$githubSecrets = @"
# PowerShell script to set GitHub Secrets
# Usage: .\set-github-secrets.ps1

param(
    [string]`$AwsRegion = "$AwsRegion",
    [string]`$AwsAccountId = "$AwsAccountId",
    [string]`$ProjectSlug = "$ProjectSlug",
    [string]`$PostgresPassword,
    [string]`$SecretKey
)

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "GitHub CLI not found. Install with: winget install GitHub.cli" -ForegroundColor Red
    exit 1
}

if (-not `$PostgresPassword) { `$PostgresPassword = -join ((48..57) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]`$_}) }
if (-not `$SecretKey) { `$SecretKey = -join ((48..57) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]`$_}) }

`$secrets = @{
    "AWS_REGION" = `$AwsRegion
    "AWS_ROLE_ARN" = "arn:aws:iam::`${AwsAccountId}:role/github-actions-`$ProjectSlug"
    "ECR_REGISTRY" = "`$AwsAccountId.dkr.ecr.`$AwsRegion.amazonaws.com"
    "ECR_REPOSITORY" = `$ProjectSlug
    "POSTGRES_PASSWORD" = `$PostgresPassword
    "SECRET_KEY" = `$SecretKey
}

foreach (`$s in `$secrets.GetEnumerator()) {
    Write-Host "Setting `$(`$s.Key)..." -NoNewline
    `$s.Value | gh secret set `$s.Key 2>&1 | Out-Null
    if (`$LASTEXITCODE -eq 0) { Write-Host " OK" -ForegroundColor Green }
    else { Write-Host " FAILED" -ForegroundColor Red }
}

Write-Host "`nSecrets configured!" -ForegroundColor Green
"@

# Write all files
Write-Host "Creating files..." -ForegroundColor Cyan

Set-Content -Path "$OutputDir/Dockerfile" -Value $dockerfile -NoNewline
Set-Content -Path "$OutputDir/docker-compose.yml" -Value $dockerCompose -NoNewline
Set-Content -Path "$OutputDir/docker-compose.prod.yml" -Value $dockerComposeProd -NoNewline
Set-Content -Path "$OutputDir/.github/workflows/deploy.yml" -Value $githubWorkflow -NoNewline
Set-Content -Path "$OutputDir/deploy/aws/setup-aws.sh" -Value $awsSetup -NoNewline
Set-Content -Path "$OutputDir/deploy/set-github-secrets.ps1" -Value $githubSecrets -NoNewline

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " Skeleton Created!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Files created:" -ForegroundColor Cyan
Write-Host "  - Dockerfile"
Write-Host "  - docker-compose.yml"
Write-Host "  - docker-compose.prod.yml"
Write-Host "  - .github/workflows/deploy.yml"
Write-Host "  - deploy/aws/setup-aws.sh"
Write-Host "  - deploy/set-github-secrets.ps1"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run: bash deploy/aws/setup-aws.sh"
Write-Host "  2. Run: .\deploy\set-github-secrets.ps1"
Write-Host "  3. Push to GitHub to trigger deployment"
