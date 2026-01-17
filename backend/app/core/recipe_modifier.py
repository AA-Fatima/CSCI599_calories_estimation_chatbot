"""Recipe modifier - handles ingredient modifications."""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.models.schemas import (
    IngredientWithNutrition,
    ModificationAction,
    IngredientBase
)
from app.core.ingredient_manager import ingredient_manager


class RecipeModifier:
    """Handles recipe modifications (add/remove/change quantity)."""
    
    async def apply_modifications(
        self,
        ingredients: List[IngredientWithNutrition],
        modifications: List[ModificationAction],
        db: AsyncSession
    ) -> List[IngredientWithNutrition]:
        """
        Apply modifications to ingredient list.
        
        Args:
            ingredients: Original list of ingredients
            modifications: List of modification actions
            
        Returns:
            Modified list of ingredients
        """
        if not ingredients:
            logger.warning("No ingredients to modify")
            return []
        
        if not modifications:
            return ingredients
        
        # Start with a copy of the ingredients list
        result = list(ingredients)
        
        for mod in modifications:
            if not mod or not hasattr(mod, 'action'):
                logger.warning(f"Invalid modification object: {mod}")
                continue
            
            try:
                if mod.action == "remove":
                    if not mod.ingredient:
                        logger.warning("Remove action has no ingredient name")
                        continue
                    result = self._remove_ingredient(result, mod.ingredient)
                    logger.info(f"Removed '{mod.ingredient}'. Remaining ingredients: {len(result)}")
                elif mod.action == "add":
                    if not mod.ingredient:
                        logger.warning("Add action has no ingredient name")
                        continue
                    result = await self._add_ingredient(result, mod.ingredient, mod.new_weight_g, db)
                    logger.info(f"Added '{mod.ingredient}'. Total ingredients: {len(result)}")
                elif mod.action == "change_quantity":
                    if not mod.ingredient:
                        logger.warning("Change quantity action has no ingredient name")
                        continue
                    result = await self._change_quantity(result, mod.ingredient, mod.new_weight_g, db)
                    logger.info(f"Changed quantity for '{mod.ingredient}' to {mod.new_weight_g}g")
                else:
                    logger.warning(f"Unknown modification action: {mod.action}")
            except Exception as e:
                logger.error(f"Error applying modification {mod.action} for '{getattr(mod, 'ingredient', 'unknown')}': {e}", exc_info=True)
                raise
        
        return result
    
    def _extract_core_ingredient(self, ingredient_name: str) -> str:
        """
        Extract core ingredient name from USDA-style descriptions.
        Examples:
        - "Potatoes, french fried, steak fries..." -> "potato"
        - "Tomatoes, grape, raw" -> "tomato"
        - "Chicken, broiler or fryers, breast..." -> "chicken"
        """
        if not ingredient_name:
            return ""
        
        name_lower = ingredient_name.lower().strip()
        
        # Remove common prefixes/suffixes and get first meaningful word
        # Split by comma and take first part
        first_part = name_lower.split(',')[0].strip()
        
        # Split by space and get first word
        words = first_part.split()
        
        # Common plural to singular mappings and aliases
        plural_to_singular = {
            'potatoes': 'potato',
            'potato': 'potato',
            'tomatoes': 'tomato',
            'tomato': 'tomato',
            'onions': 'onion',
            'onion': 'onion',
            'peppers': 'pepper',
            'pepper': 'pepper',
            'mushrooms': 'mushroom',
            'mushroom': 'mushroom',
            'pickles': 'pickle',
            'pickle': 'pickle',
            'fries': 'potato',  # fries -> potato
            'french fries': 'potato',
            'french fry': 'potato',
            'steak fries': 'potato',
        }
        
        # Check for multi-word matches first (e.g., "french fries", "steak fries")
        if len(words) >= 2:
            two_words = f"{words[0]} {words[1]}"
            if two_words in plural_to_singular:
                return plural_to_singular[two_words]
        
        # Get first word and normalize
        if words:
            first_word = words[0]
            # Check if it's a known plural or alias
            if first_word in plural_to_singular:
                return plural_to_singular[first_word]
            # Remove 's' if it's a simple plural (e.g., "chickens" -> "chicken")
            if first_word.endswith('s') and len(first_word) > 3:
                singular = first_word[:-1]
                # Don't singularize if it would create invalid words
                if singular not in ['chic', 'onion', 'pepper']:  # exceptions
                    return singular
            return first_word
        
        return name_lower
    
    def _ingredients_match(self, query_ingredient: str, db_ingredient: str) -> bool:
        """
        Check if two ingredient names refer to the same core ingredient.
        Uses smart matching to handle variations.
        """
        if not query_ingredient or not db_ingredient:
            return False
        
        query_lower = query_ingredient.lower().strip()
        db_lower = db_ingredient.lower().strip()
        
        # Extract core ingredients
        query_core = self._extract_core_ingredient(query_ingredient)
        db_core = self._extract_core_ingredient(db_ingredient)
        
        # Direct match on core ingredient
        if query_core and db_core and query_core == db_core:
            return True
        
        # Also check if query core is in db ingredient name
        if query_core and query_core in db_lower:
            return True
        
        # Check if db core is in query (for reverse matching)
        if db_core and db_core in query_lower:
            return True
        
        # Fallback: substring match (original behavior)
        if query_lower in db_lower or db_lower in query_lower:
            return True
        
        return False
    
    def _remove_ingredient(
        self,
        ingredients: List[IngredientWithNutrition],
        ingredient_name: str
    ) -> List[IngredientWithNutrition]:
        """Remove ingredient from list using smart matching."""
        if not ingredient_name or not ingredients:
            return ingredients
        
        try:
            result = []
            for ing in ingredients:
                if not ing or not ing.name:
                    result.append(ing)
                    continue
                
                # Use smart matching instead of simple substring
                if not self._ingredients_match(ingredient_name, ing.name):
                    result.append(ing)
                else:
                    logger.debug(f"Matched '{ingredient_name}' with '{ing.name}' for removal")
            
            return result
        except Exception as e:
            logger.error(f"Error in _remove_ingredient: {e}", exc_info=True)
            return ingredients
    
    async def _add_ingredient(
        self,
        ingredients: List[IngredientWithNutrition],
        ingredient_name: str,
        weight_g: Optional[float],
        db: AsyncSession
    ) -> List[IngredientWithNutrition]:
        """Add ingredient to list."""
        if weight_g is None:
            weight_g = 30.0
        
        new_ingredient = await ingredient_manager.search_and_calculate(
            IngredientBase(name=ingredient_name, weight_g=weight_g),
            db
        )
        
        if new_ingredient:
            ingredients.append(new_ingredient)
        
        return ingredients
    
    async def _change_quantity(
        self,
        ingredients: List[IngredientWithNutrition],
        ingredient_name: str,
        new_weight_g: float,
        db: AsyncSession
    ) -> List[IngredientWithNutrition]:
        """Change quantity of existing ingredient using smart matching."""
        if not ingredient_name or not new_weight_g:
            return ingredients
        
        result = []
        for ing in ingredients:
            if ing.name and self._ingredients_match(ingredient_name, ing.name):
                # Recalculate with new weight using nutrition service
                from app.services.nutrition import nutrition_service
                nutrition = nutrition_service.calculate_nutrition_by_weight(
                    ing.calories * (100.0 / ing.weight_g) if ing.weight_g > 0 else 0,
                    ing.carbs * (100.0 / ing.weight_g) if ing.weight_g > 0 else 0,
                    ing.protein * (100.0 / ing.weight_g) if ing.weight_g > 0 else 0,
                    ing.fat * (100.0 / ing.weight_g) if ing.weight_g > 0 else 0,
                    new_weight_g
                )
                
                updated = IngredientWithNutrition(
                    name=ing.name,
                    weight_g=new_weight_g,
                    usda_fdc_id=ing.usda_fdc_id,
                    calories=nutrition['calories'],
                    carbs=nutrition['carbs'],
                    protein=nutrition['protein'],
                    fat=nutrition['fat']
                )
                result.append(updated)
            else:
                result.append(ing)
        
        return result


# Global instance
recipe_modifier = RecipeModifier()
