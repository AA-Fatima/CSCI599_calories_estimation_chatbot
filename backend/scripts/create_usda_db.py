"""Convert USDA JSON files to SQLite database."""
import json
import sqlite3
import os
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "usda.db"
FOUNDATION_PATH = DATA_DIR / "USDA_foundation.json"
SR_LEGACY_PATH = DATA_DIR / "USDA_sr_legacy.json"


def create_database():
    """Create SQLite database from USDA JSON files."""
    
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print("Removed old database")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fdc_id INTEGER,
            description TEXT,
            description_lower TEXT,
            calories REAL DEFAULT 0,
            protein REAL DEFAULT 0,
            carbs REAL DEFAULT 0,
            fat REAL DEFAULT 0,
            source TEXT
        )
    ''')
    
    cursor.execute('CREATE INDEX idx_description_lower ON foods(description_lower)')
    cursor.execute('CREATE INDEX idx_fdc_id ON foods(fdc_id)')
    
    print("Created database tables")
    
    # Load Foundation Foods
    if FOUNDATION_PATH.exists():
        print(f"Loading Foundation Foods...")
        with open(FOUNDATION_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        foods = data.get('FoundationFoods', []) or data.get('foods', [])
        count = insert_foods(cursor, foods, 'foundation')
        print(f"Inserted {count} foundation foods")
    
    # Load SR Legacy Foods
    if SR_LEGACY_PATH.exists():
        print(f"Loading SR Legacy Foods...")
        with open(SR_LEGACY_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        foods = data.get('SRLegacyFoods', []) or data.get('foods', [])
        count = insert_foods(cursor, foods, 'sr_legacy')
        print(f"Inserted {count} legacy foods")
    
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) FROM foods')
    total = cursor.fetchone()[0]
    print(f"Total foods: {total}")
    
    conn.close()
    print(f"Database saved:  {DB_PATH}")


def insert_foods(cursor, foods, source):
    """Insert foods into database."""
    count = 0
    for food in foods:
        fdc_id = food.get('fdcId', 0)
        description = food.get('description', '')
        if not description:
            continue
        
        calories, protein, carbs, fat = extract_nutrition(food)
        
        cursor.execute('''
            INSERT INTO foods (fdc_id, description, description_lower, calories, protein, carbs, fat, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fdc_id, description, description.lower(), calories, protein, carbs, fat, source))
        count += 1
    
    return count


def extract_nutrition(food):
    """Extract calories (kcal), protein, carbs, fat from USDA food."""
    calories = 0.0
    protein = 0.0
    carbs = 0.0
    fat = 0.0
    
    for item in food.get('foodNutrients', []):
        nutrient = item.get('nutrient', {})
        name = (nutrient.get('name', '') or item.get('nutrientName', '')).lower()
        unit = (nutrient.get('unitName', '') or item.get('unitName', '')).lower()
        value = float(item.get('amount') or item.get('value') or 0)
        
        # Calories - ONLY kcal
        if 'energy' in name and 'kcal' in unit:
            calories = value
        
        # Protein
        elif name == 'protein':
            protein = value
        
        # Carbs
        elif 'carbohydrate' in name: 
            carbs = value
        
        # Fat
        elif 'lipid' in name or 'fat' in name:
            fat = value
    
    return calories, protein, carbs, fat


if __name__ == '__main__': 
    create_database()