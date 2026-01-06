"""Admin API routes."""
from fastapi import APIRouter, HTTPException, Query, Header, Depends
from typing import List, Optional
from app.models.schemas import AdminStatsResponse, DishCreate, DishUpdate, IngredientWithNutrition
from app.data.dishes_handler import dishes_handler
from app.services.missing_dish_service import missing_dish_service
from app.core.ingredient_manager import ingredient_manager
from app.data.usda_handler import usda_handler
from app.config import settings
from datetime import datetime
import json
import secrets

router = APIRouter(prefix="/admin", tags=["admin"])


async def verify_admin_password(x_admin_password: Optional[str] = Header(None)):
    """Verify admin password from request header."""
    if not settings.admin_password:
        raise HTTPException(
            status_code=500,
            detail="Admin password not configured on server"
        )
    
    if not x_admin_password:
        raise HTTPException(
            status_code=401,
            detail="Admin password required"
        )
    
    if not secrets.compare_digest(x_admin_password, settings.admin_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin password"
        )
    
    return True


@router.post("/verify")
async def verify_password(authorized: bool = Depends(verify_admin_password)):
    """Verify admin password.This endpoint only returns success/failure."""
    return {"authenticated": True}


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(authorized: bool = Depends(verify_admin_password)):
    """Get admin dashboard statistics."""
    total_dishes = len(dishes_handler.get_all_dishes())
    missing_dishes_count = len(missing_dish_service.get_all_missing_dishes())
    countries = dishes_handler.get_all_countries()
    
    # TODO: Implement queries today tracking
    queries_today = 0
    
    return AdminStatsResponse(
        total_dishes=total_dishes,
        missing_dishes_count=missing_dishes_count,
        queries_today=queries_today,
        countries=countries
    )


@router.get("/missing-dishes")
async def get_missing_dishes(
    authorized: bool = Depends(verify_admin_password),
    country: Optional[str] = Query(None, description="Filter by country"),
    sort_by: str = Query("query_count", description="Sort by:  query_count, first_queried, last_queried")
):
    """
    Get list of missing dishes with filters and sorting.
    """
    missing = missing_dish_service.get_all_missing_dishes()
    
    # Filter by country
    if country: 
        missing = [d for d in missing if d.get('country', '').lower() == country.lower()]
    
    # Sort
    reverse = True  # Most queries first by default
    if sort_by == "query_count":
        missing.sort(key=lambda x: x.get('query_count', 0), reverse=reverse)
    elif sort_by == "first_queried":
        missing.sort(key=lambda x: x.get('first_queried', ''), reverse=reverse)
    elif sort_by == "last_queried":
        missing.sort(key=lambda x: x.get('last_queried', ''), reverse=reverse)
    
    return {"missing_dishes": missing, "total":  len(missing)}


@router.post("/missing-dishes/{dish_name}/add-to-database")
async def add_missing_dish_to_database(
    dish_name: str,
    country: str = Query(..., description="Country of the dish"),
    authorized: bool = Depends(verify_admin_password)
):
    """
    Convert a missing dish to a real dish in the database.
    Uses the GPT's suggested ingredients.
    """
    # Get missing dish
    missing = missing_dish_service.get_missing_dish_by_name(dish_name, country)
    if not missing:
        raise HTTPException(status_code=404, detail="Missing dish not found")
    
    # Get ingredients from missing dish
    ingredients_with_nutrition = []
    
    for ing_base in missing.get('ingredients', []):
        # Search USDA and calculate nutrition
        from app.models.schemas import IngredientBase
        ing = IngredientBase(name=ing_base['name'], weight_g=ing_base['weight_g'])
        
        ingredient_with_nutrition = ingredient_manager.search_and_calculate(ing)
        
        if ingredient_with_nutrition: 
            ingredients_with_nutrition.append(ingredient_with_nutrition)
    
    if not ingredients_with_nutrition:
        raise HTTPException(status_code=400, detail="Could not find USDA data for ingredients")
    
    # Calculate totals
    total_calories = sum(ing.calories for ing in ingredients_with_nutrition)
    total_weight = sum(ing.weight_g for ing in ingredients_with_nutrition)
    
    # Generate new ID
    existing_dishes = dishes_handler.get_all_dishes()
    max_id = max([d.get('dish_id', 0) for d in existing_dishes], default=0)
    
    # Create dish data
    dish_data = {
        'dish_id': max_id + 1,
        'dish_name': missing['dish_name'],
        'weight (g)': total_weight,
        'calories': total_calories,
        'ingredients': json.dumps([
            {
                'usda_fdc_id': ing.usda_fdc_id,
                'name': ing.name,
                'weight_g':  ing.weight_g,
                'calories': ing.calories,
                'carbs': ing.carbs,
                'protein': ing.protein,
                'fat':  ing.fat
            }
            for ing in ingredients_with_nutrition
        ]),
        'country': country,
        'date_accessed':  datetime.now().strftime('%Y-%m-%d')
    }
    
    # Add to database
    success = dishes_handler.add_dish(dish_data)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add dish to database")
    
    # Remove from missing dishes
    missing_dish_service.delete_missing_dish(dish_name, country)
    
    return {
        "message": "Dish added to database successfully",
        "dish_id": dish_data['dish_id'],
        "dish":  dish_data
    }


@router.delete("/missing-dishes/{dish_name}")
async def delete_missing_dish(
    dish_name: str,
    country: str = Query(..., description="Country of the dish"),
    authorized: bool = Depends(verify_admin_password)
):
    """Delete a missing dish record (won't add to database)."""
    missing_dish_service.delete_missing_dish(dish_name, country)
    return {"message": "Missing dish deleted"}


@router.get("/dishes")
async def get_all_dishes(
    authorized: bool = Depends(verify_admin_password),
    country: Optional[str] = None
):
    """Get all dishes with optional country filter."""
    dishes = dishes_handler.get_all_dishes(country)
    return {"dishes":  dishes, "total": len(dishes)}


@router.post("/dishes")
async def create_dish(
    dish: DishCreate,
    authorized:  bool = Depends(verify_admin_password)
):
    """Create a new dish manually."""
    # Generate new ID
    existing_dishes = dishes_handler.get_all_dishes()
    max_id = max([d.get('dish_id', 0) for d in existing_dishes], default=0)
    
    # Calculate total calories
    total_calories = sum(ing.calories for ing in dish.ingredients)
    
    dish_data = {
        'dish_id': max_id + 1,
        'dish_name': dish.dish_name,
        'weight (g)': dish.weight_g,
        'calories':  total_calories,
        'ingredients': json.dumps([
            {
                'usda_fdc_id': ing.usda_fdc_id,
                'name': ing.name,
                'weight_g': ing.weight_g,
                'calories': ing.calories,
                'carbs': ing.carbs,
                'protein': ing.protein,
                'fat': ing.fat
            }
            for ing in dish.ingredients
        ]),
        'country': dish.country,
        'date_accessed': datetime.now().strftime('%Y-%m-%d')
    }
    
    success = dishes_handler.add_dish(dish_data)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add dish")
    
    # ✅ Remove from missing dishes if it exists
    try:
        missing_dish_service.delete_missing_dish(dish.dish_name, dish.country)
    except:
        pass  # It's OK if it wasn't in missing dishes
    
    return {"message": "Dish created successfully", "dish_id": dish_data['dish_id']}

@router.get("/usda/search")
async def search_usda(
    authorized: bool = Depends(verify_admin_password),
    query: str = Query(..., description="Ingredient name to search"),
    threshold: int = Query(70, description="Matching threshold (0-100)")
):
    """Search USDA database for an ingredient."""
    result = usda_handler.search_ingredient(query, threshold)
    
    if not result:
        return {"found": False, "message": f"No match found for '{query}'"}
    
    nutrition = usda_handler.get_nutrition_per_100g(result)
    
    return {
        "found": True,
        "fdc_id": result.get('fdcId'),
        "description": result.get('description'),
        "nutrition_per_100g": nutrition
    }


@router.put("/dishes/{dish_id}")
async def update_dish(
    dish_id: int,
    dish: DishUpdate,
    authorized: bool = Depends(verify_admin_password)
):
    """Update an existing dish."""
    total_calories = sum(ing.calories for ing in dish.ingredients)
    
    dish_data = {
        'dish_id': dish_id,
        'dish_name': dish.dish_name,
        'weight (g)': dish.weight_g,
        'calories': total_calories,
        'ingredients':  json.dumps([
            {
                'usda_fdc_id': ing.usda_fdc_id,
                'name': ing.name,
                'weight_g': ing.weight_g,
                'calories': ing.calories,
                'carbs': ing.carbs,
                'protein': ing.protein,
                'fat': ing.fat
            }
            for ing in dish.ingredients
        ]),
        'country': dish.country,
        'date_accessed': datetime.now().strftime('%Y-%m-%d')
    }
    
    success = dishes_handler.update_dish(dish_id, dish_data)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update dish")
    
    return {"message": "Dish updated successfully"}


@router.delete("/dishes/{dish_id}")
async def delete_dish(
    dish_id: int,
    authorized: bool = Depends(verify_admin_password)
):
    """Delete a dish from database."""
    success = dishes_handler.delete_dish(dish_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Dish not found")
    
    return {"message":  "Dish deleted successfully"}