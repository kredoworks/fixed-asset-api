#!/bin/bash
# EC2 UserData Script for Fixed Asset API
# This runs ONCE when the instance is first launched

set -ex
exec > >(tee /var/log/userdata.log) 2>&1

echo "=== Fixed Asset API - EC2 Setup ==="
echo "Date: $(date)"

# Update system
apt-get update -qq
apt-get upgrade -y -qq

# Install Docker
curl -fsSL https://get.docker.com | bash
systemctl enable docker
systemctl start docker

# Install Docker Compose v2
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Also install standalone docker-compose for compatibility
ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
apt-get install -y unzip
unzip -q awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Install SSM Agent (for GitHub Actions to connect)
snap install amazon-ssm-agent --classic
systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Create app directory
mkdir -p /opt/app
chown ubuntu:ubuntu /opt/app

# Create deployment script
cat > /opt/app/deploy.sh << 'DEPLOY_SCRIPT'
#!/bin/bash
set -e

APP_DIR="/opt/app"
cd $APP_DIR

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Pull latest image
docker compose -f docker-compose.prod.yml pull

# Start services (preserves volumes)
docker compose -f docker-compose.prod.yml up -d

# Cleanup old images
docker image prune -f

echo "Deployment complete!"
DEPLOY_SCRIPT

chmod +x /opt/app/deploy.sh
chown ubuntu:ubuntu /opt/app/deploy.sh

echo "=== EC2 Setup Complete ==="
echo "Ready for deployments via SSM"
