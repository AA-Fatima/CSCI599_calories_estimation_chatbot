"""Countries API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import CountryResponse
from app.repositories.dishes import DishesRepository
from app.api.deps import get_database

router = APIRouter(prefix="/countries", tags=["countries"])


@router.get("", response_model=CountryResponse)
async def get_countries(db: AsyncSession = Depends(get_database)):
    """
    Get list of available countries.
    
    Args:
        db: Database session
    
    Returns:
        List of country names
    """
    dishes_repo = DishesRepository(db)
    countries = await dishes_repo.get_all_countries()
    
    # Add some additional Arab countries even if not in dataset
    all_countries = set(countries + [
        "Lebanon", "Syria", "Iraq", "Saudi Arabia", "Egypt", 
        "Jordan", "Palestine", "Morocco", "Tunisia", "Algeria",
        "Kuwait", "UAE", "Qatar", "Bahrain", "Oman", "Yemen"
    ])
    
    return CountryResponse(countries=sorted(list(all_countries)))
