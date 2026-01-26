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
        query_text: str = None,
        threshold: float = None,
        min_confidence: float = 0.70,
    ) -> Optional[Tuple[Dish, float, bool]]:
        """
        Search for dish with country prioritization and confidence checking.
        
        Args:
            query_embedding: Query vector embedding
            user_country: User's country for priority search
            query_text: Original query text for exact/prefix matching
            threshold: Initial similarity threshold (default from config)
            min_confidence: Minimum confidence for high-quality matches (default 0.80)
            
        Returns:
            Tuple of (dish, similarity_score, is_from_user_country) or None
        """
        if threshold is None:
            threshold = settings.similarity_threshold
        
        logger.info(f"Searching dishes with country priority: {user_country}")
        
        query_lower = query_text.lower().strip() if query_text else ""
        
        # Phase 0: Try exact/prefix match first (most accurate)
        if query_text:
            exact_result = await self._exact_or_prefix_search(query_lower, user_country)
            if exact_result:
                dish, match_type = exact_result
                dish_name_lower = dish.dish_name.lower()
                # Double-check it's not a partial match or different dish
                if not self._is_partial_match(query_lower, dish_name_lower):
                    # Additional check: verify word overlap for safety
                    query_words = set(query_lower.split()) - {'the', 'a', 'an', 'and', 'or', 'with', 'in', 'on', 'of'}
                    dish_words = set(dish_name_lower.split()) - {'the', 'a', 'an', 'and', 'or', 'with', 'in', 'on', 'of'}
                    common_words = query_words & dish_words
                    
                    # For prefix matches, ensure at least one common word
                    if match_type == "prefix" and not common_words and len(query_words) > 0:
                        logger.warning(f"Rejecting prefix match with no common words: '{query_text}' -> '{dish.dish_name}'")
                    else:
                        logger.info(f"Found EXACT/PREFIX match in {user_country}: {dish.dish_name} ({match_type})")
                        # Return with high similarity score for exact matches
                        return dish, 0.95 if match_type == "exact" else 0.90, True
                else:
                    logger.warning(f"Rejecting partial/different match from exact search: '{query_text}' -> '{dish.dish_name}'")
        
        # Phase 1: Search in user's country with high confidence first
        result = await self._vector_search(
            query_embedding,
            country=user_country,
            threshold=max(threshold, min_confidence),  # Use higher threshold for better matches
            query_text=query_text  # Pass query text for filtering
        )
        
        if result:
            dish, similarity = result
            # Filter out partial matches and different dishes
            if query_text:
                dish_name_lower = dish.dish_name.lower()
                if self._is_partial_match(query_lower, dish_name_lower):
                    logger.warning(
                        f"Rejecting match: '{query_text}' -> '{dish.dish_name}' "
                        f"(similarity: {similarity:.3f}) - Different or partial match. Continuing search..."
                    )
                    result = None  # Continue to next phase
                else:
                    logger.info(f"Found in user's country: {dish.dish_name} (similarity: {similarity:.3f})")
                    return dish, similarity, True
            else:
                logger.info(f"Found in user's country: {dish.dish_name} (similarity: {similarity:.3f})")
                return dish, similarity, True
        
        # Phase 2: Try with lower threshold in user's country (only if no exact match)
        if threshold < min_confidence and not result:
            logger.info(f"No high-confidence match in {user_country}, trying lower threshold...")
            result = await self._vector_search(
                query_embedding,
                country=user_country,
                threshold=threshold,
                query_text=query_text
            )
            
            if result:
                dish, similarity = result
                # Filter partial matches
                if query_text and self._is_partial_match(query_lower, dish.dish_name.lower()):
                    logger.warning(f"Rejecting partial match: '{query_text}' -> '{dish.dish_name}'")
                    result = None
                elif similarity >= min_confidence:
                    logger.info(f"Found in user's country: {dish.dish_name} (similarity: {similarity:.3f})")
                    return dish, similarity, True
                else:
                    logger.warning(
                        f"Low confidence match in {user_country}: {dish.dish_name} "
                        f"(similarity: {similarity:.3f}). Continuing search..."
                    )
        
        # Phase 3: Search in all other countries with exact/prefix first
        if query_text:
            logger.info(f"Not found in {user_country}, trying exact match in all countries...")
            exact_result = await self._exact_or_prefix_search(query_lower, exclude_country=user_country)
            if exact_result:
                dish, match_type = exact_result
                # Double-check it's not a partial match
                if not self._is_partial_match(query_lower, dish.dish_name.lower()):
                    logger.info(f"Found EXACT/PREFIX match in {dish.country}: {dish.dish_name} ({match_type})")
                    return dish, 0.95 if match_type == "exact" else 0.90, False
                else:
                    logger.warning(f"Rejecting partial match from exact search: '{query_text}' -> '{dish.dish_name}'")
        
        # Phase 4: Vector search in all other countries
        logger.info(f"Not found in {user_country}, searching all countries...")
        result = await self._vector_search(
            query_embedding,
            exclude_country=user_country,
            threshold=max(threshold, min_confidence),
            query_text=query_text
        )
        
        if result:
            dish, similarity = result
            # Filter partial matches
            if query_text and self._is_partial_match(query_lower, dish.dish_name.lower()):
                logger.warning(f"Rejecting partial match: '{query_text}' -> '{dish.dish_name}'")
                result = None
            else:
                logger.info(f"Found in {dish.country}: {dish.dish_name} (similarity: {similarity:.3f})")
                return dish, similarity, False
        
        # Phase 5: Last resort - lower threshold in all countries
        if threshold < min_confidence and not result:
            result = await self._vector_search(
                query_embedding,
                exclude_country=user_country,
                threshold=threshold,
                query_text=query_text
            )
            
            if result:
                dish, similarity = result
                # Filter partial matches
                if query_text and self._is_partial_match(query_lower, dish.dish_name.lower()):
                    logger.warning(f"Rejecting partial match: '{query_text}' -> '{dish.dish_name}'")
                    result = None
                else:
                    logger.warning(
                        f"Low confidence match in {dish.country}: {dish.dish_name} "
                        f"(similarity: {similarity:.3f})"
                    )
                    return dish, similarity, False
        
        logger.info("No match found in any country")
        return None
    
    async def _exact_or_prefix_search(
        self,
        query_lower: str,
        country: str = None,
        exclude_country: str = None
    ) -> Optional[Tuple[Dish, str]]:
        """
        Search for exact or prefix match (most accurate).
        
        Args:
            query_lower: Lowercase query text
            country: Filter by country
            exclude_country: Exclude country
            
        Returns:
            Tuple of (dish, match_type) where match_type is "exact" or "prefix"
        """
        # Try exact match first
        query = select(Dish).where(
            func.lower(Dish.dish_name) == query_lower
        )
        
        if country:
            query = query.where(func.lower(Dish.country) == country.lower())
        if exclude_country:
            query = query.where(func.lower(Dish.country) != exclude_country.lower())
        
        query = query.limit(1)
        result = await self.db.execute(query)
        dish = result.scalar_one_or_none()
        
        if dish:
            return dish, "exact"
        
        # Try prefix match (starts with) - but filter out partial matches
        query = select(Dish).where(
            func.lower(Dish.dish_name).like(f"{query_lower}%")
        ).order_by(func.length(Dish.dish_name))
        
        if country:
            query = query.where(func.lower(Dish.country) == country.lower())
        if exclude_country:
            query = query.where(func.lower(Dish.country) != exclude_country.lower())
        
        # Get multiple results to filter
        query = query.limit(10)  # Get more results to filter
        result = await self.db.execute(query)
        dishes = result.scalars().all()
        
        # Filter out partial matches and return best acceptable match
        for dish in dishes:
            dish_name_lower = dish.dish_name.lower()
            # Check if it's a partial match (e.g., "shawarma" in "shawarma pizza")
            if not self._is_partial_match(query_lower, dish_name_lower):
                return dish, "prefix"
        
        # If all prefix matches are partial, return None
        return None
    
    def _is_partial_match(self, query: str, dish_name: str) -> bool:
        """
        Check if query is a partial match or completely different dish.
        Rejects matches where dishes are clearly different.
        
        Args:
            query: Query text (lowercase)
            dish_name: Dish name (lowercase)
            
        Returns:
            True if it's a bad match (partial or different dish)
        """
        # Normalize: remove extra spaces
        query = query.strip()
        dish_name = dish_name.strip()
        
        # Exact match is never partial
        if query == dish_name:
            return False
        
        # Check word overlap - if no common words, likely different dishes
        query_words = set(query.split())
        dish_words = set(dish_name.split())
        
        # Remove common stop words for comparison
        stop_words = {'the', 'a', 'an', 'and', 'or', 'with', 'in', 'on', 'of', 'for', 'to'}
        query_words_clean = query_words - stop_words
        dish_words_clean = dish_words - stop_words
        
        # If no common meaningful words, they're different dishes
        common_words = query_words_clean & dish_words_clean
        if not common_words and len(query_words_clean) > 0 and len(dish_words_clean) > 0:
            # Check character similarity as fallback
            # If less than 40% character overlap, likely different
            query_chars = set(query.replace(' ', ''))
            dish_chars = set(dish_name.replace(' ', ''))
            char_overlap = len(query_chars & dish_chars) / max(len(query_chars), len(dish_chars)) if max(len(query_chars), len(dish_chars)) > 0 else 0
            if char_overlap < 0.4:
                return True  # Different dishes (e.g., "koshari" vs "kousa mahshi")
        
        # If dish_name doesn't start with query, check if it's a substring match
        if not dish_name.startswith(query):
            # Check if query is a substring (but not at word boundary)
            if query in dish_name:
                query_pos = dish_name.find(query)
                # Check if it's at word boundary
                if query_pos > 0 and dish_name[query_pos - 1] != ' ':
                    return True  # Substring but not word boundary (likely different)
                # Check what comes after
                if query_pos + len(query) < len(dish_name):
                    next_char = dish_name[query_pos + len(query)]
                    if next_char not in [' ', '-', ',', '.']:
                        return True  # Not at word boundary
            # If query is not a substring and no common words, different dish
            elif not common_words:
                return True
        
        # If dish_name starts with query, check extra words
        if dish_name.startswith(query):
            # If dish_name is just query + space, it's not partial
            if dish_name == query or dish_name == f"{query} " or dish_name == f" {query}":
                return False
            
            # Get the part after query
            rest = dish_name[len(query):].strip()
            if not rest:
                return False
            
            rest_words = set(rest.split())
            
            # Common acceptable additions (variants of the same dish)
            acceptable_additions = {
                'wrap', 'plate', 'sandwich', 'salad', 'bowl', 'meal', 'pita',
                'with', 'and', 'the', 'a', 'an', 'of', 'in', 'on'
            }
            
            # Check if ALL extra words are acceptable
            # If ANY extra word is not acceptable, it's a partial match
            for word in rest_words:
                if word not in acceptable_additions:
                    # Check if it's a significant food word (pizza, burger, etc.)
                    significant_food_words = {
                        'pizza', 'burger', 'pasta', 'soup', 'salad', 'sandwich',
                        'wrap', 'taco', 'burrito', 'quesadilla', 'calzone'
                    }
                    if word in significant_food_words:
                        return True  # Partial match (e.g., "shawarma" in "shawarma pizza")
            
            # If all extra words are acceptable, it's not a partial match
            return False
        
        # If query words are a subset of dish words, check extra words
        if query_words.issubset(dish_words):
            extra_words = dish_words - query_words
            
            # If no extra words, it's not partial (should have been caught by exact match)
            if not extra_words:
                return False
            
            # Common acceptable additions
            acceptable_additions = {
                'wrap', 'plate', 'sandwich', 'salad', 'bowl', 'meal', 'pita',
                'with', 'and', 'the', 'a', 'an', 'of', 'in', 'on'
            }
            
            # Check if ALL extra words are acceptable
            for word in extra_words:
                if word not in acceptable_additions:
                    significant_food_words = {
                        'pizza', 'burger', 'pasta', 'soup', 'salad', 'sandwich',
                        'wrap', 'taco', 'burrito', 'quesadilla', 'calzone'
                    }
                    if word in significant_food_words:
                        return True  # Partial match
            
            return False
        
        # If no clear relationship, check character similarity
        # Calculate simple character overlap
        query_chars = set(query.replace(' ', '').lower())
        dish_chars = set(dish_name.replace(' ', '').lower())
        if len(query_chars) > 0 and len(dish_chars) > 0:
            overlap_ratio = len(query_chars & dish_chars) / max(len(query_chars), len(dish_chars))
            # If less than 50% character overlap, likely different dishes
            if overlap_ratio < 0.5:
                return True  # Different dishes
        
        return False
    
    async def _vector_search(
        self,
        query_embedding: List[float],
        country: Optional[str] = None,
        exclude_country: Optional[str] = None,
        threshold: float = None,
        min_threshold: float = 0.4,
        limit: int = 10,  # Get more results to filter
        query_text: str = None
    ) -> Optional[Tuple[Dish, float]]:
        """
        Internal vector search implementation with progressive threshold lowering.
        Returns best match after filtering partial matches.
        
        Args:
            query_embedding: Query vector
            country: Filter by specific country
            exclude_country: Exclude specific country
            threshold: Initial similarity threshold
            min_threshold: Minimum threshold to try
            limit: Number of results to return for filtering
            query_text: Query text for filtering partial matches
            
        Returns:
            Tuple of (dish, similarity_score) or None
        """
        if threshold is None:
            threshold = settings.similarity_threshold
        
        query_lower = query_text.lower().strip() if query_text else ""
        
        # Build base query with vector similarity
        base_query = select(
            Dish,
            (1 - Dish.embedding.cosine_distance(query_embedding)).label('similarity')
        )
        
        # Apply country filters
        if country:
            base_query = base_query.where(func.lower(Dish.country) == country.lower())
        if exclude_country:
            base_query = base_query.where(func.lower(Dish.country) != exclude_country.lower())
        
        # Try with initial threshold first - get multiple results
        query = base_query.where(
            (1 - Dish.embedding.cosine_distance(query_embedding)) >= threshold
        ).order_by(
            (1 - Dish.embedding.cosine_distance(query_embedding)).desc()
        ).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        # Filter out partial matches and return best
        if rows:
            for row in rows:
                dish, similarity = row
                # Filter partial matches if query_text provided
                if query_text and self._is_partial_match(query_lower, dish.dish_name.lower()):
                    logger.debug(f"Skipping partial match: '{query_text}' -> '{dish.dish_name}' (similarity: {similarity:.3f})")
                    continue
                return dish, float(similarity)
        
        # If no match, try with lower threshold
        query = base_query.where(
            (1 - Dish.embedding.cosine_distance(query_embedding)) >= min_threshold
        ).order_by(
            (1 - Dish.embedding.cosine_distance(query_embedding)).desc()
        ).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        if rows:
            for row in rows:
                dish, similarity = row
                # Filter partial matches
                if query_text and self._is_partial_match(query_lower, dish.dish_name.lower()):
                    logger.debug(f"Skipping partial match: '{query_text}' -> '{dish.dish_name}' (similarity: {similarity:.3f})")
                    continue
                return dish, float(similarity)
        
        # Last resort: get best match regardless of threshold
        query = base_query.order_by(
            (1 - Dish.embedding.cosine_distance(query_embedding)).desc()
        ).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        if rows:
            for row in rows:
                dish, similarity = row
                # Filter partial matches
                if query_text and self._is_partial_match(query_lower, dish.dish_name.lower()):
                    logger.debug(f"Skipping partial match: '{query_text}' -> '{dish.dish_name}' (similarity: {similarity:.3f})")
                    continue
                if similarity >= min_threshold:
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
