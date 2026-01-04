"""Calorie calculator - main calculation logic."""
from typing import List, Tuple
from app.models.schemas import (
    IngredientWithNutrition,
    NutritionTotals
)


class CalorieCalculator:
    """Calculate calories and nutrition totals."""
    
    def calculate_totals(
        self,
        ingredients: List[IngredientWithNutrition]
    ) -> NutritionTotals:
        """
        Calculate total nutrition from ingredients.
        
        Args:
            ingredients: List of ingredients with nutrition info
            
        Returns:
            Total nutritional values
        """
        totals = NutritionTotals(
            calories=0.0,
            carbs=0.0,
            protein=0.0,
            fat=0.0
        )
        
        for ingredient in ingredients:
            totals.calories += ingredient.calories
            totals.carbs += ingredient.carbs
            totals.protein += ingredient.protein
            totals.fat += ingredient.fat
        
        return totals
    
    def calculate_per_100g(
        self,
        ingredients: List[IngredientWithNutrition],
        total_weight_g: float
    ) -> NutritionTotals:
        """
        Calculate nutrition per 100g.
        
        Args:
            ingredients: List of ingredients
            total_weight_g: Total weight of the dish
            
        Returns:
            Nutritional values per 100g
        """
        totals = self.calculate_totals(ingredients)
        
        if total_weight_g <= 0:
            return totals
        
        factor = 100.0 / total_weight_g
        
        return NutritionTotals(
            calories=totals.calories * factor,
            carbs=totals.carbs * factor,
            protein=totals.protein * factor,
            fat=totals.fat * factor
        )


# Global instance
calorie_calculator = CalorieCalculator()
