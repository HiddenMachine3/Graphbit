# Docker Setup - Graphbit Backend

## Goal
**Single Docker container for FastAPI backend. Use Neon (free PostgreSQL) for database. Same setup for dev and production.**

## Architecture

```
DEVELOPMENT & PRODUCTION (Same setup):

┌─────────────────────────┐
│   Your Machine / Cloud  │
│                         │
│  ┌──────────────────┐   │
│  │ FastAPI Container│   │
│  │  (Port 8000)     │   │
│  │  Hot Reload ON   │   │
│  └────────┬─────────┘   │
│           │             │
└───────────┼─────────────┘
            │
            │ Internet
            │
    ┌───────▼──────────┐
    │  Neon Database   │
    │  (Free Tier)     │
    │  + pgvector      │
    └──────────────────┘
```

## Why Neon?
- ✅ Free tier available
- ✅ pgvector pre-installed
- ✅ No manual setup needed
- ✅ Works from anywhere (dev machine, cloud, CI/CD)
- ✅ Automatic backups
- ✅ Same database for dev and prod (or separate if needed)

---

## Setup Steps

### Step 1: Get Neon Database (5 minutes)

1. Go to https://neon.tech
2. Sign up (free)
3. Create a new project
4. Copy the connection string (looks like):
   ```
   postgresql://user:password@ep-cool-name-123456.us-east-2.aws.neon.tech/dbname?sslmode=require
   ```
5. Change to psycopg format by replacing `postgresql://` with `postgresql+psycopg://`:
   ```
   postgresql+psycopg://user:password@ep-cool-name-123456.us-east-2.aws.neon.tech/dbname?sslmode=require
   ```

**Note:** pgvector is already installed on Neon, nothing extra needed!

---

### Step 2: Clean Up Unused Code

**Delete:**
```bash
cd Backend
rm -rf app/worker/  # Delete entire folder
```

**Edit `requirements.txt`** - Remove:
```
celery==5.4.0
redis==5.0.8
```

**Edit `app/core/config.py`** - Remove:
```python
CELERY_BROKER_URL: str
CELERY_RESULT_BACKEND: str
```

---

### Step 3: Create Docker Files

**File: `Backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ./app

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Run with hot reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**File: `Backend/docker-compose.yml`**

```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: graphbit_api
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app/app  # Hot reload - code changes reflect instantly
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY:-dev-secret-key-change-for-production}
      - HF_TOKEN=${HF_TOKEN}
      - HF_EMBED_MODEL=${HF_EMBED_MODEL:-BAAI/bge-base-en-v1.5}
      - HF_KEYPHRASE_MODEL=${HF_KEYPHRASE_MODEL:-ml6team/keyphrase-extraction-distilbert-inspec}
      - SUGGESTION_THRESHOLD=${SUGGESTION_THRESHOLD:-0.75}
      - SUGGESTION_SEMANTIC_WEIGHT=${SUGGESTION_SEMANTIC_WEIGHT:-0.6}
      - SUGGESTION_KEYWORD_WEIGHT=${SUGGESTION_KEYWORD_WEIGHT:-0.4}
      - SUGGESTION_TOP_K=${SUGGESTION_TOP_K:-20}
      - SUGGESTION_DEDUP_THRESHOLD=${SUGGESTION_DEDUP_THRESHOLD:-0.9}
    restart: unless-stopped
```

**File: `Backend/.env`**

```bash
# Neon Database (REQUIRED)
DATABASE_URL=postgresql+psycopg://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require

# HuggingFace Token (REQUIRED)
HF_TOKEN=your_huggingface_token_here

# Secret Key (REQUIRED for production, optional for dev)
SECRET_KEY=dev-secret-key-change-for-production
```

**File: `Backend/.dockerignore`**
```
__pycache__
*.pyc
.Python
*.so
*.egg-info
.env
.venv
.git
*.md
.vscode
.idea
*.log
.pytest_cache
venv/
.tmp/
tests/
docs/
scripts/
seed_materials/
.conda_pg/
.local_pgvector_db/
```

---

### Step 4: Run Development

```bash
cd Backend

# First time - build image
docker-compose up --build

# Daily use - just start
docker-compose up

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Rebuild after requirements.txt changes
docker-compose up --build
```

**Access:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

**Code Changes:**
- Edit files in `app/` folder
- Changes auto-reload instantly (no rebuild needed)
- Only rebuild if `requirements.txt` changes

---

### Step 5: Deploy to Production

**Option 1: Railway (Easiest - Free tier available)**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# From Backend folder, init project
railway init

# Link to Neon database (or Railway can provision one)
railway link

# Set environment variables
railway variables set DATABASE_URL="your-neon-url"
railway variables set SECRET_KEY="$(openssl rand -hex 32)"
railway variables set HF_TOKEN="your-hf-token"

# Deploy
railway up

# Done! Railway auto-detects Dockerfile and deploys
```

**Option 2: Render (Simple - Free tier available)**

1. Push code to GitHub
2. Go to https://render.com
3. New → Web Service
4. Connect GitHub repo, select `Backend` folder
5. Docker detected automatically
6. Add environment variables:
   - `DATABASE_URL` (your Neon connection string)
   - `SECRET_KEY` (generate: `openssl rand -hex 32`)
   - `HF_TOKEN` (your HuggingFace token)
7. Deploy

**Option 3: Fly.io (Good for production)**

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# From Backend folder
cd Backend
fly launch

# Set secrets
fly secrets set DATABASE_URL="postgresql+psycopg://..."
fly secrets set SECRET_KEY="$(openssl rand -hex 32)"
fly secrets set HF_TOKEN="your-hf-token"

# Deploy
fly deploy
```

**Option 4: DigitalOcean App Platform**

1. Push to GitHub
2. DigitalOcean → App Platform → Create App
3. Select repo, point to `Backend` folder
4. Auto-detects Dockerfile
5. Add environment variables (DATABASE_URL, SECRET_KEY, HF_TOKEN)
6. Deploy

---

## Environment Variables

| Variable | Required | Dev Value | Production Value |
|----------|----------|-----------|------------------|
| `DATABASE_URL` | ✅ Yes | Neon connection string | Same or separate Neon DB |
| `HF_TOKEN` | ✅ Yes | Your HF token | Same token |
| `SECRET_KEY` | ⚠️ Yes for prod | `dev-secret-key` | `openssl rand -hex 32` |
| `HF_EMBED_MODEL` | No | Auto | Auto (default) |
| `HF_KEYPHRASE_MODEL` | No | Auto | Auto (default) |

---

## Testing

**Local:**
```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs

# Test database connection
curl http://localhost:8000/api/v1/projects
```

**Production:**
```bash
# Replace with your production URL
curl https://your-app.railway.app/health
curl https://your-app.railway.app/docs
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Container won't start | Check logs: `docker-compose logs` |
| Can't connect to Neon | Verify DATABASE_URL format starts with `postgresql+psycopg://` |
| "HF_TOKEN not set" | Add to `.env` file |
| Code changes not reflecting | Check volume is mounted in docker-compose.yml |
| Port 8000 in use | Change port: `8001:8000` in docker-compose.yml |

---

## Database Migrations

**Neon handles migrations automatically!**

When you start the FastAPI app:
1. SQLAlchemy auto-creates tables (via `Base.metadata.create_all` in `main.py`)
2. No manual migrations needed for basic setup
3. For production, consider using Alembic for controlled migrations

**To seed data:**
```bash
# Run inside container
docker-compose exec api python seed_data.py

# or with reset
docker-compose exec api python seed_data.py --reset
```

---

## Quick Summary

**The Setup:**
- ✅ One Docker container (FastAPI backend)
- ✅ Neon database (free, cloud-hosted, pgvector included)
- ✅ Same database for dev and production (or separate if you want)
- ✅ Hot reload for development
- ✅ Deploy to Railway/Render/Fly.io in minutes

**What You Get:**
- All developers use identical environment
- One command to start: `docker-compose up`
- Code changes reflect instantly (no rebuilds)
- Free hosting options available (Railway, Render, Fly.io free tiers)
- No complex infrastructure

**Time to Get Running:**
- Neon setup: 2 minutes
- Docker first run: 5 minutes
- Daily startup: 10 seconds
- Production deploy: 10 minutes

**Costs:**
- Neon free tier: 0.5GB storage, plenty for development
- Railway/Render free tier: Good for small projects
- Upgrade when needed (Neon Pro: $19/mo, Railway Pro: $5/mo)

---

## Next Steps

1. **Get Neon database** → https://neon.tech (2 min)
2. **Clean up code** → Remove Celery/Redis files (5 min)
3. **Create Docker files** → Copy-paste from above (2 min)
4. **Run locally** → `docker-compose up` (1 min)
5. **Deploy** → Push to Railway/Render (10 min)

**Total time: ~20 minutes to production-ready setup!**
