"""Recipe modifier - handles ingredient modifications."""
from typing import List
from app.models.schemas import (
    IngredientWithNutrition,
    ModificationAction,
    IngredientBase
)
from app.core.ingredient_manager import ingredient_manager


class RecipeModifier:
    """Handles recipe modifications (add/remove/change quantity)."""
    
    def apply_modifications(
        self,
        ingredients: List[IngredientWithNutrition],
        modifications: List[ModificationAction]
    ) -> List[IngredientWithNutrition]:
        """
        Apply modifications to ingredient list.
        
        Args:
            ingredients: Original list of ingredients
            modifications: List of modification actions
            
        Returns:
            Modified list of ingredients
        """
        result = ingredients.copy()
        
        for mod in modifications:
            if mod.action == "remove":
                result = self._remove_ingredient(result, mod.ingredient)
            elif mod.action == "add":
                result = self._add_ingredient(result, mod.ingredient, mod.new_weight_g)
            elif mod.action == "change_quantity":
                result = self._change_quantity(result, mod.ingredient, mod.new_weight_g)
        
        return result
    
    def _remove_ingredient(
        self,
        ingredients: List[IngredientWithNutrition],
        ingredient_name: str
    ) -> List[IngredientWithNutrition]:
        """Remove ingredient from list."""
        ingredient_name_lower = ingredient_name.lower().strip()
        
        return [
            ing for ing in ingredients
            if ingredient_name_lower not in ing.name.lower()
        ]
    
    def _add_ingredient(
        self,
        ingredients: List[IngredientWithNutrition],
        ingredient_name: str,
        weight_g: float = None
    ) -> List[IngredientWithNutrition]:
        """Add ingredient to list."""
        # Use default weight if not specified
        if weight_g is None:
            weight_g = 30.0  # Default 30g
        
        # Search and calculate nutrition
        new_ingredient = ingredient_manager.search_and_calculate(
            IngredientBase(name=ingredient_name, weight_g=weight_g)
        )
        
        if new_ingredient:
            ingredients.append(new_ingredient)
        
        return ingredients
    
    def _change_quantity(
        self,
        ingredients: List[IngredientWithNutrition],
        ingredient_name: str,
        new_weight_g: float
    ) -> List[IngredientWithNutrition]:
        """Change quantity of existing ingredient."""
        ingredient_name_lower = ingredient_name.lower().strip()
        
        result = []
        for ing in ingredients:
            if ingredient_name_lower in ing.name.lower():
                # Recalculate with new weight
                updated = ingredient_manager.search_and_calculate(
                    IngredientBase(name=ing.name, weight_g=new_weight_g)
                )
                if updated:
                    result.append(updated)
            else:
                result.append(ing)
        
        return result


# Global instance
recipe_modifier = RecipeModifier()
