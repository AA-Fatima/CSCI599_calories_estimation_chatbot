"""Countries API routes."""
from fastapi import APIRouter
from app.models.schemas import CountryResponse
from app.data.dishes_handler import dishes_handler

router = APIRouter(prefix="/countries", tags=["countries"])


@router.get("", response_model=CountryResponse)
async def get_countries():
    """
    Get list of available countries.
    
    Returns:
        List of country names
    """
    countries = dishes_handler.get_all_countries()
    
    # Add some additional Arab countries even if not in dataset
    all_countries = set(countries + [
        "Lebanon", "Syria", "Iraq", "Saudi Arabia", "Egypt", 
        "Jordan", "Palestine", "Morocco", "Tunisia", "Algeria",
        "Kuwait", "UAE", "Qatar", "Bahrain", "Oman", "Yemen"
    ])
    
    return CountryResponse(countries=sorted(list(all_countries)))
