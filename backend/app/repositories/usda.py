"""USDA foods repository with vector search."""
from typing import Optional, Tuple, List, Dict
from sqlalchemy import select, func, or_
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
        min_threshold: float = 0.4,
    ) -> Optional[Tuple[USDAFood, float]]:
        """
        Search for food using vector similarity with progressive threshold lowering.
        
        Args:
            query_embedding: Query vector embedding
            threshold: Initial similarity threshold (default from config)
            min_threshold: Minimum threshold to try (will return best match even if below)
            
        Returns:
            Tuple of (food, similarity_score) or None
        """
        if threshold is None:
            threshold = settings.similarity_threshold
        
        logger.info(f"Searching USDA foods with vector similarity (threshold: {threshold:.2f})")
        
        # Try with initial threshold first
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
        
        # If no match, try with lower threshold (get top result even if below threshold)
        logger.info(f"No match at threshold {threshold:.2f}, trying lower threshold...")
        query = select(
            USDAFood,
            (1 - USDAFood.embedding.cosine_distance(query_embedding)).label('similarity')
        ).where(
            (1 - USDAFood.embedding.cosine_distance(query_embedding)) >= min_threshold
        ).order_by(
            (1 - USDAFood.embedding.cosine_distance(query_embedding)).desc()
        ).limit(1)
        
        result = await self.db.execute(query)
        row = result.first()
        
        if row:
            food, similarity = row
            logger.info(f"Found USDA food (below initial threshold): {food.description} (similarity: {similarity:.3f})")
            return food, float(similarity)
        
        # Last resort: get best match regardless of threshold
        logger.info("Trying best match regardless of threshold...")
        query = select(
            USDAFood,
            (1 - USDAFood.embedding.cosine_distance(query_embedding)).label('similarity')
        ).order_by(
            (1 - USDAFood.embedding.cosine_distance(query_embedding)).desc()
        ).limit(1)
        
        result = await self.db.execute(query)
        row = result.first()
        
        if row:
            food, similarity = row
            if similarity >= min_threshold:
                logger.info(f"Found USDA food (best match): {food.description} (similarity: {similarity:.3f})")
                return food, float(similarity)
        
        logger.info("No USDA food match found")
        return None
    
    async def search_with_fallback(
        self,
        query_text: str,
        query_embedding: List[float],
        threshold: float = None,
    ) -> Optional[Tuple[USDAFood, float]]:
        """
        Search with vector similarity, falling back to text search if needed.
        
        Args:
            query_text: Original query text for text-based fallback
            query_embedding: Query vector embedding
            threshold: Similarity threshold
            
        Returns:
            Tuple of (food, similarity_score) or None
        """
        # Try vector search first
        result = await self.search(query_embedding, threshold=threshold)
        if result:
            return result
        
        # Fallback to text search
        logger.info(f"Vector search failed, trying text search for: {query_text}")
        text_results = await self.search_by_text(query_text, limit=5)
        
        if text_results:
            # Return the first text match with a reasonable similarity score
            # We'll use 0.5 as a placeholder since we don't have vector similarity here
            logger.info(f"Found via text search: {text_results[0].description}")
            return text_results[0], 0.5
        
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
        
        # Clean up common prefixes
        prefixes_to_remove = ["calories in", "calorie in", "cal in", "how many calories in"]
        for prefix in prefixes_to_remove:
            if search_lower.startswith(prefix):
                search_lower = search_lower[len(prefix):].strip()
        
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
        starts_with_matches = list(result.scalars().all())
        
        if starts_with_matches:
            return starts_with_matches
        
        # Try contains match (split search text into words)
        words = [w.strip() for w in search_lower.split() if len(w.strip()) > 2]
        if words:
            # Build contains query - at least one word must match
            conditions = [USDAFood.description_lower.like(f"%{word}%") for word in words]
            query = select(USDAFood).where(
                or_(*conditions)
            ).order_by(
                func.length(USDAFood.description)
            ).limit(limit)
            result = await self.db.execute(query)
            contains_matches = list(result.scalars().all())
            
            if contains_matches:
                return contains_matches
        
        return []
    
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
