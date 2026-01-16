# 🚀 Deployment Guide

## Quick Deployment Steps

### 1. Push to GitHub
```bash
# Ensure you're on the main branch
git branch

# Push to GitHub
git push origin main
```

### 2. Verify Repository
Your repository now includes:
- ✅ Complete README.md with documentation
- ✅ Docker deployment configuration
- ✅ .gitignore (protects sensitive data)
- ✅ .env.example (template for configuration)
- ✅ All production-ready code
- ✅ Frontend and Backend Dockerfiles
- ✅ docker-compose.yml for orchestration

### 3. Deploy on Railway.app

#### Step 1: Create Railway Account
- Go to https://railway.app
- Sign up with GitHub account

#### Step 2: Create New Project
- Click "New Project"
- Select "Deploy from GitHub repo"
- Choose your `ai-platform` repository

#### Step 3: Add Services (5 Services Total)

**Service 1: PostgreSQL**
- Click "Add Service" → "Database" → "PostgreSQL"
- Railway will auto-configure connection

**Service 2: Redis**
- Click "Add Service" → "Database" → "Redis"
- Railway will auto-configure connection

**Service 3: Backend API**
- Click "Add Service" → "GitHub Repo"
- Set Root Directory: `Backend_AIPROJ`
- Set Dockerfile Path: `Backend_AIPROJ/Dockerfile`
- Add Environment Variables:
  ```
  DB_HOST=[Use Railway's Postgres internal hostname]
  DB_PORT=5432
  DB_USER=postgres
  DB_PASS=[Railway auto-generated]
  DB_NAME=railway
  DATABASE_URL=[Railway auto-generated]
  REDIS_URL=[Railway auto-generated]
  GEMINI_API_KEY=your_api_key
  LLM_PROVIDER=gemini
  SECRET_KEY=your_random_secret_key_here
  ADMIN_USERNAME=admin
  ADMIN_PASSWORD=your_secure_password
  ENV=production
  LOG_LEVEL=INFO
  ```
- Exposed Port: 8000

**Service 4: Celery Worker**
- Click "Add Service" → "GitHub Repo"
- Set Root Directory: `Backend_AIPROJ`
- Set Dockerfile Path: `Backend_AIPROJ/Dockerfile`
- Set Start Command: `celery -A app.workers.celery_app worker --loglevel=info`
- Add same environment variables as Backend
- No exposed port needed

**Service 5: Frontend**
- Click "Add Service" → "GitHub Repo"
- Set Root Directory: `Frontend_AIPROJ`
- Set Dockerfile Path: `Frontend_AIPROJ/Dockerfile`
- Add Environment Variables:
  ```
  NEXT_PUBLIC_API_URL=https://[your-backend-url].railway.app
  ```
- Exposed Port: 3000

#### Step 4: Generate Domains
- Go to each service settings
- Click "Generate Domain" for Backend and Frontend
- Note the URLs (you'll need them)

#### Step 5: Update Frontend Environment
- Update Frontend's `NEXT_PUBLIC_API_URL` with Backend's Railway URL
- Redeploy frontend

#### Step 6: Test Deployment
- Visit your frontend URL
- Login with your configured credentials
- Test document upload and RAG features

### 4. Alternative: VPS Deployment

If deploying to your own VPS (DigitalOcean, AWS EC2, etc.):

```bash
# SSH into your server
ssh user@your-server-ip

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install docker-compose-plugin

# Clone repository
git clone https://github.com/yourusername/ai-platform.git
cd ai-platform

# Configure environment
cp .env.example .env
nano .env  # Edit with your values

# Start services
docker compose up -d --build

# View logs
docker compose logs -f

# Setup SSL with nginx (recommended)
# Follow: https://www.nginx.com/blog/using-free-ssltls-certificates-from-lets-encrypt-with-nginx/
```

### 5. Post-Deployment Checklist

- [ ] All 5 services running and healthy
- [ ] Backend API responding at `/health` endpoint
- [ ] Frontend accessible and login working
- [ ] Document upload working
- [ ] RAG search and Q&A functional
- [ ] Environment variables secured (not exposed)
- [ ] Default credentials changed
- [ ] SSL/HTTPS configured
- [ ] Monitoring set up (optional: use Railway's metrics)
- [ ] Backups configured for PostgreSQL

### 6. Monitoring & Maintenance

**Check Service Health:**
```bash
# Railway CLI
railway logs --service backend

# Docker (VPS)
docker compose ps
docker compose logs -f backend
```

**Update Deployment:**
```bash
# Railway auto-deploys on git push
git add .
git commit -m "Update feature"
git push origin main

# VPS manual update
git pull origin main
docker compose up -d --build
```

### 7. Troubleshooting

**Backend not connecting to database:**
- Check `DATABASE_URL` environment variable
- Ensure Postgres service is healthy
- Check logs: `railway logs --service backend`

**Frontend showing CORS errors:**
- Verify `NEXT_PUBLIC_API_URL` is correct
- Check backend CORS settings in `app/main.py`

**Celery not processing tasks:**
- Verify Redis connection
- Check Celery logs
- Ensure environment variables match backend

**LLM features not working:**
- Verify `GEMINI_API_KEY` is set
- Check `LLM_PROVIDER=gemini` is configured
- Review API quota limits

### 8. Cost Estimates

**Railway.app (Hobby Plan):**
- 5 services × $5/month = ~$25/month
- Includes 500 execution hours
- Suitable for demo/small projects

**VPS (DigitalOcean/Linode):**
- $12-24/month for 4GB RAM server
- Unlimited execution time
- Better for production

**AWS/GCP:**
- Variable based on usage
- Free tier available for testing
- ~$30-50/month for production

---

## 🎉 Deployment Complete!

Your AI Platform is now live and ready to showcase!

**Share your deployment:**
- Frontend URL: `https://your-app.railway.app`
- API Docs: `https://your-backend.railway.app/docs`
- GitHub: `https://github.com/yourusername/ai-platform`

**Next Steps:**
- Add custom domain (Railway supports this)
- Enable analytics/monitoring
- Configure automated backups
- Set up CI/CD pipeline
- Add rate limiting for API protection
