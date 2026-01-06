"""Dishes data handler with semantic matching."""
import json
import pandas as pd
from typing import List, Dict, Optional
from rapidfuzz import fuzz, process
from sentence_transformers import SentenceTransformer, util
from app.config import settings
from app.models.schemas import IngredientWithNutrition


class DishesHandler:
    """Handler for dishes database with semantic matching."""
    
    def __init__(self):
        """Initialize dishes handler."""
        self.dishes = []
        self.df = None
        self.usda_handler = None
        
        # Semantic model (lazy load)
        self._model = None
        self._dish_embeddings = None
        self._dish_names = []
        self._dish_map = {}  # name -> dish mapping
    
    def _get_semantic_model(self):
        """Lazy load semantic model."""
        if self._model is None:
            print("   🧠 Loading semantic model (first time only)...")
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
            self._precompute_embeddings()
        return self._model
    
    def _precompute_embeddings(self):
        """Precompute embeddings for all dishes."""
        self._dish_names = []
        self._dish_map = {}
        
        for d in self.dishes:
            name = self._get_dish_name(d)
            if name: 
                name_lower = name.lower().strip()
                self._dish_names.append(name_lower)
                self._dish_map[name_lower] = d
        
        if self._dish_names:
            self._dish_embeddings = self._model.encode(
                self._dish_names, 
                convert_to_tensor=True,
                show_progress_bar=False
            )
            print(f"   ✅ Precomputed embeddings for {len(self._dish_names)} dishes")
    
    def load_data(self):
        """Load dishes from Excel file."""
        try:
            self.df = pd.read_excel(settings.dishes_path, sheet_name='dishes')
            self.dishes = self.df.to_dict('records')
            
            print(f"Excel columns: {list(self.df.columns)}")
            print(f"Loaded {len(self.dishes)} dishes from Excel")
            
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
            dish.get('country') or
            dish.get('Country') or 
            dish.get('COUNTRY') or 
            ''
        ).strip()
    
    def _semantic_search(self, query:  str, candidates: List[Dict], threshold: float = 0.65) -> Optional[Dict]:
        """
        Find dish using semantic similarity.
        
        Args:
            query: User's dish query
            candidates: List of dish candidates to search
            threshold: Minimum similarity score (0-1)
            
        Returns: 
            Best matching dish or None
        """
        try:
            model = self._get_semantic_model()
            
            # Get names of candidates
            candidate_names = []
            candidate_dishes = []
            for d in candidates:
                name = self._get_dish_name(d)
                if name:
                    candidate_names.append(name.lower().strip())
                    candidate_dishes.append(d)
            
            if not candidate_names: 
                return None
            
            # Encode query and candidates
            query_embedding = model.encode(query.lower(), convert_to_tensor=True, show_progress_bar=False)
            candidate_embeddings = model.encode(candidate_names, convert_to_tensor=True, show_progress_bar=False)
            
            # Calculate similarities
            similarities = util.cos_sim(query_embedding, candidate_embeddings)[0]
            
            # Get best match
            best_idx = similarities.argmax().item()
            best_score = similarities[best_idx].item()
            best_name = candidate_names[best_idx]
            
            print(f"   🧠 Semantic:  '{best_name}' (similarity: {best_score:.2%})")
            
            if best_score >= threshold:
                return candidate_dishes[best_idx]
            
            return None
            
        except Exception as e:
            print(f"   ⚠️ Semantic matching error: {e}")
            return None
    
    def find_dish(
        self,
        dish_name: str,
        country: Optional[str] = None,
        fuzzy_threshold: int = 90,
        semantic_threshold: float = 0.70
    ) -> Optional[Dict]:
        """
        Find dish using combined fuzzy + semantic matching.
        
        Strategy:
        1.Exact match → Return immediately
        2.High fuzzy match (90%+) → Return immediately  
        3. Semantic match (70%+) → Return if confident
        4.Medium fuzzy (80-90%) + Semantic agrees → Return
        5.Otherwise → No match (use GPT breakdown)
        """
        if not self.dishes:
            print("⚠️ No dishes loaded!")
            return None
            
        dish_name_lower = dish_name.lower().strip()
        
        print(f"\n🔍 DISH DATABASE SEARCH")
        print(f"   Looking for: '{dish_name}'")
        print(f"   Country filter: {country}")
        
        # Filter by country
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
        
        # Build choice list
        dish_choices = []
        for dish in candidates:
            name = self._get_dish_name(dish)
            if name:
                dish_choices.append((name.lower().strip(), dish))
        
        # === STRATEGY 1: Exact match ===
        for name, dish in dish_choices:
            if name == dish_name_lower: 
                print(f"   ✅ EXACT MATCH:  '{name}'")
                return dish
        
        # === STRATEGY 2:  Fuzzy matching ===
        fuzzy_match = None
        fuzzy_score = 0
        
        if dish_choices:
            result = process.extractOne(
                dish_name_lower,
                [choice[0] for choice in dish_choices],
                scorer=fuzz.token_set_ratio
            )
            
            if result: 
                matched_name, score, idx = result
                fuzzy_match = matched_name
                fuzzy_score = score
                print(f"   📝 Fuzzy:  '{matched_name}' (score: {score}%)")
        
        # === STRATEGY 3: Semantic matching ===
        semantic_dish = self._semantic_search(dish_name_lower, candidates, semantic_threshold)
        semantic_name = self._get_dish_name(semantic_dish).lower() if semantic_dish else None
        
        # === DECISION LOGIC ===
        
        # High confidence fuzzy (90%+) → Accept
        if fuzzy_score >= 90:
            print(f"   ✅ HIGH FUZZY MATCH: '{fuzzy_match}' ({fuzzy_score}%)")
            for name, dish in dish_choices:
                if name == fuzzy_match:
                    return dish
        
        # Semantic match exists
        if semantic_dish: 
            # Check if fuzzy and semantic agree
            if fuzzy_match == semantic_name: 
                print(f"   ✅ FUZZY + SEMANTIC AGREE: '{semantic_name}'")
                return semantic_dish
            
            # They disagree - trust semantic (understands meaning)
            if fuzzy_score < 90:
                print(f"   🧠 SEMANTIC WINS: '{semantic_name}' (fuzzy suggested '{fuzzy_match}')")
                return semantic_dish
        
        # Medium fuzzy (80-90%) without semantic confirmation
        if 80 <= fuzzy_score < 90:
            print(f"   ⚠️ MEDIUM FUZZY ({fuzzy_score}%) without semantic confirmation")
            print(f"   ❌ Rejecting to avoid false match")
        
        # No confident match
        print(f"   ❌ No confident match found")
        print(f"   📋 Available dishes sample:")
        for name, dish in dish_choices[:5]:
            print(f"      - {name}")
        
        return None
    
    def get_dish_ingredients(self, dish: Dict) -> List[IngredientWithNutrition]:
        """Extract ingredients from dish."""
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
                
                print(f"      • {name}: {weight_g}g = {calories:.1f} cal (C:{carbs:.1f}g P:{protein:.1f}g F:{fat:.1f}g)")
                
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
    
    def get_all_dishes(self, country:  Optional[str] = None) -> List[Dict]:
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