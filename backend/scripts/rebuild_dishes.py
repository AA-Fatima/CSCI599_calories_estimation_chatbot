#!/usr/bin/env python3
"""Rebuild dishes table from Excel file - updates existing and adds new dishes."""
import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import AsyncSessionLocal, init_db, close_db
from app.models.database import Dish
from app.services.embedding import embedding_service
from app.config import settings


class DishesRebuilder:
    """Rebuild dishes table from Excel file."""
    
    def __init__(self):
        """Initialize rebuilder."""
        # Use BASE_DIR from config
        from app.config import BASE_DIR
        self.dishes_path = BASE_DIR / "data" / "dishes.xlsx"
    
    async def get_existing_dishes(self, db: AsyncSession) -> Dict[str, Dish]:
        """
        Get existing dishes from database keyed by (dish_name, country).
        
        Args:
            db: Database session
            
        Returns:
            Dictionary mapping (dish_name_lower, country_lower) -> Dish
        """
        query = select(Dish)
        result = await db.execute(query)
        dishes = result.scalars().all()
        
        existing = {}
        for dish in dishes:
            key = (dish.dish_name.lower().strip(), dish.country.lower().strip())
            existing[key] = dish
        
        logger.info(f"Found {len(existing)} existing dishes in database")
        return existing
    
    async def rebuild_dishes(self, db: AsyncSession, clear_existing: bool = False) -> Dict[str, int]:
        """
        Rebuild dishes from Excel file.
        
        Args:
            db: Database session
            clear_existing: If True, delete all existing dishes first
            
        Returns:
            Dictionary with counts: {'inserted': X, 'updated': Y, 'skipped': Z}
        """
        logger.info("="*60)
        logger.info("REBUILDING DISHES FROM EXCEL")
        logger.info("="*60)
        
        if not self.dishes_path.exists():
            logger.error(f"Dishes file not found: {self.dishes_path}")
            return {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        
        # Clear existing if requested
        if clear_existing:
            logger.warning("Clearing all existing dishes...")
            await db.execute(select(Dish).delete())
            await db.commit()
            logger.info("All existing dishes cleared")
        
        # Read Excel file
        try:
            df = pd.read_excel(self.dishes_path, sheet_name='dishes')
            logger.info(f"Found {len(df)} dishes in Excel file")
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            return {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 1}
        
        # Get existing dishes (if not cleared)
        existing_dishes = {} if clear_existing else await self.get_existing_dishes(db)
        
        # Prepare dish data
        dishes_data = []
        for idx, row in df.iterrows():
            try:
                dish_name = str(row.get('dish_name') or row.get('dish name') or row.get('Dish Name') or '').strip()
                if not dish_name:
                    logger.warning(f"Row {idx + 1}: Missing dish name, skipping")
                    continue
                
                country = str(row.get('country') or row.get('Country') or '').strip()
                if not country:
                    logger.warning(f"Row {idx + 1} ({dish_name}): Missing country, skipping")
                    continue
                
                dish_name_arabic = str(row.get('dish_name_arabic') or row.get('dish name arabic') or '').strip() or None
                
                # Parse ingredients
                ingredients_json = row.get('ingredients', '[]')
                if isinstance(ingredients_json, str):
                    try:
                        ingredients = json.loads(ingredients_json)
                    except json.JSONDecodeError:
                        logger.warning(f"Row {idx + 1} ({dish_name}): Failed to parse ingredients JSON")
                        ingredients = []
                else:
                    ingredients = ingredients_json if isinstance(ingredients_json, list) else []
                
                # Calculate totals
                total_calories = sum(float(ing.get('calories', 0)) for ing in ingredients)
                total_carbs = sum(float(ing.get('carbs', 0)) for ing in ingredients)
                total_protein = sum(float(ing.get('protein', 0)) for ing in ingredients)
                total_fat = sum(float(ing.get('fat', 0)) for ing in ingredients)
                
                dishes_data.append({
                    'dish_name': dish_name,
                    'dish_name_arabic': dish_name_arabic,
                    'country': country,
                    'ingredients': ingredients,
                    'total_calories': total_calories,
                    'total_carbs': total_carbs,
                    'total_protein': total_protein,
                    'total_fat': total_fat,
                    'row_idx': idx
                })
                
            except Exception as e:
                logger.error(f"Error processing row {idx + 1}: {e}")
                continue
        
        logger.info(f"Prepared {len(dishes_data)} dishes for processing")
        
        # Generate embeddings in batch
        logger.info("Generating embeddings for all dishes...")
        dish_names = [d['dish_name'].lower() for d in dishes_data]
        batch_size = settings.migration_batch_size
        embeddings = embedding_service.encode_batch(dish_names, batch_size=batch_size)
        
        # Process dishes
        counts = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        
        for idx, dish_data in enumerate(dishes_data):
            try:
                dish_name = dish_data['dish_name']
                country = dish_data['country']
                key = (dish_name.lower().strip(), country.lower().strip())
                
                # Check if dish exists
                existing_dish = existing_dishes.get(key)
                
                if existing_dish:
                    # Update existing dish
                    existing_dish.dish_name = dish_data['dish_name']
                    existing_dish.dish_name_arabic = dish_data['dish_name_arabic']
                    existing_dish.country = dish_data['country']
                    existing_dish.ingredients = dish_data['ingredients']
                    existing_dish.total_calories = dish_data['total_calories']
                    existing_dish.total_carbs = dish_data['total_carbs']
                    existing_dish.total_protein = dish_data['total_protein']
                    existing_dish.total_fat = dish_data['total_fat']
                    existing_dish.embedding = embeddings[idx] if idx < len(embeddings) else None
                    
                    counts['updated'] += 1
                    if counts['updated'] % 50 == 0:
                        await db.flush()
                        logger.info(f"Updated {counts['updated']} dishes...")
                else:
                    # Insert new dish
                    dish = Dish(
                        dish_name=dish_data['dish_name'],
                        dish_name_arabic=dish_data['dish_name_arabic'],
                        country=dish_data['country'],
                        ingredients=dish_data['ingredients'],
                        total_calories=dish_data['total_calories'],
                        total_carbs=dish_data['total_carbs'],
                        total_protein=dish_data['total_protein'],
                        total_fat=dish_data['total_fat'],
                        embedding=embeddings[idx] if idx < len(embeddings) else None
                    )
                    
                    db.add(dish)
                    counts['inserted'] += 1
                    if counts['inserted'] % 50 == 0:
                        await db.flush()
                        logger.info(f"Inserted {counts['inserted']} dishes...")
                
            except Exception as e:
                logger.error(f"Error processing dish '{dish_data.get('dish_name', 'unknown')}': {e}")
                counts['errors'] += 1
                continue
        
        # Commit all changes
        await db.commit()
        
        logger.success("="*60)
        logger.success("DISHES REBUILD COMPLETED!")
        logger.success("="*60)
        logger.info(f"Inserted: {counts['inserted']} new dishes")
        logger.info(f"Updated: {counts['updated']} existing dishes")
        logger.info(f"Skipped: {counts['skipped']} dishes")
        if counts['errors'] > 0:
            logger.warning(f"Errors: {counts['errors']} dishes")
        logger.info("="*60)
        
        return counts


async def main():
    """Main rebuild function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Rebuild dishes table from Excel')
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear all existing dishes before rebuilding (default: update existing)'
    )
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("DISHES REBUILD TOOL")
    logger.info("="*60)
    
    if args.clear:
        logger.warning("⚠️  WARNING: Will delete all existing dishes!")
        response = input("Are you sure? Type 'yes' to continue: ")
        if response.lower() != 'yes':
            logger.info("Cancelled.")
            return
    
    # Initialize database
    logger.info("\nStep 1: Initializing database...")
    await init_db()
    logger.success("Database initialized")
    
    # Rebuild dishes
    rebuilder = DishesRebuilder()
    async with AsyncSessionLocal() as db:
        try:
            logger.info("\nStep 2: Rebuilding dishes...")
            counts = await rebuilder.rebuild_dishes(db, clear_existing=args.clear)
            
            # Verify
            query = select(func.count(Dish.id))
            result = await db.execute(query)
            total = result.scalar()
            logger.info(f"\nTotal dishes in database: {total}")
            
        except Exception as e:
            logger.error(f"Rebuild failed: {e}")
            raise
        finally:
            await db.close()
    
    # Close database
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
