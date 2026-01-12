#!/usr/bin/env python3
"""Migrate existing data from files to PostgreSQL."""
import asyncio
import sys
import json
import sqlite3
from pathlib import Path
from typing import List, Dict

import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal, init_db, close_db
from app.models.database import Dish, USDAFood, MissingDish
from app.services.embedding import embedding_service
from app.config import settings


class DataMigrator:
    """Handles data migration from files to database."""
    
    def __init__(self):
        """Initialize migrator."""
        self.dishes_path = Path(settings.dishes_path)
        self.usda_db_path = Path(settings.usda_db_path)
        self.missing_dishes_path = Path(settings.missing_dishes_path)
    
    async def migrate_dishes(self, db: AsyncSession) -> int:
        """
        Migrate dishes from Excel to PostgreSQL.
        
        Args:
            db: Database session
            
        Returns:
            Number of dishes migrated
        """
        logger.info("Migrating dishes from Excel...")
        
        if not self.dishes_path.exists():
            logger.warning(f"Dishes file not found: {self.dishes_path}")
            return 0
        
        # Read Excel file
        df = pd.read_excel(self.dishes_path, sheet_name='dishes')
        logger.info(f"Found {len(df)} dishes in Excel")
        
        # Get dish names for batch embedding
        dish_names = []
        for _, row in df.iterrows():
            name = str(row.get('dish_name') or row.get('dish name') or row.get('Dish Name') or '').strip()
            if name:
                dish_names.append(name.lower())
        
        # Generate embeddings in batch
        logger.info("Generating embeddings for all dishes...")
        embeddings = embedding_service.encode_batch(dish_names, batch_size=32)
        
        # Insert dishes
        count = 0
        for idx, (_, row) in enumerate(df.iterrows()):
            try:
                dish_name = str(row.get('dish_name') or row.get('dish name') or row.get('Dish Name') or '').strip()
                if not dish_name:
                    continue
                
                country = str(row.get('country') or row.get('Country') or '').strip()
                dish_name_arabic = str(row.get('dish_name_arabic') or row.get('dish name arabic') or '').strip() or None
                
                # Parse ingredients
                ingredients_json = row.get('ingredients', '[]')
                if isinstance(ingredients_json, str):
                    try:
                        ingredients = json.loads(ingredients_json)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse ingredients for {dish_name}")
                        ingredients = []
                else:
                    ingredients = ingredients_json if isinstance(ingredients_json, list) else []
                
                # Calculate totals
                total_calories = sum(float(ing.get('calories', 0)) for ing in ingredients)
                total_carbs = sum(float(ing.get('carbs', 0)) for ing in ingredients)
                total_protein = sum(float(ing.get('protein', 0)) for ing in ingredients)
                total_fat = sum(float(ing.get('fat', 0)) for ing in ingredients)
                
                # Create dish
                dish = Dish(
                    dish_name=dish_name,
                    dish_name_arabic=dish_name_arabic,
                    country=country,
                    ingredients=ingredients,
                    total_calories=total_calories,
                    total_carbs=total_carbs,
                    total_protein=total_protein,
                    total_fat=total_fat,
                    embedding=embeddings[idx] if idx < len(embeddings) else None
                )
                
                db.add(dish)
                count += 1
                
                if count % 50 == 0:
                    await db.flush()
                    logger.info(f"Migrated {count} dishes...")
                
            except Exception as e:
                logger.error(f"Error migrating dish {idx}: {e}")
                continue
        
        await db.commit()
        logger.success(f"Successfully migrated {count} dishes")
        return count
    
    async def migrate_usda_foods(self, db: AsyncSession) -> int:
        """
        Migrate USDA foods from SQLite to PostgreSQL.
        
        Args:
            db: Database session
            
        Returns:
            Number of foods migrated
        """
        logger.info("Migrating USDA foods from SQLite...")
        
        if not self.usda_db_path.exists():
            logger.warning(f"USDA database not found: {self.usda_db_path}")
            return 0
        
        # Connect to SQLite
        conn = sqlite3.connect(self.usda_db_path)
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute('SELECT COUNT(*) FROM foods')
        total = cursor.fetchone()[0]
        logger.info(f"Found {total} foods in SQLite")
        
        # Read all foods
        cursor.execute('SELECT * FROM foods')
        rows = cursor.fetchall()
        conn.close()
        
        # Get descriptions for batch embedding
        descriptions = [row[2].lower() for row in rows]  # description column
        
        # Generate embeddings in batch
        logger.info("Generating embeddings for all USDA foods...")
        embeddings = embedding_service.encode_batch(descriptions, batch_size=64)
        
        # Insert foods
        count = 0
        for idx, row in enumerate(rows):
            try:
                food = USDAFood(
                    fdc_id=row[1],
                    description=row[2],
                    description_lower=row[3],
                    calories=float(row[4]),
                    protein=float(row[5]),
                    carbs=float(row[6]),
                    fat=float(row[7]),
                    source=row[8],
                    embedding=embeddings[idx] if idx < len(embeddings) else None
                )
                
                db.add(food)
                count += 1
                
                if count % 500 == 0:
                    await db.flush()
                    logger.info(f"Migrated {count}/{total} USDA foods...")
                
            except Exception as e:
                logger.error(f"Error migrating food {idx}: {e}")
                continue
        
        await db.commit()
        logger.success(f"Successfully migrated {count} USDA foods")
        return count
    
    async def migrate_missing_dishes(self, db: AsyncSession) -> int:
        """
        Migrate missing dishes from JSON to PostgreSQL.
        
        Args:
            db: Database session
            
        Returns:
            Number of missing dishes migrated
        """
        logger.info("Migrating missing dishes from JSON...")
        
        if not self.missing_dishes_path.exists():
            logger.warning(f"Missing dishes file not found: {self.missing_dishes_path}")
            return 0
        
        # Read JSON file
        with open(self.missing_dishes_path, 'r', encoding='utf-8') as f:
            missing_dishes_data = json.load(f)
        
        logger.info(f"Found {len(missing_dishes_data)} missing dishes in JSON")
        
        # Insert missing dishes
        count = 0
        for item in missing_dishes_data:
            try:
                missing_dish = MissingDish(
                    dish_name=item['dish_name'],
                    dish_name_arabic=item.get('dish_name_arabic'),
                    country=item['country'],
                    query_text=item['query_text'],
                    gpt_response=item.get('gpt_response'),
                    ingredients=item.get('ingredients'),
                    query_count=item.get('query_count', 1),
                    first_queried=item.get('first_queried'),
                    last_queried=item.get('last_queried'),
                    status='pending'
                )
                
                db.add(missing_dish)
                count += 1
                
            except Exception as e:
                logger.error(f"Error migrating missing dish: {e}")
                continue
        
        await db.commit()
        logger.success(f"Successfully migrated {count} missing dishes")
        return count


async def main():
    """Main migration function."""
    logger.info("="*60)
    logger.info("Starting data migration from files to PostgreSQL")
    logger.info("="*60)
    
    # Initialize database first
    logger.info("\nStep 1: Initializing database...")
    await init_db()
    logger.success("Database initialized")
    
    # Create migrator
    migrator = DataMigrator()
    
    # Migrate data
    async with AsyncSessionLocal() as db:
        try:
            # Migrate dishes
            logger.info("\nStep 2: Migrating dishes...")
            dishes_count = await migrator.migrate_dishes(db)
            
            # Migrate USDA foods
            logger.info("\nStep 3: Migrating USDA foods...")
            usda_count = await migrator.migrate_usda_foods(db)
            
            # Migrate missing dishes
            logger.info("\nStep 4: Migrating missing dishes...")
            missing_count = await migrator.migrate_missing_dishes(db)
            
            # Summary
            logger.info("\n" + "="*60)
            logger.success("Migration completed successfully!")
            logger.info("="*60)
            logger.info(f"Dishes migrated: {dishes_count}")
            logger.info(f"USDA foods migrated: {usda_count}")
            logger.info(f"Missing dishes migrated: {missing_count}")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            await db.close()
    
    # Close database
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
