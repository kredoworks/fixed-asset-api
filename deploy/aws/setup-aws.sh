#!/bin/bash
# ONE-TIME AWS Setup Script
# Run this ONCE to create all required AWS resources
#
# Prerequisites:
#   - AWS CLI configured with admin credentials
#   - Replace ACCOUNT_ID with your AWS account ID
#   - Replace GITHUB_ORG/REPO with your repository

set -e

# ============================================
# CONFIGURATION - EDIT THESE
# ============================================
AWS_REGION="ap-south-1"
ACCOUNT_ID="AKIA3J4NVIJKJNYX5VPB"
GITHUB_REPO="kredoworks/fixed-asset-api"
ECR_REPO_NAME="fixed-asset-api"
KEY_PAIR_NAME="my-vpc-01 production kp"  # Must exist already
INSTANCE_TYPE="t3.small"
AMI_ID="ami-03f4878755434977f"  # Ubuntu 22.04 in ap-south-1

# ============================================
# 1. Create ECR Repository
# ============================================
echo "Creating ECR repository..."
aws ecr create-repository \
  --repository-name $ECR_REPO_NAME \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256 \
  2>/dev/null || echo "ECR repository already exists"

ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME"
echo "ECR URI: $ECR_URI"

# ============================================
# 2. Create GitHub OIDC Provider (if not exists)
# ============================================
echo "Creating GitHub OIDC provider..."
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  2>/dev/null || echo "OIDC provider already exists"

# ============================================
# 3. Create IAM Role for GitHub Actions
# ============================================
echo "Creating IAM role for GitHub Actions..."

# Trust policy
cat > /tmp/github-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name github-actions-fixed-asset-api \
  --assume-role-policy-document file:///tmp/github-trust-policy.json \
  2>/dev/null || echo "Role already exists"

# Permissions policy
cat > /tmp/github-permissions.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "arn:aws:ecr:${AWS_REGION}:${ACCOUNT_ID}:repository/${ECR_REPO_NAME}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeLaunchTemplates",
        "ec2:RunInstances",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:SendCommand",
        "ssm:GetCommandInvocation"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name github-actions-fixed-asset-api \
  --policy-name deploy-policy \
  --policy-document file:///tmp/github-permissions.json

GITHUB_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/github-actions-fixed-asset-api"
echo "GitHub Actions Role ARN: $GITHUB_ROLE_ARN"

# ============================================
# 4. Create IAM Role for EC2 Instance
# ============================================
echo "Creating IAM role for EC2..."

cat > /tmp/ec2-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name ec2-fixed-asset-api \
  --assume-role-policy-document file:///tmp/ec2-trust-policy.json \
  2>/dev/null || echo "EC2 role already exists"

# Attach managed policies
aws iam attach-role-policy \
  --role-name ec2-fixed-asset-api \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

aws iam attach-role-policy \
  --role-name ec2-fixed-asset-api \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name ec2-fixed-asset-api-profile \
  2>/dev/null || echo "Instance profile already exists"

aws iam add-role-to-instance-profile \
  --instance-profile-name ec2-fixed-asset-api-profile \
  --role-name ec2-fixed-asset-api \
  2>/dev/null || echo "Role already attached to profile"

echo "EC2 Instance Profile: ec2-fixed-asset-api-profile"

# ============================================
# 5. Create Security Group
# ============================================
echo "Creating Security Group..."

VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)

SG_ID=$(aws ec2 create-security-group \
  --group-name fixed-asset-api-sg \
  --description "Security group for Fixed Asset API" \
  --vpc-id $VPC_ID \
  --query 'GroupId' \
  --output text 2>/dev/null) || SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=fixed-asset-api-sg" \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Add rules
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 2>/dev/null || true
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 7400 --cidr 0.0.0.0/0 2>/dev/null || true

echo "Security Group ID: $SG_ID"

# ============================================
# 6. Create Launch Template
# ============================================
echo "Creating Launch Template..."

# Base64 encode userdata
USERDATA_B64=$(base64 -w 0 deploy/aws/ec2-userdata.sh)

cat > /tmp/launch-template.json << EOF
{
  "ImageId": "${AMI_ID}",
  "InstanceType": "${INSTANCE_TYPE}",
  "KeyName": "${KEY_PAIR_NAME}",
  "SecurityGroupIds": ["${SG_ID}"],
  "IamInstanceProfile": {
    "Name": "ec2-fixed-asset-api-profile"
  },
  "UserData": "${USERDATA_B64}",
  "TagSpecifications": [
    {
      "ResourceType": "instance",
      "Tags": [
        {"Key": "Name", "Value": "fixed-asset-api"},
        {"Key": "Project", "Value": "fixed-asset-api"},
        {"Key": "Environment", "Value": "production"}
      ]
    }
  ],
  "BlockDeviceMappings": [
    {
      "DeviceName": "/dev/sda1",
      "Ebs": {
        "VolumeSize": 20,
        "VolumeType": "gp3",
        "DeleteOnTermination": true
      }
    }
  ]
}
EOF

aws ec2 create-launch-template \
  --launch-template-name fixed-asset-api-template \
  --version-description "v1" \
  --launch-template-data file:///tmp/launch-template.json \
  2>/dev/null || aws ec2 create-launch-template-version \
  --launch-template-name fixed-asset-api-template \
  --version-description "updated" \
  --launch-template-data file:///tmp/launch-template.json

echo "Launch Template: fixed-asset-api-template"

# ============================================
# SUMMARY
# ============================================
echo ""
echo "============================================"
echo "AWS SETUP COMPLETE!"
echo "============================================"
echo ""
echo "Add these secrets to GitHub repository:"
echo "  Settings -> Secrets -> Actions"
echo ""
echo "  AWS_REGION: $AWS_REGION"
echo "  AWS_ROLE_ARN: $GITHUB_ROLE_ARN"
echo "  ECR_REGISTRY: $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
echo "  ECR_REPOSITORY: $ECR_REPO_NAME"
echo ""
echo "  POSTGRES_PASSWORD: (generate secure password)"
echo "  SECRET_KEY: (generate secure key)"
echo ""
echo "============================================"
