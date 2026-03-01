# RheXa Backend - Production Build Guide

## 🚀 Complete Deployment & Optimization Guide

### Prerequisites

- **Python 3.11+** (3.12 recommended)
- **pip** (Python package manager)
- **Virtual Environment** (venv or conda)
- **Database** (MySQL, PostgreSQL, or MongoDB)
- **API Keys** (OpenAI, OpenRouter, Google OAuth, GitHub OAuth)

---

## 📋 Table of Contents

1. [Quick Start (5 minutes)](#quick-start)
2. [Environment Setup](#environment-setup)
3. [Database Configuration](#database-configuration)
4. [Installation & Building](#installation--building)
5. [Running the Application](#running-the-application)
6. [Production Deployment](#production-deployment)
7. [Monitoring & Logging](#monitoring--logging)
8. [Troubleshooting](#troubleshooting)

---

## ⚡ Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Copy environment template
copy .env.example .env

# 3. Configure .env with your settings
# Edit DATABASE_URL, API_KEY, etc.

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run migrations
alembic upgrade head

# 6. Start development server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Navigate to http://localhost:8000/docs
```

---

## 🔧 Environment Setup

### Step 1: Create Virtual Environment

```bash
# Using venv
python -m venv venv

# Activate (choose one):
# Linux/Mac
source venv/bin/activate

# Windows PowerShell
venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate.bat
```

### Step 2: Configure Environment Variables

Create `.env` file in project root:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# ============================================
# APPLICATION
# ============================================
APP_NAME=RheXa API
ENV=production
DEBUG=false

# ============================================
# SECURITY
# ============================================
SECRET_KEY=your-secret-key-here-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# ============================================
# DATABASE
# ============================================
# MySQL example
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/rhexa_db

# PostgreSQL example
# DATABASE_URL=postgresql://user:password@localhost:5432/rhexa_db

# ============================================
# AI & LLM
# ============================================
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=stepfun/step-3.5-flash:free
EMBEDDING_MODEL=text-embedding-3-small

# ============================================
# OAUTH
# ============================================
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

# Frontend URL for redirects
FRONTEND_URL=https://yourdomain.com

# ============================================
# EMAIL (Optional)
# ============================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM_EMAIL=noreply@rhexa.com
```

---

## 🗄️ Database Configuration

### Supported Databases

#### MySQL (Recommended for development)

```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/rhexa_db
```

Install MySQL:
```bash
# macOS
brew install mysql

# Ubuntu/Debian
sudo apt-get install mysql-server

# Or use Docker
docker run -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=rhexa_db \
  -p 3306:3306 \
  mysql:8.0
```

#### PostgreSQL (Recommended for production)

```env
DATABASE_URL=postgresql://user:password@localhost:5432/rhexa_db
```

Install PostgreSQL:
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# Or use Docker
docker run -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=rhexa_db \
  -p 5432:5432 \
  postgres:15
```

#### MongoDB (For document storage)

```env
DATABASE_URL=mongodb://localhost:27017/rhexa_db
```

### Run Database Migrations

```bash
# View migration status
alembic current
alembic history

# Create new migration
alembic revision --autogenerate -m "Migration description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision>
```

---

## 📦 Installation & Building

### Step 1: Install Python Dependencies

```bash
# Upgrade pip, setuptools, wheel
pip install --upgrade pip setuptools wheel

# Install production dependencies
pip install -r requirements.txt

# Also install development dependencies (optional)
pip install -r requirements-dev.txt
```

### Step 2: System Dependencies (if needed)

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  libpq-dev \
  default-libmysqlclient-dev \
  python3-dev

# macOS (with Homebrew)
brew install mysql-connector-c++
```

### Step 3: Verify Installation

```bash
# Check Python version
python --version

# List installed packages
pip list

# Test imports
python -c "import fastapi, sqlalchemy, langchain; print('✓ All packages installed')"
```

---

## ▶️ Running the Application

### Development Mode

```bash
# With auto-reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use:
uvicorn app.main:app --reload

# Access at:
# API Docs: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
# API: http://localhost:8000/api
```

### Production Mode

```bash
# Using Gunicorn with Uvicorn workers (recommended)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# Or using Uvicorn directly
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Performance Tuning

```bash
# Number of workers = (CPU cores × 2) + 1
# For 4-core CPU: use 9 workers

gunicorn app.main:app \
  -w 9 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

---

## 🐳 Docker Deployment

### Build Docker Image

```bash
# Build image
docker build -t rhexa-backend:1.0 .

# Test locally
docker run -p 8000:8000 \
  -e DATABASE_URL="mysql+pymysql://user:password@host:3306/rhexa_db" \
  rhexa-backend:1.0
```

### Docker Compose (Development)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: rhexa_db
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  backend:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      DATABASE_URL: mysql+pymysql://root:password@db:3306/rhexa_db
      DEBUG: "false"

volumes:
  mysql_data:
```

Run:
```bash
docker-compose up -d
```

---

## 🌐 Production Deployment

### Deployment Options

#### 1. **Heroku**

```bash
# Install Heroku CLI
npm install -g heroku

# Login
heroku login

# Create app
heroku create rhexa-backend

# Set environment variables
heroku config:set DATABASE_URL="mysql://..."
heroku config:set SECRET_KEY="..."
heroku config:set OPENAI_API_KEY="..."

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

#### 2. **Railway.app**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up

# View logs
railway logs
```

#### 3. **AWS (EC2 + RDS)**

Steps:
1. Launch EC2 instance (Ubuntu 22.04)
2. Install Python 3.11+
3. Clone repository
4. Set up RDS MySQL instance
5. Configure environment variables
6. Install dependencies
7. Run migrations
8. Start with Gunicorn + Nginx

```bash
# On EC2 instance:
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv nginx

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
```

#### 4. **Google Cloud Run**

```bash
# Login
gcloud auth login

# Deploy
gcloud run deploy rhexa-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL="..." \
  --memory 2Gi \
  --cpu 2
```

#### 5. **Docker Swarm / Kubernetes**

Create `deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rhexa-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rhexa-backend
  template:
    metadata:
      labels:
        app: rhexa-backend
    spec:
      containers:
      - name: backend
        image: rhexa-backend:1.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: rhexa-secrets
              key: database-url
```

Deploy:
```bash
kubectl apply -f deployment.yaml
```

---

## 📊 Monitoring & Logging

### Application Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Application started")
logger.error("Error message")
logger.warning("Warning message")
```

### Performance Monitoring

Track:
- Request latency
- Database query time
- Memory usage
- CPU usage
- Error rates

### Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }
```

Monitor with:
```bash
curl http://localhost:8000/health
```

---

## 🐛 Troubleshooting

### Common Issues

#### Import Errors

```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### Database Connection Error

```
sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError)
```

**Solutions:**
```bash
# Check DATABASE_URL in .env
echo $DATABASE_URL

# Test connection
python -c "from sqlalchemy import create_engine; engine = create_engine('your-url'); print(engine.connect())"

# Verify database is running
# For MySQL: mysql -u root -p
# For PostgreSQL: psql -U user -d rhexa_db
```

#### Port Already in Use

```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or use different port
uvicorn app.main:app --port 8001
```

#### Virtual Environment Issues

```
command not found: python
```

**Solution:**
```bash
# Create fresh virtual environment
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## ✅ Pre-Production Checklist

- [ ] Python 3.11+ installed
- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with all required values
- [ ] Database created and migrations applied (`alembic upgrade head`)
- [ ] API keys configured (OpenAI, OpenRouter, OAuth, etc.)
- [ ] SMTP email configured (optional)
- [ ] Static files configured (if using)
- [ ] Logging configured
- [ ] Health check endpoint working
- [ ] All routes tested
- [ ] Docker image built and tested (if using containers)

---

## 🚀 Performance Optimization

### 1. Database Optimization
```python
# Use connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

### 2. Caching
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_data(key: str):
    return expensive_operation(key)
```

### 3. Async Operations
```python
async def handle_request():
    result = await async_database_query()
    return result
```

### 4. Response Compression
```python
from fastapi.middleware.gzip import GZIPMiddleware

app.add_middleware(GZIPMiddleware, minimum_size=1000)
```

---

## 📚 Documentation

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Alembic Docs](https://alembic.sqlalchemy.org/)
- [LangChain Docs](https://python.langchain.com/)

---

## 💡 Next Steps

1. **Install dependencies:** `pip install -r requirements.txt`
2. **Configure environment:** Copy and edit `.env.example` to `.env`
3. **Set up database:** Create database and run migrations
4. **Test locally:** `uvicorn app.main:app --reload`
5. **Deploy:** Choose platform and follow deployment guide
6. **Monitor:** Set up logging and health checks

---

**Status:** ✅ Ready for Production  
**Version:** 1.0.0  
**Last Updated:** March 1, 2026
