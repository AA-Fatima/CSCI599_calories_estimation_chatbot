"""Nutrition service for calorie calculations."""
from typing import List
from loguru import logger
from app.models.schemas import IngredientWithNutrition, NutritionTotals


class NutritionService:
    """Service for nutrition calculations."""
    
    @staticmethod
    def calculate_totals(ingredients: List[IngredientWithNutrition]) -> NutritionTotals:
        """
        Calculate total nutrition from ingredients.
        
        Args:
            ingredients: List of ingredients with nutrition
            
        Returns:
            NutritionTotals object
        """
        totals = NutritionTotals(
            calories=0.0,
            carbs=0.0,
            protein=0.0,
            fat=0.0
        )
        
        for ing in ingredients:
            totals.calories += ing.calories
            totals.carbs += ing.carbs
            totals.protein += ing.protein
            totals.fat += ing.fat
        
        # Round to 1 decimal place
        totals.calories = round(totals.calories, 1)
        totals.carbs = round(totals.carbs, 1)
        totals.protein = round(totals.protein, 1)
        totals.fat = round(totals.fat, 1)
        
        logger.debug(f"Calculated totals: {totals.calories}cal, C:{totals.carbs}g, P:{totals.protein}g, F:{totals.fat}g")
        
        return totals
    
    @staticmethod
    def calculate_nutrition_by_weight(
        calories_per_100g: float,
        carbs_per_100g: float,
        protein_per_100g: float,
        fat_per_100g: float,
        weight_g: float
    ) -> dict:
        """
        Calculate nutrition for specific weight.
        
        Args:
            calories_per_100g: Calories per 100g
            carbs_per_100g: Carbs per 100g
            protein_per_100g: Protein per 100g
            fat_per_100g: Fat per 100g
            weight_g: Weight in grams
            
        Returns:
            Dictionary with calculated nutrition
        """
        multiplier = weight_g / 100.0
        
        return {
            'calories': round(calories_per_100g * multiplier, 1),
            'carbs': round(carbs_per_100g * multiplier, 1),
            'protein': round(protein_per_100g * multiplier, 1),
            'fat': round(fat_per_100g * multiplier, 1),
        }


# Global instance
nutrition_service = NutritionService()
