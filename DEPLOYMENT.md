# Deployment Guide

## Architecture Overview

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   GitHub Repo   │      │    AWS ECR      │      │    AWS EC2      │
│                 │      │                 │      │                 │
│  Push to v2/main├─────▶│  Docker Image   ├─────▶│  API Container  │
│                 │      │                 │      │  DB Container   │
└─────────────────┘      └─────────────────┘      └─────────────────┘
         │                                                │
         │           GitHub Actions (OIDC)                │
         └────────────────────────────────────────────────┘
```

## One-Time Setup (Do this once)

### Step 1: Create EC2 Key Pair

```bash
aws ec2 create-key-pair \
  --key-name fixed-asset-api-key \
  --query 'KeyMaterial' \
  --output text > fixed-asset-api-key.pem

chmod 400 fixed-asset-api-key.pem
```

### Step 2: Run AWS Setup Script

Edit `deploy/aws/setup-aws.sh` with your:
- AWS Account ID
- Region
- Key pair name

Then run:
```bash
cd deploy/aws
chmod +x setup-aws.sh
./setup-aws.sh
```

This creates:
- ECR repository
- GitHub OIDC provider
- IAM roles (GitHub Actions + EC2)
- Security Group
- EC2 Launch Template

### Step 3: Add GitHub Secrets

Go to: `GitHub Repo → Settings → Secrets → Actions`

Add these secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_REGION` | AWS region | `ap-south-1` |
| `AWS_ROLE_ARN` | OIDC role ARN | `arn:aws:iam::123456789:role/github-actions-fixed-asset-api` |
| `ECR_REGISTRY` | ECR registry URL | `123456789.dkr.ecr.ap-south-1.amazonaws.com` |
| `ECR_REPOSITORY` | ECR repo name | `fixed-asset-api` |
| `POSTGRES_PASSWORD` | Database password | (generate secure password) |
| `SECRET_KEY` | JWT signing key | (generate 64+ char random string) |

Generate secure values:
```bash
# PostgreSQL password
openssl rand -hex 16

# Secret key
openssl rand -hex 32
```

### Step 4: First Deployment

Push to `v2` or `main` branch:
```bash
git push origin v2
```

GitHub Actions will:
1. Build Docker image
2. Push to ECR
3. Create EC2 instance (first time only)
4. Deploy containers

---

## Normal Deployment Flow

Just push code:
```bash
git add .
git commit -m "Your changes"
git push origin v2
```

GitHub Actions automatically:
1. Builds new image
2. Pushes to ECR
3. Deploys to existing EC2
4. **Database data is preserved!**

---

## Data Safety

### What Happens on Redeploy?

| Component | On Redeploy |
|-----------|-------------|
| API Container | Replaced with new version |
| DB Container | **Restarted, data preserved** |
| PostgreSQL Data | **Preserved in Docker volume** |
| Uploaded Files | **Preserved in Docker volume** |

### Why Data is Safe

Docker volumes are **named volumes** that persist:
```yaml
volumes:
  postgres_data:
    name: fixed_asset_postgres_data  # This survives container recreation
```

### DANGEROUS Commands (NEVER use in CI/CD)

```bash
# ❌ NEVER - Deletes all data
docker-compose down -v
docker-compose down --volumes

# ❌ NEVER - Deletes database volume
docker volume rm fixed_asset_postgres_data

# ❌ NEVER - Deletes all volumes
docker volume prune -f
```

### Safe Commands

```bash
# ✅ SAFE - Stops containers, keeps data
docker-compose down

# ✅ SAFE - Updates containers
docker-compose pull
docker-compose up -d

# ✅ SAFE - Restarts services
docker-compose restart

# ✅ SAFE - Removes old images
docker image prune -f
```

---

## Manual Deployment (if needed)

SSH into EC2:
```bash
ssh -i fixed-asset-api-key.pem ubuntu@EC2_PUBLIC_IP
```

Deploy manually:
```bash
cd /opt/app

# Login to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin YOUR_ECR_REGISTRY

# Pull and restart
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## Common Issues

### 1. Deployment Fails - "Instance not found"

**Cause**: No EC2 instance exists yet

**Fix**: Run workflow with "Force create new EC2" option, or first deployment auto-creates

### 2. SSM Command Timeout

**Cause**: SSM agent not ready

**Fix**: Wait 2-3 minutes after EC2 creation, then re-run

### 3. Docker Pull Fails - "Access denied"

**Cause**: EC2 instance role missing ECR permissions

**Fix**: Verify `ec2-fixed-asset-api` role has `AmazonEC2ContainerRegistryReadOnly` policy

### 4. API Not Accessible

**Check**:
```bash
# On EC2
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs api
```

**Common fixes**:
- Security group: port 7400 must be open
- Container health: check logs for errors

### 5. Database Connection Failed

**Check** `.env` file has correct `POSTGRES_PASSWORD`

---

## Backup & Restore

### Backup Database

```bash
# On EC2
docker exec fixed_asset_db pg_dump -U postgres fixed_asset_db > backup.sql
```

### Restore Database

```bash
# On EC2
docker exec -i fixed_asset_db psql -U postgres fixed_asset_db < backup.sql
```

---

## Future Improvements (When IaC is introduced)

- [ ] Move to Terraform for infrastructure
- [ ] Add RDS for managed PostgreSQL
- [ ] Add ALB for HTTPS
- [ ] Add auto-scaling group
- [ ] Add staging environment
- [ ] Add database migrations in CI/CD

---

## Cost Estimate (Free Tier)

| Resource | Cost |
|----------|------|
| EC2 t3.micro | Free tier (750 hrs/month) |
| ECR | Free tier (500MB storage) |
| EBS (20GB gp3) | ~$1.60/month |
| Data transfer | Free tier (100GB) |

**Total**: ~$2/month (after free tier)

---

## Quick Reference

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f api

# Restart API
docker compose -f docker-compose.prod.yml restart api

# Check status
docker compose -f docker-compose.prod.yml ps

# SSH to EC2
ssh -i fixed-asset-api-key.pem ubuntu@$(aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=fixed-asset-api" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)
```
