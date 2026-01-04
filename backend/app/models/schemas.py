"""Pydantic schemas for request/response models."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class IngredientBase(BaseModel):
    """Base ingredient model."""
    name: str
    weight_g: float
    
    
class IngredientWithNutrition(IngredientBase):
    """Ingredient with nutritional information."""
    usda_fdc_id: Optional[int] = None
    calories: float
    carbs: float
    protein: float
    fat: float


class ModificationAction(BaseModel):
    """Ingredient modification action."""
    action: Literal["remove", "add", "change_quantity"]
    ingredient: str
    new_weight_g: Optional[float] = None


class GPTAnalysisResponse(BaseModel):
    """Response from GPT analysis."""
    dish_name: str
    dish_name_arabic: Optional[str] = None
    is_single_ingredient: bool
    country_variant: Optional[str] = None
    user_intent: Literal[
        "query_calories",
        "modify_dish",
        "add_ingredient",
        "remove_ingredient",
        "change_quantity",
        "unknown_dish"
    ]
    modifications: List[ModificationAction] = []
    ingredients_breakdown: List[IngredientBase] = []


class NutritionTotals(BaseModel):
    """Nutritional totals."""
    calories: float
    carbs: float
    protein: float
    fat: float


class ChatRequest(BaseModel):
    """Chat message request."""
    message: str
    session_id: Optional[str] = None
    country: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat message response."""
    session_id: str
    dish_name: str
    dish_name_arabic: Optional[str] = None
    ingredients: List[IngredientWithNutrition]
    totals: NutritionTotals
    source: Literal["dataset", "ai_estimated"]
    message: str


class DishBase(BaseModel):
    """Base dish model."""
    dish_name: str
    weight_g: float
    country: str
    ingredients: List[IngredientWithNutrition]


class DishCreate(DishBase):
    """Create dish model."""
    pass


class DishUpdate(DishBase):
    """Update dish model."""
    dish_id: Optional[int] = None


class Dish(DishBase):
    """Dish model with ID."""
    dish_id: int
    calories: float
    date_accessed: Optional[str] = None


class MissingDish(BaseModel):
    """Missing dish tracking."""
    dish_name: str
    dish_name_arabic: Optional[str] = None
    country: str
    query_text: str
    gpt_response: Dict[str, Any]
    ingredients: List[IngredientBase]
    query_count: int = 1
    first_queried: datetime
    last_queried: datetime


class CountryResponse(BaseModel):
    """Country list response."""
    countries: List[str]


class TestQuery(BaseModel):
    """Test query for comparison."""
    query: str
    country: str
    expected_calories: float
    expected_carbs: Optional[float] = None
    expected_protein: Optional[float] = None
    expected_fat: Optional[float] = None


class ComparisonResult(BaseModel):
    """Comparison result for a single query."""
    query: str
    expected: NutritionTotals
    chatbot: NutritionTotals
    gpt: NutritionTotals
    deepseek: NutritionTotals


class ComparisonMetrics(BaseModel):
    """Comparison metrics."""
    mae: float
    rmse: float
    mape: float
    accuracy_10_percent: float
    accuracy_20_percent: float


class ComparisonReport(BaseModel):
    """Full comparison report."""
    results: List[ComparisonResult]
    chatbot_metrics: ComparisonMetrics
    gpt_metrics: ComparisonMetrics
    deepseek_metrics: ComparisonMetrics
    summary: str


class AdminStatsResponse(BaseModel):
    """Admin dashboard statistics."""
    total_dishes: int
    missing_dishes_count: int
    queries_today: int
    countries: List[str]
