"""Ingredient manager - searches USDA and calculates nutrition."""
from typing import Optional
from app.models.schemas import IngredientBase, IngredientWithNutrition
from app.data.usda_handler import usda_handler


class IngredientManager:
    """Manages ingredient search and nutrition calculation."""
    
    def search_and_calculate(
        self,
        ingredient: IngredientBase,
        threshold: int = 70
    ) -> Optional[IngredientWithNutrition]:
        """
        Search for ingredient in USDA and calculate nutrition.
        
        Args:
            ingredient: Base ingredient with name and weight
            threshold: Matching threshold for fuzzy search
            
        Returns: 
            Ingredient with calculated nutrition or None
        """
        print(f"      🔍 Searching USDA for:  {ingredient.name} ({ingredient.weight_g}g)")
        
        # Search USDA database
        usda_food = usda_handler.search_ingredient(ingredient.name, threshold)
        
        if not usda_food:
            print(f"      ❌ Not found in USDA:  {ingredient.name}")
            return None
        
        # Calculate nutrition for the specific weight
        nutrition = usda_handler.calculate_nutrition_by_weight(usda_food, ingredient.weight_g)
        
        # Get actual USDA name
        usda_name = usda_food.get('description', ingredient.name)
        
        print(f"      ✅ Found:  {usda_name}")
        print(f"         - {ingredient.weight_g}g = {nutrition['calories']}cal, C:{nutrition['carbs']}g, P:{nutrition['protein']}g, F:{nutrition['fat']}g")
        
        return IngredientWithNutrition(
            name=usda_name,
            weight_g=ingredient.weight_g,
            usda_fdc_id=usda_food.get('fdcId'),
            calories=nutrition['calories'],
            carbs=nutrition['carbs'],
            protein=nutrition['protein'],
            fat=nutrition['fat']
        )


# Global instance
ingredient_manager = IngredientManager()