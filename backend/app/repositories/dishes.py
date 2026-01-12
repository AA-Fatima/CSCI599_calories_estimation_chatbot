"""Dishes repository with vector search and country priority."""
from typing import Optional, Tuple, List, Dict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.models.database import Dish
from app.config import settings


class DishesRepository:
    """Repository for dishes with semantic search."""
    
    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db
    
    async def search_with_country_priority(
        self,
        query_embedding: List[float],
        user_country: str,
        threshold: float = None,
    ) -> Optional[Tuple[Dish, float, bool]]:
        """
        Search for dish with country prioritization.
        
        Args:
            query_embedding: Query vector embedding
            user_country: User's country for priority search
            threshold: Similarity threshold (default from config)
            
        Returns:
            Tuple of (dish, similarity_score, is_from_user_country) or None
        """
        if threshold is None:
            threshold = settings.similarity_threshold
        
        logger.info(f"Searching dishes with country priority: {user_country}")
        
        # Phase 1: Search in user's country
        result = await self._vector_search(
            query_embedding,
            country=user_country,
            threshold=threshold
        )
        
        if result:
            dish, similarity = result
            logger.info(f"Found in user's country: {dish.dish_name} (similarity: {similarity:.3f})")
            return dish, similarity, True
        
        # Phase 2: Search in all other countries
        logger.info(f"Not found in {user_country}, searching all countries...")
        result = await self._vector_search(
            query_embedding,
            exclude_country=user_country,
            threshold=threshold
        )
        
        if result:
            dish, similarity = result
            logger.info(f"Found in {dish.country}: {dish.dish_name} (similarity: {similarity:.3f})")
            return dish, similarity, False
        
        logger.info("No match found in any country")
        return None
    
    async def _vector_search(
        self,
        query_embedding: List[float],
        country: Optional[str] = None,
        exclude_country: Optional[str] = None,
        threshold: float = None,
        limit: int = 1
    ) -> Optional[Tuple[Dish, float]]:
        """
        Internal vector search implementation.
        
        Args:
            query_embedding: Query vector
            country: Filter by specific country
            exclude_country: Exclude specific country
            threshold: Similarity threshold
            limit: Number of results to return
            
        Returns:
            Tuple of (dish, similarity_score) or None
        """
        if threshold is None:
            threshold = settings.similarity_threshold
        
        # Build query with vector similarity
        query = select(
            Dish,
            (1 - Dish.embedding.cosine_distance(query_embedding)).label('similarity')
        )
        
        # Apply country filters
        if country:
            query = query.where(func.lower(Dish.country) == country.lower())
        if exclude_country:
            query = query.where(func.lower(Dish.country) != exclude_country.lower())
        
        # Filter by similarity threshold and order
        query = query.where(
            (1 - Dish.embedding.cosine_distance(query_embedding)) >= threshold
        ).order_by(
            (1 - Dish.embedding.cosine_distance(query_embedding)).desc()
        ).limit(limit)
        
        result = await self.db.execute(query)
        row = result.first()
        
        if row:
            dish, similarity = row
            return dish, float(similarity)
        
        return None
    
    async def get_by_name_and_country(
        self,
        dish_name: str,
        country: str
    ) -> Optional[Dish]:
        """
        Get dish by exact name and country match.
        
        Args:
            dish_name: Dish name
            country: Country
            
        Returns:
            Dish or None
        """
        query = select(Dish).where(
            func.lower(Dish.dish_name) == dish_name.lower(),
            func.lower(Dish.country) == country.lower()
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        country: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dish]:
        """
        Get all dishes, optionally filtered by country.
        
        Args:
            country: Optional country filter
            skip: Offset for pagination
            limit: Limit for pagination
            
        Returns:
            List of dishes
        """
        query = select(Dish)
        
        if country:
            query = query.where(func.lower(Dish.country) == country.lower())
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_all_countries(self) -> List[str]:
        """
        Get list of all unique countries.
        
        Returns:
            List of country names
        """
        query = select(Dish.country).distinct().order_by(Dish.country)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, dish_data: Dict) -> Dish:
        """
        Create a new dish.
        
        Args:
            dish_data: Dish data dictionary
            
        Returns:
            Created dish
        """
        dish = Dish(**dish_data)
        self.db.add(dish)
        await self.db.flush()
        return dish
    
    async def update(self, dish_id: int, dish_data: Dict) -> Optional[Dish]:
        """
        Update an existing dish.
        
        Args:
            dish_id: Dish ID
            dish_data: Updated dish data
            
        Returns:
            Updated dish or None
        """
        query = select(Dish).where(Dish.id == dish_id)
        result = await self.db.execute(query)
        dish = result.scalar_one_or_none()
        
        if dish:
            for key, value in dish_data.items():
                setattr(dish, key, value)
            await self.db.flush()
        
        return dish
    
    async def delete(self, dish_id: int) -> bool:
        """
        Delete a dish.
        
        Args:
            dish_id: Dish ID
            
        Returns:
            True if deleted, False if not found
        """
        query = select(Dish).where(Dish.id == dish_id)
        result = await self.db.execute(query)
        dish = result.scalar_one_or_none()
        
        if dish:
            await self.db.delete(dish)
            await self.db.flush()
            return True
        
        return False
