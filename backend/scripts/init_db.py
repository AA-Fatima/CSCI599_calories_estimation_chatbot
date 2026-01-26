#!/usr/bin/env python3
"""Initialize database - create all tables and extensions."""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from app.database import init_db, engine


async def main():
    """Initialize database."""
    logger.info("Starting database initialization...")
    
    try:
        # Initialize database
        await init_db()
        logger.success("Database initialized successfully!")
        logger.info("Tables created:")
        logger.info("  - dishes (with vector embeddings)")
        logger.info("  - usda_foods (with vector embeddings)")
        logger.info("  - chat_sessions")
        logger.info("  - conversation_history")
        logger.info("  - missing_dishes")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        # Close engine
        from app.database import close_db
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
