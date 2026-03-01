# RheXa Backend - Complete Documentation

## 📚 Documentation Index

### Quick Start
- **[BACKEND_BUILD_GUIDE.md](./BACKEND_BUILD_GUIDE.md)** - Complete setup & deployment guide (3000+ words)

### Configuration
- **[.env.example](./.env.example)** - Environment variables template

### Optimization
- **[BACKEND_OPTIMIZATIONS.md](./BACKEND_OPTIMIZATIONS.md)** - Performance & security checklist

### API Endpoints
Access interactive API documentation:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## ⚡ Quick Start (5 minutes)

```bash
# 1. Activate virtual environment
source .venv/bin/activate    # Linux/Mac
# OR
.venv\Scripts\activate       # Windows

# 2. Copy environment file
cp .env.example .env

# 3. Update .env with your settings
# (Database URL, API keys, etc.)

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run migrations
alembic upgrade head

# 6. Start server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 7. View docs at http://localhost:8000/docs
```

---

## 🔧 Configuration

### Environment Variables

Required variables:
```env
SECRET_KEY=<generates with: secrets.token_urlsafe(32)>
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/rhexa_db
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
```

Optional variables:
```env
GOOGLE_CLIENT_ID=...
GITHUB_CLIENT_ID=...
SMTP_HOST=...
REDIS_URL=...
```

See [.env.example](./.env.example) for complete template.

---

## 🚀 Deployment

### Development
```bash
uvicorn app.main:app --reload
```

### Production
```bash
# Using Gunicorn (recommended)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# Using Docker
docker build -t rhexa-backend .
docker run -p 8000:8000 rhexa-backend
```

### Cloud Deployment

- **Heroku:** See [BACKEND_BUILD_GUIDE.md](./BACKEND_BUILD_GUIDE.md#1-heroku)
- **AWS:** See [BACKEND_BUILD_GUIDE.md](./BACKEND_BUILD_GUIDE.md#3-aws-ec2--rds)
- **Google Cloud Run:** See [BACKEND_BUILD_GUIDE.md](./BACKEND_BUILD_GUIDE.md#4-google-cloud-run)
- **Railway.app:** See [BACKEND_BUILD_GUIDE.md](./BACKEND_BUILD_GUIDE.md#2-railwayapp)

---

## 📊 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login with credentials
- `POST /api/auth/google/login` - Google OAuth
- `POST /api/auth/github/login` - GitHub OAuth
- `POST /api/auth/refresh` - Refresh JWT token

### Documents
- `POST /api/upload` - Upload document (PDF, Excel, CSV, TXT)
- `GET /api/documents` - List user's documents
- `POST /api/documents/{doc_id}/process` - Process document

### Chat & RAG
- `POST /api/chat` - Send message
- `GET /api/search` - Search documents
- `POST /api/chat/stream` - WebSocket chat (real-time)

### Widget
- `GET /api/widget/config` - Get widget configuration
- `POST /api/widget/embed` - Generate embed code

### Organization
- `GET /api/org/settings` - Organization settings
- `POST /api/org/settings` - Update settings

### User Profile
- `GET /api/user/profile` - Get user profile
- `PUT /api/user/profile` - Update profile
- `POST /api/user/avatar` - Upload avatar

### Data Sources
- `GET /api/data-sources` - List data sources
- `POST /api/data-sources` - Add new data source
- `DELETE /api/data-sources/{id}` - Delete data source

### Health & Status
- `GET /health` - Health check
- `GET /api/status` - System status

---

## 🗄️ Database

### Supported Databases

**MySQL (Recommended for development)**
```
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/rhexa_db
```

**PostgreSQL (Recommended for production)**
```
DATABASE_URL=postgresql://user:password@localhost:5432/rhexa_db
```

**MongoDB (For document storage)**
```
DATABASE_URL=mongodb://localhost:27017/rhexa_db
```

### Migrations

```bash
# View current migration
alembic current

# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

---

## 🔐 Security

### Best Practices

1. **Secrets Management**
   - Never commit `.env` to git
   - Use `.env.example` as template
   - Rotate secrets quarterly

2. **API Authentication**
   - JWT tokens with 7-day expiry
   - Refresh token mechanism
   - OAuth integration (Google, GitHub)

3. **Input Validation**
   - Pydantic models validate all inputs
   - File upload restrictions
   - Rate limiting on endpoints

4. **Database Security**
   - SQL injection prevention (ORM)
   - Password hashing (bcrypt)
   - Connection encryption (TLS)

---

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Logs
```bash
# View application logs
tail -f logs/rhexa.log

# Or use Docker
docker logs <container-id>
```

### Metrics
- Request latency
- Database query time
- Error rates
- User activity

---

## 🐛 Troubleshooting

### Common Issues

#### Import Error
```
ModuleNotFoundError: No module named 'fastapi'
```
**Solution:** `pip install -r requirements.txt`

#### Database Connection Failed
```
sqlalchemy.exc.OperationalError
```
**Solution:** Check `DATABASE_URL` in `.env` and verify database is running

#### Port 8000 Already in Use
```
OSError: [Errno 48] Address already in use
```
**Solution:** `lsof -i :8000` and `kill -9 <PID>`

#### Missing Environment Variables
```
pydantic_core._pydantic_core.ValidationError
```
**Solution:** Copy `.env.example` to `.env` and fill in required values

---

## 📈 Performance

### Optimization Tips

1. **Database**
   - Use connection pooling
   - Create indexes on frequently queried columns
   - Use EXPLAIN ANALYZE

2. **Caching**
   - Enable Redis caching
   - Cache frequently accessed data
   - Set reasonable TTL

3. **API**
   - Use async operations
   - Enable response compression
   - Implement request pagination

4. **Workers**
   - Set workers = (CPU cores × 2) + 1
   - Monitor memory usage
   - Enable auto-restart

---

## 🚀 Scaling

### Horizontal Scaling
- Add more servers behind load balancer
- Use Kubernetes for orchestration
- Database read replicas

### Vertical Scaling
- Increase server CPU/Memory
- Optimize queries with indexes
- Upgrade database tier

### Cost Optimization
- Use managed databases (AWS RDS, CloudSQL)
- Use serverless (AWS Lambda, Cloud Run)
- Auto-scaling groups
- Rate limiting

---

## ✅ Pre-Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] API keys obtained (OpenAI, OpenRouter, OAuth)
- [ ] SMTP configured (if using email)
- [ ] CORS origins set correctly
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Database backups automated
- [ ] Monitoring setup
- [ ] Health check endpoint working
- [ ] All tests passing
- [ ] API documentation reviewed
- [ ] Error handling tested
- [ ] Load testing completed

---

## 🆘 Support

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [LangChain Documentation](https://python.langchain.com/)

### API Documentation
While running, visit:
- Interactive Docs: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

### Community
- [FastAPI Discord](https://discord.gg/VQjSZaeJmf)
- [Python Discord](https://discord.gg/python)

---

## 📞 Next Steps

1. **Setup:** Follow [BACKEND_BUILD_GUIDE.md](./BACKEND_BUILD_GUIDE.md)
2. **Configure:** Update `.env` with your settings
3. **Database:** Run migrations with `alembic upgrade head`
4. **Server:** Start with `uvicorn app.main:app --reload`
5. **Deploy:** Choose deployment platform and follow guide

---

**Status:** ✅ Production Ready  
**Version:** 1.0.0  
**Last Updated:** March 1, 2026
