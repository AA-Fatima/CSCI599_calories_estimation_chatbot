"""Refactored admin API routes using repositories."""
from fastapi import APIRouter, HTTPException, Query, Header, Depends, Body
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import AdminStatsResponse, DishCreate, DishUpdate
from app.repositories.dishes import DishesRepository
from app.repositories.usda import USDARepository
from app.repositories.missing_dishes import MissingDishesRepository
from app.api.deps import get_database
from app.config import settings
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
    """Verify admin password. This endpoint only returns success/failure."""
    return {"authenticated": True}


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    authorized: bool = Depends(verify_admin_password),
    db: AsyncSession = Depends(get_database)
):
    """Get admin dashboard statistics."""
    dishes_repo = DishesRepository(db)
    missing_repo = MissingDishesRepository(db)
    
    # Get counts
    from sqlalchemy import select, func
    from app.models.database import Dish
    
    query = select(func.count(Dish.id))
    result = await db.execute(query)
    total_dishes = result.scalar()
    
    missing_dishes_count = await missing_repo.get_count(status="pending")
    countries = await dishes_repo.get_all_countries()
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
    db: AsyncSession = Depends(get_database),
    country: Optional[str] = Query(None, description="Filter by country"),
    status: Optional[str] = Query("pending", description="Filter by status")
):
    """Get list of missing dishes with filters."""
    missing_repo = MissingDishesRepository(db)
    missing = await missing_repo.get_all(status=status, country=country, limit=1000)
    
    # Convert to dict format
    missing_dicts = [
        {
            "id": m.id,
            "dish_name": m.dish_name,
            "dish_name_arabic": m.dish_name_arabic,
            "country": m.country,
            "query_text": m.query_text,
            "query_count": m.query_count,
            "first_queried": m.first_queried.isoformat() if m.first_queried else None,
            "last_queried": m.last_queried.isoformat() if m.last_queried else None,
            "status": m.status,
            "ingredients": m.ingredients,
            "gpt_response": m.gpt_response
        }
        for m in missing
    ]
    
    return {"missing_dishes": missing_dicts, "total": len(missing_dicts)}


@router.put("/missing-dishes/{dish_id}/status")
async def update_missing_dish_status(
    dish_id: int,
    status: str = Query(..., description="New status: pending, reviewed, added"),
    authorized: bool = Depends(verify_admin_password),
    db: AsyncSession = Depends(get_database)
):
    """Update status of a missing dish."""
    missing_repo = MissingDishesRepository(db)
    
    updated = await missing_repo.update_status(dish_id, status)
    
    if not updated:
        raise HTTPException(status_code=404, detail="Missing dish not found")
    
    await db.commit()
    
    return {"message": "Status updated successfully", "new_status": status}


@router.delete("/missing-dishes/by-name")
async def delete_missing_dish(
    dish_name: str = Query(..., description="Name of the dish"),
    country: str = Query(..., description="Country of the dish"),
    authorized: bool = Depends(verify_admin_password),
    db: AsyncSession = Depends(get_database)
):
    """Delete a missing dish record by name and country."""
    missing_repo = MissingDishesRepository(db)
    
    # Find the dish by name and country
    missing_dish = await missing_repo.get_by_name_and_country(dish_name, country)
    
    if not missing_dish:
        raise HTTPException(status_code=404, detail="Missing dish not found")
    
    # Delete by ID
    deleted = await missing_repo.delete(missing_dish.id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Missing dish not found")
    
    await db.commit()
    
    return {"message": "Missing dish deleted"}


@router.delete("/missing-dishes/{dish_id}")
async def delete_missing_dish_by_id(
    dish_id: int,
    authorized: bool = Depends(verify_admin_password),
    db: AsyncSession = Depends(get_database)
):
    """Delete a missing dish record by ID."""
    missing_repo = MissingDishesRepository(db)
    
    deleted = await missing_repo.delete(dish_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Missing dish not found")
    
    await db.commit()
    
    return {"message": "Missing dish deleted"}


@router.get("/dishes")
async def get_all_dishes(
    authorized: bool = Depends(verify_admin_password),
    db: AsyncSession = Depends(get_database),
    country: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get all dishes with optional country filter."""
    dishes_repo = DishesRepository(db)
    dishes = await dishes_repo.get_all(country=country, skip=skip, limit=limit)
    
    # Convert to dict format
    dishes_dicts = [
        {
            "dish_id": d.id,  # Use dish_id to match frontend interface
            "dish_name": d.dish_name,
            "dish_name_arabic": d.dish_name_arabic,
            "country": d.country,
            "total_calories": d.total_calories,
            "total_carbs": d.total_carbs,
            "total_protein": d.total_protein,
            "total_fat": d.total_fat,
            "ingredients": d.ingredients,
            "weight (g)": sum(ing.get('weight_g', 0) for ing in (d.ingredients or [])),
            "calories": d.total_calories or 0,
            "date_accessed": d.created_at.isoformat() if d.created_at else None
        }
        for d in dishes
    ]
    
    return {"dishes": dishes_dicts, "total": len(dishes_dicts)}


@router.post("/dishes")
async def create_dish(
    dish: DishCreate,
    authorized: bool = Depends(verify_admin_password),
    db: AsyncSession = Depends(get_database)
):
    """Create a new dish in the database."""
    from app.services.embedding import embedding_service
    from app.services.nutrition import nutrition_service
    
    dishes_repo = DishesRepository(db)
    
    # Calculate totals from ingredients
    totals = nutrition_service.calculate_totals(dish.ingredients)
    
    # Generate embedding for dish name
    dish_embedding = embedding_service.encode(dish.dish_name)
    
    # Prepare dish data
    dish_data = {
        "dish_name": dish.dish_name,
        "dish_name_arabic": None,
        "country": dish.country,
        "total_calories": totals.calories,
        "total_carbs": totals.carbs,
        "total_protein": totals.protein,
        "total_fat": totals.fat,
        "ingredients": [ing.dict() for ing in dish.ingredients],
        "embedding": dish_embedding
    }
    
    created_dish = await dishes_repo.create(dish_data)
    await db.commit()
    
    return {
        "message": "Dish created successfully",
        "dish": {
            "id": created_dish.id,
            "dish_name": created_dish.dish_name,
            "country": created_dish.country,
            "total_calories": created_dish.total_calories
        }
    }


@router.put("/dishes/{dish_id}")
async def update_dish(
    dish_id: int,
    dish: DishUpdate,
    authorized: bool = Depends(verify_admin_password),
    db: AsyncSession = Depends(get_database)
):
    """Update an existing dish."""
    from app.services.embedding import embedding_service
    from app.services.nutrition import nutrition_service
    
    dishes_repo = DishesRepository(db)
    
    # Calculate totals from ingredients
    totals = nutrition_service.calculate_totals(dish.ingredients)
    
    # Generate embedding for dish name
    dish_embedding = embedding_service.encode(dish.dish_name)
    
    # Prepare dish data
    dish_data = {
        "dish_name": dish.dish_name,
        "dish_name_arabic": getattr(dish, 'dish_name_arabic', None),
        "country": dish.country,
        "total_calories": totals.calories,
        "total_carbs": totals.carbs,
        "total_protein": totals.protein,
        "total_fat": totals.fat,
        "ingredients": [ing.dict() for ing in dish.ingredients],
        "embedding": dish_embedding
    }
    
    updated_dish = await dishes_repo.update(dish_id, dish_data)
    
    if not updated_dish:
        raise HTTPException(status_code=404, detail="Dish not found")
    
    await db.commit()
    
    return {
        "message": "Dish updated successfully",
        "dish": {
            "id": updated_dish.id,
            "dish_name": updated_dish.dish_name,
            "country": updated_dish.country,
            "total_calories": updated_dish.total_calories
        }
    }


@router.delete("/dishes/{dish_id}")
async def delete_dish(
    dish_id: int,
    authorized: bool = Depends(verify_admin_password),
    db: AsyncSession = Depends(get_database)
):
    """Delete a dish from the database."""
    dishes_repo = DishesRepository(db)
    
    deleted = await dishes_repo.delete(dish_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Dish not found")
    
    await db.commit()
    
    return {"message": "Dish deleted successfully"}


@router.post("/missing-dishes/{dish_name}/add-to-database")
async def add_missing_dish_to_database(
    dish_name: str,
    country: str = Query(..., description="Country of the dish"),
    dish: Optional[DishCreate] = Body(None, description="Edited dish data (optional)"),
    authorized: bool = Depends(verify_admin_password),
    db: AsyncSession = Depends(get_database)
):
    """Add a missing dish to the main dishes database by name and country.
    
    If dish data is provided in the request body, use that (for edited dishes).
    Otherwise, use the original missing dish data.
    """
    from sqlalchemy import select
    from app.models.database import MissingDish
    from app.services.embedding import embedding_service
    from app.services.nutrition import nutrition_service
    
    # Find missing dish by name and country
    missing_repo = MissingDishesRepository(db)
    missing_dish = await missing_repo.get_by_name_and_country(dish_name, country)
    
    if not missing_dish:
        raise HTTPException(status_code=404, detail="Missing dish not found")
    
    # Use provided dish data if available (edited dish), otherwise use missing dish data
    # Check if dish has valid ingredients (not empty dict)
    has_edited_data = dish is not None and hasattr(dish, 'ingredients') and dish.ingredients and len(dish.ingredients) > 0
    
    if has_edited_data:
        # Use edited ingredients from request
        ingredients = dish.ingredients
        dish_name_final = dish.dish_name
        country_final = dish.country
        dish_name_arabic = None
    else:
        # Use original missing dish data
        if not missing_dish.ingredients:
            raise HTTPException(
                status_code=400,
                detail="Missing dish has no ingredients. Please add ingredients first."
            )
        # Convert ingredients to IngredientWithNutrition format
        from app.models.schemas import IngredientWithNutrition
        ingredients = [
            IngredientWithNutrition(**ing) for ing in missing_dish.ingredients
        ]
        dish_name_final = missing_dish.dish_name
        country_final = missing_dish.country
        dish_name_arabic = missing_dish.dish_name_arabic
    
    # Calculate totals
    totals = nutrition_service.calculate_totals(ingredients)
    
    # Generate embedding
    dish_embedding = embedding_service.encode(dish_name_final)
    
    # Prepare ingredients for storage (convert to dict format)
    ingredients_dict = [
        {
            "name": ing.name,
            "weight_g": ing.weight_g,
            "usda_fdc_id": ing.usda_fdc_id,
            "calories": ing.calories,
            "carbs": ing.carbs,
            "protein": ing.protein,
            "fat": ing.fat
        }
        for ing in ingredients
    ]
    
    # Create dish
    dishes_repo = DishesRepository(db)
    dish_data = {
        "dish_name": dish_name_final,
        "dish_name_arabic": dish_name_arabic,
        "country": country_final,
        "total_calories": totals.calories,
        "total_carbs": totals.carbs,
        "total_protein": totals.protein,
        "total_fat": totals.fat,
        "ingredients": ingredients_dict,
        "embedding": dish_embedding
    }
    
    created_dish = await dishes_repo.create(dish_data)
    
    # Update missing dish status to "added"
    await missing_repo.update_status(missing_dish.id, "added")
    
    await db.commit()
    
    return {
        "message": "Dish added to database successfully",
        "dish": {
            "id": created_dish.id,
            "dish_name": created_dish.dish_name,
            "country": created_dish.country,
            "total_calories": created_dish.total_calories
        }
    }


@router.post("/missing-dishes/{dish_id}/add-to-database")
async def add_missing_dish_to_database_by_id(
    dish_id: int,
    authorized: bool = Depends(verify_admin_password),
    db: AsyncSession = Depends(get_database)
):
    """Add a missing dish to the main dishes database by ID."""
    """Add a missing dish to the main dishes database."""
    from sqlalchemy import select
    from app.models.database import MissingDish
    from app.services.embedding import embedding_service
    from app.services.nutrition import nutrition_service
    
    # Get missing dish
    query = select(MissingDish).where(MissingDish.id == dish_id)
    result = await db.execute(query)
    missing_dish = result.scalar_one_or_none()
    
    if not missing_dish:
        raise HTTPException(status_code=404, detail="Missing dish not found")
    
    if not missing_dish.ingredients:
        raise HTTPException(
            status_code=400,
            detail="Missing dish has no ingredients. Please add ingredients first."
        )
    
    # Convert ingredients to IngredientWithNutrition format
    from app.models.schemas import IngredientWithNutrition
    ingredients = [
        IngredientWithNutrition(**ing) for ing in missing_dish.ingredients
    ]
    
    # Calculate totals
    totals = nutrition_service.calculate_totals(ingredients)
    
    # Generate embedding
    dish_embedding = embedding_service.encode(missing_dish.dish_name)
    
    # Create dish
    dishes_repo = DishesRepository(db)
    dish_data = {
        "dish_name": missing_dish.dish_name,
        "dish_name_arabic": missing_dish.dish_name_arabic,
        "country": missing_dish.country,
        "total_calories": totals.calories,
        "total_carbs": totals.carbs,
        "total_protein": totals.protein,
        "total_fat": totals.fat,
        "ingredients": missing_dish.ingredients,
        "embedding": dish_embedding
    }
    
    created_dish = await dishes_repo.create(dish_data)
    
    # Update missing dish status
    missing_repo = MissingDishesRepository(db)
    await missing_repo.update_status(dish_id, "added")
    
    await db.commit()
    
    return {
        "message": "Dish added to database successfully",
        "dish": {
            "id": created_dish.id,
            "dish_name": created_dish.dish_name,
            "country": created_dish.country,
            "total_calories": created_dish.total_calories
        }
    }


@router.get("/usda/search")
async def search_usda(
    authorized: bool = Depends(verify_admin_password),
    db: AsyncSession = Depends(get_database),
    query: str = Query(..., description="Ingredient name to search")
):
    """Search USDA database for an ingredient."""
    from app.services.embedding import embedding_service
    
    usda_repo = USDARepository(db)
    
    # Generate embedding and search
    query_embedding = embedding_service.encode(query)
    result = await usda_repo.search(query_embedding, threshold=0.6)
    
    if not result:
        return {"found": False, "message": f"No match found for '{query}'"}
    
    food, similarity = result
    
    return {
        "found": True,
        "fdc_id": food.fdc_id,
        "description": food.description,
        "similarity": similarity,
        "nutrition_per_100g": {
            "calories": food.calories,
            "carbs": food.carbs,
            "protein": food.protein,
            "fat": food.fat
        }
    }
