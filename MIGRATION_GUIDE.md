# Migration Guide: From Prototype to Production

This guide walks you through migrating the Arabic Food Calorie Estimation system from file-based storage to production-grade PostgreSQL with vector search.

## Prerequisites

- Docker and Docker Compose installed
- At least 2GB free disk space
- Python 3.9+ (for running migration scripts)
- Existing data files in `backend/data/`:
  - `dishes.xlsx`
  - `usda.db`
  - `missing_dishes.json`

## Migration Steps

### Step 1: Update Environment Configuration

Create or update your `.env` file in the `backend/` directory:

```bash
# Copy from example
cp backend/.env.example backend/.env

# Edit with your values
nano backend/.env
```

Required settings:
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nutriarab
DB_USER=postgres
DB_PASSWORD=postgres

# API Keys
OPENAI_API_KEY=your-openai-key-here

# AI Settings
EMBEDDING_MODEL=all-MiniLM-L6-v2
SIMILARITY_THRESHOLD=0.6

# Admin
ADMIN_PASSWORD=your-secure-admin-password
```

### Step 2: Start PostgreSQL

Using Docker Compose (recommended):

```bash
# Start only PostgreSQL
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
docker-compose ps
# Should show postgres as "healthy"

# Check logs if needed
docker-compose logs postgres
```

### Step 3: Initialize Database

This creates all tables and enables pgvector extension:

```bash
cd backend

# Install dependencies if not already installed
pip install -r requirements.txt

# Run initialization
python scripts/init_db.py
```

Expected output:
```
Starting database initialization...
Database initialized successfully!
Tables created:
  - dishes (with vector embeddings)
  - usda_foods (with vector embeddings)
  - chat_sessions
  - conversation_history
  - missing_dishes
```

### Step 4: Migrate Data

This imports all existing data and generates embeddings:

```bash
# Still in backend directory
python scripts/migrate_data.py
```

This process will:
1. Read dishes from `dishes.xlsx`
2. Generate embeddings for all dish names
3. Import dishes to PostgreSQL
4. Read USDA foods from `usda.db`
5. Generate embeddings for all food descriptions
6. Import USDA foods to PostgreSQL
7. Import missing dishes from `missing_dishes.json`

**Note:** This may take 5-15 minutes depending on dataset size and CPU speed.

Expected output:
```
Starting data migration from files to PostgreSQL
============================================================

Step 1: Initializing database...
Database initialized

Step 2: Migrating dishes...
Found 150 dishes in Excel
Generating embeddings for all dishes...
Migrated 50 dishes...
Migrated 100 dishes...
Migrated 150 dishes...
Successfully migrated 150 dishes

Step 3: Migrating USDA foods...
Found 8789 foods in SQLite
Generating embeddings for all USDA foods...
Migrated 500/8789 USDA foods...
Migrated 1000/8789 USDA foods...
...
Successfully migrated 8789 USDA foods

Step 4: Migrating missing dishes...
Found 45 missing dishes in JSON
Successfully migrated 45 missing dishes

============================================================
Migration completed successfully!
============================================================
Dishes migrated: 150
USDA foods migrated: 8789
Missing dishes migrated: 45
============================================================
```

### Step 5: Verify Migration

Check database contents:

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d nutriarab

# Run queries to verify
SELECT COUNT(*) FROM dishes;
SELECT COUNT(*) FROM usda_foods;
SELECT COUNT(*) FROM missing_dishes;

# Check a sample dish
SELECT dish_name, country, total_calories 
FROM dishes 
LIMIT 5;

# Exit
\q
```

### Step 6: Start the Application

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Wait for "Application startup complete"
```

### Step 7: Test the API

```bash
# Health check
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","database":"healthy","version":"2.0.0"}

# Test countries endpoint
curl http://localhost:8000/api/countries

# Test chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "calories in hummus",
    "country": "Lebanon"
  }'
```

## Rollback Procedure

If you need to rollback to the file-based system:

### Option 1: Keep Both Systems

The old file-based handlers are still in the codebase:
- `app/data/dishes_handler.py`
- `app/data/usda_handler.py`
- `app/services/session_manager.py`
- `app/services/missing_dish_service.py`

To use them, temporarily revert:
1. Change `chat.py` to import `chat_service` instead of `chat_service_new`
2. Change `main.py` to import `admin` instead of `admin_new`
3. Change `main.py` lifespan to call `load_all_data()` instead of `init_db()`

### Option 2: Fresh Start

```bash
# Stop everything
docker-compose down -v

# Remove database volume
docker volume rm CSCI599_calories_estimation_chatbot_postgres_data

# Start without database
docker-compose up backend frontend
```

## Troubleshooting

### Database Connection Failed

```bash
# Check if PostgreSQL is running
docker-compose ps

# Check PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Migration Script Fails

**Error: "No such file 'dishes.xlsx'"**
- Ensure `backend/data/dishes.xlsx` exists
- Check file path in `backend/app/config.py`

**Error: "Out of memory"**
- Reduce batch size in `migrate_data.py`
- Process in smaller chunks
- Use a machine with more RAM

**Error: "Embedding model download failed"**
- Check internet connection
- Model downloads to `~/.cache/huggingface/`
- Ensure sufficient disk space (~100MB)

### Slow Embedding Generation

If embedding generation is too slow:

1. **Use GPU** (if available):
```python
# In embedding service
SentenceTransformer(model_name, device='cuda')
```

2. **Reduce batch size**:
```python
# In migrate_data.py
embeddings = embedding_service.encode_batch(texts, batch_size=16)
```

3. **Pre-download model**:
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Vector Search Not Working

```bash
# Verify pgvector extension is installed
docker-compose exec postgres psql -U postgres -d nutriarab -c "SELECT * FROM pg_extension WHERE extname='vector';"

# If not installed, install manually:
docker-compose exec postgres psql -U postgres -d nutriarab -c "CREATE EXTENSION vector;"
```

### Admin Panel Shows No Data

1. Check database connection in health endpoint
2. Verify data was migrated (see Step 5)
3. Check admin authentication is working
4. Check browser console for errors

## Performance Optimization

### For Production Deployment

1. **Enable connection pooling** (already configured in `database.py`)

2. **Add indexes** (already done in models):
   - Dish names
   - Countries
   - FDC IDs

3. **Tune PostgreSQL**:
```sql
-- In PostgreSQL config
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
```

4. **Monitor query performance**:
```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();
```

5. **Add Redis caching** (future enhancement):
   - Cache frequently requested dishes
   - Cache vector search results
   - Cache session data

## Backup and Restore

### Backup Database

```bash
# Full backup
docker-compose exec postgres pg_dump -U postgres nutriarab > backup_$(date +%Y%m%d).sql

# Backup with compression
docker-compose exec postgres pg_dump -U postgres nutriarab | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore Database

```bash
# From SQL file
docker-compose exec -T postgres psql -U postgres nutriarab < backup_20240112.sql

# From compressed file
gunzip -c backup_20240112.sql.gz | docker-compose exec -T postgres psql -U postgres nutriarab
```

## Post-Migration Checklist

- [ ] Database health check returns "healthy"
- [ ] All API endpoints respond correctly
- [ ] Chat functionality works with vector search
- [ ] Country priority search works correctly
- [ ] Admin panel accessible
- [ ] Missing dishes are tracked
- [ ] Sessions persist across server restarts
- [ ] Rate limiting is active
- [ ] Logs show no errors
- [ ] Old file-based data files backed up
- [ ] Environment variables properly set
- [ ] Database backups configured

## Next Steps

After successful migration:

1. **Monitor Performance**
   - Watch database query times
   - Monitor memory usage
   - Check vector search accuracy

2. **Optimize Similarity Threshold**
   - Test with various queries
   - Adjust `SIMILARITY_THRESHOLD` as needed
   - Current default: 0.6

3. **Add New Dishes**
   - Use admin panel to add dishes
   - Embeddings generated automatically
   - Country priority search works immediately

4. **Setup Automated Backups**
   - Daily database dumps
   - Store in separate location
   - Test restore procedure

5. **Consider Additional Enhancements**
   - Add Redis for caching
   - Implement full-text search
   - Add analytics and metrics
   - Setup monitoring (Prometheus/Grafana)

## Support

For issues during migration:
1. Check this guide's Troubleshooting section
2. Review `ARCHITECTURE.md` for technical details
3. Check application logs: `docker-compose logs backend`
4. Check database logs: `docker-compose logs postgres`

## Migration Checklist Summary

Before migration:
- [ ] Backup all data files
- [ ] Install prerequisites
- [ ] Review system requirements

During migration:
- [ ] Configure environment variables
- [ ] Start PostgreSQL
- [ ] Initialize database
- [ ] Run migration script
- [ ] Verify data imported correctly

After migration:
- [ ] Test all API endpoints
- [ ] Verify vector search works
- [ ] Check admin panel functions
- [ ] Test chat functionality
- [ ] Setup backups
- [ ] Monitor performance

Good luck with your migration! 🚀
