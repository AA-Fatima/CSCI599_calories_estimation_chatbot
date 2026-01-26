"""Ingredient manager - searches USDA and calculates nutrition using repositories."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.models.schemas import IngredientBase, IngredientWithNutrition
from app.repositories.usda import USDARepository
from app.services.embedding import embedding_service
from app.services.nutrition import nutrition_service


class IngredientManager:
    """Manages ingredient search and nutrition calculation using repositories."""
    
    async def search_and_calculate(
        self,
        ingredient: IngredientBase,
        db: AsyncSession
    ) -> Optional[IngredientWithNutrition]:
        """
        Search for ingredient in USDA and calculate nutrition.
        
        Args:
            ingredient: Base ingredient with name and weight
            db: Database session
            
        Returns: 
            Ingredient with calculated nutrition or None
        """
        logger.debug(f"Searching USDA for: {ingredient.name} ({ingredient.weight_g}g)")
        
        usda_repo = USDARepository(db)
        
        # Generate embedding and search with fallback
        query_embedding = embedding_service.encode(ingredient.name)
        result = await usda_repo.search_with_fallback(
            query_text=ingredient.name,
            query_embedding=query_embedding,
            threshold=0.5
        )
        
        if not result:
            logger.warning(f"Not found in USDA: {ingredient.name}")
            return None
        
        food, similarity = result
        logger.debug(f"Found: {food.description} (similarity: {similarity:.3f})")
        
        # Calculate nutrition for the specific weight
        nutrition = nutrition_service.calculate_nutrition_by_weight(
            food.calories,
            food.carbs,
            food.protein,
            food.fat,
            ingredient.weight_g
        )
        
        return IngredientWithNutrition(
            name=food.description,
            weight_g=ingredient.weight_g,
            usda_fdc_id=food.fdc_id,
            calories=nutrition['calories'],
            carbs=nutrition['carbs'],
            protein=nutrition['protein'],
            fat=nutrition['fat']
        )


# Global instance
ingredient_manager = IngredientManager()
