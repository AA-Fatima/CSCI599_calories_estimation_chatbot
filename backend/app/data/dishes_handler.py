"""Excel dishes handler."""
import json
import pandas as pd
from typing import List, Optional, Dict
from rapidfuzz import fuzz, process
from app.config import settings
from app.models.schemas import Dish, IngredientWithNutrition


class DishesHandler:
    """Handler for dishes Excel file."""
    
    def __init__(self):
        """Initialize dishes handler."""
        self.dishes = []
        self.df = None
        self.usda_handler = None  # Will be set after import
        
    def load_data(self):
        """Load dishes from Excel file."""
        try:
            self.df = pd.read_excel(settings.dishes_path, sheet_name='dishes')
            self.dishes = self.df.to_dict('records')
            
            # Debug:  Print column names
            print(f"Excel columns: {list(self.df.columns)}")
            print(f"Loaded {len(self.dishes)} dishes from Excel")
            
            # Print first dish to see structure
            if self.dishes:
                print(f"Sample dish keys: {list(self.dishes[0].keys())}")
                sample_name = self._get_dish_name(self.dishes[0])
                sample_country = self._get_dish_country(self.dishes[0])
                print(f"Sample dish: '{sample_name}' from '{sample_country}'")
                
        except Exception as e: 
            print(f"Error loading dishes: {e}")
            self.dishes = []
            self.df = pd.DataFrame()
    
    def _get_dish_name(self, dish: Dict) -> str:
        """Get dish name handling different column names."""
        return str(
            dish.get('dish_name') or 
            dish.get('dish name') or 
            dish.get('Dish Name') or 
            dish.get('Dish_Name') or
            dish.get('name') or 
            ''
        ).strip()
    
    def _get_dish_country(self, dish: Dict) -> str:
        """Get dish country handling different column names."""
        return str(
            dish.get('country') or  # lowercase - YOUR FORMAT
            dish.get('Country') or 
            dish.get('COUNTRY') or 
            ''
        ).strip()
    
    def find_dish(
        self,
        dish_name: str,
        country: Optional[str] = None,
        threshold: int = 75
    ) -> Optional[Dict]:
        """
        Find dish by name and optionally country using fuzzy matching.
        """
        if not self.dishes:
            print("⚠️ No dishes loaded!")
            return None
            
        dish_name_lower = dish_name.lower().strip()
        
        print(f"\n🔍 DISH DATABASE SEARCH")
        print(f"   Looking for: '{dish_name}'")
        print(f"   Country filter: {country}")
        
        candidates = self.dishes
        if country:
            candidates = [
                d for d in self.dishes 
                if self._get_dish_country(d).lower() == country.lower()
            ]
            print(f"   Found {len(candidates)} dishes for country '{country}'")
        
        if not candidates:
            print(f"   No dishes for country '{country}', searching all {len(self.dishes)} dishes...")
            candidates = self.dishes
        
        dish_choices = []
        for dish in candidates: 
            name = self._get_dish_name(dish)
            if name: 
                dish_choices.append((name.lower().strip(), dish))
        
        # First try exact match
        for name, dish in dish_choices:
            if name == dish_name_lower: 
                print(f"   ✅ EXACT MATCH FOUND:  '{name}'")
                return dish
        
        # Try fuzzy matching
        if dish_choices:
            result = process.extractOne(
                dish_name_lower,
                [choice[0] for choice in dish_choices],
                scorer=fuzz.token_set_ratio
            )
            
            if result: 
                matched_name, score, idx = result
                print(f"   🔎 Best fuzzy match: '{matched_name}' (score: {score}%)")
                
                if score >= threshold: 
                    for name, dish in dish_choices:
                        if name == matched_name:
                            print(f"   ✅ FUZZY MATCH ACCEPTED (score {score} >= {threshold})")
                            return dish
                else:
                    print(f"   ❌ Score {score}% is below threshold {threshold}%")
        
        print(f"   ❌ No match found.Available dishes sample:")
        for name, dish in dish_choices[:5]: 
            print(f"      - {name}")
        
        return None
    
    def get_dish_ingredients(self, dish:  Dict) -> List[IngredientWithNutrition]:
        """Extract ingredients from dish - they already have complete nutrition."""
        try:
            ingredients_json = dish.get('ingredients', '[]')
            if isinstance(ingredients_json, str):
                ingredients_data = json.loads(ingredients_json)
            else:
                ingredients_data = ingredients_json
            
            print(f"   📦 Found {len(ingredients_data)} ingredients in dataset")
            
            ingredients = []
            for ing in ingredients_data:
                name = ing['name']
                weight_g = float(ing['weight_g'])
                calories = float(ing.get('calories', 0))
                carbs = float(ing.get('carbs', 0))
                protein = float(ing.get('protein', 0))
                fat = float(ing.get('fat', 0))
                
                print(f"      • {name}:  {weight_g}g = {calories:.1f} cal (C:{carbs:.1f}g P:{protein:.1f}g F:{fat:.1f}g)")
                
                ingredient = IngredientWithNutrition(
                    name=name,
                    weight_g=weight_g,
                    usda_fdc_id=ing.get('usda_fdc_id'),
                    calories=calories,
                    carbs=carbs,
                    protein=protein,
                    fat=fat
                )
                ingredients.append(ingredient)
            
            return ingredients
            
        except Exception as e: 
            print(f"Error parsing ingredients: {e}")
            return []
        
    def get_all_dishes(self, country: Optional[str] = None) -> List[Dict]: 
        """Get all dishes, optionally filtered by country."""
        if country:
            return [
                d for d in self.dishes 
                if self._get_dish_country(d).lower() == country.lower()
            ]
        return self.dishes
    
    def get_all_countries(self) -> List[str]:
        """Get list of all unique countries."""
        countries = set()
        for dish in self.dishes:
            country = self._get_dish_country(dish)
            if country:
                countries.add(country)
        return sorted(list(countries))
    
    def add_dish(self, dish_data: Dict) -> bool:
        """Add a new dish to the Excel file."""
        try:
            self.dishes.append(dish_data)
            self.df = pd.DataFrame(self.dishes)
            self.df.to_excel(settings.dishes_path, index=False, sheet_name='dishes')
            return True
        except Exception as e:
            print(f"Error adding dish: {e}")
            return False
    
    def update_dish(self, dish_id:  int, dish_data: Dict) -> bool:
        """Update an existing dish."""
        try: 
            for i, dish in enumerate(self.dishes):
                if dish.get('dish_id') == dish_id:
                    self.dishes[i] = dish_data
                    break
            self.df = pd.DataFrame(self.dishes)
            self.df.to_excel(settings.dishes_path, index=False, sheet_name='dishes')
            return True
        except Exception as e:
            print(f"Error updating dish: {e}")
            return False
    
    def delete_dish(self, dish_id:  int) -> bool:
        """Delete a dish."""
        try:
            self.dishes = [d for d in self.dishes if d.get('dish_id') != dish_id]
            self.df = pd.DataFrame(self.dishes)
            self.df.to_excel(settings.dishes_path, index=False, sheet_name='dishes')
            return True
        except Exception as e:
            print(f"Error deleting dish: {e}")
            return False


# Global instance
dishes_handler = DishesHandler()