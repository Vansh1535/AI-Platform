# 🐳 Docker Deployment Guide

## What Docker Does

Docker packages your app so it runs the **same way everywhere** - your laptop, a server, the cloud. But it doesn't host your app online by itself.

Think of Docker like a shipping container:
- ✅ Packages everything together
- ✅ Works anywhere
- ❌ Doesn't ship itself (you need a truck/ship = hosting platform)

---

## Quick Start (Local Testing)

### 1. Install Docker Desktop
Download from: https://www.docker.com/products/docker-desktop

### 2. Create Environment File
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API keys
notepad .env
```

### 3. Run Everything
```bash
# Start all services (database, backend, frontend)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Access Your Platform
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 5. Stop Everything
```bash
docker-compose down
```

---

## Making It Live on the Internet

### Option A: DigitalOcean App Platform (Easiest - $5/month)

1. **Push code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/ai-platform.git
   git push -u origin main
   ```

2. **Deploy on DigitalOcean**
   - Go to https://cloud.digitalocean.com/apps
   - Click "Create App"
   - Connect your GitHub repo
   - It will auto-detect Docker files
   - Set environment variables (GEMINI_API_KEY, etc.)
   - Deploy!
   - You get: `https://your-app.ondigitalocean.app`

**Cost: $5-12/month**

### Option B: Railway.app (Easiest Free Start)

1. **Go to Railway.app**
   - Sign up at https://railway.app
   - Click "New Project"
   - "Deploy from GitHub"
   
2. **Add Services**
   - Backend (auto-detects Dockerfile)
   - Frontend (auto-detects Dockerfile)
   - PostgreSQL (click "Add Database")

3. **Set Environment Variables** in Railway dashboard:
   ```
   GEMINI_API_KEY=your_key
   SECRET_KEY=random_string
   DATABASE_URL=auto_provided_by_railway
   ```

4. **You get URLs automatically:**
   - Backend: `https://backend-production-xxxx.up.railway.app`
   - Frontend: `https://frontend-production-xxxx.up.railway.app`

**Cost: Free tier available, then $5/month**

### Option C: AWS/Azure (Most Control, More Complex)

**AWS EC2 with Docker:**
```bash
# 1. Launch Ubuntu EC2 instance

# 2. SSH into server
ssh -i your-key.pem ubuntu@your-ec2-ip

# 3. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 4. Clone your repo
git clone https://github.com/yourusername/ai-platform.git
cd ai-platform

# 5. Create .env file
nano .env
# Add your keys

# 6. Run with Docker Compose
docker-compose up -d

# 7. Access via EC2 public IP
# http://your-ec2-ip:3000
```

**Setup Domain & SSL:**
```bash
# Install nginx
sudo apt install nginx certbot python3-certbot-nginx

# Configure nginx
sudo nano /etc/nginx/sites-available/aiplatform

# Get SSL certificate
sudo certbot --nginx -d yourplatform.com
```

**Cost: ~$10-30/month**

---

## Commands You'll Use

### Development
```bash
# Build containers
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart a service
docker-compose restart backend

# Run commands inside container
docker-compose exec backend python scripts/seed_admin.py
```

### Production
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Backup database
docker-compose exec postgres pg_dump -U admin aiplatform > backup.sql
```

### Troubleshooting
```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs backend

# Enter container shell
docker-compose exec backend bash

# Check environment variables
docker-compose exec backend printenv

# Remove everything and start fresh
docker-compose down -v
docker-compose up -d --build
```

---

## Recommended Deployment Path

**For you right now:**

1. **Test locally with Docker** (Today)
   ```bash
   docker-compose up
   # Access at localhost:3000
   ```

2. **Deploy to Railway.app** (5 minutes)
   - Free to start
   - Easiest deployment
   - Automatic HTTPS
   - Get live URL immediately

3. **Later: Move to AWS/DigitalOcean** (When you need more control)
   - Custom domain
   - More resources
   - Full control

---

## Current Status Check

Let's verify your Docker files:

```bash
# Test if Docker is installed
docker --version

# Test backend build
cd Backend_AIPROJ
docker build -t aiplatform-backend .

# Test frontend build
cd ../Frontend_AIPROJ
docker build -t aiplatform-frontend .

# Test full stack
cd ..
docker-compose up
```

---

## Summary

**Docker** = Packaging tool (like a zip file for apps)
**Railway/DigitalOcean/AWS** = Hosting platform (makes it live)

**To make your platform live:**
1. Use Docker to package it ✅ (files created above)
2. Push to GitHub
3. Deploy to Railway.app (free/easy) or DigitalOcean ($5/month)
4. Done! Get public URL

**Want to deploy now? I recommend Railway.app - it's the easiest!**
