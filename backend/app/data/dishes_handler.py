"""Dishes data handler with smart matching."""
import json
import pandas as pd
from typing import List, Dict, Optional, Set
from rapidfuzz import fuzz, process
from sentence_transformers import SentenceTransformer, util
from app.config import settings
from app.models.schemas import IngredientWithNutrition


class DishesHandler:
    """Handler for dishes database with smart matching."""
    
    # =============================================
    # SYNONYMS - Words that mean the same thing
    # =============================================
    SYNONYMS = {
        # Container/Serving style
        'wrap': ['wrap', 'sandwich', 'pita', 'bread'],
        'sandwich': ['sandwich', 'wrap', 'pita', 'bread'],
        'plate': ['plate', 'dish', 'platter', 'bowl'],
        'bowl': ['bowl', 'plate', 'dish'],
        
        # Cooking methods
        'grilled': ['grilled', 'meshwi', 'mashwi', 'bbq', 'barbecue'],
        'fried': ['fried', 'ma2li', 'maqli', 'crispy'],
        'baked': ['baked', 'roasted', 'oven'],
        'boiled': ['boiled', 'masloo2', 'cooked'],
        
        # Sizes
        'small':  ['small', 'mini', 'sghir', 'sghire', 'saghir'],
        'medium': ['medium', 'regular', 'normal', 'wasat'],
        'large': ['large', 'big', 'kbir', 'kbire', 'kabir'],
        
        # Meat types
        'chicken': ['chicken', 'djej', 'djeij', 'djaj', 'dajaj', 'فراخ', 'دجاج'],
        'beef':  ['beef', 'lahme', 'lahm', 'لحم', 'لحمة'],
        'lamb': ['lamb', 'kharouf', 'غنم', 'خروف'],
        
        # Common foods
        'fries': ['fries', 'batata', 'potato', 'potatoes', 'chips', 'بطاطا'],
        'rice': ['rice', 'roz', 'riz', 'رز', 'أرز'],
        'bread': ['bread', 'khobz', 'khubz', 'pita', 'خبز'],
        'salad': ['salad', 'salata', 'سلطة'],
    }
    
    # =============================================
    # SPELLING VARIATIONS - Normalize to standard
    # =============================================
    SPELLING_VARIATIONS = {
        # Fajita
        'fahita': 'fajita', 'fajita': 'fajita', 'fahitas': 'fajita', 'fajitas': 'fajita',
        # Hummus
        'hommos': 'hummus', 'hummos': 'hummus', 'humus': 'hummus',
        '7ummus': 'hummus', '7ommos': 'hummus', 'حمص': 'hummus',
        # Tabbouleh
        'tabouleh': 'tabbouleh', 'taboule': 'tabbouleh',
        'tab2oule': 'tabbouleh', 'tabbouli': 'tabbouleh', 'تبولة': 'tabbouleh',
        # Falafel
        'flafel': 'falafel', 'felafel': 'falafel', 'فلافل': 'falafel',
        # Shawarma
        'shawrma': 'shawarma', 'shawerma': 'shawarma', 'shwarma': 'shawarma', 'شاورما': 'shawarma',
        # Kibbeh
        'kibbe': 'kibbeh', 'kebbeh': 'kibbeh', 'kubbeh': 'kibbeh', 'kubba': 'kibbeh', 'كبة': 'kibbeh',
        # Kunafa
        'knafeh': 'kunafa', 'knefe': 'kunafa', 'konafa': 'kunafa', 'kanafeh': 'kunafa', 'كنافة': 'kunafa',
        # Fattoush
        'fattush': 'fattoush', 'fatoush': 'fattoush', 'fattouch': 'fattoush', 'فتوش': 'fattoush',
        # Manakish
        'mana2ish': 'manakish', 'manaeesh': 'manakish',
        'man2ousheh': 'manakish', 'mankoushe': 'manakish', 'مناقيش': 'manakish',
        # Labneh
        'labne': 'labneh', 'labaneh': 'labneh', 'labna': 'labneh', 'لبنة': 'labneh',
        # Mujadara
        'mjaddara': 'mujadara', 'mudardara': 'mujadara', 'mejadra': 'mujadara', 'مجدرة': 'mujadara',
        # Koshari
        'koshary': 'koshari', 'kushari': 'koshari', 'koshri': 'koshari', 'كشري': 'koshari',
        # Kabsa
        'kabseh': 'kabsa', 'machboos': 'kabsa', 'machbus': 'kabsa', 'كبسة': 'kabsa',
        # Kousa
        'kousa': 'kousa', 'kusa': 'kousa', 'koussa': 'kousa', 'كوسا': 'kousa',
        # Ful
        'foul': 'ful', 'fool': 'ful', 'فول': 'ful',
        # Baba ghanoush
        'babaganoush': 'baba ghanoush', 'baba ganoush':  'baba ghanoush', 'متبل':  'baba ghanoush',
    }
    
    # =============================================
    # STOP WORDS - Only these are truly ignored
    # =============================================
    STOP_WORDS = {
        'with', 'and', 'the', 'a', 'an', 'of', 'in', 'on', 'for', 'to',
        'how', 'many', 'much', 'calories', 'calorie', 'cal', 'kcal',
        'please', 'thanks', 'thank', 'you',
        # Arabic articles
        'ال', 'و', 'في', 'من',
        # Arabizi articles
        'el', 'al', 'w', 'b', 'bi', 'bl', 'fi',
    }
    
    def __init__(self):
        """Initialize dishes handler."""
        self.dishes = []
        self.df = None
        self.usda_handler = None
        
        # Semantic model (lazy load)
        self._model = None
        self._dish_embeddings = None
        self._dish_names = []
        self._dish_map = {}
    
    def _normalize_spelling(self, word: str) -> str:
        """Normalize common spelling variations."""
        word_lower = word.lower().strip()
        return self.SPELLING_VARIATIONS.get(word_lower, word_lower)
    
    def _get_synonyms(self, word: str) -> Set[str]:
        """Get all synonyms for a word."""
        word_lower = word.lower().strip()
        for key, synonyms in self.SYNONYMS.items():
            if word_lower in synonyms:
                return set(synonyms)
        return {word_lower}
    
    def _words_are_synonyms(self, word1: str, word2: str) -> bool:
        """Check if two words are synonyms."""
        w1 = word1.lower().strip()
        w2 = word2.lower().strip()
        
        if w1 == w2:
            return True
        
        synonyms1 = self._get_synonyms(w1)
        synonyms2 = self._get_synonyms(w2)
        
        return bool(synonyms1 & synonyms2)
    
    def _extract_key_words(self, text: str) -> List[str]:
        """Extract key food words, removing only stop words."""
        words = text.lower().replace(',', ' ').replace('-', ' ').replace('+', ' ').split()
        key_words = []
        
        for word in words:
            word = word.strip()
            if word and word not in self.STOP_WORDS and len(word) > 1:
                # Normalize spelling
                normalized = self._normalize_spelling(word)
                key_words.append(normalized)
        
        return key_words
    
    def _calculate_match_score(self, query_words: List[str], dish_words: List[str]) -> float:
        """
        Calculate match score between query and dish.
        Uses synonym matching.
        """
        if not query_words or not dish_words: 
            return 0.0
        
        matched_query = 0
        matched_dish = 0
        
        # Check how many query words match dish words (including synonyms)
        for qword in query_words: 
            for dword in dish_words:
                if self._words_are_synonyms(qword, dword):
                    matched_query += 1
                    break
        
        # Check how many dish words match query words (including synonyms)
        for dword in dish_words:
            for qword in query_words:
                if self._words_are_synonyms(qword, dword):
                    matched_dish += 1
                    break
        
        # Calculate bidirectional coverage
        query_coverage = matched_query / len(query_words)
        dish_coverage = matched_dish / len(dish_words)
        
        # Weighted average (favor query coverage slightly)
        score = (query_coverage * 0.6) + (dish_coverage * 0.4)
        
        return score
    
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
            dish.get('name') or
            ''
        ).strip()
    
    def _get_dish_country(self, dish: Dict) -> str:
        """Get dish country handling different column names."""
        return str(
            dish.get('country') or
            dish.get('Country') or
            ''
        ).strip()
    
    def _semantic_search(self, query:  str, candidates: List[Dict], threshold: float = 0.80) -> Optional[Dict]:
        """Find dish using semantic similarity."""
        try:
            model = self._get_semantic_model()
            
            candidate_names = []
            candidate_dishes = []
            for d in candidates:
                name = self._get_dish_name(d)
                if name:
                    candidate_names.append(name.lower().strip())
                    candidate_dishes.append(d)
            
            if not candidate_names: 
                return None
            
            query_embedding = model.encode(query.lower(), convert_to_tensor=True, show_progress_bar=False)
            candidate_embeddings = model.encode(candidate_names, convert_to_tensor=True, show_progress_bar=False)
            
            similarities = util.cos_sim(query_embedding, candidate_embeddings)[0]
            
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
        fuzzy_threshold: int = 85,
        semantic_threshold: float = 0.85
    ) -> Optional[Dict]:
        """
        Find dish using multiple matching strategies with synonym support.
        
        Strategies (in order):
        1.Exact match
        2.Keyword + Synonym matching (high score)
        3.High fuzzy match (85%+)
        4.Very high semantic match (85%+) with keyword verification
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
        
        # Extract keywords from query
        query_words = self._extract_key_words(dish_name_lower)
        print(f"   🔑 Query words: {query_words}")
        
        # === STRATEGY 1: Exact match ===
        for name, dish in dish_choices:
            if name == dish_name_lower:
                print(f"   ✅ EXACT MATCH: '{name}'")
                return dish
        
        # === STRATEGY 2: Keyword + Synonym matching ===
        keyword_matches = []
        for name, dish in dish_choices:
            dish_words = self._extract_key_words(name)
            score = self._calculate_match_score(query_words, dish_words)
            
            if score > 0:
                keyword_matches.append((name, dish, score, dish_words))
        
        if keyword_matches:
            keyword_matches.sort(key=lambda x:  x[2], reverse=True)
            best = keyword_matches[0]
            
            print(f"   🔑 Best keyword match: '{best[0]}' (score: {best[2]:.2f})")
            
            # Accept if score is very high (90%+)
            if best[2] >= 0.9:
                print(f"   ✅ KEYWORD MATCH (high): '{best[0]}'")
                return best[1]
            
            # Accept if score is good (75%+) and it's the only good match
            if best[2] >= 0.75: 
                # Check if there are other close matches
                close_matches = [m for m in keyword_matches if m[2] >= best[2] - 0.1]
                if len(close_matches) == 1:
                    print(f"   ✅ KEYWORD MATCH (unique): '{best[0]}'")
                    return best[1]
                else:
                    print(f"   🔶 Multiple close matches, being cautious...")
        
        # === STRATEGY 3: Fuzzy matching ===
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
        
        # High confidence fuzzy (85%+)
        if fuzzy_score >= fuzzy_threshold: 
            print(f"   ✅ HIGH FUZZY MATCH:  '{fuzzy_match}' ({fuzzy_score}%)")
            for name, dish in dish_choices:
                if name == fuzzy_match:
                    return dish
        
        # === STRATEGY 4: Semantic matching (STRICT) ===
        semantic_dish = self._semantic_search(dish_name_lower, candidates, semantic_threshold)
        
        if semantic_dish: 
            semantic_name = self._get_dish_name(semantic_dish).lower()
            semantic_words = self._extract_key_words(semantic_name)
            
            # Verify with keyword check - must have at least one common meaningful word
            match_score = self._calculate_match_score(query_words, semantic_words)
            
            if match_score >= 0.5:
                print(f"   ✅ SEMANTIC MATCH (verified): '{semantic_name}' (keyword score: {match_score:.2f})")
                return semantic_dish
            else:
                print(f"   🔶 Semantic match '{semantic_name}' failed keyword verification (score: {match_score:.2f})")
        
        # No confident match
        print(f"   ❌ No confident match found")
        print(f"   📋 Available dishes sample:")
        for name, dish in dish_choices[:5]: 
            print(f"      - {name}")
        
        return None
    
    def get_dish_ingredients(self, dish:  Dict) -> List[IngredientWithNutrition]: 
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
                ingredient = IngredientWithNutrition(
                    name=ing['name'],
                    weight_g=float(ing['weight_g']),
                    usda_fdc_id=ing.get('usda_fdc_id'),
                    calories=float(ing.get('calories', 0)),
                    carbs=float(ing.get('carbs', 0)),
                    protein=float(ing.get('protein', 0)),
                    fat=float(ing.get('fat', 0))
                )
                ingredients.append(ingredient)
                print(f"      • {ing['name']}: {ing['weight_g']}g = {ing.get('calories', 0)} cal")
            
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
            self._reset_cache()
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
            self._reset_cache()
            return True
        except Exception as e:
            print(f"Error updating dish:  {e}")
            return False
    
    def delete_dish(self, dish_id: int) -> bool:
        """Delete a dish."""
        try:
            self.dishes = [d for d in self.dishes if d.get('dish_id') != dish_id]
            self.df = pd.DataFrame(self.dishes)
            self.df.to_excel(settings.dishes_path, index=False, sheet_name='dishes')
            self._reset_cache()
            return True
        except Exception as e: 
            print(f"Error deleting dish:  {e}")
            return False
    
    def _reset_cache(self):
        """Reset embeddings cache after data changes."""
        self._dish_embeddings = None
        self._dish_names = []
        self._dish_map = {}


# Global instance
dishes_handler = DishesHandler()