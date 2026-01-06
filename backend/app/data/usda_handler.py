"""USDA data handler using SQLite database."""
import sqlite3
from pathlib import Path
from typing import Dict, Optional, List
from rapidfuzz import fuzz, process
from app.config import BASE_DIR


class USDAHandler: 
    """Handler for USDA database."""
    
    def __init__(self):
        """Initialize USDA handler."""
        self.db_path = BASE_DIR / "data" / "usda.db"
        self.is_loaded = False
    
    def load_data(self):
        """Check if database exists."""
        if self.db_path.exists():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM foods')
            count = cursor.fetchone()[0]
            conn.close()
            self.is_loaded = True
            print(f"   ✅ USDA SQLite database ready with {count} foods")
        else:
            print(f"   ❌ USDA database not found at {self.db_path}")
            self.is_loaded = False
    
    def _get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def search_ingredient(self, ingredient_name: str, threshold: int = 70) -> Optional[Dict]:
        """Search for ingredient in USDA database."""
        if not self.is_loaded:
            print(f"      ⚠️ USDA database not loaded!")
            return None
        
        search_term = ingredient_name.lower().strip()
        print(f"      🔎 Searching SQLite for: '{search_term}'")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # === STRATEGY 1: Exact match ===
        cursor.execute(
            'SELECT * FROM foods WHERE description_lower = ?  LIMIT 1',
            (search_term,)
        )
        row = cursor.fetchone()
        if row:
            print(f"      ✅ EXACT match:  '{row[2]}'")
            conn.close()
            return self._row_to_dict(row)
        
        # === STRATEGY 2: Starts with match ===
        cursor.execute(
            'SELECT * FROM foods WHERE description_lower LIKE ? ORDER BY LENGTH(description) LIMIT 10',
            (search_term + '%',)
        )
        rows = cursor.fetchall()
        if rows:
            # Filter out unwanted matches
            best = None
            for row in rows:
                desc_lower = row[3]
                if any(word in desc_lower for word in ['extra', 'light', 'low', 'reduced', 'fat-free', 'salad', 'dressing']):
                    continue
                best = row
                break
            if not best:
                best = rows[0]
            print(f"      ✅ STARTS-WITH match: '{best[2]}'")
            conn.close()
            return self._row_to_dict(best)
        
        # === STRATEGY 3: Contains match ===
        main_ingredient = search_term.split(',')[0].strip()
        cursor.execute(
            'SELECT * FROM foods WHERE description_lower LIKE ? ORDER BY LENGTH(description) LIMIT 20',
            (main_ingredient + '%',)
        )
        rows = cursor.fetchall()
        if rows:
            # Prefer raw versions
            best = None
            for row in rows:
                desc_lower = row[3]
                if 'raw' in desc_lower: 
                    best = row
                    break
            if not best:
                for row in rows:
                    desc_lower = row[3]
                    if not any(x in desc_lower for x in ['juice', 'pudding', 'pie', 'cake', 'baby', 'infant']):
                        best = row
                        break
            if not best:
                best = rows[0]
            print(f"      ✅ CONTAINS match:  '{best[2]}'")
            conn.close()
            return self._row_to_dict(best)
        
        # === STRATEGY 4: Fuzzy match ===
        cursor.execute('SELECT description_lower, description, id FROM foods')
        all_foods = cursor.fetchall()
        
        descriptions = [row[0] for row in all_foods]
        result = process.extractOne(
            search_term,
            descriptions,
            scorer=fuzz.token_sort_ratio
        )
        
        if result and result[1] >= threshold:
            # Find the matching row
            cursor.execute(
                'SELECT * FROM foods WHERE description_lower = ?  LIMIT 1',
                (result[0],)
            )
            row = cursor.fetchone()
            if row: 
                print(f"      ✅ FUZZY match ({result[1]}%): '{row[2]}'")
                conn.close()
                return self._row_to_dict(row)
        
        conn.close()
        print(f"      ❌ No match found for '{search_term}'")
        return None
    
    def _row_to_dict(self, row) -> Dict:
        """Convert database row to dictionary."""
        return {
            'id': row[0],
            'fdcId': row[1],
            'description': row[2],
            'calories': row[4],
            'protein': row[5],
            'carbs': row[6],
            'fat':  row[7],
            'source': row[8]
        }
    
    def get_nutrition_per_100g(self, food_item:  Dict) -> Dict[str, float]: 
        """Get nutrition from food dict (already extracted in DB)."""
        nutrients = {
            'calories':  float(food_item.get('calories', 0)),
            'carbs': float(food_item.get('carbs', 0)),
            'protein': float(food_item.get('protein', 0)),
            'fat': float(food_item.get('fat', 0))
        }
        print(f"         📊 Nutrition:  {nutrients['calories']}cal, C:{nutrients['carbs']}g, P:{nutrients['protein']}g, F:{nutrients['fat']}g")
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