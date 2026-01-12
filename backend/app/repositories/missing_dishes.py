"""Missing dishes repository for tracking dishes not in dataset."""
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.models.database import MissingDish


class MissingDishesRepository:
    """Repository for missing dishes."""
    
    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db
    
    async def add_or_update(
        self,
        dish_name: str,
        dish_name_arabic: Optional[str],
        country: str,
        query_text: str,
        gpt_response: Optional[Dict],
        ingredients: Optional[List[Dict]]
    ) -> MissingDish:
        """
        Add or update missing dish record.
        
        Args:
            dish_name: Name of the dish
            dish_name_arabic: Arabic name
            country: Country variant
            query_text: Original user query
            gpt_response: GPT's response dictionary
            ingredients: GPT's suggested ingredients
            
        Returns:
            Created or updated missing dish
        """
        # Check if dish already exists
        existing = await self.get_by_name_and_country(dish_name, country)
        
        if existing:
            # Update existing record
            existing.query_count += 1
            existing.last_queried = datetime.utcnow()
            existing.query_text = query_text  # Update with latest query
            if gpt_response:
                existing.gpt_response = gpt_response
            if ingredients:
                existing.ingredients = ingredients
            await self.db.flush()
            logger.info(f"Updated missing dish: {dish_name} ({country}) - count: {existing.query_count}")
            return existing
        else:
            # Create new record
            missing_dish = MissingDish(
                dish_name=dish_name,
                dish_name_arabic=dish_name_arabic,
                country=country,
                query_text=query_text,
                gpt_response=gpt_response,
                ingredients=ingredients,
                query_count=1,
                first_queried=datetime.utcnow(),
                last_queried=datetime.utcnow(),
                status="pending"
            )
            self.db.add(missing_dish)
            await self.db.flush()
            logger.info(f"Added new missing dish: {dish_name} ({country})")
            return missing_dish
    
    async def get_by_name_and_country(
        self,
        dish_name: str,
        country: str
    ) -> Optional[MissingDish]:
        """
        Get missing dish by name and country.
        
        Args:
            dish_name: Dish name
            country: Country
            
        Returns:
            MissingDish or None
        """
        query = select(MissingDish).where(
            func.lower(MissingDish.dish_name) == dish_name.lower(),
            func.lower(MissingDish.country) == country.lower()
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        status: Optional[str] = None,
        country: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[MissingDish]:
        """
        Get all missing dishes with optional filters.
        
        Args:
            status: Filter by status (pending, reviewed, added)
            country: Filter by country
            skip: Offset for pagination
            limit: Limit for pagination
            
        Returns:
            List of missing dishes
        """
        query = select(MissingDish)
        
        if status:
            query = query.where(MissingDish.status == status)
        if country:
            query = query.where(func.lower(MissingDish.country) == country.lower())
        
        query = query.order_by(
            MissingDish.query_count.desc(),
            MissingDish.last_queried.desc()
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_status(
        self,
        dish_id: int,
        status: str
    ) -> Optional[MissingDish]:
        """
        Update status of a missing dish.
        
        Args:
            dish_id: Dish ID
            status: New status (pending, reviewed, added)
            
        Returns:
            Updated dish or None
        """
        query = select(MissingDish).where(MissingDish.id == dish_id)
        result = await self.db.execute(query)
        dish = result.scalar_one_or_none()
        
        if dish:
            dish.status = status
            await self.db.flush()
            logger.info(f"Updated missing dish status: {dish.dish_name} -> {status}")
        
        return dish
    
    async def delete(self, dish_id: int) -> bool:
        """
        Delete a missing dish record.
        
        Args:
            dish_id: Dish ID
            
        Returns:
            True if deleted, False if not found
        """
        query = select(MissingDish).where(MissingDish.id == dish_id)
        result = await self.db.execute(query)
        dish = result.scalar_one_or_none()
        
        if dish:
            await self.db.delete(dish)
            await self.db.flush()
            logger.info(f"Deleted missing dish: {dish.dish_name}")
            return True
        
        return False
    
    async def get_count(self, status: Optional[str] = None) -> int:
        """
        Get count of missing dishes.
        
        Args:
            status: Optional status filter
            
        Returns:
            Count of missing dishes
        """
        query = select(func.count(MissingDish.id))
        
        if status:
            query = query.where(MissingDish.status == status)
        
        result = await self.db.execute(query)
        return result.scalar()
