# Complete Setup to Deployment Guide
## Fixed Asset Verification API

**Version:** 1.0
**Last Updated:** December 2024
**Audience:** Beginners / Freshers

---

# Table of Contents

1. [Introduction](#1-introduction)
2. [Prerequisites](#2-prerequisites)
3. [Understanding the Project](#3-understanding-the-project)
4. [Local Development Setup](#4-local-development-setup)
5. [Understanding Docker](#5-understanding-docker)
6. [AWS Cloud Concepts](#6-aws-cloud-concepts)
7. [CI/CD Pipeline Setup](#7-cicd-pipeline-setup)
8. [Deployment Process](#8-deployment-process)
9. [Troubleshooting](#9-troubleshooting)
10. [Glossary](#10-glossary)

---

# 1. Introduction

## What is this Project?

The **Fixed Asset Verification API** is a backend application that helps organizations track and verify their physical assets (computers, furniture, equipment, etc.). It provides:

- User authentication (login/signup)
- Role-based access control (Admin, Auditor, Owner, Viewer)
- Asset management
- Verification cycles
- Audit trails

## What Will You Learn?

By following this guide, you will learn:

1. How to set up a Python project locally
2. How to use Docker for containerization
3. How to deploy to AWS cloud
4. How CI/CD (Continuous Integration/Deployment) works

---

# 2. Prerequisites

## Software to Install

Before starting, install the following on your computer:

### 2.1 Python 3.12+

**What is it?** The programming language used for this project.

**How to install:**
1. Go to https://www.python.org/downloads/
2. Download Python 3.12 or later
3. During installation, CHECK "Add Python to PATH"
4. Verify installation:
   ```
   python --version
   ```

### 2.2 Git

**What is it?** Version control system to track code changes.

**How to install:**
1. Go to https://git-scm.com/downloads
2. Download and install
3. Verify:
   ```
   git --version
   ```

### 2.3 Visual Studio Code (VS Code)

**What is it?** Code editor where you write and edit code.

**How to install:**
1. Go to https://code.visualstudio.com/
2. Download and install
3. Install recommended extensions:
   - Python
   - Docker
   - GitLens

### 2.4 Docker Desktop

**What is it?** Tool to run applications in containers (isolated environments).

**How to install:**
1. Go to https://www.docker.com/products/docker-desktop
2. Download and install
3. Restart your computer
4. Verify:
   ```
   docker --version
   ```

### 2.5 GitHub CLI

**What is it?** Command-line tool to interact with GitHub.

**How to install (Windows PowerShell):**
```powershell
winget install GitHub.cli
```

**Verify:**
```
gh --version
```

### 2.6 AWS CLI

**What is it?** Command-line tool to interact with Amazon Web Services.

**How to install (Windows PowerShell):**
```powershell
winget install Amazon.AWSCLI
```

**Verify:**
```
aws --version
```

---

# 3. Understanding the Project

## 3.1 Project Structure

```
fixed-asset-api/
│
├── main.py                 # Application entry point
├── pyproject.toml          # Project dependencies (like package.json)
├── poetry.lock             # Locked dependency versions
│
├── api/                    # API endpoints (routes)
│   ├── auth.py             # Login, signup, logout
│   ├── users.py            # User management
│   ├── assets.py           # Asset CRUD operations
│   └── ...
│
├── core/                   # Core utilities
│   ├── security.py         # JWT tokens, password hashing
│   ├── database.py         # Database connection
│   └── ...
│
├── models/                 # Database models (tables)
│   ├── user.py
│   ├── asset.py
│   └── ...
│
├── config/                 # Configuration files
│   ├── dev.py              # Development settings
│   ├── prod.py             # Production settings
│   └── ...
│
├── deploy/                 # Deployment scripts
│   ├── aws/                # AWS setup scripts
│   └── ...
│
├── Dockerfile              # Container build instructions
├── docker-compose.yml      # Local development containers
└── docker-compose.prod.yml # Production containers
```

## 3.2 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Language** | Python 3.12 | Backend programming |
| **Framework** | FastAPI | Web API framework |
| **Database** | PostgreSQL | Data storage |
| **ORM** | SQLAlchemy | Database queries in Python |
| **Auth** | JWT | Secure user authentication |
| **Container** | Docker | Package app with dependencies |
| **Cloud** | AWS | Host the application |
| **CI/CD** | GitHub Actions | Automated deployment |

## 3.3 How the Application Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER (Browser/App)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Auth    │  │  Users   │  │  Assets  │  │ Verifica │        │
│  │  Routes  │  │  Routes  │  │  Routes  │  │  tions   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Users   │  │  Assets  │  │  Cycles  │  │  Logs    │        │
│  │  Table   │  │  Table   │  │  Table   │  │  Table   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## 3.4 User Roles Explained

| Role | Permissions |
|------|-------------|
| **ADMIN** | Full access - can do everything |
| **AUDITOR** | Can verify assets, view all data |
| **OWNER** | Owns specific assets, can update their status |
| **VIEWER** | Read-only access |

---

# 4. Local Development Setup

## Step 1: Clone the Repository

**What does this do?** Downloads the project code to your computer.

```bash
# Open terminal/command prompt
cd Documents/github    # Navigate to your projects folder

# Clone the repository
git clone https://github.com/kredoworks/fixed-asset-api.git

# Enter the project folder
cd fixed-asset-api
```

## Step 2: Run the Setup Script

**What does this do?** Creates virtual environment, installs packages, creates configuration files.

```bash
python setup.py
```

**What happens:**
1. Creates a virtual environment (`.venv` folder)
2. Installs Poetry (package manager)
3. Installs all project dependencies
4. Creates `.env` file with default settings

## Step 3: Activate Virtual Environment

**What is a virtual environment?** An isolated Python environment for this project only.

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**Mac/Linux:**
```bash
source .venv/bin/activate
```

You should see `(.venv)` at the beginning of your terminal prompt.

## Step 4: Start the Database

**What does this do?** Starts PostgreSQL database in a Docker container.

```bash
docker-compose up db -d
```

**Explanation:**
- `docker-compose up` = Start containers defined in docker-compose.yml
- `db` = Only start the database service
- `-d` = Run in background (detached mode)

**Verify it's running:**
```bash
docker ps
```

You should see a container named `fixed-asset-api-db-1` running.

## Step 5: Initialize the Database

**What does this do?** Creates database tables and adds sample data.

```bash
python reset_db.py
```

**What happens:**
1. Drops existing tables (if any)
2. Creates all tables from models
3. Seeds sample data (users, assets, etc.)

## Step 6: Start the API Server

**What does this do?** Runs the FastAPI application.

```bash
uvicorn main:app --reload --port 8000
```

**Explanation:**
- `uvicorn` = ASGI server to run FastAPI
- `main:app` = Look for `app` object in `main.py`
- `--reload` = Auto-restart on code changes
- `--port 8000` = Run on port 8000

## Step 7: Access the API

Open your browser and go to:

- **API Documentation:** http://localhost:8000/docs
- **Alternative Docs:** http://localhost:8000/redoc

You should see the Swagger UI with all available endpoints!

## Step 8: Test Login

1. Go to http://localhost:8000/docs
2. Find `POST /api/auth/login`
3. Click "Try it out"
4. Enter credentials:
   ```json
   {
     "email": "admin@company.com",
     "password": "admin123"
   }
   ```
5. Click "Execute"
6. You should receive a JWT token!

---

# 5. Understanding Docker

## 5.1 What is Docker?

Docker is like a **shipping container for software**. Just like shipping containers can carry any goods and work on any ship, Docker containers can run any application on any computer.

```
Traditional Way:
  "It works on my machine!" 😢
  - Different Python versions
  - Missing dependencies
  - Configuration differences

Docker Way:
  "It works everywhere!" 😊
  - Same environment everywhere
  - All dependencies included
  - Consistent configuration
```

## 5.2 Key Docker Concepts

| Concept | Analogy | Explanation |
|---------|---------|-------------|
| **Image** | Recipe | Instructions to build a container |
| **Container** | Cake | Running instance of an image |
| **Dockerfile** | Recipe book | File containing image instructions |
| **docker-compose** | Menu | Defines multiple containers together |
| **Volume** | Storage box | Persistent data storage |

## 5.3 Our Dockerfile Explained

```dockerfile
# Start with Python 3.12 base image
FROM python:3.12-slim

# Don't create .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Show Python output immediately
ENV PYTHONUNBUFFERED=1

# Install Poetry (package manager)
ENV POETRY_HOME="/opt/poetry"
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set working directory inside container
WORKDIR /app

# Copy dependency files first (for caching)
COPY pyproject.toml poetry.lock* ./

# Install dependencies (without dev packages)
RUN poetry install --without dev --no-interaction --no-ansi

# Copy all project files
COPY . .

# Create uploads folder
RUN mkdir -p uploads

# Expose port 8000
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 5.4 Docker Compose Explained

**docker-compose.yml** defines how multiple containers work together:

```yaml
version: '3.8'

services:
  # Database service
  db:
    image: postgres:15-alpine      # Use PostgreSQL image
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: fixed_asset_db
    ports:
      - "5432:5432"                 # Map port to host
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Persist data

  # API service
  api:
    build: .                        # Build from Dockerfile
    ports:
      - "8000:8000"                 # Map port to host
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/fixed_asset_db
    depends_on:
      - db                          # Start db first

volumes:
  postgres_data:                    # Named volume for persistence
```

## 5.5 Common Docker Commands

```bash
# Build and start all services
docker-compose up --build

# Start in background
docker-compose up -d

# Stop all services
docker-compose down

# View running containers
docker ps

# View container logs
docker-compose logs api

# Enter a container
docker exec -it <container_name> bash

# Remove all containers and volumes (CAUTION!)
docker-compose down -v
```

---

# 6. AWS Cloud Concepts

## 6.1 What is AWS?

Amazon Web Services (AWS) is a cloud platform that provides:
- Servers (EC2)
- Databases (RDS)
- Storage (S3)
- Container registry (ECR)
- And 200+ other services

## 6.2 AWS Services We Use

### ECR (Elastic Container Registry)

**What is it?** A place to store Docker images (like Docker Hub, but private).

```
Your Computer          ECR                    EC2
┌──────────┐     ┌──────────────┐      ┌──────────┐
│  Build   │────▶│ Store Image  │─────▶│   Pull   │
│  Image   │     │              │      │  & Run   │
└──────────┘     └──────────────┘      └──────────┘
```

### EC2 (Elastic Compute Cloud)

**What is it?** Virtual servers in the cloud.

**Think of it as:** Renting a computer in Amazon's data center.

| Instance Type | CPU | Memory | Use Case |
|---------------|-----|--------|----------|
| t3.micro | 2 | 1 GB | Testing, small apps |
| t3.small | 2 | 2 GB | Light production |
| t3.medium | 2 | 4 GB | Production |

### IAM (Identity and Access Management)

**What is it?** Controls who can access what in AWS.

**Components:**
- **Users:** People who access AWS
- **Roles:** Permissions for services (e.g., EC2 can access ECR)
- **Policies:** Rules that define permissions

### SSM (Systems Manager)

**What is it?** Manage EC2 instances without SSH keys.

**Benefits:**
- No SSH key management
- Audit trail of all commands
- Works through AWS console

## 6.3 OIDC Authentication (Advanced)

**What is it?** A secure way for GitHub Actions to access AWS without storing secrets.

**Traditional Way (Risky):**
```
Store AWS Access Key in GitHub Secrets
  ↓
If key is leaked, attacker has AWS access forever
```

**OIDC Way (Secure):**
```
GitHub Actions proves its identity to AWS
  ↓
AWS gives temporary credentials (15 min)
  ↓
Credentials expire automatically
```

---

# 7. CI/CD Pipeline Setup

## 7.1 What is CI/CD?

**CI (Continuous Integration):**
- Automatically build and test code when pushed
- Catch errors early

**CD (Continuous Deployment):**
- Automatically deploy to production
- No manual intervention needed

## 7.2 Our Pipeline Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Developer │────▶│   GitHub    │────▶│   GitHub    │────▶│    AWS      │
│   Pushes    │     │   Receives  │     │   Actions   │     │   Deploys   │
│   Code      │     │   Code      │     │   Runs      │     │   App       │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Detailed Steps:**

1. **Push Code** → Developer pushes to GitHub
2. **Trigger** → GitHub Actions workflow starts
3. **Build** → Docker image is built
4. **Push** → Image pushed to ECR
5. **Deploy** → EC2 pulls image and restarts

## 7.3 GitHub Actions Workflow Explained

File: `.github/workflows/deploy.yml`

```yaml
name: Deploy to AWS

# When to run this workflow
on:
  push:
    branches: [main, v2]   # Run on push to main or v2

jobs:
  build-and-push:
    runs-on: ubuntu-latest  # Use Ubuntu server

    steps:
      # Step 1: Get the code
      - name: Checkout
        uses: actions/checkout@v4

      # Step 2: Login to AWS using OIDC
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}

      # Step 3: Login to ECR
      - name: Login to Amazon ECR
        uses: aws-actions/amazon-ecr-login@v2

      # Step 4: Build and push Docker image
      - name: Build and push
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:latest .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest

  deploy:
    needs: build-and-push  # Wait for build to complete

    steps:
      # Deploy to EC2 via SSM
      - name: Deploy via SSM
        run: |
          aws ssm send-command \
            --instance-ids $INSTANCE_ID \
            --document-name "AWS-RunShellScript" \
            --parameters commands='[
              "docker-compose pull",
              "docker-compose up -d"
            ]'
```

## 7.4 Setting Up GitHub Secrets

GitHub Secrets store sensitive information securely.

**Required Secrets:**

| Secret Name | Example Value | Description |
|-------------|---------------|-------------|
| AWS_REGION | ap-south-1 | AWS region |
| AWS_ROLE_ARN | arn:aws:iam::123...:role/... | IAM role ARN |
| ECR_REGISTRY | 123...dkr.ecr.ap-south-1.amazonaws.com | ECR URL |
| ECR_REPOSITORY | fixed-asset-api | Repository name |
| POSTGRES_PASSWORD | secure-password-123 | Database password |
| SECRET_KEY | 64-char-random-string | JWT signing key |

**How to set secrets:**

1. Go to your GitHub repository
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret

**Or use our script:**
```powershell
.\deploy\set-github-secrets.ps1
```

---

# 8. Deployment Process

## 8.1 One-Time AWS Setup

This creates all necessary AWS resources.

### Step 1: Configure AWS CLI

```bash
aws configure
```

Enter:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (ap-south-1)
- Output format (json)

### Step 2: Run AWS Setup Script

```bash
cd deploy/aws
bash setup-aws.sh
```

**This creates:**
- ECR repository
- OIDC provider
- IAM roles
- Security group
- Launch template

### Step 3: Configure GitHub Secrets

```powershell
cd deploy
.\set-github-secrets.ps1
```

## 8.2 Deploy the Application

Once setup is complete, deployment is automatic!

```bash
# Make changes
git add .
git commit -m "Your changes"
git push origin main
```

**That's it!** GitHub Actions will:
1. Build the Docker image
2. Push to ECR
3. Deploy to EC2

## 8.3 Verify Deployment

### Check GitHub Actions

1. Go to https://github.com/your-repo/actions
2. Watch the workflow run
3. Green checkmark = Success!

### Get EC2 Public IP

```bash
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=fixed-asset-api" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text
```

### Access the API

Open in browser:
```
http://<EC2_PUBLIC_IP>:7400/docs
```

---

# 9. Troubleshooting

## Common Issues and Solutions

### Issue: "Python not found"

**Solution:**
- Reinstall Python with "Add to PATH" checked
- Or manually add to PATH

### Issue: "Docker daemon not running"

**Solution:**
- Open Docker Desktop
- Wait for it to start completely

### Issue: "Permission denied" on Linux/Mac

**Solution:**
```bash
chmod +x script.sh
```

### Issue: GitHub Actions failing

**Check:**
1. Are all secrets configured?
2. Is the AWS role trust policy correct?
3. Do IAM permissions include required actions?

### Issue: EC2 instance not responding

**Check:**
1. Is the instance running?
2. Is the security group allowing traffic on the correct port?
3. Is the application running inside the instance?

**Debug with SSM:**
```bash
aws ssm start-session --target <instance-id>
# Then inside:
docker ps
docker logs <container-name>
```

### Issue: Database connection failed

**Check:**
1. Is the database container running?
2. Is DATABASE_URL correct?
3. Are credentials correct?

---

# 10. Glossary

| Term | Definition |
|------|------------|
| **API** | Application Programming Interface - way for programs to communicate |
| **Backend** | Server-side code that handles data and logic |
| **CI/CD** | Continuous Integration/Continuous Deployment |
| **Container** | Isolated environment to run applications |
| **Docker** | Platform for building and running containers |
| **EC2** | AWS virtual server service |
| **ECR** | AWS container image storage service |
| **Endpoint** | URL path that handles specific requests |
| **FastAPI** | Python web framework for building APIs |
| **Git** | Version control system |
| **GitHub** | Platform for hosting Git repositories |
| **GitHub Actions** | CI/CD service built into GitHub |
| **IAM** | AWS identity and access management |
| **JWT** | JSON Web Token - secure authentication token |
| **OIDC** | OpenID Connect - authentication protocol |
| **ORM** | Object-Relational Mapping - database abstraction |
| **Poetry** | Python dependency management tool |
| **PostgreSQL** | Relational database system |
| **REST** | Architectural style for APIs |
| **SSH** | Secure Shell - remote access protocol |
| **SSM** | AWS Systems Manager - instance management |
| **Virtual Environment** | Isolated Python environment |
| **YAML** | Human-readable data format for config files |

---

# Quick Reference Card

## Local Development
```bash
# Start
docker-compose up -d
python reset_db.py
uvicorn main:app --reload

# Access
http://localhost:8000/docs
```

## Deployment
```bash
# One-time setup
bash deploy/aws/setup-aws.sh
.\deploy\set-github-secrets.ps1

# Deploy (automatic)
git push origin main
```

## Useful Commands
```bash
# Docker
docker ps                    # List containers
docker-compose logs         # View logs
docker-compose down         # Stop all

# AWS
aws ec2 describe-instances  # List EC2s
aws ssm start-session       # SSH via SSM

# GitHub
gh run list                 # List workflow runs
gh run watch                # Watch current run
```

---

**Congratulations!** 🎉

You now understand the complete journey from local development to cloud deployment!

---

*Document created for Fixed Asset Verification API*
*For questions, contact the development team*
