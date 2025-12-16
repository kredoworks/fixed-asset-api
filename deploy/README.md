# Deployment Options

## Option 1: One-Click AWS CloudFormation (Recommended)

Click the button below to deploy:

[![Launch Stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=fixed-asset-api&templateURL=https://raw.githubusercontent.com/kredoworks/fixed-asset-api/v2/deploy/cloudformation.yaml)

**Or manually:**
1. Go to [AWS CloudFormation Console](https://console.aws.amazon.com/cloudformation)
2. Click "Create Stack" → "With new resources"
3. Upload `cloudformation.yaml`
4. Enter parameters (KeyPair name)
5. Click "Create Stack"
6. Wait ~5 minutes

**What gets created:**
- EC2 instance (Ubuntu 22.04)
- Security Group (ports 22, 80, 443, 8000)
- Elastic IP (stable public IP)
- Docker containers (API + PostgreSQL)

---

## Option 2: EC2 Deploy Script

SSH into any Ubuntu EC2 instance and run:

```bash
curl -sSL https://raw.githubusercontent.com/kredoworks/fixed-asset-api/v2/deploy/ec2-deploy.sh | sudo bash
```

---

## Option 3: Local Docker

```bash
git clone -b v2 https://github.com/kredoworks/fixed-asset-api.git
cd fixed-asset-api
docker-compose up -d
```

---

## Option 4: Railway (Zero Config)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

1. Click button above
2. Connect GitHub repo
3. Railway auto-detects Dockerfile
4. Add PostgreSQL plugin
5. Set environment variables

---

## Option 5: Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. New → Web Service
3. Connect GitHub repo
4. Set:
   - Environment: Docker
   - Add PostgreSQL database
   - Set env vars from `.env.example`

---

## After Deployment

| Item | URL |
|------|-----|
| API | `http://YOUR_IP:8000` |
| Swagger Docs | `http://YOUR_IP:8000/docs` |
| Health Check | `http://YOUR_IP:8000/health` |

**Test Credentials:**
| Role | Email | Password |
|------|-------|----------|
| ADMIN | admin@company.com | admin123 |
| AUDITOR | john.auditor@company.com | auditor123 |
| OWNER | mike.developer@company.com | owner123 |
| VIEWER | viewer@company.com | viewer123 |

---

## Troubleshooting

**Check logs:**
```bash
cd /opt/fixed-asset-api
docker-compose logs -f api
docker-compose logs -f db
```

**Restart services:**
```bash
docker-compose restart api
```

**Reset database:**
```bash
docker-compose run --rm db-init
```

**View deployment log (EC2):**
```bash
cat /var/log/user-data.log
```
