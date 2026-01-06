"""USDA data handler."""
import json
import gzip
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from rapidfuzz import fuzz, process
from app.config import settings


class USDAHandler: 
    """Handler for USDA Foundation and SR Legacy datasets."""
    
    def __init__(self):
        """Initialize USDA handler."""
        self.foundation_foods = []
        self.legacy_foods = []
        self.all_foods = []
    
    def _load_json_file(self, file_path: str) -> dict:
        """Load JSON file, handling both regular and gzip compressed files."""
        path = Path(file_path)
        
        # Try to detect if file is gzipped by reading first bytes
        try: 
            with open(path, 'rb') as f:
                first_bytes = f.read(2)
            
            # GZIP magic number is 1f 8b
            if first_bytes == b'\x1f\x8b': 
                print(f"      📦 Detected GZIP format, decompressing...")
                with gzip.open(path, 'rt', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e: 
            print(f"      ❌ Error loading {path}: {e}")
            raise
        
    def load_data(self):
        """Load USDA data from JSON files."""
        # Load Foundation Foods
        try:
            print(f"   Loading foundation from: {settings.usda_foundation_path}")
            foundation_data = self._load_json_file(settings.usda_foundation_path)
            self.foundation_foods = (
                foundation_data.get('FoundationFoods', []) or 
                foundation_data.get('foods', [])
            )
            print(f"   ✅ Loaded {len(self.foundation_foods)} foundation foods")
        except FileNotFoundError:
            print(f"   ⚠️ Foundation file not found - skipping")
            self.foundation_foods = []
        except Exception as e:
            print(f"   ⚠️ Error loading foundation foods: {e}")
            self.foundation_foods = []
        
        # Load SR Legacy Foods
        try:
            print(f"   Loading legacy from: {settings.usda_sr_legacy_path}")
            legacy_data = self._load_json_file(settings.usda_sr_legacy_path)
            self.legacy_foods = (
                legacy_data.get('SRLegacyFoods', []) or 
                legacy_data.get('foods', [])
            )
            print(f"   ✅ Loaded {len(self.legacy_foods)} legacy foods")
        except FileNotFoundError: 
            print(f"   ⚠️ SR Legacy file not found - continuing with foundation only")
            self.legacy_foods = []
        except Exception as e: 
            print(f"   ⚠️ Error loading legacy foods:  {e}")
            self.legacy_foods = []
        
        self.all_foods = self.foundation_foods + self.legacy_foods
        print(f"   📊 Total USDA foods loaded:  {len(self.all_foods)}")
    
    def search_ingredient(self, ingredient_name: str, threshold: int = 70) -> Optional[Dict]:
        """Search for ingredient in USDA database."""
        if not self.all_foods:
            print(f"      ⚠️ No USDA foods loaded!")
            return None
        
        # Normalize search term
        search_term = ingredient_name.lower().strip()
        print(f"      🔎 Normalized search: '{search_term}'")
        
        # Build food list
        food_items = []
        for food in self.all_foods:
            desc = food.get('description', '')
            if desc: 
                food_items.append((desc.lower(), desc, food))
        
        # === STRATEGY 1: Exact match ===
        for desc_lower, desc_orig, food in food_items:
            if desc_lower == search_term:
                print(f"      ✅ EXACT match: '{desc_orig}'")
                return food
        
        # === STRATEGY 2: Starts with match ===
        starts_matches:  List[Tuple[str, Dict, int]] = []  # (desc_orig, food, length)
        
        for desc_lower, desc_orig, food in food_items:
            if desc_lower.startswith(search_term):
                starts_matches.append((desc_orig, food, len(desc_orig)))
            elif desc_lower.startswith(search_term + ","):
                starts_matches.append((desc_orig, food, len(desc_orig)))

        # In the STARTS-WITH section, add preference for "raw" or plain versions
            
        if starts_matches:
            # Prefer items WITHOUT "extra", "light", "low", etc.
            def score_match(match_tuple):
                desc_lower = match_tuple[0].lower()
                penalty = 0
                if any(word in desc_lower for word in ['extra', 'light', 'low', 'reduced', 'fat-free']):
                    penalty += 100
                if 'salad' in desc_lower or 'dressing' in desc_lower:
                    penalty += 50
                return (penalty, match_tuple[2])  # (penalty, length)
            
            starts_matches.sort(key=score_match)
            print(f"      ✅ STARTS-WITH match:  '{starts_matches[0][0]}'")
            return starts_matches[0][1]

        # === STRATEGY 3: Contains match ===
        search_parts = [p.strip() for p in search_term.split(',')]
        main_ingredient = search_parts[0]
        
        contains_matches: List[Tuple[str, Dict, int, int]] = []  # (desc_orig, food, score, length)
        
        for desc_lower, desc_orig, food in food_items: 
            desc_parts = [p.strip() for p in desc_lower.split(',')]
            
            # First part must match
            if desc_parts[0] == main_ingredient or desc_parts[0] == main_ingredient + 's':
                if len(search_parts) > 1:
                    all_found = all(sp in desc_lower for sp in search_parts)
                    if all_found:
                        score = 100
                        if 'raw' in desc_lower:
                            score += 10
                        contains_matches.append((desc_orig, food, score, len(desc_orig)))
                else:
                    score = 100
                    if 'raw' in desc_lower: 
                        score += 20
                    if any(x in desc_lower for x in ['juice', 'pudding', 'pie', 'cake', 'loaf', 'baby', 'infant']):
                        score -= 50
                    contains_matches.append((desc_orig, food, score, len(desc_orig)))
        
        if contains_matches:
            # Sort by score (desc), then length (asc)
            contains_matches.sort(key=lambda x:  (-x[2], x[3]))
            print(f"      ✅ CONTAINS match: '{contains_matches[0][0]}'")
            return contains_matches[0][1]
        
        # === STRATEGY 4: Fuzzy match ===
        result = process.extractOne(
            search_term,
            [item[0] for item in food_items],
            scorer=fuzz.token_sort_ratio
        )
        
        if result and result[1] >= threshold:
            for desc_lower, desc_orig, food in food_items: 
                if desc_lower == result[0]:
                    print(f"      ✅ FUZZY match ({result[1]}%): '{desc_orig}'")
                    return food
        
        print(f"      ❌ No match found for '{search_term}'")
        return None
    
    def get_nutrition_per_100g(self, food_item:  Dict) -> Dict[str, float]:
        """Extract nutritional values per 100g from USDA food item."""
        nutrients = {
            'calories':  0.0,
            'carbs': 0.0,
            'protein': 0.0,
            'fat': 0.0
        }
        
        food_nutrients = food_item.get('foodNutrients', [])
        
        for nutrient_item in food_nutrients: 
            nutrient_info = nutrient_item.get('nutrient', {})
            name = nutrient_info.get('name', '').lower()
            value = nutrient_item.get('amount', 0.0)
            
            if not name: 
                name = nutrient_item.get('nutrientName', '').lower()
                value = nutrient_item.get('value', 0.0)
            
            # Energy/Calories - multiple possible names
            if 'energy' in name and 'kcal' in nutrient_info.get('unitName', '').lower():
                nutrients['calories'] = float(value)
            elif 'energy' in name and nutrients['calories'] == 0:
                # Check if unit is kcal in the name itself
                unit = nutrient_info.get('unitName', '')
                if unit.lower() == 'kcal': 
                    nutrients['calories'] = float(value)
                # If value seems reasonable for kcal (not kJ which is much higher)
                elif value < 1000 and value > 0:
                    nutrients['calories'] = float(value)
            
            # Carbohydrates
            elif 'carbohydrate' in name and 'by difference' in name:
                nutrients['carbs'] = float(value)
            
            # Protein
            elif name == 'protein': 
                nutrients['protein'] = float(value)
            
            # Fat
            elif 'total lipid' in name or name == 'total lipid (fat)' or name == 'fat':
                nutrients['fat'] = float(value)
        
        # Debug print
        print(f"         📊 Extracted:  {nutrients['calories']}cal, C:{nutrients['carbs']}g, P:{nutrients['protein']}g, F:{nutrients['fat']}g")
        
        return nutrients
    
    def calculate_nutrition_by_weight(
        self,
        food_item: Dict,
        weight_g: float
    ) -> Dict[str, float]: 
        """Calculate nutrition for specific weight."""
        per_100g = self.get_nutrition_per_100g(food_item)
        
        return {
            'calories': round((per_100g['calories'] * weight_g) / 100, 1),
            'carbs': round((per_100g['carbs'] * weight_g) / 100, 1),
            'protein': round((per_100g['protein'] * weight_g) / 100, 1),
            'fat':  round((per_100g['fat'] * weight_g) / 100, 1),
        }


# Global instance
usda_handler = USDAHandler()