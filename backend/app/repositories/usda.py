"""USDA foods repository with vector search."""
from typing import Optional, Tuple, List, Dict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.models.database import USDAFood
from app.config import settings


class USDARepository:
    """Repository for USDA foods with semantic search."""
    
    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db
    
    async def search(
        self,
        query_embedding: List[float],
        threshold: float = None,
    ) -> Optional[Tuple[USDAFood, float]]:
        """
        Search for food using vector similarity.
        
        Args:
            query_embedding: Query vector embedding
            threshold: Similarity threshold (default from config)
            
        Returns:
            Tuple of (food, similarity_score) or None
        """
        if threshold is None:
            threshold = settings.similarity_threshold
        
        logger.info("Searching USDA foods with vector similarity")
        
        # Build query with vector similarity
        query = select(
            USDAFood,
            (1 - USDAFood.embedding.cosine_distance(query_embedding)).label('similarity')
        ).where(
            (1 - USDAFood.embedding.cosine_distance(query_embedding)) >= threshold
        ).order_by(
            (1 - USDAFood.embedding.cosine_distance(query_embedding)).desc()
        ).limit(1)
        
        result = await self.db.execute(query)
        row = result.first()
        
        if row:
            food, similarity = row
            logger.info(f"Found USDA food: {food.description} (similarity: {similarity:.3f})")
            return food, float(similarity)
        
        logger.info("No USDA food match found")
        return None
    
    async def search_by_text(
        self,
        search_text: str,
        limit: int = 10
    ) -> List[USDAFood]:
        """
        Search for foods by text (for exact or fuzzy matching).
        
        Args:
            search_text: Search text
            limit: Maximum number of results
            
        Returns:
            List of matching foods
        """
        search_lower = search_text.lower().strip()
        
        # Try exact match first
        query = select(USDAFood).where(
            USDAFood.description_lower == search_lower
        ).limit(1)
        result = await self.db.execute(query)
        exact_match = result.scalar_one_or_none()
        
        if exact_match:
            return [exact_match]
        
        # Try starts-with match
        query = select(USDAFood).where(
            USDAFood.description_lower.like(f"{search_lower}%")
        ).order_by(
            func.length(USDAFood.description)
        ).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_fdc_id(self, fdc_id: int) -> Optional[USDAFood]:
        """
        Get food by FDC ID.
        
        Args:
            fdc_id: USDA FDC ID
            
        Returns:
            USDAFood or None
        """
        query = select(USDAFood).where(USDAFood.fdc_id == fdc_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create(self, food_data: Dict) -> USDAFood:
        """
        Create a new USDA food entry.
        
        Args:
            food_data: Food data dictionary
            
        Returns:
            Created food
        """
        food = USDAFood(**food_data)
        self.db.add(food)
        await self.db.flush()
        return food
    
    async def get_count(self) -> int:
        """
        Get total count of USDA foods.
        
        Returns:
            Total count
        """
        query = select(func.count(USDAFood.id))
        result = await self.db.execute(query)
        return result.scalar()
