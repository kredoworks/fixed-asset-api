# Deployment Guide: FastAPI to AWS (GitHub Actions → ECR → EC2)

## Overview

This guide covers the complete setup from local development to cloud deployment.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   GitHub    │────▶│   GitHub    │────▶│    AWS      │────▶│    EC2      │
│   Push      │     │   Actions   │     │    ECR      │     │  Instance   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                          │                                        │
                          │         OIDC Auth (No Keys!)           │
                          └───────────────────────────────────────▶│
                                                              SSM Deploy
```

---

## Part 1: Local Development Setup

### Prerequisites
- Python 3.12+
- Poetry
- Docker & Docker Compose
- PostgreSQL (or use Docker)

### Quick Start
```bash
# 1. Clone and setup
git clone <repo>
cd <project>
python setup.py          # Creates venv, installs deps, creates .env

# 2. Start database
docker-compose up db -d

# 3. Run migrations & seed
python reset_db.py

# 4. Start API
uvicorn main:app --reload --port 8000
```

### Key Files
| File | Purpose |
|------|---------|
| `setup.py` | Initialize project (venv, packages, .env) |
| `reset_db.py` | Reset database and seed data |
| `pyproject.toml` | Poetry dependencies |
| `.env` | Environment variables |

---

## Part 2: Docker Setup

### Local Development
```bash
docker-compose up --build
```

### Production Build
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Key Files
| File | Purpose |
|------|---------|
| `Dockerfile` | Python 3.12 + Poetry build |
| `docker-compose.yml` | Local dev with PostgreSQL |
| `docker-compose.prod.yml` | Production with named volumes |

### Dockerfile Highlights
```dockerfile
FROM python:3.12-slim
# Poetry install without dev dependencies
RUN poetry install --without dev --no-interaction --no-ansi
```

---

## Part 3: AWS Infrastructure

### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                         AWS Cloud                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │    ECR      │    │   IAM       │    │      EC2        │  │
│  │  (Images)   │    │  (OIDC)     │    │   (Instance)    │  │
│  └─────────────┘    └─────────────┘    │  ┌───────────┐  │  │
│                                         │  │  Docker   │  │  │
│                                         │  │ Compose   │  │  │
│                                         │  │ ┌───────┐ │  │  │
│                                         │  │ │  API  │ │  │  │
│                                         │  │ │  DB   │ │  │  │
│                                         │  │ └───────┘ │  │  │
│                                         │  └───────────┘  │  │
│                                         └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Resources Created
| Resource | Name | Purpose |
|----------|------|---------|
| ECR Repository | `<project-slug>` | Store Docker images |
| OIDC Provider | `token.actions.githubusercontent.com` | GitHub ↔ AWS auth |
| IAM Role | `github-actions-<project>` | GitHub Actions permissions |
| IAM Role | `ec2-<project>` | EC2 instance permissions |
| Instance Profile | `ec2-<project>` | Attach role to EC2 |
| Security Group | `<project>-sg` | Network access rules |
| Launch Template | `<project>-template` | EC2 configuration |

### Security Group Ports
| Port | Purpose |
|------|---------|
| 22 | SSH |
| 80 | HTTP |
| 443 | HTTPS |
| 7400 | API (custom) |

---

## Part 4: GitHub Actions CI/CD

### Workflow Triggers
- Push to `main` or `v2` branch

### Workflow Steps
1. **Build & Push**
   - Checkout code
   - Authenticate via OIDC (no stored AWS keys!)
   - Build Docker image
   - Push to ECR

2. **Deploy**
   - Find or create EC2 instance
   - Deploy via SSM (no SSH keys needed!)
   - Pull new image and restart containers

### GitHub Secrets Required
| Secret | Example Value |
|--------|---------------|
| `AWS_REGION` | `ap-south-1` |
| `AWS_ROLE_ARN` | `arn:aws:iam::123456789012:role/github-actions-<project>` |
| `ECR_REGISTRY` | `123456789012.dkr.ecr.ap-south-1.amazonaws.com` |
| `ECR_REPOSITORY` | `<project-slug>` |
| `POSTGRES_PASSWORD` | `<secure-password>` |
| `SECRET_KEY` | `<64-char-hex-string>` |

---

## Part 5: Step-by-Step Setup

### Prerequisites
```bash
# Install tools
winget install GitHub.cli
winget install Amazon.AWSCLI

# Login
gh auth login
aws configure
```

### 1. Create AWS Resources
```bash
cd deploy/aws
bash setup-aws.sh
```

### 2. Configure GitHub Secrets
```powershell
cd deploy
.\set-github-secrets.ps1
```

### 3. Push to Deploy
```bash
git push origin main
```

### 4. Monitor Deployment
```bash
gh run watch
# Or visit: https://github.com/<owner>/<repo>/actions
```

### 5. Access API
```
http://<EC2_PUBLIC_IP>:<PORT>/docs
```

---

## Part 6: Data Persistence

### Docker Volumes (Preserved Across Deployments)
```yaml
volumes:
  postgres_data:     # Database files
  uploads_data:      # User uploads
```

### Backup Database
```bash
# SSH into EC2
docker exec <db-container> pg_dump -U postgres <db-name> > backup.sql
```

### Restore Database
```bash
docker exec -i <db-container> psql -U postgres <db-name> < backup.sql
```

---

## Part 7: Troubleshooting

### Check EC2 Instance
```bash
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=<project>" \
  --query 'Reservations[0].Instances[0].[InstanceId,PublicIpAddress,State.Name]'
```

### Check Docker on EC2 (via SSM)
```bash
aws ssm start-session --target <instance-id>
# Then:
docker ps
docker logs <container>
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Launch template not found | Create with correct name (`<project>-template`) |
| OIDC auth failed | Check IAM role trust policy |
| ECR push failed | Check IAM permissions |
| SSM command failed | Ensure SSM agent running on EC2 |
| API not accessible | Check security group ports |

---

## Part 8: Reusable Skeleton

For new projects, use the skeleton generator:

```powershell
.\deploy\create-project-skeleton.ps1 `
  -ProjectName "my-new-api" `
  -AwsRegion "ap-south-1" `
  -Port 8000
```

This creates all deployment files automatically!

---

## Quick Reference

### Commands
```bash
# Local dev
docker-compose up --build

# Deploy manually
git push origin main

# Check deployment
gh run list --limit 5

# Get EC2 IP
aws ec2 describe-instances --filters "Name=tag:Name,Values=<project>" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text

# SSH via SSM (no key needed)
aws ssm start-session --target <instance-id>
```

### File Structure
```
project/
├── .github/workflows/deploy.yml   # CI/CD pipeline
├── deploy/
│   ├── aws/setup-aws.sh           # Create AWS resources
│   ├── set-github-secrets.ps1     # Configure secrets
│   └── create-project-skeleton.ps1 # Generate for new projects
├── docker-compose.yml             # Local dev
├── docker-compose.prod.yml        # Production
├── Dockerfile                     # Container build
└── documentation/
    └── DEPLOYMENT_GUIDE.md        # This file
```
