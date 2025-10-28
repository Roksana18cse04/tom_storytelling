# Docker Deployment Guide - Tom Storytelling

## Prerequisites

- Docker installed ([Download Docker](https://www.docker.com/products/docker-desktop))
- Docker Compose installed (included with Docker Desktop)
- `.env` file with your credentials

## Quick Start

### 1. Setup Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
copy .env.example .env
```

Edit `.env`:
```
OPENAI_API_KEY=your_openai_api_key_here
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
MONGO_URL=mongodb://localhost:27017/tom_storytelling
```

### 2. Build Docker Image

```bash
docker build -t tom-storytelling .
```

### 3. Run with Docker Compose

```bash
docker-compose up -d
```

### 4. Check Application

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 5. View Logs

```bash
docker-compose logs -f
```

### 6. Stop Application

```bash
docker-compose down
```

## Manual Docker Run (without docker-compose)

```bash
docker run -d ^
  --name tom_storytelling ^
  -p 8000:8000 ^
  -e OPENAI_API_KEY=your_key ^
  -e CLOUDINARY_CLOUD_NAME=your_cloud ^
  -e CLOUDINARY_API_KEY=your_key ^
  -e CLOUDINARY_API_SECRET=your_secret ^
  -e MONGO_URL=your_mongo_url ^
  -v %cd%/user_images:/app/user_images ^
  tom-storytelling
```

## AWS Deployment

### Option 1: AWS ECS (Elastic Container Service)

#### Step 1: Push to Amazon ECR

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository
aws ecr create-repository --repository-name tom-storytelling --region us-east-1

# Tag your image
docker tag tom-storytelling:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/tom-storytelling:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/tom-storytelling:latest
```

#### Step 2: Deploy to ECS Fargate

1. Go to AWS ECS Console
2. Create new cluster (Fargate)
3. Create task definition:
   - Container image: Your ECR image URL
   - Port: 8000
   - Environment variables: Add all from `.env`
   - CPU: 512, Memory: 1024
4. Create service with task definition
5. Configure load balancer (optional)

### Option 2: AWS App Runner (Easiest)

1. Go to AWS App Runner Console
2. Create service
3. Source: Container registry → Amazon ECR
4. Select your image
5. Configure:
   - Port: 8000
   - Environment variables: Add all from `.env`
   - CPU: 1 vCPU, Memory: 2 GB
6. Deploy

### Option 3: AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p docker tom-storytelling --region us-east-1

# Create environment
eb create tom-storytelling-env

# Deploy
eb deploy
```

## Troubleshooting

### View container logs:
```bash
docker logs tom_storytelling
```

### Access container shell:
```bash
docker exec -it tom_storytelling /bin/bash
```

### Check container status:
```bash
docker ps
```

### Rebuild after changes:
```bash
docker-compose up -d --build
```

### Remove all containers and images:
```bash
docker-compose down
docker rmi tom-storytelling
```

## Production Considerations

1. **Environment Variables**: Use AWS Secrets Manager or Parameter Store
2. **Database**: Use MongoDB Atlas or AWS DocumentDB
3. **Images**: Currently stored in Cloudinary (already configured)
4. **Monitoring**: Enable CloudWatch logs and metrics
5. **Scaling**: Configure auto-scaling in ECS/App Runner
6. **Security**: Use VPC, security groups, and IAM roles

## Cost Estimation

- **AWS App Runner**: ~$25-50/month (1 vCPU, 2GB RAM)
- **AWS ECS Fargate**: ~$15-30/month (0.5 vCPU, 1GB RAM)
- **MongoDB Atlas**: Free tier available (512MB)
- **Cloudinary**: Free tier available (25GB storage)

## Support

For issues, check:
- Docker logs: `docker-compose logs -f`
- Health endpoint: http://localhost:8000/health
- API docs: http://localhost:8000/docs
