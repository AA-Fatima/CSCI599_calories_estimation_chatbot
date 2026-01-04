"""Missing dish service - tracks dishes not in dataset."""
import json
from typing import List, Dict
from datetime import datetime
from app.config import settings
from app.models.schemas import MissingDish, IngredientBase


class MissingDishService:
    """Service for tracking missing dishes."""
    
    def __init__(self):
        """Initialize missing dish service."""
        self.missing_dishes: List[Dict] = []
        self.load_data()
    
    def load_data(self):
        """Load missing dishes from JSON file."""
        try:
            with open(settings.missing_dishes_path, 'r', encoding='utf-8') as f:
                self.missing_dishes = json.load(f)
        except Exception as e:
            print(f"Error loading missing dishes: {e}")
            self.missing_dishes = []
    
    def save_data(self):
        """Save missing dishes to JSON file."""
        try:
            with open(settings.missing_dishes_path, 'w', encoding='utf-8') as f:
                json.dump(self.missing_dishes, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error saving missing dishes: {e}")
    
    def add_missing_dish(
        self,
        dish_name: str,
        dish_name_arabic: str,
        country: str,
        query_text: str,
        gpt_response: Dict,
        ingredients: List[IngredientBase]
    ):
        """
        Add or update missing dish record.
        
        Args:
            dish_name: Name of the dish
            dish_name_arabic: Arabic name
            country: Country variant
            query_text: Original user query
            gpt_response: GPT's response dictionary
            ingredients: GPT's suggested ingredients
        """
        # Check if dish already exists
        existing = None
        for dish in self.missing_dishes:
            if (dish['dish_name'].lower() == dish_name.lower() and
                dish['country'].lower() == country.lower()):
                existing = dish
                break
        
        if existing:
            # Increment query count and update last queried
            existing['query_count'] += 1
            existing['last_queried'] = datetime.now().isoformat()
        else:
            # Add new missing dish
            new_dish = {
                'dish_name': dish_name,
                'dish_name_arabic': dish_name_arabic,
                'country': country,
                'query_text': query_text,
                'gpt_response': gpt_response,
                'ingredients': [
                    {'name': ing.name, 'weight_g': ing.weight_g}
                    for ing in ingredients
                ],
                'query_count': 1,
                'first_queried': datetime.now().isoformat(),
                'last_queried': datetime.now().isoformat()
            }
            self.missing_dishes.append(new_dish)
        
        self.save_data()
    
    def get_all_missing_dishes(self) -> List[Dict]:
        """Get all missing dishes."""
        return self.missing_dishes
    
    def get_missing_dish_by_name(self, dish_name: str, country: str = None) -> Dict:
        """Get specific missing dish."""
        for dish in self.missing_dishes:
            if dish['dish_name'].lower() == dish_name.lower():
                if country is None or dish['country'].lower() == country.lower():
                    return dish
        return None
    
    def delete_missing_dish(self, dish_name: str, country: str):
        """Delete a missing dish record."""
        self.missing_dishes = [
            d for d in self.missing_dishes
            if not (d['dish_name'].lower() == dish_name.lower() and
                   d['country'].lower() == country.lower())
        ]
        self.save_data()


# Global instance
missing_dish_service = MissingDishService()
