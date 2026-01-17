"""Create vector indexes for optimal search performance."""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine
from loguru import logger


async def create_vector_indexes():
    """Create vector indexes for dishes and USDA foods."""
    logger.info("Creating vector indexes for optimal search performance...")
    
    async with engine.connect() as conn:
        # Enable pgvector extension if not already enabled
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.commit()
        logger.info("✓ pgvector extension enabled")
        
        # Create vector index for dishes
        try:
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_dishes_embedding 
                ON dishes 
                USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = 100)
            """))
            await conn.commit()
            logger.success("✓ Created vector index for dishes")
        except Exception as e:
            logger.warning(f"Could not create dishes vector index: {e}")
            logger.info("This is OK if index already exists or table is empty")
        
        # Create vector index for USDA foods
        try:
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_usda_embedding 
                ON usda_foods 
                USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = 100)
            """))
            await conn.commit()
            logger.success("✓ Created vector index for USDA foods")
        except Exception as e:
            logger.warning(f"Could not create USDA vector index: {e}")
            logger.info("This is OK if index already exists or table is empty")
        
        # Enable pg_trgm for fuzzy text search
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await conn.commit()
            logger.success("✓ pg_trgm extension enabled")
        except Exception as e:
            logger.warning(f"Could not enable pg_trgm: {e}")
            logger.info("This is OK - text search will still work")
        
        logger.info("="*60)
        logger.success("Vector indexes creation completed!")
        logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(create_vector_indexes())
