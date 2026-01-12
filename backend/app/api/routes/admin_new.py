"""Refactored admin API routes using repositories."""
from fastapi import APIRouter, HTTPException, Query, Header, Depends
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import AdminStatsResponse
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


@router.delete("/missing-dishes/{dish_id}")
async def delete_missing_dish(
    dish_id: int,
    authorized: bool = Depends(verify_admin_password),
    db: AsyncSession = Depends(get_database)
):
    """Delete a missing dish record."""
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
            "id": d.id,
            "dish_name": d.dish_name,
            "dish_name_arabic": d.dish_name_arabic,
            "country": d.country,
            "total_calories": d.total_calories,
            "total_carbs": d.total_carbs,
            "total_protein": d.total_protein,
            "total_fat": d.total_fat,
            "ingredients": d.ingredients
        }
        for d in dishes
    ]
    
    return {"dishes": dishes_dicts, "total": len(dishes_dicts)}


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
