# Production Deployment Checklist

This checklist ensures all required steps are completed before deploying to production.

---

## Pre-Deployment Phase (1-2 hours)

### Security

- [ ] Change all default passwords (PostgreSQL, SECRET_KEY, etc.)
  - [ ] Generate strong password: `openssl rand -base64 32`
  - [ ] Update in `.env.production`
- [ ] Review CORS_ORIGINS - only include your domains
- [ ] Enable HTTPS/SSL (Let's Encrypt or your CA)
- [ ] Review Nginx security headers (already configured)
- [ ] Verify SECRET_KEY is 32+ characters and random
- [ ] Ensure no secrets in git (use .gitignore)

### Database

- [ ] Choose PostgreSQL over SQLite for production
- [ ] Set strong POSTGRES_PASSWORD
- [ ] Configure database backups (daily recommended)
- [ ] Test database restore procedure
- [ ] Plan disk space (50GB+ recommended)
- [ ] Enable PostgreSQL logging

### Backend

- [ ] Set LOG_LEVEL=INFO (not DEBUG)
- [ ] Configure LLM API key if using (OPENAI_API_KEY)
- [ ] Test API endpoints with sample data
- [ ] Run backend tests: `pytest tests/ -v`
- [ ] Check all environment variables in `.env.production`
- [ ] Set WORKERS=4 (adjust based on CPU cores)

### Frontend

- [ ] Update VITE_API_URL to correct domain
- [ ] Test all pages and workflows
- [ ] Verify API integration works
- [ ] Test file uploads (drag-drop)
- [ ] Test comparison table and exports
- [ ] Build and test: `npm run build && npm run preview`

### Infrastructure

- [ ] Choose deployment platform (Docker)
- [ ] Plan domain/DNS setup
- [ ] Set up SSL certificates
- [ ] Plan backup strategy
- [ ] Plan monitoring/alerting
- [ ] Set up log aggregation

---

## Docker Setup and Configuration (30 minutes)

### For Docker Compose

- [ ] Copy template: `cp .env.production .env`
- [ ] Edit `.env` with production values
- [ ] Build images: `docker-compose -f docker/docker-compose.yml build`
- [ ] Test locally: `docker-compose -f docker/docker-compose.yml up -d`
- [ ] Verify services: `docker-compose ps`
- [ ] Check logs: `docker-compose logs -f backend`
- [ ] Test API: `curl http://localhost/api/health`
- [ ] Stop and transfer to production: `docker-compose down`

---

## Database Initialization Phase (10 minutes)

- [ ] Database schema created automatically via init-db.sql
- [ ] Verify tables exist:
  ```sql
  SELECT table_name FROM information_schema.tables WHERE table_schema='public';
  ```
- [ ] Verify indexes created
- [ ] Test connection from backend
- [ ] Backup empty database for quick reset

---

## SSL/TLS Configuration (20 minutes)

### Option A: Let's Encrypt (Automatic)

- [ ] Install Certbot and run
  ```bash
  certbot certonly --standalone -d yourdomain.com
  cp /etc/letsencrypt/live/yourdomain.com/*.pem docker/ssl/
  ```

### Option B: Manual Certificate

- [ ] Obtain SSL certificate from your CA
- [ ] Place in `docker/ssl/` directory
- [ ] Update Nginx config if needed
- [ ] Enable HTTPS in Nginx

### Verification

- [ ] Test HTTPS connection
- [ ] Check certificate validity period
- [ ] Set up certificate renewal (Let's Encrypt auto-renews)

---

## 📊 Monitoring Setup (30 minutes)

### Required

- [ ] Enable container health checks (configured)
- [ ] Monitor Docker resource usage
- [ ] Setup log collection (stdout/stderr captured)
- [ ] Setup error alerts

### Optional but Recommended

- [ ] Prometheus for metrics
- [ ] Grafana for dashboards
- [ ] ELK stack for log aggregation
- [ ] Datadog or CloudWatch for monitoring
- [ ] Sentry for error tracking

### Alerting

- [ ] CPU > 80% for 5 minutes
- [ ] Memory > 90% for 2 minutes
- [ ] Disk free < 10%
- [ ] API errors > 5% of requests
- [ ] Database connection failures
- [ ] Service restart loops

---

## 💾 Backup & Recovery (20 minutes)

### Setup Automated Backups

- [ ] Configure backup script (already provided)
- [ ] Add to crontab for daily backups
- [ ] Test backup creation
- [ ] Upload backups to S3/cloud storage
- [ ] Keep 30-day retention policy

### Test Disaster Recovery

- [ ] Create test backup
- [ ] Delete some data
- [ ] Restore from backup
- [ ] Verify restored data
- [ ] Document recovery procedure

### Backup Location

- [ ] Local: `/backups/legal_review/`
- [ ] Cloud: S3 bucket or similar
- [ ] Retention: 30 days minimum

---

## 🧪 Pre-Launch Testing (1 hour)

### Backend API Tests

```bash
# Health check
curl http://localhost:8000/health

# Create project
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "description": "Test"}'

# List projects
curl http://localhost:8000/api/projects

# API documentation
curl http://localhost:8000/docs
```

### Frontend Tests

- [ ] Access homepage
- [ ] Create new project
- [ ] Upload test document
- [ ] Verify extraction works
- [ ] Review extracted values
- [ ] Export comparison table
- [ ] Check all UI responsive on mobile

### Integration Tests

- [ ] End-to-end workflow (create → upload → extract → review)
- [ ] Multi-document comparison
- [ ] CSV export
- [ ] Quality evaluation
- [ ] Error handling (bad file, missing fields)

### Load Testing (Optional)

- [ ] 100 concurrent users
- [ ] 1000 requests/second
- [ ] Large file upload (100MB)
- [ ] Monitor response times

---

## 📈 Performance Verification (30 minutes)

- [ ] Backend API responds < 200ms
- [ ] Document parsing < 5 seconds
- [ ] Field extraction < 2 seconds per field
- [ ] Page load time < 3 seconds
- [ ] API endpoint latency < 500ms P95
- [ ] No memory leaks (check after 1 hour)
- [ ] CPU usage < 50% at idle
- [ ] Memory usage < 500MB per service

---

## 🔍 Security Audit (30 minutes)

### Checklist

- [ ] No hardcoded credentials in code
- [ ] Secrets in environment variables only
- [ ] HTTPS enforced (redirect HTTP → HTTPS)
- [ ] CORS restricted to known domains
- [ ] Rate limiting enabled
- [ ] Security headers present (run: `curl -I https://yourdomain.com`)
- [ ] SQL injection prevention (using parameterized queries)
- [ ] XSS protection (React escapes by default)
- [ ] CSRF tokens if needed
- [ ] File upload validation

### Security Headers Check

```bash
curl -I https://yourdomain.com
# Should include:
# X-Content-Type-Options: nosniff
# X-Frame-Options: SAMEORIGIN
# X-XSS-Protection: 1; mode=block
# Content-Security-Policy: ...
# Strict-Transport-Security: max-age=31536000
```

---

## Deployment Phase (30 minutes)

### Option A: Docker Compose on Server

```bash
# 1. SSH to server
ssh deploy@your-server.com

# 2. Copy docker-compose and .env
scp docker-compose.yml deploy@your-server.com:/app/
scp .env.production deploy@your-server.com:/app/.env

# 3. Start services
cd /app
docker-compose up -d

# 4. Verify
docker-compose ps
docker-compose logs -f
```

---

## Post-Deployment Verification (1 hour after launch)

### Immediate Checks

- [ ] All services running (docker ps or kubectl get pods)
- [ ] Health checks passing
- [ ] No error logs in backend/frontend
- [ ] API responding to requests
- [ ] Database connected
- [ ] Frontend loads without errors
- [ ] API documentation accessible

### Functional Verification

- [ ] Create project works
- [ ] Upload document works
- [ ] Extract fields works
- [ ] Review workflow works
- [ ] Comparison table displays
- [ ] Export CSV works
- [ ] All pages load

### Performance Monitoring

- [ ] Monitor CPU/memory usage
- [ ] Check response times
- [ ] Monitor error rates
- [ ] Check request latency P50/P95/P99
- [ ] Monitor disk space
- [ ] Check database connections

### 24-Hour Checks

- [ ] No crash/restart loops
- [ ] Memory stable (no growth)
- [ ] CPU usage normal
- [ ] Database queries performing well
- [ ] All users can access system
- [ ] No error spikes

---

## 🐛 Rollback Plan (Emergency Only)

If issues occur after deployment:

```bash
# Docker Compose: Restore previous version
docker-compose down
git checkout previous_version
docker-compose build
docker-compose up -d

# Kubernetes: Rollback deployment
kubectl rollout undo deployment/backend -n legal-review

# Database: Restore from backup
bash docker/scripts/restore-db.sh backup_YYYYMMDD_HHMMSS.sql.gz
```

---

## 📞 Support Resources

- **Documentation**: See `docker/DOCKER_GUIDE.md`
- **Troubleshooting**: See `docs/TROUBLESHOOTING.md`
- **API Reference**: See `docs/API_REFERENCE.md`
- **Quick Reference**: See `docker/COMMANDS.md`
- **Logs**: `docker-compose logs -f`

---

## ✨ Success Criteria

✅ Your deployment is successful when:

1. ✓ All services running without errors
2. ✓ API responding to requests (http://yourdomain.com/api/health = 200)
3. ✓ Frontend loads (http://yourdomain.com = 200)
4. ✓ Can create a project
5. ✓ Can upload a document
6. ✓ Can extract fields
7. ✓ Can review extractions
8. ✓ Can compare documents
9. ✓ Can export to CSV
10. ✓ No errors in logs after 1 hour of operation

---

**Deployment by**: **\*\*\*\***\_\_\_**\*\*\*\***
**Date**: **\*\*\*\***\_\_\_**\*\*\*\***
**Status**: ☐ Not Started ☐ In Progress ☐ Complete ☐ Verified

**Sign-off**: **\*\*\*\***\_\_\_**\*\*\*\***
