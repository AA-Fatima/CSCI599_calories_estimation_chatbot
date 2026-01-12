# Production Architecture Documentation

## Architecture Overview

This document describes the production-grade architecture implemented for the Arabic Food Calorie Estimation system.

## Key Changes from Original Architecture

### From File-Based to Database-Driven

**Old Architecture (Prototype):**
- ❌ Excel files for dishes storage (`dishes.xlsx`)
- ❌ SQLite for USDA data (`usda.db`)
- ❌ JSON for missing dishes (`missing_dishes.json`)
- ❌ In-memory session storage (Python dict)
- ❌ Manual fuzzy matching with hardcoded synonyms
- ❌ File-based data loading on startup

**New Architecture (Production):**
- ✅ PostgreSQL with pgvector for all data storage
- ✅ Vector embeddings for semantic search
- ✅ Persistent session management
- ✅ Async database operations throughout
- ✅ Repository pattern for clean data access
- ✅ Rate limiting for API protection

## Technology Stack

### Database Layer
- **PostgreSQL 16** with **pgvector** extension
- **SQLAlchemy 2.0** with async support (AsyncSession)
- **asyncpg** driver for optimal performance
- Vector embeddings (384 dimensions) using `all-MiniLM-L6-v2` model

### Backend Services
- **FastAPI** with async endpoints
- **Sentence Transformers** for embeddings (singleton service)
- **OpenAI GPT-4** for dish analysis
- **Loguru** for structured logging
- **SlowAPI** for rate limiting (30 requests/minute)

### Data Migration
- Scripts to migrate from files to PostgreSQL
- Automatic embedding generation for all dishes and foods
- Preserves all existing data

## Database Schema

### Tables

#### 1. `dishes`
Stores all Arabic/Middle Eastern dishes with vector embeddings.

```sql
- id: Primary key
- dish_name: Dish name (indexed)
- dish_name_arabic: Arabic name
- country: Country of origin (indexed)
- ingredients: JSON array of ingredients
- total_calories, total_carbs, total_protein, total_fat: Nutritional totals
- embedding: Vector(384) for semantic search
- created_at, updated_at: Timestamps
```

#### 2. `usda_foods`
USDA food database with vector embeddings.

```sql
- id: Primary key
- fdc_id: USDA FDC ID (unique, indexed)
- description: Food description (indexed)
- description_lower: Lowercase for exact matching
- calories, protein, carbs, fat: Nutrition per 100g
- source: Data source
- embedding: Vector(384) for semantic search
- created_at: Timestamp
```

#### 3. `chat_sessions`
Persistent user sessions.

```sql
- id: Primary key
- session_id: UUID (unique, indexed)
- country: User's selected country
- last_dish: Last discussed dish
- last_dish_ingredients: JSON of last ingredients
- created_at, last_activity: Timestamps
```

#### 4. `conversation_history`
Message history for each session.

```sql
- id: Primary key
- session_id: Foreign key to chat_sessions
- user_message: User's input
- bot_response: Bot's response
- timestamp: Message timestamp
```

#### 5. `missing_dishes`
Tracks dishes not found in database.

```sql
- id: Primary key
- dish_name, dish_name_arabic, country
- query_text: Original query
- gpt_response, ingredients: JSON data
- query_count: How many times requested
- first_queried, last_queried: Timestamps
- status: pending/reviewed/added
```

## Vector Search Implementation

### Country Priority Search

The system implements a two-phase search strategy:

```python
# Phase 1: Search in user's country
result = search_in_country(query_embedding, user_country)
if result:
    return (dish, similarity, is_from_user_country=True)

# Phase 2: Search in all other countries
result = search_excluding_country(query_embedding, user_country)
if result:
    return (dish, similarity, is_from_user_country=False)
```

**Example:** A Lebanese user asking for "koshari" (Egyptian dish):
1. First searches Lebanon dishes
2. Not found, searches all countries
3. Returns Egyptian koshari with note: "This is an Egyptian dish."

### Similarity Threshold

- Default: 0.6 (configurable via `SIMILARITY_THRESHOLD` env var)
- Uses cosine similarity with pgvector's built-in operations
- Efficient with SQL-level vector operations

### Embedding Model

- **Model:** `all-MiniLM-L6-v2`
- **Dimensions:** 384
- **Speed:** ~3000 sentences/second on CPU
- **Quality:** Optimized for semantic similarity
- **Singleton:** Loaded once on first use

## Repository Pattern

Clean separation of concerns with repositories:

### DishesRepository
```python
- search_with_country_priority(query_embedding, user_country)
- get_by_name_and_country(dish_name, country)
- get_all(country, skip, limit)
- get_all_countries()
- create(dish_data)
- update(dish_id, dish_data)
- delete(dish_id)
```

### USDARepository
```python
- search(query_embedding, threshold)
- search_by_text(search_text, limit)
- get_by_fdc_id(fdc_id)
- create(food_data)
- get_count()
```

### SessionsRepository
```python
- create(session_id, country)
- get(session_id)
- update(session_id, last_dish, last_dish_ingredients)
- add_to_history(session_id, user_message, bot_response)
- get_history(session_id, limit)
- get_formatted_history(session_id, limit)
- cleanup_old_sessions(max_age_hours)
```

### MissingDishesRepository
```python
- add_or_update(dish_name, dish_name_arabic, country, ...)
- get_by_name_and_country(dish_name, country)
- get_all(status, country, skip, limit)
- update_status(dish_id, status)
- delete(dish_id)
- get_count(status)
```

## Services Layer

### EmbeddingService (Singleton)
- Lazy loads sentence-transformers model
- Provides `encode()` and `encode_batch()` methods
- Precomputes embeddings efficiently
- Thread-safe singleton pattern

### NutritionService
- Calculates nutritional totals
- Scales nutrition by weight
- Rounds values appropriately

### ChatService
- Orchestrates entire chat flow
- Handles GPT interaction
- Manages fallback search
- Coordinates with repositories

## API Endpoints

### Chat Endpoints
- `POST /api/chat` - Send message (with rate limiting)
- `GET /api/chat/history/{session_id}` - Get conversation history

### Admin Endpoints
- `POST /api/admin/verify` - Verify admin password
- `GET /api/admin/stats` - Dashboard statistics
- `GET /api/admin/missing-dishes` - List missing dishes
- `PUT /api/admin/missing-dishes/{id}/status` - Update status
- `DELETE /api/admin/missing-dishes/{id}` - Delete record
- `GET /api/admin/dishes` - List all dishes
- `GET /api/admin/usda/search` - Search USDA database

### Utility Endpoints
- `GET /api/countries` - List available countries
- `GET /health` - Health check (includes database status)
- `GET /` - API information

## Configuration

### Environment Variables

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nutriarab
DB_USER=postgres
DB_PASSWORD=postgres

# API Keys
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4

# AI Settings
EMBEDDING_MODEL=all-MiniLM-L6-v2
SIMILARITY_THRESHOLD=0.6

# Admin
ADMIN_PASSWORD=your-secure-password

# Environment
ENVIRONMENT=production
DEBUG=False
CORS_ORIGINS=https://yourdomain.com
```

## Data Migration

### Step 1: Initialize Database

```bash
python scripts/init_db.py
```

Creates all tables and enables pgvector extension.

### Step 2: Migrate Existing Data

```bash
python scripts/migrate_data.py
```

Migrates:
- Dishes from `dishes.xlsx` (with embeddings)
- USDA foods from `usda.db` (with embeddings)
- Missing dishes from `missing_dishes.json`

**Note:** Migration script generates embeddings for all items, which may take several minutes for large datasets.

## Deployment with Docker Compose

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]

  backend:
    build: ./backend
    depends_on:
      postgres:
        condition: service_healthy
```

## Rate Limiting

- Default: 30 requests per minute per IP
- Configured with SlowAPI
- Protects against abuse
- Returns 429 Too Many Requests when exceeded

## Async Operations

All database operations are fully async:
- Non-blocking I/O
- Handles concurrent requests efficiently
- Uses `AsyncSession` throughout
- Proper connection pooling

## Logging

Uses Loguru for structured logging:
- INFO: Key operations (searches, matches)
- DEBUG: Detailed flow information
- ERROR: Failures and exceptions
- SUCCESS: Successful operations

## Performance Considerations

1. **Vector Search:** Highly optimized with pgvector
2. **Connection Pooling:** SQLAlchemy handles connections
3. **Batch Embedding:** Processes multiple items at once
4. **Lazy Loading:** Embedding model loaded on first use
5. **Indexing:** Proper indexes on frequently queried fields
6. **Rate Limiting:** Prevents resource exhaustion

## Security Features

1. **Admin Authentication:** Password-based with constant-time comparison
2. **CORS Configuration:** Restrict allowed origins
3. **Rate Limiting:** Prevent abuse
4. **SQL Injection Protection:** SQLAlchemy parameterized queries
5. **Environment Variables:** Secrets not in code

## Monitoring & Health Checks

Health endpoint (`/health`) returns:
- Application status
- Database connectivity
- Version information

Response:
```json
{
  "status": "healthy",
  "database": "healthy",
  "version": "2.0.0"
}
```

## Backward Compatibility

The old file-based handlers are preserved for reference:
- `app/data/dishes_handler.py`
- `app/data/usda_handler.py`
- `app/services/session_manager.py`
- `app/services/missing_dish_service.py`

These are NOT used in production but kept for migration reference.

## Future Enhancements

- [ ] Add caching layer (Redis)
- [ ] Implement full-text search
- [ ] Add analytics and metrics
- [ ] Implement background task processing
- [ ] Add database read replicas
- [ ] Implement backup automation

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose ps

# Check logs
docker-compose logs postgres

# Test connection
psql -h localhost -U postgres -d nutriarab
```

### Migration Issues
```bash
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d postgres
python scripts/init_db.py
python scripts/migrate_data.py
```

### Embedding Model Issues
```bash
# Model downloads on first use to ~/.cache/huggingface/
# Ensure sufficient disk space (~100MB)
```

## Support

For issues or questions, please refer to the main README or contact the development team.
